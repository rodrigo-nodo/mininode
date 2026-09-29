-- A3.2: link authenticated Privacy Web diagnostic snapshots to workspace sites.
BEGIN;

ALTER TABLE privacy.diagnostic
    ADD COLUMN IF NOT EXISTS workspace_site_id UUID NULL;

ALTER TABLE privacy.diagnostic
    DROP CONSTRAINT IF EXISTS privacy_diagnostic_workspace_site_fk;
ALTER TABLE privacy.diagnostic
    ADD CONSTRAINT privacy_diagnostic_workspace_site_fk
    FOREIGN KEY (workspace_site_id)
    REFERENCES access.workspace_sites(id)
    ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS privacy_diagnostic_workspace_site_created_idx
    ON privacy.diagnostic (workspace_site_id, created_at DESC)
    WHERE workspace_site_id IS NOT NULL;

COMMIT;
