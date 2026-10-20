"""Operator-only site grouping: verified evidence, transaction-safe reconciliation, audit.

A status of approved means the source was actually grouped. No entitlement or
payment can ever be transferred by this module.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import UUID

from psycopg.types.json import Jsonb

from mininode_api.services import access
from mininode_api.web_inspector.fetcher import WebFetcher

logger = logging.getLogger(__name__)


class OperatorConflict(ValueError):
    """The requested action cannot be performed safely."""


def is_operator(email: str) -> bool:
    """Server-side allowlist on an identity verified by Clerk/Cloudflare Access."""
    allowed = {item.strip().lower() for item in
               os.getenv("MININODE_REVIEW_OPERATOR_EMAILS", "").split(",") if item.strip()}
    return bool(allowed and email.strip().lower() in allowed)


def list_operator_reviews() -> list[dict]:
    with access._connection() as db, db.cursor() as cur:
        cur.execute("""
            SELECT r.id, r.workspace_id, w.name, r.status, r.requested_at,
                   r.reviewed_at, r.review_note,
                   CASE WHEN a.id=merges.source_site_id THEN merges.source_hostname ELSE a.hostname END,
                   CASE WHEN b.id=merges.source_site_id THEN merges.source_hostname ELSE b.hostname END,
                   r.first_workspace_site_id, r.second_workspace_site_id
            FROM access.site_group_review_requests r
            LEFT JOIN access.site_group_operator_merges merges ON merges.review_id = r.id
            JOIN access.workspaces w ON w.id = r.workspace_id
            JOIN access.workspace_sites x ON x.id = r.first_workspace_site_id
            JOIN access.workspace_sites y ON y.id = r.second_workspace_site_id
            JOIN access.sites a ON a.id = x.site_id
            JOIN access.sites b ON b.id = y.site_id
            ORDER BY (r.status = 'pending') DESC, r.requested_at DESC LIMIT 100
        """)
        return [dict(id=row[0], workspace_id=row[1], workspace=row[2],
                     status=row[3], requested_at=row[4], reviewed_at=row[5],
                     note=row[6], first_hostname=row[7], second_hostname=row[8],
                     first_workspace_site_id=row[9], second_workspace_site_id=row[10])
                for row in cur.fetchall()]


def notify_pending(review_id: UUID) -> bool:
    """Best-effort Resend notification, no message if already sent or unconfigured.

    Requests remain persisted when mail is unavailable. A subsequent submission
    retries undelivered mail; no provider credential is persisted or logged.
    """
    key = os.getenv("RESEND_API_KEY", "")
    destination = os.getenv("MININODE_CONTACT_EMAIL", "").strip()
    sender = os.getenv("MININODE_REVIEW_FROM_EMAIL", "").strip()
    if not key or not destination or not sender:
        logger.warning("Review notification not configured")
        return False
    with access._connection() as db, db.cursor() as cur:
        cur.execute("""
            SELECT r.id, r.status, a.hostname, b.hostname, r.notification_sent_at
            FROM access.site_group_review_requests r
            JOIN access.workspace_sites wa ON wa.id=r.first_workspace_site_id
            JOIN access.workspace_sites wb ON wb.id=r.second_workspace_site_id
            JOIN access.sites a ON a.id=wa.site_id
            JOIN access.sites b ON b.id=wb.site_id WHERE r.id=%s
        """, (review_id,))
        row = cur.fetchone()
    if not row or row[1] != "pending" or row[4] is not None:
        return False
    payload = json.dumps({
        "from": sender, "to": [destination],
        "subject": "[Mininode] Nueva solicitud de agrupación",
        "text": (f"Solicitaron revisar la agrupación de {row[2]} y {row[3]}.\n"
                 "Revisa la solicitud desde el panel privado:\n"
                 + os.getenv("MININODE_REVIEW_PANEL_URL", "https://dev.mininode.io/operator/site-reviews/") + "\n"),
    }).encode("utf-8")
    request = Request("https://api.resend.com/emails", data=payload, method="POST",
                      headers={"Authorization": "Bearer " + key,
                               "Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=8) as response:
            if not 200 <= response.status < 300:
                return False
    except Exception:
        logger.warning("Review notification delivery failed (credentials omitted)")
        return False
    with access._connection() as db:
        db.execute("""
            UPDATE access.site_group_review_requests
               SET notification_sent_at = CURRENT_TIMESTAMP
             WHERE id = %s AND status = 'pending' AND notification_sent_at IS NULL
        """, (review_id,))
    return True


def _stable_redirect(host_a: str, host_b: str) -> tuple[str, str] | None:
    """Return (source,destination) only for an actual stable public HTTPS redirect.

    Two independent public GET observations, pinned DNS and guarded redirects
    per hop. Operator approval never relies on site similarity or user claims.
    """
    possible = []
    try:
        with WebFetcher() as fetcher:
            for source, target in ((host_a, host_b), (host_b, host_a)):
                pages = [fetcher._fetch_page(
                    "https://" + source + "/", source, deadline=None,
                    allow_public_cross_domain_redirects=True,
                ) for _ in range(2)]
                if all(
                    page.error is None and page.status_code == 200
                    and page.redirect_count > 0
                    and urlsplit(page.final_url or "").scheme == "https"
                    and urlsplit(page.final_url or "").hostname == target
                    for page in pages
                ) and pages[0].final_url == pages[1].final_url:
                    possible.append((source, target))
    except Exception:
        logger.warning("Operator redirect verification failed")
        return None
    return possible[0] if len(possible) == 1 else None


def decide(review_id: UUID, reviewer: UUID, decision: str, note: str) -> dict:
    if decision not in ("approved", "rejected"):
        raise ValueError("Decisión inválida.")
    note = note.strip()
    if not 3 <= len(note) <= 1000:
        raise ValueError("Indica un motivo entre 3 y 1000 caracteres.")
    # Fetch candidate outside the write transaction; network evidence is refreshed
    # before any merge and candidate records are rechecked under row locks.
    with access._connection() as db, db.cursor() as cur:
        cur.execute("""
            SELECT r.status, a.hostname, b.hostname
            FROM access.site_group_review_requests r
            JOIN access.workspace_sites x ON x.id=r.first_workspace_site_id
            JOIN access.workspace_sites y ON y.id=r.second_workspace_site_id
            JOIN access.sites a ON a.id=x.site_id
            JOIN access.sites b ON b.id=y.site_id
            WHERE r.id=%s
        """, (review_id,))
        candidate = cur.fetchone()
    if candidate is None:
        raise LookupError("Solicitud no encontrada.")
    if candidate[0] != "pending":
        raise OperatorConflict("La solicitud ya no está pendiente.")
    direction = None
    if decision == "approved":
        direction = _stable_redirect(candidate[1], candidate[2])
        if direction is None:
            raise OperatorConflict("No hay evidencia pública HTTPS estable para agrupar estos sitios.")

    with access._connection() as db, db.cursor() as cur:
        cur.execute("""
            SELECT workspace_id, first_workspace_site_id, second_workspace_site_id, status
            FROM access.site_group_review_requests WHERE id=%s FOR UPDATE
        """, (review_id,))
        row = cur.fetchone()
        if row is None or row[3] != "pending":
            raise OperatorConflict("La solicitud cambió durante la revisión.")
        workspace, first, second, _ = row
        if decision == "rejected":
            cur.execute("""
                UPDATE access.site_group_review_requests
                SET status='rejected', reviewed_at=CURRENT_TIMESTAMP,
                    reviewed_by_user_id=%s, review_note=%s WHERE id=%s
            """, (reviewer, note, review_id))
            return {"id": review_id, "status": "rejected", "moved_diagnostics": 0}

        source_hostname, target_hostname = direction
        # Reuse the existing apex/www advisory lock when applicable.
        for hostname in (source_hostname, target_hostname):
            access_hostname = hostname.removeprefix("www.")
            if access_hostname.count(".") == 1:
                cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                            ("site-alias-www:" + access_hostname,))
        cur.execute("""
            SELECT ws.id, ws.site_id, ws.workspace_id, ws.company_id, ws.detached_at,
                   s.hostname
            FROM access.workspace_sites ws JOIN access.sites s ON s.id=ws.site_id
            WHERE ws.id IN (%s,%s) ORDER BY ws.id FOR UPDATE OF ws,s
        """, (first, second))
        rows = cur.fetchall()
        if len(rows) != 2 or {item[5] for item in rows} != {source_hostname, target_hostname}:
            raise OperatorConflict("Las identidades de los sitios cambiaron.")
        if any(item[2] != workspace or item[3] is not None or item[4] is not None for item in rows):
            raise OperatorConflict("Los sitios deben estar activos y sin asociación a empresas.")
        sites = {item[5]: item for item in rows}
        source, target = sites[source_hostname], sites[target_hostname]
        if source[1] == target[1]:
            raise OperatorConflict("Los sitios ya comparten identidad.")
        cur.execute("""
            SELECT count(*) FROM access.workspace_sites
            WHERE site_id IN (%s,%s)
        """, (source[1], target[1]))
        if cur.fetchone()[0] != 2:
            raise OperatorConflict("Otro workspace sigue alguno de los sitios.")
        cur.execute("SELECT to_regclass('access.site_aliases')")
        if cur.fetchone()[0] is None:
            raise OperatorConflict("La tabla de aliases no está disponible.")
        cur.execute("""
            SELECT count(*) FROM access.site_aliases
            WHERE site_id=%s OR hostname=%s
        """, (source[1], source_hostname))
        if cur.fetchone()[0]:
            raise OperatorConflict("Existen aliases que impiden agrupar el origen.")
        cur.execute("""
            SELECT EXISTS(
                SELECT 1 FROM access.entitlements WHERE workspace_site_id IN (%s,%s)
            ) OR EXISTS(
                SELECT 1 FROM billing.orders WHERE workspace_site_id IN (%s,%s)
            )
        """, (source[0], target[0], source[0], target[0]))
        if cur.fetchone()[0]:
            raise OperatorConflict("Existen entitlements u órdenes: requiere revisión comercial independiente.")
        cur.execute("SELECT to_regclass('privacy.correction_plan_order')")
        if cur.fetchone()[0] is not None:
            cur.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM privacy.correction_plan_order o
                    JOIN privacy.diagnostic d ON d.id=o.diagnostic_id
                    WHERE d.workspace_site_id IN (%s,%s)
                       OR lower(split_part(split_part(o.site_url, '://', 2), '/', 1))
                           IN (%s,%s)
                )
            """, (source[0], target[0], source_hostname, target_hostname))
            if cur.fetchone()[0]:
                raise OperatorConflict("Hay planes u órdenes previas: requiere revisión comercial.")
        cur.execute("""
            SELECT count(*) FROM access.site_group_operator_merges
            WHERE source_site_id IN (%s,%s) OR target_site_id=%s
        """, (source[1], target[1], source[1]))
        if cur.fetchone()[0]:
            raise OperatorConflict("Las identidades participan de una agrupación anterior.")
        cur.execute("""
            SELECT EXISTS(
                SELECT 1 FROM access.site_reconciliations
                WHERE target_site_id IN (%s,%s)
                   OR target_workspace_site_id IN (%s,%s)
            ) OR EXISTS(
                SELECT 1 FROM access.site_group_review_requests
                WHERE id != %s AND status = 'pending'
                  AND (first_workspace_site_id IN (%s,%s)
                       OR second_workspace_site_id IN (%s,%s))
            )
        """, (source[1], target[1], source[0], target[0],
              review_id, source[0], target[0], source[0], target[0]))
        if cur.fetchone()[0]:
            raise OperatorConflict("Existen conciliaciones o solicitudes relacionadas pendientes.")
        cur.execute("SELECT to_jsonb(s) FROM access.sites s WHERE id=%s", (source[1],))
        source_snapshot = cur.fetchone()[0]
        cur.execute("SELECT to_jsonb(ws) FROM access.workspace_sites ws WHERE id=%s", (source[0],))
        link_snapshot = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM privacy.diagnostic WHERE workspace_site_id=%s", (source[0],))
        count = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO access.site_group_operator_merges
            (review_id,workspace_id,source_site_id,target_site_id,
             source_hostname,target_hostname,source_workspace_site_id,target_workspace_site_id,
             source_site_snapshot,source_workspace_site_snapshot,moved_diagnostics,evidence_method)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'stable_https_home_redirect')
        """, (review_id, workspace, source[1], target[1], source_hostname,
              target_hostname, source[0], target[0], Jsonb(source_snapshot),
              Jsonb(link_snapshot), count))
        # Keep structural IDs/tombstones: review queue foreign keys remain valid,
        # and full original rows are recorded in the immutable audit above.
        cur.execute("""
            UPDATE privacy.diagnostic SET workspace_site_id=%s
            WHERE workspace_site_id=%s
        """, (target[0], source[0]))
        if cur.rowcount != count:
            raise OperatorConflict("El historial cambió durante la agrupación.")
        cur.execute("""
            UPDATE access.site_group_review_requests
            SET status='approved', reviewed_at=CURRENT_TIMESTAMP,
                reviewed_by_user_id=%s, review_note=%s WHERE id=%s
        """, (reviewer, note, review_id))
        cur.execute("""
            UPDATE access.workspace_sites
            SET detached_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE id=%s
        """, (source[0],))
        cur.execute("""
            UPDATE access.sites
            SET hostname=%s, canonical_url=NULL, updated_at=CURRENT_TIMESTAMP WHERE id=%s
        """, ("retired-" + source[1].hex + ".invalid", source[1]))
        cur.execute("""
            INSERT INTO access.site_aliases(id,site_id,hostname,verification_method)
            VALUES (gen_random_uuid(),%s,%s,'stable_redirect')
        """, (target[1], source_hostname))
        return {"id": review_id, "status": "approved", "moved_diagnostics": count}
