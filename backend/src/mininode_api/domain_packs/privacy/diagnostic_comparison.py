"""Deterministic diagnostic comparisons shared by entitlement-based Privacy Web.

Pure domain logic: no database, commercial orders, or capability tokens.
"""

from __future__ import annotations

from typing import Mapping

from .versioning import diagnostic_comparability


def compare_diagnostics(
    plan: Mapping, original: Mapping, current: Mapping
) -> dict:
    """Compare plan items only when both diagnostics share canonical versions."""
    comparability = diagnostic_comparability(original, current)
    original_score = original["score"]
    current_score = current["score"]
    if comparability["status"] == "not_comparable":
        return {
            "version": "2",
            "comparability": comparability,
            "original_score": original_score,
            "current_score": current_score,
            "score_change": None,
            "total_plan_items": None,
            "corrected_count": None,
            "pending_count": None,
            "not_evaluable_count": None,
            "items": [],
        }

    current_controls = {
        item.get("control_code"): item for item in current.get("controls", [])
    }
    items = []
    for plan_item in plan.get("items", []):
        code = plan_item["control_code"]
        current_item = current_controls.get(code)
        if current_item is None or current_item.get("result") in {
            "not_evaluable", "not_applicable"
        }:
            check_status = "not_evaluable"
        elif current_item.get("result") == "detected":
            check_status = "corrected"
        else:
            check_status = "still_pending"
        items.append({
            "control_id": code,
            "name": plan_item.get("name", code),
            "status": check_status,
        })
    return {
        "version": "2",
        "comparability": comparability,
        "original_score": original_score,
        "current_score": current_score,
        "score_change": current_score - original_score,
        "total_plan_items": len(items),
        "corrected_count": sum(item["status"] == "corrected" for item in items),
        "pending_count": sum(item["status"] == "still_pending" for item in items),
        "not_evaluable_count": sum(item["status"] == "not_evaluable" for item in items),
        "items": items,
    }

