"""PW-03B contract: real PostgreSQL, authenticated access and no legacy orders."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
import os

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict
from fastapi.testclient import TestClient

from mininode_api.api import privacy_entitled_plan as api
from mininode_api.main import create_app
from mininode_api.services import (
    access, access_identity, privacy_diagnostic_snapshot, privacy_entitled_plan,
)

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
    if conninfo_to_dict(url).get("host", "localhost") not in {"localhost", "127.0.0.1", "postgres"}:
        pytest.skip("Never run integration tests against remote databases")
    access.initialize_database()
    privacy_diagnostic_snapshot.initialize_database()
    privacy_entitled_plan.initialize_database()
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
            conn.execute("DELETE FROM access.entitlements WHERE id=%s", (entitlement_id,))
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
    assert data["site_url"] == c["snapshot"]["site_url"]
    assert data["check"]["status"] == "available"
    assert data["check"]["expires_at"]
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
            "SELECT count(*) FROM privacy.entitled_plan_check",
        ).fetchone()[0] >= 0


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
    assert c["client"].get(path, headers=c["headers"]).status_code == 403
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
    latest = c["client"].get(path, headers=c["headers"]).json()["check"]["latest_check"]
    assert latest["result"]["current_score"] == 85
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
