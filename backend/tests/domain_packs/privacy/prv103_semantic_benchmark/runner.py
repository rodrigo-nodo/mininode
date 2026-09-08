from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

HERE = Path(__file__).resolve().parent
CORPUS_PATH = HERE / "corpus.json"
TAXONOMY_PATH = HERE / "intent_taxonomy.json"
MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

LABELS = ("concrete", "generic", "none", "unknown")
SCORE_GRID = tuple(round(0.20 + i * 0.025, 3) for i in range(27))
MARGIN_GRID = tuple(round(i * 0.025, 3) for i in range(11))


@dataclass(frozen=True)
class ScoredCase:
    case_id: str
    gold: str
    top_intent: str
    forced_class: str
    score: float
    margin: float
    baseline_v07: str | None = None


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def compose_text(case: dict) -> str:
    fields = []
    for key in ("heading", "legend", "introductory_text", "submit_text"):
        value = case.get(key)
        if value:
            fields.append(f"{key}: {' '.join(str(value).split())}")
    return "\n".join(fields) if fields else "(sin texto visible)"


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    return float(sum(a * b for a, b in zip(left, right)))


def _normalize(vector: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return [0.0 for _ in vector]
    return [float(v) / norm for v in vector]


def _mean(vectors: Sequence[Sequence[float]]) -> list[float]:
    if not vectors:
        raise ValueError("at least one vector is required")
    width = len(vectors[0])
    return _normalize([sum(v[i] for v in vectors) / len(vectors) for i in range(width)])


def load_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_ID)


def build_intent_vectors(model, taxonomy: dict) -> tuple[list[dict], dict[str, list[float]]]:
    intents = taxonomy["intents"]
    all_prototypes: list[str] = []
    slices: dict[str, tuple[int, int]] = {}
    start = 0
    for intent in intents:
        prototypes = intent["prototypes"]
        all_prototypes.extend(prototypes)
        slices[intent["id"]] = (start, start + len(prototypes))
        start += len(prototypes)
    encoded = model.encode(all_prototypes, normalize_embeddings=True, convert_to_numpy=True)
    vectors = {
        intent["id"]: _mean(encoded[a:b])
        for intent in intents
        for a, b in [slices[intent["id"]]]
    }
    return intents, vectors


def score_cases(model, cases: list[dict], taxonomy: dict) -> list[ScoredCase]:
    intents, intent_vectors = build_intent_vectors(model, taxonomy)
    intent_class = {item["id"]: item["class"] for item in intents}
    texts = [compose_text(case) for case in cases]
    encoded = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    scored: list[ScoredCase] = []
    for case, vector in zip(cases, encoded):
        candidates = sorted(
            ((_dot(vector, intent_vectors[item["id"]]), item["id"]) for item in intents),
            reverse=True,
        )
        top_score, top_intent = candidates[0]
        second_score = candidates[1][0]
        scored.append(
            ScoredCase(
                case_id=case["id"],
                gold=case["gold"],
                top_intent=top_intent,
                forced_class=intent_class[top_intent],
                score=float(top_score),
                margin=float(top_score - second_score),
                baseline_v07=case.get("baseline_v07"),
            )
        )
    return scored


def selective_prediction(case: ScoredCase, min_score: float, min_margin: float) -> str:
    if case.forced_class == "unknown":
        return "unknown"
    if case.score < min_score or case.margin < min_margin:
        return "unknown"
    return case.forced_class


def metrics(rows: Sequence[tuple[str, str]]) -> dict:
    total = len(rows)
    exact = sum(pred == gold for pred, gold in rows)
    emitted = [(pred, gold) for pred, gold in rows if pred != "unknown"]
    emitted_correct = sum(pred == gold for pred, gold in emitted)
    gold_concrete = sum(gold == "concrete" for _, gold in rows)
    pred_concrete = sum(pred == "concrete" for pred, _ in rows)
    true_concrete = sum(pred == gold == "concrete" for pred, gold in rows)
    false_concrete = sum(pred == "concrete" and gold != "concrete" for pred, gold in rows)
    false_none = sum(pred == "none" and gold != "none" for pred, gold in rows)
    pred_generic = sum(pred == "generic" for pred, _ in rows)
    true_generic = sum(pred == gold == "generic" for pred, gold in rows)
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
        "unknown_rate": sum(pred == "unknown" for pred, _ in rows) / total if total else 0.0,
        "predicted_distribution": dict(Counter(pred for pred, _ in rows)),
        "gold_distribution": dict(Counter(gold for _, gold in rows)),
    }


