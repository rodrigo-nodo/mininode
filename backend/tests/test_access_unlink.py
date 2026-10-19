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
