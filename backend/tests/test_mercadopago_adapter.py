import hashlib
import hmac
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from mininode_api.services import billing, mercadopago


class Response:
    def __init__(self, payload):
        self.payload = payload
    def raise_for_status(self):
        pass
    def json(self):
        return self.payload


def order():
    now = datetime.now(timezone.utc)
    return billing.Order(uuid4(), uuid4(), uuid4(), "privacy_web", 9900, "CLP", "pending", None, None, now, None)


def test_webhook_signature_matches_mercado_pago_manifest(monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "secret")
    manifest = "id:ord123;request-id:req-1;ts:12345;"
    digest = hmac.new(b"secret", manifest.encode(), hashlib.sha256).hexdigest()
    assert mercadopago.validate_webhook_signature(
        x_signature=f"ts=12345,v1={digest}", x_request_id="req-1", data_id="ORD123"
    )
    assert not mercadopago.validate_webhook_signature(
        x_signature="ts=12345,v1=bad", x_request_id="req-1", data_id="ORD123"
    )


def test_checkout_uses_server_order_and_same_tab_url(monkeypatch):
    item = order()
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("MININODE_PUBLIC_URL", "https://dev.mininode.io")
    captured = {}
    def post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return Response({"id": "ORD123", "checkout_url": "https://www.mercadopago.cl/checkout/test"})
    linked = {}
    monkeypatch.setattr(mercadopago.httpx, "post", post)
    monkeypatch.setattr(billing, "attach_provider_order", lambda *args, **kwargs: linked.update(args=args, kwargs=kwargs))

    provider_id, checkout_url = mercadopago.create_checkout(item, payer_email="buyer@example.com")

    assert provider_id == "ORD123"
    assert checkout_url.startswith("https://")
    assert captured["headers"]["X-Idempotency-Key"] == str(item.id)
    assert captured["json"]["external_reference"] == str(item.id)
    assert captured["json"]["total_amount"] == "9900"
    assert captured["json"]["items"][0]["unit_price"] == "9900"
    assert captured["json"]["config"]["online"]["auto_return"] == "all"
    assert linked["kwargs"] == {"provider": "mercadopago", "provider_order_id": "ORD123"}


def test_processed_accredited_order_confirms_billing(monkeypatch):
    item = order()
    provider_id = "ORD123"
    item = billing.Order(
        item.id, item.workspace_site_id, item.diagnostic_id, item.product_code, item.amount,
        item.currency, item.status, "mercadopago", provider_id, item.created_at, None
    )
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr(billing, "get_order_for_provider", lambda order_id: item if order_id == item.id else None)
    monkeypatch.setattr(
        mercadopago.httpx, "get",
        lambda *args, **kwargs: Response({
            "id": provider_id,
            "external_reference": str(item.id),
            "currency": "CLP",
            "total_amount": "9900",
            "total_paid_amount": "9900",
            "status": "processed",
            "status_detail": "accredited",
            "last_updated_date": "2026-10-06T18:00:00Z",
        }),
    )
    confirmed = {}
    entitlement_id = uuid4()
    def confirm(*args, **kwargs):
        confirmed.update(args=args, kwargs=kwargs)
        return entitlement_id
    monkeypatch.setattr(billing, "payment_confirmed", confirm)

    assert mercadopago.process_order_notification(provider_id) == entitlement_id
    assert confirmed["args"] == (item.id,)
    assert confirmed["kwargs"]["provider"] == "mercadopago"
    assert confirmed["kwargs"]["provider_order_id"] == provider_id
    assert confirmed["kwargs"]["verified_paid_at"] == datetime(2026, 10, 6, 18, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("field,value", [
    ("currency", "USD"),
    ("total_amount", "1"),
    ("total_paid_amount", "1"),
])
def test_provider_mismatch_never_confirms(monkeypatch, field, value):
    item = order()
    provider_id = "ORD123"
    item = billing.Order(
        item.id, item.workspace_site_id, item.diagnostic_id, item.product_code, item.amount,
        item.currency, item.status, "mercadopago", provider_id, item.created_at, None
    )
    payload = {
        "id": provider_id, "external_reference": str(item.id), "currency": "CLP",
        "total_amount": "9900", "total_paid_amount": "9900", "status": "processed",
        "status_detail": "accredited", "last_updated_date": "2026-10-06T18:00:00Z",
    }
    payload[field] = value
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr(billing, "get_order_for_provider", lambda _: item)
    monkeypatch.setattr(mercadopago.httpx, "get", lambda *args, **kwargs: Response(payload))
    monkeypatch.setattr(billing, "payment_confirmed", lambda *args, **kwargs: pytest.fail("must not confirm"))

    with pytest.raises(ValueError):
        mercadopago.process_order_notification(provider_id)


def test_non_accredited_order_does_not_confirm(monkeypatch):
    item = order()
    provider_id = "ORD123"
    item = billing.Order(
        item.id, item.workspace_site_id, item.diagnostic_id, item.product_code, item.amount,
        item.currency, item.status, "mercadopago", provider_id, item.created_at, None
    )
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr(billing, "get_order_for_provider", lambda _: item)
    monkeypatch.setattr(
        mercadopago.httpx, "get",
        lambda *args, **kwargs: Response({
            "id": provider_id, "external_reference": str(item.id), "currency": "CLP",
            "total_amount": "9900", "total_paid_amount": "0", "status": "created",
            "status_detail": "created", "last_updated_date": "2026-10-06T18:00:00Z",
        }),
    )
    monkeypatch.setattr(billing, "payment_confirmed", lambda *args, **kwargs: pytest.fail("must not confirm"))
    assert mercadopago.process_order_notification(provider_id) is None
