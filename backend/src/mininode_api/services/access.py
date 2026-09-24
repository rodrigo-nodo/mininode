"""Canonical persistence model for Mininode Access workspaces."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

import psycopg

INITIALIZE_SQL = """
CREATE SCHEMA IF NOT EXISTS access;

CREATE TABLE IF NOT EXISTS access.users (
    id UUID PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT access_users_email_normalized_check
        CHECK (email <> '' AND email = lower(btrim(email)))
);

CREATE TABLE IF NOT EXISTS access.workspaces (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT access_workspaces_name_not_blank_check
        CHECK (btrim(name) <> '')
);

CREATE TABLE IF NOT EXISTS access.workspace_members (
    workspace_id UUID NOT NULL REFERENCES access.workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES access.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (workspace_id, user_id),
    CONSTRAINT access_workspace_members_role_not_blank_check
        CHECK (btrim(role) <> '')
);

CREATE INDEX IF NOT EXISTS access_workspace_members_user_idx
    ON access.workspace_members (user_id, workspace_id);

CREATE TABLE IF NOT EXISTS access.companies (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES access.workspaces(id),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT access_companies_name_not_blank_check
        CHECK (btrim(name) <> '')
);

CREATE INDEX IF NOT EXISTS access_companies_workspace_idx
    ON access.companies (workspace_id, id);

CREATE TABLE IF NOT EXISTS access.sites (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL REFERENCES access.companies(id),
    hostname TEXT NOT NULL,
    canonical_url TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT access_sites_hostname_normalized_check
        CHECK (hostname <> '' AND hostname = lower(btrim(hostname))),
    CONSTRAINT access_sites_company_hostname_unique
        UNIQUE (company_id, hostname)
);

CREATE INDEX IF NOT EXISTS access_sites_company_idx
    ON access.sites (company_id, id);

CREATE TABLE IF NOT EXISTS access.entitlements (
    id UUID PRIMARY KEY,
    site_id UUID NOT NULL REFERENCES access.sites(id),
    product_code TEXT NOT NULL,
    active_from TIMESTAMPTZ NOT NULL,
    active_until TIMESTAMPTZ NULL,
    status TEXT NOT NULL,
    source TEXT NOT NULL,
    source_id TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT access_entitlements_product_code_not_blank_check
        CHECK (btrim(product_code) <> ''),
    CONSTRAINT access_entitlements_status_not_blank_check
        CHECK (btrim(status) <> ''),
    CONSTRAINT access_entitlements_source_not_blank_check
        CHECK (btrim(source) <> ''),
    CONSTRAINT access_entitlements_window_check
        CHECK (active_until IS NULL OR active_until > active_from)
);

CREATE INDEX IF NOT EXISTS access_entitlements_site_product_idx
    ON access.entitlements (site_id, product_code, active_from DESC);
"""


def _database_url() -> str:
    value = os.getenv("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL is not configured")
    return value


@contextmanager
def _connection() -> Iterator[psycopg.Connection]:
    with psycopg.connect(_database_url()) as connection:
        yield connection


def initialize_database() -> None:
    """Create the canonical Access schema idempotently."""
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(INITIALIZE_SQL)
