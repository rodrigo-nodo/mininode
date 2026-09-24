import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

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


@pytest.mark.parametrize(
    "paid_at,expected",
    [
        (
            datetime(2026, 8, 25, 12, 30, tzinfo=timezone.utc),
            datetime(2026, 9, 25, 12, 30, tzinfo=timezone.utc),
        ),
        (
            datetime(2026, 1, 31, 8, 0, tzinfo=timezone.utc),
            datetime(2026, 2, 28, 8, 0, tzinfo=timezone.utc),
        ),
        (
            datetime(2028, 1, 31, 8, 0, tzinfo=timezone.utc),
            datetime(2028, 2, 29, 8, 0, tzinfo=timezone.utc),
        ),
        (
            datetime(2026, 12, 31, 23, 15, tzinfo=timezone.utc),
            datetime(2027, 1, 31, 23, 15, tzinfo=timezone.utc),
        ),
    ],
)
def test_expiration_is_one_calendar_month_from_activation(paid_at, expected):
    assert service.expires_at(paid_at) == expected


@pytest.mark.parametrize(
    "now_delta,expected",
    [
        (timedelta(0), "available"),
        (timedelta(microseconds=1), "expired"),
    ],
)
def test_active_month_metadata_boundary_and_latest_review(monkeypatch, now_delta, expected):
    paid_at = datetime(2026, 8, 25, tzinfo=timezone.utc)
    deadline = service.expires_at(paid_at)
    context = service.CheckContext(
        "order", "diagnostic", "https://stored.example", paid_at, PLAN
    )
    latest_at = paid_at + timedelta(days=5)
    latest_result = {"version": "2", "current_score": 70}

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
    monkeypatch.setattr(service, "_latest", lambda cursor, plan_id: (latest_at, latest_result))

    metadata = service.get_check_metadata("plan", now=deadline + now_delta)

    assert metadata["status"] == expected
    assert metadata["expires_at"] == deadline
    assert metadata["latest_check"] == {
        "created_at": latest_at,
        "result": latest_result,
    }


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
            "status": "comparable",
            "reason": None,
            "original": {"framework_version": "0.1", "scoring_version": "0.1"},
            "current": {"framework_version": "0.1", "scoring_version": "0.1"},
        },
        "original_score": 26,
        "current_score": 73,
        "score_change": 47,
        "total_plan_items": 3,
        "corrected_count": 1,
        "pending_count": 1,
        "not_evaluable_count": 1,
        "items": [
            {"control_id": "PRV-001", "name": "Política visible", "status": "corrected"},
            {"control_id": "PRV-003", "name": "Política propia", "status": "still_pending"},
            {"control_id": "PRV-007", "name": "Datos tratados", "status": "not_evaluable"},
        ],
    }
    assert all(item["control_id"] != "PRV-999" for item in result["items"])


def test_schema_removes_single_use_constraint_and_indexes_review_history():
    sql = service.INITIALIZE_SQL
    create_table = sql.split("DO $$", 1)[0]
    assert "UNIQUE (correction_plan_id)" not in create_table
    assert "pg_get_constraintdef(oid) = 'UNIQUE (correction_plan_id)'" in sql
    assert "DROP CONSTRAINT %I" in sql
    assert "correction_plan_check_plan_created_idx" in sql
    assert "original_diagnostic_id UUID NOT NULL REFERENCES privacy.diagnostic(id)" in sql
    assert "check_diagnostic_id UUID NOT NULL REFERENCES privacy.diagnostic(id)" in sql
    assert "result_snapshot JSONB NOT NULL" in sql


def test_context_uses_joined_diagnostic_site_not_caller_input():
    class Cursor:
        statement = ""

        def execute(self, statement, params):
            self.statement = statement

        def fetchone(self):
            return (
                "order",
                "diagnostic",
                "https://stored.example",
                datetime.now(timezone.utc),
                PLAN,
                "paid",
            )

    cursor = Cursor()
    context = service._context(cursor, "plan")
    assert context.site_url == "https://stored.example"
    assert "JOIN privacy.diagnostic" in cursor.statement
    assert "d.site_url" in cursor.statement
    assert "o.amount" not in cursor.statement


def test_perform_check_can_be_repeated_while_privacy_web_is_active(monkeypatch):
    paid_at = datetime(2026, 9, 1, tzinfo=timezone.utc)
    context = service.CheckContext(
        "order", "diagnostic", "https://stored.example", paid_at, PLAN
    )
    original = versioned({
        "score": 40,
        "controls": [
            {"control_code": "PRV-001", "result": "not_detected"},
            {"control_code": "PRV-003", "result": "partial"},
            {"control_code": "PRV-007", "result": "not_detected"},
        ],
    })
    current = versioned({
        "site_url": "https://stored.example",
        "score": 70,
        "controls": [
            {"control_code": "PRV-001", "result": "detected"},
            {"control_code": "PRV-003", "result": "partial"},
            {"control_code": "PRV-007", "result": "not_detected"},
        ],
    })
    created_at = paid_at + timedelta(days=1)
    executions = []

    class Cursor:
        def execute(self, statement, params=None):
            executions.append((" ".join(statement.split()), params))

        def fetchone(self):
            return (created_at,)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    @contextmanager
    def connection():
        yield type("Connection", (), {"cursor": lambda self: Cursor()})()

    monkeypatch.setattr(service, "_connection", connection)
    monkeypatch.setattr(
        service.privacy_correction_plan,
        "get_correction_plan",
        lambda token: {"id": "plan"},
    )
    monkeypatch.setattr(service, "_context", lambda cursor, plan_id: context)
    monkeypatch.setattr(
        service.privacy_diagnostic_snapshot,
        "get_diagnostic_snapshot",
        lambda diagnostic_id: SimpleNamespace(diagnostic_snapshot=original),
    )
    monkeypatch.setattr(service, "diagnose_privacy_url", lambda url: current)
    monkeypatch.setattr(
        service.privacy_diagnostic_snapshot,
        "create_diagnostic_snapshot",
        lambda diagnostic: SimpleNamespace(id=uuid4(), diagnostic_snapshot=current),
    )

    first = service.perform_check("token", now=paid_at + timedelta(days=1))
    second = service.perform_check("token", now=paid_at + timedelta(days=2))

    assert first["status"] == "available"
    assert second["status"] == "available"
    assert first["expires_at"] == service.expires_at(paid_at)
    inserts = [
        statement
        for statement, _ in executions
        if "INSERT INTO privacy.correction_plan_check" in statement
    ]
    assert len(inserts) == 2


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
