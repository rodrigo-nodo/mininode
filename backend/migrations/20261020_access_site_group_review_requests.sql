-- Non-commercial operator review queue for existing workspace site identities.
-- Requests never merge sites, alter diagnostics or confer entitlements.
BEGIN;

CREATE TABLE IF NOT EXISTS access.site_group_review_requests (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES access.workspaces(id) ON DELETE CASCADE,
    first_workspace_site_id UUID NOT NULL REFERENCES access.workspace_sites(id) ON DELETE RESTRICT,
    second_workspace_site_id UUID NOT NULL REFERENCES access.workspace_sites(id) ON DELETE RESTRICT,
    requested_by_user_id UUID NOT NULL REFERENCES access.users(id) ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected')),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMPTZ NULL,
    review_note TEXT NULL,
    CONSTRAINT site_group_review_distinct_sites CHECK (first_workspace_site_id < second_workspace_site_id),
    CONSTRAINT site_group_review_once_per_workspace_pair
        UNIQUE (workspace_id, first_workspace_site_id, second_workspace_site_id)
);

CREATE INDEX IF NOT EXISTS site_group_review_workspace_status_idx
    ON access.site_group_review_requests(workspace_id, status);

COMMIT;
