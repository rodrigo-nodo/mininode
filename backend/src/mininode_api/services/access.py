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
    hostname: str


@dataclass(frozen=True)
class CompanyContext:
    id: UUID
    name: str
    sites: tuple[SiteContext, ...]


@dataclass(frozen=True)
class WorkspaceContext:
    id: UUID
    name: str
    role: str
    companies: tuple[CompanyContext, ...]


@dataclass(frozen=True)
class AuthorizedSite:
    site_id: UUID
    company_id: UUID
    workspace_id: UUID
    role: str


def list_authorized_context(user_id: UUID) -> tuple[WorkspaceContext, ...]:
    """Return only workspace/company/site hierarchy authorized for this user."""

    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                w.id,
                w.name,
                wm.role,
                c.id,
                c.name,
                s.id,
                s.hostname
            FROM access.workspace_members AS wm
            JOIN access.workspaces AS w
              ON w.id = wm.workspace_id
            LEFT JOIN access.companies AS c
              ON c.workspace_id = w.id
            LEFT JOIN access.sites AS s
              ON s.company_id = c.id
            WHERE wm.user_id = %s
              AND wm.role IN (%s, %s)
            ORDER BY
                lower(w.name),
                w.id,
                lower(c.name) NULLS FIRST,
                c.id NULLS FIRST,
                s.hostname NULLS FIRST,
                s.id NULLS FIRST
            """,
            (user_id, ROLE_OWNER, ROLE_MEMBER),
        )
        rows = cursor.fetchall()

    workspace_builders: dict[UUID, dict] = {}
    for (
        workspace_id,
        workspace_name,
        role,
        company_id,
        company_name,
        site_id,
        hostname,
    ) in rows:
        workspace = workspace_builders.setdefault(
            workspace_id,
            {
                "name": workspace_name,
                "role": role,
                "companies": {},
            },
        )

        if company_id is None:
            continue

        company = workspace["companies"].setdefault(
            company_id,
            {
                "name": company_name,
                "sites": [],
            },
        )
        if site_id is not None:
            company["sites"].append(SiteContext(id=site_id, hostname=hostname))

    return tuple(
        WorkspaceContext(
            id=workspace_id,
            name=workspace["name"],
            role=workspace["role"],
            companies=tuple(
                CompanyContext(
                    id=company_id,
                    name=company["name"],
                    sites=tuple(company["sites"]),
                )
                for company_id, company in workspace["companies"].items()
            ),
        )
        for workspace_id, workspace in workspace_builders.items()
    )


def get_authorized_site(user_id: UUID, site_id: UUID) -> AuthorizedSite | None:
    """Resolve a site only when the user belongs to its workspace."""

    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                s.id,
                c.id,
                w.id,
                wm.role
            FROM access.sites AS s
            JOIN access.companies AS c
              ON c.id = s.company_id
            JOIN access.workspaces AS w
              ON w.id = c.workspace_id
            JOIN access.workspace_members AS wm
              ON wm.workspace_id = w.id
             AND wm.user_id = %s
            WHERE s.id = %s
              AND wm.role IN (%s, %s)
            LIMIT 1
            """,
            (user_id, site_id, ROLE_OWNER, ROLE_MEMBER),
        )
        row = cursor.fetchone()

    if row is None:
        return None

    return AuthorizedSite(
        site_id=row[0],
        company_id=row[1],
        workspace_id=row[2],
        role=row[3],
    )
