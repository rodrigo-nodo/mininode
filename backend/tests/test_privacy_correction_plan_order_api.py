import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.main import create_app  # noqa: E402
from mininode_api.api import privacy as privacy_api  # noqa: E402
from mininode_api.services import privacy_correction_plan_order as service  # noqa: E402
from mininode_api.services import privacy_correction_plan_activation as activation  # noqa: E402
from mininode_api.services import privacy_diagnostic_snapshot as snapshots  # noqa: E402


def an_order(status="pending_payment"):
    now = datetime.now(timezone.utc)
    return service.CorrectionPlanOrder(
        uuid4(), uuid4(), None, "https://example.com/", "buyer@example.com", service.PRODUCT_CODE,
        service.PRODUCT_AMOUNT, service.PRODUCT_CURRENCY, status, now, now,
    )


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("API_KEY", "internal-key")
    app = create_app()
    app.state.privacy_correction_plan_order_ready = True
    app.state.privacy_correction_plan_ready = True
    app.state.privacy_diagnostic_snapshot_ready = True
    return TestClient(app)


def test_public_post_accepts_only_diagnostic_and_email(client, monkeypatch):
    calls = []
    order = an_order()
    monkeypatch.setattr(service, "create_order", lambda **kwargs: calls.append(kwargs) or order)
    response = client.post(
        "/privacy/correction-plan-orders",
        json={"diagnostic_id": str(order.diagnostic_id), "email": " Buyer@Example.COM "},
    )
    assert response.status_code == 201
    assert response.json() == {
        "order_id": str(order.id), "product": "PRIVACY_CORRECTION_PLAN",
        "amount": 9900, "currency": "CLP", "status": "pending_payment",
    }
    assert calls == [{"diagnostic_id": order.diagnostic_id, "email": "buyer@example.com"}]
    assert not {"email", "access_token", "plan_path"}.intersection(response.json())


@pytest.mark.parametrize("field,value", [
    ("amount", 1), ("currency", "USD"), ("status", "paid"),
    ("product_code", "OTHER"),
])
def test_public_post_rejects_caller_controlled_commercial_fields(client, field, value):
    response = client.post(
        "/privacy/correction-plan-orders",
        json={"diagnostic_id": str(uuid4()), "email": "buyer@example.com", field: value},
    )
    assert response.status_code == 422


def test_public_post_rejects_invalid_values_and_site_url(client):
    assert client.post("/privacy/correction-plan-orders", json={
        "diagnostic_id": str(uuid4()), "email": "not-an-email",
    }).status_code == 422
    assert client.post("/privacy/correction-plan-orders", json={
        "diagnostic_id": str(uuid4()), "email": "buyer@example.com", "site_url": "https://other.example",
    }).status_code == 422


def test_mark_paid_is_protected_and_idempotent(client, monkeypatch):
    order = an_order(status="paid")
    calls = []
    monkeypatch.setattr(service, "mark_order_paid", lambda order_id: calls.append(order_id) or order)
    path = f"/privacy/correction-plan-orders/{order.id}/mark-paid"
    assert client.post(path).status_code == 401
    for _ in range(2):
        response = client.post(path, headers={"X-Api-Key": "internal-key"})
        assert response.status_code == 200
        assert response.json()["status"] == "paid"
    assert calls == [order.id, order.id]


def test_activate_is_protected_and_returns_only_technical_plan_fields(client, monkeypatch):
    order = an_order()
    result = activation.ActivatedOrder(order.id, "paid", uuid4(), "/privacy/plan/secret")
    calls = []
    monkeypatch.setattr(activation, "activate_order", lambda order_id: calls.append(order_id) or result)
    path = f"/privacy/correction-plan-orders/{order.id}/activate"
    assert client.post(path).status_code == 401
    response = client.post(path, headers={"X-Api-Key": "internal-key"})
    assert response.status_code == 200
    assert response.json() == {
        "order_id": str(order.id), "status": "paid",
        "correction_plan_id": str(result.correction_plan_id),
        "plan_path": "/privacy/plan/secret",
    }
    assert "email" not in response.json() and "access_token" not in response.json()
    assert calls == [order.id]


@pytest.mark.parametrize("error,expected", [
    (service.CorrectionPlanOrderNotFoundError(), 404),
    (activation.OrderAlreadyActivatedError(), 409),
    (activation.OrderActivationStateError(), 409),
])
def test_activate_errors_are_controlled(client, monkeypatch, error, expected):
    monkeypatch.setattr(activation, "activate_order", lambda _: (_ for _ in ()).throw(error))
    response = client.post(
        f"/privacy/correction-plan-orders/{uuid4()}/activate",
        headers={"X-Api-Key": "internal-key"},
    )
    assert response.status_code == expected


