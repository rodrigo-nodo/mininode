import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest

BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.services import privacy_correction_plan_order as service  # noqa: E402
from mininode_api.services import privacy_diagnostic_snapshot as snapshots  # noqa: E402


def fake_connection(monkeypatch, *, rows=()):
    executions = []
    pending_rows = iter(rows)
    class Cursor:
        def execute(self, statement, params=None): executions.append((" ".join(statement.split()), params))
        def fetchone(self): return next(pending_rows, None)
        def __enter__(self): return self
        def __exit__(self, *args): pass
    @contextmanager
    def connection(): yield type("Connection", (), {"cursor": lambda self: Cursor()})()
    monkeypatch.setattr(service, "_connection", connection)
    return executions


def diagnostic_record(*, expired=False):
    created = datetime.now(timezone.utc) - (timedelta(hours=25) if expired else timedelta())
    return snapshots.StoredPrivacyDiagnostic(
        uuid4(), "https://example.com/", {"site_url": "https://example.com/", "score": 42, "controls": []},
        42, created, created + timedelta(hours=24),
    )


def order_row(diagnostic_id=None, *, status="pending_payment"):
    now = datetime.now(timezone.utc)
    return (uuid4(), diagnostic_id or uuid4(), None, "https://example.com/", "buyer@example.com",
            service.PRODUCT_CODE, service.PRODUCT_AMOUNT, service.PRODUCT_CURRENCY, status, now, now)


def test_initialization_links_order_to_diagnostic_without_uniqueness(monkeypatch):
    executions = fake_connection(monkeypatch)
    service.initialize_database()
    sql = executions[0][0]
    assert "diagnostic_id UUID NOT NULL REFERENCES privacy.diagnostic(id)" in sql
    assert "correction_plan_id UUID NULL REFERENCES privacy.correction_plan(id)" in sql
    assert "site_url TEXT NOT NULL" in sql and "site_url TEXT UNIQUE" not in sql
    assert "email TEXT NOT NULL" in sql and "email TEXT UNIQUE" not in sql
    assert "amount INTEGER NOT NULL CHECK (amount = 49900)" in sql
    assert "currency = 'CLP'" in sql
    assert "product_code = 'PRIVACY_CORRECTION_PLAN'" in sql
    assert "status IN ('pending_payment', 'paid', 'cancelled')" in sql
    assert "access_token" not in sql
    assert "ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ NULL" in sql


def test_create_uses_diagnostic_site_and_backend_commercial_values(monkeypatch):
    diagnostic = diagnostic_record()
    monkeypatch.setattr(snapshots, "get_diagnostic_snapshot", lambda value: diagnostic)
    executions = fake_connection(monkeypatch, rows=[order_row(diagnostic.id)])
    created = service.create_order(diagnostic_id=diagnostic.id, email=" Buyer@Example.COM ")
    _, params = executions[0]
    assert isinstance(params[0], UUID)
    assert params[1:] == (diagnostic.id, "https://example.com/", "buyer@example.com",
                          "PRIVACY_CORRECTION_PLAN", 49900, "CLP", "pending_payment")
    assert created.diagnostic_id == diagnostic.id


def test_expired_diagnostic_does_not_insert_order(monkeypatch):
    diagnostic = diagnostic_record(expired=True)
    monkeypatch.setattr(snapshots, "get_diagnostic_snapshot", lambda value: diagnostic)
    executions = fake_connection(monkeypatch)
    with pytest.raises(snapshots.PrivacyDiagnosticPurchaseExpiredError):
        service.create_order(diagnostic_id=diagnostic.id, email="buyer@example.com")
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
    with pytest.raises(service.CorrectionPlanOrderNotFoundError): service.get_order(uuid4())


def test_attach_plan_sets_paid_only_for_an_unactivated_pending_order(monkeypatch):
    plan_id = uuid4()
    row = list(order_row(status="paid"))
    row[2] = plan_id
    executions = fake_connection(monkeypatch, rows=[tuple(row)])
    attached = service.attach_correction_plan(row[0], plan_id)
    sql, params = executions[0]
    assert "correction_plan_id = %s, status = 'paid'" in sql
    assert "status = 'pending_payment' AND correction_plan_id IS NULL" in sql
    assert params == (plan_id, row[0])
    assert attached.correction_plan_id == plan_id
    assert "paid_at = CURRENT_TIMESTAMP" in sql
