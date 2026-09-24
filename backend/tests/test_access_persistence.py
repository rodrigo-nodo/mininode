import sys
from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.main import create_app  # noqa: E402
from mininode_api.services import access  # noqa: E402
from mininode_api.services import (  # noqa: E402
    learn_feedback,
    privacy_correction_plan,
    privacy_correction_plan_check,
    privacy_correction_plan_order,
    privacy_diagnostic_snapshot,
)
from mininode_api.privacy_data.services import data_maps  # noqa: E402


def test_schema_defines_canonical_workspace_hierarchy():
    sql = access.INITIALIZE_SQL

    for table in (
        "access.users",
        "access.workspaces",
        "access.workspace_members",
        "access.companies",
        "access.sites",
        "access.entitlements",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql

    assert "PRIMARY KEY (workspace_id, user_id)" in sql
    assert "REFERENCES access.workspaces(id)" in sql
    assert "REFERENCES access.users(id)" in sql
    assert "REFERENCES access.companies(id)" in sql
    assert "REFERENCES access.sites(id)" in sql

    assert "email = lower(btrim(email))" in sql
    assert "hostname = lower(btrim(hostname))" in sql
    assert "UNIQUE (company_id, hostname)" in sql

    assert "product_code TEXT NOT NULL" in sql
    assert "active_from TIMESTAMPTZ NOT NULL" in sql
    assert "active_until TIMESTAMPTZ NULL" in sql
    assert "status TEXT NOT NULL" in sql
    assert "source TEXT NOT NULL" in sql
    assert "source_id TEXT NULL" in sql
    assert "active_until IS NULL OR active_until > active_from" in sql


def test_initialize_database_executes_schema_once(monkeypatch):
    executions = []

    class Cursor:
        def execute(self, statement, params=None):
            executions.append((statement, params))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class Connection:
        def cursor(self):
            return Cursor()

    @contextmanager
    def connection():
        yield Connection()

    monkeypatch.setattr(access, "_connection", connection)
    access.initialize_database()

    assert executions == [(access.INITIALIZE_SQL, None)]


def _stub_other_database_initializers(monkeypatch):
    for module in (
        learn_feedback,
        privacy_correction_plan,
        privacy_diagnostic_snapshot,
        privacy_correction_plan_order,
        privacy_correction_plan_check,
        data_maps,
    ):
        monkeypatch.setattr(module, "initialize_database", lambda: None)


def test_startup_initializes_access_independently(monkeypatch):
    _stub_other_database_initializers(monkeypatch)
    calls = []
    monkeypatch.setattr(access, "initialize_database", lambda: calls.append("access"))

    app = create_app()
    assert app.state.access_ready is False

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert app.state.access_ready is True

    assert calls == ["access"]


def test_access_startup_failure_does_not_break_health(monkeypatch, caplog):
    _stub_other_database_initializers(monkeypatch)

    def fail():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(access, "initialize_database", fail)

    app = create_app()
    with caplog.at_level("ERROR"), TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert app.state.access_ready is False

    assert "Access database initialization failed" in caplog.text
