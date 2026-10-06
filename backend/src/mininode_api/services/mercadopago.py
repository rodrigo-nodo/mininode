"""Mercado Pago Checkout Pro adapter using the recommended Orders API."""
from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime
from decimal import Decimal
from uuid import UUID

import httpx

from mininode_api.services import billing

API_BASE = "https://api.mercadopago.com"
PROVIDER = "mercadopago"


def _token() -> str:
    value = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "").strip()
    if not value:
        raise RuntimeError("MERCADOPAGO_ACCESS_TOKEN is not configured")
    return value


def _webhook_secret() -> str:
    value = os.getenv("MERCADOPAGO_WEBHOOK_SECRET", "").strip()
    if not value:
        raise RuntimeError("MERCADOPAGO_WEBHOOK_SECRET is not configured")
    return value


def _return_base_url() -> str:
    value = os.getenv("MININODE_PUBLIC_URL", "").strip().rstrip("/")
    if not value.startswith("https://"):
        raise RuntimeError("MININODE_PUBLIC_URL must be an HTTPS URL")
    return value


def validate_webhook_signature(*, x_signature: str, x_request_id: str, data_id: str) -> bool:
    parts = {}
    for part in x_signature.split(","):
        key, sep, value = part.strip().partition("=")
        if sep:
            parts[key] = value
    ts, received = parts.get("ts"), parts.get("v1")
    if not ts or not received or not x_request_id or not data_id:
        return False
    manifest = f"id:{data_id.lower()};request-id:{x_request_id};ts:{ts};"
    expected = hmac.new(_webhook_secret().encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received)


def create_checkout(order: billing.Order, *, payer_email: str) -> tuple[str, str]:
    if order.status != "pending":
        raise ValueError("Only pending orders can start checkout")
    base = _return_base_url()
    payload = {
        "type": "online",
        "processing_mode": "manual",
        "capture_mode": "automatic_async",
        "total_amount": str(order.amount),
        "external_reference": str(order.id),
        "description": "Mininode Privacy Web - 1 mes",
        "payer": {"email": payer_email},
        "items": [{
            "title": "Mininode Privacy Web - 1 mes",
            "unit_price": str(order.amount),
            "quantity": 1,
            "unit_measure": "unit",
            "total_amount": str(order.amount),
        }],
        "config": {"online": {
            "success_url": f"{base}/privacy/?payment=success",
            "failure_url": f"{base}/privacy/?payment=failure",
            "pending_url": f"{base}/privacy/?payment=pending",
            "auto_return": "all",
        }},
    }
    response = httpx.post(
        f"{API_BASE}/v1/orders",
        headers={
            "Authorization": f"Bearer {_token()}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": str(order.id),
        },
        json=payload,
        timeout=15.0,
    )
    response.raise_for_status()
    data = response.json()
    provider_order_id = str(data.get("id", ""))
    checkout_url = str(data.get("checkout_url", ""))
    if not provider_order_id or not checkout_url.startswith("https://"):
        raise RuntimeError("Mercado Pago returned an invalid checkout")
    billing.attach_provider_order(order.id, provider=PROVIDER, provider_order_id=provider_order_id)
    return provider_order_id, checkout_url


def _parse_provider_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Mercado Pago timestamp must include timezone")
    return parsed


def process_order_notification(provider_order_id: str) -> UUID | None:
    response = httpx.get(
        f"{API_BASE}/v1/orders/{provider_order_id}",
        headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"},
        timeout=15.0,
    )
    response.raise_for_status()
    data = response.json()

    if str(data.get("id")) != provider_order_id:
        raise ValueError("Mercado Pago order id mismatch")
    try:
        internal_order_id = UUID(str(data["external_reference"]))
    except (KeyError, ValueError) as exc:
        raise ValueError("Invalid Mercado Pago external reference") from exc

    order = billing.get_order_for_provider(internal_order_id)
    if order is None:
        raise ValueError("Billing order not found")
    if (order.provider, order.provider_order_id) != (PROVIDER, provider_order_id):
        raise ValueError("Mercado Pago order is not linked to Billing order")
    if str(data.get("currency")) != order.currency:
        raise ValueError("Mercado Pago currency mismatch")
    if Decimal(str(data.get("total_amount"))) != Decimal(order.amount):
        raise ValueError("Mercado Pago amount mismatch")

    status, detail = data.get("status"), data.get("status_detail")
    if status != "processed" or detail != "accredited":
        return None
    if Decimal(str(data.get("total_paid_amount"))) != Decimal(order.amount):
        raise ValueError("Mercado Pago paid amount mismatch")

    paid_at = _parse_provider_time(str(data["last_updated_date"]))
    return billing.payment_confirmed(
        internal_order_id,
        provider=PROVIDER,
        provider_order_id=provider_order_id,
        verified_paid_at=paid_at,
    )
