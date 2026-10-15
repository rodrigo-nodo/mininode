"""Real PostgreSQL contract tests. Only CI's disposable DATABASE_URL is allowed."""
import hashlib
import importlib.util
import os
import threading
import uuid
from pathlib import Path

import psycopg
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "predeploy_migrations.py"
spec = importlib.util.spec_from_file_location("predeploy_migrations", SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


@pytest.fixture
def pg(monkeypatch, tmp_path):
    url = os.getenv("DATABASE_URL")
    if not url or "mininode_test" not in url:
        pytest.skip("Only disposable mininode_test PostgreSQL is permitted")
    monkeypatch.setattr(runner, "MIGRATIONS_DIR", tmp_path)
    monkeypatch.setattr(runner, "APPROVED_CHECKSUMS", {})
    table = "migration_ci_" + uuid.uuid4().hex
    yield url, tmp_path, table
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(f"DROP TABLE IF EXISTS public.{table}")


def sql_file(directory, name, sql):
    (directory / name).write_text(sql, encoding="utf-8")
    runner.APPROVED_CHECKSUMS.setdefault(name, hashlib.sha256(sql.encode("utf-8")).hexdigest())
    return name


def history(url, filename):
    with psycopg.connect(url) as conn:
        return conn.execute(
            "SELECT checksum_sha256, applied_at FROM public.schema_migrations WHERE filename = %s",
            (filename,),
        ).fetchall()


def test_real_postgres_atomic_history_idempotence_checksum(pg):
    url, folder, table = pg
    name = sql_file(folder, table + ".sql", f"CREATE TABLE public.{table} (id INTEGER PRIMARY KEY);")
    runner.migrate(url, [name])
    first = history(url, name)
    assert len(first) == 1 and len(first[0][0]) == 64
    runner.migrate(url, [name])
    assert history(url, name) == first
    with psycopg.connect(url) as conn:
        assert conn.execute("SELECT to_regclass(%s)", (f"public.{table}",)).fetchone()[0] == table
    modified = f"CREATE TABLE public.{table} (id TEXT PRIMARY KEY);"
    sql_file(folder, name, modified)
    # The catalog would be updated in a reviewed code change; the database
    # must still refuse changing the contents of an already applied version.
    runner.APPROVED_CHECKSUMS[name] = hashlib.sha256(modified.encode("utf-8")).hexdigest()
    with pytest.raises(RuntimeError, match="checksum changed"):
        runner.migrate(url, [name])
    assert history(url, name) == first


def test_real_postgres_failed_sql_rolls_back_schema_and_history(pg):
    url, folder, table = pg
    name = sql_file(folder, table + ".sql",
                    f"CREATE TABLE public.{table} (id INTEGER); SELECT 1/0;")
    with pytest.raises(psycopg.Error):
        runner.migrate(url, [name])
    assert history(url, name) == []
    with psycopg.connect(url) as conn:
        assert conn.execute("SELECT to_regclass(%s)", (f"public.{table}",)).fetchone()[0] is None


def test_real_postgres_two_concurrent_runners_apply_once(pg):
    url, folder, table = pg
    name = sql_file(folder, table + ".sql", f"""
        CREATE TABLE public.{table} (id INTEGER);
        SELECT pg_sleep(0.25);
        INSERT INTO public.{table} VALUES (1);
    """)
    errors = []
    barrier = threading.Barrier(2)
    def execute():
        try:
            barrier.wait(timeout=5)
            runner.migrate(url, [name])
        except Exception as exc:
            errors.append(exc)
    a, b = threading.Thread(target=execute), threading.Thread(target=execute)
    a.start()
    b.start()
    a.join(timeout=15)
    b.join(timeout=15)
    assert not a.is_alive() and not b.is_alive(), "concurrent runner deadlocked"
    assert not errors, errors
    assert len(history(url, name)) == 1
    with psycopg.connect(url) as conn:
        assert conn.execute(f"SELECT COUNT(*) FROM public.{table}").fetchone()[0] == 1

def test_workspace_site_fk_dedup_preserves_canonical_and_rejects_mismatch(pg):
    url, _, _ = pg
    schema = "fk_ci_" + uuid.uuid4().hex
    source = (SCRIPT.parents[1] / "migrations" / "20261015_privacy_workspace_site_fk_dedup.sql").read_text()
    sql = source.replace("privacy.diagnostic", f"{schema}.diagnostic")
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA {schema}")
            cur.execute(f"CREATE TABLE {schema}.sites (id uuid PRIMARY KEY)")
            cur.execute(f"CREATE TABLE {schema}.diagnostic (workspace_site_id uuid)")
            cur.execute(f"""ALTER TABLE {schema}.diagnostic
                ADD CONSTRAINT privacy_diagnostic_workspace_site_fk
                FOREIGN KEY (workspace_site_id) REFERENCES {schema}.sites(id) ON DELETE SET NULL""")
            cur.execute(f"""ALTER TABLE {schema}.diagnostic
                ADD CONSTRAINT diagnostic_workspace_site_id_fkey
                FOREIGN KEY (workspace_site_id) REFERENCES {schema}.sites(id) ON DELETE SET NULL""")
            cur.execute(sql)
            cur.execute(sql)  # idempotent without a second drop
            names = [r[0] for r in cur.execute(
                "SELECT conname FROM pg_constraint WHERE conrelid=%s::regclass AND contype='f'",
                (f"{schema}.diagnostic",),
            )]
            assert names == ["privacy_diagnostic_workspace_site_fk"]
        conn.rollback()  # disposable test objects never persisted

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA {schema}")
            cur.execute(f"CREATE TABLE {schema}.sites (id uuid PRIMARY KEY)")
            cur.execute(f"CREATE TABLE {schema}.diagnostic (workspace_site_id uuid)")
            cur.execute(f"""ALTER TABLE {schema}.diagnostic
                ADD CONSTRAINT privacy_diagnostic_workspace_site_fk
                FOREIGN KEY (workspace_site_id) REFERENCES {schema}.sites(id) ON DELETE SET NULL""")
            cur.execute(f"""ALTER TABLE {schema}.diagnostic
                ADD CONSTRAINT diagnostic_workspace_site_id_fkey
                FOREIGN KEY (workspace_site_id) REFERENCES {schema}.sites(id) ON DELETE CASCADE""")
            with pytest.raises(psycopg.errors.RaiseException, match="definitions differ"):
                cur.execute(sql)
        conn.rollback()


@pytest.mark.parametrize("canonical_present", [False, True], ids=["canonical_missing", "redundant_missing"])
def test_workspace_site_fk_dedup_missing_constraint_cases(pg, canonical_present):
    url, _, _ = pg
    schema = "fk_ci_" + uuid.uuid4().hex
    source = (SCRIPT.parents[1] / "migrations" / "20261015_privacy_workspace_site_fk_dedup.sql").read_text()
    sql = source.replace("privacy.diagnostic", f"{schema}.diagnostic")
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA {schema}")
            cur.execute(f"CREATE TABLE {schema}.sites (id uuid PRIMARY KEY)")
            cur.execute(f"CREATE TABLE {schema}.diagnostic (workspace_site_id uuid)")
            constraint = "privacy_diagnostic_workspace_site_fk" if canonical_present else "diagnostic_workspace_site_id_fkey"
            cur.execute(f"""ALTER TABLE {schema}.diagnostic
                ADD CONSTRAINT {constraint}
                FOREIGN KEY (workspace_site_id) REFERENCES {schema}.sites(id) ON DELETE SET NULL""")
            if canonical_present:
                cur.execute(sql)
                cur.execute(sql)
                actual = [row[0] for row in cur.execute(
                    "SELECT conname FROM pg_constraint WHERE conrelid=%s::regclass AND contype='f'",
                    (f"{schema}.diagnostic",),
                )]
                assert actual == ["privacy_diagnostic_workspace_site_fk"]
            else:
                with pytest.raises(psycopg.errors.RaiseException, match="Canonical workspace-site FK missing"):
                    cur.execute(sql)
                conn.rollback()
                with psycopg.connect(url) as check:
                    assert check.execute("SELECT to_regclass(%s)", (f"{schema}.diagnostic",)).fetchone()[0] is None
                return
        conn.rollback()
