-- PW-03B: additive, entitlement-scoped plans and repeated reviews.
-- Applied only through the approved migrations runner; no runtime DDL.
BEGIN;
CREATE SCHEMA IF NOT EXISTS privacy;
CREATE TABLE IF NOT EXISTS privacy.entitled_plan (
  id UUID PRIMARY KEY,
  workspace_site_id UUID NOT NULL REFERENCES access.workspace_sites(id),
  entitlement_id UUID NOT NULL UNIQUE REFERENCES access.entitlements(id),
  original_diagnostic_id UUID NOT NULL REFERENCES privacy.diagnostic(id),
  plan_snapshot JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS privacy_entitled_plan_site_idx
  ON privacy.entitled_plan(workspace_site_id, created_at DESC);
CREATE TABLE IF NOT EXISTS privacy.entitled_plan_check (
  id UUID PRIMARY KEY,
  entitled_plan_id UUID NOT NULL REFERENCES privacy.entitled_plan(id),
  check_diagnostic_id UUID NOT NULL REFERENCES privacy.diagnostic(id),
  result_snapshot JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS privacy_entitled_plan_check_latest_idx
  ON privacy.entitled_plan_check(entitled_plan_id, created_at DESC);
COMMIT;
