from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "production-db-migration.yml"


def test_production_migration_workflow_is_manual_and_guarded():
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    trigger = data.get("on", data.get(True))
    assert "workflow_dispatch" in trigger
    assert "schedule" not in trigger
    assert "push" not in trigger

    job = data["jobs"]["migrate"]
    assert job["environment"] == "production"

    text = WORKFLOW.read_text(encoding="utf-8")
    assert "RUN_PRODUCTION_MIGRATION" in text
    assert "secrets.PRODUCTION_DATABASE_URL" in text
    assert "scripts/run_migration.py" in text
    assert "ref: main" in text


def test_legacy_workflow_blocks_seven_promotion_migrations():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "Reject DEV to PROD promotion migrations" in text
    for name in (
        "20261019_access_site_aliases.sql",
        "20261019_access_workspace_site_unlink.sql",
        "20261020_access_site_group_operator.sql",
        "20261020_access_site_group_review_requests.sql",
        "20261020_access_site_reconciliations.sql",
        "20261020_privacy_requested_url.sql",
        "20261022_access_entitlement_admin_events.sql",
    ):
        assert name in text
    assert "exit 1" in text
