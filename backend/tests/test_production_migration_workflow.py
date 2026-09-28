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
