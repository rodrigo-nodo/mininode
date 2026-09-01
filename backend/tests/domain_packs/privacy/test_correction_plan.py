import inspect
import sys
from pathlib import Path


BACKEND_SRC = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.domain_packs.privacy.correction_plan import (  # noqa: E402
    build_correction_plan,
)
from mininode_api.domain_packs.privacy.prioritization import (  # noqa: E402
    load_actions,
    prioritize_findings,
)


def finding(code, result, confidence="high"):
    return {"control_code": code, "result": result, "confidence": confidence}


def test_plan_eligibility_includes_only_actionable_evaluations_with_actions(monkeypatch):
    results = [
        finding("PRV-001", "not_detected"),
        finding("PRV-003", "partial"),
        finding("PRV-301", "detected"),
        finding("PRV-201", "not_applicable"),
        finding("PRV-501", "not_evaluable"),
        finding("PRV-004", "not_detected"),
        finding("PRV-009", "partial"),
    ]
    catalog = load_actions()
    actions = dict(catalog["actions"])
    actions.pop("PRV-003")
    monkeypatch.setattr(
        "mininode_api.domain_packs.privacy.correction_plan.load_actions",
        lambda: {"version": catalog["version"], "actions": actions},
    )

    plan = build_correction_plan(results, initial_score=26)

    assert [item["control_code"] for item in plan["items"]] == ["PRV-001"]
    assert plan["item_count"] == 1


def test_plan_is_complete_ordered_and_reproducible():
    results = [
        finding("PRV-301", "not_detected", "high"),
        finding("PRV-012", "partial", "high"),
        finding("PRV-010", "partial", "high"),
        finding("PRV-007", "not_detected", "low"),
        finding("PRV-005", "not_detected", "high"),
        finding("PRV-501", "partial", "high"),
        finding("PRV-003", "not_detected", "medium"),
        finding("PRV-001", "not_detected", "medium"),
    ]

    first = build_correction_plan(results, initial_score=37)
    second = build_correction_plan(results, initial_score=37)

    assert first == second
    assert first["item_count"] == 8
    assert [item["control_code"] for item in first["items"]] == [
        "PRV-001", "PRV-003", "PRV-501", "PRV-005",
        "PRV-007", "PRV-010", "PRV-012", "PRV-301",
    ]
    assert len(prioritize_findings(results, limit=99)) == 3


def test_plan_contract_uses_catalog_actions_and_preserves_supplied_score():
    plan = build_correction_plan(
        [finding("PRV-501", "not_detected")], initial_score=137
    )
    item = plan["items"][0]
    catalog = load_actions()
    action = catalog["actions"]["PRV-501"]["not_detected"]

    assert plan == {
        "version": "1",
        "actions_version": catalog["version"],
        "initial_score": 137,
        "item_count": 1,
        "items": [item],
    }
    assert item["action_steps"] == action["action_steps"]
    assert item["validation_step"] == action["validation_step"]


def test_plan_engine_has_no_external_or_ai_integration():
    source = inspect.getsource(
        sys.modules["mininode_api.domain_packs.privacy.correction_plan"]
    ).lower()
    assert all(term not in source for term in ("httpx", "requests", "openai", "llm"))


def test_new_actionable_controls_flow_through_generic_plan_engine():
    plan = build_correction_plan([
        finding("PRV-013", "not_detected"),
        finding("PRV-014", "partial"),
        finding("PRV-014", "not_applicable"),
    ], initial_score=50)
    assert [item["control_code"] for item in plan["items"]] == ["PRV-013", "PRV-014"]
    assert all(item["action_steps"] and item["validation_step"] for item in plan["items"])


def test_prv102_insecure_transport_generates_complete_actionable_item():
    plan = build_correction_plan(
        [finding("PRV-102", "not_detected")], initial_score=75
    )

    assert plan["version"] == "1"
    assert plan["actions_version"] == "2"
    assert plan["item_count"] == 1
    assert {
        "control_code", "finding", "recommendation", "action_steps",
        "validation_step",
    } <= set(plan["items"][0])
