"""New operator schema is additive, reviewed and separately allowlisted."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "predeploy_migrations.py"
spec = importlib.util.spec_from_file_location("operator_predeploy", SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_operator_review_migration_checksum_and_nondestructive_contract():
    name = "20261020_access_site_group_operator.sql"
    sql, checksum = runner.load_sql(name)
    assert checksum == runner.APPROVED_CHECKSUMS[name]
    assert "ADD COLUMN IF NOT EXISTS reviewed_by_user_id" in sql
    assert "CREATE TABLE IF NOT EXISTS access.site_group_operator_merges" in sql
    assert "source_site_snapshot JSONB NOT NULL" in sql
    assert "DROP TABLE" not in sql.upper()
    assert "DELETE FROM" not in sql.upper()
