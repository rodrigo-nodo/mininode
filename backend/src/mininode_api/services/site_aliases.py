"""Read-only resolution of previously verified logical-site aliases.

No URL fetch, ownership claim, alias creation or entitlement issuance occurs here.
"""
from __future__ import annotations

from uuid import UUID

from mininode_api.services import access


def resolve_site_id(hostname: str) -> UUID | None:
    """Resolve an exact primary hostname or a verified alias to one site ID.

    Primary hosts take precedence. If legacy data contains a primary/alias
    collision, fail closed instead of selecting an unrelated logical site.
    """
    normalized, _ = access.normalize_site_url(hostname)
    with access._connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT site_id FROM (
                SELECT id AS site_id FROM access.sites WHERE hostname = %s
                UNION
                SELECT site_id FROM access.site_aliases
                WHERE hostname = %s AND verification_status = 'verified'
            ) AS matches
            """,
            (normalized, normalized),
        )
        rows = cursor.fetchall()
    if len(rows) > 1:
        raise ValueError("Hostname belongs to conflicting logical sites")
    return rows[0][0] if rows else None
