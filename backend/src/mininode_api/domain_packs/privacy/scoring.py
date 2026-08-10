"""Deterministic scoring for the Privacy Pack v0.1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping


_SCORING_PATH = Path(__file__).with_name("scoring.json")


def load_scoring() -> dict:
    with _SCORING_PATH.open(encoding="utf-8") as source:
        return json.load(source)


def score_privacy(evaluations: Iterable[Mapping]) -> dict:
    """Calculate score, preparation state and evaluation coverage."""
    rules = load_scoring()
    evaluations = list(evaluations)
    scoring_controls = [item for item in evaluations if item["type"] != "context"]
    applicable = [
        item for item in scoring_controls if item["status"] != "not_applicable"
    ]
    evaluable = [item for item in applicable if item["status"] != "not_evaluable"]

    possible = sum(
        rules["impact_weights"][item["impact"]]
        * item.get("score_weight", 1)
        for item in evaluable
    )
    earned = sum(
        rules["impact_weights"][item["impact"]]
        * item.get("score_weight", 1)
        * rules["status_factors"][item["status"]]
        for item in evaluable
    )
    score = round(100 * earned / possible) if possible else 0
    coverage = round(100 * len(evaluable) / len(applicable)) if applicable else 100
    state = next(
        item["label"]
        for item in rules["ranges"]
        if item["minimum"] <= score <= item["maximum"]
    )
    return {"score": score, "state": state, "coverage": coverage}
