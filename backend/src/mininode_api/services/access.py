"""Canonical persistence model for Mininode Access workspaces."""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator
from uuid import UUID, uuid4

import psycopg

ROLE_OWNER = "owner"
ROLE_MEMBER = "member"
WORKSPACE_ROLES = frozenset({ROLE_OWNER, ROLE_MEMBER})

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
        CHECK (btrim(name) <> ''),
    CONSTRAINT access_companies_id_workspace_unique
        UNIQUE (id, workspace_id)
);

CREATE INDEX IF NOT EXISTS access_companies_workspace_idx
    ON access.companies (workspace_id, id);

CREATE TABLE IF NOT EXISTS access.sites (
    id UUID PRIMARY KEY,
    hostname TEXT NOT NULL,
    canonical_url TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT access_sites_hostname_normalized_check
        CHECK (hostname <> '' AND hostname = lower(btrim(hostname))),
    CONSTRAINT access_sites_hostname_unique
        UNIQUE (hostname)
);

CREATE TABLE IF NOT EXISTS access.workspace_sites (
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

CREATE INDEX IF NOT EXISTS access_workspace_sites_workspace_idx
    ON access.workspace_sites (workspace_id, id);
CREATE INDEX IF NOT EXISTS access_workspace_sites_site_idx
    ON access.workspace_sites (site_id, workspace_id);

CREATE TABLE IF NOT EXISTS access.entitlements (
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
    CONSTRAINT access_entitlements_product_code_not_blank_check
        CHECK (btrim(product_code) <> ''),
    CONSTRAINT access_entitlements_status_not_blank_check
        CHECK (btrim(status) <> ''),
    CONSTRAINT access_entitlements_source_not_blank_check
        CHECK (btrim(source) <> ''),
    CONSTRAINT access_entitlements_window_check
        CHECK (active_until IS NULL OR active_until > active_from)
);

CREATE INDEX IF NOT EXISTS access_entitlements_workspace_site_product_idx
    ON access.entitlements (workspace_site_id, product_code, active_from DESC);
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


@dataclass(frozen=True)
class StoredUser:
    id: UUID
    email: str


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_or_create_user(email: str) -> StoredUser:
    normalized = normalize_email(email)
    if not normalized:
        raise ValueError("email is required")

    user_id = uuid4()
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO access.users (id, email)
            VALUES (%s, %s)
            ON CONFLICT (email) DO UPDATE
            SET email = EXCLUDED.email
            RETURNING id, email
            """,
            (user_id, normalized),
        )
        row = cursor.fetchone()

    return StoredUser(id=row[0], email=row[1])


@dataclass(frozen=True)
class SiteContext:
    id: UUID
    site_id: UUID
    hostname: str
    company_id: UUID | None
    company_name: str | None


@dataclass(frozen=True)
class WorkspaceContext:
    id: UUID
    name: str
    role: str
    sites: tuple[SiteContext, ...]


@dataclass(frozen=True)
class AuthorizedSite:
    workspace_site_id: UUID
    site_id: UUID
    company_id: UUID | None
    workspace_id: UUID
    role: str


def list_authorized_context(user_id: UUID) -> tuple[WorkspaceContext, ...]:
    """Return only workspace-site relationships authorized for this user."""

    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT w.id, w.name, wm.role, ws.id, s.id, s.hostname, c.id, c.name
            FROM access.workspace_members AS wm
            JOIN access.workspaces AS w ON w.id = wm.workspace_id
            LEFT JOIN access.workspace_sites AS ws ON ws.workspace_id = w.id
            LEFT JOIN access.sites AS s ON s.id = ws.site_id
            LEFT JOIN access.companies AS c ON c.id = ws.company_id
            WHERE wm.user_id = %s
              AND wm.role IN (%s, %s)
            ORDER BY lower(w.name), w.id, s.hostname NULLS FIRST, ws.id NULLS FIRST
            """,
            (user_id, ROLE_OWNER, ROLE_MEMBER),
        )
        rows = cursor.fetchall()

    workspace_builders: dict[UUID, dict] = {}
    for workspace_id, workspace_name, role, workspace_site_id, site_id, hostname, company_id, company_name in rows:
        workspace = workspace_builders.setdefault(
            workspace_id,
            {"name": workspace_name, "role": role, "sites": []},
        )
        if workspace_site_id is not None:
            workspace["sites"].append(
                SiteContext(
                    id=workspace_site_id,
                    site_id=site_id,
                    hostname=hostname,
                    company_id=company_id,
                    company_name=company_name,
                )
            )

    return tuple(
        WorkspaceContext(
            id=workspace_id,
            name=workspace["name"],
            role=workspace["role"],
            sites=tuple(workspace["sites"]),
        )
        for workspace_id, workspace in workspace_builders.items()
    )

def get_authorized_site(user_id: UUID, workspace_site_id: UUID) -> AuthorizedSite | None:
    """Resolve a workspace-site relationship only for a member of that workspace."""

    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT ws.id, s.id, ws.company_id, w.id, wm.role
            FROM access.workspace_sites AS ws
            JOIN access.sites AS s ON s.id = ws.site_id
            JOIN access.workspaces AS w ON w.id = ws.workspace_id
            JOIN access.workspace_members AS wm
              ON wm.workspace_id = w.id AND wm.user_id = %s
            WHERE ws.id = %s
              AND wm.role IN (%s, %s)
            LIMIT 1
            """,
            (user_id, workspace_site_id, ROLE_OWNER, ROLE_MEMBER),
        )
        row = cursor.fetchone()

    if row is None:
        return None

    return AuthorizedSite(
        workspace_site_id=row[0],
        site_id=row[1],
        company_id=row[2],
        workspace_id=row[3],
        role=row[4],
    )
