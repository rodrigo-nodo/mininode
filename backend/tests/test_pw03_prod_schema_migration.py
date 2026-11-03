"""PW-03 PROD promotion PR1: additive schema on disposable PostgreSQL 18.

Historical commerce tables and data remain intact after migration.
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
from tests.legacy_privacy_schema import LEGACY_PLAN_SQL, LEGACY_ORDER_SQL, LEGACY_CHECK_SQL

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
    conn.execute(LEGACY_PLAN_SQL)
    conn.execute(LEGACY_ORDER_SQL)
    conn.execute(LEGACY_CHECK_SQL)


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
    with pytest.raises((psycopg.errors.InvalidSchemaName, psycopg.errors.UndefinedTable)):
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


# PW-03 PR5 is an explicitly manual operation, NEVER a pre-deploy migration.
RETIREMENT_SCRIPT = BACKEND / "operations" / "pw03_pr5_retire_legacy_commerce.sql"
PREFLIGHT_SCRIPT = BACKEND / "operations" / "pw03_pr5_readonly_preflight.sql"


@pytest.fixture
def pr5_legacy_data(disposable):
    """Realistic historical and new Plan rows in a disposable PostgreSQL 18 DB."""
    with psycopg.connect(disposable) as db:
        _init_legacy(db)
    runner.migrate(disposable, [MIGRATION])
    user, workspace, site, site_link, diagnostic = (uuid4() for _ in range(5))
    old_plans = [uuid4(), uuid4()]
    old_orders = [uuid4(), uuid4(), uuid4()]
    old_check, entitlement, entitled_plan, entitled_check = (uuid4() for _ in range(4))
    with psycopg.connect(disposable) as db:
        db.execute("INSERT INTO access.users(id,email) VALUES (%s,'pr5@example.invalid')", (user,))
        db.execute("INSERT INTO access.workspaces(id,name) VALUES (%s,'PR5 isolated')", (workspace,))
        db.execute("INSERT INTO access.sites(id,hostname) VALUES (%s,'pr5.example.invalid')", (site,))
        db.execute("INSERT INTO access.workspace_sites(id,workspace_id,site_id) VALUES (%s,%s,%s)",
                   (site_link, workspace, site))
        db.execute("""INSERT INTO privacy.diagnostic
            (id,site_url,diagnostic_snapshot,score,purchase_expires_at,workspace_site_id)
            VALUES (%s,'https://pr5.example.invalid','{}'::jsonb,60,now()+interval '1 day',%s)""",
                   (diagnostic, site_link))
        for number, old_plan in enumerate(old_plans):
            db.execute("""INSERT INTO privacy.correction_plan
                (id,site_url,token_hash,plan_snapshot,plan_version,actions_version,initial_score)
                VALUES (%s,'https://pr5.example.invalid',%s,'{}'::jsonb,'old','old',60)""",
                       (old_plan, f"pr5-test-token-{number}"))
        for number, old_order in enumerate(old_orders):
            paid = number < 2
            db.execute("""INSERT INTO privacy.correction_plan_order
                (id,diagnostic_id,correction_plan_id,site_url,email,product_code,amount,currency,status,paid_at)
                VALUES (%s,%s,%s,'https://pr5.example.invalid','pr5@example.invalid',
                        'PRIVACY_CORRECTION_PLAN',9900,'CLP',%s,
                        CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE NULL END)""",
                       (old_order, diagnostic, old_plans[number] if paid else None,
                        'paid' if paid else 'pending_payment', paid))
        db.execute("""INSERT INTO privacy.correction_plan_check
            (id,correction_plan_id,order_id,original_diagnostic_id,check_diagnostic_id,result_snapshot)
            VALUES (%s,%s,%s,%s,%s,'{}'::jsonb)""",
                   (old_check, old_plans[0], old_orders[0], diagnostic, diagnostic))
        db.execute("""INSERT INTO access.entitlements
            (id,workspace_site_id,product_code,active_from,active_until,status,source)
            VALUES (%s,%s,'privacy_web',now(),now()+interval '1 month','active','internal_grant')""",
                   (entitlement, site_link))
        db.execute("""INSERT INTO privacy.entitled_plan
            (id,workspace_site_id,entitlement_id,original_diagnostic_id,plan_snapshot)
            VALUES (%s,%s,%s,%s,'{}'::jsonb)""",
                   (entitled_plan, site_link, entitlement, diagnostic))
        db.execute("""INSERT INTO privacy.entitled_plan_check
            (id,entitled_plan_id,check_diagnostic_id,result_snapshot)
            VALUES (%s,%s,%s,'{}'::jsonb)""",
                   (entitled_check, entitled_plan, diagnostic))
    return dict(url=disposable, diagnostic=diagnostic, entitlement=entitlement,
                entitled_plan=entitled_plan, entitled_check=entitled_check,
                old_plans=old_plans, old_orders=old_orders)


def _pr5_preflight(conn):
    """Synthetic-only preflight. PROD fingerprints require independent review."""
    return conn.execute(PREFLIGHT_SCRIPT.read_text(encoding="utf-8")).fetchone()


def _ack_pr5(conn, database_name, *, user_name=None, include_ack=True):
    """Only public destination and approval constants; no fingerprint hashes."""
    conn.execute("SELECT set_config('mininode.pw03_pr5_target_database', %s, false)",
                 (database_name,))
    conn.execute("SELECT set_config('mininode.pw03_pr5_target_user', %s, false)",
                 (user_name if user_name is not None
                  else conn.execute("SELECT current_user").fetchone()[0],))
    if include_ack:
        conn.execute("SELECT set_config('mininode.pw03_pr5_ack', %s, false)",
                     ("DELETE_2_PAID_1_PENDING_LEGACY_ORDERS",))


def _pr5_tables(conn):
    return {
        name: conn.execute("SELECT to_regclass(%s)", ("privacy." + name,)).fetchone()[0]
        for name in ("correction_plan", "correction_plan_order", "correction_plan_check")
    }


def test_pr5_script_manual_transaction_and_exact_drop_contract():
    body = RETIREMENT_SCRIPT.read_text(encoding="utf-8")
    preflight = PREFLIGHT_SCRIPT.read_text(encoding="utf-8")
    assert not (BACKEND / "migrations" / RETIREMENT_SCRIPT.name).exists()
    assert RETIREMENT_SCRIPT.name not in runner.APPROVED_CHECKSUMS
    with pytest.raises(ValueError, match="not in reviewed catalog"):
        runner.load_sql(RETIREMENT_SCRIPT.name)
    assert body.count("DROP TABLE privacy.") == 3
    assert body.count(" RESTRICT;") == 3
    assert body.count("COMMIT;") == 1
    assert "BEGIN;" in body and "ACCESS EXCLUSIVE MODE NOWAIT" in body
    assert "CASCADE;" not in body
    assert "approved_inventory_sha256" not in body
    assert "fingerprint" not in body.lower()
    assert "sha256(" not in body.lower()
    assert "sha256(" not in preflight.lower()
    assert "set_config" not in preflight.lower()
    for protected in ("privacy.diagnostic", "privacy.entitled_plan",
                      "privacy.entitled_plan_check", "billing.orders",
                      "access.entitlements"):
        assert "DROP TABLE " + protected not in body


def test_pr5_without_any_approval_keeps_all_data(pr5_legacy_data):
    p = pr5_legacy_data
    with pytest.raises(psycopg.errors.RaiseException, match="database/user"):
        with psycopg.connect(p["url"], autocommit=True) as conn:
            conn.execute(RETIREMENT_SCRIPT.read_text(encoding="utf-8"))
    with psycopg.connect(p["url"]) as db:
        assert all(_pr5_tables(db).values())


@pytest.mark.parametrize("bad", ["database", "user", "ack"])
def test_pr5_sql_refuses_wrong_destination_or_ack(pr5_legacy_data, bad):
    p = pr5_legacy_data
    with psycopg.connect(p["url"], autocommit=True) as conn:
        db = conn.execute("SELECT current_database()").fetchone()[0]
        if bad == "database":
            _ack_pr5(conn, "different_database")
        elif bad == "user":
            _ack_pr5(conn, db, user_name="other_user")
        else:
            _ack_pr5(conn, db, include_ack=False)
        with pytest.raises(psycopg.errors.RaiseException,
                           match="database/user|destructive acknowledgement"):
            conn.execute(RETIREMENT_SCRIPT.read_text(encoding="utf-8"))
    with psycopg.connect(p["url"]) as db:
        assert all(_pr5_tables(db).values())


def test_pr5_sql_rejects_changed_paid_status_without_partial_delete(pr5_legacy_data):
    p = pr5_legacy_data
    with psycopg.connect(p["url"]) as conn:
        conn.execute("UPDATE privacy.correction_plan_order SET status='cancelled' WHERE id=%s",
                     (p["old_orders"][2],))
    with psycopg.connect(p["url"], autocommit=True) as conn:
        _ack_pr5(conn, conn.execute("SELECT current_database()").fetchone()[0])
        with pytest.raises(psycopg.errors.RaiseException, match="legacy inventory"):
            conn.execute(RETIREMENT_SCRIPT.read_text(encoding="utf-8"))
    with psycopg.connect(p["url"]) as db:
        assert all(_pr5_tables(db).values())
        assert db.execute("SELECT count(*) FROM privacy.correction_plan_order").fetchone()[0] == 3


def test_pr5_sql_rejects_broken_relation_with_unchanged_counts(pr5_legacy_data):
    p = pr5_legacy_data
    with psycopg.connect(p["url"]) as conn:
        # Valid FK, invalid business link: review points to a different paid order.
        conn.execute("UPDATE privacy.correction_plan_check SET order_id=%s",
                     (p["old_orders"][1],))
    with psycopg.connect(p["url"], autocommit=True) as conn:
        _ack_pr5(conn, conn.execute("SELECT current_database()").fetchone()[0])
        with pytest.raises(psycopg.errors.RaiseException, match="legacy inventory"):
            conn.execute(RETIREMENT_SCRIPT.read_text(encoding="utf-8"))
    with psycopg.connect(p["url"]) as db:
        assert all(_pr5_tables(db).values())


def test_pr5_sql_restrict_rolls_back_all_drops(pr5_legacy_data):
    p = pr5_legacy_data
    with psycopg.connect(p["url"]) as conn:
        conn.execute("""CREATE TABLE public.external_legacy_reference (
            plan_id uuid REFERENCES privacy.correction_plan(id))""")
    with psycopg.connect(p["url"], autocommit=True) as conn:
        _ack_pr5(conn, conn.execute("SELECT current_database()").fetchone()[0])
        with pytest.raises(psycopg.errors.DependentObjectsStillExist):
            conn.execute(RETIREMENT_SCRIPT.read_text(encoding="utf-8"))
    with psycopg.connect(p["url"]) as db:
        assert all(_pr5_tables(db).values())
        assert db.execute("SELECT count(*) FROM privacy.correction_plan_order").fetchone()[0] == 3


def test_pr5_readonly_preflight_returns_only_structural_manifest(pr5_legacy_data):
    p = pr5_legacy_data
    preflight = PREFLIGHT_SCRIPT.read_text(encoding="utf-8")
    assert not any(x in preflight.upper() for x in
                   ("DROP TABLE", "DELETE FROM", "TRUNCATE", "UPDATE "))
    with psycopg.connect(p["url"]) as conn:
        row = _pr5_preflight(conn)
        assert row[0] == conn.execute("SELECT current_database()").fetchone()[0]
        assert row[2] is False
        assert len(row[3]) == 2 and len(row[4]) == 3 and len(row[5]) == 1
        assert {v["id"] for v in row[4]} == {str(x) for x in p["old_orders"]}
        assert {v["status"] for v in row[4]} == {"paid", "pending_payment"}


def test_pr5_retirement_preserves_current_product_data(pr5_legacy_data):
    p = pr5_legacy_data
    with psycopg.connect(p["url"], autocommit=True) as conn:
        _ack_pr5(conn, conn.execute("SELECT current_database()").fetchone()[0])
        conn.execute(RETIREMENT_SCRIPT.read_text(encoding="utf-8"))
    with psycopg.connect(p["url"]) as conn:
        assert not any(_pr5_tables(conn).values())
        assert conn.execute("SELECT id FROM privacy.diagnostic WHERE id=%s",
                            (p["diagnostic"],)).fetchone()[0] == p["diagnostic"]
        assert conn.execute("SELECT id FROM access.entitlements WHERE id=%s",
                            (p["entitlement"],)).fetchone()[0] == p["entitlement"]
        assert conn.execute("SELECT id FROM privacy.entitled_plan WHERE id=%s",
                            (p["entitled_plan"],)).fetchone()[0] == p["entitled_plan"]
        assert conn.execute("SELECT id FROM privacy.entitled_plan_check WHERE id=%s",
                            (p["entitled_check"],)).fetchone()[0] == p["entitled_check"]
        assert conn.execute("SELECT count(*) FROM billing.orders").fetchone()[0] == 0
        from mininode_api.services import site_group_operator
        with conn.cursor() as cur:
            site_group_operator._require_no_legacy_orders(
                cur, tuple(), frozenset(("pr5.example.invalid",))
            )


# PW-03 Render Shell executable: manual CLI + actual SQL on disposable PG18.
SHELL_SCRIPT = BACKEND / "scripts" / "pw03_retire_legacy_shell.py"
shell_spec = importlib.util.spec_from_file_location("pw03_shell", SHELL_SCRIPT)
shell = importlib.util.module_from_spec(shell_spec)
shell_spec.loader.exec_module(shell)


def _synthetic_render_env(commit="a" * 40):
    return {
        **shell.EXPECTED_RENDER,
        "RENDER_GIT_COMMIT": commit,
        "DATABASE_URL": "postgresql://mininode_user:fake@"
                        + shell.EXPECTED_POSTGRES_ID + "/mininode",
    }


def test_pr5_shell_only_check_or_execute_and_image_copy_contract(monkeypatch, capsys):
    assert shell.main([]) == 0
    assert "Sin operación" in capsys.readouterr().out
    assert "operations/pw03_pr5_retire_legacy_commerce.sql" in (
        BACKEND / "Dockerfile").read_text(encoding="utf-8")
    assert "operations/pw03_pr5_readonly_preflight.sql" in (
        BACKEND / "Dockerfile").read_text(encoding="utf-8")
    assert "scripts/pw03_retire_legacy_shell.py" not in (
        BACKEND / "scripts" / "predeploy_migrations.py").read_text(encoding="utf-8")
    assert shell.OLD_TABLES == (
        "privacy.correction_plan", "privacy.correction_plan_order",
        "privacy.correction_plan_check",
    )


def test_pr5_shell_rejects_wrong_runtime_and_wrong_url():
    env = _synthetic_render_env()
    assert shell.validate_render_env(env) == "a" * 40
    for key in shell.EXPECTED_RENDER:
        wrong = dict(env, **{key: "incorrect"})
        with pytest.raises(shell.GuardError, match="Render PROD"):
            shell.validate_render_env(wrong)
    # A display name can differ from the dashboard name or change. It
    # must not gate an otherwise verified service, unlike the immutable ID.
    assert shell.validate_render_env({**env, "RENDER_SERVICE_NAME": "other-display-name"}) == "a" * 40
    assert shell.validate_render_env({k: v for k, v in env.items()
                                      if k != "RENDER_SERVICE_NAME"}) == "a" * 40
    with pytest.raises(shell.GuardError, match="RENDER_SERVICE_ID"):
        shell.validate_render_env({**env, "RENDER_SERVICE_ID": "srv-other"})
    with pytest.raises(shell.GuardError, match="commit desplegado"):
        shell.validate_render_env(dict(env, RENDER_GIT_COMMIT="invalid"))
    shell.validate_database_url(env["DATABASE_URL"], env)
    for invalid_url in (
        "postgresql://mininode_user:fake@dpg-wrong-id/mininode",
        "postgresql://mininode_user:fake@" + shell.EXPECTED_POSTGRES_ID
            + ".attacker.example/mininode",
        "postgresql://mininode_user:fake@" + shell.EXPECTED_POSTGRES_ID
            + ".oregon-postgres.render.com/mininode",
        "postgresql://mininode_user:fake@" + shell.EXPECTED_POSTGRES_ID
            + ",dpg-wrong-id/mininode",
        "postgresql://mininode_user:fake@localhost/mininode",
    ):
        with pytest.raises(shell.GuardError, match="Host PostgreSQL"):
            shell.validate_database_url(invalid_url, env)
    for invalid_url in (
        "postgresql://mininode_user:fake@" + shell.EXPECTED_POSTGRES_ID
            + "/mininode?hostaddr=127.0.0.1",
        "postgresql://mininode_user:fake@" + shell.EXPECTED_POSTGRES_ID
            + "/mininode?service=evil",
        "postgresql://mininode_user:fake@" + shell.EXPECTED_POSTGRES_ID
            + "/mininode?target_session_attrs=any",
        "postgresql://mininode_user:fake@" + shell.EXPECTED_POSTGRES_ID
            + "/mininode?options=-c%20search_path%3Dpublic",
    ):
        with pytest.raises(shell.GuardError, match="parámetros libpq"):
            shell.validate_database_url(invalid_url, env)
    for setting in ("PGHOSTADDR", "PGHOST", "PGSERVICE", "PGSERVICEFILE",
                    "PGOPTIONS", "PGPASSWORD", "PGLOADBALANCEHOSTS",
                    "PGFUTURE_NETWORK_OVERRIDE"):
        with pytest.raises(shell.GuardError, match="PG\\*"):
            shell.validate_database_url(env["DATABASE_URL"], {**env, setting: "redirect"})
    with pytest.raises(shell.GuardError, match="usuario"):
        shell.validate_database_url(
            "postgresql://another_user:fake@" + shell.EXPECTED_POSTGRES_ID + "/mininode", env)
    with pytest.raises(shell.GuardError, match="contraseña"):
        shell.validate_database_url(
            "postgresql://mininode_user@" + shell.EXPECTED_POSTGRES_ID + "/mininode", env)
    with pytest.raises(shell.GuardError, match="Puerto"):
        shell.validate_database_url(env["DATABASE_URL"] + "?port=5433", env)
    with pytest.raises(shell.GuardError, match="TLS"):
        shell.validate_database_url(env["DATABASE_URL"] + "?sslmode=disable", env)
    shell.validate_database_url(env["DATABASE_URL"] + "?sslmode=require", env)
    with pytest.raises(shell.GuardError, match="DATABASE_URL"):
        shell.validate_database_url("", env)


def test_pr5_shell_rejects_libpq_hostaddr_before_connect(monkeypatch, capsys):
    env = {**_synthetic_render_env(), "PGHOSTADDR": "127.0.0.1"}
    monkeypatch.setattr(shell.os, "environ", env)
    monkeypatch.setattr(shell.psycopg, "connect",
                        lambda *args, **kw: pytest.fail("must not connect"))
    assert shell.main(["--check"]) == 1
    assert "FAIL" in capsys.readouterr().err


def test_pr5_shell_execute_refuses_non_tty_before_connect(monkeypatch, capsys):
    monkeypatch.setattr(shell.os, "environ", _synthetic_render_env())
    monkeypatch.setattr(shell, "_require_interactive_tty", lambda: (_ for _ in ()).throw(
        shell.GuardError("No TTY")))
    monkeypatch.setattr(shell.psycopg, "connect",
                        lambda *a, **kw: pytest.fail("must not connect"))
    assert shell.main(["--execute"]) == 1
    assert "FAIL" in capsys.readouterr().err


def test_pr5_shell_confirmation_rejects_wrong_sha_and_phrase(monkeypatch):
    sha = "a" * 40
    monkeypatch.setattr("builtins.input", lambda prompt: (
        shell.EXPECTED_POSTGRES_ID if "postgresId" in prompt else "f" * 40))
    monkeypatch.setattr(shell.getpass, "getpass",
                        lambda prompt: shell.EXPLICIT_APPROVAL)
    with pytest.raises(shell.GuardError, match="Identidad"):
        shell.confirm_destructive_approval(sha)

    monkeypatch.setattr("builtins.input", lambda prompt: (
        shell.EXPECTED_POSTGRES_ID if "postgresId" in prompt else sha))
    monkeypatch.setattr(shell.getpass, "getpass", lambda prompt: "incorrect")
    with pytest.raises(shell.GuardError, match="autorización destructiva"):
        shell.confirm_destructive_approval(sha)
    monkeypatch.setattr(shell.getpass, "getpass",
                        lambda prompt: shell.EXPLICIT_APPROVAL)
    assert shell.confirm_destructive_approval(sha) is None


def test_pr5_shell_never_echoes_confirmation(monkeypatch):
    import warnings
    sha = "a" * 40
    monkeypatch.setattr("builtins.input", lambda prompt: (
        shell.EXPECTED_POSTGRES_ID if "postgresId" in prompt else sha))

    def unsafe_getpass(prompt):
        warnings.warn("Echo fallback", shell.getpass.GetPassWarning)
    monkeypatch.setattr(shell.getpass, "getpass", unsafe_getpass)
    with pytest.raises(shell.getpass.GetPassWarning):
        shell.confirm_destructive_approval(sha)


@pytest.fixture
def pr5_shell_data(pr5_legacy_data, monkeypatch):
    info = conninfo_to_dict(pr5_legacy_data["url"])
    monkeypatch.setattr(shell, "EXPECTED_DATABASE", info["dbname"])
    monkeypatch.setattr(shell, "EXPECTED_DB_USER", info.get("user", "postgres"))
    return pr5_legacy_data


def test_pr5_shell_check_is_readonly(pr5_shell_data):
    from psycopg.rows import dict_row
    with psycopg.connect(pr5_shell_data["url"], autocommit=True,
                         row_factory=dict_row) as conn:
        assert shell.check_only(conn) == {
            "planes_antiguos": 2, "ordenes_antiguas": 3, "revisiones_antiguas": 1,
        }
        assert conn.execute("SHOW default_transaction_read_only").fetchone() == {
            "default_transaction_read_only": "on",
        }
        assert all(conn.execute("SELECT to_regclass(%s) AS target",
                                (name,)).fetchone()["target"]
                   for name in shell.OLD_TABLES)


def test_pr5_shell_check_rejects_incorrect_order_status(pr5_shell_data):
    from psycopg.rows import dict_row
    p = pr5_shell_data
    with psycopg.connect(p["url"]) as conn:
        conn.execute("UPDATE privacy.correction_plan_order SET status='cancelled' WHERE id=%s",
                     (p["old_orders"][2],))
    with psycopg.connect(p["url"], autocommit=True, row_factory=dict_row) as conn:
        with pytest.raises(shell.GuardError, match="órdenes"):
            shell.check_only(conn)
        assert all(conn.execute("SELECT to_regclass(%s) AS target",
                                (name,)).fetchone()["target"]
                   for name in shell.OLD_TABLES)


def test_pr5_shell_check_rejects_wrong_review_link(pr5_shell_data):
    from psycopg.rows import dict_row
    p = pr5_shell_data
    with psycopg.connect(p["url"]) as conn:
        conn.execute("UPDATE privacy.correction_plan_check SET order_id=%s",
                     (p["old_orders"][1],))
    with psycopg.connect(p["url"], autocommit=True, row_factory=dict_row) as conn:
        with pytest.raises(shell.GuardError, match="revisión antigua"):
            shell.check_only(conn)


def test_pr5_shell_execute_requires_autocommit_and_primary(pr5_shell_data):
    from psycopg.rows import dict_row
    p = pr5_shell_data
    with psycopg.connect(p["url"], row_factory=dict_row) as conn:
        with pytest.raises(shell.GuardError, match="autocommit"):
            shell.execute_retirement(conn)


def test_pr5_shell_execute_reuses_connection_preserves_new_data(pr5_shell_data):
    from psycopg.rows import dict_row
    p = pr5_shell_data
    with psycopg.connect(p["url"], autocommit=True, row_factory=dict_row) as conn:
        shell.execute_retirement(conn)
        assert all(conn.execute("SELECT to_regclass(%s) AS target",
                                (name,)).fetchone()["target"] is None
                   for name in shell.OLD_TABLES)
        assert conn.execute("SELECT count(*) AS n FROM privacy.entitled_plan").fetchone()["n"] == 1
        assert conn.execute("SELECT count(*) AS n FROM privacy.diagnostic").fetchone()["n"] == 1
        assert conn.execute("SELECT count(*) AS n FROM billing.orders").fetchone()["n"] == 0


def test_pr5_shell_execute_rejects_bad_inventory_without_drops(pr5_shell_data):
    from psycopg.rows import dict_row
    p = pr5_shell_data
    with psycopg.connect(p["url"]) as conn:
        conn.execute("UPDATE privacy.correction_plan_order SET status='cancelled' WHERE id=%s",
                     (p["old_orders"][2],))
    with psycopg.connect(p["url"], autocommit=True, row_factory=dict_row) as conn:
        with pytest.raises(psycopg.errors.RaiseException, match="legacy inventory"):
            shell.execute_retirement(conn)
        assert all(conn.execute("SELECT to_regclass(%s) AS target",
                                (name,)).fetchone()["target"]
                   for name in shell.OLD_TABLES)


def test_pr5_shell_full_manual_execute_one_connection(pr5_shell_data, monkeypatch, capsys):
    from psycopg.rows import dict_row
    p = pr5_shell_data
    sha = "a" * 40
    env = {
        **shell.EXPECTED_RENDER,
        "RENDER_GIT_COMMIT": sha,
        "DATABASE_URL": "postgresql://postgres:synthetic@"
                        + shell.EXPECTED_POSTGRES_ID
                        + "/" + conninfo_to_dict(p["url"])["dbname"],
    }
    real_connect = psycopg.connect
    connections = []

    def connect_once(url, **options):
        assert url == env["DATABASE_URL"]
        connections.append(True)
        return real_connect(p["url"], **options)

    monkeypatch.setattr(shell.os, "environ", env)
    monkeypatch.setattr(shell.psycopg, "connect", connect_once)
    monkeypatch.setattr(shell, "_require_interactive_tty", lambda: None)
    monkeypatch.setattr("builtins.input", lambda prompt: (
        shell.EXPECTED_POSTGRES_ID if "postgresId" in prompt else sha))
    monkeypatch.setattr(shell.getpass, "getpass",
                        lambda prompt: shell.EXPLICIT_APPROVAL)
    assert shell.main(["--execute"]) == 0
    output = capsys.readouterr().out
    assert "PASS: retiro manual confirmado" in output
    assert "planes_antiguos=2" in output
    assert len(connections) == 1
    with real_connect(p["url"]) as conn:
        assert not any(_pr5_tables(conn).values())
        assert conn.execute("SELECT count(*) FROM privacy.entitled_plan").fetchone()[0] == 1


def test_pr5_shell_no_hash_payloads_or_sensitive_logging_guard():
    script = SHELL_SCRIPT.read_text(encoding="utf-8")
    assert "approved_inventory_sha256" not in script
    assert "cluster_fingerprint_sha256" not in script
    assert "log_parameter_max_length" not in script
    assert "read_approved_values" not in script
    assert "EXPLICIT_APPROVAL" in script
    assert "EXPECTED_INTERNAL_HOST" in script


