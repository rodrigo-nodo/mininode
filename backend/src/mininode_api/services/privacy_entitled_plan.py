"""Authenticated Privacy Web plans and reviews, bound to Access entitlements.

Independent of legacy commercial correction_plan_order and capability tokens.
Each entitlement owns an immutable baseline and repeatable checks; all access is
checked against live workspace membership, site linkage, status and time window.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb

from mininode_api.domain_packs.privacy.correction_plan import build_correction_plan
from mininode_api.domain_packs.privacy.evaluator import load_controls
from mininode_api.domain_packs.privacy.versioning import diagnostic_versions
from mininode_api.services import billing, privacy_correction_plan_check
from mininode_api.services.privacy_diagnostic import diagnose_privacy_url

logger = logging.getLogger(__name__)


class PlanUnavailable(Exception):
    """No active entitlement or authorized site is available."""


class PlanNotFound(Exception):
    """No baseline was prepared for this entitlement."""


class CheckUnavailable(Exception):
    """The inspection/persistence could not be completed."""


def check_schema_ready() -> None:
    """Read-only readiness gate: migrations must run before API startup."""
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT to_regclass('privacy.entitled_plan'),
                       to_regclass('privacy.entitled_plan_check')
            """)
            if any(table is None for table in cur.fetchone()):
                raise RuntimeError("PW-03B schema migration has not been applied")
            # Fail closed on incompatible layouts too, never attempt runtime DDL.
            cur.execute("""
                SELECT id, workspace_site_id, entitlement_id,
                       original_diagnostic_id, plan_snapshot, created_at
                  FROM privacy.entitled_plan LIMIT 0
            """)
            cur.execute("""
                SELECT id, entitled_plan_id, check_diagnostic_id,
                       result_snapshot, created_at
                  FROM privacy.entitled_plan_check LIMIT 0
            """)


def _entitlement(cur, user_id: UUID, site_id: UUID, *, allow_expired: bool = False):
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
    if entitlement is None and allow_expired:
        # Preserve the last result when a period ends naturally. Revoked grants
        # never qualify for read-only recovery.
        cur.execute("""
            SELECT e.id, e.active_until
            FROM access.entitlements e
            JOIN privacy.entitled_plan p ON p.entitlement_id=e.id
            WHERE e.workspace_site_id=%s AND e.product_code=%s
              AND e.status='active'
              AND e.active_until IS NOT NULL AND e.active_until<=CURRENT_TIMESTAMP
            ORDER BY e.active_until DESC, e.id DESC LIMIT 1
        """, (site_id, billing.PRODUCT))
        entitlement = cur.fetchone()
    if entitlement is None:
        raise PlanUnavailable()
    return entitlement


def _plan(cur, entitlement_id: UUID):
    cur.execute("""
        SELECT p.id, p.workspace_site_id, d.site_url, d.diagnostic_snapshot,
               p.plan_snapshot, p.created_at, d.created_at
        FROM privacy.entitled_plan p
        JOIN privacy.diagnostic d ON d.id=p.original_diagnostic_id
        WHERE p.entitlement_id=%s
    """, (entitlement_id,))
    return cur.fetchone()


def _latest_check(cur, plan_id: UUID):
    cur.execute("""
        SELECT c.created_at, c.result_snapshot, d.diagnostic_snapshot, d.created_at
        FROM privacy.entitled_plan_check c
        JOIN privacy.entitled_plan p ON p.id=c.entitled_plan_id
        JOIN privacy.diagnostic d ON d.id=c.check_diagnostic_id
                                 AND d.workspace_site_id=p.workspace_site_id
        WHERE c.entitled_plan_id=%s
        ORDER BY c.created_at DESC, c.id DESC LIMIT 1
    """, (plan_id,))
    return cur.fetchone()


def _public_source_url(value: object) -> str | None:
    """Keep only safe public page locations; never expose query tokens or credentials."""
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None):
            return None
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    except ValueError:
        return None


def _diagnostic_view(snapshot: dict, created_at: datetime, *, source: str) -> dict:
    """C2 read-only projection; raw technical evidence never leaves the server."""
    catalog = {control["code"]: control for control in load_controls()}
    controls = []
    for item in snapshot.get("controls", []):
        if not isinstance(item, dict) or not isinstance(item.get("control_code"), str):
            continue
        code = item["control_code"]
        metadata = catalog.get(code, {})
        area = metadata.get("domain")
        if area == "Seguridad visible":
            area = "Seguridad"
        controls.append({
            "control_code": code,
            "name": metadata.get("name", code),
            "area": area,
            "type": metadata.get("type"),
            "result": item.get("result"),
            "reason": item.get("reason") if isinstance(item.get("reason"), str) else None,
            "confidence": item.get("confidence") if isinstance(item.get("confidence"), str) else None,
            "evidence_summary": (
                item.get("evidence_summary")
                if isinstance(item.get("evidence_summary"), str) else None
            ),
            "source_url": _public_source_url(item.get("source_url")),
        })
    scope = snapshot.get("scope")
    scope = scope if isinstance(scope, dict) else {}
    return {
        "source": source,
        "created_at": created_at,
        "score": snapshot["score"],
        "framework_version": snapshot.get("framework_version"),
        "scoring_version": snapshot.get("scoring_version"),
        "scope": {
            "pages_analyzed": scope.get("pages_analyzed"),
            "limited": scope.get("limited"),
        },
        "controls": controls,
    }


