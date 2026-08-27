import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.services import privacy_correction_plan_check as service  # noqa: E402


PLAN = {
    "items": [
        {"control_code": "PRV-001", "name": "Política visible"},
        {"control_code": "PRV-003", "name": "Política propia"},
        {"control_code": "PRV-007", "name": "Datos tratados"},
    ]
}


def test_expiration_uses_only_paid_at():
    paid_at = datetime(2026, 8, 25, tzinfo=timezone.utc)
    assert service.expires_at(paid_at) == paid_at + timedelta(days=90)


def test_deterministic_comparison_uses_plan_codes_and_snapshot_scores():
    original = {
        "score": 26,
        "controls": [
            {"control_code": "PRV-001", "result": "not_detected"},
            {"control_code": "PRV-003", "result": "partial"},
            {"control_code": "PRV-007", "result": "not_detected"},
            {"control_code": "PRV-999", "result": "detected"},
        ],
    }
    current = {
        "score": 73,
        "controls": [
            {"control_code": "PRV-001", "result": "detected"},
            {"control_code": "PRV-003", "result": "partial"},
            {"control_code": "PRV-007", "result": "not_evaluable"},
            {"control_code": "PRV-999", "result": "not_detected"},
        ],
    }
    result = service.compare_diagnostics(PLAN, original, current)
    assert result == {
        "version": "1", "original_score": 26, "current_score": 73,
        "score_change": 47, "total_plan_items": 3, "corrected_count": 1,
        "pending_count": 1, "not_evaluable_count": 1,
        "items": [
            {"control_id": "PRV-001", "name": "Política visible", "status": "corrected"},
            {"control_id": "PRV-003", "name": "Política propia", "status": "still_pending"},
            {"control_id": "PRV-007", "name": "Datos tratados", "status": "not_evaluable"},
        ],
    }
    assert all(item["control_id"] != "PRV-999" for item in result["items"])


def test_schema_has_single_check_constraint_and_required_relations():
    sql = service.INITIALIZE_SQL
    assert "UNIQUE (correction_plan_id)" in sql
    assert "original_diagnostic_id UUID NOT NULL REFERENCES privacy.diagnostic(id)" in sql
    assert "check_diagnostic_id UUID NOT NULL REFERENCES privacy.diagnostic(id)" in sql
    assert "result_snapshot JSONB NOT NULL" in sql


def test_context_uses_joined_diagnostic_site_not_caller_input():
    class Cursor:
        statement = ""
        def execute(self, statement, params): self.statement = statement
        def fetchone(self):
            return ("order", "diagnostic", "https://stored.example", datetime.now(timezone.utc), PLAN, "paid")
    cursor = Cursor()
    context = service._context(cursor, "plan")
    assert context.site_url == "https://stored.example"
    assert "JOIN privacy.diagnostic" in cursor.statement
    assert "d.site_url" in cursor.statement


def test_new_transparency_controls_use_generic_corrected_comparison():
    plan = {"items": [
        {"control_code": "PRV-013", "name": "Reclamo ante la Agencia"},
        {"control_code": "PRV-014", "name": "Retiro del consentimiento"},
    ]}
    original = {"score": 40, "controls": [
        {"control_code": "PRV-013", "result": "not_detected"},
        {"control_code": "PRV-014", "result": "partial"},
    ]}
    current = {"score": 70, "controls": [
        {"control_code": "PRV-013", "result": "detected"},
        {"control_code": "PRV-014", "result": "detected"},
    ]}
    result = service.compare_diagnostics(plan, original, current)
    assert result["corrected_count"] == 2
    assert [item["status"] for item in result["items"]] == ["corrected", "corrected"]
