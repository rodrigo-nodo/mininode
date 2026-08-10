"""Finding prioritization for the Privacy Pack v0.1."""

from __future__ import annotations

from typing import Iterable, Mapping

from .scoring import load_scoring


_ELIGIBLE_TYPES = {"evaluation", "conditional_evaluation"}
_ELIGIBLE_STATUSES = {"partial", "not_detected"}


def prioritize_findings(
    evaluations: Iterable[Mapping], *, limit: int = 3
) -> list[dict]:
    """Return at most three actionable findings in deterministic order."""
    impact_weights = load_scoring()["impact_weights"]
    eligible = [
        dict(item)
        for item in evaluations
        if item["type"] in _ELIGIBLE_TYPES
        and item["status"] in _ELIGIBLE_STATUSES
    ]
    eligible.sort(
        key=lambda item: (
            -impact_weights[item["impact"]],
            0 if item["status"] == "not_detected" else 1,
            -item.get("confidence", 0),
            item["code"],
        )
    )
    return eligible[: min(limit, 3)]
