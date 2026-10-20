"""Non-commercial, workspace-authorized requests for operator site grouping review.

Never changes site identities, diagnostic history, orders or entitlements.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from mininode_api.services import access


class ReviewQueueUnavailable(RuntimeError):
    """The additive DEV migration has not been applied."""


@dataclass(frozen=True)
class SiteGroupReview:
    id: UUID
    first_workspace_site_id: UUID
    second_workspace_site_id: UUID
    status: str


def _require_workspace(cursor, user_id: UUID, workspace_id: UUID) -> bool:
    cursor.execute(
        """SELECT 1 FROM access.workspace_members
           WHERE user_id = %s AND workspace_id = %s
             AND role IN ('owner','member')""",
        (user_id, workspace_id),
    )
    return cursor.fetchone() is not None


def _require_queue(cursor) -> None:
    cursor.execute("SELECT to_regclass('access.site_group_review_requests')")
    if cursor.fetchone()[0] is None:
        raise ReviewQueueUnavailable("Review queue not enabled")


def create_review_request(
    user_id: UUID, workspace_id: UUID, first_site: UUID, second_site: UUID
) -> SiteGroupReview | None:
    """Idempotent request for two *existing active* sites in one authorized workspace.

    An invalidated request is reopened only on an explicit new request after
    relinking; re-linking itself cannot restore a stale pending request.

    None means the user/workspace pair is unavailable; no public merging or
    automatic commercial decisions are possible through this endpoint.
    """
    if first_site == second_site:
        raise ValueError("Selecciona dos sitios distintos.")
    first, second = sorted((first_site, second_site))
    with access._connection() as connection, connection.cursor() as cursor:
        if not _require_workspace(cursor, user_id, workspace_id):
            return None
        _require_queue(cursor)
        cursor.execute(
            """SELECT id FROM access.workspace_sites
               WHERE workspace_id = %s AND id IN (%s, %s)
                 AND detached_at IS NULL
               ORDER BY id FOR UPDATE""",
            (workspace_id, first, second),
        )
        if [row[0] for row in cursor.fetchall()] != [first, second]:
            return None
        cursor.execute(
            """INSERT INTO access.site_group_review_requests
                 (id, workspace_id, first_workspace_site_id,
                  second_workspace_site_id, requested_by_user_id)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (workspace_id, first_workspace_site_id,
                            second_workspace_site_id) DO UPDATE
                 SET status = 'pending',
                     requested_by_user_id = EXCLUDED.requested_by_user_id,
                     requested_at = CURRENT_TIMESTAMP,
                     invalidated_at = NULL,
                     review_note = NULL,
                     reviewed_at = NULL
               WHERE access.site_group_review_requests.status = 'invalidated'""",
            (uuid4(), workspace_id, first, second, user_id),
        )
        cursor.execute(
            """SELECT id, first_workspace_site_id, second_workspace_site_id, status
               FROM access.site_group_review_requests
               WHERE workspace_id = %s
                 AND first_workspace_site_id = %s
                 AND second_workspace_site_id = %s""",
            (workspace_id, first, second),
        )
        result = cursor.fetchone()
        return SiteGroupReview(*result)


def list_review_requests(user_id: UUID, workspace_id: UUID) -> tuple[SiteGroupReview, ...] | None:
    """List only existing, active pairs for the caller's workspace."""
    with access._connection() as connection, connection.cursor() as cursor:
        if not _require_workspace(cursor, user_id, workspace_id):
            return None
        _require_queue(cursor)
        cursor.execute(
            """SELECT r.id, r.first_workspace_site_id, r.second_workspace_site_id, r.status
               FROM access.site_group_review_requests r
               JOIN access.workspace_sites s1
                 ON s1.id = r.first_workspace_site_id
                AND s1.workspace_id = r.workspace_id
                AND s1.detached_at IS NULL
               JOIN access.workspace_sites s2
                 ON s2.id = r.second_workspace_site_id
                AND s2.workspace_id = r.workspace_id
                AND s2.detached_at IS NULL
               WHERE r.workspace_id = %s
               ORDER BY r.requested_at DESC, r.id DESC""",
            (workspace_id,),
        )
        return tuple(SiteGroupReview(*row) for row in cursor.fetchall())
