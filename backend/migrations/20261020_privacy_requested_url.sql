-- Additive origin-only provenance for Privacy Web diagnostics.
-- No historical rows, scores, snapshots or site associations are changed.
BEGIN;

ALTER TABLE privacy.diagnostic
    ADD COLUMN IF NOT EXISTS requested_url TEXT NULL;

COMMIT;
