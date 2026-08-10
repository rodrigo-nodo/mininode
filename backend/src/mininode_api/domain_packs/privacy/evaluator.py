"""Evaluation helpers for the Privacy Pack v0.1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping


_CONTROLS_PATH = Path(__file__).with_name("controls.json")
VALID_STATUSES = {
    "detected",
    "partial",
    "not_detected",
    "not_applicable",
    "not_evaluable",
}


def load_controls() -> list[dict]:
    """Return the canonical controls in their declared order."""
    with _CONTROLS_PATH.open(encoding="utf-8") as source:
        return json.load(source)["controls"]


def evaluate_privacy(statuses: Mapping[str, str]) -> list[dict]:
    """Combine a status per control with the canonical control metadata.

    Missing controls are explicitly marked ``not_evaluable`` so that they reduce
    coverage instead of being mistaken for a negative finding.
    """
    controls = load_controls()
    known_codes = {control["code"] for control in controls}
    unknown_codes = set(statuses) - known_codes
    if unknown_codes:
        raise ValueError(f"Unknown privacy controls: {', '.join(sorted(unknown_codes))}")

    evaluations = []
    for control in controls:
        status = statuses.get(control["code"], "not_evaluable")
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status for {control['code']}: {status}")
        evaluations.append({**control, "status": status})
    return evaluations
