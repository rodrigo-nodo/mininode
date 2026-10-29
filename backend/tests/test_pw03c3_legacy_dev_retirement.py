"""PW-03C3 DEV retirement proposal: tests only on disposable CI PostgreSQL.

The real DEV/PROD databases are never targeted by these tests or this PR.
"""
from pathlib import Path
import os
from uuid import uuid4

import psycopg
from psycopg.conninfo import conninfo_to_dict
import pytest

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_NAME = "20261029_pw03c3_retire_legacy_dev.sql"
MIGRATION = ROOT / "migrations" / MIGRATION_NAME
PREDEPLOY = ROOT / "scripts" / "predeploy_migrations.py"
OPERATOR = ROOT / "src" / "mininode_api" / "services" / "site_group_operator.py"


def _url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        pytest.skip("Disposable mininode_test PostgreSQL is required")
    parsed = conninfo_to_dict(url)
    if parsed.get("dbname") != "mininode_test" or parsed.get("host", "localhost") not in (
        "localhost", "127.0.0.1", "postgres"
    ):
        pytest.skip("Refuse database outside disposable local/CI mininode_test")
    return url


@pytest.fixture
def legacy():
    url = _url()
    schema = "pw03c3_ci_" + uuid4().hex
    source = MIGRATION.read_text(encoding="utf-8")
    sql = source.replace("'mininode_db_dev'", "'mininode_test'").replace(
        "privacy.", f"{schema}."
    )
    # One uncommitted transaction owns all synthetic objects, including
    # a model-new sentinel. Rollback restores the original CI DB state.
    with psycopg.connect(url) as conn:
        cur = conn.cursor()
        cur.execute(f"CREATE SCHEMA {schema}")
        cur.execute(f"CREATE TABLE {schema}.correction_plan (id integer PRIMARY KEY)")
        cur.execute(
            f"CREATE TABLE {schema}.correction_plan_order ("
            f"id integer PRIMARY KEY, correction_plan_id integer REFERENCES {schema}.correction_plan(id))"
        )
        cur.execute(
            f"CREATE TABLE {schema}.correction_plan_check ("
            f"id integer PRIMARY KEY, order_id integer REFERENCES {schema}.correction_plan_order(id))"
        )
        cur.execute(f"CREATE TABLE {schema}.entitled_plan (id integer PRIMARY KEY)")
        cur.execute(f"CREATE TABLE {schema}.entitled_plan_check (id integer PRIMARY KEY)")
        yield cur, schema, sql
        conn.rollback()


def _execute_rollback_on_error(cur, sql):
    cur.execute("SAVEPOINT pw03c3_before")
    try:
        cur.execute(sql)
    except psycopg.Error:
        cur.execute("ROLLBACK TO SAVEPOINT pw03c3_before")
        raise


def test_dev_only_and_manual_approval_contract():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "current_database() <> 'mininode_db_dev'" in sql
    assert "IN ACCESS EXCLUSIVE MODE NOWAIT" in sql
    assert "DROP TABLE privacy.correction_plan_check" in sql
    assert "RESTRICT" in sql
    assert "CASCADE" not in sql.split("DROP TABLE", 1)[1]
    assert "privacy.diagnostic" not in sql.split("DROP TABLE", 1)[1]
    # The predeploy runner cannot apply an unregistered destructive file.
    import importlib.util
    spec = importlib.util.spec_from_file_location("pw03c3_predeploy", PREDEPLOY)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    assert MIGRATION_NAME not in runner.APPROVED_CHECKSUMS
    with pytest.raises(ValueError, match="not in reviewed catalog"):
        runner.load_sql(MIGRATION_NAME)
    # PROD is unchanged: the grouping guard still checks legacy orders.
    guard = OPERATOR.read_text(encoding="utf-8")
    assert "to_regclass('privacy.correction_plan_order')" in guard
    assert "LOCK TABLE privacy.correction_plan_order IN SHARE MODE NOWAIT" in guard
    assert "SELECT d.workspace_site_id, o.site_url" in guard


def test_wrong_database_fails_before_any_ddl(legacy):
    cur, schema, _ = legacy
    with pytest.raises(psycopg.errors.RaiseException, match="DEV-only"):
        _execute_rollback_on_error(cur, MIGRATION.read_text(encoding="utf-8"))
    assert cur.execute(
        "SELECT to_regclass(%s)::text", (f"{schema}.correction_plan",)
    ).fetchone()[0] is not None


def test_empty_tables_are_retired_and_new_model_survives(legacy):
    cur, schema, sql = legacy
    cur.execute(f"INSERT INTO {schema}.entitled_plan VALUES (1)")
    cur.execute(f"INSERT INTO {schema}.entitled_plan_check VALUES (2)")
    cur.execute(sql)
    for name in ("correction_plan", "correction_plan_order", "correction_plan_check"):
        assert cur.execute(
            "SELECT to_regclass(%s)::text", (f"{schema}.{name}",)
        ).fetchone()[0] is None
    assert cur.execute(f"SELECT count(*) FROM {schema}.entitled_plan").fetchone()[0] == 1
    assert cur.execute(f"SELECT count(*) FROM {schema}.entitled_plan_check").fetchone()[0] == 1


@pytest.mark.parametrize("table", ("correction_plan", "correction_plan_order", "correction_plan_check"))
def test_any_nonempty_table_blocks_every_drop(legacy, table):
    cur, schema, sql = legacy
    cur.execute(f"INSERT INTO {schema}.{table}(id) VALUES (1)")
    with pytest.raises(psycopg.errors.RaiseException, match="not empty"):
        _execute_rollback_on_error(cur, sql)
    for name in ("correction_plan", "correction_plan_order", "correction_plan_check"):
        assert cur.execute(
            "SELECT to_regclass(%s)::text", (f"{schema}.{name}",)
        ).fetchone()[0] is not None
    assert cur.execute(f"SELECT count(*) FROM {schema}.{table}").fetchone()[0] == 1


def test_missing_table_fails_closed(legacy):
    cur, schema, sql = legacy
    cur.execute(f"DROP TABLE {schema}.correction_plan_check")
    with pytest.raises(psycopg.errors.RaiseException, match="expected legacy tables missing"):
        _execute_rollback_on_error(cur, sql)
    assert cur.execute(
        "SELECT to_regclass(%s)::text", (f"{schema}.correction_plan_order",)
    ).fetchone()[0] is not None


def test_unexpected_dependent_object_blocks_without_cascade(legacy):
    cur, schema, sql = legacy
    cur.execute(
        f"CREATE TABLE {schema}.external_reference ("
        f"plan_id integer REFERENCES {schema}.correction_plan(id))"
    )
    with pytest.raises(psycopg.errors.DependentObjectsStillExist):
        _execute_rollback_on_error(cur, sql)
    for name in ("correction_plan", "correction_plan_order", "correction_plan_check"):
        assert cur.execute(
            "SELECT to_regclass(%s)::text", (f"{schema}.{name}",)
        ).fetchone()[0] is not None
    assert cur.execute(
        "SELECT to_regclass(%s)::text", (f"{schema}.external_reference",)
    ).fetchone()[0] is not None
