"""Evaluate the frozen PRV-103 QA8 candidate architecture after blind adjudication."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from mininode_api.domain_packs.privacy.evidence_adapter import _form_purpose_signal
from mininode_api.web_inspector.models import FormEvidence

from intent_llm_runner import (
    ALLOWED_FIELDS,
    Inference,
    MODEL_ID,
    PROMPT_VERSION,
    REASONING_EFFORT,
    final_class_for,
    load_json,
    openai_client,
)

HERE = Path(__file__).resolve().parent
CASES_PATH = HERE / "qa8_cases.json"
REFERENCE_PATH = HERE / "qa8_reference.json"
TAXONOMY_PATH = HERE / "intent_taxonomy.json"
FROZEN_MAIN_SHA = "2fcf1c093023d6761cce5460a0a85779f5b0d180"
FRAMEWORK_VERSION = "0.7"


def _form(case: dict[str, Any]) -> FormEvidence:
    return FormEvidence(
        source_url="https://qa8.invalid/",
        action="",
        method="post",
        fields=[],
        checkboxes=[],
        nearby_text="",
        privacy_links=[],
        heading=case.get("heading"),
        legend=case.get("legend"),
        introductory_text=case.get("introductory_text"),
        submit_text=case.get("submit_text"),
    )


def baseline_class(case: dict[str, Any]) -> str:
    return _form_purpose_signal(_form(case))


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    exact = sum(row["final_class"] == row["reference_class"] for row in rows)
    emitted = [row for row in rows if row["final_class"] != "unknown"]
    emitted_correct = sum(row["final_class"] == row["reference_class"] for row in emitted)
    gold_concrete = sum(row["reference_class"] == "concrete" for row in rows)
    pred_concrete = sum(row["final_class"] == "concrete" for row in rows)
    true_concrete = sum(row["final_class"] == row["reference_class"] == "concrete" for row in rows)
    return {
        "total": total,
        "exact": exact,
        "accuracy": exact / total if total else 0.0,
        "coverage": len(emitted) / total if total else 0.0,
        "emitted_precision": emitted_correct / len(emitted) if emitted else 1.0,
        "concrete_precision": true_concrete / pred_concrete if pred_concrete else 1.0,
        "concrete_recall": true_concrete / gold_concrete if gold_concrete else 1.0,
        "false_concrete_promotions": sum(
            row["final_class"] == "concrete" and row["reference_class"] != "concrete"
            for row in rows
        ),
        "false_adverse_none": sum(
            row["final_class"] == "none" and row["reference_class"] != "none"
            for row in rows
        ),
        "invalid_outputs": sum(row["fallback_used"] and not row["llm_valid"] for row in rows),
        "unknown_rate": sum(row["final_class"] == "unknown" for row in rows) / total if total else 0.0,
        "predicted_distribution": dict(Counter(row["final_class"] for row in rows)),
        "reference_distribution": dict(Counter(row["reference_class"] for row in rows)),
    }


def _decision(metrics: dict[str, Any]) -> str:
    if (
        metrics["false_concrete_promotions"] != 0
        or metrics["false_adverse_none"] != 0
        or metrics["invalid_outputs"] != 0
    ):
        return "NEEDS_FIX"
    if (
        metrics["emitted_precision"] >= 0.90
        and metrics["coverage"] >= 0.70
        and metrics["accuracy"] >= 0.80
        and metrics["concrete_recall"] >= 0.75
    ):
        return "PASS"
    if (
        metrics["emitted_precision"] >= 0.90
        and metrics["coverage"] >= 0.60
        and metrics["accuracy"] >= 0.70
        and metrics["concrete_recall"] >= 0.65
    ):
        return "PASS_WITH_OBSERVATIONS"
    return "NEEDS_FIX"


def evaluate(client=None) -> dict[str, Any]:
    cases_payload = load_json(CASES_PATH)
    reference_payload = load_json(REFERENCE_PATH)
    taxonomy = load_json(TAXONOMY_PATH)

    assert reference_payload["frozen_before_model_evaluation"] is True
    assert cases_payload["allowed_fields"] == list(ALLOWED_FIELDS)

    cases = cases_payload["cases"]
    reference = {row["blind_id"]: row for row in reference_payload["cases"]}
    assert len(cases) == len(reference) == 28
    assert {row["blind_id"] for row in cases} == set(reference)

    classify = client or openai_client(taxonomy)
    rows: list[dict[str, Any]] = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_reasoning_tokens = 0
    total_latency = 0.0
    llm_calls = 0

    for case in cases:
        blind_id = case["blind_id"]
        baseline = baseline_class(case)
        fallback_used = baseline == "unknown"
        llm_valid = True
        intent_id = None
        uncertain = None
        evidence: list[dict[str, str]] = []
        reason_short = None
        validation_error = None
        final_class = baseline

        if fallback_used:
            llm_calls += 1
            inference: Inference = classify(case, taxonomy)
            total_input_tokens += inference.input_tokens
            total_output_tokens += inference.output_tokens
            total_reasoning_tokens += inference.reasoning_tokens
            total_latency += inference.latency_seconds
            llm_valid = inference.valid
            validation_error = inference.error
            if inference.valid and inference.output is not None:
                output = inference.output
                intent_id = output.intent_id
                uncertain = output.uncertain
                evidence = [{"field": item.field, "quote": item.quote} for item in output.evidence]
                reason_short = output.reason_short
                final_class = final_class_for(output, taxonomy)
            else:
                final_class = "unknown"

        ref = reference[blind_id]
        rows.append(
            {
                "blind_id": blind_id,
                "reference_class": ref["reference_class"],
                "baseline_v07": baseline,
                "fallback_used": fallback_used,
                "llm_valid": llm_valid,
                "intent_id": intent_id,
                "uncertain": uncertain,
                "evidence": evidence,
                "reason_short": reason_short,
                "validation_error": validation_error,
                "final_class": final_class,
                "correct": final_class == ref["reference_class"],
            }
        )

    metrics = _metrics(rows)
    return {
        "qa_cycle": "PRV-103 QA8 fresh independent holdout",
        "configuration": {
            "frozen_main_sha": FROZEN_MAIN_SHA,
            "framework_version": FRAMEWORK_VERSION,
            "model_id": MODEL_ID,
            "prompt_version": PROMPT_VERSION,
            "reasoning_effort": REASONING_EFFORT,
            "taxonomy_version": taxonomy["taxonomy_version"],
            "architecture": "baseline_v07_then_llm_only_if_unknown",
            "reference_cases": len(rows),
        },
        "rows": rows,
        "metrics": metrics,
        "quantitative_decision": _decision(metrics),
        "usage": {
            "llm_calls": llm_calls,
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "reasoning_tokens": total_reasoning_tokens,
            "total_latency_seconds": total_latency,
            "average_latency_per_llm_call": total_latency / llm_calls if llm_calls else 0.0,
        },
        "errors": [row for row in rows if not row["correct"]],
        "note": "Quantitative decision applies the gates frozen before adjudication. A systematic generalizable error pattern may only downgrade the final QA decision after reviewing error rows; no tuning is permitted in this QA cycle.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/privacy-prv103-qa8-evaluation/result.json"))
    args = parser.parse_args()
    result = evaluate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "metrics": result["metrics"],
        "quantitative_decision": result["quantitative_decision"],
        "usage": result["usage"],
        "errors": result["errors"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
