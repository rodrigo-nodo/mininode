"""Administrative Privacy Web grants. All mutations lock the workspace-site row."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from mininode_api.services import billing

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS access.entitlement_admin_events (
 id UUID PRIMARY KEY,
 entitlement_id UUID NOT NULL REFERENCES access.entitlements(id),
 operator_user_id UUID NOT NULL REFERENCES access.users(id),
 action TEXT NOT NULL CHECK (action IN ('granted','revoked')),
 reason TEXT NOT NULL CHECK (length(btrim(reason)) >= 3),
 created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS entitlement_admin_events_entitlement_idx
 ON access.entitlement_admin_events(entitlement_id, created_at);
"""

class GrantConflict(ValueError):
    pass

def initialize_database():
    with billing._connect() as conn:
        conn.execute(SCHEMA_SQL)

def search_sites(hostname: str):
    hostname = hostname.strip().lower()
    if len(hostname) < 3 or len(hostname) > 253:
        raise ValueError("Indica un dominio de al menos 3 caracteres.")
    with billing._connect() as conn:
        return conn.execute("""
            SELECT ws.id, w.name, s.hostname
            FROM access.workspace_sites ws
            JOIN access.workspaces w ON w.id=ws.workspace_id
            JOIN access.sites s ON s.id=ws.site_id
            WHERE ws.detached_at IS NULL AND s.hostname ILIKE %s
            ORDER BY s.hostname, w.name LIMIT 50
        """, ('%' + hostname.replace('%', '\\%').replace('_', '\\_') + '%',)).fetchall()

def list_grants(workspace_site_id: UUID):
    with billing._connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ws.id FROM access.workspace_sites ws
                WHERE ws.id=%s AND ws.detached_at IS NULL
            """, (workspace_site_id,))
            if cur.fetchone() is None:
                raise LookupError("Sitio no encontrado.")
            cur.execute("""
                SELECT e.id, e.active_from, e.active_until, e.status, e.source,
                       (SELECT ev.reason FROM access.entitlement_admin_events ev
                        WHERE ev.entitlement_id=e.id ORDER BY ev.created_at DESC LIMIT 1)
                FROM access.entitlements e
                WHERE e.workspace_site_id=%s AND e.product_code=%s
                ORDER BY e.active_from DESC
            """, (workspace_site_id, billing.PRODUCT))
            return cur.fetchall()

def grant(workspace_site_id: UUID, operator_id: UUID, reason: str, days: int = 30):
    reason = reason.strip()
    if not 1 <= days <= 365 or len(reason) < 3 or len(reason) > 1000:
        raise ValueError("Duración entre 1 y 365 días y motivo entre 3 y 1000 caracteres.")
    with billing._connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT detached_at FROM access.workspace_sites WHERE id=%s FOR UPDATE", (workspace_site_id,))
            site = cur.fetchone()
            if site is None or site[0] is not None:
                raise LookupError("Sitio no encontrado o desvinculado.")
            now = datetime.now(timezone.utc)
            cur.execute("""
                SELECT active_from, active_until FROM access.entitlements
                WHERE workspace_site_id=%s AND product_code=%s AND status='active'
                  AND (active_until IS NULL OR active_until > %s)
                ORDER BY active_from
            """, (workspace_site_id, billing.PRODUCT, now))
            periods = cur.fetchall()
            if any(end is None for _, end in periods):
                raise GrantConflict("Existe un acceso sin vencimiento.")
            future = sum(start > now for start, _ in periods)
            if future:
                raise GrantConflict("Ya existe un período futuro reservado.")
            start = max([now] + [end for _, end in periods])
            end = start + timedelta(days=days)
            eid = uuid4()
            cur.execute("""
                INSERT INTO access.entitlements
                (id,workspace_site_id,product_code,active_from,active_until,status,source,source_id)
                VALUES (%s,%s,%s,%s,%s,'active','internal_grant',%s)
            """, (eid, workspace_site_id, billing.PRODUCT, start, end, str(eid)))
            cur.execute("""
                INSERT INTO access.entitlement_admin_events
                (id,entitlement_id,operator_user_id,action,reason)
                VALUES (%s,%s,%s,'granted',%s)
            """, (uuid4(), eid, operator_id, reason))
            return eid

def revoke(entitlement_id: UUID, operator_id: UUID, reason: str):
    reason = reason.strip()
    if len(reason) < 3 or len(reason) > 1000:
        raise ValueError("Motivo entre 3 y 1000 caracteres.")
    with billing._connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT workspace_site_id FROM access.entitlements WHERE id=%s AND source='internal_grant'", (entitlement_id,))
            row = cur.fetchone()
            if row is None:
                raise LookupError("Cortesía no encontrada.")
            cur.execute("SELECT id FROM access.workspace_sites WHERE id=%s FOR UPDATE", (row[0],))
            cur.execute("""
                SELECT status, active_until FROM access.entitlements
                WHERE id=%s FOR UPDATE
            """, (entitlement_id,))
            status, until = cur.fetchone()
            if status != 'active' or (until is not None and until <= datetime.now(timezone.utc)):
                raise GrantConflict("La cortesía ya no está vigente.")
            cur.execute("UPDATE access.entitlements SET status='revoked',updated_at=CURRENT_TIMESTAMP WHERE id=%s", (entitlement_id,))
            cur.execute("""
                INSERT INTO access.entitlement_admin_events
                (id,entitlement_id,operator_user_id,action,reason)
                VALUES (%s,%s,%s,'revoked',%s)
            """, (uuid4(), entitlement_id, operator_id, reason))
