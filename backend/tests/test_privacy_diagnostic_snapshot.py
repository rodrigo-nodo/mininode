import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest

BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.services import privacy_diagnostic_snapshot as service  # noqa: E402


def fake_connection(monkeypatch, *, rows=()):
    executions = []
    pending_rows = iter(rows)

    class Cursor:
        def execute(self, statement, params=None):
            executions.append((" ".join(statement.split()), params))

        def fetchone(self):
            return next(pending_rows, None)

        def __enter__(self): return self
        def __exit__(self, *args): pass

    @contextmanager
    def connection():
        yield type("Connection", (), {"cursor": lambda self: Cursor()})()

    monkeypatch.setattr(service, "_connection", connection)
    return executions


def diagnostic():
    return {
        "site_url": "https://example.com/", "score": 42, "coverage": 90,
        "status": "Puede mejorar", "controls": [{"control_code": "PRV-001"}],
        "priorities": [], "scope": {"pages_analyzed": 1},
    }


def stored_row(snapshot=None):
    created = datetime.now(timezone.utc)
    return (uuid4(), "https://example.com/", snapshot or diagnostic(), 42, created, created + timedelta(hours=24))


def test_initialization_defines_immutable_minimal_diagnostic_table(monkeypatch):
    executions = fake_connection(monkeypatch)
    service.initialize_database()
    sql = executions[0][0]
    assert "CREATE SCHEMA IF NOT EXISTS privacy" in sql
    assert "CREATE TABLE IF NOT EXISTS privacy.diagnostic" in sql
    assert "id UUID PRIMARY KEY" in sql
    assert "site_url TEXT NOT NULL" in sql and "site_url TEXT UNIQUE" not in sql
    assert "diagnostic_snapshot JSONB NOT NULL" in sql
    assert "score BETWEEN 0 AND 100" in sql
    assert "purchase_expires_at TIMESTAMPTZ NOT NULL" in sql
    for personal_field in ("email", "user_agent", "ip_address", "name"):
        assert personal_field not in sql
    assert "UPDATE privacy.diagnostic" not in sql


def test_create_stores_snapshot_intact_with_backend_24_hour_expiration(monkeypatch):
    snapshot = diagnostic()
    row = stored_row(snapshot)
    executions = fake_connection(monkeypatch, rows=[row])
    stored = service.create_diagnostic_snapshot(snapshot)
    sql, params = executions[0]
    assert "CURRENT_TIMESTAMP + INTERVAL '24 hours'" in sql
    assert isinstance(params[0], UUID)
    assert params[1] == snapshot["site_url"]
    assert params[2].obj == snapshot
    assert params[3] == 42
    assert stored.diagnostic_snapshot == snapshot
    assert stored.purchase_expires_at - stored.created_at == timedelta(hours=24)


def test_get_returns_snapshot_without_recalculation(monkeypatch):
    snapshot = diagnostic()
    executions = fake_connection(monkeypatch, rows=[stored_row(snapshot)])
    stored = service.get_diagnostic_snapshot(uuid4())
    assert stored.score == snapshot["score"]
    assert stored.diagnostic_snapshot == snapshot
    assert "SELECT" in executions[0][0]


def test_missing_and_expired_diagnostics_are_controlled(monkeypatch):
    fake_connection(monkeypatch)
    with pytest.raises(service.PrivacyDiagnosticSnapshotNotFoundError):
        service.get_diagnostic_snapshot(uuid4())
    created = datetime.now(timezone.utc) - timedelta(hours=25)
    expired = service.StoredPrivacyDiagnostic(uuid4(), "https://example.com/", diagnostic(), 42, created, created + timedelta(hours=24))
    with pytest.raises(service.PrivacyDiagnosticPurchaseExpiredError):
        service.require_purchasable(expired, now=datetime.now(timezone.utc))
