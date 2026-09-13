"""Privacy Score calculation for Privacy Pack v0.1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping

from .evaluator import load_controls


_SCORING_PATH = Path(__file__).with_name("scoring.json")


def load_scoring() -> dict:
    with _SCORING_PATH.open(encoding="utf-8") as source:
        return json.load(source)


def score_privacy(results: Iterable[Mapping]) -> dict:
    """Calculate visible preparation score and evidence coverage.

    The returned score is not a percentage of legal compliance. Controls
    catalogued as context are excluded from score and coverage.
    """
    rules = load_scoring()
    controls = {control["code"]: control for control in load_controls()}
    normalized = []
    for item in results:
        code = item.get("control_code", item.get("code"))
        if code not in controls:
            raise ValueError(f"Unknown privacy control: {code}")
        normalized.append((controls[code], item.get("result", item.get("status"))))

    scoring_results = [
        pair
        for pair in normalized
        if pair[0]["type"] != "context"
    ]
    applicable = [pair for pair in scoring_results if pair[1] != "not_applicable"]
    evaluated = [pair for pair in applicable if pair[1] != "not_evaluable"]

    possible_points = sum(
        rules["impact_weights"][control["impact"]]
        * control.get("score_weight", 1)
        for control, _ in evaluated
    )
    earned_points = sum(
        rules["impact_weights"][control["impact"]]
        * control.get("score_weight", 1)
        * rules["result_factors"][result]
        for control, result in evaluated
    )
    score = round(100 * earned_points / possible_points) if possible_points else 0
    coverage = round(100 * len(evaluated) / len(applicable)) if applicable else 100
    status = next(
        score_range["label"]
        for score_range in rules["ranges"]
        if score_range["minimum"] <= score <= score_range["maximum"]
    )
    return {
        "score": score,
        "status": status,
        "coverage": coverage,
        "evaluated_controls": len(evaluated),
        "applicable_controls": len(applicable),
    }
