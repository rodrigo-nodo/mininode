"""Deterministic evidence evaluation for Privacy Pack v0.1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


_CONTROLS_PATH = Path(__file__).with_name("controls.json")
_ALLOWED_CONFIDENCE = {"high", "medium", "low"}


def load_controls() -> list[dict[str, Any]]:
    """Load the approved control catalog in its canonical order."""
    with _CONTROLS_PATH.open(encoding="utf-8") as source:
        return json.load(source)["controls"]


def _previous_result(previous_results: Mapping | None, code: str) -> str | None:
    if not previous_results or code not in previous_results:
        return None
    value = previous_results[code]
    return value.get("result") if isinstance(value, Mapping) else value


def _reported_evidence(evidence: Mapping[str, Any]) -> list[Any]:
    reported = evidence.get("evidence", evidence.get("items"))
    if reported is None:
        return [
            {key: value}
            for key, value in evidence.items()
            if key not in {"confidence", "technical_error"}
        ]
    return list(reported) if isinstance(reported, (list, tuple)) else [reported]


def _result(control: Mapping, result: str, evidence: Mapping, confidence: str) -> dict:
    if confidence not in _ALLOWED_CONFIDENCE:
        raise ValueError(f"Invalid confidence: {confidence}")
    return {
        "control_code": control["code"],
        "result": result,
        "confidence": confidence,
        "evidence": _reported_evidence(evidence),
        "reason": control["criteria"][result],
    }


def evaluate_control(
    control_code: str,
    evidence: Mapping[str, Any],
    previous_results: Mapping | None = None,
) -> dict:
    """Evaluate one control from structured, already-collected evidence.

    This function performs no network access. Evidence collection is deliberately
    outside the Privacy Pack.
    """
    controls = {control["code"]: control for control in load_controls()}
    if control_code not in controls:
        raise ValueError(f"Unknown privacy control: {control_code}")
    if not isinstance(evidence, Mapping):
        raise TypeError("evidence must be a mapping")

    control = controls[control_code]
    confidence = evidence.get("confidence", "high")
    if evidence.get("technical_error"):
        return _result(control, "not_evaluable", evidence, "low")

    dependency = control.get("dependency")
    if dependency and _previous_result(previous_results, dependency) == "not_detected":
        return _result(control, "not_applicable", evidence, confidence)

    if control_code == "PRV-001":
        result = "detected" if evidence.get("policy_visible") else "not_detected"
    elif control_code == "PRV-002":
        accessible = evidence.get("policy_accessible", False)
        relevant = evidence.get("policy_content_relevant", False)
        if accessible and relevant:
            result = "detected"
        elif evidence.get("policy_link_found") or accessible or relevant:
            result = "partial"
        else:
            result = "not_detected"
    elif control_code == "PRV-101":
        result = "detected" if evidence.get("personal_data_form") else "not_detected"
    elif control_code == "PRV-104":
        information = evidence.get("privacy_information", False)
        consent_required = evidence.get("consent_required", False)
        consent = evidence.get("consent_mechanism", False)
        complete = evidence.get("information_complete", information)
        if information and complete and (not consent_required or consent):
            result = "detected"
        elif information or consent or evidence.get("privacy_link"):
            result = "partial"
        else:
            result = "not_detected"
    elif control_code == "PRV-201":
        if evidence.get("relevant_cookies") is False:
            result = "not_applicable"
        else:
            information = evidence.get("cookie_information", False)
            preferences_required = evidence.get("preferences_required", False)
            preferences = evidence.get("preference_mechanism", False)
            complete = evidence.get("information_complete", information)
            if information and complete and (not preferences_required or preferences):
                result = "detected"
            elif information or preferences or evidence.get("cookie_banner"):
                result = "partial"
            else:
                result = "not_detected"
    elif control_code == "PRV-301":
        result = "detected" if evidence.get("contact_channel_visible") else "not_detected"
    else:  # PRV-501
        https_valid = evidence.get("https", False) and evidence.get("tls_valid", False)
        anomaly = evidence.get("mixed_content", False) or evidence.get(
            "inconsistent_redirects", False
        )
        if https_valid and anomaly:
            result = "partial"
        elif https_valid:
            result = "detected"
        else:
            result = "not_detected"

    return _result(control, result, evidence, confidence)
