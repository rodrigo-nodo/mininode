from __future__ import annotations

from backend.tests.domain_packs.privacy.prv103_semantic_benchmark.intent_llm_runner import load_json
from backend.tests.domain_packs.privacy.prv103_semantic_benchmark.qa6_intent_llm_runner import (
    GOLD_PATH,
    _run_passes_floor,
)


def quality(**overrides):
    base = {
        "false_concrete_promotions": 0,
        "false_adverse_none": 0,
        "invalid_outputs": 0,
        "emitted_precision": 0.95,
        "coverage": 0.80,
        "accuracy": 0.90,
        "concrete_recall": 0.85,
    }
    base.update(overrides)
    return base


def test_qa6_reference_is_frozen_blind_and_contains_46_unique_cases():
    reference = load_json(GOLD_PATH)
    assert reference["reference_frozen_before_model_outputs"] is True
    assert reference["independent_reviewer"] is False
    assert reference["allowed_fields"] == [
        "heading", "legend", "introductory_text", "submit_text"
    ]
    assert len(reference["cases"]) == 46
    ids = [case["blind_id"] for case in reference["cases"]]
    assert len(ids) == len(set(ids))
    assert all(
        set(case) == {
            "blind_id", "heading", "legend", "introductory_text", "submit_text", "gold"
        }
        for case in reference["cases"]
    )


def test_any_false_concrete_fails_both_qa6_floors():
    unsafe = quality(false_concrete_promotions=1)
    assert _run_passes_floor(unsafe, pass_level="pass") is False
    assert _run_passes_floor(unsafe, pass_level="observations") is False


def test_pass_and_observation_thresholds_are_frozen():
    assert _run_passes_floor(quality(), pass_level="pass") is True
    assert _run_passes_floor(
        quality(coverage=0.65, accuracy=0.75, concrete_recall=0.70),
        pass_level="pass",
    ) is False
    assert _run_passes_floor(
        quality(coverage=0.65, accuracy=0.75, concrete_recall=0.70),
        pass_level="observations",
    ) is True
