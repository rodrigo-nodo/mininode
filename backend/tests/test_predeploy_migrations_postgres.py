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
