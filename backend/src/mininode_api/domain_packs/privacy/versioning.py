"""Canonical diagnostic versions and deterministic comparability rules."""

from __future__ import annotations

from typing import Any, Mapping

from .evaluator import load_control_catalog
from .scoring import load_scoring


def diagnostic_versions() -> dict[str, str]:
    """Read diagnostic versions from the canonical domain catalogs."""
    versions = {
        "framework_version": load_control_catalog().get("version"),
        "scoring_version": load_scoring().get("version"),
    }
    if any(not isinstance(value, str) or not value.strip() for value in versions.values()):
        raise ValueError("Privacy diagnostic versions must be non-empty strings")
    return versions


def diagnostic_comparability(
    original: Mapping[str, Any], current: Mapping[str, Any]
) -> dict[str, Any]:
    """Return whether two snapshots share the same framework and scoring versions."""
    keys = ("framework_version", "scoring_version")
    original_versions = {key: original.get(key) for key in keys}
    current_versions = {key: current.get(key) for key in keys}

    all_versions = (*original_versions.values(), *current_versions.values())
    if any(not isinstance(value, str) or not value.strip() for value in all_versions):
        reason = "missing_version"
    elif original_versions["framework_version"] != current_versions["framework_version"]:
        reason = "framework_version_mismatch"
    elif original_versions["scoring_version"] != current_versions["scoring_version"]:
        reason = "scoring_version_mismatch"
    else:
        reason = None

    return {
        "status": "comparable" if reason is None else "not_comparable",
        "reason": reason,
        "original": original_versions,
        "current": current_versions,
    }
