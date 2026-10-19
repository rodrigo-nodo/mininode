"""Resolution of previously verified logical-site aliases.

No network request, ownership claim, alias creation, or entitlement issuance.
"""
from __future__ import annotations

from uuid import UUID

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
