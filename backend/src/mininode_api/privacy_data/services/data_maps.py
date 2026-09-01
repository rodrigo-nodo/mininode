"""Persistence and capability-token access for Privacy Data maps."""

from __future__ import annotations

import hashlib
import os
import secrets
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb

from mininode_api.privacy_data.catalog import CATALOG_VERSION

TOKEN_BYTES = 32
INITIALIZE_SQL = """
CREATE SCHEMA IF NOT EXISTS privacy_data;

CREATE TABLE IF NOT EXISTS privacy_data.data_maps (
    id UUID PRIMARY KEY,
    public_token_hash TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('draft', 'completed')),
    industry_profile TEXT NULL,
    business_size TEXT NULL,
    catalog_version TEXT NOT NULL,
    engine_version TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    recommendations_generated_at TIMESTAMPTZ NULL,
    metadata JSONB
);
"""


class DataMapNotFoundError(Exception):
    pass


class DataMapExpiredError(Exception):
    pass


@dataclass(frozen=True)
class StoredDataMap:
    id: UUID
    status: str
    industry_profile: str | None
    business_size: str | None
    catalog_version: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class CreatedDataMap:
    token: str
    data_map: StoredDataMap


def _database_url() -> str:
    value = os.getenv("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL is not configured")
    return value


@contextmanager
def _connection() -> Iterator[psycopg.Connection]:
    with psycopg.connect(_database_url()) as connection:
        yield connection


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def initialize_database() -> None:
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(INITIALIZE_SQL)


def create_data_map() -> CreatedDataMap:
    map_id = uuid4()
    token = secrets.token_urlsafe(TOKEN_BYTES)
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO privacy_data.data_maps (
                id, public_token_hash, status, catalog_version, created_at,
                updated_at, expires_at, metadata
            ) VALUES (
                %s, %s, 'draft', %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP + INTERVAL '7 days', %s
            )
            RETURNING id, status, industry_profile, business_size,
                      catalog_version, created_at, updated_at, expires_at
            """,
            (map_id, hash_token(token), CATALOG_VERSION, Jsonb({})),
        )
        row = cursor.fetchone()
    return CreatedDataMap(token=token, data_map=StoredDataMap(*row))


def get_data_map(token: str, *, now: datetime | None = None) -> StoredDataMap:
    if not token:
        raise DataMapNotFoundError("Data map not found")
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, status, industry_profile, business_size, catalog_version,
                   created_at, updated_at, expires_at
            FROM privacy_data.data_maps WHERE public_token_hash = %s
            """,
            (hash_token(token),),
        )
        row = cursor.fetchone()
    if row is None:
        raise DataMapNotFoundError("Data map not found")
    data_map = StoredDataMap(*row)
    if data_map.expires_at <= (now or datetime.now(timezone.utc)):
        raise DataMapExpiredError("Data map has expired")
    return data_map