def _pending_verification(snapshot: dict, baseline: dict) -> list[dict]:
    """Uncertain evaluated controls need verification, not a claim of correction."""
    catalog = {control["code"]: control for control in load_controls()}
    baseline_codes = {item["control_code"] for item in baseline.get("items", [])}
    reviewed = {}
    for item in snapshot.get("controls", []):
        if isinstance(item, dict) and isinstance(item.get("control_code"), str):
            reviewed[item["control_code"]] = item.get("result")
    pending = []
    for code, control in catalog.items():
        if control["type"] not in {"evaluation", "conditional_evaluation"} or control.get("score_weight", 1) <= 0:
            continue
        result = reviewed.get(code)
        if result == "not_evaluable" or (code in baseline_codes and result in {None, "not_applicable"}):
            pending.append({
                "control_code": code,
                "name": control["name"],
                "status": "pending_verification",
                "reason": result or "missing",
            })
    return pending


def _current_actions(baseline: dict, snapshot: dict, updated_at: datetime, *, source: str) -> dict:
    """Read-only C3 plan; never mutate the immutable baseline or infer from old versions."""
    if source == "review":
        versions = diagnostic_versions()
        if any(snapshot.get(key) != value for key, value in versions.items()):
            return {
                "status": "version_mismatch",
                "source": source,
                "created_at": updated_at,
                "item_count": None,
                "items": [],
                "verification_pending_count": None,
                "verification_pending": [],
                "actions_version": None,
            }
        generated = build_correction_plan(
            snapshot.get("controls", []), initial_score=snapshot["score"]
        )
    else:
        # Before the first follow-up, reuse the saved initial plan as-is.
        generated = baseline
    verification = _pending_verification(snapshot, baseline)
    return {
        "status": "available",
        "source": source,
        "created_at": updated_at,
        "item_count": generated["item_count"],
        "items": generated["items"],
        "verification_pending_count": len(verification),
        "verification_pending": verification,
        "actions_version": generated["actions_version"],
    }


def _response(cur, entitlement, plan) -> dict:
    plan_id, _, site_url, original, snapshot, created_at, initial_at = plan
    latest = _latest_check(cur, plan_id)
    current_snapshot, current_at = (latest[2], latest[3]) if latest else (original, initial_at)
    return {
        "id": plan_id,
        "site_url": site_url,
        "created_at": created_at,
        "plan": snapshot,
        "current_actions": _current_actions(
            snapshot, current_snapshot, current_at, source="review" if latest else "initial"
        ),
        "diagnostic": {
            "initial": {
                "score": original["score"],
                "created_at": initial_at,
                "framework_version": original.get("framework_version"),
                "scoring_version": original.get("scoring_version"),
            },
            "current": _diagnostic_view(
                current_snapshot, current_at, source="review" if latest else "initial"
            ),
        },
        "check": {
            "status": ("expired" if entitlement[1] is not None
                       and datetime.now(timezone.utc) >= entitlement[1] else "available"),
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
            entitlement = _entitlement(cur, user_id, site_id, allow_expired=True)
            current = _plan(cur, entitlement[0])
            if current is None:
                raise PlanNotFound()
            return _response(cur, entitlement, current)


def _ensure_time_window(cur, until: datetime | None) -> None:
    """Use real DB wall-clock, not transaction-start CURRENT_TIMESTAMP."""
    if until is None:
        return
    cur.execute("SELECT clock_timestamp() < %s", (until,))
    if cur.fetchone()[0] is not True:
        raise PlanUnavailable("Privacy Web expired during review")


def review(user_id: UUID, site_id: UUID) -> dict:
    """Serialize and atomically save a repeatable review and its diagnosis."""
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            entitlement = _entitlement(cur, user_id, site_id)
            current = _plan(cur, entitlement[0])
            if current is None:
                raise PlanNotFound()
            plan_id, _, original_url, original, plan_snapshot, _, _ = current
            # The inspected URL is always the original stored target.
            # No URL or workspace is accepted from the browser.
            try:
                diagnosis = diagnose_privacy_url(original_url)
                # Re-check after potentially slow external inspection, before
                # any persistence. Transaction-start now() would be stale here.
                _ensure_time_window(cur, entitlement[1])
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
                # Never return a review as active if the window closed during
                # persistence; the exception rolls back both inserted rows.
                _ensure_time_window(cur, entitlement[1])
            except PlanUnavailable:
                raise
            except Exception as exc:
                logger.warning("Privacy entitlement review failed; transaction rolled back")
                raise CheckUnavailable() from exc
            return {
                "status": "available",
                "expires_at": entitlement[1],
                "created_at": created_at,
                "result": result,
            }
