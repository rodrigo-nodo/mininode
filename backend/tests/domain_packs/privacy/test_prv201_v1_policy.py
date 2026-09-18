import sys
from pathlib import Path


BACKEND_SRC = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.domain_packs.privacy.evaluator import load_control_catalog  # noqa: E402
from mininode_api.domain_packs.privacy.prioritization import prioritize_findings  # noqa: E402
from mininode_api.domain_packs.privacy.scoring import score_privacy  # noqa: E402


def _result(code, result):
    return {"control_code": code, "result": result, "confidence": "high"}


def test_prv201_is_canonical_context_with_zero_weight():
    control = next(
        control for control in load_control_catalog()["controls"]
        if control["code"] == "PRV-201"
    )

    assert control["type"] == "context"
    assert control["score_weight"] == 0


def test_prv201_does_not_change_v1_score_or_coverage():
    baseline = [_result("PRV-301", "detected")]

    assert score_privacy(baseline + [_result("PRV-201", "detected")]) == score_privacy(baseline)
    assert score_privacy(baseline + [_result("PRV-201", "not_detected")]) == score_privacy(baseline)


def test_prv201_does_not_create_priority():
    assert prioritize_findings([
        _result("PRV-201", "detected"),
        _result("PRV-201", "not_detected"),
    ]) == []
