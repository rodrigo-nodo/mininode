import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.main import create_app  # noqa: E402
from mininode_api.services import learn_feedback, privacy_correction_plan as service  # noqa: E402
from mininode_api.services import privacy_correction_plan_check as checks  # noqa: E402
from mininode_api.services import privacy_correction_plan_flow as flow  # noqa: E402
from mininode_api.services.privacy_diagnostic import PrivacyInspectionError  # noqa: E402


PLAN = {
    "version": "1",
    "actions_version": "actions-1",
    "initial_score": 26,
    "item_count": 1,
    "items": [{"control_code": "PRV-001"}],
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("API_KEY", "internal-key")
    app = create_app()
    app.state.privacy_correction_plan_ready = True
    app.state.privacy_correction_plan_check_ready = True
    return TestClient(app)


def test_post_requires_api_key(client):
    response = client.post(
        "/privacy/correction-plans",
        json={"site_url": "https://example.com", "plan": PLAN},
    )
    assert response.status_code == 401


def test_post_creates_plan_without_exposing_hash(client, monkeypatch):
    plan_id = uuid4()
    calls = []
    monkeypatch.setattr(
        service,
        "create_correction_plan",
        lambda **kwargs: calls.append(kwargs)
        or service.CreatedCorrectionPlan(plan_id, "secret-token"),
    )
    response = client.post(
        "/privacy/correction-plans",
        headers={"X-Api-Key": "internal-key"},
        json={"site_url": "https://example.com", "plan": PLAN},
    )
    assert response.status_code == 201
    assert response.json() == {
        "access_token": "secret-token",
        "plan_path": "/privacy/plan/secret-token",
    }
    assert "token_hash" not in response.json()
    assert calls == [{"site_url": "https://example.com", "plan": PLAN}]


def test_from_url_requires_api_key(client):
    response = client.post(
        "/privacy/correction-plans/from-url", json={"url": "https://example.com"}
    )
    assert response.status_code == 401


def test_from_url_returns_plan_access_without_internal_data(client, monkeypatch):
    created = service.CreatedCorrectionPlan(uuid4(), "generated-token")
    monkeypatch.setattr(
        flow,
        "create_correction_plan_from_url",
        lambda url: (created, {**PLAN, "item_count": 7}),
    )

    response = client.post(
        "/privacy/correction-plans/from-url",
        headers={"X-Api-Key": "internal-key"},
        json={"url": "https://example.com"},
    )

    assert response.status_code == 201
    assert response.json() == {
        "access_token": "generated-token",
        "plan_path": "/privacy/plan/generated-token",
        "initial_score": 26,
        "item_count": 7,
    }
    assert "token_hash" not in response.json()


def test_from_url_preserves_diagnostic_error_and_empty_plan_semantics(client, monkeypatch):
    monkeypatch.setattr(
        flow,
        "create_correction_plan_from_url",
        lambda url: (_ for _ in ()).throw(PrivacyInspectionError("unsafe_target")),
    )
    unsafe = client.post(
        "/privacy/correction-plans/from-url",
        headers={"X-Api-Key": "internal-key"},
        json={"url": "http://127.0.0.1"},
    )
    assert unsafe.status_code == 400
    assert unsafe.json()["error"] == "unsafe_target"

    monkeypatch.setattr(
        flow,
        "create_correction_plan_from_url",
        lambda url: (_ for _ in ()).throw(flow.NoActionableItemsError("none")),
    )
    empty = client.post(
        "/privacy/correction-plans/from-url",
        headers={"X-Api-Key": "internal-key"},
        json={"url": "https://example.com"},
    )
    assert empty.status_code == 422
    assert empty.json() == {"error": "no_actionable_items", "message": "none"}


def test_get_uses_token_without_api_key(client, monkeypatch):
    stored = {
        "id": uuid4(),
        "site_url": "https://example.com",
        "created_at": datetime.now(timezone.utc),
        "plan": PLAN,
    }
    monkeypatch.setattr(service, "get_correction_plan", lambda token: stored)
    monkeypatch.setattr(checks, "get_check_metadata", lambda plan_id: {"status": "available", "expires_at": datetime.now(timezone.utc)})
    response = client.get("/privacy/correction-plans/secret-token")
    assert response.status_code == 200
    assert response.json()["plan"] == PLAN
    assert "token_hash" not in response.json()


def test_public_check_endpoint_accepts_no_body_or_api_key(client, monkeypatch):
    result = {"status": "used", "created_at": datetime.now(timezone.utc), "result": {"version": "1"}}
    monkeypatch.setattr(checks, "perform_check", lambda token: result)
    response = client.post("/privacy/correction-plans/secret-token/check")
    assert response.status_code == 200
    assert response.json()["result"] == {"version": "1"}
    assert "token_hash" not in response.json()


@pytest.mark.parametrize(
    "error,expected",
    [(checks.ImprovementCheckNotFoundError, 404), (checks.ImprovementCheckUsedError, 409),
     (checks.ImprovementCheckExpiredError, 410), (checks.ImprovementInspectionError, 503)],
)
def test_check_errors_are_controlled(client, monkeypatch, error, expected):
    monkeypatch.setattr(checks, "perform_check", lambda token: (_ for _ in ()).throw(error()))
    response = client.post("/privacy/correction-plans/secret-token/check")
    assert response.status_code == expected


def test_invalid_or_revoked_token_returns_same_404(client, monkeypatch):
    def missing(_token):
        raise service.CorrectionPlanNotFoundError("Plan not found")

    monkeypatch.setattr(service, "get_correction_plan", missing)
    response = client.get("/privacy/correction-plans/not-active")
    assert response.status_code == 404
    assert response.json() == {"detail": "Plan no encontrado."}


def test_no_list_endpoint_and_unavailable_service_is_controlled(client):
    assert client.get("/privacy/correction-plans").status_code == 405
    client.app.state.privacy_correction_plan_ready = False
    assert client.get("/privacy/correction-plans/token").status_code == 503


def test_privacy_startup_failure_does_not_break_health_diagnostic_or_learn(monkeypatch):
    learn_calls = []
    monkeypatch.setattr(
        learn_feedback, "initialize_database", lambda: learn_calls.append("initialized")
    )
    monkeypatch.setattr(
        service,
        "initialize_database",
        lambda: (_ for _ in ()).throw(RuntimeError("database unavailable")),
    )
    app = create_app()
    with TestClient(app) as startup_client:
        assert startup_client.get("/health").status_code == 200
        assert any(route.path == "/privacy/diagnose" for route in app.routes)
        assert startup_client.get("/privacy/correction-plans/token").status_code == 503
        assert app.state.learn_feedback_ready is True
    assert learn_calls == ["initialized"]
