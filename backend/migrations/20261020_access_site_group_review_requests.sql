-- Non-commercial review queue for two active sites in one workspace.
-- The database enforces matching workspace, and detachment invalidates pending
-- requests in the same transaction, regardless of the caller.
BEGIN;

-- Required for composite foreign keys. IDs remain globally unique.
CREATE UNIQUE INDEX IF NOT EXISTS access_workspace_sites_id_workspace_idx
    ON access.workspace_sites (id, workspace_id);

CREATE TABLE IF NOT EXISTS access.site_group_review_requests (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES access.workspaces(id) ON DELETE CASCADE,
    first_workspace_site_id UUID NOT NULL,
    second_workspace_site_id UUID NOT NULL,
    requested_by_user_id UUID NOT NULL REFERENCES access.users(id) ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'invalidated')),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMPTZ NULL,
    invalidated_at TIMESTAMPTZ NULL,
    review_note TEXT NULL,
    CONSTRAINT site_group_review_first_workspace_fk
        FOREIGN KEY (first_workspace_site_id, workspace_id)
        REFERENCES access.workspace_sites(id, workspace_id) ON DELETE RESTRICT,
    CONSTRAINT site_group_review_second_workspace_fk
        FOREIGN KEY (second_workspace_site_id, workspace_id)
        REFERENCES access.workspace_sites(id, workspace_id) ON DELETE RESTRICT,
    CONSTRAINT site_group_review_distinct_sites
        CHECK (first_workspace_site_id < second_workspace_site_id),
    CONSTRAINT site_group_review_once_per_workspace_pair
        UNIQUE (workspace_id, first_workspace_site_id, second_workspace_site_id)
);

CREATE INDEX IF NOT EXISTS site_group_review_workspace_status_idx
    ON access.site_group_review_requests(workspace_id, status);

CREATE OR REPLACE FUNCTION access.invalidate_site_group_reviews_on_detach()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    UPDATE access.site_group_review_requests
       SET status = 'invalidated', invalidated_at = CURRENT_TIMESTAMP
     WHERE status = 'pending'
       AND (first_workspace_site_id = NEW.id
            OR second_workspace_site_id = NEW.id);
    RETURN NEW;
END;
$$;

-- Idempotent for disposable PostgreSQL CI databases.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
         WHERE tgname = 'site_group_review_on_detach'
           AND tgrelid = 'access.workspace_sites'::regclass
           AND NOT tgisinternal
    ) THEN
        CREATE TRIGGER site_group_review_on_detach
        AFTER UPDATE OF detached_at ON access.workspace_sites
        FOR EACH ROW
        WHEN (OLD.detached_at IS NULL AND NEW.detached_at IS NOT NULL)
        EXECUTE FUNCTION access.invalidate_site_group_reviews_on_detach();
    END IF;
END;
$$;

COMMIT;
