"""Deterministic evaluators for the Mininode Privacy Pack v0.1.

The module consumes prepared evidence only. It deliberately performs no network
access, crawling, persistence, or AI-assisted interpretation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

_PACK_DIR = Path(__file__).resolve().parent


def load_controls() -> list[dict[str, Any]]:
    """Load the Privacy control catalog."""
    with (_PACK_DIR / "controls.json").open(encoding="utf-8") as file:
        return json.load(file)["controls"]


def _control_index() -> dict[str, dict[str, Any]]:
    return {control["code"]: control for control in load_controls()}


def _previous_result(previous_results: Any, control_code: str) -> str | None:
    if not previous_results:
        return None
    if isinstance(previous_results, Mapping):
        value = previous_results.get(control_code)
        if isinstance(value, Mapping):
            return value.get("result")
        return value if isinstance(value, str) else None
    for item in previous_results:
        if item.get("control_code") == control_code:
            return item.get("result")
    return None


def _output(
    control: dict[str, Any],
    result: str,
    evidence: Mapping[str, Any],
    *,
    reason: str | None = None,
) -> dict[str, Any]:
    observations = evidence.get("observations", [])
    if isinstance(observations, str):
        observations = [observations]
    confidence = evidence.get("confidence", "high")
    if confidence not in {"high", "medium", "low"}:
        raise ValueError("confidence must be high, medium, or low")
    return {
        "control_code": control["code"],
        "result": result,
        "confidence": confidence,
        "evidence": list(observations),
        "reason": reason or control["criteria"][result],
    }


def _technical_error(
    control: dict[str, Any], evidence: Mapping[str, Any]
) -> dict[str, Any] | None:
    if evidence.get("technical_error"):
        return _output(control, "not_evaluable", evidence)
    return None


def _evaluate_prv_001(control: dict[str, Any], evidence: Mapping[str, Any], _: Any) -> dict[str, Any]:
    if error := _technical_error(control, evidence):
        return error
    result = "detected" if evidence.get("policy_visible", False) else "not_detected"
    return _output(control, result, evidence)


def _evaluate_prv_002(control: dict[str, Any], evidence: Mapping[str, Any], previous: Any) -> dict[str, Any]:
    dependency = _previous_result(previous, "PRV-001")
    if dependency == "not_detected":
        return _output(control, "not_applicable", evidence)
    if dependency != "detected" or evidence.get("technical_error"):
        return _output(control, "not_evaluable", evidence)
    accessible = evidence.get("policy_accessible", False)
    relevant = evidence.get("content_relevant", False)
    if accessible and relevant:
        result = "detected"
    elif accessible or relevant:
        result = "partial"
    else:
        result = "not_detected"
    return _output(control, result, evidence)


def _evaluate_prv_101(control: dict[str, Any], evidence: Mapping[str, Any], _: Any) -> dict[str, Any]:
    if error := _technical_error(control, evidence):
        return error
    forms = evidence.get("personal_data_forms", [])
    detected = evidence.get("personal_data_form", bool(forms))
    return _output(control, "detected" if detected else "not_detected", evidence)


def _evaluate_prv_104(control: dict[str, Any], evidence: Mapping[str, Any], previous: Any) -> dict[str, Any]:
    dependency = _previous_result(previous, "PRV-101")
    if dependency == "not_detected":
        return _output(control, "not_applicable", evidence)
    if dependency != "detected" or evidence.get("technical_error"):
        return _output(control, "not_evaluable", evidence)
    clear_information = evidence.get("information_clear", False)
    consent_required = evidence.get("consent_required", False)
    consent_visible = evidence.get("consent_visible", False)
    if clear_information and (not consent_required or consent_visible):
        result = "detected"
    elif evidence.get("privacy_signal", False) or clear_information or consent_visible:
        result = "partial"
    else:
        result = "not_detected"
    return _output(control, result, evidence)


def _evaluate_prv_201(control: dict[str, Any], evidence: Mapping[str, Any], _: Any) -> dict[str, Any]:
    if error := _technical_error(control, evidence):
        return error
    if not evidence.get("relevant_cookies_detected", False):
        return _output(control, "not_applicable", evidence)
    information = evidence.get("cookie_information_visible", False)
    preferences_required = evidence.get("preferences_required", False)
    preferences_available = evidence.get("preferences_available", False)
    if information and (not preferences_required or preferences_available):
        result = "detected"
    elif information or preferences_available:
        result = "partial"
    else:
        result = "not_detected"
    return _output(control, result, evidence)


def _evaluate_prv_301(control: dict[str, Any], evidence: Mapping[str, Any], _: Any) -> dict[str, Any]:
    if error := _technical_error(control, evidence):
        return error
    channels = evidence.get("contact_channels", [])
    detected = evidence.get("contact_visible", bool(channels))
    return _output(control, "detected" if detected else "not_detected", evidence)


def _evaluate_prv_501(control: dict[str, Any], evidence: Mapping[str, Any], _: Any) -> dict[str, Any]:
    if error := _technical_error(control, evidence):
        return error
    https = evidence.get("https", False)
    valid_certificate = evidence.get("certificate_valid", False)
    anomalies = evidence.get("anomalies", [])
    if https and valid_certificate and not anomalies:
        result = "detected"
    elif https and valid_certificate:
        result = "partial"
    else:
        result = "not_detected"
    return _output(control, result, evidence)


_EVALUATORS = {
    "PRV-001": _evaluate_prv_001,
    "PRV-002": _evaluate_prv_002,
    "PRV-101": _evaluate_prv_101,
    "PRV-104": _evaluate_prv_104,
    "PRV-201": _evaluate_prv_201,
    "PRV-301": _evaluate_prv_301,
    "PRV-501": _evaluate_prv_501,
}


def evaluate_control(
    control_code: str,
    evidence: Mapping[str, Any],
    previous_results: Any = None,
) -> dict[str, Any]:
    """Evaluate one control from prepared, structured evidence."""
    controls = _control_index()
    if control_code not in controls:
        raise ValueError(f"Unknown Privacy control: {control_code}")
    if not isinstance(evidence, Mapping):
        raise TypeError("evidence must be a mapping")
    return _EVALUATORS[control_code](
        controls[control_code], evidence, previous_results
    )
