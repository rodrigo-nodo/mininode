import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.api import privacy as privacy_api  # noqa: E402
from mininode_api.services import access_identity  # noqa: E402
from mininode_api.main import create_app  # noqa: E402
from mininode_api.services import access  # noqa: E402


def _client(monkeypatch):
    user = access.StoredUser(id=uuid4(), email="owner@example.com")
    monkeypatch.setattr(
        access_identity,
        "verify_access_jwt",
        lambda token: access_identity.AccessIdentity(email=user.email),
    )
    monkeypatch.setattr(access, "get_or_create_user", lambda email: user)
    app = create_app()
    app.state.access_ready = True
    app.state.privacy_diagnostic_snapshot_ready = True
    return TestClient(app), user


def test_foreign_workspace_site_is_rejected_before_inspection(monkeypatch):
    client, user = _client(monkeypatch)
    workspace_site_id = uuid4()
    monkeypatch.setattr(access, "get_authorized_site", lambda user_id, site_id: None)
    calls = []
    monkeypatch.setattr(privacy_api, "diagnose_privacy_url", lambda url: calls.append(url))

    response = client.post(
        f"/privacy/workspace-sites/{workspace_site_id}/diagnose",
        headers={"Cf-Access-Jwt-Assertion": "signed-token"},
    )

    assert response.status_code == 404
    assert calls == []


def test_authenticated_diagnosis_uses_stored_url_and_links_snapshot(monkeypatch):
    client, user = _client(monkeypatch)
    workspace_site_id = uuid4()
    authorized = access.AuthorizedSite(
        workspace_site_id=workspace_site_id,
        site_id=uuid4(),
        company_id=None,
        workspace_id=uuid4(),
        role="owner",
        hostname="stored.example",
        canonical_url="https://stored.example",
    )
    monkeypatch.setattr(
        access,
        "get_authorized_site",
        lambda user_id, site_id: authorized
        if user_id == user.id and site_id == workspace_site_id
        else None,
    )
    inspected = []
    diagnostic = {"site_url": "https://stored.example/", "score": 88}
    monkeypatch.setattr(
        privacy_api,
        "diagnose_privacy_url",
        lambda url: inspected.append(url) or diagnostic,
    )
    stored_id = uuid4()
    persisted = []

    def store(result, *, workspace_site_id=None):
        persisted.append((result, workspace_site_id))
        return SimpleNamespace(
            id=stored_id,
            purchase_expires_at="2026-09-30T00:00:00Z",
        )

    monkeypatch.setattr(
        privacy_api.privacy_diagnostic_snapshot,
        "create_diagnostic_snapshot",
        store,
    )

    response = client.post(
        f"/privacy/workspace-sites/{workspace_site_id}/diagnose",
        json={"url": "https://attacker.example"},
        headers={"Cf-Access-Jwt-Assertion": "signed-token"},
    )

    assert response.status_code == 200
    assert inspected == ["https://stored.example"]
    assert persisted == [(diagnostic, workspace_site_id)]
    assert response.json()["diagnostic_id"] == str(stored_id)
