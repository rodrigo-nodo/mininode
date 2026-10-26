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


def test_stale_refresh_persists_new_snapshot_and_preserves_original_in_postgres(monkeypatch):
    """Integration: real route + access authorization + PostgreSQL persistence.

    Only the external site inspector is replaced to make the test deterministic.
    No schema drops or use of the production database are permitted here.
    """
    import os
    import psycopg
    from psycopg.conninfo import conninfo_to_dict

    url = os.getenv("DATABASE_URL", "")
    if not url:
        pytest.skip("Local PostgreSQL DATABASE_URL required")
    if conninfo_to_dict(url).get("host", "localhost") not in {"localhost", "127.0.0.1", "postgres"}:
        pytest.skip("Only isolated local/CI PostgreSQL is allowed")

    access.initialize_database()
    privacy_diagnostic_snapshot.initialize_database()
    user_id, workspace_id, canonical_site_id, workspace_site_id = (uuid4() for _ in range(4))
    hostname = f"pw03-refresh-{uuid4().hex}.example"
    original = {"site_url": f"https://{hostname}/", "score": 70, "controls": [],
                "priorities": [{"name": "Original"}]}
    refreshed_snapshot = {"site_url": f"https://{hostname}/", "score": 89, "controls": [],
                          "priorities": [{"name": "Updated"}]}
    old_id = None
    try:
        with psycopg.connect(url) as conn:
            conn.execute("INSERT INTO access.users (id,email) VALUES (%s,%s)",
                         (user_id, f"{user_id}@example.test"))
            conn.execute("INSERT INTO access.workspaces (id,name) VALUES (%s,'PW-03 isolated')",
                         (workspace_id,))
            conn.execute("INSERT INTO access.workspace_members (workspace_id,user_id,role) VALUES (%s,%s,'owner')",
                         (workspace_id, user_id))
            conn.execute("INSERT INTO access.sites (id,hostname,canonical_url) VALUES (%s,%s,%s)",
                         (canonical_site_id, hostname, f"https://{hostname}/"))
            conn.execute("INSERT INTO access.workspace_sites (id,workspace_id,site_id) VALUES (%s,%s,%s)",
                         (workspace_site_id, workspace_id, canonical_site_id))

        saved = privacy_diagnostic_snapshot.create_diagnostic_snapshot(
            original, workspace_site_id=workspace_site_id,
            requested_url=f"https://{hostname}/",
        )
        old_id = saved.id
        with psycopg.connect(url) as conn:
            conn.execute(
                "UPDATE privacy.diagnostic SET purchase_expires_at=CURRENT_TIMESTAMP - INTERVAL '1 hour' WHERE id=%s",
                (old_id,),
            )
        monkeypatch.setattr(
            access_identity, "verify_access_jwt",
            lambda _: access_identity.AccessIdentity(email=f"{user_id}@example.test"),
        )
        monkeypatch.setattr(access, "get_or_create_user", lambda _: access.StoredUser(
            id=user_id, email=f"{user_id}@example.test",
        ))
        inspections = []
        monkeypatch.setattr(
            api, "diagnose_privacy_url",
            lambda target: inspections.append(target) or refreshed_snapshot,
        )
        app = create_app()
        app.state.access_ready = True
        app.state.privacy_diagnostic_snapshot_ready = True
        client = TestClient(app)
        path = f"/privacy/workspace-sites/{workspace_site_id}/prepare-activation"
        headers = {"Cf-Access-Jwt-Assertion": "signed-token"}

        response = client.post(path, headers=headers)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["refreshed"] is True
        new_id = result["diagnostic"]["diagnostic_id"]
        assert new_id != str(old_id)
        assert result["diagnostic"]["score"] == 89
        assert result["diagnostic"]["workspace_site_id"] == str(workspace_site_id)
        assert inspections == [f"https://{hostname}/"]

        # The response ID must exist in PostgreSQL, with unchanged original evidence.
        with psycopg.connect(url) as conn:
            records = conn.execute(
                """SELECT id, diagnostic_snapshot, score
                   FROM privacy.diagnostic WHERE workspace_site_id=%s
                   ORDER BY created_at ASC, id ASC""",
                (workspace_site_id,),
            ).fetchall()
        assert len(records) == 2
        by_id = {str(row[0]): row for row in records}
        assert by_id[str(old_id)][1:] == (original, 70)
        assert by_id[new_id][1:] == (refreshed_snapshot, 89)
        assert str(privacy_diagnostic_snapshot.get_latest_for_workspace_site(workspace_site_id).id) == new_id

        # A new attempt reuses the stored snapshot rather than paying for another scan.
        repeated = client.post(path, headers=headers)
        assert repeated.status_code == 200
        assert repeated.json()["refreshed"] is False
        assert repeated.json()["diagnostic"]["diagnostic_id"] == new_id
        assert inspections == [f"https://{hostname}/"]

        # If the next inspection cannot be saved, the previous snapshot remains intact.
        with psycopg.connect(url) as conn:
            conn.execute(
                "UPDATE privacy.diagnostic SET purchase_expires_at=CURRENT_TIMESTAMP - INTERVAL '1 hour' WHERE id=%s",
                (new_id,),
            )
        def fail_store(*_args, **_kwargs):
            raise RuntimeError("simulated local persistence failure")
        monkeypatch.setattr(privacy_diagnostic_snapshot, "create_diagnostic_snapshot", fail_store)
        failed = client.post(path, headers=headers)
        assert failed.status_code == 503
        assert "diagnostic" not in failed.json()
        with psycopg.connect(url) as conn:
            still_saved = conn.execute(
                "SELECT id, diagnostic_snapshot FROM privacy.diagnostic WHERE workspace_site_id=%s",
                (workspace_site_id,),
            ).fetchall()
        assert len(still_saved) == 2
        assert {str(row[0]) for row in still_saved} == {str(old_id), new_id}
        assert {str(row[0]): row[1] for row in still_saved}[str(old_id)] == original
    finally:
        # Clean only test-owned rows; never reset a schema or touch other tenants.
        with psycopg.connect(url) as conn:
            conn.execute("DELETE FROM privacy.diagnostic WHERE workspace_site_id=%s",
                         (workspace_site_id,))
            conn.execute("DELETE FROM access.workspace_sites WHERE id=%s",
                         (workspace_site_id,))
            conn.execute("DELETE FROM access.sites WHERE id=%s", (canonical_site_id,))
            conn.execute("DELETE FROM access.workspace_members WHERE workspace_id=%s",
                         (workspace_id,))
            conn.execute("DELETE FROM access.workspaces WHERE id=%s", (workspace_id,))
            conn.execute("DELETE FROM access.users WHERE id=%s", (user_id,))
