-- PW-02: audited operator courtesy events; additive, compatible with existing data.
BEGIN;
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
COMMIT;
