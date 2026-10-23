-- Additive audit trail for a manually approved, same-workspace apex/www reconciliation.
-- This migration never merges or deletes any site or diagnostic.
BEGIN;

CREATE TABLE IF NOT EXISTS access.site_reconciliations (
    source_site_id UUID PRIMARY KEY,
    source_hostname TEXT NOT NULL UNIQUE,
    target_site_id UUID NOT NULL REFERENCES access.sites(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES access.workspaces(id) ON DELETE RESTRICT,
    source_workspace_site_id UUID NOT NULL,
    target_workspace_site_id UUID NOT NULL REFERENCES access.workspace_sites(id) ON DELETE RESTRICT,
    -- Complete original records, including timestamps and future columns.
    -- Captured from locked rows BEFORE their structural deletion.
    source_site_snapshot JSONB NOT NULL
        CHECK (jsonb_typeof(source_site_snapshot) = 'object'),
    source_workspace_site_snapshot JSONB NOT NULL
        CHECK (jsonb_typeof(source_workspace_site_snapshot) = 'object'),
    moved_diagnostics INTEGER NOT NULL CHECK (moved_diagnostics >= 0),
    evidence_method TEXT NOT NULL CHECK (evidence_method = 'stable_redirect'),
    reconciled_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMIT;
