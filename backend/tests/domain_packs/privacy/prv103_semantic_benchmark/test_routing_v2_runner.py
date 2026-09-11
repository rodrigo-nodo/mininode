from __future__ import annotations

from copy import deepcopy

import routing_v2_runner as runner


def case(**values):
    row = {field: None for field in runner.ALLOWED_FIELDS}
    row.update(values)
    return row


def test_v2_development_dataset_is_frozen_and_harmonized():
    rows = runner.load_development_cases()
    assert len(rows) == 104
    assert {dataset: sum(row["dataset"] == dataset for row in rows) for dataset in ("QA6", "QA7", "QA8")} == {
        "QA6": 46,
        "QA7": 30,
        "QA8": 28,
    }
    by_id = {(row["dataset"], row["blind_id"]): row for row in rows}
    assert by_id[("QA6", "QA6_CHILE-009")]["reference_v2"] == "generic"
    assert by_id[("QA7", "QA7-019")]["reference_v2"] == "generic"
    assert by_id[("QA8", "QA8-007")]["reference_v2"] == "unknown"
    assert by_id[("QA8", "QA8-016")]["reference_v2"] == "generic"
    assert by_id[("QA8", "QA8-021")]["reference_v2"] == "generic"


def test_residual_router_only_handles_safe_fast_paths():
    contract = runner.load_json(runner.CONTRACT_PATH)
    assert runner.residual_fast_path(case(), contract) == ("unknown", "empty_case")
    assert runner.residual_fast_path(case(submit_text="Enviar"), contract) == ("generic", "trivial_generic")
    assert runner.residual_fast_path(case(submit_text="Subscribe Sending..."), contract) == (
        "generic",
        "trivial_generic",
    )
    assert runner.residual_fast_path(
        case(introductory_text="* indicates a required field.", submit_text="Submit"), contract
    ) == ("generic", "trivial_generic")
    assert runner.residual_fast_path(case(heading="Form", submit_text="Send Message"), contract) == (
        "generic",
        "trivial_generic",
    )
    assert runner.residual_fast_path(case(introductory_text="OR"), contract) == ("none", "technical_only")
    assert runner.residual_fast_path(case(legend="Notice", submit_text="Loading..."), contract) == (
        "none",
        "technical_only",
    )


def test_residual_router_delegates_semantic_cases_and_never_fast_paths_concrete():
    contract = runner.load_json(runner.CONTRACT_PATH)
    semantic = [
        case(submit_text="Request a demo"),
        case(submit_text="Try for free"),
        case(submit_text="Talk to Vercel"),
        case(introductory_text="Get expert tips delivered to your inbox.", submit_text="Subscribe"),
        case(heading="Contact Splunk sales", submit_text="Send my question"),
    ]
    assert all(runner.residual_fast_path(item, contract) is None for item in semantic)

    rows = runner.load_development_cases()
    routed = [runner.residual_fast_path(row, contract) for row in rows]
    assert all(route is None or route[0] != "concrete" for route in routed)


def _metric_template(*, accuracy=0.95, precision=0.95, recall=0.9, calls=100):
    return {
        "total": 100,
        "exact": int(accuracy * 100),
        "accuracy": accuracy,
        "coverage": 0.95,
        "emitted_precision": precision,
        "concrete_precision": 1.0,
        "concrete_recall": recall,
        "false_concrete_promotions": 0,
        "false_adverse_none": 0,
        "invalid_outputs": 0,
        "unknown_rate": 0.05,
        "llm_calls": calls,
        "predicted_distribution": {},
        "reference_distribution": {},
        "route_distribution": {},
    }


def _run_payload():
    def rows(prediction="generic"):
        return [
            {
                "dataset": "QA6",
                "blind_id": f"X{i}",
                "reference": prediction,
                "prediction": prediction,
                "valid_output": True,
                "llm_used": True,
                "intent_id": "x",
                "uncertain": False,
                "route": "x",
            }
            for i in range(100)
        ]

    return {"llm_all": rows(), "residual": rows(), "usage_all_calls": {}}


def test_selection_prefers_residual_when_quality_is_equivalent_and_calls_drop(monkeypatch):
    contract = runner.load_json(runner.CONTRACT_PATH)
    all_metrics = _metric_template(calls=100)
    residual_metrics = _metric_template(accuracy=0.94, calls=55)
    run1 = _run_payload()
    run2 = deepcopy(run1)

    metric_by_id = {
        id(run1["llm_all"]): all_metrics,
        id(run1["residual"]): residual_metrics,
        id(run2["llm_all"]): all_metrics,
        id(run2["residual"]): residual_metrics,
    }

    def fake_metrics(rows):
        return metric_by_id[id(rows)]

    monkeypatch.setattr(runner, "metrics", fake_metrics)
    selected = runner.select_architecture(run1, run2, contract)
    assert selected["selected"] == "semantic_residual_router"
    assert selected["llm_call_reduction_vs_all"] == 0.45
