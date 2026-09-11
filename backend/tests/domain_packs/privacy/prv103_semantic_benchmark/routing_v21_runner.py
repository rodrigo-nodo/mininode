"""Final consumed-data benchmark for PRV-103 semantic contract v2.1.

Research-only. Uses QA6-QA8 already consumed. It evaluates only the final
Semantic Residual Router candidate; it does not touch production and must not be
used as a fresh QA.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

import routing_v2_runner as base

HERE = Path(__file__).resolve().parent
TAXONOMY_PATH = HERE / "intent_taxonomy_v21.json"
CONTRACT_PATH = HERE / "semantic_contract_v21.json"
MODEL_ID = "gpt-5.6-sol"
PROMPT_VERSION = "prv103-intent-v2-03"
REASONING_EFFORT = "medium"

_BASE_INSTRUCTIONS = base.instructions_v2


def _apply_overrides_v21(rows: list[dict[str, Any]], contract: dict[str, Any]) -> None:
    by_key = {(row["dataset"], row["blind_id"]): row for row in rows}
    for override in contract["reference_overrides"]:
        key = (override["dataset"], override["blind_id"])
        if key not in by_key:
            raise ValueError(f"semantic v2.1 override references missing case: {key}")
        row = by_key[key]
        if row["historical_reference"] != override["historical"]:
            raise ValueError(f"historical reference drift for {key}")
        row["reference_v2"] = override["v21"]
        row["reference_override_reason"] = override["reason"]


def instructions_v21(taxonomy: dict[str, Any]) -> str:
    return _BASE_INSTRUCTIONS(taxonomy) + (
        " Regla v2.1 adicional: pedir ayuda, publicar una pregunta, hablar con una empresa "
        "o contactar ventas sigue siendo contact_generic cuando el mismo formulario no "
        "nombra una tarea, servicio o resultado específico. Obtener un descuento, cupón, "
        "beneficio u oferta explícita es promotion_or_discount."
    )


def configure_base() -> None:
    base.TAXONOMY_PATH = TAXONOMY_PATH
    base.CONTRACT_PATH = CONTRACT_PATH
    base.MODEL_ID = MODEL_ID
    base.PROMPT_VERSION = PROMPT_VERSION
    base.REASONING_EFFORT = REASONING_EFFORT
    base._apply_overrides = _apply_overrides_v21
    base.instructions_v2 = instructions_v21


def load_development_cases() -> list[dict[str, Any]]:
    configure_base()
    return base.load_development_cases()


def run_residual_once(cases: list[dict[str, Any]], client=None) -> dict[str, Any]:
    configure_base()
    taxonomy = base.load_json(TAXONOMY_PATH)
    contract = base.load_json(CONTRACT_PATH)
    classify = client or base.openai_client_v2(taxonomy)

    rows: list[dict[str, Any]] = []
    usage = Counter()
    resolved_models: set[str] = set()

    for case in cases:
        common = {
            "dataset": case["dataset"],
            "blind_id": case["blind_id"],
            "reference": case["reference_v2"],
        }
        fast = base.residual_fast_path(case, contract)
        if fast is not None:
            predicted, route = fast
            rows.append(
                {
                    **common,
                    "prediction": predicted,
                    "valid_output": True,
                    "intent_id": "__deterministic__",
                    "uncertain": predicted == "unknown",
                    "evidence_fields": [],
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "reasoning_tokens": 0,
                    "latency_seconds": 0.0,
                    "resolved_model": None,
                    "llm_used": False,
                    "route": route,
                }
            )
            continue

        inference = classify(case, taxonomy)
        semantic = base._semantic_prediction(case, inference, taxonomy)
        usage.update(
            {
                "calls": 1,
                "input_tokens": semantic["input_tokens"],
                "output_tokens": semantic["output_tokens"],
                "reasoning_tokens": semantic["reasoning_tokens"],
            }
        )
        usage["latency_millis"] += int(round(semantic["latency_seconds"] * 1000))
        if semantic["resolved_model"]:
            resolved_models.add(semantic["resolved_model"])
        rows.append({**common, **semantic, "llm_used": True, "route": "semantic_llm"})

    return {
        "rows": rows,
        "usage": {
            "calls": usage["calls"],
            "input_tokens": usage["input_tokens"],
            "output_tokens": usage["output_tokens"],
            "reasoning_tokens": usage["reasoning_tokens"],
            "total_latency_seconds": usage["latency_millis"] / 1000,
            "resolved_models": sorted(resolved_models),
        },
    }


def _passes(metrics: dict[str, Any], gates: dict[str, Any]) -> bool:
    return (
        metrics["false_concrete_promotions"] == gates["false_concrete_promotions"]
        and metrics["false_adverse_none"] == gates["false_adverse_none"]
        and metrics["invalid_outputs"] == gates["invalid_outputs"]
        and metrics["accuracy"] >= gates["minimum_accuracy"]
        and metrics["emitted_precision"] >= gates["minimum_emitted_precision"]
        and metrics["concrete_recall"] >= gates["minimum_concrete_recall"]
    )


def evaluate(run1: dict[str, Any], run2: dict[str, Any], cases: list[dict[str, Any]]) -> dict[str, Any]:
    contract = base.load_json(CONTRACT_PATH)
    gates = contract["final_development_gates"]
    m1 = base.metrics(run1["rows"])
    m2 = base.metrics(run2["rows"])
    stability = base.class_stability(run1["rows"], run2["rows"])
    total = len(cases)
    call_reduction_1 = 1 - (m1["llm_calls"] / total if total else 0.0)
    call_reduction_2 = 1 - (m2["llm_calls"] / total if total else 0.0)
    minimum_reduction = min(call_reduction_1, call_reduction_2)
    ready = (
        _passes(m1, gates)
        and _passes(m2, gates)
        and stability >= gates["minimum_class_stability"]
        and minimum_reduction >= gates["minimum_llm_call_reduction_vs_all_cases"]
    )
    return {
        "decision": "ready_for_qa9" if ready else "stop_semantic_line",
        "reason": (
            "Final v2.1 residual candidate meets all frozen development gates; QA9 may be prepared."
            if ready
            else "Final v2.1 residual candidate misses at least one frozen gate; stop this line and do not consume QA9."
        ),
        "run_1": m1,
        "run_2": m2,
        "class_stability": stability,
        "llm_call_reduction_vs_all_cases": minimum_reduction,
        "gates": gates,
    }


def _compact(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "dataset": row["dataset"],
            "blind_id": row["blind_id"],
            "reference": row["reference"],
            "prediction": row["prediction"],
            "correct": row["prediction"] == row["reference"],
            "route": row["route"],
            "llm_used": row["llm_used"],
            "intent_id": row["intent_id"],
            "uncertain": row["uncertain"],
            "valid_output": row["valid_output"],
            "evidence_fields": row.get("evidence_fields", []),
        }
        for row in rows
    ]


def build_result(run1: dict[str, Any], run2: dict[str, Any], cases: list[dict[str, Any]]) -> dict[str, Any]:
    contract = base.load_json(CONTRACT_PATH)
    evaluation = evaluate(run1, run2, cases)
    return {
        "benchmark": "PRV-103 semantic routing v2.1 final development benchmark",
        "fresh_qa": False,
        "production_changed": False,
        "configuration": {
            "model": MODEL_ID,
            "prompt_version": PROMPT_VERSION,
            "reasoning_effort": REASONING_EFFORT,
            "taxonomy_version": base.load_json(TAXONOMY_PATH)["taxonomy_version"],
            "contract_version": contract["contract_version"],
            "cases": len(cases),
            "datasets": dict(Counter(case["dataset"] for case in cases)),
            "reference_overrides": contract["reference_overrides"],
        },
        "decision": evaluation,
        "run_1": {
            "metrics": base.metrics(run1["rows"]),
            "by_dataset": base.metrics_by_dataset(run1["rows"]),
            "usage": run1["usage"],
            "rows": _compact(run1["rows"]),
        },
        "run_2": {
            "metrics": base.metrics(run2["rows"]),
            "by_dataset": base.metrics_by_dataset(run2["rows"]),
            "usage": run2["usage"],
            "rows": _compact(run2["rows"]),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    cases = load_development_cases()
    taxonomy = base.load_json(TAXONOMY_PATH)
    client = base.openai_client_v2(taxonomy)
    run1 = run_residual_once(cases, client=client)
    run2 = run_residual_once(cases, client=client)
    result = build_result(run1, run2, cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
