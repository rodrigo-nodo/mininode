import importlib.util
from pathlib import Path
import pytest

PATH = Path(__file__).resolve().parents[1] / "scripts" / "predeploy_migrations.py"
spec = importlib.util.spec_from_file_location("predeploy_migrations", PATH)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

def test_default_safe_no_op(monkeypatch):
    monkeypatch.delenv("MIGRATION_APPROVED_FILES", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert runner.main() == 0

@pytest.mark.parametrize("value", [
    "../bad.sql", "nested/x.sql", "x.txt", "a.sql,a.sql", "b.sql,a.sql",
    "x.sql,", "x.sql;DROP TABLE users"
])
def test_invalid_approvals_fail_closed(value):
    with pytest.raises(ValueError):
        runner.parse_approved(value)

def test_existing_transaction_wrapper_is_removed():
    sql, digest = runner.load_sql("20261013_privacy_anonymous_claim.sql")
    assert "BEGIN;" not in [x.strip() for x in sql.splitlines()]
    assert "COMMIT;" not in [x.strip() for x in sql.splitlines()]
    assert len(digest) == 64

def test_unknown_migration_rejected():
    with pytest.raises(ValueError):
        runner.load_sql("nonexistent.sql")

def test_no_connection_if_file_is_missing(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("database must not be accessed")
    monkeypatch.setattr(runner.psycopg, "connect", unexpected)
    with pytest.raises(ValueError):
        runner.migrate("postgresql://placeholder", ["nonexistent.sql"])

@pytest.mark.parametrize("filename", sorted(runner.BLOCKED_LEGACY))
def test_historical_migrations_hard_blocked(filename):
    with pytest.raises(ValueError, match="Legacy migration blocked"):
        runner.load_sql(filename)

def test_destructive_sql_blocked(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "MIGRATIONS_DIR", tmp_path)
    for statement in ("DROP TABLE example;", "TRUNCATE example;", "ALTER TABLE example DROP COLUMN id;"):
        (tmp_path / "test.sql").write_text(statement, encoding="utf-8")
        with pytest.raises(ValueError, match="Destructive SQL blocked"):
            runner.load_sql("test.sql")
