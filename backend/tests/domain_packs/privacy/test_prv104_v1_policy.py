import sys
from pathlib import Path


BACKEND_SRC = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.domain_packs.privacy.prioritization import prioritize_findings  # noqa: E402
from mininode_api.domain_packs.privacy.scoring import score_privacy  # noqa: E402


def _result(code, result):
    return {"control_code": code, "result": result, "confidence": "high"}


def test_prv104_does_not_change_v1_score_or_coverage():
    baseline = [_result("PRV-301", "detected")]
    with_adverse_prv104 = baseline + [_result("PRV-104", "not_detected")]

    assert score_privacy(with_adverse_prv104) == score_privacy(baseline)


def test_prv104_does_not_create_v1_priority_or_correction_action():
    results = [
        _result("PRV-104", "not_detected"),
        _result("PRV-104", "partial"),
    ]

    assert prioritize_findings(results) == []
