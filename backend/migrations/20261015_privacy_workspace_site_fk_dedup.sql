-- Reconcile duplicate workspace-site foreign keys without changing their semantics.
-- Abort if the expected canonical relationship or duplicate differs.
DO $migration$
DECLARE
    canonical_oid oid;
    redundant_oid oid;
BEGIN
    SELECT oid INTO canonical_oid
      FROM pg_constraint
     WHERE conrelid = 'privacy.diagnostic'::regclass
       AND conname = 'privacy_diagnostic_workspace_site_fk'
       AND contype = 'f';

    IF canonical_oid IS NULL THEN
        RAISE EXCEPTION 'Canonical workspace-site FK missing; manual review required';
    END IF;

    SELECT oid INTO redundant_oid
      FROM pg_constraint
     WHERE conrelid = 'privacy.diagnostic'::regclass
       AND conname = 'diagnostic_workspace_site_id_fkey'
       AND contype = 'f';

    IF redundant_oid IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1
              FROM pg_constraint canonical
              JOIN pg_constraint redundant ON redundant.oid = redundant_oid
             WHERE canonical.oid = canonical_oid
               AND canonical.conkey = redundant.conkey
               AND canonical.confrelid = redundant.confrelid
               AND canonical.confkey = redundant.confkey
               AND canonical.confupdtype = redundant.confupdtype
               AND canonical.confdeltype = redundant.confdeltype
               AND canonical.confmatchtype = redundant.confmatchtype
               AND canonical.condeferrable = redundant.condeferrable
               AND canonical.condeferred = redundant.condeferred
               AND canonical.convalidated = redundant.convalidated
        ) THEN
            RAISE EXCEPTION 'Workspace-site FK definitions differ; manual review required';
        END IF;
        ALTER TABLE privacy.diagnostic DROP CONSTRAINT diagnostic_workspace_site_id_fkey;
    END IF;
END
$migration$;
