-- Additive logical unlink. Preserve all FK references and diagnostic history.
BEGIN;
ALTER TABLE access.workspace_sites ADD COLUMN IF NOT EXISTS detached_at TIMESTAMPTZ NULL;
CREATE INDEX IF NOT EXISTS access_workspace_sites_active_idx
 ON access.workspace_sites (workspace_id, id) WHERE detached_at IS NULL;
COMMIT;
