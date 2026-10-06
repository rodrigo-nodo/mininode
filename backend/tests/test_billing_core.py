from datetime import datetime, timezone
from mininode_api.services import billing

def test_privacy_web_price_is_server_side():
    assert billing.PRODUCT == "privacy_web"
    assert billing.PRICE_CLP == 9900

def test_calendar_month_is_not_fixed_30_days():
    assert billing.add_calendar_month(datetime(2026, 1, 31, tzinfo=timezone.utc)) == datetime(2026, 2, 28, tzinfo=timezone.utc)
    assert billing.add_calendar_month(datetime(2026, 12, 6, tzinfo=timezone.utc)) == datetime(2027, 1, 6, tzinfo=timezone.utc)

def test_schema_protects_payment_idempotency():
    assert "UNIQUE (provider, provider_order_id)" in billing.SCHEMA_SQL
    assert "billing_payment_entitlement_source_idx" in billing.SCHEMA_SQL

def test_frontend_cannot_set_price():
    from mininode_api.api.billing import CreateOrderRequest
    assert set(CreateOrderRequest.model_fields) == {"workspace_site_id", "diagnostic_id"}
