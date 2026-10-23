-- Additive logical-site aliases. No data rewrite, no automatic claims or purchases.
BEGIN;

CREATE TABLE IF NOT EXISTS access.site_aliases (
    id UUID PRIMARY KEY,
    site_id UUID NOT NULL REFERENCES access.sites(id) ON DELETE RESTRICT,
    hostname TEXT NOT NULL UNIQUE,
    verification_status TEXT NOT NULL DEFAULT 'verified'
        CHECK (verification_status = 'verified'),
    verification_method TEXT NOT NULL
        CHECK (verification_method IN ('stable_redirect', 'reviewed_evidence')),
    verified_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT access_site_aliases_hostname_normalized_check
        CHECK (hostname <> '' AND hostname = lower(btrim(hostname))),
    CONSTRAINT access_site_aliases_method_not_blank_check
        CHECK (btrim(verification_method) <> '')
);
CREATE INDEX IF NOT EXISTS access_site_aliases_site_idx
    ON access.site_aliases (site_id);

COMMIT;
