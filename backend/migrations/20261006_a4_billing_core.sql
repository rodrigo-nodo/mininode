-- A4 Billing Core: provider-independent commercial orders.
BEGIN;
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
CREATE INDEX IF NOT EXISTS billing_orders_site_idx
    ON billing.orders(workspace_site_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS billing_payment_entitlement_source_idx
    ON access.entitlements(source, source_id)
    WHERE source = 'payment' AND source_id IS NOT NULL;
COMMIT;
