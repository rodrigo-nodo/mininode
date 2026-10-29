"""PW-03B contract: real PostgreSQL, authenticated access and no legacy orders."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
import importlib.util
import inspect
import os
import time

import psycopg
from psycopg.types.json import Jsonb
import pytest
from psycopg.conninfo import conninfo_to_dict
from fastapi.testclient import TestClient

from mininode_api.api import privacy_entitled_plan as api
from mininode_api.main import create_app
from mininode_api.domain_packs.privacy.versioning import diagnostic_versions
from mininode_api.services import (
    access, access_identity, privacy_diagnostic_snapshot, privacy_entitled_plan,
)

MIGRATION = "20261026_privacy_entitled_plans.sql"
RUNNER = Path(__file__).resolve().parents[1] / "scripts" / "predeploy_migrations.py"
spec = importlib.util.spec_from_file_location("pw03b_predeploy", RUNNER)
migration_runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration_runner)


SAMPLE = {
    "site_url": "https://example.test/",
    "score": 65,
    "framework_version": "0.6",
    "scoring_version": "0.6",
    "controls": [{"control_code": "PRV-001", "result": "not_detected", "confidence": "high"}],
    "priorities": [{"name": "Revisar la política"}],
}


@pytest.fixture
def context(monkeypatch):
    url = os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("Local PostgreSQL DATABASE_URL required")
    info = conninfo_to_dict(url)
    if info.get("host", "localhost") not in {"localhost", "127.0.0.1", "postgres"} or info.get("dbname") != "mininode_test":
        pytest.skip("Only disposable local/CI mininode_test PostgreSQL is allowed")
    access.initialize_database()
    privacy_diagnostic_snapshot.initialize_database()
    migration_runner.migrate(url, [MIGRATION])
    privacy_entitled_plan.check_schema_ready()
    user_id, foreign_id, workspace_id, site_id, ws_site_id, entitlement_id = (uuid4() for _ in range(6))
    host = f"pw03b-{uuid4().hex}.example"
    snapshot = {**SAMPLE, "site_url": f"https://{host}/"}
    with psycopg.connect(url) as conn:
        conn.execute("INSERT INTO access.users (id,email) VALUES (%s,%s),(%s,%s)",
                     (user_id, f"{user_id}@example.test", foreign_id, f"{foreign_id}@example.test"))
        conn.execute("INSERT INTO access.workspaces(id,name) VALUES (%s,'PW03B test')", (workspace_id,))
        conn.execute("INSERT INTO access.workspace_members(workspace_id,user_id,role) VALUES (%s,%s,'owner')",
                     (workspace_id, user_id))
        conn.execute("INSERT INTO access.sites(id,hostname,canonical_url) VALUES (%s,%s,%s)",
                     (site_id, host, f"https://{host}/"))
        conn.execute("INSERT INTO access.workspace_sites(id,workspace_id,site_id) VALUES (%s,%s,%s)",
                     (ws_site_id, workspace_id, site_id))
        now = datetime.now(timezone.utc)
        conn.execute("""
            INSERT INTO access.entitlements
              (id,workspace_site_id,product_code,active_from,active_until,status,source,source_id)
            VALUES (%s,%s,'privacy_web',%s,%s,'active','internal_grant',%s)
        """, (entitlement_id, ws_site_id, now - timedelta(minutes=1),
              now + timedelta(days=30), str(entitlement_id)))
    original = privacy_diagnostic_snapshot.create_diagnostic_snapshot(
        snapshot, workspace_site_id=ws_site_id, requested_url=f"https://{host}/",
    )
    user = access.StoredUser(id=user_id, email=f"{user_id}@example.test")
    monkeypatch.setattr(access_identity, "verify_access_jwt",
                        lambda _: access_identity.AccessIdentity(email=user.email))
    monkeypatch.setattr(access, "get_or_create_user", lambda _: user)
    app = create_app()
    app.state.access_ready = True
    app.state.privacy_diagnostic_snapshot_ready = True
    app.state.privacy_entitled_plan_ready = True
    try:
        yield {
            "url": url, "client": TestClient(app), "site": ws_site_id,
            "original": original.id, "snapshot": snapshot,
            "user": user, "foreign": foreign_id, "entitlement": entitlement_id,
            "headers": {"Cf-Access-Jwt-Assertion": "signed-test"},
        }
    finally:
        with psycopg.connect(url) as conn:
            conn.execute("""
                DELETE FROM privacy.entitled_plan_check WHERE entitled_plan_id IN
                  (SELECT id FROM privacy.entitled_plan WHERE workspace_site_id=%s)
            """, (ws_site_id,))
            conn.execute("DELETE FROM privacy.entitled_plan WHERE workspace_site_id=%s", (ws_site_id,))
            conn.execute("DELETE FROM privacy.diagnostic WHERE workspace_site_id=%s", (ws_site_id,))
            conn.execute("DELETE FROM access.entitlements WHERE workspace_site_id=%s", (ws_site_id,))
            conn.execute("DELETE FROM access.workspace_sites WHERE id=%s", (ws_site_id,))
            conn.execute("DELETE FROM access.sites WHERE id=%s", (site_id,))
            conn.execute("DELETE FROM access.workspace_members WHERE workspace_id=%s", (workspace_id,))
            conn.execute("DELETE FROM access.workspaces WHERE id=%s", (workspace_id,))
            conn.execute("DELETE FROM access.users WHERE id IN (%s,%s)", (user_id, foreign_id))


def _path(ctx):
    return f"/privacy/workspace-sites/{ctx['site']}/plan"


def test_courtesy_creates_stable_baseline_without_legacy_order(context):
    c = context
    path = _path(c)
    assert c["client"].post(path).status_code == 401
    response = c["client"].post(path, headers=c["headers"])
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["plan"]["initial_score"] == c["snapshot"]["score"]
    assert data["current_actions"]["status"] == "available"
    assert data["current_actions"]["source"] == "initial"
    assert data["current_actions"]["created_at"] == data["diagnostic"]["initial"]["created_at"]
    assert data["current_actions"]["items"] == data["plan"]["items"]
    assert data["current_actions"]["item_count"] == data["plan"]["item_count"]
    assert data["site_url"] == c["snapshot"]["site_url"]
    assert data["check"]["status"] == "available"
    assert data["check"]["expires_at"]
    diagnostic = data["diagnostic"]
    assert diagnostic["initial"]["score"] == c["snapshot"]["score"]
    assert diagnostic["current"]["score"] == c["snapshot"]["score"]
    assert diagnostic["initial"]["created_at"] == diagnostic["current"]["created_at"]
    assert diagnostic["current"]["source"] == "initial"
    assert diagnostic["current"]["framework_version"] == c["snapshot"]["framework_version"]
    assert diagnostic["current"]["scoring_version"] == c["snapshot"]["scoring_version"]
    assert diagnostic["current"]["controls"][0]["control_code"] == "PRV-001"
    assert diagnostic["current"]["controls"][0]["area"] == "Transparencia"
    assert diagnostic["current"]["controls"][0]["result"] == "not_detected"
    with psycopg.connect(c["url"]) as conn:
        original_date = conn.execute(
            "SELECT created_at FROM privacy.diagnostic WHERE id=%s", (c["original"],)
        ).fetchone()[0]
    assert diagnostic["initial"]["created_at"] == original_date.isoformat()
    again = c["client"].post(path, headers=c["headers"])
    assert again.status_code == 200
    assert again.json()["id"] == data["id"]
    with psycopg.connect(c["url"]) as conn:
        plan = conn.execute("""
            SELECT original_diagnostic_id,entitlement_id FROM privacy.entitled_plan
            WHERE id=%s
        """, (data["id"],)).fetchone()
        assert plan == (c["original"], c["entitlement"])
        assert conn.execute(
            "SELECT count(*) FROM privacy.entitled_plan WHERE entitlement_id=%s",
            (c["entitlement"],),
        ).fetchone()[0] == 1
    assert c["client"].get(path, headers=c["headers"]).status_code == 200


def test_membership_and_revocation_fail_closed(context, monkeypatch):
    c = context
    path = _path(c)
    unowned = access.StoredUser(id=c["foreign"], email="foreign@example.test")
    monkeypatch.setattr(access, "get_or_create_user", lambda _: unowned)
    assert c["client"].post(path, headers=c["headers"]).status_code == 403
    monkeypatch.setattr(access, "get_or_create_user", lambda _: c["user"])
    assert c["client"].post(path, headers=c["headers"]).status_code == 200

    with psycopg.connect(c["url"]) as conn:
        conn.execute(
            "UPDATE access.entitlements SET status='revoked' WHERE id=%s",
            (c["entitlement"],),
        )
    assert c["client"].get(path, headers=c["headers"]).status_code == 403
    assert c["client"].post(path + "/check", headers=c["headers"]).status_code == 403
    with psycopg.connect(c["url"]) as conn:
        assert conn.execute(
            "SELECT count(*) FROM privacy.entitled_plan_check WHERE entitled_plan_id IN (SELECT id FROM privacy.entitled_plan WHERE workspace_site_id=%s)",
            (c["site"],),
        ).fetchone()[0] == 0


def test_expiry_blocks_access_without_erasing_plan_or_original(context):
    c = context
    path = _path(c)
    created = c["client"].post(path, headers=c["headers"])
    assert created.status_code == 200
    plan_id = created.json()["id"]
    with psycopg.connect(c["url"]) as conn:
        conn.execute(
            "UPDATE access.entitlements SET active_until=now() - interval '1 second' WHERE id=%s",
            (c["entitlement"],),
        )
    assert c["client"].post(path, headers=c["headers"]).status_code == 403
    expired = c["client"].get(path, headers=c["headers"])
    assert expired.status_code == 200
    assert expired.json()["id"] == plan_id
    assert expired.json()["check"]["status"] == "expired"
    assert expired.json()["diagnostic"]["current"]["source"] == "initial"
    assert expired.json()["current_actions"]["status"] == "available"
    assert expired.json()["current_actions"]["items"] == created.json()["plan"]["items"]
    assert expired.json()["diagnostic"]["current"]["score"] == c["snapshot"]["score"]
    assert c["client"].post(path + "/check", headers=c["headers"]).status_code == 403
    with psycopg.connect(c["url"]) as conn:
        assert conn.execute(
            "SELECT count(*) FROM privacy.entitled_plan WHERE id=%s", (plan_id,),
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT count(*) FROM privacy.diagnostic WHERE id=%s", (c["original"],),
        ).fetchone()[0] == 1


def test_repeated_checks_compare_frozen_base_and_persist_atomic_history(context, monkeypatch):
    c = context
    path = _path(c)
    plan = c["client"].post(path, headers=c["headers"])
    assert plan.status_code == 200
    plan_id = plan.json()["id"]
    inspected = []
    revised = {**c["snapshot"], "score": 85,
               "controls": [{"control_code": "PRV-001", "result": "detected", "confidence": "high"}]}
    monkeypatch.setattr(privacy_entitled_plan, "diagnose_privacy_url",
                        lambda url: inspected.append(url) or revised)
    first = c["client"].post(path + "/check", headers=c["headers"])
    second = c["client"].post(path + "/check", headers=c["headers"])
    assert first.status_code == second.status_code == 200
    assert len(inspected) == 2
    assert all(url == c["snapshot"]["site_url"] for url in inspected)
    assert first.json()["result"]["original_score"] == c["snapshot"]["score"]
    assert first.json()["result"]["current_score"] == 85
    response = c["client"].get(path, headers=c["headers"]).json()
    latest = response["check"]["latest_check"]
    assert latest["result"]["current_score"] == 85
    assert response["diagnostic"]["initial"]["score"] == 65
    assert response["diagnostic"]["current"]["score"] == 85
    assert response["diagnostic"]["current"]["source"] == "review"
    assert response["diagnostic"]["current"]["controls"][0]["result"] == "detected"
    assert response["diagnostic"]["current"]["created_at"] is not None
    assert response["diagnostic"]["initial"]["created_at"] is not None
    with psycopg.connect(c["url"]) as conn:
        assert conn.execute(
            "SELECT count(*) FROM privacy.entitled_plan_check WHERE entitled_plan_id=%s",
            (plan_id,),
        ).fetchone()[0] == 2
        rows = conn.execute("""
            SELECT diagnostic_snapshot,score FROM privacy.diagnostic WHERE workspace_site_id=%s
            ORDER BY created_at
        """, (c["site"],)).fetchall()
    assert len(rows) == 3
    assert rows[0] == (c["snapshot"], c["snapshot"]["score"])
    assert all(row == (revised, 85) for row in rows[1:])


def test_failed_check_rolls_back_diagnostic_and_result(context, monkeypatch):
    c = context
    path = _path(c)
    assert c["client"].post(path, headers=c["headers"]).status_code == 200
    def fail(_url):
        raise RuntimeError("external inspector unavailable")
    monkeypatch.setattr(privacy_entitled_plan, "diagnose_privacy_url", fail)
    denied = c["client"].post(path + "/check", headers=c["headers"])
    assert denied.status_code == 503
    with psycopg.connect(c["url"]) as conn:
        assert conn.execute(
            "SELECT count(*) FROM privacy.diagnostic WHERE workspace_site_id=%s",
            (c["site"],),
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT count(*) FROM privacy.entitled_plan_check WHERE entitled_plan_id IN (SELECT id FROM privacy.entitled_plan WHERE workspace_site_id=%s)",
            (c["site"],),
        ).fetchone()[0] == 0


def test_schema_is_applied_by_reviewed_migration_and_startup_is_read_only(context):
    c = context
    url = c["url"]
    with psycopg.connect(url) as conn:
        applied = conn.execute(
            "SELECT checksum_sha256, applied_at FROM public.schema_migrations WHERE filename=%s",
            (MIGRATION,),
        ).fetchone()
        assert applied is not None
        assert len(applied[0]) == 64
        assert conn.execute(
            "SELECT to_regclass('privacy.entitled_plan'), to_regclass('privacy.entitled_plan_check')"
        ).fetchone() == ("privacy.entitled_plan", "privacy.entitled_plan_check")
    migration_runner.migrate(url, [MIGRATION])
    with psycopg.connect(url) as conn:
        assert conn.execute(
            "SELECT count(*) FROM public.schema_migrations WHERE filename=%s", (MIGRATION,)
        ).fetchone()[0] == 1
    check_source = inspect.getsource(privacy_entitled_plan.check_schema_ready).upper()
    assert "CREATE TABLE" not in check_source
    assert "ALTER TABLE" not in check_source
    assert "DROP TABLE" not in check_source
    privacy_entitled_plan.check_schema_ready()


def test_entitlement_expiring_during_inspection_rolls_back_without_claiming_active(context, monkeypatch):
    c = context
    path = _path(c)
    assert c["client"].post(path, headers=c["headers"]).status_code == 200
    # Initial membership/entitlement passes. The inspector then runs past
    # the real DB deadline while transaction-start CURRENT_TIMESTAMP remains old.
    with psycopg.connect(c["url"]) as conn:
        conn.execute("""
            UPDATE access.entitlements
            SET active_until=clock_timestamp() + INTERVAL '650 milliseconds'
            WHERE id=%s
        """, (c["entitlement"],))
    inspected = []
    def slow_inspection(url):
        inspected.append(url)
        time.sleep(0.85)
        return {**c["snapshot"], "score": 87}
    monkeypatch.setattr(privacy_entitled_plan, "diagnose_privacy_url", slow_inspection)
    refused = c["client"].post(path + "/check", headers=c["headers"])
    assert refused.status_code == 403, refused.text
    assert len(inspected) == 1
    with psycopg.connect(c["url"]) as conn:
        assert conn.execute(
            "SELECT count(*) FROM privacy.diagnostic WHERE workspace_site_id=%s",
            (c["site"],),
        ).fetchone()[0] == 1
        assert conn.execute("""
            SELECT count(*) FROM privacy.entitled_plan_check
            WHERE entitled_plan_id IN (SELECT id FROM privacy.entitled_plan WHERE workspace_site_id=%s)
        """, (c["site"],)).fetchone()[0] == 0


@pytest.mark.parametrize(
    "value, expected",
    [
        ("https://example.test/privacy?key=secret#section", "https://example.test/privacy"),
        ("http://example.test/a/b?token=private", "http://example.test/a/b"),
        ("javascript:alert(1)", None),
        ("https://user:password@example.test/policy", None),
        ("/policy", None),
        (None, None),
    ],
)
def test_c2_public_source_url_drops_unsafe_links_and_sensitive_queries(value, expected):
    assert privacy_entitled_plan._public_source_url(value) == expected


def test_c2_projection_is_public_read_only_and_uses_real_control_metadata():
    snapshot = {
        "score": 47, "framework_version": "0.11", "scoring_version": "0.11",
        "scope": {"pages_analyzed": 2, "limited": False, "debug_secret": "private"},
        "internal_diagnostic": {"api_key": "private"},
        "controls": [
            {
                "control_code": "PRV-001", "result": "not_detected",
                "reason": "No se encontró una política visible.",
                "confidence": "high", "evidence_summary": "No hay enlace de privacidad.",
                "source_url": "https://example.test/?session=private",
                "evidence": [{"secret": "should-never-leave-server"}],
                "debug": {"credentials": "private"},
            },
            {
                "control_code": "PRV-501", "result": "detected",
                "source_url": "https://example.test/",
                "evidence": ["private evidence detail"],
            },
            {"control_code": "PRV-FUTURE", "result": "not_evaluable"},
        ],
    }
    when = datetime(2026, 10, 28, tzinfo=timezone.utc)
    result = privacy_entitled_plan._diagnostic_view(snapshot, when, source="review")
    assert result["created_at"] == when
    assert result["score"] == 47
    assert result["scope"] == {"pages_analyzed": 2, "limited": False}
    assert result["controls"][0] == {
        "control_code": "PRV-001",
        "name": "Política de privacidad visible", "area": "Transparencia",
        "type": "evaluation", "result": "not_detected",
        "reason": "No se encontró una política visible.",
        "confidence": "high", "evidence_summary": "No hay enlace de privacidad.",
        "source_url": "https://example.test/",
    }
    assert result["controls"][1]["area"] == "Seguridad"
    assert result["controls"][2]["area"] is None
    assert result["controls"][2]["name"] == "PRV-FUTURE"
    assert "private" not in str(result)
    assert "evidence" not in result["controls"][0]


def test_c3_actions_rebuild_from_latest_review_without_mutating_baseline(context, monkeypatch):
    c = context
    path = _path(c)
    baseline = c["client"].post(path, headers=c["headers"]).json()
    assert baseline["plan"]["item_count"] == 1
    assert [item["control_code"] for item in baseline["plan"]["items"]] == ["PRV-001"]
    current = {**c["snapshot"], **diagnostic_versions(), "score": 84,
               "controls": [
                   {"control_code": "PRV-001", "result": "detected", "confidence": "high"},
                   {"control_code": "PRV-003", "result": "not_detected", "confidence": "high"},
               ]}
    monkeypatch.setattr(privacy_entitled_plan, "diagnose_privacy_url", lambda _url: current)
    check = c["client"].post(path + "/check", headers=c["headers"])
    assert check.status_code == 200, check.text
    # The original diagnostic uses an older version: score deltas are not comparable.
    assert check.json()["result"]["comparability"]["status"] == "not_comparable"
    latest = c["client"].get(path, headers=c["headers"])
    assert latest.status_code == 200, latest.text
    data = latest.json()
    assert data["plan"] == baseline["plan"]
    assert data["diagnostic"]["current"]["score"] == 84
    actions = data["current_actions"]
    assert actions["status"] == "available"
    assert actions["source"] == "review"
    assert actions["created_at"] == data["diagnostic"]["current"]["created_at"]
    assert actions["item_count"] == 1
    assert [item["control_code"] for item in actions["items"]] == ["PRV-003"]
    assert actions["items"][0]["action_steps"]
    assert actions["items"][0]["validation_step"]
    assert actions["verification_pending"] == []
    with psycopg.connect(c["url"]) as conn:
        assert conn.execute(
            "SELECT plan_snapshot FROM privacy.entitled_plan WHERE id=%s",
            (baseline["id"],),
        ).fetchone()[0] == baseline["plan"]


def test_c3_uncertain_findings_are_not_counted_as_corrected_or_actionable(context, monkeypatch):
    c = context
    path = _path(c)
    first = c["client"].post(path, headers=c["headers"]).json()
    versions = diagnostic_versions()
    followup = {**c["snapshot"], **versions, "score": 75,
                "controls": [
                    {"control_code": "PRV-001", "result": "not_evaluable", "confidence": "low"},
                    {"control_code": "PRV-003", "result": "not_detected", "confidence": "high"},
                ]}
    monkeypatch.setattr(privacy_entitled_plan, "diagnose_privacy_url", lambda _: followup)
    assert c["client"].post(path + "/check", headers=c["headers"]).status_code == 200
    actions = c["client"].get(path, headers=c["headers"]).json()["current_actions"]
    assert actions["status"] == "available"
    assert [item["control_code"] for item in actions["items"]] == ["PRV-003"]
    assert actions["verification_pending_count"] == 1
    assert actions["verification_pending"] == [{
        "control_code": "PRV-001", "name": "Política de privacidad visible",
        "status": "pending_verification", "reason": "not_evaluable",
    }]
    assert all(item["control_code"] != "PRV-001" for item in actions["items"])
    assert first["plan"]["item_count"] == 1
    # A second valid review replaces the first active plan, not its baseline.
    followup["controls"] = [
        {"control_code": "PRV-001", "result": "detected", "confidence": "high"},
        {"control_code": "PRV-003", "result": "detected", "confidence": "high"},
    ]
    assert c["client"].post(path + "/check", headers=c["headers"]).status_code == 200
    latest = c["client"].get(path, headers=c["headers"]).json()
    assert latest["current_actions"]["item_count"] == 0
    assert latest["current_actions"]["verification_pending_count"] == 0
    assert latest["plan"] == first["plan"]


def test_c3_unknown_or_nonapplicable_baseline_control_requires_verification():
    versions = diagnostic_versions()
    initial = {
        "item_count": 1, "items": [{"control_code": "PRV-001", "name": "Original"}],
        "actions_version": "2",
    }
    at = datetime(2026, 10, 28, tzinfo=timezone.utc)
    snapshot = {**versions, "score": 78, "controls": [
        {"control_code": "PRV-001", "result": "not_applicable"},
    ]}
    result = privacy_entitled_plan._current_actions(initial, snapshot, at, source="review")
    assert result["item_count"] == 0
    assert result["verification_pending_count"] == 1
    assert result["verification_pending"][0]["reason"] == "not_applicable"
    snapshot["controls"] = []
    result = privacy_entitled_plan._current_actions(initial, snapshot, at, source="review")
    assert result["verification_pending"][0]["reason"] == "missing"


def test_c3_version_mismatch_never_claims_zero_pending_or_generates_actions():
    versions = diagnostic_versions()
    initial = {"item_count": 2, "items": [
        {"control_code": "PRV-001"}, {"control_code": "PRV-003"},
    ], "actions_version": "2"}
    at = datetime(2026, 10, 28, tzinfo=timezone.utc)
    current = {**versions, "framework_version": "unrecognized-version",
               "score": 95, "controls": [
                   {"control_code": "PRV-001", "result": "detected"},
                   {"control_code": "PRV-003", "result": "not_detected"},
               ]}
    result = privacy_entitled_plan._current_actions(initial, current, at, source="review")
    assert result["status"] == "version_mismatch"
    assert result["source"] == "review"
    assert result["item_count"] is None
    assert result["items"] == []
    assert result["verification_pending_count"] is None
    assert result["actions_version"] is None
    assert initial["item_count"] == 2


def test_c3_no_review_retains_immutable_initial_plan_even_when_versions_are_old():
    initial = {"item_count": 1, "items": [{
        "control_code": "PRV-001", "name": "Historical wording",
        "action_steps": ["Old approved advice"], "validation_step": "Check again",
    }], "actions_version": "1"}
    snapshot = {"framework_version": "old", "scoring_version": "old",
                "score": 35, "controls": [
                    {"control_code": "PRV-001", "result": "not_detected"},
                ]}
    at = datetime(2026, 10, 28, tzinfo=timezone.utc)
    result = privacy_entitled_plan._current_actions(initial, snapshot, at, source="initial")
    assert result["status"] == "available"
    assert result["items"] == initial["items"]
    assert result["items"][0]["action_steps"] == ["Old approved advice"]
    assert result["actions_version"] == "1"
    assert result["created_at"] == at

def test_c3_new_issue_persists_across_nonapplicable_and_missing_reviews(context, monkeypatch):
    """B1: good initially, new finding, non-applicable/missing, confirmed correction."""
    c = context
    path = _path(c)
    original = {**c["snapshot"], "controls": [
        {"control_code": "PRV-001", "result": "not_detected", "confidence": "high"},
        {"control_code": "PRV-003", "result": "detected", "confidence": "high"},
    ]}
    with psycopg.connect(c["url"]) as conn:
        conn.execute(
            "UPDATE privacy.diagnostic SET diagnostic_snapshot=%s WHERE id=%s",
            (Jsonb(original), c["original"]),
        )
    baseline = c["client"].post(path, headers=c["headers"]).json()
    assert [item["control_code"] for item in baseline["plan"]["items"]] == ["PRV-001"]
    current = {**c["snapshot"], **diagnostic_versions(), "score": 80, "controls": [
        {"control_code": "PRV-001", "result": "detected", "confidence": "high"},
        {"control_code": "PRV-003", "result": "not_detected", "confidence": "high"},
    ]}
    monkeypatch.setattr(privacy_entitled_plan, "diagnose_privacy_url", lambda _: current)

    assert c["client"].post(path + "/check", headers=c["headers"]).status_code == 200
    first = c["client"].get(path, headers=c["headers"]).json()
    assert [i["control_code"] for i in first["current_actions"]["items"]] == ["PRV-003"]
    assert first["current_actions"]["verification_pending_count"] == 0

    current["controls"] = [
        {"control_code": "PRV-001", "result": "detected"},
        {"control_code": "PRV-003", "result": "not_applicable"},
    ]
    assert c["client"].post(path + "/check", headers=c["headers"]).status_code == 200
    second = c["client"].get(path, headers=c["headers"]).json()
    assert second["current_actions"]["item_count"] == 0
    assert second["current_actions"]["verification_pending_count"] == 1
    assert [(i["control_code"], i["reason"]) for i in second["current_actions"]["verification_pending"]] == [
        ("PRV-003", "not_applicable"),
    ]

    current["controls"] = [{"control_code": "PRV-001", "result": "detected"}]
    assert c["client"].post(path + "/check", headers=c["headers"]).status_code == 200
    third = c["client"].get(path, headers=c["headers"]).json()
    assert third["current_actions"]["item_count"] == 0
    assert third["current_actions"]["verification_pending_count"] == 1
    assert [(i["control_code"], i["reason"]) for i in third["current_actions"]["verification_pending"]] == [
        ("PRV-003", "missing"),
    ]

    current["controls"] = [
        {"control_code": "PRV-001", "result": "detected"},
        {"control_code": "PRV-003", "result": "detected"},
    ]
    assert c["client"].post(path + "/check", headers=c["headers"]).status_code == 200
    final = c["client"].get(path, headers=c["headers"]).json()
    assert final["current_actions"]["item_count"] == 0
    assert final["current_actions"]["verification_pending_count"] == 0
    assert final["plan"] == baseline["plan"]
    with psycopg.connect(c["url"]) as conn:
        assert conn.execute(
            "SELECT plan_snapshot FROM privacy.entitled_plan WHERE id=%s",
            (baseline["id"],),
        ).fetchone()[0] == baseline["plan"]


def test_c3_historical_open_findings_are_cleared_by_confirmed_detection_only():
    versions = diagnostic_versions()
    baseline = {"items": [{"control_code": "PRV-001"}]}
    def review(one, three):
        return {**versions, "score": 80, "controls": [
            {"control_code": "PRV-001", "result": one, "confidence": "high"},
            {"control_code": "PRV-003", "result": three, "confidence": "high"},
        ]}
    prior = [
        review("detected", "not_detected"),
        review("not_applicable", "not_applicable"),
        review("not_evaluable", "not_evaluable"),
    ]
    assert privacy_entitled_plan._prior_unresolved_actions(baseline, prior) == {"PRV-003"}
    prior.append(review("detected", "detected"))
    assert privacy_entitled_plan._prior_unresolved_actions(baseline, prior) == set()
    prior.append({**versions, "score": 80, "controls": []})
    assert privacy_entitled_plan._prior_unresolved_actions(baseline, prior) == set()

def test_c4a_previous_comparison_rejects_indeterminate_as_improvement():
    versions = diagnostic_versions()
    before = {**versions, "score": 47, "controls": [
        {"control_code": "PRV-003", "result": "not_detected"}]}
    unknown = {**versions, "score": 47, "controls": [
        {"control_code": "PRV-003", "result": "not_evaluable"}]}
    result = privacy_entitled_plan._compare_review_states(before, unknown)
    assert result["score_change"] == 0
    assert result["changes"] == [{
        "control_code": "PRV-003", "previous": "not_detected",
        "current": "not_evaluable", "status": "not_conclusive",
    }]


def test_c4a_previous_comparison_version_mismatch():
    versions = diagnostic_versions()
    before = {**versions, "score": 47, "controls": []}
    after = {**before, "framework_version": "unrelated-framework", "score": 65}
    result = privacy_entitled_plan._compare_review_states(before, after)
    assert result["score_change"] is None
    assert result["changes"] == []


def test_c4a_history_integrates_multiple_reviews_order_comparisons_and_access(context, monkeypatch):
    """Real PostgreSQL/API history is scoped to a live authorized Plan."""
    c = context
    path = _path(c)
    versions = diagnostic_versions()
    baseline = {**c["snapshot"], **versions, "score": 47, "controls": [
        {"control_code": "PRV-001", "result": "not_detected",
         "confidence": "high", "evidence": [{"secret": "initial-private"}]},
    ]}
    with psycopg.connect(c["url"]) as conn:
        conn.execute("UPDATE privacy.diagnostic SET diagnostic_snapshot=%s,score=%s WHERE id=%s",
                     (Jsonb(baseline), 47, c["original"]))
    started = c["client"].post(path, headers=c["headers"])
    assert started.status_code == 200, started.text
    initial = started.json()["history"]
    assert len(initial) == 1 and initial[0]["kind"] == "initial"
    assert initial[0]["diagnostic"]["score"] == 47
    assert initial[0]["vs_initial"] is None and initial[0]["vs_previous"] is None

    reviews = [
        {**baseline, "score": 62, "controls": [
            {"control_code": "PRV-001", "result": "detected", "confidence": "high",
             "evidence": [{"secret": "first-private"}]}]},
        {**baseline, "score": 62, "controls": [
            {"control_code": "PRV-001", "result": "not_evaluable", "confidence": "low"}]},
        {**baseline, "score": 47, "controls": [
            {"control_code": "PRV-001", "result": "not_detected", "confidence": "high"}]},
    ]
    pending = iter(reviews)
    monkeypatch.setattr(privacy_entitled_plan, "diagnose_privacy_url",
                        lambda _: next(pending))
    for _ in reviews:
        response = c["client"].post(path + "/check", headers=c["headers"])
        assert response.status_code == 200, response.text

    response = c["client"].get(path, headers=c["headers"])
    assert response.status_code == 200, response.text
    data = response.json()
    history = data["history"]
    assert [entry["kind"] for entry in history] == ["review", "review", "review", "initial"]
    assert [entry["diagnostic"]["score"] for entry in history] == [47, 62, 62, 47]
    assert [entry["diagnostic"]["controls"][0]["result"] for entry in history] == [
        "not_detected", "not_evaluable", "detected", "not_detected",
    ]
    # Last-to-first ordering is based on saved DB check order, including tied timestamps.
    with psycopg.connect(c["url"]) as conn:
        timestamps = conn.execute("""
            SELECT d.created_at FROM privacy.entitled_plan_check ch
            JOIN privacy.diagnostic d ON d.id=ch.check_diagnostic_id
            WHERE ch.entitled_plan_id=%s
            ORDER BY ch.created_at DESC,ch.id DESC
        """, (data["id"],)).fetchall()
    assert [entry["created_at"] for entry in history[:3]] == [
        row[0].isoformat() for row in timestamps]
    assert history[0]["vs_initial"]["score_change"] == 0
    assert history[0]["vs_previous"]["score_change"] == -15
    # The intermediate uncertain review is never treated as a correction.
    assert history[1]["vs_previous"]["changes"][0]["status"] == "not_conclusive"
    assert history[2]["vs_previous"]["changes"][0]["status"] == "improved"
    assert history[3]["vs_previous"] is None
    assert data["check"]["latest_check"]["result"]["current_score"] == 47
    assert "secret" not in str(history)

    foreign = access.StoredUser(id=c["foreign"], email="foreign@example.test")
    monkeypatch.setattr(access, "get_or_create_user", lambda _: foreign)
    assert c["client"].get(path, headers=c["headers"]).status_code == 403
    monkeypatch.setattr(access, "get_or_create_user", lambda _: c["user"])
    with psycopg.connect(c["url"]) as conn:
        conn.execute("UPDATE access.entitlements SET status='revoked' WHERE id=%s",
                     (c["entitlement"],))
    assert c["client"].get(path, headers=c["headers"]).status_code == 403


def test_c4a_history_does_not_connect_incompatible_versions(context, monkeypatch):
    c = context
    path = _path(c)
    versions = diagnostic_versions()
    original = {**c["snapshot"], **versions, "score": 47}
    with psycopg.connect(c["url"]) as conn:
        conn.execute("UPDATE privacy.diagnostic SET diagnostic_snapshot=%s,score=47 WHERE id=%s",
                     (Jsonb(original), c["original"]))
    assert c["client"].post(path, headers=c["headers"]).status_code == 200
    incompatible = {**original, "framework_version": "future-version", "score": 70}
    monkeypatch.setattr(privacy_entitled_plan, "diagnose_privacy_url", lambda _: incompatible)
    assert c["client"].post(path + "/check", headers=c["headers"]).status_code == 200
    history = c["client"].get(path, headers=c["headers"]).json()["history"]
    assert len(history) == 2
    for comparison in (history[0]["vs_initial"], history[0]["vs_previous"]):
        assert comparison["comparability"]["status"] == "not_comparable"
        assert comparison["score_change"] is None
    assert history[0]["vs_previous"]["changes"] == []


@pytest.mark.parametrize("old,new,expected", [
    ("not_detected", "partial", "improved"),
    ("partial", "detected", "improved"),
    ("not_detected", "detected", "improved"),
    ("detected", "partial", "regressed"),
    ("partial", "not_detected", "regressed"),
    ("detected", "not_detected", "regressed"),
])
def test_c4a_partial_transitions_follow_ordered_evidence(old, new, expected):
    versions = diagnostic_versions()
    before = {**versions, "score": 47, "controls": [
        {"control_code": "PRV-003", "result": old}]}
    after = {**versions, "score": 47, "controls": [
        {"control_code": "PRV-003", "result": new}]}
    result = privacy_entitled_plan._compare_review_states(before, after)
    assert result["changes"] == [{
        "control_code": "PRV-003", "previous": old,
        "current": new, "status": expected,
    }]


def test_c4a_history_includes_nonbaseline_controls_in_both_comparisons(context, monkeypatch):
    c = context
    path = _path(c)
    versions = diagnostic_versions()
    initial = {**c["snapshot"], **versions, "score": 47, "controls": [
        {"control_code": "PRV-001", "result": "not_detected"},
        {"control_code": "PRV-003", "result": "detected"},
    ]}
    with psycopg.connect(c["url"]) as conn:
        conn.execute("UPDATE privacy.diagnostic SET diagnostic_snapshot=%s, score=47 WHERE id=%s",
                     (Jsonb(initial), c["original"]))
    first = c["client"].post(path, headers=c["headers"])
    assert first.status_code == 200, first.text
    assert [item["control_code"] for item in first.json()["plan"]["items"]] == ["PRV-001"]
    reviews = iter([
        {**initial, "score": 55, "controls": [
            {"control_code": "PRV-001", "result": "partial"},
            {"control_code": "PRV-003", "result": "not_detected"},
        ]},
        {**initial, "score": 58, "controls": [
            {"control_code": "PRV-001", "result": "not_evaluable"},
            # PRV-003 is missing, not corrected.
        ]},
    ])
    monkeypatch.setattr(privacy_entitled_plan, "diagnose_privacy_url",
                        lambda _: next(reviews))
    for _ in range(2):
        response = c["client"].post(path + "/check", headers=c["headers"])
        assert response.status_code == 200, response.text
    history = c["client"].get(path, headers=c["headers"]).json()["history"]
    first_review, second_review = history[1], history[0]
    for field in ("vs_initial", "vs_previous"):
        changes = {item["control_code"]: item for item in first_review[field]["changes"]}
        assert changes["PRV-001"]["status"] == "improved"
        assert changes["PRV-003"]["status"] == "regressed"
    assert {item["control_code"]: item["status"] for item in second_review["vs_initial"]["changes"]} == {
        "PRV-001": "not_conclusive", "PRV-003": "not_conclusive",
    }
    assert {item["control_code"]: item["status"] for item in second_review["vs_previous"]["changes"]} == {
        "PRV-001": "not_conclusive", "PRV-003": "not_conclusive",
    }


def test_site_history_survives_three_month_gap_and_new_entitlement(context, monkeypatch):
    """Three former reviews stay visible without mutating the prior Plan."""
    c = context
    path = _path(c)
    versions = diagnostic_versions()
    baseline = {**c["snapshot"], **versions, "score": 47}
    with psycopg.connect(c["url"]) as conn:
        conn.execute(
            "UPDATE privacy.diagnostic SET diagnostic_snapshot=%s, score=47 WHERE id=%s",
            (Jsonb(baseline), c["original"]),
        )
    old = c["client"].post(path, headers=c["headers"])
    assert old.status_code == 200
    old_id = old.json()["id"]
    old_scores = iter((62, 62, 47))
    monkeypatch.setattr(
        privacy_entitled_plan, "diagnose_privacy_url",
        lambda _: {**baseline, "score": next(old_scores)},
    )
    for _ in range(3):
        assert c["client"].post(path + "/check", headers=c["headers"]).status_code == 200
    with psycopg.connect(c["url"]) as conn:
        conn.execute("""
            UPDATE access.entitlements SET active_from=now()-INTERVAL '120 days',
               active_until=now()-INTERVAL '90 days' WHERE id=%s
        """, (c["entitlement"],))
        conn.execute(
            "UPDATE privacy.diagnostic SET created_at=now()-INTERVAL '120 days' WHERE id=%s",
            (c["original"],),
        )
        conn.execute("""
            UPDATE privacy.diagnostic d SET created_at=c.created_at-INTERVAL '90 days'
            FROM privacy.entitled_plan_check c
            WHERE c.check_diagnostic_id=d.id AND c.entitled_plan_id=%s
        """, (old_id,))
        next_id = uuid4()
        conn.execute("""
            INSERT INTO access.entitlements (
                id, workspace_site_id, product_code, active_from, active_until,
                status, source, source_id
            ) VALUES (%s,%s,'privacy_web',now()-INTERVAL '1 minute',
                     now()+INTERVAL '30 days','active','internal_grant',%s)
        """, (next_id, c["site"], str(next_id)))

    current = c["client"].post(path, headers=c["headers"])
    assert current.status_code == 200, current.text
    current_id = current.json()["id"]
    assert current_id != old_id
    assert current.json()["diagnostic"]["initial"]["score"] == 47
    assert current.json()["check"]["status"] == "available"
    assert "latest_check" not in current.json()["check"]
    history = current.json()["history"]
    assert [entry["kind"] for entry in history] == ["review", "review", "review", "initial"]
    assert [entry["diagnostic"]["score"] for entry in history] == [47, 62, 62, 47]
    assert all(entry["period"] == 0 for entry in history)
    assert history[0]["vs_initial"]["score_change"] == 0
    # The last old review is reused as the new immutable baseline, not duplicated.
    with psycopg.connect(c["url"]) as conn:
        reused = conn.execute(
            "SELECT original_diagnostic_id FROM privacy.entitled_plan WHERE id=%s",
            (current_id,),
        ).fetchone()[0]
        last_old = conn.execute("""
            SELECT check_diagnostic_id FROM privacy.entitled_plan_check
            WHERE entitled_plan_id=%s ORDER BY created_at DESC,id DESC LIMIT 1
        """, (old_id,)).fetchone()[0]
        assert reused == last_old

    monkeypatch.setattr(
        privacy_entitled_plan, "diagnose_privacy_url",
        lambda _: {**baseline, "score": 70},
    )
    checked = c["client"].post(path + "/check", headers=c["headers"])
    assert checked.status_code == 200, checked.text
    after = c["client"].get(path, headers=c["headers"]).json()
    assert after["id"] == current_id
    assert after["diagnostic"]["current"]["score"] == 70
    assert after["diagnostic"]["initial"]["score"] == 47
    assert [x["diagnostic"]["score"] for x in after["history"]] == [70, 47, 62, 62, 47]
    assert [x["period"] for x in after["history"]] == [1, 0, 0, 0, 0]
    assert after["history"][0]["vs_initial"]["score_change"] == 23
    assert after["history"][0]["vs_previous"]["score_change"] == 23
    with psycopg.connect(c["url"]) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM privacy.entitled_plan_check WHERE entitled_plan_id=%s",
            (old_id,),
        ).fetchone()[0] == 3
        assert conn.execute(
            "SELECT COUNT(*) FROM privacy.entitled_plan_check WHERE entitled_plan_id=%s",
            (current_id,),
        ).fetchone()[0] == 1


def test_reactivation_with_distinct_diagnostic_has_labeled_baseline_and_version_guard(context, monkeypatch):
    c = context
    path = _path(c)
    original = {**c["snapshot"], **diagnostic_versions(), "score": 47}
    with psycopg.connect(c["url"]) as conn:
        conn.execute("UPDATE privacy.diagnostic SET diagnostic_snapshot=%s, score=47 WHERE id=%s",
                     (Jsonb(original), c["original"]))
    old = c["client"].post(path, headers=c["headers"])
    assert old.status_code == 200
    monkeypatch.setattr(
        privacy_entitled_plan, "diagnose_privacy_url", lambda _: {**original, "score": 65}
    )
    assert c["client"].post(path + "/check", headers=c["headers"]).status_code == 200
    with psycopg.connect(c["url"]) as conn:
        conn.execute("""
            UPDATE access.entitlements SET active_from=now()-INTERVAL '120 days',
                active_until=now()-INTERVAL '90 days' WHERE id=%s
        """, (c["entitlement"],))
        conn.execute("UPDATE privacy.diagnostic SET created_at=now()-INTERVAL '120 days' WHERE id=%s",
                     (c["original"],))
        conn.execute("""
            UPDATE privacy.diagnostic d SET created_at=c.created_at-INTERVAL '90 days'
            FROM privacy.entitled_plan_check c WHERE c.check_diagnostic_id=d.id
              AND c.entitled_plan_id=%s
        """, (old.json()["id"],))
    # A genuinely new diagnostic taken at reactivation is not the same event
    # as the last review from the former period; show it explicitly.
    new_snapshot = {**original, "framework_version": "future-incompatible", "score": 74}
    privacy_diagnostic_snapshot.create_diagnostic_snapshot(
        new_snapshot, workspace_site_id=c["site"], requested_url=original["site_url"]
    )
    next_id = uuid4()
    with psycopg.connect(c["url"]) as conn:
        conn.execute("""
            INSERT INTO access.entitlements (
                id, workspace_site_id, product_code, active_from, active_until,
                status, source, source_id
            ) VALUES (%s,%s,'privacy_web',now()-INTERVAL '1 minute',
                     now()+INTERVAL '30 days','active','internal_grant',%s)
        """, (next_id, c["site"], str(next_id)))
    result = c["client"].post(path, headers=c["headers"])
    assert result.status_code == 200, result.text
    history = result.json()["history"]
    assert [item["kind"] for item in history] == ["baseline", "review", "initial"]
    assert [item["period"] for item in history] == [1, 0, 0]
    assert [item["diagnostic"]["score"] for item in history] == [74, 65, 47]
    assert history[0]["vs_previous"]["comparability"]["status"] == "not_comparable"
    assert history[0]["vs_initial"]["score_change"] is None
    # Revoking previous access must not let its evidence leak to another site;
    # same-site history still belongs to the currently authorized workspace.
    with psycopg.connect(c["url"]) as conn:
        conn.execute("UPDATE access.entitlements SET status='revoked' WHERE id=%s",
                     (c["entitlement"],))
    assert len(c["client"].get(path, headers=c["headers"]).json()["history"]) == 3
    # Without a live entitlement the history cannot be accessed.
    with psycopg.connect(c["url"]) as conn:
        conn.execute("UPDATE access.entitlements SET status='revoked' WHERE id=%s", (next_id,))
    assert c["client"].get(path, headers=c["headers"]).status_code == 403


def test_site_history_never_crosses_workspaces_for_the_same_hostname(context, monkeypatch):
    c = context
    path = _path(c)
    assert c["client"].post(path, headers=c["headers"]).status_code == 200
    other_workspace, other_link, other_entitlement = (uuid4() for _ in range(3))
    with psycopg.connect(c["url"]) as conn:
        shared_site = conn.execute(
            "SELECT site_id FROM access.workspace_sites WHERE id=%s", (c["site"],)
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO access.workspaces(id,name) VALUES (%s,'Separate workspace')",
            (other_workspace,),
        )
        conn.execute(
            "INSERT INTO access.workspace_members(workspace_id,user_id,role) VALUES (%s,%s,'owner')",
            (other_workspace, c["foreign"]),
        )
        conn.execute(
            "INSERT INTO access.workspace_sites(id,workspace_id,site_id) VALUES (%s,%s,%s)",
            (other_link, other_workspace, shared_site),
        )
        conn.execute("""
            INSERT INTO access.entitlements (
              id, workspace_site_id, product_code, active_from, active_until,
              status, source, source_id
            ) VALUES (%s,%s,'privacy_web',now()-INTERVAL '1 minute',
                      now()+INTERVAL '30 days','active','internal_grant',%s)
        """, (other_entitlement, other_link, str(other_entitlement)))
    try:
        privacy_diagnostic_snapshot.create_diagnostic_snapshot(
            {**c["snapshot"], "score": 93}, workspace_site_id=other_link,
            requested_url=c["snapshot"]["site_url"],
        )
        original_user = c["user"]
        second_user = access.StoredUser(id=c["foreign"], email="foreign@example.test")
        monkeypatch.setattr(access, "get_or_create_user", lambda _: second_user)
        other_path = f"/privacy/workspace-sites/{other_link}/plan"
        other_plan = c["client"].post(other_path, headers=c["headers"])
        assert other_plan.status_code == 200, other_plan.text
        assert [i["diagnostic"]["score"] for i in other_plan.json()["history"]] == [93]
        assert c["client"].get(path, headers=c["headers"]).status_code == 403
        monkeypatch.setattr(access, "get_or_create_user", lambda _: original_user)
        initial = c["client"].get(path, headers=c["headers"])
        assert initial.status_code == 200
        assert [i["diagnostic"]["score"] for i in initial.json()["history"]] == [65]
        assert c["client"].get(other_path, headers=c["headers"]).status_code == 403
    finally:
        with psycopg.connect(c["url"]) as conn:
            conn.execute("""
                DELETE FROM privacy.entitled_plan_check WHERE entitled_plan_id IN
                  (SELECT id FROM privacy.entitled_plan WHERE workspace_site_id=%s)
            """, (other_link,))
            conn.execute("DELETE FROM privacy.entitled_plan WHERE workspace_site_id=%s",
                         (other_link,))
            conn.execute("DELETE FROM privacy.diagnostic WHERE workspace_site_id=%s",
                         (other_link,))
            conn.execute("DELETE FROM access.entitlements WHERE workspace_site_id=%s",
                         (other_link,))
            conn.execute("DELETE FROM access.workspace_sites WHERE id=%s", (other_link,))
            conn.execute("DELETE FROM access.workspace_members WHERE workspace_id=%s",
                         (other_workspace,))
            conn.execute("DELETE FROM access.workspaces WHERE id=%s", (other_workspace,))
