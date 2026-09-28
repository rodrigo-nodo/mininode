-- A2.1 destructive migration: public site + private workspace-site relationship.
-- Approved for the pre-customer Access schema. Preserves users, workspaces,
-- workspace_members and companies. Existing site/entitlement rows are intentionally discarded.
BEGIN;

DROP TABLE IF EXISTS access.entitlements;
DROP TABLE IF EXISTS access.workspace_sites;
DROP TABLE IF EXISTS access.sites;

ALTER TABLE access.companies
    DROP CONSTRAINT IF EXISTS access_companies_id_workspace_unique;
ALTER TABLE access.companies
    ADD CONSTRAINT access_companies_id_workspace_unique
    UNIQUE (id, workspace_id);

CREATE TABLE access.sites (
    id UUID PRIMARY KEY,
    hostname TEXT NOT NULL UNIQUE,
    canonical_url TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT access_sites_hostname_normalized_check
        CHECK (hostname <> '' AND hostname = lower(btrim(hostname)))
);

CREATE TABLE access.workspace_sites (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES access.workspaces(id) ON DELETE CASCADE,
    site_id UUID NOT NULL REFERENCES access.sites(id) ON DELETE CASCADE,
    company_id UUID NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT access_workspace_sites_workspace_site_unique
        UNIQUE (workspace_id, site_id),
    CONSTRAINT access_workspace_sites_company_same_workspace_fk
        FOREIGN KEY (company_id, workspace_id)
        REFERENCES access.companies(id, workspace_id)
        ON DELETE SET NULL (company_id)
);

CREATE INDEX access_workspace_sites_workspace_idx
    ON access.workspace_sites (workspace_id, id);
CREATE INDEX access_workspace_sites_site_idx
    ON access.workspace_sites (site_id, workspace_id);

CREATE TABLE access.entitlements (
    id UUID PRIMARY KEY,
    workspace_site_id UUID NOT NULL REFERENCES access.workspace_sites(id) ON DELETE CASCADE,
    product_code TEXT NOT NULL,
    active_from TIMESTAMPTZ NOT NULL,
    active_until TIMESTAMPTZ NULL,
    status TEXT NOT NULL,
    source TEXT NOT NULL,
    source_id TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT access_entitlements_product_code_not_blank_check CHECK (btrim(product_code) <> ''),
    CONSTRAINT access_entitlements_status_not_blank_check CHECK (btrim(status) <> ''),
    CONSTRAINT access_entitlements_source_not_blank_check CHECK (btrim(source) <> ''),
    CONSTRAINT access_entitlements_window_check CHECK (active_until IS NULL OR active_until > active_from)
);

CREATE INDEX access_entitlements_workspace_site_product_idx
    ON access.entitlements (workspace_site_id, product_code, active_from DESC);

COMMIT;
