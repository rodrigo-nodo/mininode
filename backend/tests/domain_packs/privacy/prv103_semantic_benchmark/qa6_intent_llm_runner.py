"""PRV-103 Intent QA6 runner over the frozen fresh blind reference."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

from intent_llm_runner import (
    ALLOWED_FIELDS,
    CaseResult,
    Inference,
    final_class_for,
    load_json,
    metrics,
    openai_client,
    stability,
)

HERE = Path(__file__).resolve().parent
GOLD_PATH = HERE / "qa6_gold.json"
TAXONOMY_PATH = HERE / "intent_taxonomy.json"
MODEL_ID = "gpt-5.6-sol"
PROMPT_VERSION = "prv103-intent-v2-01"
REASONING_EFFORT = "medium"


def _run(client=None) -> dict[str, Any]:
    reference = load_json(GOLD_PATH)
    taxonomy = load_json(TAXONOMY_PATH)
    classify = client or openai_client(taxonomy)
    rows: list[CaseResult] = []

    assert reference["reference_frozen_before_model_outputs"] is True
    assert reference["allowed_fields"] == list(ALLOWED_FIELDS)

    for case in reference["cases"]:
        # The client receives the reference row, but the frozen PR #209 client builds
        # its API payload from ALLOWED_FIELDS only. Gold/blind_id are never sent.
        inference: Inference = classify(case, taxonomy)
        if inference.valid and inference.output is not None:
            output = inference.output
            intent_id = output.intent_id
            final_class = final_class_for(output, taxonomy)
            evidence = output.evidence
            reason = output.reason_short
            uncertain = output.uncertain
        else:
            intent_id = "__invalid__"
            final_class = "unknown"
            evidence = ()
            reason = inference.error or "invalid output"
            uncertain = True

        rows.append(
            CaseResult(
                case_id=case["blind_id"],
                source_cycle="QA6",
                split="fresh_holdout",
                gold=case["gold"],
                baseline_v07=None,
                intent_id=intent_id,
                final_class=final_class,
                evidence=evidence,
                reason_short=reason,
                uncertain=uncertain,
                valid_output=inference.valid,
                validation_error=inference.error,
                input_tokens=inference.input_tokens,
                output_tokens=inference.output_tokens,
                reasoning_tokens=inference.reasoning_tokens,
                latency_seconds=inference.latency_seconds,
                resolved_model=inference.resolved_model,
            )
        )

    return {
        "qa_cycle": "PRV-103 Intent QA6",
        "configuration": {
            "model_id": MODEL_ID,
            "prompt_version": PROMPT_VERSION,
            "reasoning_effort": REASONING_EFFORT,
            "taxonomy_version": taxonomy["taxonomy_version"],
            "reference_cases": len(reference["cases"]),
            "reference_independent_reviewer": reference["independent_reviewer"],
        },
        "results": [
            {**asdict(row), "evidence": [asdict(item) for item in row.evidence]}
            for row in rows
        ],
        "quality": metrics(rows),
        "usage": {
            "calls": len(rows),
            "input_tokens": sum(row.input_tokens for row in rows),
            "output_tokens": sum(row.output_tokens for row in rows),
            "reasoning_tokens": sum(row.reasoning_tokens for row in rows),
            "total_latency_seconds": sum(row.latency_seconds for row in rows),
            "average_latency_seconds": (
                sum(row.latency_seconds for row in rows) / len(rows) if rows else 0.0
            ),
            "resolved_models": sorted({row.resolved_model for row in rows if row.resolved_model}),
        },
    }


def _rows(payload: dict[str, Any]) -> list[CaseResult]:
    from intent_llm_runner import EvidenceItem

    rows = []
    for raw in payload["results"]:
        evidence = tuple(EvidenceItem(**item) for item in raw["evidence"])
        rows.append(CaseResult(**{**raw, "evidence": evidence}))
    return rows


def _run_passes_floor(quality: dict[str, Any], *, pass_level: str) -> bool:
    if (
        quality["false_concrete_promotions"] != 0
        or quality["false_adverse_none"] != 0
        or quality["invalid_outputs"] != 0
    ):
        return False
    if pass_level == "pass":
        return (
            quality["emitted_precision"] >= 0.90
            and quality["coverage"] >= 0.70
            and quality["accuracy"] >= 0.80
            and quality["concrete_recall"] >= 0.75
        )
    if pass_level == "observations":
        return (
            quality["emitted_precision"] >= 0.90
            and quality["coverage"] >= 0.60
            and quality["accuracy"] >= 0.70
            and quality["concrete_recall"] >= 0.65
        )
    raise ValueError(pass_level)


def build_summary(run1: dict[str, Any], run2: dict[str, Any]) -> dict[str, Any]:
    stable = stability(_rows(run1), _rows(run2))
    q1 = run1["quality"]
    q2 = run2["quality"]

    if _run_passes_floor(q1, pass_level="pass") and _run_passes_floor(q2, pass_level="pass") and stable["class_stability"] >= 0.95:
        decision = "PASS"
    elif _run_passes_floor(q1, pass_level="observations") and _run_passes_floor(q2, pass_level="observations") and stable["class_stability"] >= 0.90:
        decision = "PASS_WITH_OBSERVATIONS"
    else:
        decision = "NEEDS_FIX"

    return {
        "qa_cycle": "PRV-103 Intent QA6",
        "run_1_quality": q1,
        "run_2_quality": q2,
        "stability": stable,
        "decision": decision,
        "safety_gate": {
            "run_1_false_concrete": q1["false_concrete_promotions"],
            "run_2_false_concrete": q2["false_concrete_promotions"],
            "run_1_false_none": q1["false_adverse_none"],
            "run_2_false_none": q2["false_adverse_none"],
            "run_1_invalid": q1["invalid_outputs"],
            "run_2_invalid": q2["invalid_outputs"],
        },
        "reference_independent_reviewer": run1["configuration"]["reference_independent_reviewer"],
        "production_changed": False,
    }


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run", "summary"))
    parser.add_argument("--run", type=int, choices=(1, 2))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/prv103-intent-qa6"))
    args = parser.parse_args()

    if args.command == "run":
        if not args.run:
            parser.error("run requires --run 1 or 2")
        payload = _run()
        payload["run_number"] = args.run
        _write(args.output_dir / f"run-{args.run}.json", payload)
        print(json.dumps({"run": args.run, "quality": payload["quality"], "usage": payload["usage"]}, ensure_ascii=False, indent=2))
        return

    run1 = load_json(args.output_dir / "run-1.json")
    run2 = load_json(args.output_dir / "run-2.json")
    summary = build_summary(run1, run2)
    _write(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