def choose_thresholds(dev_scored: Sequence[ScoredCase]) -> dict:
    candidates = []
    for score in SCORE_GRID:
        for margin in MARGIN_GRID:
            rows = [(selective_prediction(case, score, margin), case.gold) for case in dev_scored]
            m = metrics(rows)
            safe = m["false_concrete_promotions"] == 0 and m["false_adverse_none"] == 0
            precision_ok = m["emitted_precision"] >= 0.90
            candidates.append((safe, precision_ok, m, score, margin))
    valid = [c for c in candidates if c[0] and c[1]]
    if valid:
        chosen = max(valid, key=lambda x: (x[2]["coverage"], x[2]["accuracy"], x[2]["emitted_precision"], -x[3], -x[4]))
        mode = "safety_precision_then_coverage"
    else:
        chosen = max(
            candidates,
            key=lambda x: (
                -(x[2]["false_concrete_promotions"] + x[2]["false_adverse_none"]),
                x[2]["emitted_precision"],
                x[2]["coverage"],
                x[2]["accuracy"],
            ),
        )
        mode = "fallback_no_candidate_met_dev_constraints"
    _, _, m, score, margin = chosen
    return {"min_score": score, "min_margin": margin, "selection_mode": mode, "dev_metrics": m}


def evaluate(scored: Sequence[ScoredCase], min_score: float, min_margin: float) -> dict:
    forced_rows = [(case.forced_class, case.gold) for case in scored]
    selective_rows = [(selective_prediction(case, min_score, min_margin), case.gold) for case in scored]
    detail = []
    for case in scored:
        detail.append({
            "id": case.case_id,
            "gold": case.gold,
            "baseline_v07": case.baseline_v07,
            "top_intent": case.top_intent,
            "score": round(case.score, 6),
            "margin": round(case.margin, 6),
            "semantic_forced": case.forced_class,
            "semantic_selective": selective_prediction(case, min_score, min_margin),
        })
    return {"forced": metrics(forced_rows), "selective": metrics(selective_rows), "cases": detail}


def baseline_metrics(cases: Sequence[dict]) -> dict | None:
    rows = [(case["baseline_v07"], case["gold"]) for case in cases if case.get("baseline_v07") is not None]
    return metrics(rows) if rows else None


def experiment_decision(eval_metrics: dict) -> str:
    m = eval_metrics["selective"]
    if m["false_concrete_promotions"] > 0 or m["false_adverse_none"] > 0:
        return "D_RISKY"
    if (
        m["emitted_precision"] >= 0.90
        and m["coverage"] >= 0.50
        and m["accuracy"] >= 0.65
        and m["concrete_recall"] >= 0.50
    ):
        return "A_PROMISING"
    if m["emitted_precision"] >= 0.85 and m["coverage"] >= 0.40:
        return "B_EXPLORATORY"
    return "C_NO_MATERIAL_VALUE"


def run(model=None) -> dict:
    corpus = load_json(CORPUS_PATH)
    taxonomy = load_json(TAXONOMY_PATH)
    dev = [case for case in corpus["cases"] if case["split"] == "dev"]
    eval_cases = [case for case in corpus["cases"] if case["split"] == "eval"]
    model = model or load_model()
    dev_scored = score_cases(model, dev, taxonomy)
    thresholds = choose_thresholds(dev_scored)
    eval_scored = score_cases(model, eval_cases, taxonomy)
    evaluation = evaluate(eval_scored, thresholds["min_score"], thresholds["min_margin"])
    revision = None
    try:
        revision = model._first_module().auto_model.config._commit_hash
    except Exception:
        pass
    return {
        "experiment": "PRV-103 Semantic V1",
        "corpus_version": corpus["corpus_version"],
        "model_id": MODEL_ID,
        "model_revision": revision,
        "taxonomy_version": taxonomy["taxonomy_version"],
        "dev_cases": len(dev),
        "eval_cases": len(eval_cases),
        "thresholds": thresholds,
        "baseline_v07_eval": baseline_metrics(eval_cases),
        "semantic_eval": evaluation,
        "decision": experiment_decision(evaluation),
        "production_changed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run()
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
