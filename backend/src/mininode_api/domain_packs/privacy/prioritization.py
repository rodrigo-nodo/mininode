"""Consumer-facing priorities for Privacy Pack v0.1."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Mapping

from .evaluator import load_controls
from .scoring import load_scoring


_ELIGIBLE_TYPES = {"evaluation", "conditional_evaluation"}
_ELIGIBLE_RESULTS = {"partial", "not_detected"}
_CONFIDENCE_ORDER = {"high": 3, "medium": 2, "low": 1}
_VISIBLE_PRIORITY = {
    "muy_alto": "Alta",
    "alto": "Alta",
    "medio": "Media",
    "bajo": "Baja",
}


@lru_cache(maxsize=1)
def load_actions() -> dict:
    """Load and minimally validate the versioned deterministic action catalog."""
    path = Path(__file__).with_name("actions.json")
    with path.open(encoding="utf-8") as source:
        catalog = json.load(source)
    if not isinstance(catalog, dict) or not catalog.get("version"):
        raise ValueError("Privacy action catalog requires a version")
    if not isinstance(catalog.get("actions"), dict):
        raise ValueError("Privacy action catalog requires an actions object")
    return catalog


def prioritize_findings(results: Iterable[Mapping], *, limit: int = 3) -> list[dict]:
    """Return up to three formal, consumer-facing improvement priorities."""
    controls = {control["code"]: control for control in load_controls()}
    impact_weights = load_scoring()["impact_weights"]
    eligible = []
    for result in results:
        code = result.get("control_code", result.get("code"))
        control = controls.get(code)
        outcome = result.get("result", result.get("status"))
        if (
            control
            and control["type"] in _ELIGIBLE_TYPES
            and outcome in _ELIGIBLE_RESULTS
        ):
            eligible.append((control, result, outcome))

    eligible.sort(
        key=lambda item: (
            -impact_weights[item[0]["impact"]],
            0 if item[2] == "not_detected" else 1,
            -_CONFIDENCE_ORDER.get(item[1].get("confidence", "low"), 1),
            item[0]["code"],
        )
    )
    priorities = []
    for control, result, outcome in eligible[: min(max(limit, 0), 3)]:
        priority = {
            "control_code": control["code"],
            "name": control["name"],
            "priority": _VISIBLE_PRIORITY[control["impact"]],
            "finding": control["criteria"][outcome],
            "recommendation": control["base_recommendation"],
        }
        if result.get("source_url"):
            priority["source_url"] = result["source_url"]
        if result.get("evidence_summary"):
            priority["evidence_summary"] = result["evidence_summary"]
        priorities.append(priority)
    actions = load_actions()["actions"]
    for priority, (_, _, outcome) in zip(
        priorities, eligible[: min(max(limit, 0), 3)]
    ):
        action = actions.get(priority["control_code"], {}).get(outcome)
        if action:
            priority["action_steps"] = list(action["action_steps"])
            priority["validation_step"] = action["validation_step"]
    return priorities
