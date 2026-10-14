"""Immutable persistence for completed Privacy Web diagnostics."""

from __future__ import annotations

import os
import hashlib
import hmac
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator, Mapping
from uuid import UUID, uuid4

from mininode_api.services import access

import psycopg
from psycopg.types.json import Jsonb

INITIALIZE_SQL = """
CREATE SCHEMA IF NOT EXISTS privacy;

CREATE TABLE IF NOT EXISTS privacy.diagnostic (
    id UUID PRIMARY KEY,
    site_url TEXT NOT NULL,
    diagnostic_snapshot JSONB NOT NULL,
    score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    purchase_expires_at TIMESTAMPTZ NOT NULL,
    workspace_site_id UUID NULL REFERENCES access.workspace_sites(id) ON DELETE SET NULL,
    claim_token_hash TEXT NULL,
    claimed_by_user_id UUID NULL REFERENCES access.users(id) ON DELETE SET NULL
);
ALTER TABLE privacy.diagnostic ADD COLUMN IF NOT EXISTS claim_token_hash TEXT;
ALTER TABLE privacy.diagnostic ADD COLUMN IF NOT EXISTS claimed_by_user_id UUID NULL REFERENCES access.users(id) ON DELETE SET NULL;
"""


class PrivacyDiagnosticSnapshotNotFoundError(Exception):
    """No diagnostic snapshot matches the supplied identifier."""


class PrivacyDiagnosticClaimRejectedError(Exception):
    """Invalid claim proof or diagnostic owned by another workspace."""


class PrivacyDiagnosticPurchaseExpiredError(Exception):
    """The diagnostic is outside its backend-controlled purchase window."""


@dataclass(frozen=True)
class StoredPrivacyDiagnostic:
    id: UUID
    site_url: str
    diagnostic_snapshot: dict
    score: int
    created_at: datetime
    purchase_expires_at: datetime
    workspace_site_id: UUID | None = None


def _database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    return database_url


@contextmanager
def _connection() -> Iterator[psycopg.Connection]:
    with psycopg.connect(_database_url()) as connection:
        yield connection


def initialize_database() -> None:
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(INITIALIZE_SQL)


def create_diagnostic_snapshot(diagnostic: Mapping, *, workspace_site_id: UUID | None = None, claim_token: str | None = None) -> StoredPrivacyDiagnostic:
    """Persist the completed result unchanged, without inspecting the site again."""
    score = diagnostic.get("score")
    site_url = diagnostic.get("site_url")
    if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 100:
        raise ValueError("Diagnostic score must be between 0 and 100")
    if not isinstance(site_url, str) or not site_url:
        raise ValueError("Diagnostic site_url is required")

    if claim_token is not None and (workspace_site_id is not None or len(claim_token) < 32):
        raise ValueError("Claim token is only for anonymous diagnostics")
    claim_hash = hashlib.sha256(claim_token.encode()).hexdigest() if claim_token else None
    diagnostic_id = uuid4()
    snapshot = dict(diagnostic)
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO privacy.diagnostic (
                id, site_url, diagnostic_snapshot, score, purchase_expires_at, workspace_site_id, claim_token_hash
            ) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP + INTERVAL '24 hours', %s, %s)
            RETURNING id, site_url, diagnostic_snapshot, score, created_at,
                      purchase_expires_at, workspace_site_id
            """,
            (diagnostic_id, site_url, Jsonb(snapshot), score, workspace_site_id, claim_hash),
        )
        return StoredPrivacyDiagnostic(*cursor.fetchone())


def get_diagnostic_snapshot(diagnostic_id: UUID) -> StoredPrivacyDiagnostic:
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, site_url, diagnostic_snapshot, score, created_at,
                   purchase_expires_at, workspace_site_id
            FROM privacy.diagnostic WHERE id = %s
            """,
            (diagnostic_id,),
        )
        row = cursor.fetchone()
    if row is None:
        raise PrivacyDiagnosticSnapshotNotFoundError("Diagnostic not found")
    return StoredPrivacyDiagnostic(*row)


def get_latest_for_workspace_site(workspace_site_id: UUID) -> StoredPrivacyDiagnostic:
    """Return the newest stored review for one private workspace-site relation."""
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, site_url, diagnostic_snapshot, score, created_at,
                   purchase_expires_at, workspace_site_id
            FROM privacy.diagnostic
            WHERE workspace_site_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (workspace_site_id,),
        )
        row = cursor.fetchone()
    if row is None:
        raise PrivacyDiagnosticSnapshotNotFoundError("Diagnostic not found")
    return StoredPrivacyDiagnostic(*row)


def list_latest_for_workspace(workspace_id: UUID) -> tuple[StoredPrivacyDiagnostic, ...]:
    """Return at most one newest stored review per site in the workspace."""
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT DISTINCT ON (d.workspace_site_id)
                   d.id, d.site_url, d.diagnostic_snapshot, d.score, d.created_at,
                   d.purchase_expires_at, d.workspace_site_id
            FROM privacy.diagnostic AS d
            JOIN access.workspace_sites AS ws ON ws.id = d.workspace_site_id
            WHERE ws.workspace_id = %s
            ORDER BY d.workspace_site_id, d.created_at DESC, d.id DESC
            """,
            (workspace_id,),
        )
        rows = cursor.fetchall()
    return tuple(StoredPrivacyDiagnostic(*row) for row in rows)


def require_purchasable(
    diagnostic: StoredPrivacyDiagnostic, *, now: datetime | None = None
) -> StoredPrivacyDiagnostic:
    current_time = now or datetime.now(timezone.utc)
    if current_time > diagnostic.purchase_expires_at:
        raise PrivacyDiagnosticPurchaseExpiredError("Diagnostic purchase window expired")
    return diagnostic


def claim_anonymous_diagnostic(diagnostic_id: UUID, claim_token: str, user_id: UUID) -> UUID:
    """Claim a fresh anonymous review; its row lock serializes competing claims."""
    if not isinstance(claim_token, str) or not 32 <= len(claim_token) <= 512:
        raise PrivacyDiagnosticClaimRejectedError("Invalid claim proof")
    token_hash = hashlib.sha256(claim_token.encode()).hexdigest()
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """SELECT site_url, claim_token_hash, workspace_site_id, claimed_by_user_id,
                      purchase_expires_at >= CURRENT_TIMESTAMP
               FROM privacy.diagnostic WHERE id = %s FOR UPDATE""",
            (diagnostic_id,),
        )
        row = cursor.fetchone()
        if row is None or row[1] is None or not hmac.compare_digest(token_hash, row[1]):
            raise PrivacyDiagnosticClaimRejectedError("Invalid claim proof")
        site_url, _, existing_site, claimed_by, eligible = row
        if existing_site is not None:
            authorized = access.get_authorized_site(user_id, existing_site)
            if claimed_by != user_id or authorized is None:
                raise PrivacyDiagnosticClaimRejectedError("Diagnostic already claimed")
            return existing_site
        if not eligible:
            raise PrivacyDiagnosticPurchaseExpiredError("Diagnostic purchase window expired")
        workspace = access.get_or_create_personal_workspace(user_id)
        linked_site = access.follow_site(user_id, workspace.id, site_url)
        if linked_site is None:
            raise PrivacyDiagnosticClaimRejectedError("Workspace unavailable")
        cursor.execute(
            """UPDATE privacy.diagnostic SET workspace_site_id = %s, claimed_by_user_id = %s
               WHERE id = %s AND workspace_site_id IS NULL""",
            (linked_site.id, user_id, diagnostic_id),
        )
        return linked_site.id
