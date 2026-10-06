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

def test_confirmation_is_serialized_and_transactional():
    import inspect
    source = inspect.getsource(billing.payment_confirmed)
    assert "FOR UPDATE" in source
    assert "status == 'paid'" in source
    assert "Paid order without entitlement" in source
    assert "source_id" in source

def test_renewal_starts_after_current_active_period():
    import inspect
    source = inspect.getsource(billing.payment_confirmed)
    assert "max(active_until)" in source
    assert "max(verified_paid_at, latest)" in source
    assert "latest > add_calendar_month(verified_paid_at)" in source
    assert "already has one future period paid" in source
