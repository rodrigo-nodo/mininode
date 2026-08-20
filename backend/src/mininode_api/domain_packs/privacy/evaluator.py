"""Deterministic evidence evaluation for Privacy Pack v0.1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


_CONTROLS_PATH = Path(__file__).with_name("controls.json")
_ALLOWED_CONFIDENCE = {"high", "medium", "low"}
_VISIBLE_FIELD_LABELS = {
    "name": "nombre",
    "email": "correo electrónico",
    "phone": "teléfono",
    "message": "mensaje",
}
_VISIBLE_FIELD_ORDER = tuple(_VISIBLE_FIELD_LABELS)


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
            if key not in {"confidence", "technical_error", "visible_evidence"}
        ]
    return list(reported) if isinstance(reported, (list, tuple)) else [reported]


def _join_visible_fields(fields: list[str]) -> str:
    if len(fields) == 1:
        return fields[0]
    return f"{', '.join(fields[:-1])} y {fields[-1]}"


def _evidence_summary(control_code: str, evidence: Mapping[str, Any]) -> str | None:
    visible = evidence.get("visible_evidence")
    if not isinstance(visible, Mapping) or visible.get("type") != "personal_data_form":
        return None
    source_urls = evidence.get("source_urls")
    if not isinstance(source_urls, (list, tuple)) or not source_urls:
        return None
    if visible.get("source_url") != source_urls[0]:
        return None

    if control_code == "PRV-101":
        categories = set(visible.get("fields", ()))
        labels = [
            _VISIBLE_FIELD_LABELS[category]
            for category in _VISIBLE_FIELD_ORDER
            if category in categories
        ]
        if labels:
            return f"Formulario que solicita {_join_visible_fields(labels)}."
        return "Se detectó un formulario que solicita datos potencialmente personales."
    if control_code == "PRV-104":
        if visible.get("privacy_link"):
            return "Se detectó un formulario con un enlace visible relacionado con privacidad."
        if visible.get("privacy_information"):
            return "Se detectó información visible relacionada con privacidad asociada al formulario."
        if visible.get("consent_mechanism"):
            return (
                "Se detectó una señal visible de consentimiento o aceptación asociada "
                "al formulario, sin información de privacidad reconocida en el contexto "
                "revisado."
            )
        return (
            "En el formulario revisado no se identificaron señales visibles de información "
            "de privacidad ni de consentimiento o aceptación."
        )
    return None


def _result(control: Mapping, result: str, evidence: Mapping, confidence: str) -> dict:
    if confidence not in _ALLOWED_CONFIDENCE:
        raise ValueError(f"Invalid confidence: {confidence}")
    evaluated = {
        "control_code": control["code"],
        "result": result,
        "confidence": confidence,
        "evidence": _reported_evidence(evidence),
        "reason": control["criteria"][result],
    }
    source_urls = evidence.get("source_urls")
    if isinstance(source_urls, (list, tuple)) and source_urls:
        evaluated["source_url"] = source_urls[0]
    summary = _evidence_summary(control["code"], evidence)
    if summary:
        evaluated["evidence_summary"] = summary
    return evaluated


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
    dependency = control.get("dependency")
    dependency_result = _previous_result(previous_results, dependency) if dependency else None
    if dependency and dependency_result == "not_detected":
        return _result(control, "not_applicable", evidence, confidence)
    if dependency and dependency_result == "not_evaluable":
        return _result(control, "not_evaluable", evidence, "low")
    if evidence.get("technical_error"):
        return _result(control, "not_evaluable", evidence, "low")

    if control_code == "PRV-001":
        result = "detected" if evidence.get("policy_visible") else "not_detected"
    elif control_code == "PRV-002":
        accessible = evidence.get("policy_accessible", False)
        relevant = evidence.get("policy_content_relevant", False)
        if accessible and relevant:
            result = "detected"
        else:
            result = "partial"
    elif control_code == "PRV-003":
        attribution = evidence.get("policy_attribution")
        if attribution == "own":
            result = "detected"
        elif attribution == "ambiguous":
            result = "partial"
        else:
            result = "not_detected"
    elif control_code == "PRV-005":
        identification = evidence.get("responsible_identification")
        result = "detected" if identification == "clear" else "partial" if identification == "ambiguous" else "not_detected"
    elif control_code == "PRV-006":
        channel = evidence.get("rights_channel")
        result = "detected" if channel == "explicit" else "partial" if channel == "generic" else "not_detected"
    elif control_code == "PRV-007":
        result = "detected" if evidence.get("data_categories") else "partial" if evidence.get("generic_personal_data") else "not_detected"
    elif control_code == "PRV-008":
        result = "detected" if evidence.get("treatment_purposes") else "partial" if evidence.get("generic_data_use") else "not_detected"
    elif control_code == "PRV-011":
        rights = evidence.get("holder_rights", ())
        result = "detected" if len(rights) >= 2 else "partial" if rights or evidence.get("generic_rights_reference") else "not_detected"
    elif control_code == "PRV-101":
        result = "detected" if evidence.get("personal_data_form") else "not_detected"
    elif control_code == "PRV-104":
        information = evidence.get("privacy_information", False)
        consent = evidence.get("consent_mechanism", False)
        if information:
            result = "detected"
        elif consent:
            result = "partial"
        else:
            result = "not_detected"
    elif control_code == "PRV-201":
        cookies_observed = evidence.get(
            "cookies_observed", evidence.get("relevant_cookies")
        )
        if cookies_observed is False:
            result = "not_applicable"
        elif evidence.get("cookie_banner", evidence.get("cookie_information", False)):
            result = "detected"
        else:
            result = "not_detected"
    elif control_code == "PRV-301":
        result = "detected" if evidence.get("contact_channel_visible") else "not_detected"
    else:  # PRV-501
        https = evidence.get("https")
        tls_valid = evidence.get("tls_valid")
        https_valid = https is True and tls_valid is True
        anomaly = evidence.get("mixed_content", False) or evidence.get(
            "inconsistent_redirects", False
        )
        if https_valid and anomaly:
            result = "partial"
        elif https_valid:
            result = "detected"
        elif https is False or tls_valid is False:
            result = "not_detected"
        else:
            result = "not_evaluable"

    return _result(control, result, evidence, confidence)
