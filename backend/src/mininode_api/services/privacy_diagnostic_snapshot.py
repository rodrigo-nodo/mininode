"""Immutable persistence for completed Privacy Web diagnostics."""

from __future__ import annotations

import os
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
    purchase_expires_at TIMESTAMPTZ NOT NULL
);
"""


class PrivacyDiagnosticSnapshotNotFoundError(Exception):
    """No diagnostic snapshot matches the supplied identifier."""


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


def create_diagnostic_snapshot(diagnostic: Mapping) -> StoredPrivacyDiagnostic:
    """Persist the completed result unchanged, without inspecting the site again."""
    score = diagnostic.get("score")
    site_url = diagnostic.get("site_url")
    if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 100:
        raise ValueError("Diagnostic score must be between 0 and 100")
    if not isinstance(site_url, str) or not site_url:
        raise ValueError("Diagnostic site_url is required")

    diagnostic_id = uuid4()
    snapshot = dict(diagnostic)
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO privacy.diagnostic (
                id, site_url, diagnostic_snapshot, score, purchase_expires_at
            ) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP + INTERVAL '24 hours')
            RETURNING id, site_url, diagnostic_snapshot, score, created_at,
                      purchase_expires_at
            """,
            (diagnostic_id, site_url, Jsonb(snapshot), score),
        )
        return StoredPrivacyDiagnostic(*cursor.fetchone())


def get_diagnostic_snapshot(diagnostic_id: UUID) -> StoredPrivacyDiagnostic:
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, site_url, diagnostic_snapshot, score, created_at,
                   purchase_expires_at
            FROM privacy.diagnostic WHERE id = %s
            """,
            (diagnostic_id,),
        )
        row = cursor.fetchone()
    if row is None:
        raise PrivacyDiagnosticSnapshotNotFoundError("Diagnostic not found")
    return StoredPrivacyDiagnostic(*row)


def require_purchasable(
    diagnostic: StoredPrivacyDiagnostic, *, now: datetime | None = None
) -> StoredPrivacyDiagnostic:
    current_time = now or datetime.now(timezone.utc)
    if current_time > diagnostic.purchase_expires_at:
        raise PrivacyDiagnosticPurchaseExpiredError("Diagnostic purchase window expired")
    return diagnostic
