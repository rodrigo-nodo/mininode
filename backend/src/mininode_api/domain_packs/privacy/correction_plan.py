"""Deterministic correction plans for Privacy diagnoses."""

from __future__ import annotations

from typing import Iterable, Mapping

from .prioritization import (
    _VISIBLE_PRIORITY,
    load_actions,
    ordered_actionable_findings,
)


def build_correction_plan(
    results: Iterable[Mapping], *, initial_score: int
) -> dict:
    """Build a complete plan from evaluated controls and an existing score.

    Findings without a catalog action for their exact result are omitted rather
    than receiving generated or inferred instructions.
    """
    catalog = load_actions()
    items = []
    for control, _evaluated_result, outcome in ordered_actionable_findings(results):
        action = catalog["actions"].get(control["code"], {}).get(outcome)
        if not action:
            continue
        items.append(
            {
                "control_code": control["code"],
                "name": control["name"],
                "priority": _VISIBLE_PRIORITY[control["impact"]],
                "result": outcome,
                "finding": control["criteria"][outcome],
                "recommendation": control["base_recommendation"],
                "action_steps": list(action["action_steps"]),
                "validation_step": action["validation_step"],
            }
        )

    return {
        "version": "1",
        "actions_version": catalog["version"],
        "initial_score": initial_score,
        "item_count": len(items),
        "items": items,
    }
