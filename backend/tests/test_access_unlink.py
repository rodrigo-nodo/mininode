"""Unlink must be workspace-scoped and non-destructive."""
from contextlib import contextmanager
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from mininode_api.main import create_app
from mininode_api.services import access, access_identity


@pytest.fixture
def client(monkeypatch):
    uid = uuid4()
    monkeypatch.setattr(access_identity, "verify_access_jwt", lambda token: access_identity.AccessIdentity(email="owner@example.com"))
    monkeypatch.setattr(access, "get_or_create_user", lambda email: access.StoredUser(id=uid, email=email))
    app = create_app()
    app.state.access_ready = True
    return TestClient(app), uid


def test_unlink_endpoint_authorized_and_not_found(client, monkeypatch):
    http, uid = client
    workspace, site = uuid4(), uuid4()
    calls = []
    def unlink(user, ws, sid):
        calls.append((user, ws, sid))
        return True
    monkeypatch.setattr(access, "unlink_workspace_site", unlink)
    response = http.delete(f"/access/workspaces/{workspace}/sites/{site}", headers={"Cf-Access-Jwt-Assertion": "valid"})
    assert response.status_code == 204
    assert calls == [(uid, workspace, site)]
    monkeypatch.setattr(access, "unlink_workspace_site", lambda *a: False)
    assert http.delete(f"/access/workspaces/{workspace}/sites/{site}", headers={"Cf-Access-Jwt-Assertion": "valid"}).status_code == 404


def test_unlink_requires_identity_and_blocks_active_contract(client, monkeypatch):
    http, _ = client
    url = f"/access/workspaces/{uuid4()}/sites/{uuid4()}"
    assert http.delete(url).status_code == 401
    def block(*args):
        raise access.ActiveSiteCannotBeUnlinked()
    monkeypatch.setattr(access, "unlink_workspace_site", block)
    response = http.delete(url, headers={"Cf-Access-Jwt-Assertion": "valid"})
    assert response.status_code == 409


def test_unlink_never_deletes_workspace_sites_or_snapshots():
    import inspect
    sql = inspect.getsource(access.unlink_workspace_site)
    assert "FOR UPDATE OF ws" in sql
    assert "ws.workspace_id = %s" in sql and "wm.user_id = %s" in sql
    assert "status IN ('pending', 'paid')" in sql
    assert "active_until" in sql
    assert "SET detached_at = CURRENT_TIMESTAMP" in sql
    assert "DELETE FROM" not in sql


def test_reassociation_clears_detached_flag():
    import inspect
    assert "detached_at = NULL" in inspect.getsource(access.follow_site)
    assert "ws.detached_at IS NULL" in inspect.getsource(access.get_authorized_site)
    assert "ws.detached_at IS NULL" in inspect.getsource(access.list_authorized_context)


def test_unlink_persists_snapshots_and_does_not_touch_other_workspace():
    import os
    import psycopg
    from mininode_api.services import billing, privacy_diagnostic_snapshot as snapshots

    url = os.environ.get("DATABASE_URL", "")
    if "mininode_test" not in url:
        pytest.skip("Real database mutation tests require disposable mininode_test")

    access.initialize_database()
    snapshots.initialize_database()
    billing.initialize_database()
    user_a, user_b, workspace_a, workspace_b, site_id = [uuid4() for _ in range(5)]
    ws_a, ws_b = uuid4(), uuid4()
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO access.users (id,email) VALUES (%s,%s),(%s,%s)",
                        (user_a, f"{user_a}@example.test", user_b, f"{user_b}@example.test"))
            cur.execute("INSERT INTO access.workspaces (id,name) VALUES (%s,'A'),(%s,'B')",
                        (workspace_a, workspace_b))
            cur.execute("INSERT INTO access.workspace_members (workspace_id,user_id,role) VALUES (%s,%s,'owner'),(%s,%s,'owner')",
                        (workspace_a,user_a,workspace_b,user_b))
            cur.execute("INSERT INTO access.sites(id,hostname) VALUES (%s,%s)",
                        (site_id, f"unlink-{site_id}.example"))
            cur.execute("INSERT INTO access.workspace_sites(id,workspace_id,site_id) VALUES (%s,%s,%s),(%s,%s,%s)",
                        (ws_a,workspace_a,site_id,ws_b,workspace_b,site_id))
    diagnostic = snapshots.create_diagnostic_snapshot(
        {"site_url": f"https://unlink-{site_id}.example/", "score": 44},
        workspace_site_id=ws_a,
    )
    try:
        assert access.unlink_workspace_site(user_b, workspace_a, ws_a) is False
        assert access.unlink_workspace_site(user_a, workspace_a, ws_a) is True
        assert access.unlink_workspace_site(user_a, workspace_a, ws_a) is False
        assert access.get_authorized_site(user_a, ws_a) is None
        assert access.get_authorized_site(user_b, ws_b) is not None
        assert snapshots.get_diagnostic_snapshot(diagnostic.id).workspace_site_id == ws_a
        assert all(s.id != ws_a for w in access.list_authorized_context(user_a) for s in w.sites)
        assert snapshots.list_latest_for_workspace(workspace_a) == ()
        with psycopg.connect(url) as conn:
            row = conn.execute("SELECT detached_at FROM access.workspace_sites WHERE id = %s", (ws_a,)).fetchone()
            assert row[0] is not None
    finally:
        with psycopg.connect(url) as conn:
            conn.execute("DELETE FROM privacy.diagnostic WHERE id = %s", (diagnostic.id,))
            conn.execute("DELETE FROM access.workspace_sites WHERE id IN (%s,%s)", (ws_a,ws_b))
            conn.execute("DELETE FROM access.sites WHERE id = %s", (site_id,))
            conn.execute("DELETE FROM access.workspace_members WHERE workspace_id IN (%s,%s)", (workspace_a,workspace_b))
            conn.execute("DELETE FROM access.workspaces WHERE id IN (%s,%s)", (workspace_a,workspace_b))
            conn.execute("DELETE FROM access.users WHERE id IN (%s,%s)", (user_a,user_b))
