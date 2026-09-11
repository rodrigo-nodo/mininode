from __future__ import annotations

from intent_llm_runner import Inference, IntentOutput
import qa8_evaluate as qa8


class FakeClient:
    def __init__(self):
        self.calls: list[str] = []

    def __call__(self, case, taxonomy):
        self.calls.append(case["blind_id"])
        return Inference(
            output=IntentOutput(
                intent_id="submit_generic",
                evidence=(),
                reason_short="generic submission",
                uncertain=False,
            ),
            valid=True,
            error=None,
            input_tokens=10,
            output_tokens=5,
            reasoning_tokens=0,
            latency_seconds=0.1,
            resolved_model="fake",
        )


def test_qa8_reference_is_frozen_and_matches_cases():
    cases = qa8.load_json(qa8.CASES_PATH)
    reference = qa8.load_json(qa8.REFERENCE_PATH)
    assert reference["frozen_before_model_evaluation"] is True
    assert len(cases["cases"]) == 28
    assert len(reference["cases"]) == 28
    assert {row["blind_id"] for row in cases["cases"]} == {
        row["blind_id"] for row in reference["cases"]
    }


def test_fallback_is_used_only_when_baseline_is_unknown():
    cases = qa8.load_json(qa8.CASES_PATH)["cases"]
    expected = [row["blind_id"] for row in cases if qa8.baseline_class(row) == "unknown"]
    fake = FakeClient()
    result = qa8.evaluate(client=fake)
    assert fake.calls == expected
    assert result["usage"]["llm_calls"] == len(expected)
    for row in result["rows"]:
        assert row["fallback_used"] is (row["baseline_v07"] == "unknown")


def test_quantitative_gates_are_the_frozen_qa8_thresholds():
    pass_metrics = {
        "false_concrete_promotions": 0,
        "false_adverse_none": 0,
        "invalid_outputs": 0,
        "emitted_precision": 0.90,
        "coverage": 0.70,
        "accuracy": 0.80,
        "concrete_recall": 0.75,
    }
    assert qa8._decision(pass_metrics) == "PASS"

    observations = dict(pass_metrics, coverage=0.60, accuracy=0.70, concrete_recall=0.65)
    assert qa8._decision(observations) == "PASS_WITH_OBSERVATIONS"

    unsafe = dict(pass_metrics, false_concrete_promotions=1)
    assert qa8._decision(unsafe) == "NEEDS_FIX"
