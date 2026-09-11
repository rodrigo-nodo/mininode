"""Development benchmark for PRV-103 semantic contract v2.

This is research-only. It compares the current deterministic baseline, LLM-all,
and a semantic residual router over already-consumed QA6-QA8 cases. It must not
be used as a fresh QA or imported by production code.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from intent_llm_runner import (
    ALLOWED_FIELDS,
    Inference,
    final_class_for,
    load_json,
    output_schema,
    validate_output,
)
from mininode_api.domain_packs.privacy.evidence_adapter import _form_purpose_signal
from mininode_api.web_inspector.models import FormEvidence

HERE = Path(__file__).resolve().parent
QA6_PATH = HERE / "qa6_gold.json"
QA7_CASES_PATH = HERE / "qa7_cases.json"
QA7_REFERENCE_PATH = HERE / "qa7_reference.json"
QA8_CASES_PATH = HERE / "qa8_cases.json"
QA8_REFERENCE_PATH = HERE / "qa8_reference.json"
TAXONOMY_PATH = HERE / "intent_taxonomy_v2.json"
CONTRACT_PATH = HERE / "semantic_contract_v2.json"

MODEL_ID = "gpt-5.6-sol"
PROMPT_VERSION = "prv103-intent-v2-02"
REASONING_EFFORT = "medium"
LABELS = ("concrete", "generic", "none", "unknown")

Classifier = Callable[[dict[str, Any], dict[str, Any]], Inference]


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _reference_map(path: Path, field: str) -> dict[str, str]:
    payload = load_json(path)
    return {row["blind_id"]: row[field] for row in payload["cases"]}


def _apply_overrides(rows: list[dict[str, Any]], contract: dict[str, Any]) -> None:
    by_key = {(row["dataset"], row["blind_id"]): row for row in rows}
    for override in contract["reference_overrides"]:
        key = (override["dataset"], override["blind_id"])
        if key not in by_key:
            raise ValueError(f"semantic v2 override references missing case: {key}")
        row = by_key[key]
        if row["historical_reference"] != override["historical"]:
            raise ValueError(f"historical reference drift for {key}")
        row["reference_v2"] = override["v2"]
        row["reference_override_reason"] = override["reason"]


def load_development_cases() -> list[dict[str, Any]]:
    contract = load_json(CONTRACT_PATH)
    rows: list[dict[str, Any]] = []

    qa6 = load_json(QA6_PATH)
    for case in qa6["cases"]:
        rows.append(
            {
                "dataset": "QA6",
                "blind_id": case["blind_id"],
                **{field: case.get(field) for field in ALLOWED_FIELDS},
                "historical_reference": case["gold"],
                "reference_v2": case["gold"],
            }
        )

    qa7_cases = load_json(QA7_CASES_PATH)
    qa7_ref = _reference_map(QA7_REFERENCE_PATH, "reference")
    for case in qa7_cases["cases"]:
        blind_id = case["blind_id"]
        if blind_id not in qa7_ref:
            raise ValueError(f"QA7 reference missing {blind_id}")
        rows.append(
            {
                "dataset": "QA7",
                "blind_id": blind_id,
                **{field: case.get(field) for field in ALLOWED_FIELDS},
                "historical_reference": qa7_ref[blind_id],
                "reference_v2": qa7_ref[blind_id],
            }
        )

    qa8_cases = load_json(QA8_CASES_PATH)
    qa8_ref = _reference_map(QA8_REFERENCE_PATH, "reference_class")
    for case in qa8_cases["cases"]:
        blind_id = case["blind_id"]
        if blind_id not in qa8_ref:
            raise ValueError(f"QA8 reference missing {blind_id}")
        rows.append(
            {
                "dataset": "QA8",
                "blind_id": blind_id,
                **{field: case.get(field) for field in ALLOWED_FIELDS},
                "historical_reference": qa8_ref[blind_id],
                "reference_v2": qa8_ref[blind_id],
            }
        )

    _apply_overrides(rows, contract)
    if len({(row["dataset"], row["blind_id"]) for row in rows}) != len(rows):
        raise ValueError("duplicate development case")
    return rows


def residual_fast_path(case: dict[str, Any], contract: dict[str, Any]) -> tuple[str, str] | None:
    values = {field: _normalize(case.get(field)) for field in ALLOWED_FIELDS}
    nonempty = [value for value in values.values() if value]
    if not nonempty:
        return "unknown", "empty_case"

    router = contract["router"]
    technical = set(router["technical_text"])
    technical_context = set(router["technical_context_text"])
    if all(value in technical | technical_context for value in nonempty) and any(
        value in technical for value in nonempty
    ):
        return "none", "technical_only"

    submit = values["submit_text"]
    trivial = set(router["trivial_generic_submit_text"])
    neutral = set(router["neutral_context_text"])
    context = [values[field] for field in ALLOWED_FIELDS[:-1] if values[field]]
    if submit in trivial and all(value in neutral for value in context):
        return "generic", "trivial_generic"

    return None


def _form(case: dict[str, Any]) -> FormEvidence:
    return FormEvidence(
        source_url="https://blind.invalid/form",
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


def baseline_rows(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "dataset": case["dataset"],
            "blind_id": case["blind_id"],
            "reference": case["reference_v2"],
            "prediction": _form_purpose_signal(_form(case)),
            "valid_output": True,
            "llm_used": False,
            "intent_id": "baseline_v07",
            "uncertain": False,
            "route": "baseline_v07",
        }
        for case in cases
    ]


def catalog_for_model(taxonomy: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"intent_id": item["id"], "examples": item["prototypes"]}
        for item in taxonomy["intents"]
    ]


def instructions_v2(taxonomy: dict[str, Any]) -> str:
    catalog = json.dumps(catalog_for_model(taxonomy), ensure_ascii=False, separators=(",", ":"))
    return (
        "Clasifica únicamente la intención observable del formulario recibido. "
        "No decidas cumplimiento ni clases de producto. Usa solo heading, legend, "
        "introductory_text y submit_text; no uses conocimiento externo, URL, campos, "
        "organización inferida ni contexto de página ausente. Elige exactamente un "
        "intent_id del catálogo cerrado. Reglas de frontera: un destinatario nombrado, "
        "una empresa, un equipo o ventas no convierten por sí solos el contacto en una "
        "finalidad concreta. Contactar, hablar con alguien, enviar un mensaje o una "
        "pregunta general/de ventas sigue siendo contact_generic si el mismo formulario "
        "no expresa otro resultado o servicio específico. Soporte o ayuda son concretos "
        "solo cuando el texto del mismo formulario expresa claramente ese servicio. "
        "Una suscripción es concreta solo si describe qué contenido, alertas o comunicaciones "
        "se recibirán. 'Try for free' o equivalente aislado, sin objeto o resultado de "
        "creación visible, es ambiguous_action; crear una cuenta/workspace explícita sí "
        "es trial_or_creation. Texto puramente técnico o estructural como OR, Loading... "
        "o placeholders puede ser technical_placeholder. Si la evidencia no soporta "
        "claramente una intención o existe conflicto, uncertain=true. evidence debe citar "
        "literalmente substrings de los campos recibidos y solo los campos necesarios. "
        "reason_short debe ser una frase breve basada en evidencia visible, sin razonamiento "
        "interno. Catálogo cerrado de intenciones: " + catalog
    )


def openai_client_v2(taxonomy: dict[str, Any]) -> Classifier:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("Install experiment-only dependency 'openai'.") from exc

    sdk = OpenAI(timeout=30.0, max_retries=1)
    schema = output_schema(taxonomy)
    frozen_instructions = instructions_v2(taxonomy)

    def classify(case: dict[str, Any], _: dict[str, Any]) -> Inference:
        form = {field: case.get(field) for field in ALLOWED_FIELDS}
        started = time.perf_counter()
        response = sdk.responses.create(
            model=MODEL_ID,
            reasoning={"effort": REASONING_EFFORT},
            instructions=frozen_instructions,
            input=json.dumps(form, ensure_ascii=False),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "prv103_intent_adjudication_v2",
                    "strict": True,
                    "schema": schema,
                }
            },
            max_output_tokens=256,
            store=False,
        )
        elapsed = time.perf_counter() - started
        usage = response.usage
        details = getattr(usage, "output_tokens_details", None)
        reasoning_tokens = int(getattr(details, "reasoning_tokens", 0) or 0)
        try:
            parsed = json.loads(response.output_text)
            output = validate_output(parsed, case, taxonomy)
            return Inference(
                output=output,
                valid=True,
                error=None,
                input_tokens=int(usage.input_tokens),
                output_tokens=int(usage.output_tokens),
                reasoning_tokens=reasoning_tokens,
                latency_seconds=elapsed,
                resolved_model=getattr(response, "model", None),
            )
        except (ValueError, json.JSONDecodeError) as exc:
            return Inference(
                output=None,
                valid=False,
                error=str(exc),
                input_tokens=int(usage.input_tokens),
                output_tokens=int(usage.output_tokens),
                reasoning_tokens=reasoning_tokens,
                latency_seconds=elapsed,
                resolved_model=getattr(response, "model", None),
            )

    return classify


def _semantic_prediction(case: dict[str, Any], inference: Inference, taxonomy: dict[str, Any]) -> dict[str, Any]:
    if inference.valid and inference.output is not None:
        output = inference.output
        final_class = final_class_for(output, taxonomy)
        intent_id = output.intent_id
        uncertain = output.uncertain
        evidence_fields = [item.field for item in output.evidence]
    else:
        final_class = "unknown"
        intent_id = "__invalid__"
        uncertain = True
        evidence_fields = []
    return {
        "prediction": final_class,
        "valid_output": inference.valid,
        "intent_id": intent_id,
        "uncertain": uncertain,
        "evidence_fields": evidence_fields,
        "input_tokens": inference.input_tokens,
        "output_tokens": inference.output_tokens,
        "reasoning_tokens": inference.reasoning_tokens,
        "latency_seconds": inference.latency_seconds,
        "resolved_model": inference.resolved_model,
    }


def run_once(cases: list[dict[str, Any]], client: Classifier | None = None) -> dict[str, Any]:
    taxonomy = load_json(TAXONOMY_PATH)
    contract = load_json(CONTRACT_PATH)
    classify = client or openai_client_v2(taxonomy)

    llm_all: list[dict[str, Any]] = []
    residual: list[dict[str, Any]] = []
    usage = Counter()
    resolved_models: set[str] = set()

    for case in cases:
        inference = classify(case, taxonomy)
        semantic = _semantic_prediction(case, inference, taxonomy)
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

        common = {
            "dataset": case["dataset"],
            "blind_id": case["blind_id"],
            "reference": case["reference_v2"],
        }
        llm_all.append({**common, **semantic, "llm_used": True, "route": "llm_all"})

        fast = residual_fast_path(case, contract)
        if fast is None:
            residual.append({**common, **semantic, "llm_used": True, "route": "semantic_llm"})
        else:
            fast_class, route = fast
            residual.append(
                {
                    **common,
                    "prediction": fast_class,
                    "valid_output": True,
                    "intent_id": "__deterministic__",
                    "uncertain": fast_class == "unknown",
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

    return {
        "llm_all": llm_all,
        "residual": residual,
        "usage_all_calls": {
            "calls": usage["calls"],
            "input_tokens": usage["input_tokens"],
            "output_tokens": usage["output_tokens"],
            "reasoning_tokens": usage["reasoning_tokens"],
            "total_latency_seconds": usage["latency_millis"] / 1000,
            "resolved_models": sorted(resolved_models),
        },
    }


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    exact = sum(row["prediction"] == row["reference"] for row in rows)
    emitted = [row for row in rows if row["prediction"] != "unknown"]
    emitted_correct = sum(row["prediction"] == row["reference"] for row in emitted)
    gold_concrete = sum(row["reference"] == "concrete" for row in rows)
    pred_concrete = sum(row["prediction"] == "concrete" for row in rows)
    true_concrete = sum(row["prediction"] == row["reference"] == "concrete" for row in rows)
    return {
        "total": total,
        "exact": exact,
        "accuracy": exact / total if total else 1.0,
        "coverage": len(emitted) / total if total else 1.0,
        "emitted_precision": emitted_correct / len(emitted) if emitted else 1.0,
        "concrete_precision": true_concrete / pred_concrete if pred_concrete else 1.0,
        "concrete_recall": true_concrete / gold_concrete if gold_concrete else 1.0,
        "false_concrete_promotions": sum(
            row["prediction"] == "concrete" and row["reference"] != "concrete" for row in rows
        ),
        "false_adverse_none": sum(
            row["prediction"] == "none" and row["reference"] != "none" for row in rows
        ),
        "invalid_outputs": sum(not row["valid_output"] for row in rows if row["llm_used"]),
        "unknown_rate": sum(row["prediction"] == "unknown" for row in rows) / total if total else 0.0,
        "llm_calls": sum(row["llm_used"] for row in rows),
        "predicted_distribution": dict(Counter(row["prediction"] for row in rows)),
        "reference_distribution": dict(Counter(row["reference"] for row in rows)),
        "route_distribution": dict(Counter(row["route"] for row in rows)),
    }


def metrics_by_dataset(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        dataset: metrics([row for row in rows if row["dataset"] == dataset])
        for dataset in ("QA6", "QA7", "QA8")
    }


def class_stability(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> float:
    left_map = {(row["dataset"], row["blind_id"]): row["prediction"] for row in left}
    right_map = {(row["dataset"], row["blind_id"]): row["prediction"] for row in right}
    if left_map.keys() != right_map.keys():
        raise ValueError("stability runs contain different cases")
    return sum(left_map[key] == right_map[key] for key in left_map) / len(left_map)


def _passes_quality(value: dict[str, Any], gates: dict[str, Any]) -> bool:
    return (
        value["false_concrete_promotions"] == gates["false_concrete_promotions"]
        and value["false_adverse_none"] == gates["false_adverse_none"]
        and value["invalid_outputs"] == gates["invalid_outputs"]
        and value["accuracy"] >= gates["minimum_accuracy"]
        and value["emitted_precision"] >= gates["minimum_emitted_precision"]
        and value["concrete_recall"] >= gates["minimum_concrete_recall"]
    )


def select_architecture(run1: dict[str, Any], run2: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    gates = contract["development_selection_gates"]
    total = len(run1["llm_all"])
    summaries: dict[str, Any] = {}
    for name in ("llm_all", "residual"):
        q1 = metrics(run1[name])
        q2 = metrics(run2[name])
        stability = class_stability(run1[name], run2[name])
        summaries[name] = {
            "run_1": q1,
            "run_2": q2,
            "class_stability": stability,
            "passes_quality_both_runs": _passes_quality(q1, gates) and _passes_quality(q2, gates),
        }

    residual_calls = summaries["residual"]["run_1"]["llm_calls"]
    call_reduction = 1 - (residual_calls / total if total else 0.0)
    residual_quality = summaries["residual"]["passes_quality_both_runs"]
    residual_stable = summaries["residual"]["class_stability"] >= gates["minimum_class_stability"]
    residual_close_to_all = all(
        summaries["residual"][f"run_{idx}"]["accuracy"]
        >= summaries["llm_all"][f"run_{idx}"]["accuracy"] - gates["maximum_accuracy_drop_vs_llm_all"]
        for idx in (1, 2)
    )

    if (
        residual_quality
        and residual_stable
        and call_reduction >= gates["minimum_llm_call_reduction_vs_all"]
        and residual_close_to_all
    ):
        selected = "semantic_residual_router"
        reason = "Residual router meets frozen quality/safety/stability gates and materially reduces LLM calls."
    elif (
        summaries["llm_all"]["passes_quality_both_runs"]
        and summaries["llm_all"]["class_stability"] >= gates["minimum_class_stability"]
    ):
        selected = "llm_all"
        reason = "LLM-all meets gates but residual router does not meet the frozen development selection contract."
    else:
        selected = "not_ready_for_qa9"
        reason = "Neither candidate meets the frozen development selection contract; do not consume a fresh QA9 holdout."

    return {
        "selected": selected,
        "reason": reason,
        "llm_call_reduction_vs_all": call_reduction,
        "candidates": summaries,
    }


def _compact_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
    contract = load_json(CONTRACT_PATH)
    selection = select_architecture(run1, run2, contract)
    baseline = baseline_rows(cases)
    return {
        "benchmark": "PRV-103 semantic routing v2 development benchmark",
        "fresh_qa": False,
        "production_changed": False,
        "configuration": {
            "model": MODEL_ID,
            "prompt_version": PROMPT_VERSION,
            "reasoning_effort": REASONING_EFFORT,
            "taxonomy_version": load_json(TAXONOMY_PATH)["taxonomy_version"],
            "contract_version": contract["contract_version"],
            "cases": len(cases),
            "datasets": dict(Counter(case["dataset"] for case in cases)),
            "reference_overrides": contract["reference_overrides"],
        },
        "baseline_v07": {
            "metrics": metrics(baseline),
            "by_dataset": metrics_by_dataset(baseline),
        },
        "run_1": {
            "llm_all": metrics(run1["llm_all"]),
            "llm_all_by_dataset": metrics_by_dataset(run1["llm_all"]),
            "residual": metrics(run1["residual"]),
            "residual_by_dataset": metrics_by_dataset(run1["residual"]),
            "usage_all_calls": run1["usage_all_calls"],
            "llm_all_rows": _compact_rows(run1["llm_all"]),
            "residual_rows": _compact_rows(run1["residual"]),
        },
        "run_2": {
            "llm_all": metrics(run2["llm_all"]),
            "llm_all_by_dataset": metrics_by_dataset(run2["llm_all"]),
            "residual": metrics(run2["residual"]),
            "residual_by_dataset": metrics_by_dataset(run2["residual"]),
            "usage_all_calls": run2["usage_all_calls"],
            "llm_all_rows": _compact_rows(run2["llm_all"]),
            "residual_rows": _compact_rows(run2["residual"]),
        },
        "selection": selection,
    }


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    cases = load_development_cases()
    taxonomy = load_json(TAXONOMY_PATH)
    client = openai_client_v2(taxonomy)
    run1 = run_once(cases, client=client)
    run2 = run_once(cases, client=client)
    result = build_result(run1, run2, cases)
    _write(args.output, result)
    print(
        json.dumps(
            {
                "selection": result["selection"],
                "baseline_v07": result["baseline_v07"]["metrics"],
                "run_1_llm_all": result["run_1"]["llm_all"],
                "run_1_residual": result["run_1"]["residual"],
                "run_2_llm_all": result["run_2"]["llm_all"],
                "run_2_residual": result["run_2"]["residual"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
