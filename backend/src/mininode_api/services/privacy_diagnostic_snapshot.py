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
    claimed_by_user_id UUID NULL
);
ALTER TABLE privacy.diagnostic ADD COLUMN IF NOT EXISTS claim_token_hash TEXT;
ALTER TABLE privacy.diagnostic ADD COLUMN IF NOT EXISTS claimed_by_user_id UUID NULL;
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
            WHERE ws.workspace_id = %s AND ws.detached_at IS NULL
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


def claim_anonymous_diagnostic(diagnostic_id: UUID, claim_token: str, user_id: UUID, workspace_id: UUID) -> UUID:
    """Atomically attach an anonymous snapshot to a selected, authorized workspace."""
    if not isinstance(claim_token, str) or not 32 <= len(claim_token) <= 512:
        raise PrivacyDiagnosticClaimRejectedError("Invalid claim proof")
    token_hash = hashlib.sha256(claim_token.encode()).hexdigest()
    with _connection() as connection, connection.cursor() as cursor:
        # One transaction and one cursor for proof, membership, site and diagnostic.
        # Serialize competing claims without locking the diagnostic row across other connections.
        cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (str(diagnostic_id),))
        cursor.execute(
            """SELECT site_url, claim_token_hash, workspace_site_id, claimed_by_user_id
               FROM privacy.diagnostic WHERE id = %s""",
            (diagnostic_id,),
        )
        row = cursor.fetchone()
        if row is None or row[1] is None or not hmac.compare_digest(token_hash, row[1]):
            raise PrivacyDiagnosticClaimRejectedError("Invalid claim proof")
        site_url, _, existing_site, claimed_by = row
        cursor.execute(
            """SELECT 1 FROM access.workspace_members
               WHERE workspace_id = %s AND user_id = %s AND role IN ('owner', 'member')""",
            (workspace_id, user_id),
        )
        if cursor.fetchone() is None:
            raise PrivacyDiagnosticClaimRejectedError("Workspace unavailable")
        if existing_site is not None:
            cursor.execute(
                "SELECT 1 FROM access.workspace_sites WHERE id = %s AND workspace_id = %s",
                (existing_site, workspace_id),
            )
            if claimed_by != user_id or cursor.fetchone() is None:
                raise PrivacyDiagnosticClaimRejectedError("Diagnostic already claimed")
            return existing_site
        # Free account saving is independent of the commercial purchase window.
        # Proof remains single-claim and workspace-authorized even after 24 hours.
        hostname, canonical_url = _normalize_claim_url(site_url)
        from mininode_api.services.site_aliases import resolve_existing_site
        existing = resolve_existing_site(cursor, hostname)
        if existing is None:
            from mininode_api.services.site_aliases import register_verified_www_alias
            if register_verified_www_alias(cursor, hostname):
                existing = resolve_existing_site(cursor, hostname)
        if existing is not None:
            site_id = existing[0]
        else:
            cursor.execute(
                """INSERT INTO access.sites (id, hostname, canonical_url)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (hostname) DO UPDATE SET hostname = EXCLUDED.hostname
                   RETURNING id""",
                (uuid4(), hostname, canonical_url),
            )
            site_id = cursor.fetchone()[0]
        cursor.execute(
            """INSERT INTO access.workspace_sites (id, workspace_id, site_id)
               VALUES (%s, %s, %s)
               ON CONFLICT (workspace_id, site_id) DO UPDATE SET site_id = EXCLUDED.site_id, detached_at = NULL
               RETURNING id""",
            (uuid4(), workspace_id, site_id),
        )
        workspace_site_id = cursor.fetchone()[0]
        cursor.execute(
            """UPDATE privacy.diagnostic SET workspace_site_id = %s, claimed_by_user_id = %s
               WHERE id = %s AND workspace_site_id IS NULL AND claimed_by_user_id IS NULL
               RETURNING workspace_site_id""",
            (workspace_site_id, user_id, diagnostic_id),
        )
        if cursor.fetchone() is None:
            raise PrivacyDiagnosticClaimRejectedError("Diagnostic claim conflict")
        return workspace_site_id


def _normalize_claim_url(site_url: str) -> tuple[str, str]:
    # Reuse Access URL normalization, without opening an Access DB connection.
    from mininode_api.services.access import normalize_site_url
    return normalize_site_url(site_url)
