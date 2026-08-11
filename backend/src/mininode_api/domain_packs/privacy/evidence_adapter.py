"""Translate generic Web Inspector evidence into Privacy Pack signals."""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit

from mininode_api.web_inspector.models import EvidenceContract, FormEvidence, LinkEvidence


CONTROL_CODES = (
    "PRV-001",
    "PRV-002",
    "PRV-101",
    "PRV-104",
    "PRV-201",
    "PRV-301",
    "PRV-501",
)
_PRIVACY_TERMS = (
    "privacidad",
    "privacy",
    "politica de privacidad",
    "proteccion de datos",
    "datos personales",
)
_PERSONAL_TERMS = {
    "nombre", "name", "apellido", "surname", "rut", "run", "dni", "documento",
    "correo", "correo electronico", "email", "e mail", "celular", "movil",
    "telefono", "fono", "phone", "direccion", "address", "comuna", "ciudad",
    "city", "pais", "country", "empresa", "company",
}
_PRIVACY_INFORMATION_TERMS = _PRIVACY_TERMS + ("tratamiento de datos",)
_CONSENT_TERMS = (
    "acepto", "consiento", "autorizo", "consent", "privacy", "privacidad",
    "terminos",
)
_PERSONAL_TYPES = {"email", "tel", "textarea"}
_TECHNICAL_TYPES = {"hidden", "submit", "button", "reset", "image"}


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(character for character in value if not unicodedata.combining(character))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def _contains_phrase(value: str, terms: tuple[str, ...] | set[str]) -> bool:
    normalized = _normalize(value)
    return any(
        re.search(rf"(?:^|\s){re.escape(_normalize(term))}(?:$|\s)", normalized)
        for term in terms
    )


def _normalized_url(value: str) -> str:
    parts = urlsplit(value)
    hostname = (parts.hostname or "").lower()
    port = parts.port
    default_port = (parts.scheme.lower() == "http" and port == 80) or (
        parts.scheme.lower() == "https" and port == 443
    )
    netloc = hostname if not port or default_port else f"{hostname}:{port}"
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), netloc, path, parts.query, ""))


def _privacy_match(link: LinkEvidence) -> tuple[bool, str]:
    if _contains_phrase(link.text, _PRIVACY_TERMS):
        return True, "high"
    if _contains_phrase(urlsplit(link.url).path, _PRIVACY_TERMS):
        return True, "medium"
    return False, "low"


def _inspection_sufficient(contract: EvidenceContract) -> bool:
    return contract.target.final_url is not None and contract.inspection.pages_analyzed > 0


def _personal_form(form: FormEvidence) -> tuple[bool, str | None]:
    for field in form.fields:
        field_type = _normalize(field.type)
        if field_type in _TECHNICAL_TYPES:
            continue
        if field_type in _PERSONAL_TYPES:
            return True, "high"
        if _contains_phrase(field.label, _PERSONAL_TERMS):
            return True, "high"
        if _contains_phrase(field.name, _PERSONAL_TERMS):
            return True, "medium"
    return False, None


