"""PW-03 PROD promotion PR1: additive schema on disposable PostgreSQL 18.

The old backend and its legacy commerce tables must remain usable after migration.
No Render or PROD database connection is used.
"""
import os
import importlib.util
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from mininode_api.services import access, billing, privacy_diagnostic_snapshot
from mininode_api.services import (
    privacy_correction_plan, privacy_correction_plan_order, privacy_correction_plan_check,
)

BACKEND = Path(__file__).resolve().parents[1]
MIGRATION = "20261026_privacy_entitled_plans.sql"
spec = importlib.util.spec_from_file_location("pw03_prod_runner", BACKEND / "scripts" / "predeploy_migrations.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


@pytest.fixture
def disposable():
    base = os.getenv("DATABASE_URL", "")
    if not base:
        pytest.skip("Disposable mininode_test PostgreSQL required")
    info = conninfo_to_dict(base)
    if info.get("dbname") != "mininode_test" or info.get("host", "localhost") not in {
        "localhost", "127.0.0.1", "postgres",
    }:
        pytest.skip("Only local/CI mininode_test PostgreSQL allowed")
    name = "mininode_test_pw03_" + uuid4().hex[:12]
    with psycopg.connect(base, autocommit=True) as admin:
        assert int(admin.execute("SHOW server_version_num").fetchone()[0]) // 10000 == 18
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            yield make_conninfo(base, dbname=name)
        finally:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def _init_legacy(conn):
    conn.execute(access.INITIALIZE_SQL)
    conn.execute(privacy_diagnostic_snapshot.INITIALIZE_SQL)
    conn.execute(billing.SCHEMA_SQL)
    conn.execute(privacy_correction_plan.INITIALIZE_SQL)
    conn.execute(privacy_correction_plan_order.INITIALIZE_SQL)
    conn.execute(privacy_correction_plan_check.INITIALIZE_SQL)


def test_additive_migration_preserves_old_backend_and_historical_rows(disposable):
    ids = [uuid4() for _ in range(7)]
    user, workspace, site, linked, diagnostic, legacy_plan, old_order = ids
    old_check = uuid4()
    with psycopg.connect(disposable) as conn:
        _init_legacy(conn)
        conn.execute("INSERT INTO access.users(id,email) VALUES (%s,'pw03@example.invalid')", (user,))
        conn.execute("INSERT INTO access.workspaces(id,name) VALUES (%s,'PW03 CI')", (workspace,))
        conn.execute("INSERT INTO access.sites(id,hostname) VALUES (%s,'pw03.example.invalid')", (site,))
        conn.execute("INSERT INTO access.workspace_sites(id,workspace_id,site_id) VALUES (%s,%s,%s)", (linked, workspace, site))
        conn.execute("""INSERT INTO privacy.diagnostic
            (id,site_url,diagnostic_snapshot,score,purchase_expires_at,workspace_site_id)
            VALUES (%s,'https://pw03.example.invalid','{}'::jsonb,60,now()+interval '1 day',%s)""",
            (diagnostic, linked))
        conn.execute("""INSERT INTO privacy.correction_plan
            (id,site_url,token_hash,plan_snapshot,plan_version,actions_version,initial_score)
            VALUES (%s,'https://pw03.example.invalid','pw03-test-hash','{}'::jsonb,'old','old',60)""", (legacy_plan,))
        conn.execute("""INSERT INTO privacy.correction_plan_order
            (id,diagnostic_id,correction_plan_id,site_url,email,product_code,amount,currency,status)
            VALUES (%s,%s,%s,'https://pw03.example.invalid','pw03@example.invalid',
                    'PRIVACY_CORRECTION_PLAN',9900,'CLP','pending_payment')""",
            (old_order, diagnostic, legacy_plan))
        conn.execute("""INSERT INTO privacy.correction_plan_check
            (id,correction_plan_id,order_id,original_diagnostic_id,check_diagnostic_id,result_snapshot)
            VALUES (%s,%s,%s,%s,%s,'{}'::jsonb)""", (old_check, legacy_plan, old_order, diagnostic, diagnostic))
    old_tables = ("privacy.correction_plan", "privacy.correction_plan_order",
                  "privacy.correction_plan_check", "privacy.diagnostic", "billing.orders")
    with psycopg.connect(disposable) as conn:
        before = {t: conn.execute("SELECT count(*) FROM " + t).fetchone()[0] for t in old_tables}
    runner.migrate(disposable, [MIGRATION])
    with psycopg.connect(disposable) as conn:
        assert {t: conn.execute("SELECT count(*) FROM " + t).fetchone()[0] for t in old_tables} == before
        for table in ("privacy.entitled_plan", "privacy.entitled_plan_check"):
            assert conn.execute("SELECT to_regclass(%s)", (table,)).fetchone()[0] is not None
            assert conn.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
        assert conn.execute("SELECT id FROM privacy.correction_plan_order WHERE id=%s", (old_order,)).fetchone()[0] == old_order
        history = conn.execute("SELECT filename,checksum_sha256,applied_at FROM public.schema_migrations WHERE filename=%s", (MIGRATION,)).fetchall()
        assert len(history) == 1
        assert history[0][1] == runner.APPROVED_CHECKSUMS[MIGRATION]
        fk = {(r[0],r[1]) for r in conn.execute("""SELECT c.conrelid::regclass::text, c.confrelid::regclass::text
            FROM pg_constraint c WHERE c.contype='f'
              AND c.conrelid IN ('privacy.entitled_plan'::regclass,'privacy.entitled_plan_check'::regclass)""")}
        assert fk == {
            ("privacy.entitled_plan", "access.workspace_sites"),
            ("privacy.entitled_plan", "access.entitlements"),
            ("privacy.entitled_plan", "privacy.diagnostic"),
            ("privacy.entitled_plan_check", "privacy.entitled_plan"),
            ("privacy.entitled_plan_check", "privacy.diagnostic"),
        }
    runner.migrate(disposable, [MIGRATION])
    with psycopg.connect(disposable) as conn:
        assert conn.execute("SELECT filename,checksum_sha256,applied_at FROM public.schema_migrations WHERE filename=%s", (MIGRATION,)).fetchall() == history
        assert {t: conn.execute("SELECT count(*) FROM " + t).fetchone()[0] for t in old_tables} == before


def test_missing_access_dependencies_rolls_back_ddl_and_history(disposable):
    # Schema is incomplete: the migration must not leave a half-created plan.
    with psycopg.connect(disposable) as conn:
        conn.execute("CREATE SCHEMA privacy")
    with pytest.raises(psycopg.errors.UndefinedTable):
        runner.migrate(disposable, [MIGRATION])
    with psycopg.connect(disposable) as conn:
        assert conn.execute("SELECT to_regclass('privacy.entitled_plan')").fetchone()[0] is None
        assert conn.execute("SELECT to_regclass('privacy.entitled_plan_check')").fetchone()[0] is None
        assert conn.execute("SELECT to_regclass('public.schema_migrations')").fetchone()[0] is None


def test_pw03_migration_is_reviewed_additive_and_requires_explicit_approval(monkeypatch):
    raw = (BACKEND / "migrations" / MIGRATION).read_text(encoding="utf-8")
    statements = raw.upper()
    assert "CREATE TABLE IF NOT EXISTS PRIVACY.ENTITLED_PLAN (" in statements
    assert "CREATE TABLE IF NOT EXISTS PRIVACY.ENTITLED_PLAN_CHECK (" in statements
    assert not any(x in statements for x in ("DROP ", "DELETE FROM", "TRUNCATE ", "UPDATE "))
    sql_text, checksum = runner.load_sql(MIGRATION)
    assert "CREATE TABLE IF NOT EXISTS privacy.entitled_plan" in sql_text
    assert checksum == runner.APPROVED_CHECKSUMS[MIGRATION]
    monkeypatch.delenv("MIGRATION_APPROVED_FILES", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert runner.main() == 0
