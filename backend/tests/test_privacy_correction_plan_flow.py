import sys
from pathlib import Path
from uuid import uuid4

import pytest

BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.services import privacy_correction_plan as persistence  # noqa: E402
from mininode_api.services import privacy_correction_plan_flow as flow  # noqa: E402
from mininode_api.services.privacy_diagnostic import PrivacyInspectionError  # noqa: E402


def finding(code, result, confidence="high"):
    return {"control_code": code, "result": result, "confidence": confidence}


def test_real_builder_receives_diagnostic_snapshot_and_persists_complete_plan(monkeypatch):
    diagnostic = {
        "site_url": "https://www.example.com/final",
        "score": 37,
        "controls": [
            finding("PRV-301", "not_detected"),
            finding("PRV-012", "partial"),
            finding("PRV-010", "partial"),
            finding("PRV-007", "not_detected", "low"),
            finding("PRV-005", "not_detected"),
            finding("PRV-501", "partial"),
            finding("PRV-003", "not_detected", "medium"),
            finding("PRV-001", "not_detected", "medium"),
        ],
        # The free priorities are deliberately shorter than the complete plan.
        "priorities": [{"control_code": "PRV-001"}],
        "scope": {"pages_requested": 2, "pages_analyzed": 2, "limited": False},
    }
    persisted = []
    created = persistence.CreatedCorrectionPlan(uuid4(), "generated-token")
    monkeypatch.setattr(flow, "diagnose_privacy_url", lambda url: diagnostic)
    monkeypatch.setattr(
        persistence,
        "create_correction_plan",
        lambda **kwargs: persisted.append(kwargs) or created,
    )

    actual, plan = flow.create_correction_plan_from_url("https://example.com")

    assert actual is created
    assert plan["initial_score"] == 37
    assert plan["item_count"] == 8
    assert persisted == [{"site_url": diagnostic["site_url"], "plan": plan}]
    assert plan["items"][0]["action_steps"]
    assert len(plan["items"]) > len(diagnostic["priorities"])


def test_no_actionable_items_does_not_persist_or_generate_token(monkeypatch):
    diagnostic = {
        "site_url": "https://example.com",
        "score": 100,
        "controls": [finding("PRV-001", "detected")],
    }
    monkeypatch.setattr(flow, "diagnose_privacy_url", lambda url: diagnostic)
    monkeypatch.setattr(
        persistence,
        "create_correction_plan",
        lambda **kwargs: pytest.fail("an empty plan must not be persisted"),
    )

    with pytest.raises(flow.NoActionableItemsError):
        flow.create_correction_plan_from_url("https://example.com")


def test_diagnostic_failure_preserves_domain_error_and_never_persists(monkeypatch):
    error = PrivacyInspectionError("unsafe_target")

    def fail(_url):
        raise error

    monkeypatch.setattr(flow, "diagnose_privacy_url", fail)
    monkeypatch.setattr(
        persistence,
        "create_correction_plan",
        lambda **kwargs: pytest.fail("a failed diagnosis must not create a row"),
    )

    with pytest.raises(PrivacyInspectionError) as raised:
        flow.create_correction_plan_from_url("http://127.0.0.1")
    assert raised.value is error