def test_read_is_protected_missing_is_404_and_no_list_exists(client, monkeypatch):
    order_id = uuid4()
    assert client.get(f"/privacy/correction-plan-orders/{order_id}").status_code == 401
    monkeypatch.setattr(
        service, "get_order",
        lambda _: (_ for _ in ()).throw(service.CorrectionPlanOrderNotFoundError()),
    )
    assert client.get(
        f"/privacy/correction-plan-orders/{order_id}",
        headers={"X-Api-Key": "internal-key"},
    ).status_code == 404
    assert client.get("/privacy/correction-plan-orders").status_code == 405


def test_database_failure_is_controlled(client, monkeypatch):
    monkeypatch.setattr(service, "create_order", lambda **_: (_ for _ in ()).throw(RuntimeError()))
    response = client.post("/privacy/correction-plan-orders", json={
        "diagnostic_id": str(uuid4()), "email": "buyer@example.com",
    })
    assert response.status_code == 503
    assert "buyer@example.com" not in response.text


def test_order_startup_failure_does_not_break_health(monkeypatch):
    monkeypatch.setattr(service, "initialize_database", lambda: (_ for _ in ()).throw(RuntimeError()))
    app = create_app()
    with TestClient(app) as startup_client:
        assert startup_client.get("/health").json() == {"status": "ok"}
        assert app.state.privacy_correction_plan_order_ready is False


def test_expired_and_missing_diagnostics_have_controlled_semantics(client, monkeypatch):
    diagnostic_id = uuid4()
    monkeypatch.setattr(
        service, "create_order",
        lambda **_: (_ for _ in ()).throw(snapshots.PrivacyDiagnosticPurchaseExpiredError()),
    )
    expired = client.post("/privacy/correction-plan-orders", json={
        "diagnostic_id": str(diagnostic_id), "email": "buyer@example.com",
    })
    assert expired.status_code == 410
    assert expired.json() == {"detail": "El diagnóstico ya no está disponible para crear un Plan. Realice una nueva revisión."}

    monkeypatch.setattr(
        service, "create_order",
        lambda **_: (_ for _ in ()).throw(snapshots.PrivacyDiagnosticSnapshotNotFoundError()),
    )
    missing = client.post("/privacy/correction-plan-orders", json={
        "diagnostic_id": str(diagnostic_id), "email": "buyer@example.com",
    })
    assert missing.status_code == 404


def test_free_diagnostic_adds_snapshot_metadata_without_changing_result(client, monkeypatch):
    diagnostic = {
        "site_url": "https://example.com/", "score": 42, "coverage": 90,
        "status": "Puede mejorar", "controls": [], "priorities": [],
        "scope": {"pages_analyzed": 1},
    }
    created = datetime.now(timezone.utc)
    stored = snapshots.StoredPrivacyDiagnostic(
        uuid4(), diagnostic["site_url"], diagnostic, 42, created,
        created + timedelta(hours=24),
    )
    monkeypatch.setattr(privacy_api, "diagnose_privacy_url", lambda url: diagnostic.copy())
    monkeypatch.setattr(snapshots, "create_diagnostic_snapshot", lambda result: stored)
    response = client.post(
        "/privacy/diagnose", headers={"X-Api-Key": "internal-key"},
        json={"url": "https://example.com"},
    )
    assert response.status_code == 200
    body = response.json()
    for field, value in diagnostic.items():
        assert body[field] == value
    assert body["diagnostic_id"] == str(stored.id)
    assert body["purchase_expires_at"] == stored.purchase_expires_at.isoformat()


def test_snapshot_failure_does_not_break_free_diagnostic(client, monkeypatch):
    diagnostic = {
        "site_url": "https://example.com/", "score": 42, "controls": [],
        "priorities": [], "scope": {},
    }
    monkeypatch.setattr(privacy_api, "diagnose_privacy_url", lambda url: diagnostic.copy())
    monkeypatch.setattr(
        snapshots, "create_diagnostic_snapshot",
        lambda result: (_ for _ in ()).throw(RuntimeError("database unavailable")),
    )
    response = client.post(
        "/privacy/diagnose", headers={"X-Api-Key": "internal-key"},
        json={"url": "https://example.com"},
    )
    assert response.status_code == 200
    assert response.json() == diagnostic


def test_snapshot_startup_failure_does_not_break_health(monkeypatch):
    monkeypatch.setattr(
        snapshots, "initialize_database",
        lambda: (_ for _ in ()).throw(RuntimeError("database unavailable")),
    )
    app = create_app()
    with TestClient(app) as startup_client:
        assert startup_client.get("/health").json() == {"status": "ok"}
        assert app.state.privacy_diagnostic_snapshot_ready is False
        assert any(route.path == "/privacy/diagnose" for route in app.routes)
