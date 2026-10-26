"""PW-03: prepare activation without creating payments or losing saved evidence."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from mininode_api.api import privacy as api
from mininode_api.main import create_app
from mininode_api.services import access, access_identity, privacy_diagnostic_snapshot


@pytest.fixture
def prepared(monkeypatch):
    user = access.StoredUser(id=uuid4(), email="owner@example.com")
    site_id = uuid4()
    monkeypatch.setattr(
        access_identity, "verify_access_jwt",
        lambda token: access_identity.AccessIdentity(email=user.email),
    )
    monkeypatch.setattr(access, "get_or_create_user", lambda email: user)
    monkeypatch.setattr(
        access, "get_authorized_site",
        lambda user_id, target_id: SimpleNamespace(hostname="saved.example")
        if user_id == user.id and target_id == site_id else None,
    )
    app = create_app()
    app.state.access_ready = True
    app.state.privacy_diagnostic_snapshot_ready = True
    return TestClient(app), user, site_id, monkeypatch


def _stored(site_id, *, hours):
    return SimpleNamespace(
        id=uuid4(),
        workspace_site_id=site_id,
        site_url="https://saved.example/",
        diagnostic_snapshot={
            "site_url": "https://saved.example/", "score": 80, "controls": [],
            "priorities": [{"name": "Review"}],
        },
        created_at=datetime.now(timezone.utc) - timedelta(hours=2),
        purchase_expires_at=datetime.now(timezone.utc) + timedelta(hours=hours),
    )


def test_requires_identity_and_workspace_membership_before_reading_or_inspection(prepared):
    client, user, site_id, monkeypatch = prepared
    calls = []
    monkeypatch.setattr(
        privacy_diagnostic_snapshot, "get_latest_for_workspace_site",
        lambda _: calls.append("read"),
    )
    path = f"/privacy/workspace-sites/{site_id}/prepare-activation"
    assert client.post(path).status_code == 401
    assert calls == []

    monkeypatch.setattr(access, "get_authorized_site", lambda *_: None)
    assert client.post(path, headers={"Cf-Access-Jwt-Assertion": "signed-token"}).status_code == 404
    assert calls == []


def test_recent_diagnosis_reused_without_reinspection_or_order(prepared):
    client, _, site_id, monkeypatch = prepared
    saved = _stored(site_id, hours=3)
    monkeypatch.setattr(
        privacy_diagnostic_snapshot, "get_latest_for_workspace_site",
        lambda _: saved,
    )
    inspected = []
    monkeypatch.setattr(api, "diagnose_workspace_site", lambda *_: inspected.append(True))
    response = client.post(
        f"/privacy/workspace-sites/{site_id}/prepare-activation",
        headers={"Cf-Access-Jwt-Assertion": "signed-token"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["refreshed"] is False
    assert payload["diagnostic"]["diagnostic_id"] == str(saved.id)
    assert payload["diagnostic"]["workspace_site_id"] == str(site_id)
    assert payload["diagnostic"]["score"] == 80
    assert inspected == []


def test_expired_diagnosis_reinspected_and_saved_before_continuing(prepared):
    client, _, site_id, monkeypatch = prepared
    old = _stored(site_id, hours=-1)
    new_id = uuid4()
    monkeypatch.setattr(
        privacy_diagnostic_snapshot, "get_latest_for_workspace_site", lambda _: old,
    )
    calls = []
    def refresh(target, request, user):
        calls.append((target, user.id))
        return {
            "diagnostic_id": new_id,
            "purchase_expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
            "site_url": "https://saved.example/", "score": 85, "controls": [],
            "priorities": [{"name": "Review"}],
        }
    monkeypatch.setattr(api, "diagnose_workspace_site", refresh)
    response = client.post(
        f"/privacy/workspace-sites/{site_id}/prepare-activation",
        headers={"Cf-Access-Jwt-Assertion": "signed-token"},
    )
    assert response.status_code == 200
    assert response.json()["refreshed"] is True
    assert response.json()["diagnostic"]["diagnostic_id"] == str(new_id)
    assert response.json()["diagnostic"]["workspace_site_id"] == str(site_id)
    assert len(calls) == 1


@pytest.mark.parametrize("refresh", [
    lambda: JSONResponse(status_code=503, content={"error": "inspection_failed"}),
    lambda: {"score": 85, "site_url": "https://saved.example/"},
])
def test_refresh_failure_never_returns_a_purchasable_diagnosis(prepared, refresh):
    client, _, site_id, monkeypatch = prepared
    monkeypatch.setattr(
        privacy_diagnostic_snapshot, "get_latest_for_workspace_site",
        lambda _: _stored(site_id, hours=-1),
    )
    monkeypatch.setattr(api, "diagnose_workspace_site", lambda *_: refresh())
    response = client.post(
        f"/privacy/workspace-sites/{site_id}/prepare-activation",
        headers={"Cf-Access-Jwt-Assertion": "signed-token"},
    )
    assert response.status_code == 503
    assert "diagnostic" not in response.json()


def test_site_without_saved_diagnosis_requires_new_diagnosis(prepared):
    client, _, site_id, monkeypatch = prepared
    def missing(_):
        raise privacy_diagnostic_snapshot.PrivacyDiagnosticSnapshotNotFoundError("missing")
    monkeypatch.setattr(
        privacy_diagnostic_snapshot, "get_latest_for_workspace_site", missing,
    )
    response = client.post(
        f"/privacy/workspace-sites/{site_id}/prepare-activation",
        headers={"Cf-Access-Jwt-Assertion": "signed-token"},
    )
    assert response.status_code == 409
