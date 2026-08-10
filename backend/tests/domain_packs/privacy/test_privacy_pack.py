import json
import sys
from pathlib import Path

BACKEND_SRC = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.domain_packs.privacy.evaluator import evaluate_control
from mininode_api.domain_packs.privacy.prioritization import select_priorities
from mininode_api.domain_packs.privacy.scoring import (
    calculate_privacy_score,
    status_for_score,
)

PACK_DIR = (
    BACKEND_SRC / "mininode_api" / "domain_packs" / "privacy"
)


def load_json(name):
    with (PACK_DIR / name).open(encoding="utf-8") as file:
        return json.load(file)


def result(code, evaluation_result, confidence="high", reason="Hallazgo visible."):
    return {
        "control_code": code,
        "result": evaluation_result,
        "confidence": confidence,
        "evidence": [],
        "reason": reason,
    }


def test_catalog_and_scoring_configuration_are_valid():
    catalog = load_json("controls.json")
    config = load_json("scoring.json")

    assert catalog["version"] == "0.1"
    assert config["version"] == "0.1"
    assert len(catalog["controls"]) == 7
    assert len({control["code"] for control in catalog["controls"]}) == 7
    assert config["impact_weights"] == {
        "bajo": 1,
        "medio": 2,
        "alto": 3,
        "muy_alto": 4,
    }
    assert config["result_factors"] == {
        "detected": 1.0,
        "partial": 0.5,
        "not_detected": 0.0,
    }


def test_context_and_dependencies_are_declared():
    controls = {
        control["code"]: control for control in load_json("controls.json")["controls"]
    }

    assert controls["PRV-101"]["control_type"] == "context"
    assert controls["PRV-101"]["score_weight"] == 0
    assert controls["PRV-002"]["depends_on"] == "PRV-001"
    assert controls["PRV-104"]["depends_on"] == "PRV-101"


def test_all_seven_control_evaluators_use_structured_evidence():
    prv001 = evaluate_control("PRV-001", {"policy_visible": True})
    prv002 = evaluate_control(
        "PRV-002",
        {"policy_accessible": True, "content_relevant": True},
        {"PRV-001": prv001},
    )
    prv101 = evaluate_control("PRV-101", {"personal_data_form": True})
    prv104 = evaluate_control(
        "PRV-104",
        {"information_clear": True, "consent_required": False},
        {"PRV-101": prv101},
    )
    prv201 = evaluate_control(
        "PRV-201",
        {"relevant_cookies_detected": False},
    )
    prv301 = evaluate_control("PRV-301", {"contact_channels": ["email"]})
    prv501 = evaluate_control(
        "PRV-501",
        {"https": True, "certificate_valid": True},
    )

    assert [
        prv001["result"],
        prv002["result"],
        prv101["result"],
        prv104["result"],
        prv201["result"],
        prv301["result"],
        prv501["result"],
    ] == [
        "detected",
        "detected",
        "detected",
        "detected",
        "not_applicable",
        "detected",
        "detected",
    ]


def test_conditional_controls_respect_dependencies():
    policy = evaluate_control(
        "PRV-002", {}, {"PRV-001": {"result": "not_detected"}}
    )
    form = evaluate_control(
        "PRV-104", {}, {"PRV-101": {"result": "not_detected"}}
    )

    assert policy["result"] == "not_applicable"
    assert form["result"] == "not_applicable"


def test_result_factors_and_not_applicable_exclusion():
    detected = calculate_privacy_score([result("PRV-001", "detected")])
    partial = calculate_privacy_score([result("PRV-501", "partial")])
    missing = calculate_privacy_score([result("PRV-001", "not_detected")])
    not_applicable = calculate_privacy_score(
        [
            result("PRV-201", "not_applicable"),
            result("PRV-301", "detected"),
        ]
    )

    assert detected["score"] == 100
    assert partial["score"] == 50
    assert missing["score"] == 0
    assert not_applicable == {
        "score": 100,
        "status": "Alta preparación visible",
        "coverage": 100,
        "evaluated_controls": 1,
        "applicable_controls": 1,
    }


def test_not_evaluable_reduces_coverage_without_affecting_score():
    summary = calculate_privacy_score(
        [
            result("PRV-001", "not_evaluable"),
            result("PRV-301", "detected"),
        ]
    )

    assert summary["score"] == 100
    assert summary["coverage"] == 50
    assert summary["evaluated_controls"] == 1
    assert summary["applicable_controls"] == 2


def test_complete_scenario_scores_67_with_full_coverage():
    summary = calculate_privacy_score(
        [
            result("PRV-001", "detected"),
            result("PRV-002", "partial"),
            result("PRV-101", "detected"),
            result("PRV-104", "not_detected"),
            result("PRV-201", "not_applicable"),
            result("PRV-301", "detected"),
            result("PRV-501", "detected"),
        ]
    )

    assert summary == {
        "score": 67,
        "status": "En preparación",
        "coverage": 100,
        "evaluated_controls": 5,
        "applicable_controls": 5,
    }


def test_score_status_ranges_include_boundaries():
    assert status_for_score(0) == "Preparación inicial"
    assert status_for_score(39) == "Preparación inicial"
    assert status_for_score(40) == "En preparación"
    assert status_for_score(69) == "En preparación"
    assert status_for_score(70) == "Preparación avanzada"
    assert status_for_score(84) == "Preparación avanzada"
    assert status_for_score(85) == "Alta preparación visible"
    assert status_for_score(100) == "Alta preparación visible"


def test_prioritization_is_limited_and_excludes_context():
    priorities = select_priorities(
        [
            result("PRV-101", "not_detected"),
            result("PRV-001", "not_detected"),
            result("PRV-104", "partial"),
            result("PRV-201", "not_detected"),
            result("PRV-301", "not_detected"),
            result("PRV-501", "partial"),
        ]
    )

    assert len(priorities) == 3
    assert "PRV-101" not in {priority["control_code"] for priority in priorities}
    assert all(set(priority) == {
        "control_code", "name", "priority", "finding", "recommendation"
    } for priority in priorities)


def test_not_detected_precedes_partial_for_equal_impact():
    priorities = select_priorities(
        [
            result("PRV-104", "partial", "high"),
            result("PRV-501", "not_detected", "low"),
        ]
    )

    assert [priority["control_code"] for priority in priorities] == [
        "PRV-501",
        "PRV-104",
    ]
