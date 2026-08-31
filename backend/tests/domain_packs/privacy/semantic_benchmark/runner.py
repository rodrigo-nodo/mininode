"""Run production's unchanged deterministic rules against synthetic fixtures."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

BACKEND_SRC = Path(__file__).resolve().parents[4] / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.domain_packs.privacy.evaluator import evaluate_control  # noqa: E402
from mininode_api.domain_packs.privacy.evidence_adapter import adapt_evidence  # noqa: E402
from mininode_api.web_inspector.models import (  # noqa: E402
    CookieEvidence, EvidenceContract, InspectionEvidence, LinkEvidence,
    PageEvidence, TargetEvidence, TransportEvidence,
)

from .schema import BenchmarkCase, CONTROLS, load_corpus


EVIDENCE_KEYS = {
    "PRV-008": "processing_purposes",
    "PRV-010": "data_recipients",
    "PRV-012": "data_retention",
}
STRENGTH = {
    "PRV-008": {"none": 0, "generic": 1, "concrete": 2},
    "PRV-010": {"none": 0, "generic": 1, "explicit": 2},
    "PRV-012": {"none": 0, "generic": 1, "explicit": 2},
}


@dataclass(frozen=True)
class CaseResult:
    policy_id: str
    control: str
    expected_class: str
    actual_class: str
    match: bool


def _contract(case: BenchmarkCase) -> EvidenceContract:
    base_url = f"https://{case.policy_id}.benchmark.invalid/"
    if case.prv003 == "not_detected":
        links: list[LinkEvidence] = []
        pages = [PageEvidence(base_url, 200, "Inicio", "text/html")]
    else:
        policy_url = base_url + "privacy"
        links = [LinkEvidence(policy_url, "Política de privacidad", base_url)]
        text = "\n".join(item.text for item in case.evidence + case.hard_negatives)
        pages = [
            PageEvidence(
                policy_url, 200, "Política de privacidad", "text/html",
                visible_text=text, content_text=text,
            )
        ]
    return EvidenceContract(
        target=TargetEvidence(base_url, base_url, f"{case.policy_id}.benchmark.invalid"),
        inspection=InspectionEvidence(1, 1, False, []),
        pages=pages,
        transport=TransportEvidence(True, True, None, False),
        links=links,
        forms=[],
        cookies=CookieEvidence(False, [], False, False),
        contacts=[],
    )


def run_case(case: BenchmarkCase) -> CaseResult:
    adapted = adapt_evidence(_contract(case))
    prv003 = evaluate_control("PRV-003", adapted["PRV-003"])
    evaluated = evaluate_control(case.control, adapted[case.control], {"PRV-003": prv003})
    actual = (
        "not_applicable"
        if evaluated["result"] == "not_applicable"
        else adapted[case.control][EVIDENCE_KEYS[case.control]]
    )
    return CaseResult(
        case.policy_id, case.control, case.expected_class, actual,
        case.expected_class == actual,
    )


def run_benchmark(cases: Iterable[BenchmarkCase] | None = None) -> list[CaseResult]:
    selected = load_corpus().cases if cases is None else cases
    return [run_case(case) for case in selected]


def _direction(result: CaseResult) -> int:
    """Return +1 for promotion, -1 for omission, 0 for incomparable/equal."""
    if result.expected_class in {"not_applicable", "explicit_none"}:
        return 0
    if result.actual_class in {"not_applicable", "explicit_none"}:
        return 0
    order = STRENGTH[result.control]
    if result.expected_class not in order or result.actual_class not in order:
        return 0
    return (order[result.actual_class] > order[result.expected_class]) - (
        order[result.actual_class] < order[result.expected_class]
    )


def calculate_metrics(results: Iterable[CaseResult]) -> dict:
    rows = list(results)
    matches = sum(item.match for item in rows)
    by_control: dict[str, dict] = {}
    for control in CONTROLS:
        selected = [item for item in rows if item.control == control]
        correct = sum(item.match for item in selected)
        by_control[control] = {
            "total": len(selected),
            "matches": correct,
            "accuracy": correct / len(selected) if selected else 0.0,
        }
    labels = sorted({item.expected_class for item in rows} | {item.actual_class for item in rows})
    precision = []
    recall = []
    for label in labels:
        true_positive = sum(
            item.expected_class == label == item.actual_class for item in rows
        )
        predicted = sum(item.actual_class == label for item in rows)
        expected = sum(item.expected_class == label for item in rows)
        precision.append(true_positive / predicted if predicted else 0.0)
        recall.append(true_positive / expected if expected else 0.0)
    confusion = Counter(
        (item.control, item.expected_class, item.actual_class) for item in rows
    )
    return {
        "total_cases": len(rows),
        "exact_matches": matches,
        "mismatches": len(rows) - matches,
        "accuracy": matches / len(rows) if rows else 0.0,
        "per_control": by_control,
        "confusion_counts": [
            {"control": key[0], "expected": key[1], "actual": key[2], "count": count}
            for key, count in sorted(confusion.items())
        ],
        "false_positive_promotions": sum(_direction(item) > 0 for item in rows),
        "false_negative_omissions": sum(_direction(item) < 0 for item in rows),
        "macro_precision": sum(precision) / len(precision) if precision else 0.0,
        "macro_recall": sum(recall) / len(recall) if recall else 0.0,
    }


def _text_report(results: list[CaseResult], metrics: dict) -> str:
    lines = [
        f"{'policy_id':<16} {'control':<8} {'expected':<15} {'baseline':<15} match",
        "-" * 66,
    ]
    lines.extend(
        f"{row.policy_id:<16} {row.control:<8} {row.expected_class:<15} "
        f"{row.actual_class:<15} {str(row.match).lower()}"
        for row in results
    )
    lines.extend([
        "", f"total: {metrics['total_cases']}",
        f"matches: {metrics['exact_matches']}",
        f"mismatches: {metrics['mismatches']}",
        f"accuracy: {metrics['accuracy']:.3f}",
        f"false_positive_promotions: {metrics['false_positive_promotions']}",
        f"false_negative_omissions: {metrics['false_negative_omissions']}", "",
        "per control:",
    ])
    lines.extend(
        f"  {control}: {value['matches']}/{value['total']} ({value['accuracy']:.3f})"
        for control, value in metrics["per_control"].items()
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    results = run_benchmark()
    metrics = calculate_metrics(results)
    if args.format == "json":
        print(json.dumps({"results": [asdict(row) for row in results], "metrics": metrics}, indent=2))
    else:
        print(_text_report(results, metrics))


if __name__ == "__main__":
    main()
