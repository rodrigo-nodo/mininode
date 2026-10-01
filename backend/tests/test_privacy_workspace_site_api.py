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


def test_workspace_url_diagnosis_rejects_foreign_workspace_before_inspection(monkeypatch):
    client, user = _client(monkeypatch)
    workspace_id = uuid4()
    monkeypatch.setattr(access, "list_authorized_context", lambda user_id: ())
    calls = []
    monkeypatch.setattr(privacy_api, "diagnose_privacy_url", lambda url: calls.append(url))

    response = client.post(
        f"/privacy/workspaces/{workspace_id}/diagnose",
        json={"url": "https://example.com"},
        headers={"Cf-Access-Jwt-Assertion": "signed-token"},
    )

    assert response.status_code == 404
    assert calls == []


def test_workspace_url_diagnosis_associates_site_after_success_and_links_snapshot(monkeypatch):
    client, user = _client(monkeypatch)
    workspace_id = uuid4()
    workspace_site_id = uuid4()
    site_id = uuid4()
    monkeypatch.setattr(
        access,
        "list_authorized_context",
        lambda user_id: (
            access.WorkspaceContext(
                id=workspace_id,
                name="Mi espacio",
                role=access.ROLE_OWNER,
                sites=(),
            ),
        ) if user_id == user.id else (),
    )
    monkeypatch.setattr(access, "normalize_site_url", lambda url: ("example.com", "https://example.com"))
    events = []
    diagnostic = {"site_url": "https://example.com/", "score": 91}
    monkeypatch.setattr(
        privacy_api,
        "diagnose_privacy_url",
        lambda url: events.append(("diagnose", url)) or diagnostic,
    )
    followed = access.SiteContext(
        id=workspace_site_id,
        site_id=site_id,
        hostname="example.com",
        company_id=None,
        company_name=None,
    )
    monkeypatch.setattr(
        access,
        "follow_site",
        lambda user_id, resolved_workspace_id, url: events.append(
            ("follow", user_id, resolved_workspace_id, url)
        ) or followed,
    )
    stored_id = uuid4()
    persisted = []

    def store(result, *, workspace_site_id=None):
        persisted.append((result, workspace_site_id))
        return SimpleNamespace(id=stored_id, purchase_expires_at="2026-10-02T00:00:00Z")

    monkeypatch.setattr(
        privacy_api.privacy_diagnostic_snapshot,
        "create_diagnostic_snapshot",
        store,
    )

    response = client.post(
        f"/privacy/workspaces/{workspace_id}/diagnose",
        json={"url": "https://example.com/path"},
        headers={"Cf-Access-Jwt-Assertion": "signed-token"},
    )

    assert response.status_code == 200
    assert events[0] == ("diagnose", "https://example.com/path")
    assert events[1] == ("follow", user.id, workspace_id, "https://example.com/path")
    assert persisted[0][1] == workspace_site_id
    assert response.json()["workspace_site_id"] == str(workspace_site_id)
    assert response.json()["diagnostic_id"] == str(stored_id)


def test_workspace_url_diagnosis_does_not_associate_site_when_inspection_fails(monkeypatch):
    client, user = _client(monkeypatch)
    workspace_id = uuid4()
    monkeypatch.setattr(
        access,
        "list_authorized_context",
        lambda user_id: (
            access.WorkspaceContext(
                id=workspace_id,
                name="Mi espacio",
                role=access.ROLE_OWNER,
                sites=(),
            ),
        ),
    )
    monkeypatch.setattr(access, "normalize_site_url", lambda url: ("example.com", "https://example.com"))
    monkeypatch.setattr(
        privacy_api,
        "diagnose_privacy_url",
        lambda url: (_ for _ in ()).throw(
            privacy_api.PrivacyInspectionError("inspection_failed")
        ),
    )
    follow_calls = []
    monkeypatch.setattr(
        access,
        "follow_site",
        lambda *args: follow_calls.append(args),
    )

    response = client.post(
        f"/privacy/workspaces/{workspace_id}/diagnose",
        json={"url": "https://example.com"},
        headers={"Cf-Access-Jwt-Assertion": "signed-token"},
    )

    assert response.status_code == 422
    assert follow_calls == []
