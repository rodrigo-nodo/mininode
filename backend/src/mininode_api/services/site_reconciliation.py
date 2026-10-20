"""Conservative, operator-controlled reconciliation of two existing apex/www sites.

Dry-run is the default. No public endpoint or automatic reconciliation.
All structural changes are one PostgreSQL transaction, with audit evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from psycopg.types.json import Jsonb

from mininode_api.services import access
from mininode_api.services.site_equivalence import inspect_www_equivalence


class ReconciliationBlocked(ValueError):
    """Refuse any ambiguous, cross-workspace or commercially linked reconciliation."""


@dataclass(frozen=True)
class ReconciliationResult:
    status: str
    workspace_id: UUID
    primary_site_id: UUID
    source_site_id: UUID
    primary_workspace_site_id: UUID
    source_workspace_site_id: UUID
    diagnostics: int


def _normalize_pair(primary: str, alias: str) -> tuple[str, str]:
    primary_host, _ = access.normalize_site_url(primary)
    alias_host, _ = access.normalize_site_url(alias)
    if (
        primary != primary_host or alias != alias_host
        or primary_host.startswith("www.")
        or primary_host.count(".") != 1
        or alias_host != f"www.{primary_host}"
    ):
        raise ReconciliationBlocked("Only exact normalized apex/www hostname pairs are supported")
    return primary_host, alias_host


def reconcile_existing_www(
    workspace_id: UUID,
    primary_hostname: str,
    alias_hostname: str,
    *,
    apply: bool = False,
    verifier=None,
) -> ReconciliationResult:
    """Preflight a single workspace pair, with an optional explicit atomic apply.

    Source association MUST already be detached, and both sites must be
    exclusive to this workspace with zero commercial references, even expired.
    Aborts on foreign identity, company mapping, collisions, missing schema,
    unexpected FKs or inconclusive live redirect evidence.
    """
    primary, alias = _normalize_pair(primary_hostname, alias_hostname)
    if not isinstance(workspace_id, UUID):
        raise ReconciliationBlocked("A workspace UUID is required")

    with access._connection() as connection, connection.cursor() as cursor:
        # Same lock used by automatic alias registration and site association.
        cursor.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            ("site-alias-www:" + primary,),
        )
        cursor.execute(
            """SELECT source_site_id, target_site_id, source_workspace_site_id,
                      target_workspace_site_id, moved_diagnostics, workspace_id
               FROM access.site_reconciliations WHERE source_hostname = %s""",
            (alias,),
        )
        old = cursor.fetchone()
        if old is not None:
            if old[5] != workspace_id:
                raise ReconciliationBlocked("Reconciliation belongs to another workspace")
            cursor.execute("SELECT id FROM access.sites WHERE hostname = %s", (primary,))
            target = cursor.fetchone()
            if target is None or target[0] != old[1]:
                raise ReconciliationBlocked("Previously reconciled target identity has changed")
            cursor.execute("SELECT id FROM access.sites WHERE hostname = %s", (alias,))
            if cursor.fetchone() is not None:
                raise ReconciliationBlocked("Previously reconciled source hostname was recreated")
            cursor.execute("SELECT site_id FROM access.site_aliases WHERE hostname = %s", (alias,))
            alias_record = cursor.fetchone()
            if alias_record is None or alias_record[0] != old[1]:
                raise ReconciliationBlocked("Previously reconciled alias no longer resolves to its target")
            return ReconciliationResult("already_reconciled", workspace_id, old[1], old[0], old[3], old[2], old[4])

        cursor.execute(
            """SELECT id, hostname FROM access.sites
               WHERE hostname IN (%s, %s) ORDER BY hostname FOR UPDATE""",
            (primary, alias),
        )
        sites = {hostname: site_id for site_id, hostname in cursor.fetchall()}
        if set(sites) != {primary, alias} or sites[primary] == sites[alias]:
            raise ReconciliationBlocked("Both distinct primary site records are required")
        target_id, source_id = sites[primary], sites[alias]

        cursor.execute(
            """SELECT id, workspace_id, site_id, company_id, detached_at
               FROM access.workspace_sites
               WHERE site_id IN (%s, %s) ORDER BY id FOR UPDATE""",
            (target_id, source_id),
        )
        links = cursor.fetchall()
        if (
            len(links) != 2
            or {item[1] for item in links} != {workspace_id}
            or {item[2] for item in links} != {target_id, source_id}
            or any(item[3] is not None for item in links)
        ):
            raise ReconciliationBlocked("Sites must belong only to the selected workspace without company links")
        by_site = {item[2]: item for item in links}
        primary_link, source_link = by_site[target_id], by_site[source_id]
        if primary_link[4] is not None or source_link[4] is None:
            raise ReconciliationBlocked("Keep the primary active and unlink the secondary before reconciliation")

        cursor.execute(
            """SELECT count(*) FROM access.site_aliases
               WHERE site_id = %s OR hostname = %s""",
            (source_id, alias),
        )
        if cursor.fetchone()[0]:
            raise ReconciliationBlocked("Conflicting or dependent site aliases exist")

        # Reject unexpected foreign-key dependents; deleting the source identity
        # must not silently CASCADE data in a newly introduced subsystem.
        cursor.execute(
            """SELECT conrelid::regclass::text FROM pg_constraint
               WHERE contype = 'f' AND confrelid = 'access.sites'::regclass
                 AND conrelid NOT IN ('access.workspace_sites'::regclass,
                                      'access.site_aliases'::regclass,
                                      'access.site_reconciliations'::regclass)"""
        )
        if cursor.fetchall():
            raise ReconciliationBlocked("Unexpected dependencies reference access.sites")
        cursor.execute(
            "SELECT count(*) FROM access.site_reconciliations WHERE target_site_id = %s",
            (source_id,),
        )
        if cursor.fetchone()[0]:
            raise ReconciliationBlocked("Secondary site is a historical reconciliation target")

        # Inspect ALL foreign keys referencing the association we will remove.
        # Only known columns may reference its ID. A new FK with CASCADE or
        # SET NULL must be noticed here rather than silently changing data.
        cursor.execute(
            """SELECT c.conrelid::regclass::text, a.attname,
                      array_length(c.conkey, 1), ref_att.attname
               FROM pg_constraint AS c
               LEFT JOIN pg_attribute AS a
                 ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
               LEFT JOIN pg_attribute AS ref_att
                 ON ref_att.attrelid = c.confrelid AND ref_att.attnum = c.confkey[1]
               WHERE c.contype = 'f'
                 AND c.confrelid = 'access.workspace_sites'::regclass"""
        )
        permitted = {
            ("privacy.diagnostic", "workspace_site_id"),
            ("access.entitlements", "workspace_site_id"),
            ("billing.orders", "workspace_site_id"),
            ("access.site_reconciliations", "target_workspace_site_id"),
        }
        fk_dependencies = cursor.fetchall()
        if any(
            (table, column) not in permitted or key_columns != 1 or referenced_column != "id"
            for table, column, key_columns, referenced_column in fk_dependencies
        ):
            raise ReconciliationBlocked("Unexpected dependencies reference access.workspace_sites")
        cursor.execute(
            """SELECT EXISTS (
                 SELECT 1 FROM access.site_reconciliations
                 WHERE target_workspace_site_id = %s
               )""",
            (source_link[0],),
        )
        if cursor.fetchone()[0]:
            raise ReconciliationBlocked("Secondary association is a historical reconciliation target")

        cursor.execute(
            """SELECT EXISTS (
                 SELECT 1 FROM access.entitlements e
                 JOIN access.workspace_sites ws ON ws.id = e.workspace_site_id
                 WHERE ws.site_id IN (%s, %s)
               ) OR EXISTS (
                 SELECT 1 FROM billing.orders b
                 JOIN access.workspace_sites ws ON ws.id = b.workspace_site_id
                 WHERE ws.site_id IN (%s, %s)
               )""",
            (target_id, source_id, target_id, source_id),
        )
        if cursor.fetchone()[0]:
            raise ReconciliationBlocked("Commercial records exist: manual review required")

        cursor.execute(
            "SELECT count(*) FROM privacy.diagnostic WHERE workspace_site_id = %s",
            (source_link[0],),
        )
        count = cursor.fetchone()[0]

        proof = (verifier or inspect_www_equivalence)(alias)
        if not (
            proof.equivalent is True
            and proof.requested_hostname == alias
            and proof.counterpart_hostname == primary
            and proof.reason == "stable_www_redirect"
        ):
            raise ReconciliationBlocked("Stable apex/www HTTPS redirect evidence not confirmed")

        result = ReconciliationResult(
            "applied" if apply else "ready",
            workspace_id, target_id, source_id, primary_link[0], source_link[0], count,
        )
        if not apply:
            return result

        # Record complete source rows before structural deletion, including
        # canonical URL, creation/update times and detachment timestamp.
        # All statements share one transaction; any later error rolls back
        # both history rewiring and the audit entry.
        cursor.execute(
            "SELECT to_jsonb(s) FROM access.sites AS s WHERE id = %s",
            (source_id,),
        )
        original_site = cursor.fetchone()
        cursor.execute(
            "SELECT to_jsonb(ws) FROM access.workspace_sites AS ws WHERE id = %s",
            (source_link[0],),
        )
        original_association = cursor.fetchone()
        if original_site is None or original_association is None:
            raise ReconciliationBlocked("Source metadata disappeared during reconciliation")
        cursor.execute(
            """INSERT INTO access.site_reconciliations
               (source_site_id, source_hostname, target_site_id, workspace_id,
                source_workspace_site_id, target_workspace_site_id,
                source_site_snapshot, source_workspace_site_snapshot,
                moved_diagnostics, evidence_method)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'stable_redirect')""",
            (
                source_id, alias, target_id, workspace_id,
                source_link[0], primary_link[0],
                Jsonb(original_site[0]), Jsonb(original_association[0]), count,
            ),
        )
        cursor.execute(
            """UPDATE privacy.diagnostic SET workspace_site_id = %s
               WHERE workspace_site_id = %s""",
            (primary_link[0], source_link[0]),
        )
        if cursor.rowcount != count:
            raise ReconciliationBlocked("Diagnostic count changed during reconciliation")
        cursor.execute("DELETE FROM access.workspace_sites WHERE id = %s", (source_link[0],))
        if cursor.rowcount != 1:
            raise ReconciliationBlocked("Source workspace association changed")
        cursor.execute("DELETE FROM access.sites WHERE id = %s", (source_id,))
        if cursor.rowcount != 1:
            raise ReconciliationBlocked("Source primary identity changed")
        cursor.execute(
            """INSERT INTO access.site_aliases
                 (id, site_id, hostname, verification_method)
               VALUES (gen_random_uuid(), %s, %s, 'stable_redirect')""",
            (target_id, alias),
        )
        return result
