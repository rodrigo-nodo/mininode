"""Authenticated Privacy Web plans and reviews, bound to Access entitlements.

Independent of legacy commercial correction_plan_order and capability tokens.
Each entitlement owns an immutable baseline and repeatable checks; all access is
checked against live workspace membership, site linkage, status and time window.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb

from mininode_api.domain_packs.privacy.correction_plan import build_correction_plan
from mininode_api.services import billing, privacy_correction_plan_check
from mininode_api.services.privacy_diagnostic import diagnose_privacy_url

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS privacy;
CREATE TABLE IF NOT EXISTS privacy.entitled_plan (
  id UUID PRIMARY KEY,
  workspace_site_id UUID NOT NULL REFERENCES access.workspace_sites(id),
  entitlement_id UUID NOT NULL UNIQUE REFERENCES access.entitlements(id),
  original_diagnostic_id UUID NOT NULL REFERENCES privacy.diagnostic(id),
  plan_snapshot JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS privacy_entitled_plan_site_idx
  ON privacy.entitled_plan(workspace_site_id, created_at DESC);
CREATE TABLE IF NOT EXISTS privacy.entitled_plan_check (
  id UUID PRIMARY KEY,
  entitled_plan_id UUID NOT NULL REFERENCES privacy.entitled_plan(id),
  check_diagnostic_id UUID NOT NULL REFERENCES privacy.diagnostic(id),
  result_snapshot JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS privacy_entitled_plan_check_latest_idx
  ON privacy.entitled_plan_check(entitled_plan_id, created_at DESC);
"""


class PlanUnavailable(Exception):
    """No active entitlement or authorized site is available."""


class PlanNotFound(Exception):
    """No baseline was prepared for this entitlement."""


class CheckUnavailable(Exception):
    """The inspection/persistence could not be completed."""


def initialize_database() -> None:
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute(SCHEMA_SQL)


def _entitlement(cur, user_id: UUID, site_id: UUID):
    # All mutations (admin grants/revocations, billing) serialize on ws row.
    # Hold that lock through creation/check to avoid serving revoked periods.
    cur.execute("""
        SELECT ws.id FROM access.workspace_sites ws
        JOIN access.workspace_members wm ON wm.workspace_id=ws.workspace_id
        WHERE ws.id=%s AND ws.detached_at IS NULL
          AND wm.user_id=%s AND wm.role IN ('owner','member')
        FOR UPDATE OF ws
    """, (site_id, user_id))
    if cur.fetchone() is None:
        raise PlanUnavailable()
    cur.execute("""
        SELECT id, active_until FROM access.entitlements
        WHERE workspace_site_id=%s AND product_code=%s AND status='active'
          AND active_from<=CURRENT_TIMESTAMP
          AND (active_until IS NULL OR active_until>CURRENT_TIMESTAMP)
        ORDER BY active_from DESC, id DESC LIMIT 1
    """, (site_id, billing.PRODUCT))
    entitlement = cur.fetchone()
    if entitlement is None:
        raise PlanUnavailable()
    return entitlement


def _plan(cur, entitlement_id: UUID):
    cur.execute("""
        SELECT p.id, p.workspace_site_id, d.site_url, d.diagnostic_snapshot,
               p.plan_snapshot, p.created_at
        FROM privacy.entitled_plan p
        JOIN privacy.diagnostic d ON d.id=p.original_diagnostic_id
        WHERE p.entitlement_id=%s
    """, (entitlement_id,))
    return cur.fetchone()


def _latest_check(cur, plan_id: UUID):
    cur.execute("""
        SELECT created_at, result_snapshot FROM privacy.entitled_plan_check
        WHERE entitled_plan_id=%s ORDER BY created_at DESC, id DESC LIMIT 1
    """, (plan_id,))
    return cur.fetchone()


def _response(cur, entitlement, plan) -> dict:
    plan_id, _, site_url, _, snapshot, created_at = plan
    latest = _latest_check(cur, plan_id)
    return {
        "id": plan_id,
        "site_url": site_url,
        "created_at": created_at,
        "plan": snapshot,
        "check": {
            "status": "available",
            "expires_at": entitlement[1],
            **({"latest_check": {"created_at": latest[0], "result": latest[1]}} if latest else {}),
        },
    }


def ensure_plan(user_id: UUID, site_id: UUID) -> dict:
    """Create one frozen baseline per active entitlement, idempotently.

    Never reinspect here: the plan is derived from an existing saved snapshot.
    A courtesy can open the same plan without creating a fake billing order.
    """
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            entitlement = _entitlement(cur, user_id, site_id)
            current = _plan(cur, entitlement[0])
            if current is None:
                cur.execute("""
                    SELECT id, diagnostic_snapshot FROM privacy.diagnostic
                    WHERE workspace_site_id=%s
                    ORDER BY created_at DESC, id DESC LIMIT 1
                """, (site_id,))
                diagnostic = cur.fetchone()
                if diagnostic is None:
                    raise PlanNotFound("Realiza primero un diagnóstico de este sitio.")
                original_id, original = diagnostic
                plan_snapshot = build_correction_plan(
                    original.get("controls", []), initial_score=original["score"],
                )
                cur.execute("""
                    INSERT INTO privacy.entitled_plan
                      (id,workspace_site_id,entitlement_id,original_diagnostic_id,plan_snapshot)
                    VALUES (%s,%s,%s,%s,%s)
                """, (uuid4(), site_id, entitlement[0], original_id, Jsonb(plan_snapshot)))
                current = _plan(cur, entitlement[0])
            return _response(cur, entitlement, current)


def get_plan(user_id: UUID, site_id: UUID) -> dict:
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            entitlement = _entitlement(cur, user_id, site_id)
            current = _plan(cur, entitlement[0])
            if current is None:
                raise PlanNotFound()
            return _response(cur, entitlement, current)


def review(user_id: UUID, site_id: UUID) -> dict:
    """Serialize and atomically save a repeatable review and its diagnosis."""
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            entitlement = _entitlement(cur, user_id, site_id)
            current = _plan(cur, entitlement[0])
            if current is None:
                raise PlanNotFound()
            plan_id, _, original_url, original, plan_snapshot, _ = current
            # The inspected URL is always the original stored target.
            # No URL or workspace is accepted from the browser.
            try:
                diagnosis = diagnose_privacy_url(original_url)
                checked_id = uuid4()
                cur.execute("""
                    INSERT INTO privacy.diagnostic
                      (id,site_url,requested_url,diagnostic_snapshot,score,
                       purchase_expires_at,workspace_site_id)
                    VALUES (%s,%s,%s,%s,%s,CURRENT_TIMESTAMP + INTERVAL '24 hours',%s)
                """, (checked_id, diagnosis["site_url"], original_url,
                      Jsonb(diagnosis), diagnosis["score"], site_id))
                result = privacy_correction_plan_check.compare_diagnostics(
                    plan_snapshot, original, diagnosis,
                )
                cur.execute("""
                    INSERT INTO privacy.entitled_plan_check
                      (id,entitled_plan_id,check_diagnostic_id,result_snapshot)
                    VALUES (%s,%s,%s,%s) RETURNING created_at
                """, (uuid4(), plan_id, checked_id, Jsonb(result)))
                created_at = cur.fetchone()[0]
            except Exception as exc:
                logger.warning("Privacy entitlement review failed; transaction rolled back")
                raise CheckUnavailable() from exc
            return {
                "status": "available",
                "expires_at": entitlement[1],
                "created_at": created_at,
                "result": result,
            }
