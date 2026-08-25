import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest

BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.services import privacy_correction_plan_order as service  # noqa: E402


def fake_connection(monkeypatch, *, rows=()):
    executions = []
    pending_rows = iter(rows)

    class Cursor:
        def execute(self, statement, params=None):
            executions.append((" ".join(statement.split()), params))

        def fetchone(self):
            return next(pending_rows, None)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    @contextmanager
    def connection():
        yield type("Connection", (), {"cursor": lambda self: Cursor()})()

    monkeypatch.setattr(service, "_connection", connection)
    return executions


def order_row(*, status="pending_payment", site_url="https://example.com/", email="buyer@example.com"):
    now = datetime.now(timezone.utc)
    return (
        uuid4(), site_url, email, service.PRODUCT_CODE, service.PRODUCT_AMOUNT,
        service.PRODUCT_CURRENCY, status, now, now,
    )


def test_initialization_defines_minimal_order_table(monkeypatch):
    executions = fake_connection(monkeypatch)
    service.initialize_database()
    sql = executions[0][0]
    assert "CREATE SCHEMA IF NOT EXISTS privacy" in sql
    assert "CREATE TABLE IF NOT EXISTS privacy.correction_plan_order" in sql
    assert "id UUID PRIMARY KEY" in sql
    assert "site_url TEXT NOT NULL" in sql and "site_url TEXT UNIQUE" not in sql
    assert "email TEXT NOT NULL" in sql and "email TEXT UNIQUE" not in sql
    assert "amount INTEGER NOT NULL CHECK (amount = 49900)" in sql
    assert "currency = 'CLP'" in sql
    assert "product_code = 'PRIVACY_CORRECTION_PLAN'" in sql
    assert "status IN ('pending_payment', 'paid', 'cancelled')" in sql
    assert "access_token" not in sql


def test_create_normalizes_input_and_uses_backend_commercial_values(monkeypatch):
    row = order_row(site_url="https://example.com/path", email="buyer@example.com")
    executions = fake_connection(monkeypatch, rows=[row])
    created = service.create_order(
        site_url=" HTTPS://EXAMPLE.COM:443/path?utm_source=test ",
        email=" Buyer@Example.COM ",
    )
    sql, params = executions[0]
    assert "INSERT INTO privacy.correction_plan_order" in sql
    assert isinstance(params[0], UUID)
    assert params[1:] == (
        "https://example.com/path", "buyer@example.com", "PRIVACY_CORRECTION_PLAN",
        49900, "CLP", "pending_payment",
    )
    assert created.status == "pending_payment"


def test_create_rejects_invalid_site_without_database_or_network(monkeypatch):
    executions = fake_connection(monkeypatch)
    with pytest.raises(Exception, match="invalid_url"):
        service.create_order(site_url="file:///tmp/private", email="buyer@example.com")
    assert executions == []


@pytest.mark.parametrize("status", ["pending_payment", "paid"])
def test_mark_paid_is_idempotent_and_only_updates_state(monkeypatch, status):
    executions = fake_connection(monkeypatch, rows=[order_row(status="paid")])
    paid = service.mark_order_paid(uuid4())
    sql, _ = executions[0]
    assert "SET status = 'paid'" in sql
    assert "status IN ('pending_payment', 'paid')" in sql
    assert "correction_plan (" not in sql
    assert paid.status == "paid"


def test_missing_order_is_not_found(monkeypatch):
    fake_connection(monkeypatch)
    with pytest.raises(service.CorrectionPlanOrderNotFoundError):
        service.get_order(uuid4())
