"""Persistent, capability-token access to immutable Privacy correction plans."""

from __future__ import annotations

import hashlib
import os
import secrets
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, Mapping
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb

TOKEN_BYTES = 32

INITIALIZE_SQL = """
CREATE SCHEMA IF NOT EXISTS privacy;

CREATE TABLE IF NOT EXISTS privacy.correction_plan (
    id UUID PRIMARY KEY,
    site_url TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    plan_snapshot JSONB NOT NULL,
    plan_version TEXT NOT NULL,
    actions_version TEXT NOT NULL,
    initial_score INTEGER NOT NULL CHECK (initial_score BETWEEN 0 AND 100),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'revoked')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class CorrectionPlanNotFoundError(Exception):
    """No active plan matches the supplied capability token."""


@dataclass(frozen=True)
class CreatedCorrectionPlan:
    id: UUID
    access_token: str


def _database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    return database_url


@contextmanager
def _connection() -> Iterator[psycopg.Connection]:
    with psycopg.connect(_database_url()) as connection:
        yield connection


def _token_hash(access_token: str) -> str:
    return hashlib.sha256(access_token.encode("utf-8")).hexdigest()


def initialize_database() -> None:
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(INITIALIZE_SQL)


def _validate_plan(plan: Mapping) -> None:
    required = {"version", "actions_version", "initial_score", "item_count", "items"}
    missing = required.difference(plan)
    if missing:
        raise ValueError("Correction plan is missing required fields")
    score = plan["initial_score"]
    if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 100:
        raise ValueError("Correction plan initial_score must be between 0 and 100")


def create_correction_plan(*, site_url: str, plan: Mapping) -> CreatedCorrectionPlan:
    """Persist an already-built plan snapshot and return its secret once."""
    _validate_plan(plan)
    plan_id = uuid4()
    access_token = secrets.token_urlsafe(TOKEN_BYTES)
    token_hash = _token_hash(access_token)
    snapshot = dict(plan)

    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO privacy.correction_plan (
                id, site_url, token_hash, plan_snapshot, plan_version,
                actions_version, initial_score, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'active')
            """,
            (
                plan_id,
                site_url,
                token_hash,
                Jsonb(snapshot),
                plan["version"],
                plan["actions_version"],
                plan["initial_score"],
            ),
        )
    return CreatedCorrectionPlan(id=plan_id, access_token=access_token)


def get_correction_plan(access_token: str) -> dict:
    """Return the stored snapshot for an exact, active capability token."""
    if not access_token:
        raise CorrectionPlanNotFoundError("Plan not found")
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, site_url, created_at, plan_snapshot
            FROM privacy.correction_plan
            WHERE token_hash = %s AND status = 'active'
            """,
            (_token_hash(access_token),),
        )
        row = cursor.fetchone()
    if row is None:
        raise CorrectionPlanNotFoundError("Plan not found")
    plan_id, site_url, created_at, snapshot = row
    return {
        "id": plan_id,
        "site_url": site_url,
        "created_at": created_at,
        "plan": snapshot,
    }
