from __future__ import annotations

from copy import deepcopy

import routing_v21_runner as runner


def test_v21_contract_is_final_and_reference_is_harmonized():
    contract = runner.base.load_json(runner.CONTRACT_PATH)
    assert contract["contract_version"] == "prv103-semantic-v2.1"
    assert contract["final_development_candidate"] is True
    assert len(contract["reference_overrides"]) == 6

    rows = runner.load_development_cases()
    assert len(rows) == 104
    assert {dataset: sum(row["dataset"] == dataset for row in rows) for dataset in ("QA6", "QA7", "QA8")} == {
        "QA6": 46,
        "QA7": 30,
        "QA8": 28,
    }
    by_id = {(row["dataset"], row["blind_id"]): row for row in rows}
    assert by_id[("QA6", "QA6_CHILE-009")]["reference_v2"] == "generic"
    assert by_id[("QA6", "QA6_INTL-014")]["reference_v2"] == "generic"
    assert by_id[("QA7", "QA7-007")]["reference_v2"] == "generic"
    assert by_id[("QA8", "QA8-007")]["reference_v2"] == "unknown"
    assert by_id[("QA8", "QA8-016")]["reference_v2"] == "generic"
    assert by_id[("QA8", "QA8-021")]["reference_v2"] == "generic"

    distribution = {label: sum(row["reference_v2"] == label for row in rows) for label in ("concrete", "generic", "none", "unknown")}
    assert distribution == {"concrete": 23, "generic": 67, "none": 3, "unknown": 11}


def test_v21_router_only_shortcuts_safe_cases():
    contract = runner.base.load_json(runner.CONTRACT_PATH)
    rows = runner.load_development_cases()
    routes = [runner.base.residual_fast_path(row, contract) for row in rows]
    counts = {
        "empty_case": sum(route == ("unknown", "empty_case") for route in routes),
        "technical_only": sum(route == ("none", "technical_only") for route in routes),
        "trivial_generic": sum(route == ("generic", "trivial_generic") for route in routes),
        "semantic_llm": sum(route is None for route in routes),
    }
    assert counts == {"empty_case": 9, "technical_only": 3, "trivial_generic": 58, "semantic_llm": 34}
    assert all(route is None or route[0] != "concrete" for route in routes)


def _row(reference: str, prediction: str, *, llm_used: bool) -> dict:
    return {
        "dataset": "QA6",
        "blind_id": reference + prediction + str(llm_used),
        "reference": reference,
        "prediction": prediction,
        "valid_output": True,
        "llm_used": llm_used,
        "intent_id": "x",
        "uncertain": prediction == "unknown",
        "route": "semantic_llm" if llm_used else "trivial_generic",
    }


def test_v21_decision_allows_qa9_only_when_all_frozen_gates_pass(monkeypatch):
    cases = [{"dataset": "QA6", "blind_id": f"C{i}"} for i in range(100)]
    good_metrics = {
        "total": 100,
        "exact": 95,
        "accuracy": 0.95,
        "coverage": 0.9,
        "emitted_precision": 0.95,
        "concrete_precision": 1.0,
        "concrete_recall": 0.9,
        "false_concrete_promotions": 0,
        "false_adverse_none": 0,
        "invalid_outputs": 0,
        "unknown_rate": 0.1,
        "llm_calls": 34,
        "predicted_distribution": {},
        "reference_distribution": {},
        "route_distribution": {},
    }
    run1 = {"rows": [_row("generic", "generic", llm_used=False)]}
    run2 = deepcopy(run1)

    monkeypatch.setattr(runner.base, "metrics", lambda rows: dict(good_metrics))
    monkeypatch.setattr(runner.base, "class_stability", lambda left, right: 0.99)
    decision = runner.evaluate(run1, run2, cases)
    assert decision["decision"] == "ready_for_qa9"

    bad = dict(good_metrics)
    bad["false_concrete_promotions"] = 1
    monkeypatch.setattr(runner.base, "metrics", lambda rows: dict(bad))
    decision = runner.evaluate(run1, run2, cases)
    assert decision["decision"] == "stop_semantic_line"
