import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.main import create_app  # noqa: E402
from mininode_api.services import privacy_correction_plan_order as service  # noqa: E402


def an_order(status="pending_payment"):
    now = datetime.now(timezone.utc)
    return service.CorrectionPlanOrder(
        uuid4(), "https://example.com/", "buyer@example.com", service.PRODUCT_CODE,
        service.PRODUCT_AMOUNT, service.PRODUCT_CURRENCY, status, now, now,
    )


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("API_KEY", "internal-key")
    app = create_app()
    app.state.privacy_correction_plan_order_ready = True
    return TestClient(app)


def test_public_post_accepts_only_site_and_email(client, monkeypatch):
    calls = []
    order = an_order()
    monkeypatch.setattr(service, "create_order", lambda **kwargs: calls.append(kwargs) or order)
    response = client.post(
        "/privacy/correction-plan-orders",
        json={"site_url": "HTTPS://EXAMPLE.COM", "email": " Buyer@Example.COM "},
    )
    assert response.status_code == 201
    assert response.json() == {
        "order_id": str(order.id), "product": "PRIVACY_CORRECTION_PLAN",
        "amount": 49900, "currency": "CLP", "status": "pending_payment",
    }
    assert calls == [{"site_url": "https://example.com/", "email": "buyer@example.com"}]
    assert not {"email", "access_token", "plan_path"}.intersection(response.json())


@pytest.mark.parametrize("field,value", [
    ("amount", 1), ("currency", "USD"), ("status", "paid"),
    ("product_code", "OTHER"),
])
def test_public_post_rejects_caller_controlled_commercial_fields(client, field, value):
    response = client.post(
        "/privacy/correction-plan-orders",
        json={"site_url": "https://example.com", "email": "buyer@example.com", field: value},
    )
    assert response.status_code == 422


def test_public_post_rejects_invalid_or_oversized_values(client):
    assert client.post("/privacy/correction-plan-orders", json={
        "site_url": "https://example.com", "email": "not-an-email",
    }).status_code == 422
    assert client.post("/privacy/correction-plan-orders", json={
        "site_url": "https://" + "a" * 2048, "email": "buyer@example.com",
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
        "site_url": "https://example.com", "email": "buyer@example.com",
    })
    assert response.status_code == 503
    assert "buyer@example.com" not in response.text


def test_order_startup_failure_does_not_break_health(monkeypatch):
    monkeypatch.setattr(service, "initialize_database", lambda: (_ for _ in ()).throw(RuntimeError()))
    app = create_app()
    with TestClient(app) as startup_client:
        assert startup_client.get("/health").json() == {"status": "ok"}
        assert app.state.privacy_correction_plan_order_ready is False
