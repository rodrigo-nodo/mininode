-- Operator decisions and immutable evidence for conservatively grouped sites.
-- No data is reconciled by this migration.
BEGIN;
ALTER TABLE access.site_group_review_requests
  ADD COLUMN IF NOT EXISTS reviewed_by_user_id UUID NULL REFERENCES access.users(id),
  ADD COLUMN IF NOT EXISTS notification_sent_at TIMESTAMPTZ NULL;

CREATE TABLE IF NOT EXISTS access.site_group_operator_merges (
  review_id UUID PRIMARY KEY REFERENCES access.site_group_review_requests(id) ON DELETE RESTRICT,
  workspace_id UUID NOT NULL REFERENCES access.workspaces(id) ON DELETE RESTRICT,
  source_site_id UUID NOT NULL UNIQUE,
  target_site_id UUID NOT NULL REFERENCES access.sites(id) ON DELETE RESTRICT,
  source_hostname TEXT NOT NULL UNIQUE,
  target_hostname TEXT NOT NULL,
  source_workspace_site_id UUID NOT NULL REFERENCES access.workspace_sites(id) ON DELETE RESTRICT,
  target_workspace_site_id UUID NOT NULL REFERENCES access.workspace_sites(id) ON DELETE RESTRICT,
  source_site_snapshot JSONB NOT NULL,
  source_workspace_site_snapshot JSONB NOT NULL,
  moved_diagnostics INTEGER NOT NULL CHECK (moved_diagnostics >= 0),
  evidence_method TEXT NOT NULL CHECK (evidence_method = 'stable_https_home_redirect'),
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMIT;
