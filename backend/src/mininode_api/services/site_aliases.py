"""Resolution of previously verified logical-site aliases.

No network request, ownership claim, alias creation, or entitlement issuance.
"""
from __future__ import annotations

from uuid import UUID, uuid4

from mininode_api.services import access


def resolve_existing_site(cursor, hostname: str) -> tuple[UUID, str] | None:
    """Return (site_id, primary hostname), failing closed on conflicting identities.

    The additive alias migration is enabled separately per environment. Before
    activation, preserve the original hostname-only behavior.
    """
    cursor.execute("SELECT to_regclass('access.site_aliases')")
    aliases_ready = cursor.fetchone()[0] is not None
    if aliases_ready:
        cursor.execute(
            """
            SELECT id, hostname FROM access.sites WHERE hostname = %s
            UNION
            SELECT s.id, s.hostname
            FROM access.site_aliases a
            JOIN access.sites s ON s.id = a.site_id
            WHERE a.hostname = %s AND a.verification_status = 'verified'
            """,
            (hostname, hostname),
        )
    else:
        cursor.execute(
            "SELECT id, hostname FROM access.sites WHERE hostname = %s",
            (hostname,),
        )
    rows = cursor.fetchall()
    if len(rows) > 1:
        raise ValueError("Hostname belongs to conflicting logical sites")
    return rows[0] if rows else None


def resolve_site_id(hostname: str) -> UUID | None:
    """Resolve a primary hostname or previously verified alias to a site ID."""
    normalized, _ = access.normalize_site_url(hostname)
    with access._connection() as connection, connection.cursor() as cursor:
        site = resolve_existing_site(cursor, normalized)
    return site[0] if site else None


def register_verified_www_alias(cursor, hostname: str, *, verifier=None) -> bool:
    """Attach one unused www/apex hostname to an existing primary site.

    Caller must have checked workspace authorization. Caller transaction owns
    the insert. Never merges two existing site records or moves an alias.
    Returns true only if a new alias was inserted.
    """
    from mininode_api.services.site_equivalence import inspect_www_equivalence

    apex = hostname.removeprefix("www.")
    if apex.count(".") != 1 or hostname.startswith("www.www."):
        return False
    counterpart = apex if hostname.startswith("www.") else f"www.{hostname}"
    cursor.execute("SELECT to_regclass('access.site_aliases')")
    if cursor.fetchone()[0] is None:
        return False

    # One advisory lock per pair across both registration/creation entrypoints.
    # Do not permit two concurrent inserts to choose opposite primary identities.
    cursor.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
        ("site-alias-www:" + apex,),
    )
    if resolve_existing_site(cursor, hostname) is not None:
        return False
    other = resolve_existing_site(cursor, counterpart)
    if other is None:
        return False

    proof = (verifier or inspect_www_equivalence)(hostname)
    if not (proof.equivalent and proof.requested_hostname == hostname
            and proof.counterpart_hostname == counterpart):
        return False

    # Primary hostname collision? Never overwrite. If another transaction
    # created the requested hostname, this INSERT must not reassign it.
    cursor.execute("SELECT id FROM access.sites WHERE hostname = %s", (hostname,))
    if cursor.fetchone() is not None:
        return False
    cursor.execute(
        """INSERT INTO access.site_aliases
               (id, site_id, hostname, verification_method)
           VALUES (%s, %s, %s, 'stable_redirect')
           ON CONFLICT (hostname) DO NOTHING
           RETURNING site_id""",
        (uuid4(), other[0], hostname),
    )
    result = cursor.fetchone()
    return result is not None and result[0] == other[0]