def adapt_evidence(contract: EvidenceContract) -> dict[str, dict]:
    """Return deterministic, minimized evidence for exactly seven controls."""
    sufficient = _inspection_sufficient(contract)
    candidates = [(link, confidence) for link in contract.links for matched, confidence in [_privacy_match(link)] if matched]
    policy_confidence = "high" if any(confidence == "high" for _, confidence in candidates) else "medium"

    prv001 = {"confidence": policy_confidence if candidates else ("high" if sufficient else "low")}
    if sufficient:
        prv001["policy_visible"] = bool(candidates)
    else:
        prv001["technical_error"] = True

    prv002: dict = {
        "policy_link_found": bool(candidates),
        "confidence": policy_confidence if candidates else ("high" if sufficient else "low"),
    }
    if candidates:
        successful_pages = {_normalized_url(page.url): page for page in contract.pages}
        error_urls = {_normalized_url(error["url"]) for error in contract.inspection.errors if error.get("url")}
        candidate_urls = {_normalized_url(link.url) for link, _ in candidates}
        successful_candidates = candidate_urls & successful_pages.keys()
        failed_candidates = candidate_urls & error_urls
        if successful_candidates:
            prv002["policy_accessible"] = True
            # A candidate link establishes visibility, but an HTTP success alone does
            # not establish that the obtained page is relevant.  v0.1 only confirms
            # relevance when the obtained page title supplies a clear corroborating
            # signal; it never examines or retains full page content.
            relevant = any(
                _normalized_url(link.url) in successful_pages
                and _contains_phrase(
                    successful_pages[_normalized_url(link.url)].title or "",
                    _PRIVACY_TERMS,
                )
                for link, _ in candidates
            )
            prv002["policy_content_relevant"] = relevant
        elif failed_candidates:
            prv002["policy_accessible"] = False
            prv002["policy_content_relevant"] = False
        else:
            prv002["technical_error"] = True
            prv002["confidence"] = "low"
    elif not sufficient:
        prv002["technical_error"] = True

    personal_forms = [(form, confidence) for form in contract.forms for matched, confidence in [_personal_form(form)] if matched]
    prv101 = {"confidence": "low"}
    if sufficient:
        prv101["personal_data_form"] = bool(personal_forms)
        prv101["confidence"] = (
            "high" if any(confidence == "high" for _, confidence in personal_forms)
            else "medium" if personal_forms else "high"
        )
    else:
        prv101["technical_error"] = True

    privacy_link = any(form.privacy_links for form, _ in personal_forms)
    privacy_information = privacy_link or any(
        _contains_phrase(form.nearby_text, _PRIVACY_INFORMATION_TERMS)
        for form, _ in personal_forms
    )
    consent = any(
        _contains_phrase(checkbox.label, _CONSENT_TERMS)
        for form, _ in personal_forms
        for checkbox in form.checkboxes
    )
    prv104 = {
        "privacy_information": privacy_information,
        "consent_required": consent,
        "consent_mechanism": consent,
        "information_complete": False,
        "privacy_link": privacy_link,
        "confidence": "high" if personal_forms else ("high" if sufficient else "low"),
    }
    if not sufficient:
        prv104["technical_error"] = True

    prv201 = {
        "cookie_information": contract.cookies.banner_detected,
        "preferences_required": False,
        "preference_mechanism": contract.cookies.preferences_detected,
        "information_complete": False,
        "cookie_banner": contract.cookies.banner_detected,
        "confidence": "high" if sufficient else "low",
    }
    if sufficient:
        prv201["relevant_cookies"] = bool(contract.cookies.detected or contract.cookies.set_cookie_names)
    else:
        prv201["technical_error"] = True

    contact_visible = any(
        (
            getattr(contact, "type", None) in {"email", "phone"}
            and bool(getattr(contact, "value", None))
        )
        or bool(getattr(contact, "email", None))
        or bool(getattr(contact, "phone", None))
        for contact in contract.contacts
    )
    prv301 = {"confidence": "high" if sufficient else "low"}
    if sufficient:
        prv301["contact_channel_visible"] = contact_visible
    else:
        prv301["technical_error"] = True

    transport = contract.transport
    prv501 = {
        "https": transport.https,
        "tls_valid": transport.tls_valid,
        "mixed_content": transport.mixed_content,
        "inconsistent_redirects": False,
        "confidence": "high",
    }
    if transport.https is None or transport.tls_valid is None:
        prv501["technical_error"] = True
        prv501["confidence"] = "low"

    return {
        "PRV-001": prv001,
        "PRV-002": prv002,
        "PRV-101": prv101,
        "PRV-104": prv104,
        "PRV-201": prv201,
        "PRV-301": prv301,
        "PRV-501": prv501,
    }
