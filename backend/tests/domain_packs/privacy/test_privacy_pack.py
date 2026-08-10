import json
import sys
from pathlib import Path

import pytest


BACKEND_SRC = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.domain_packs.privacy.evaluator import (  # noqa: E402
    evaluate_privacy,
    load_controls,
)
from mininode_api.domain_packs.privacy.prioritization import (  # noqa: E402
    prioritize_findings,
)
from mininode_api.domain_packs.privacy.scoring import score_privacy  # noqa: E402


SCENARIO = {
    "PRV-001": "detected",
    "PRV-002": "partial",
    "PRV-101": "detected",
    "PRV-104": "not_detected",
    "PRV-201": "not_applicable",
    "PRV-301": "detected",
    "PRV-501": "detected",
}


def test_control_catalog_has_the_closed_v01_definition():
    controls = load_controls()
    assert [control["code"] for control in controls] == [
        "PRV-001", "PRV-002", "PRV-101", "PRV-104", "PRV-201",
        "PRV-301", "PRV-501",
    ]
    assert next(item for item in controls if item["code"] == "PRV-101")[
        "score_weight"
    ] == 0


def test_required_scenario_scores_67_with_full_coverage():
    result = score_privacy(evaluate_privacy(SCENARIO))
    assert result == {"score": 67, "state": "En preparación", "coverage": 100}


def test_not_evaluable_is_unscored_and_reduces_coverage():
    statuses = {**SCENARIO, "PRV-301": "not_evaluable"}
    result = score_privacy(evaluate_privacy(statuses))
    assert result["coverage"] == 80


def test_context_and_not_applicable_do_not_affect_score():
    baseline = score_privacy(evaluate_privacy(SCENARIO))
    changed_context = {**SCENARIO, "PRV-101": "not_detected"}
    assert score_privacy(evaluate_privacy(changed_context)) == baseline


def test_priorities_follow_impact_status_confidence_and_code_order():
    evaluations = evaluate_privacy(SCENARIO)
    for item in evaluations:
        item["confidence"] = 0.8
    priorities = prioritize_findings(evaluations)
    assert [item["code"] for item in priorities] == ["PRV-104", "PRV-002"]


def test_priorities_are_limited_to_three_and_exclude_context():
    statuses = {code: "not_detected" for code in SCENARIO}
    priorities = prioritize_findings(evaluate_privacy(statuses), limit=20)
    assert len(priorities) == 3
    assert all(item["type"] != "context" for item in priorities)


def test_invalid_input_is_rejected():
    with pytest.raises(ValueError, match="Unknown privacy controls"):
        evaluate_privacy({"PRV-999": "detected"})
    with pytest.raises(ValueError, match="Invalid status"):
        evaluate_privacy({"PRV-001": "unknown"})


def test_json_files_are_valid_utf8_json():
    privacy_dir = BACKEND_SRC / "mininode_api" / "domain_packs" / "privacy"
    for filename in ("controls.json", "scoring.json"):
        with (privacy_dir / filename).open(encoding="utf-8") as source:
            assert isinstance(json.load(source), dict)
