-- Privacy Web: explicit ownership proof for anonymous diagnostic claims.
-- Apply using the approved migration runner before deploying the claim endpoint.
BEGIN;
ALTER TABLE privacy.diagnostic ADD COLUMN IF NOT EXISTS claim_token_hash TEXT;
ALTER TABLE privacy.diagnostic ADD COLUMN IF NOT EXISTS claimed_by_user_id UUID NULL;
ALTER TABLE privacy.diagnostic DROP CONSTRAINT IF EXISTS privacy_diagnostic_claimed_by_user_fk;
ALTER TABLE privacy.diagnostic ADD CONSTRAINT privacy_diagnostic_claimed_by_user_fk
    FOREIGN KEY (claimed_by_user_id) REFERENCES access.users(id) ON DELETE SET NULL;
COMMIT;
