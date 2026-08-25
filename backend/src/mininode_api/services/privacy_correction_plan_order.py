"""Minimal commercial orders for the Privacy correction plan."""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator
from uuid import UUID, uuid4

import psycopg

from mininode_api.services import privacy_diagnostic_snapshot

PRODUCT_CODE = "PRIVACY_CORRECTION_PLAN"
PRODUCT_AMOUNT = 49900
PRODUCT_CURRENCY = "CLP"
INITIAL_STATUS = "pending_payment"

INITIALIZE_SQL = """
CREATE SCHEMA IF NOT EXISTS privacy;

CREATE TABLE IF NOT EXISTS privacy.correction_plan_order (
    id UUID PRIMARY KEY,
    diagnostic_id UUID NOT NULL REFERENCES privacy.diagnostic(id),
    correction_plan_id UUID NULL REFERENCES privacy.correction_plan(id),
    site_url TEXT NOT NULL,
    email TEXT NOT NULL,
    product_code TEXT NOT NULL CHECK (product_code = 'PRIVACY_CORRECTION_PLAN'),
    amount INTEGER NOT NULL CHECK (amount = 49900),
    currency TEXT NOT NULL CHECK (currency = 'CLP'),
    status TEXT NOT NULL CHECK (status IN ('pending_payment', 'paid', 'cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE privacy.correction_plan_order
    ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ NULL;

ALTER TABLE privacy.correction_plan_order
    ADD COLUMN IF NOT EXISTS correction_plan_id UUID NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'correction_plan_order_correction_plan_id_fkey'
          AND conrelid = 'privacy.correction_plan_order'::regclass
    ) THEN
        ALTER TABLE privacy.correction_plan_order
            ADD CONSTRAINT correction_plan_order_correction_plan_id_fkey
            FOREIGN KEY (correction_plan_id) REFERENCES privacy.correction_plan(id);
    END IF;
END $$;
"""


class CorrectionPlanOrderNotFoundError(Exception):
    """No order matches the supplied identifier."""


class CorrectionPlanOrderStateError(Exception):
    """The order cannot be activated from its current state."""


@dataclass(frozen=True)
class CorrectionPlanOrder:
    id: UUID
    diagnostic_id: UUID
    correction_plan_id: UUID | None
    site_url: str
    email: str
    product_code: str
    amount: int
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime
    paid_at: datetime | None = None


def _database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    return database_url


@contextmanager
def _connection() -> Iterator[psycopg.Connection]:
    with psycopg.connect(_database_url()) as connection:
        yield connection


@contextmanager
def activation_lock(order_id: UUID) -> Iterator[None]:
    """Serialize activation attempts for one order across API workers."""
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            (str(order_id),),
        )
        yield


def initialize_database() -> None:
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(INITIALIZE_SQL)


def _from_row(row: tuple) -> CorrectionPlanOrder:
    return CorrectionPlanOrder(*row)


def create_order(*, diagnostic_id: UUID, email: str) -> CorrectionPlanOrder:
    order_id = uuid4()
    diagnostic = privacy_diagnostic_snapshot.require_purchasable(
        privacy_diagnostic_snapshot.get_diagnostic_snapshot(diagnostic_id)
    )
    normalized_email = email.strip().lower()
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO privacy.correction_plan_order (
                id, diagnostic_id, site_url, email, product_code, amount, currency, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, diagnostic_id, correction_plan_id, site_url, email, product_code, amount, currency,
                      status, created_at, updated_at, paid_at
            """,
            (
                order_id,
                diagnostic.id,
                diagnostic.site_url,
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
            SELECT id, diagnostic_id, correction_plan_id, site_url, email, product_code, amount, currency,
                   status, created_at, updated_at, paid_at
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
            SET status = 'paid', paid_at = COALESCE(paid_at, CURRENT_TIMESTAMP),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND status IN ('pending_payment', 'paid')
            RETURNING id, diagnostic_id, correction_plan_id, site_url, email, product_code, amount, currency,
                      status, created_at, updated_at, paid_at
            """,
            (order_id,),
        )
        row = cursor.fetchone()
    if row is None:
        raise CorrectionPlanOrderNotFoundError("Order not found")
    return _from_row(row)


def attach_correction_plan(order_id: UUID, correction_plan_id: UUID) -> CorrectionPlanOrder:
    """Attach one plan and transition only a pending order to ``paid``."""
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE privacy.correction_plan_order
            SET correction_plan_id = %s, status = 'paid', paid_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND status = 'pending_payment' AND correction_plan_id IS NULL
            RETURNING id, diagnostic_id, correction_plan_id, site_url, email, product_code,
                      amount, currency, status, created_at, updated_at, paid_at
            """,
            (correction_plan_id, order_id),
        )
        row = cursor.fetchone()
    if row is None:
        raise CorrectionPlanOrderStateError("Order is not pending activation")
    return _from_row(row)
