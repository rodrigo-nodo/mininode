"""Repeatable, deterministic Privacy Web reviews during an active month."""

from __future__ import annotations

import calendar
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator, Mapping
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb

from mininode_api.domain_packs.privacy.versioning import diagnostic_comparability
from mininode_api.services import privacy_correction_plan, privacy_diagnostic_snapshot
from mininode_api.services.privacy_diagnostic import diagnose_privacy_url

INITIALIZE_SQL = """
CREATE SCHEMA IF NOT EXISTS privacy;

CREATE TABLE IF NOT EXISTS privacy.correction_plan_check (
    id UUID PRIMARY KEY,
    correction_plan_id UUID NOT NULL REFERENCES privacy.correction_plan(id),
    order_id UUID NOT NULL REFERENCES privacy.correction_plan_order(id),
    original_diagnostic_id UUID NOT NULL REFERENCES privacy.diagnostic(id),
    check_diagnostic_id UUID NOT NULL REFERENCES privacy.diagnostic(id),
    result_snapshot JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

DO $$
DECLARE
    single_use_constraint RECORD;
BEGIN
    FOR single_use_constraint IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'privacy.correction_plan_check'::regclass
          AND contype = 'u'
          AND pg_get_constraintdef(oid) = 'UNIQUE (correction_plan_id)'
    LOOP
        EXECUTE format(
            'ALTER TABLE privacy.correction_plan_check DROP CONSTRAINT %I',
            single_use_constraint.conname
        );
    END LOOP;
END $$;

CREATE INDEX IF NOT EXISTS correction_plan_check_plan_created_idx
    ON privacy.correction_plan_check (correction_plan_id, created_at DESC);
"""


class ImprovementCheckNotFoundError(Exception):
    """The capability token does not resolve to an eligible Privacy Web activation."""


class ImprovementCheckExpiredError(Exception):
    """Privacy Web is outside its active month."""


class ImprovementCheckUnavailableError(Exception):
    """The order is not paid or lacks a trustworthy activation time."""


class ImprovementInspectionError(Exception):
    """The new inspection or persistence could not be completed."""


@dataclass(frozen=True)
class CheckContext:
    order_id: UUID
    diagnostic_id: UUID
    site_url: str
    paid_at: datetime
    plan_snapshot: dict


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
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(INITIALIZE_SQL)


def expires_at(paid_at: datetime) -> datetime:
    """Return one calendar month after the trusted activation time."""
    year = paid_at.year + (1 if paid_at.month == 12 else 0)
    month = 1 if paid_at.month == 12 else paid_at.month + 1
    day = min(paid_at.day, calendar.monthrange(year, month)[1])
    return paid_at.replace(year=year, month=month, day=day)


def _context(cursor, plan_id: UUID) -> CheckContext:
    cursor.execute(
        """
        SELECT o.id, o.diagnostic_id, d.site_url, o.paid_at, p.plan_snapshot,
               o.status
        FROM privacy.correction_plan p
        JOIN privacy.correction_plan_order o ON o.correction_plan_id = p.id
        JOIN privacy.diagnostic d ON d.id = o.diagnostic_id
        WHERE p.id = %s AND p.status = 'active'
        """,
        (plan_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise ImprovementCheckNotFoundError()
    order_id, diagnostic_id, site_url, paid_at, plan_snapshot, order_status = row
    if order_status != "paid" or paid_at is None:
        raise ImprovementCheckUnavailableError()
    return CheckContext(order_id, diagnostic_id, site_url, paid_at, plan_snapshot)


def _latest(cursor, plan_id: UUID):
    cursor.execute(
        """SELECT created_at, result_snapshot FROM privacy.correction_plan_check
           WHERE correction_plan_id = %s
           ORDER BY created_at DESC
           LIMIT 1""",
        (plan_id,),
    )
    return cursor.fetchone()


def get_check_metadata(plan_id: UUID, *, now: datetime | None = None) -> dict:
    with _connection() as connection, connection.cursor() as cursor:
        context = _context(cursor, plan_id)
        latest = _latest(cursor, plan_id)

    deadline = expires_at(context.paid_at)
    metadata = {
        "status": (
            "expired"
            if (now or datetime.now(timezone.utc)) > deadline
            else "available"
        ),
        "expires_at": deadline,
    }
    if latest:
        metadata["latest_check"] = {
            "created_at": latest[0],
            "result": latest[1],
        }
    return metadata


def compare_diagnostics(
    plan: Mapping, original: Mapping, current: Mapping
) -> dict:
    """Compare plan items only when both diagnostics share canonical versions."""
    comparability = diagnostic_comparability(original, current)
    original_score = original["score"]
    current_score = current["score"]
    if comparability["status"] == "not_comparable":
        return {
            "version": "2",
            "comparability": comparability,
            "original_score": original_score,
            "current_score": current_score,
            "score_change": None,
            "total_plan_items": None,
            "corrected_count": None,
            "pending_count": None,
            "not_evaluable_count": None,
            "items": [],
        }

    current_controls = {
        item.get("control_code"): item for item in current.get("controls", [])
    }
    items = []
    for plan_item in plan.get("items", []):
        code = plan_item["control_code"]
        current_item = current_controls.get(code)
        if current_item is None or current_item.get("result") in {
            "not_evaluable", "not_applicable"
        }:
            check_status = "not_evaluable"
        elif current_item.get("result") == "detected":
            check_status = "corrected"
        else:
            check_status = "still_pending"
        items.append({
            "control_id": code,
            "name": plan_item.get("name", code),
            "status": check_status,
        })
    return {
        "version": "2",
        "comparability": comparability,
        "original_score": original_score,
        "current_score": current_score,
        "score_change": current_score - original_score,
        "total_plan_items": len(items),
        "corrected_count": sum(item["status"] == "corrected" for item in items),
        "pending_count": sum(item["status"] == "still_pending" for item in items),
        "not_evaluable_count": sum(item["status"] == "not_evaluable" for item in items),
        "items": items,
    }


def perform_check(access_token: str, *, now: datetime | None = None) -> dict:
    """Inspect and persist one review while holding a plan-scoped advisory lock."""
    try:
        plan_record = privacy_correction_plan.get_correction_plan(access_token)
    except privacy_correction_plan.CorrectionPlanNotFoundError as exc:
        raise ImprovementCheckNotFoundError() from exc
    plan_id = plan_record["id"]
    current_time = now or datetime.now(timezone.utc)
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            (str(plan_id),),
        )
        context = _context(cursor, plan_id)
        deadline = expires_at(context.paid_at)
        if current_time > deadline:
            raise ImprovementCheckExpiredError()

        try:
            original = privacy_diagnostic_snapshot.get_diagnostic_snapshot(
                context.diagnostic_id
            )
            diagnostic = diagnose_privacy_url(context.site_url)
            checked = privacy_diagnostic_snapshot.create_diagnostic_snapshot(diagnostic)
            result = compare_diagnostics(
                context.plan_snapshot, original.diagnostic_snapshot,
                checked.diagnostic_snapshot,
            )
            cursor.execute(
                """
                INSERT INTO privacy.correction_plan_check (
                    id, correction_plan_id, order_id, original_diagnostic_id,
                    check_diagnostic_id, result_snapshot
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING created_at
                """,
                (uuid4(), plan_id, context.order_id, context.diagnostic_id,
                 checked.id, Jsonb(result)),
            )
            created_at = cursor.fetchone()[0]
        except ImprovementCheckExpiredError:
            raise
        except Exception as exc:
            raise ImprovementInspectionError() from exc
    return {
        "status": "available",
        "expires_at": deadline,
        "created_at": created_at,
        "result": result,
    }
