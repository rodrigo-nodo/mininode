"""Run the frozen semantic benchmark with direct, experimental NLI inference."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from typing import Callable, Iterable, Sequence

from .runner import CaseResult, calculate_metrics, run_benchmark
from .schema import BenchmarkCase, Fixture, load_corpus


MODEL_ID = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
# Experimental calibration knobs. They are deliberately visible and are not used by
# production. A class must clear both an absolute entailment floor and its runner-up.
ENTAILMENT_THRESHOLD = 0.65
CLASS_MARGIN = 0.10

# More than one statement is intentional: specificity, negation, and object scope are
# represented explicitly rather than asking one ambiguous question per control.
HYPOTHESES = {
    "PRV-008": {
        "concrete": (
            "El texto afirma que se usan datos personales para gestionar pedidos, prestar soporte o proporcionar un servicio concreto.",
            "El texto afirma que se usan datos personales para mejorar o personalizar productos o servicios.",
        ),
        "generic": (
            "El texto afirma que se tratan datos personales con fines relacionados con los servicios, sin nombrar un objetivo concreto.",
        ),
    },
    "PRV-010": {
        "explicit_none": (
            "El texto afirma que la organización no comparte datos personales con ningún tercero.",
        ),
        "explicit": (
            "El texto afirma que la organización comunica datos personales a una categoría concreta de destinatarios o proveedores.",
        ),
        "generic": (
            "El texto afirma que la organización puede compartir datos personales con terceros, sin identificar una categoría concreta de destinatario.",
        ),
    },
    "PRV-012": {
        "explicit": (
            "El texto establece un plazo, evento o criterio concreto durante el que la organización conserva datos personales.",
        ),
        "generic": (
            "El texto afirma que la organización conserva datos personales, pero no establece un plazo, evento o criterio concreto.",
        ),
    },
}

ScoreFunction = Callable[[Sequence[tuple[str, str]]], Sequence[dict[str, float]]]


@dataclass(frozen=True)
class Candidate:
    semantic_class: str
    fixture: Fixture
    entailment: float
    neutral: float
    contradiction: float


@dataclass(frozen=True)
class NliCaseResult:
    policy_id: str
    control: str
    predicted_class: str
    expected_class: str
    match: bool
    evidence_fixture_id: str | None
    evidence_text: str | None
    score: dict[str, float]
    model_id: str


def hypotheses_for(control: str) -> tuple[tuple[str, str], ...]:
    """Return the ordered semantic classes and hypotheses for one control."""
    return tuple(
        (semantic_class, hypothesis)
        for semantic_class, hypotheses in HYPOTHESES[control].items()
        for hypothesis in hypotheses
    )


def combine_scores(
    control: str,
    document: Sequence[Fixture],
    scores: Sequence[dict[str, float]],
) -> list[Candidate]:
    """Keep the strongest fragment/hypothesis entailment for each class."""
    hypotheses = hypotheses_for(control)
    expected_count = len(document) * len(hypotheses)
    if len(scores) != expected_count:
        raise ValueError(f"expected {expected_count} NLI scores, received {len(scores)}")
    best: dict[str, Candidate] = {}
    offset = 0
    for fixture in document:
        for semantic_class, _ in hypotheses:
            score = scores[offset]
            offset += 1
            candidate = Candidate(
                semantic_class, fixture, score["entailment"],
                score["neutral"], score["contradiction"],
            )
            if (
                semantic_class not in best
                or candidate.entailment > best[semantic_class].entailment
            ):
                best[semantic_class] = candidate
    return sorted(best.values(), key=lambda item: item.entailment, reverse=True)


def choose_class(candidates: Sequence[Candidate]) -> Candidate | None:
    """Accept the best class only when confidence and separation are sufficient."""
    if not candidates or candidates[0].entailment < ENTAILMENT_THRESHOLD:
        return None
    runner_up = candidates[1].entailment if len(candidates) > 1 else 0.0
    if candidates[0].entailment - runner_up < CLASS_MARGIN:
        return None
    return candidates[0]


def run_case(
    case: BenchmarkCase, document: Sequence[Fixture], scorer: ScoreFunction
) -> tuple[NliCaseResult, int]:
    """Apply the PRV-003 gate, then score every fragment against every hypothesis."""
    if case.prv003 == "not_detected":
        return NliCaseResult(
            case.policy_id, case.control, "not_applicable", case.expected_class,
            case.expected_class == "not_applicable", None, None, {}, MODEL_ID,
        ), 0
    hypotheses = hypotheses_for(case.control)
    pairs = [(fixture.text, hypothesis) for fixture in document for _, hypothesis in hypotheses]
    candidates = combine_scores(case.control, document, scorer(pairs))
    accepted = choose_class(candidates)
    predicted = accepted.semantic_class if accepted else "none"
    return NliCaseResult(
        case.policy_id, case.control, predicted, case.expected_class,
        predicted == case.expected_class,
        accepted.fixture.fixture_id if accepted else None,
        accepted.fixture.text if accepted else None,
        ({
            "entailment": accepted.entailment,
            "neutral": accepted.neutral,
            "contradiction": accepted.contradiction,
        } if accepted else ({
            "entailment": candidates[0].entailment,
            "neutral": candidates[0].neutral,
            "contradiction": candidates[0].contradiction,
        } if candidates else {})),
        MODEL_ID,
    ), len(pairs)


def metrics_for(results: Iterable[NliCaseResult]) -> dict:
    """Reuse the frozen baseline metric definitions for semantic predictions."""
    return calculate_metrics(
        CaseResult(row.policy_id, row.control, row.expected_class,
                   row.predicted_class, row.match)
        for row in results
    )


def run_experiment(scorer: ScoreFunction) -> tuple[list[NliCaseResult], dict]:
    corpus = load_corpus()
    started = time.perf_counter()
    results: list[NliCaseResult] = []
    total_inferences = 0
    for case in corpus.cases:
        result, count = run_case(case, corpus.documents[case.policy_id], scorer)
        results.append(result)
        total_inferences += count
    elapsed = time.perf_counter() - started
    metrics = metrics_for(results)
    metrics.update({
        "elapsed_seconds": elapsed,
        "average_seconds_per_case": elapsed / len(results) if results else 0.0,
        "total_inferences": total_inferences,
    })
    return results, metrics


def transformers_scorer() -> ScoreFunction:
    """Load the optional experiment-only Transformers pipeline on CPU."""
    try:
        from transformers import pipeline
    except ImportError as exc:
        raise SystemExit(
            "Direct NLI requires experiment-only 'torch' and 'transformers'. "
            "Install them in a temporary environment; product requirements are unchanged."
        ) from exc
    classifier = pipeline(
        "text-classification", model=MODEL_ID, tokenizer=MODEL_ID,
        device=-1, top_k=None,
    )

    def score(pairs: Sequence[tuple[str, str]]) -> Sequence[dict[str, float]]:
        raw = classifier(
            [{"text": premise, "text_pair": hypothesis} for premise, hypothesis in pairs],
            batch_size=8, truncation=True,
        )
        normalized = []
        for row in raw:
            labels = {item["label"].lower(): float(item["score"]) for item in row}
            normalized.append({name: labels[name] for name in ("entailment", "neutral", "contradiction")})
        return normalized

    return score


def _comparison(baseline: dict, direct: dict) -> str:
    rows = [
        ("accuracy", baseline["accuracy"], direct["accuracy"]),
        ("false_positive_promotions", baseline["false_positive_promotions"], direct["false_positive_promotions"]),
        ("false_negative_omissions", baseline["false_negative_omissions"], direct["false_negative_omissions"]),
        ("semantic_polarity_errors", baseline["semantic_polarity_errors"], direct["semantic_polarity_errors"]),
    ]
    rows.extend(
        (f"{control} accuracy", baseline["per_control"][control]["accuracy"], direct["per_control"][control]["accuracy"])
        for control in HYPOTHESES
    )
    lines = ["BASELINE RULES vs DIRECT NLI", f"{'metric':<30} {'baseline':>10} {'direct_nli':>12}", "-" * 54]
    lines.extend(f"{name:<30} {left:>10.3f} {right:>12.3f}" for name, left, right in rows)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    results, metrics = run_experiment(transformers_scorer())
    baseline = calculate_metrics(run_benchmark())
    payload = {"model_id": MODEL_ID, "thresholds": {
        "entailment": ENTAILMENT_THRESHOLD, "class_margin": CLASS_MARGIN,
    }, "results": [asdict(row) for row in results], "metrics": metrics,
        "baseline_metrics": baseline}
    if args.format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(_comparison(baseline, metrics))
        print(f"\nelapsed_seconds: {metrics['elapsed_seconds']:.3f}")
        print(f"average_seconds_per_case: {metrics['average_seconds_per_case']:.3f}")
        print(f"total_inferences: {metrics['total_inferences']}")
        mismatches = [row for row in results if not row.match][:5]
        print("\nfirst mismatches:")
        for row in mismatches:
            print(f"  {row.policy_id} {row.control}: {row.expected_class} -> {row.predicted_class} ({row.evidence_fixture_id or 'no accepted evidence'})")


if __name__ == "__main__":
    main()
