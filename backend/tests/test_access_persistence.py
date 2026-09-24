import os
import sys
from contextlib import contextmanager
from pathlib import Path

import psycopg
import pytest
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


def test_access_schema_executes_twice_on_real_postgres():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required for the PostgreSQL integration test")

    expected_tables = {
        "users",
        "workspaces",
        "workspace_members",
        "companies",
        "sites",
        "entitlements",
    }

    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA IF EXISTS access CASCADE")

    try:
        access.initialize_database()
        access.initialize_database()

        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'access'
                """
            )
            assert {row[0] for row in cursor.fetchall()} == expected_tables

            cursor.execute(
                """
                SELECT con.conname, con.contype, pg_get_constraintdef(con.oid)
                FROM pg_constraint con
                JOIN pg_class c ON c.oid = con.conrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'access'
                """
            )
            constraints = cursor.fetchall()
            constraint_names = {row[0] for row in constraints}
            definitions = [row[2] for row in constraints]

            assert sum(row[1] == "f" for row in constraints) == 5
            assert any(definition == "UNIQUE (email)" for definition in definitions)
            assert "access_sites_company_hostname_unique" in constraint_names
            assert "access_entitlements_window_check" in constraint_names
            assert "access_users_email_normalized_check" in constraint_names
            assert "access_sites_hostname_normalized_check" in constraint_names

            cursor.execute(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'access'
                """
            )
            indexes = {row[0] for row in cursor.fetchall()}
            assert {
                "access_workspace_members_user_idx",
                "access_companies_workspace_idx",
                "access_sites_company_idx",
                "access_entitlements_site_product_idx",
            }.issubset(indexes)
    finally:
        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA IF EXISTS access CASCADE")
