-- Privacy Web anonymous diagnostic ownership. Apply before deploying the claim endpoint.
BEGIN;
ALTER TABLE privacy.diagnostic ADD COLUMN IF NOT EXISTS claim_token_hash TEXT;
ALTER TABLE privacy.diagnostic ADD COLUMN IF NOT EXISTS claimed_by_user_id UUID NULL;

-- Earlier application initializers may have installed an automatically named FK.
-- Consolidate to exactly one canonical constraint, including on repeated runs.
DO $migration$
DECLARE old_fk RECORD;
BEGIN
    FOR old_fk IN
        SELECT c.conname
        FROM pg_constraint c
        JOIN pg_attribute a ON a.attrelid = c.conrelid
        WHERE c.conrelid = 'privacy.diagnostic'::regclass
          AND c.contype = 'f'
          AND c.conkey = ARRAY[a.attnum]::smallint[]
          AND a.attname = 'claimed_by_user_id'
          AND c.conname <> 'privacy_diagnostic_claimed_by_user_fk'
    LOOP
        EXECUTE format('ALTER TABLE privacy.diagnostic DROP CONSTRAINT %I', old_fk.conname);
    END LOOP;
END
$migration$;

DO $migration$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'privacy.diagnostic'::regclass
          AND conname = 'privacy_diagnostic_claimed_by_user_fk'
    ) THEN
        ALTER TABLE privacy.diagnostic
            ADD CONSTRAINT privacy_diagnostic_claimed_by_user_fk
            FOREIGN KEY (claimed_by_user_id) REFERENCES access.users(id) ON DELETE SET NULL;
    END IF;
END
$migration$;
COMMIT;
