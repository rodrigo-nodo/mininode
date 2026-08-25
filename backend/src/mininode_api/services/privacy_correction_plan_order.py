"""Minimal commercial orders for the Privacy correction plan."""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator
from uuid import UUID, uuid4

import psycopg

from mininode_api.services.privacy_diagnostic import validate_public_url_format
from mininode_api.web_inspector.fetcher import normalize_url

PRODUCT_CODE = "PRIVACY_CORRECTION_PLAN"
PRODUCT_AMOUNT = 49900
PRODUCT_CURRENCY = "CLP"
INITIAL_STATUS = "pending_payment"

INITIALIZE_SQL = """
CREATE SCHEMA IF NOT EXISTS privacy;

CREATE TABLE IF NOT EXISTS privacy.correction_plan_order (
    id UUID PRIMARY KEY,
    site_url TEXT NOT NULL,
    email TEXT NOT NULL,
    product_code TEXT NOT NULL CHECK (product_code = 'PRIVACY_CORRECTION_PLAN'),
    amount INTEGER NOT NULL CHECK (amount = 49900),
    currency TEXT NOT NULL CHECK (currency = 'CLP'),
    status TEXT NOT NULL CHECK (status IN ('pending_payment', 'paid', 'cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class CorrectionPlanOrderNotFoundError(Exception):
    """No order matches the supplied identifier."""


@dataclass(frozen=True)
class CorrectionPlanOrder:
    id: UUID
    site_url: str
    email: str
    product_code: str
    amount: int
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime


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


def normalize_site_url(site_url: str) -> str:
    """Validate and canonicalize without resolving or requesting the site."""
    return normalize_url(validate_public_url_format(site_url))


def _from_row(row: tuple) -> CorrectionPlanOrder:
    return CorrectionPlanOrder(*row)


def create_order(*, site_url: str, email: str) -> CorrectionPlanOrder:
    order_id = uuid4()
    normalized_site_url = normalize_site_url(site_url)
    normalized_email = email.strip().lower()
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO privacy.correction_plan_order (
                id, site_url, email, product_code, amount, currency, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, site_url, email, product_code, amount, currency,
                      status, created_at, updated_at
            """,
            (
                order_id,
                normalized_site_url,
                normalized_email,
                PRODUCT_CODE,
                PRODUCT_AMOUNT,
                PRODUCT_CURRENCY,
                INITIAL_STATUS,
            ),
        )
        return _from_row(cursor.fetchone())


def get_order(order_id: UUID) -> CorrectionPlanOrder:
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, site_url, email, product_code, amount, currency,
                   status, created_at, updated_at
            FROM privacy.correction_plan_order WHERE id = %s
            """,
            (order_id,),
        )
        row = cursor.fetchone()
    if row is None:
        raise CorrectionPlanOrderNotFoundError("Order not found")
    return _from_row(row)


def mark_order_paid(order_id: UUID) -> CorrectionPlanOrder:
    """Set the technical paid state only; plan generation is intentionally separate."""
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE privacy.correction_plan_order
            SET status = 'paid', updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND status IN ('pending_payment', 'paid')
            RETURNING id, site_url, email, product_code, amount, currency,
                      status, created_at, updated_at
            """,
            (order_id,),
        )
        row = cursor.fetchone()
    if row is None:
        raise CorrectionPlanOrderNotFoundError("Order not found")
    return _from_row(row)
