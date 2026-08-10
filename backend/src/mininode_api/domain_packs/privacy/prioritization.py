"""Finding prioritization for the Mininode Privacy Pack v0.1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

_PACK_DIR = Path(__file__).resolve().parent
_IMPACT_ORDER = {"muy_alto": 4, "alto": 3, "medio": 2, "bajo": 1}
_RESULT_ORDER = {"not_detected": 2, "partial": 1}
_CONFIDENCE_ORDER = {"high": 3, "medium": 2, "low": 1}


def load_controls() -> list[dict[str, Any]]:
    with (_PACK_DIR / "controls.json").open(encoding="utf-8") as file:
        return json.load(file)["controls"]


def _visible_priority(impact: str, result: str) -> str:
    if impact == "muy_alto" or (impact == "alto" and result == "not_detected"):
        return "Alta"
    if impact in {"alto", "medio"}:
        return "Media"
    return "Baja"


def select_priorities(
    results: Iterable[Mapping[str, Any]],
    controls: Iterable[Mapping[str, Any]] | None = None,
    limit: int = 3,
) -> list[dict[str, str]]:
    """Return at most three formal, client-safe priorities by default."""
    if limit < 0:
        raise ValueError("limit cannot be negative")
    control_index = {
        control["code"]: control for control in (controls or load_controls())
    }
    candidates: list[tuple[dict[str, Any], Mapping[str, Any]]] = []
    for evaluation in results:
        control = control_index.get(evaluation["control_code"])
        if control is None:
            raise ValueError(
                f"Unknown Privacy control: {evaluation['control_code']}"
            )
        if control["control_type"] not in {
            "evaluation",
            "conditional_evaluation",
        }:
            continue
        if evaluation["result"] not in {"partial", "not_detected"}:
            continue
        candidates.append((control, evaluation))

    candidates.sort(
        key=lambda item: (
            -_IMPACT_ORDER[item[0]["impact"]],
            -_RESULT_ORDER[item[1]["result"]],
            -_CONFIDENCE_ORDER.get(item[1].get("confidence", "low"), 0),
            item[0]["code"],
        )
    )

    priorities = []
    for control, evaluation in candidates[: min(limit, 3)]:
        priorities.append(
            {
                "control_code": control["code"],
                "name": control["name"],
                "priority": _visible_priority(
                    control["impact"], evaluation["result"]
                ),
                "finding": evaluation.get(
                    "reason", control["criteria"][evaluation["result"]]
                ),
                "recommendation": control["base_recommendation"],
            }
        )
    return priorities
