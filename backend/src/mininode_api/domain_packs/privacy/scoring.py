"""Privacy Score calculation for the Mininode Privacy Pack v0.1."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

_PACK_DIR = Path(__file__).resolve().parent


def load_scoring_config() -> dict[str, Any]:
    with (_PACK_DIR / "scoring.json").open(encoding="utf-8") as file:
        return json.load(file)


def load_controls() -> list[dict[str, Any]]:
    with (_PACK_DIR / "controls.json").open(encoding="utf-8") as file:
        return json.load(file)["controls"]


def status_for_score(score: int, config: Mapping[str, Any] | None = None) -> str:
    """Return the configured textual status for an integer score."""
    if not 0 <= score <= 100:
        raise ValueError("score must be between 0 and 100")
    config = config or load_scoring_config()
    for score_range in config["status_ranges"]:
        if score_range["min"] <= score <= score_range["max"]:
            return score_range["status"]
    raise ValueError(f"No status range configured for score {score}")


def _round_nearest(value: float) -> int:
    return math.floor(value + 0.5)


def calculate_privacy_score(
    results: Iterable[Mapping[str, Any]],
    controls: Iterable[Mapping[str, Any]] | None = None,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Calculate score and coverage from already evaluated controls."""
    config = dict(config or load_scoring_config())
    control_index = {
        control["code"]: control for control in (controls or load_controls())
    }
    earned_points = 0.0
    possible_points = 0.0
    evaluated_controls = 0
    applicable_controls = 0

    for evaluation in results:
        code = evaluation["control_code"]
        if code not in control_index:
            raise ValueError(f"Unknown Privacy control: {code}")
        control = control_index[code]
        result = evaluation["result"]
        if control["control_type"] == "context":
            continue
        if result == "not_applicable":
            continue

        applicable_controls += 1
        if result == "not_evaluable":
            continue
        if result not in config["result_factors"]:
            raise ValueError(f"Unsupported evaluation result: {result}")

        evaluated_controls += 1
        weight = config["impact_weights"][control["impact"]]
        score_weight = control.get("score_weight", 1)
        possible = weight * score_weight
        possible_points += possible
        earned_points += possible * config["result_factors"][result]

    score = (
        _round_nearest(earned_points / possible_points * 100)
        if possible_points
        else 0
    )
    coverage = (
        _round_nearest(evaluated_controls / applicable_controls * 100)
        if applicable_controls
        else 0
    )
    return {
        "score": score,
        "status": status_for_score(score, config),
        "coverage": coverage,
        "evaluated_controls": evaluated_controls,
        "applicable_controls": applicable_controls,
    }
