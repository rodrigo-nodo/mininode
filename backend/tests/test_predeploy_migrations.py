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

def test_unknown_sql_is_rejected_even_if_file_exists(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "MIGRATIONS_DIR", tmp_path)
    (tmp_path / "unknown.sql").write_text("SELECT 1;", encoding="utf-8")
    with pytest.raises(ValueError, match="not in reviewed catalog"):
        runner.load_sql("unknown.sql")

def test_known_migration_checksum_matches_catalog():
    _, checksum = runner.load_sql("20261013_privacy_anonymous_claim.sql")
    assert checksum == runner.APPROVED_CHECKSUMS["20261013_privacy_anonymous_claim.sql"]

def test_modified_reviewed_file_rejected_before_connect(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "MIGRATIONS_DIR", tmp_path)
    name = "20261013_privacy_anonymous_claim.sql"
    (tmp_path / name).write_text("SELECT 2;", encoding="utf-8")
    def unexpected(*args, **kwargs):
        raise AssertionError("must not open database")
    monkeypatch.setattr(runner.psycopg, "connect", unexpected)
    with pytest.raises(ValueError, match="catalog checksum mismatch"):
        runner.migrate("postgresql://placeholder", [name])

@pytest.mark.parametrize("tokens", [
    ("DROP", "/* comentario */", "TABLE", "access.sites;"),
    ("DROP", "INDEX", "access.some_index;"),
    ("ALTER", "TABLE", "access.sites", "DROP", "CONSTRAINT", "some_constraint;"),
])
def test_unreviewed_sql_variants_fail_closed(monkeypatch, tmp_path, tokens):
    monkeypatch.setattr(runner, "MIGRATIONS_DIR", tmp_path)
    name = "unreviewed.sql"
    (tmp_path / name).write_text(" ".join(tokens), encoding="utf-8")
    with pytest.raises(ValueError, match="not in reviewed catalog"):
        runner.load_sql(name)


# Promotion is schema-only: execution is separately approved per environment.
PROMOTION_BATCH_A = (
    "20261019_access_site_aliases.sql",
    "20261019_access_workspace_site_unlink.sql",
    "20261020_access_site_group_review_requests.sql",
    "20261020_access_site_reconciliations.sql",
    "20261020_privacy_requested_url.sql",
    "20261022_access_entitlement_admin_events.sql",
)
PROMOTION_BATCH_B = ("20261020_access_site_group_operator.sql",)


def test_prod_promotion_batches_catalogued_and_sorted():
    assert list(PROMOTION_BATCH_A) == sorted(PROMOTION_BATCH_A)
    assert list(PROMOTION_BATCH_B) == sorted(PROMOTION_BATCH_B)
    for name in PROMOTION_BATCH_A + PROMOTION_BATCH_B:
        sql, digest = runner.load_sql(name)
        assert digest == runner.APPROVED_CHECKSUMS[name]
        assert "DROP TABLE" not in sql.upper()
        assert "DELETE FROM " not in sql.upper()
    assert "CREATE TABLE IF NOT EXISTS access.site_group_review_requests" in runner.load_sql("20261020_access_site_group_review_requests.sql")[0]
    assert "ALTER TABLE access.site_group_review_requests" in runner.load_sql("20261020_access_site_group_operator.sql")[0]


def test_prod_promotion_requires_environment_approval(monkeypatch):
    monkeypatch.delenv("MIGRATION_APPROVED_FILES", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert runner.main() == 0
