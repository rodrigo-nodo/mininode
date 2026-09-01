"""Offline W2.S.3 semantic adjudication experiment (never used by production)."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from .runner import CaseResult, calculate_metrics, run_benchmark
from .schema import BenchmarkCase, Fixture, VALID_CLASSES, load_corpus

MODEL_ID = "gpt-5.6-sol"
LLM_PROMPT_VERSION = "w2s3-01"
REASONING_EFFORT = "medium"
# Experimental estimate only. Snapshot recorded before inference; update only in a future phase.
PRICE_REFERENCE_DATE = "2026-08-31"
INPUT_USD_PER_MILLION = 1.25
OUTPUT_USD_PER_MILLION = 10.00

ROUTE_TO_LLM = {
    "PRV-008": frozenset({"generic", "none"}),
    "PRV-010": frozenset({"generic", "none"}),
    "PRV-012": frozenset({"generic", "none"}),
}

CONTROL_PROMPTS = {
    "PRV-008": "Clasifica finalidades de tratamiento de datos personales: concrete si hay una finalidad específica, generic si solo se afirma una finalidad o prestación sin propósito concreto, none si no existe. No confundas seguridad, descripción del sitio, cookies o términos con una finalidad de tratamiento.",
    "PRV-010": "Clasifica comunicación de datos personales: explicit si se comunica a una categoría identificable, generic si se comparte con terceros sin categoría, explicit_none solo si se declara que no se comparten datos, none si no hay evidencia. No equipares no vender con no compartir ni infieras comunicación de enlaces, cookies o nombres externos.",
    "PRV-012": "Clasifica conservación de datos personales: explicit si hay plazo, evento o criterio concreto, generic si se afirma conservación sin criterio suficiente, none si no existe regla general. No uses por sí sola duración de cookies, navegador, logs técnicos o estadísticas.",
}


@dataclass(frozen=True)
class LlmOutput:
    predicted_class: str
    evidence_fixture_ids: tuple[str, ...]
    reason_short: str
    uncertain: bool


@dataclass(frozen=True)
class Inference:
    output: LlmOutput
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    latency_seconds: float


@dataclass(frozen=True)
class ExperimentalCaseResult:
    policy_id: str
    control: str
    expected_class: str
    rules_class: str
    llm_class: str
    hybrid_class: str
    llm_evidence_fixture_ids: tuple[str, ...]
    llm_evidence_texts: tuple[str, ...]
    reason_short: str
    uncertain: bool
    model_id: str
    prompt_version: str
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    latency_seconds: float
    match_rules: bool
    match_llm: bool
    match_hybrid: bool
    routed: bool


Client = Callable[[str, Sequence[dict[str, str]], dict[str, Any]], Inference]


def output_schema(control: str) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "predicted_class": {"type": "string", "enum": sorted(VALID_CLASSES[control] - {"not_applicable"})},
            "evidence_fixture_ids": {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
            "reason_short": {"type": "string", "minLength": 1, "maxLength": 240},
            "uncertain": {"type": "boolean"},
        },
        "required": ["predicted_class", "evidence_fixture_ids", "reason_short", "uncertain"],
        "additionalProperties": False,
    }


def validate_output(control: str, raw: Any, document: Sequence[Fixture]) -> LlmOutput:
    if not isinstance(raw, dict) or set(raw) != {"predicted_class", "evidence_fixture_ids", "reason_short", "uncertain"}:
        raise ValueError("invalid_output: output fields do not match schema")
    if raw["predicted_class"] not in VALID_CLASSES[control] - {"not_applicable"}:
        raise ValueError("invalid_output: class is not valid for control")
    ids = raw["evidence_fixture_ids"]
    if not isinstance(ids, (list, tuple)) or any(not isinstance(item, str) for item in ids) or len(ids) != len(set(ids)):
        raise ValueError("invalid_output: evidence_fixture_ids must be unique strings")
    known = {item.fixture_id for item in document}
    if not set(ids) <= known:
        raise ValueError("invalid_output: evidence fixture ID is not in input document")
    reason = raw["reason_short"]
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 240 or reason.count(".") > 1:
        raise ValueError("invalid_output: reason_short must be one short sentence")
    if not isinstance(raw["uncertain"], bool):
        raise ValueError("invalid_output: uncertain must be boolean")
    return LlmOutput(raw["predicted_class"], tuple(ids), reason.strip(), raw["uncertain"])


def should_route(control: str, rules_class: str) -> bool:
    return rules_class != "not_applicable" and rules_class in ROUTE_TO_LLM[control]


def compose_hybrid(control: str, rules_class: str, llm_class: str) -> str:
    return llm_class if should_route(control, rules_class) else rules_class


def run_case(case: BenchmarkCase, document: Sequence[Fixture], rules_class: str, client: Client) -> ExperimentalCaseResult:
    if case.prv003 == "not_detected":
        inference = Inference(LlmOutput("not_applicable", (), "PRV-003 gate: policy not detected.", False), 0, 0, 0, 0.0)
    else:
        payload = [{"fixture_id": item.fixture_id, "text": item.text} for item in document]
        try:
            inference = client(case.control, payload, output_schema(case.control))
            # Validate again at the trust boundary, including fixture provenance.
            validated = validate_output(case.control, asdict(inference.output), document)
            inference = Inference(validated, inference.input_tokens, inference.output_tokens, inference.reasoning_tokens, inference.latency_seconds)
        except (ValueError, json.JSONDecodeError) as exc:
            inference = Inference(
                LlmOutput("invalid_output", (), str(exc), True), 0, 0, 0, 0.0
            )
    llm_class = inference.output.predicted_class
    hybrid = compose_hybrid(case.control, rules_class, llm_class)
    texts = {item.fixture_id: item.text for item in document}
    return ExperimentalCaseResult(
        case.policy_id, case.control, case.expected_class, rules_class, llm_class, hybrid,
        inference.output.evidence_fixture_ids, tuple(texts[item] for item in inference.output.evidence_fixture_ids),
        inference.output.reason_short, inference.output.uncertain, MODEL_ID, LLM_PROMPT_VERSION,
        inference.input_tokens, inference.output_tokens, inference.reasoning_tokens, inference.latency_seconds,
        rules_class == case.expected_class, llm_class == case.expected_class, hybrid == case.expected_class,
        should_route(case.control, rules_class),
    )


def openai_client() -> Client:
    """Import the experiment-only SDK lazily; unit tests never require it."""
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit("Install experiment-only dependency 'openai'; backend requirements remain unchanged.") from exc
    sdk = OpenAI()

    def classify(control: str, document: Sequence[dict[str, str]], schema: dict[str, Any]) -> Inference:
        started = time.perf_counter()
        response = sdk.responses.create(
            model=MODEL_ID,
            reasoning={"effort": REASONING_EFFORT},
            instructions=("Evalúa únicamente el documento recibido. Devuelve una clase semántica y evidencia observable del input; no expongas razonamiento interno. " + CONTROL_PROMPTS[control]),
            input=json.dumps(document, ensure_ascii=False),
            text={"format": {"type": "json_schema", "name": "semantic_adjudication", "strict": True, "schema": schema}},
        )
        elapsed = time.perf_counter() - started
        parsed = validate_output(control, json.loads(response.output_text), tuple(Fixture(item["fixture_id"], item["text"], "negative", "runtime input") for item in document))
        usage = response.usage
        details = getattr(usage, "output_tokens_details", None)
        reasoning = int(getattr(details, "reasoning_tokens", 0) or 0)
        return Inference(parsed, int(usage.input_tokens), int(usage.output_tokens), reasoning, elapsed)
    return classify


def metrics_for(rows: Iterable[ExperimentalCaseResult], field: str) -> dict[str, Any]:
    selected = list(rows)
    metrics = calculate_metrics(CaseResult(row.policy_id, row.control, row.expected_class, getattr(row, field), getattr(row, field) == row.expected_class) for row in selected)
    calls = sum(row.llm_class != "not_applicable" for row in selected)
    routed = sum(row.routed for row in selected)
    latency = sum(row.latency_seconds for row in selected)
    metrics.update({"llm_calls": calls, "routed_cases": routed, "routing_percentage": routed / len(selected) if selected else 0.0,
                    "input_tokens": sum(row.input_tokens for row in selected), "output_tokens": sum(row.output_tokens for row in selected),
                    "reasoning_tokens": sum(row.reasoning_tokens for row in selected), "total_latency_seconds": latency,
                    "average_latency_per_call": latency / calls if calls else 0.0})
    return metrics


def cost_summary(rows: Iterable[ExperimentalCaseResult]) -> dict[str, Any]:
    items = list(rows); input_tokens = sum(x.input_tokens for x in items); output_tokens = sum(x.output_tokens for x in items)
    return {"price_reference_date": PRICE_REFERENCE_DATE, "input_usd_per_million_tokens": INPUT_USD_PER_MILLION,
            "output_usd_per_million_tokens": OUTPUT_USD_PER_MILLION, "estimated_usd": input_tokens / 1_000_000 * INPUT_USD_PER_MILLION + output_tokens / 1_000_000 * OUTPUT_USD_PER_MILLION,
            "notice": "Experimental estimate separate from quality metrics; prices may change."}


def compare_stability(run1: Sequence[ExperimentalCaseResult], run2: Sequence[ExperimentalCaseResult]) -> dict[str, Any]:
    second = {(x.policy_id, x.control): x for x in run2}; class_diff = []; evidence_diff = []; uncertain_diff = []
    for left in run1:
        right = second[(left.policy_id, left.control)]
        key = {"policy_id": left.policy_id, "control": left.control}
        if left.llm_class != right.llm_class: class_diff.append({**key, "run_1": left.llm_class, "run_2": right.llm_class})
        if left.llm_evidence_fixture_ids != right.llm_evidence_fixture_ids: evidence_diff.append({**key, "run_1": left.llm_evidence_fixture_ids, "run_2": right.llm_evidence_fixture_ids})
        if left.uncertain != right.uncertain: uncertain_diff.append({**key, "run_1": left.uncertain, "run_2": right.uncertain})
    return {"total_cases": len(run1), "stable_classes": len(run1) - len(class_diff), "class_differences": class_diff, "evidence_differences": evidence_diff, "uncertain_differences": uncertain_diff}


def execute(client: Client) -> list[ExperimentalCaseResult]:
    corpus = load_corpus(); baseline = {(x.policy_id, x.control): x.actual_class for x in run_benchmark()}
    return [run_case(case, corpus.documents[case.policy_id], baseline[(case.policy_id, case.control)], client) for case in corpus.cases]


def _write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("command", choices=("baseline", "llm", "hybrid", "stability", "summary")); parser.add_argument("--output-dir", type=Path, default=Path("artifacts")); parser.add_argument("--run", type=int, choices=(1, 2)); args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.command == "baseline":
        rows = run_benchmark(); _write(args.output_dir / "baseline.json", {"results": [asdict(x) for x in rows], "metrics": calculate_metrics(rows)}); return
    if args.command == "llm":
        if not args.run: parser.error("llm requires --run 1 or 2")
        rows = execute(openai_client()); _write(args.output_dir / f"llm-run-{args.run}.json", {"configuration": {"model": MODEL_ID, "prompt_version": LLM_PROMPT_VERSION, "reasoning_effort": REASONING_EFFORT}, "results": [asdict(x) for x in rows], "metrics": metrics_for(rows, "llm_class"), "cost": cost_summary(rows)}); return
    def load_run(number: int) -> list[ExperimentalCaseResult]:
        return [ExperimentalCaseResult(**{**x, "llm_evidence_fixture_ids": tuple(x["llm_evidence_fixture_ids"]), "llm_evidence_texts": tuple(x["llm_evidence_texts"])}) for x in json.loads((args.output_dir / f"llm-run-{number}.json").read_text())["results"]]
    run1 = load_run(1)
    if args.command == "hybrid": _write(args.output_dir / "hybrid-run-1.json", {"results": [asdict(x) for x in run1], "metrics": metrics_for(run1, "hybrid_class")}); return
    if args.command == "stability": _write(args.output_dir / "stability-report.json", compare_stability(run1, load_run(2))); return
    _write(args.output_dir / "experiment-summary.json", {"quality_run": 1, "rules": metrics_for(run1, "rules_class"), "llm_only": metrics_for(run1, "llm_class"), "hybrid_selective": metrics_for(run1, "hybrid_class"), "cost": cost_summary(run1), "stability": compare_stability(run1, load_run(2))})


if __name__ == "__main__": main()
