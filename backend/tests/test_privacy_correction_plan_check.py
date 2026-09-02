import sys
from contextlib import contextmanager
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


def versioned(snapshot):
    return {"framework_version": "0.1", "scoring_version": "0.1", **snapshot}


def test_current_and_legacy_expiration_use_paid_at_and_persisted_amount():
    paid_at = datetime(2026, 8, 25, tzinfo=timezone.utc)
    assert service.expires_at(paid_at, 9900) == paid_at + timedelta(days=30)
    assert service.expires_at(paid_at, 49900) == paid_at + timedelta(days=90)


@pytest.mark.parametrize("offset,expected", [
    (timedelta(days=30), "available"),
    (timedelta(days=30, microseconds=1), "expired"),
])
def test_current_offer_metadata_boundary(monkeypatch, offset, expected):
    paid_at = datetime(2026, 8, 25, tzinfo=timezone.utc)
    context = service.CheckContext(
        "order", "diagnostic", "https://stored.example", paid_at, 9900, PLAN
    )

    class Connection:
        def cursor(self):
            return self
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    @contextmanager
    def connection():
        yield Connection()

    monkeypatch.setattr(service, "_connection", connection)
    monkeypatch.setattr(service, "_context", lambda cursor, plan_id: context)
    monkeypatch.setattr(service, "_existing", lambda cursor, plan_id: None)

    metadata = service.get_check_metadata("plan", now=paid_at + offset)

    assert metadata["status"] == expected
    assert metadata["expires_at"] == paid_at + timedelta(days=30)


def test_deterministic_comparison_uses_plan_codes_and_snapshot_scores():
    original = versioned({
        "score": 26,
        "controls": [
            {"control_code": "PRV-001", "result": "not_detected"},
            {"control_code": "PRV-003", "result": "partial"},
            {"control_code": "PRV-007", "result": "not_detected"},
            {"control_code": "PRV-999", "result": "detected"},
        ],
    })
    current = versioned({
        "score": 73,
        "controls": [
            {"control_code": "PRV-001", "result": "detected"},
            {"control_code": "PRV-003", "result": "partial"},
            {"control_code": "PRV-007", "result": "not_evaluable"},
            {"control_code": "PRV-999", "result": "not_detected"},
        ],
    })
    result = service.compare_diagnostics(PLAN, original, current)
    assert result == {
        "version": "2",
        "comparability": {
            "status": "comparable", "reason": None,
            "original": {"framework_version": "0.1", "scoring_version": "0.1"},
            "current": {"framework_version": "0.1", "scoring_version": "0.1"},
        },
        "original_score": 26, "current_score": 73,
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
            return ("order", "diagnostic", "https://stored.example", datetime.now(timezone.utc), 9900, PLAN, "paid")
    cursor = Cursor()
    context = service._context(cursor, "plan")
    assert context.site_url == "https://stored.example"
    assert "JOIN privacy.diagnostic" in cursor.statement
    assert "d.site_url" in cursor.statement
    assert "o.amount" in cursor.statement


def test_new_transparency_controls_use_generic_corrected_comparison():
    plan = {"items": [
        {"control_code": "PRV-013", "name": "Reclamo ante la Agencia"},
        {"control_code": "PRV-014", "name": "Retiro del consentimiento"},
    ]}
    original = versioned({"score": 40, "controls": [
        {"control_code": "PRV-013", "result": "not_detected"},
        {"control_code": "PRV-014", "result": "partial"},
    ]})
    current = versioned({"score": 70, "controls": [
        {"control_code": "PRV-013", "result": "detected"},
        {"control_code": "PRV-014", "result": "detected"},
    ]})
    result = service.compare_diagnostics(plan, original, current)
    assert result["corrected_count"] == 2
    assert [item["status"] for item in result["items"]] == ["corrected", "corrected"]


def test_incomparable_diagnostics_do_not_claim_score_or_item_changes():
    original = versioned({"score": 62, "controls": []})
    current = versioned({"score": 74, "controls": []})
    current["framework_version"] = "0.2"

    result = service.compare_diagnostics(PLAN, original, current)

    assert result["version"] == "2"
    assert result["comparability"]["status"] == "not_comparable"
    assert result["comparability"]["reason"] == "framework_version_mismatch"
    assert result["original_score"] == 62
    assert result["current_score"] == 74
    assert result["score_change"] is None
    assert result["corrected_count"] is None
    assert result["pending_count"] is None
    assert result["not_evaluable_count"] is None
    assert result["items"] == []
