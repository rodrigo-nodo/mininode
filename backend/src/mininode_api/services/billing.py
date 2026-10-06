"""Provider-independent billing core. No public payment confirmation endpoint."""
from __future__ import annotations

import calendar
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

import psycopg

PRODUCT = "privacy_web"
PRICE_CLP = 9900

SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS billing;
CREATE TABLE IF NOT EXISTS billing.orders (
 id UUID PRIMARY KEY,
 workspace_site_id UUID NOT NULL REFERENCES access.workspace_sites(id),
 diagnostic_id UUID NOT NULL REFERENCES privacy.diagnostic(id),
 product_code TEXT NOT NULL,
 amount INTEGER NOT NULL CHECK (amount > 0),
 currency TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','paid','failed','cancelled')),
 provider TEXT NULL,
 provider_order_id TEXT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
 paid_at TIMESTAMPTZ NULL,
 CONSTRAINT billing_paid_timestamp CHECK ((status = 'paid') = (paid_at IS NOT NULL)),
 UNIQUE (provider, provider_order_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS billing_payment_entitlement_source_idx
 ON access.entitlements (source, source_id)
 WHERE source = 'payment' AND source_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS billing_orders_site_idx ON billing.orders(workspace_site_id, created_at DESC);
"""

@dataclass(frozen=True)
class Order:
    id: UUID
    workspace_site_id: UUID
    diagnostic_id: UUID
    product_code: str
    amount: int
    currency: str
    status: str
    provider: str | None
    provider_order_id: str | None
    created_at: datetime
    paid_at: datetime | None

ORDER_FIELDS = "id, workspace_site_id, diagnostic_id, product_code, amount, currency, status, provider, provider_order_id, created_at, paid_at"

def _connect():
    return psycopg.connect(os.environ["DATABASE_URL"])

def initialize_database():
    # Access and Privacy diagnostic tables must be initialized first.
    with _connect() as conn:
        conn.execute(SCHEMA_SQL)

def create_order(user_id: UUID, workspace_site_id: UUID, diagnostic_id: UUID) -> Order:
    """Server resolves the price and verifies site membership and diagnostic recency."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1 FROM access.workspace_sites ws
                JOIN access.workspace_members wm ON wm.workspace_id = ws.workspace_id
                JOIN privacy.diagnostic d ON d.workspace_site_id = ws.id
                WHERE ws.id = %s AND wm.user_id = %s AND wm.role IN ('owner','member')
                  AND d.id = %s AND d.purchase_expires_at >= CURRENT_TIMESTAMP
            """, (workspace_site_id, user_id, diagnostic_id))
            if cur.fetchone() is None:
                raise ValueError("Site or eligible diagnostic not found")
            cur.execute(f"""
                INSERT INTO billing.orders
                (id, workspace_site_id, diagnostic_id, product_code, amount, currency)
                VALUES (%s,%s,%s,%s,%s,%s) RETURNING {ORDER_FIELDS}
            """, (uuid4(), workspace_site_id, diagnostic_id, PRODUCT, PRICE_CLP, "CLP"))
            return Order(*cur.fetchone())

def get_order(user_id: UUID, order_id: UUID) -> Order | None:
    with _connect() as conn:
        row = conn.execute(f"""
            SELECT {', '.join('o.' + f.strip() for f in ORDER_FIELDS.split(','))}
            FROM billing.orders o
            JOIN access.workspace_sites ws ON ws.id = o.workspace_site_id
            JOIN access.workspace_members wm ON wm.workspace_id = ws.workspace_id
            WHERE o.id = %s AND wm.user_id = %s AND wm.role IN ('owner','member')
        """, (order_id, user_id)).fetchone()
    return Order(*row) if row else None

def get_order_for_provider(order_id: UUID) -> Order | None:
    """Internal provider lookup. Never expose this without user authorization."""
    with _connect() as conn:
        row = conn.execute(f"SELECT {ORDER_FIELDS} FROM billing.orders WHERE id = %s", (order_id,)).fetchone()
    return Order(*row) if row else None

def attach_provider_order(order_id: UUID, *, provider: str, provider_order_id: str) -> None:
    """Link a pending Billing order to exactly one provider order."""
    if not provider or not provider_order_id:
        raise ValueError("Provider and provider order id are required")
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status, provider, provider_order_id FROM billing.orders WHERE id=%s FOR UPDATE", (order_id,))
            row = cur.fetchone()
            if row is None:
                raise ValueError("Order not found")
            status, current_provider, current_reference = row
            if status != "pending":
                raise ValueError("Only pending orders can be linked")
            if current_provider is not None:
                if (current_provider, current_reference) == (provider, provider_order_id):
                    return
                raise ValueError("Order is already linked to another provider order")
            cur.execute(
                "UPDATE billing.orders SET provider=%s, provider_order_id=%s WHERE id=%s",
                (provider, provider_order_id, order_id),
            )

def add_calendar_month(start: datetime) -> datetime:
    year = start.year + (start.month == 12)
    month = start.month % 12 + 1
    return start.replace(year=year, month=month, day=min(start.day, calendar.monthrange(year, month)[1]))

def payment_confirmed(order_id: UUID, *, provider: str, provider_order_id: str,
                      verified_paid_at: datetime) -> UUID:
    """Trusted adapter only: verification of provider signatures/payment belongs to adapter.

    Lock the workspace-site to serialize renewals from different orders, then
    lock the order. Duplicate callbacks return the existing entitlement.
    """
    if not provider or not provider_order_id or verified_paid_at.tzinfo is None:
        raise ValueError("Verified provider, reference and timezone-aware timestamp required")
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT workspace_site_id FROM billing.orders WHERE id = %s", (order_id,))
            row = cur.fetchone()
            if row is None:
                raise ValueError("Order not found")
            site_id = row[0]
            cur.execute("SELECT id FROM access.workspace_sites WHERE id = %s FOR UPDATE", (site_id,))
            if cur.fetchone() is None:
                raise ValueError("Site not found")
            cur.execute("""
                SELECT o.status, o.provider, o.provider_order_id, o.product_code,
                       d.purchase_expires_at
                FROM billing.orders o
                JOIN privacy.diagnostic d ON d.id = o.diagnostic_id
                WHERE o.id = %s
                FOR UPDATE OF o
            """, (order_id,))
            status, previous_provider, previous_reference, product, purchase_expires_at = cur.fetchone()
            if status == 'paid':
                if (previous_provider, previous_reference) != (provider, provider_order_id):
                    raise ValueError("Payment reference mismatch")
                cur.execute("SELECT id FROM access.entitlements WHERE source = 'payment' AND source_id = %s", (str(order_id),))
                existing = cur.fetchone()
                if existing is None:
                    raise RuntimeError("Paid order without entitlement")
                return existing[0]
            if status != 'pending':
                raise ValueError("Order cannot be paid in current state")
            if previous_provider is not None and (previous_provider, previous_reference) != (provider, provider_order_id):
                raise ValueError("Payment reference mismatch")
            if verified_paid_at > purchase_expires_at:
                raise ValueError("Diagnostic purchase window expired")
            cur.execute("""
                SELECT max(active_until) FROM access.entitlements
                WHERE workspace_site_id = %s AND product_code = %s AND status = 'active'
                  AND active_until IS NOT NULL AND active_until > %s
            """, (site_id, product, verified_paid_at))
            latest = cur.fetchone()[0]
            if latest is not None and latest > add_calendar_month(verified_paid_at):
                raise ValueError("Privacy Web already has one future period paid")
            start = max(verified_paid_at, latest) if latest else verified_paid_at
            entitlement_id = uuid4()
            cur.execute("""
                INSERT INTO access.entitlements
                  (id,workspace_site_id,product_code,active_from,active_until,status,source,source_id)
                VALUES (%s,%s,%s,%s,%s,'active','payment',%s)
            """, (entitlement_id, site_id, product, start, add_calendar_month(start), str(order_id)))
            cur.execute("""
                UPDATE billing.orders SET status='paid', paid_at=%s, provider=%s, provider_order_id=%s
                WHERE id=%s
            """, (verified_paid_at, provider, provider_order_id, order_id))
            return entitlement_id

def current_entitlement(user_id: UUID, workspace_site_id: UUID, product_code: str = PRODUCT):
    with _connect() as conn:
        return conn.execute("""
            SELECT e.id, e.active_from, e.active_until, e.source FROM access.entitlements e
            JOIN access.workspace_sites ws ON ws.id = e.workspace_site_id
            JOIN access.workspace_members wm ON wm.workspace_id = ws.workspace_id
            WHERE ws.id=%s AND wm.user_id=%s AND wm.role IN ('owner','member')
              AND e.product_code=%s AND e.status='active'
              AND e.active_from <= CURRENT_TIMESTAMP
              AND (e.active_until IS NULL OR e.active_until > CURRENT_TIMESTAMP)
            ORDER BY e.active_until DESC NULLS FIRST LIMIT 1
        """, (workspace_site_id, user_id, product_code)).fetchone()
