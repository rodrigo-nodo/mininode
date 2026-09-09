"""PRV-103 Intent LLM V2 research runner. Never imported by production."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

HERE = Path(__file__).resolve().parent
CORPUS_PATH = HERE / "corpus.json"
TAXONOMY_PATH = HERE / "intent_taxonomy.json"
MODEL_ID = "gpt-5.6-sol"
PROMPT_VERSION = "prv103-intent-v2-01"
REASONING_EFFORT = "medium"
ALLOWED_FIELDS = ("heading", "legend", "introductory_text", "submit_text")
LABELS = ("concrete", "generic", "none", "unknown")


@dataclass(frozen=True)
class EvidenceItem:
    field: str
    quote: str


@dataclass(frozen=True)
class IntentOutput:
    intent_id: str
    evidence: tuple[EvidenceItem, ...]
    reason_short: str
    uncertain: bool


@dataclass(frozen=True)
class Inference:
    output: IntentOutput | None
    valid: bool
    error: str | None
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    latency_seconds: float
    resolved_model: str | None


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    source_cycle: str
    split: str
    gold: str
    baseline_v07: str | None
    intent_id: str
    final_class: str
    evidence: tuple[EvidenceItem, ...]
    reason_short: str
    uncertain: bool
    valid_output: bool
    validation_error: str | None
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    latency_seconds: float
    resolved_model: str | None


Client = Callable[[dict[str, Any], dict[str, Any]], Inference]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_text(value: str) -> str:
    return " ".join(value.split())


def intent_map(taxonomy: dict[str, Any]) -> dict[str, str]:
    return {item["id"]: item["class"] for item in taxonomy["intents"]}


def catalog_for_model(taxonomy: dict[str, Any]) -> list[dict[str, Any]]:
    # Deliberately omit product classes. The LLM identifies intent only.
    return [
        {"intent_id": item["id"], "examples": item["prototypes"]}
        for item in taxonomy["intents"]
    ]


def output_schema(taxonomy: dict[str, Any]) -> dict[str, Any]:
    ids = [item["id"] for item in taxonomy["intents"]]
    return {
        "type": "object",
        "properties": {
            "intent_id": {"type": "string", "enum": ids},
            "evidence": {
                "type": "array",
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string", "enum": list(ALLOWED_FIELDS)},
                        "quote": {"type": "string", "minLength": 1, "maxLength": 200},
                    },
                    "required": ["field", "quote"],
                    "additionalProperties": False,
                },
            },
            "reason_short": {"type": "string", "minLength": 1, "maxLength": 240},
            "uncertain": {"type": "boolean"},
        },
        "required": ["intent_id", "evidence", "reason_short", "uncertain"],
        "additionalProperties": False,
    }


def validate_output(raw: Any, case: dict[str, Any], taxonomy: dict[str, Any]) -> IntentOutput:
    required = {"intent_id", "evidence", "reason_short", "uncertain"}
    if not isinstance(raw, dict) or set(raw) != required:
        raise ValueError("output fields do not match the frozen contract")

    mapping = intent_map(taxonomy)
    intent_id = raw["intent_id"]
    if intent_id not in mapping:
        raise ValueError("intent_id is not present in the frozen taxonomy")

    if not isinstance(raw["uncertain"], bool):
        raise ValueError("uncertain must be boolean")

    reason = raw["reason_short"]
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 240:
        raise ValueError("reason_short must be a non-empty short string")

    evidence_raw = raw["evidence"]
    if not isinstance(evidence_raw, list) or len(evidence_raw) > 4:
        raise ValueError("evidence must be an array with at most four items")

    evidence: list[EvidenceItem] = []
    seen_fields: set[str] = set()
    for item in evidence_raw:
        if not isinstance(item, dict) or set(item) != {"field", "quote"}:
            raise ValueError("evidence item fields do not match the frozen contract")
        field = item["field"]
        quote = item["quote"]
        if field not in ALLOWED_FIELDS:
            raise ValueError("evidence field is outside the allowed form evidence")
        if field in seen_fields:
            raise ValueError("evidence field is duplicated")
        if not isinstance(quote, str) or not quote.strip() or len(quote) > 200:
            raise ValueError("evidence quote must be a short non-empty string")
        source = case.get(field)
        if not isinstance(source, str) or not source.strip():
            raise ValueError("evidence references an empty field")
        normalized_quote = normalize_text(quote)
        normalized_source = normalize_text(source)
        if normalized_quote not in normalized_source:
            raise ValueError("evidence quote is not present in the cited input field")
        seen_fields.add(field)
        evidence.append(EvidenceItem(field, normalized_quote))

    # Canonical order makes evidence stability independent of array ordering.
    evidence.sort(key=lambda item: (ALLOWED_FIELDS.index(item.field), item.quote))
    return IntentOutput(intent_id, tuple(evidence), reason.strip(), raw["uncertain"])


def final_class_for(output: IntentOutput, taxonomy: dict[str, Any]) -> str:
    if output.uncertain:
        return "unknown"
    return intent_map(taxonomy)[output.intent_id]


def metrics(results: Sequence[CaseResult]) -> dict[str, Any]:
    total = len(results)
    exact = sum(row.final_class == row.gold for row in results)
    emitted = [row for row in results if row.final_class != "unknown"]
    emitted_correct = sum(row.final_class == row.gold for row in emitted)
    gold_concrete = sum(row.gold == "concrete" for row in results)
    pred_concrete = sum(row.final_class == "concrete" for row in results)
    true_concrete = sum(row.final_class == row.gold == "concrete" for row in results)
    pred_generic = sum(row.final_class == "generic" for row in results)
    true_generic = sum(row.final_class == row.gold == "generic" for row in results)
    false_concrete = sum(row.final_class == "concrete" and row.gold != "concrete" for row in results)
    false_none = sum(row.final_class == "none" and row.gold != "none" for row in results)
    return {
        "total": total,
        "exact": exact,
        "accuracy": exact / total if total else 0.0,
        "coverage": len(emitted) / total if total else 0.0,
        "emitted_precision": emitted_correct / len(emitted) if emitted else 1.0,
        "concrete_precision": true_concrete / pred_concrete if pred_concrete else 1.0,
        "concrete_recall": true_concrete / gold_concrete if gold_concrete else 1.0,
        "generic_precision": true_generic / pred_generic if pred_generic else 1.0,
        "false_concrete_promotions": false_concrete,
        "false_adverse_none": false_none,
        "unknown_rate": sum(row.final_class == "unknown" for row in results) / total if total else 0.0,
        "invalid_outputs": sum(not row.valid_output for row in results),
        "predicted_distribution": dict(Counter(row.final_class for row in results)),
        "gold_distribution": dict(Counter(row.gold for row in results)),
    }


def baseline_v07_metrics(corpus_cases: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
    rows = [case for case in corpus_cases if case.get("baseline_v07") is not None]
    if not rows:
        return None
    synthetic = [
        CaseResult(
            case_id=case["id"], source_cycle=case["source_cycle"], split=case["split"],
            gold=case["gold"], baseline_v07=case["baseline_v07"], intent_id="baseline",
            final_class=case["baseline_v07"], evidence=(), reason_short="baseline",
            uncertain=False, valid_output=True, validation_error=None,
            input_tokens=0, output_tokens=0, reasoning_tokens=0, latency_seconds=0.0,
            resolved_model=None,
        )
        for case in rows
    ]
    return metrics(synthetic)


def stability(run1: Sequence[CaseResult], run2: Sequence[CaseResult]) -> dict[str, Any]:
    right = {row.case_id: row for row in run2}
    if set(right) != {row.case_id for row in run1}:
        raise ValueError("run case IDs differ")
    total = len(run1)
    class_matches = 0
    intent_matches = 0
    uncertain_matches = 0
    evidence_matches = 0
    differences: list[dict[str, Any]] = []
    for left in run1:
        other = right[left.case_id]
        same_class = left.final_class == other.final_class
        same_intent = left.intent_id == other.intent_id
        same_uncertain = left.uncertain == other.uncertain
        same_evidence = left.evidence == other.evidence
        class_matches += same_class
        intent_matches += same_intent
        uncertain_matches += same_uncertain
        evidence_matches += same_evidence
        if not (same_class and same_intent and same_uncertain and same_evidence):
            differences.append({
                "id": left.case_id,
                "class": [left.final_class, other.final_class],
                "intent": [left.intent_id, other.intent_id],
                "uncertain": [left.uncertain, other.uncertain],
                "evidence_equal": same_evidence,
            })
    return {
        "total": total,
        "class_stability": class_matches / total if total else 1.0,
        "intent_stability": intent_matches / total if total else 1.0,
        "uncertain_stability": uncertain_matches / total if total else 1.0,
        "evidence_stability": evidence_matches / total if total else 1.0,
        "differences": differences,
    }


def decision(quality: dict[str, Any], stable: dict[str, Any]) -> str:
    if (
        quality["false_concrete_promotions"] > 0
        or quality["false_adverse_none"] > 0
        or quality["invalid_outputs"] > 0
    ):
        return "D_RISKY"
    if (
        quality["emitted_precision"] >= 0.90
        and quality["coverage"] >= 0.70
        and quality["accuracy"] >= 0.75
        and quality["concrete_recall"] >= 0.70
        and stable["class_stability"] >= 0.95
    ):
        return "A_PROMISING"
    if (
        quality["emitted_precision"] >= 0.85
        and quality["coverage"] >= 0.50
        and quality["accuracy"] >= 0.65
        and stable["class_stability"] >= 0.90
    ):
        return "B_EXPLORATORY"
    return "C_NO_MATERIAL_VALUE"


def instructions(taxonomy: dict[str, Any]) -> str:
    catalog = json.dumps(catalog_for_model(taxonomy), ensure_ascii=False, separators=(",", ":"))
    return (
        "Clasifica únicamente la intención observable del formulario recibido. "
        "No decidas clases de producto ni cumplimiento. Usa solo heading, legend, "
        "introductory_text y submit_text; no uses conocimiento externo ni infieras "
        "desde campos que no están presentes. Elige exactamente un intent_id del "
        "catálogo. Contacto, registro o suscripción genéricos siguen siendo genéricos "
        "si no existe un resultado explícito. Acciones aisladas como Buscar, Next, "
        "Start now o equivalentes sin objeto reconocible son ambiguas. Un placeholder "
        "de plantilla sin significado humano es technical_placeholder. Si la evidencia "
        "no soporta claramente una intención o hay conflicto, uncertain=true. "
        "evidence debe citar literalmente substrings de los campos recibidos y solo "
        "los campos necesarios. reason_short debe ser una frase breve basada en la "
        "evidencia visible, sin razonamiento interno. Catálogo cerrado de intenciones: "
        + catalog
    )


def openai_client(taxonomy: dict[str, Any]) -> Client:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit("Install experiment-only dependency 'openai'.") from exc

    sdk = OpenAI()
    schema = output_schema(taxonomy)
    frozen_instructions = instructions(taxonomy)

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
                    "name": "prv103_intent_adjudication",
                    "strict": True,
                    "schema": schema,
                }
            },
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


def run(client: Client | None = None) -> dict[str, Any]:
    corpus = load_json(CORPUS_PATH)
    taxonomy = load_json(TAXONOMY_PATH)
    classify = client or openai_client(taxonomy)
    results: list[CaseResult] = []
    for case in corpus["cases"]:
        inference = classify(case, taxonomy)
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
        results.append(
            CaseResult(
                case_id=case["id"],
                source_cycle=case["source_cycle"],
                split=case["split"],
                gold=case["gold"],
                baseline_v07=case.get("baseline_v07"),
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
        "experiment": "PRV-103 Intent LLM V2",
        "prompt_version": PROMPT_VERSION,
        "model_id": MODEL_ID,
        "reasoning_effort": REASONING_EFFORT,
        "corpus_version": corpus["corpus_version"],
        "taxonomy_version": taxonomy["taxonomy_version"],
        "results": [
            {
                **asdict(row),
                "evidence": [asdict(item) for item in row.evidence],
            }
            for row in results
        ],
        "quality": metrics(results),
        "usage": {
            "calls": len(results),
            "input_tokens": sum(row.input_tokens for row in results),
            "output_tokens": sum(row.output_tokens for row in results),
            "reasoning_tokens": sum(row.reasoning_tokens for row in results),
            "total_latency_seconds": sum(row.latency_seconds for row in results),
            "average_latency_seconds": (
                sum(row.latency_seconds for row in results) / len(results) if results else 0.0
            ),
            "resolved_models": sorted({row.resolved_model for row in results if row.resolved_model}),
        },
        "production_changed": False,
    }


def result_from_dict(raw: dict[str, Any]) -> CaseResult:
    evidence = tuple(EvidenceItem(**item) for item in raw["evidence"])
    return CaseResult(**{**raw, "evidence": evidence})


def build_summary(run1: dict[str, Any], run2: dict[str, Any]) -> dict[str, Any]:
    corpus = load_json(CORPUS_PATH)
    rows1 = [result_from_dict(item) for item in run1["results"]]
    rows2 = [result_from_dict(item) for item in run2["results"]]
    stable = stability(rows1, rows2)
    all_quality = metrics(rows1)
    qa4 = metrics([row for row in rows1 if row.source_cycle == "QA4"])
    qa5 = metrics([row for row in rows1 if row.source_cycle == "QA5"])
    return {
        "experiment": "PRV-103 Intent LLM V2",
        "quality_run": 1,
        "stability_run": 2,
        "configuration": {
            "model_id": MODEL_ID,
            "prompt_version": PROMPT_VERSION,
            "reasoning_effort": REASONING_EFFORT,
            "corpus_version": run1["corpus_version"],
            "taxonomy_version": run1["taxonomy_version"],
        },
        "quality_all_69": all_quality,
        "quality_qa4": qa4,
        "quality_qa5": qa5,
        "baseline_v07_qa5": baseline_v07_metrics(corpus["cases"]),
        "stability": stable,
        "usage": {"run_1": run1["usage"], "run_2": run2["usage"]},
        "decision": decision(all_quality, stable),
        "production_changed": False,
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run", "summary"))
    parser.add_argument("--run", type=int, choices=(1, 2))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/prv103-intent-llm-v2"))
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.command == "run":
        if not args.run:
            parser.error("run requires --run 1 or 2")
        payload = run()
        payload["run_number"] = args.run
        write_json(args.output_dir / f"run-{args.run}.json", payload)
        print(json.dumps({"run": args.run, "quality": payload["quality"], "usage": payload["usage"]}, indent=2))
        return

    run1 = load_json(args.output_dir / "run-1.json")
    run2 = load_json(args.output_dir / "run-2.json")
    summary = build_summary(run1, run2)
    write_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
