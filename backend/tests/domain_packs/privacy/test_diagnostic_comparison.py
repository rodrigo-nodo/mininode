"""PW-03C1: keep the established comparison contract independent of legacy orders."""

import inspect

import pytest

from mininode_api.domain_packs.privacy.diagnostic_comparison import compare_diagnostics
from mininode_api.services import privacy_entitled_plan


def versioned(score, controls=None, *, framework="0.11", scoring="0.3"):
    return {
        "framework_version": framework,
        "scoring_version": scoring,
        "score": score,
        "controls": controls if controls is not None else [],
    }


def test_equal_versions_preserve_exact_review_contract():
    plan = {"items": [
        {"control_code": "PRV-001", "name": "Política visible"},
        {"control_code": "PRV-003", "name": "Política propia"},
        {"control_code": "PRV-007", "name": "Datos tratados"},
    ]}
    original = versioned(26)
    current = versioned(73, [
        {"control_code": "PRV-001", "result": "detected"},
        {"control_code": "PRV-003", "result": "partial"},
        {"control_code": "PRV-007", "result": "not_evaluable"},
        {"control_code": "PRV-999", "result": "not_detected"},
    ])
    assert compare_diagnostics(plan, original, current) == {
        "version": "2",
        "comparability": {
            "status": "comparable",
            "reason": None,
            "original": {"framework_version": "0.11", "scoring_version": "0.3"},
            "current": {"framework_version": "0.11", "scoring_version": "0.3"},
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


@pytest.mark.parametrize("result", [None, "not_evaluable", "not_applicable"])
def test_absent_or_indeterminate_evidence_never_confirms_correction(result):
    plan = {"items": [{"control_code": "PRV-003"}]}
    controls = [] if result is None else [{"control_code": "PRV-003", "result": result}]
    comparison = compare_diagnostics(plan, versioned(47), versioned(47, controls))
    assert comparison["corrected_count"] == 0
    assert comparison["pending_count"] == 0
    assert comparison["not_evaluable_count"] == 1
    assert comparison["items"] == [
        {"control_id": "PRV-003", "name": "PRV-003", "status": "not_evaluable"},
    ]


@pytest.mark.parametrize("result", ["partial", "not_detected"])
def test_unresolved_controls_remain_pending(result):
    plan = {"items": [{"control_code": "PRV-003", "name": "Transparencia"}]}
    current = versioned(47, [{"control_code": "PRV-003", "result": result}])
    comparison = compare_diagnostics(plan, versioned(47), current)
    assert comparison["pending_count"] == 1
    assert comparison["corrected_count"] == 0
    assert comparison["items"][0]["status"] == "still_pending"


@pytest.mark.parametrize("changed,reason", [
    ({"framework_version": "0.12"}, "framework_version_mismatch"),
    ({"scoring_version": "0.4"}, "scoring_version_mismatch"),
    ({"framework_version": None}, "missing_version"),
])
def test_incompatible_versions_never_claim_score_or_item_changes(changed, reason):
    plan = {"items": [{"control_code": "PRV-001"}]}
    current = {**versioned(74, [{"control_code": "PRV-001", "result": "detected"}]), **changed}
    comparison = compare_diagnostics(plan, versioned(62), current)
    assert comparison["version"] == "2"
    assert comparison["comparability"]["status"] == "not_comparable"
    assert comparison["comparability"]["reason"] == reason
    assert comparison["original_score"] == 62
    assert comparison["current_score"] == 74
    for key in ("score_change", "total_plan_items", "corrected_count",
                "pending_count", "not_evaluable_count"):
        assert comparison[key] is None
    assert comparison["items"] == []


def test_entitled_plan_uses_neutral_comparator_without_importing_legacy_service():
    assert privacy_entitled_plan.compare_diagnostics is compare_diagnostics
    assert "privacy_correction_plan_check" not in inspect.getsource(privacy_entitled_plan)
