"""Translate generic Web Inspector evidence into Privacy Pack signals."""

from __future__ import annotations

import re
import unicodedata
from ipaddress import ip_address
from urllib.parse import urlsplit, urlunsplit

from mininode_api.web_inspector.models import EvidenceContract, FormEvidence, LinkEvidence


CONTROL_CODES = (
    "PRV-001",
    "PRV-002",
    "PRV-003",
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
_KNOWN_PRIVACY_PROVIDERS = {
    "hcaptcha.com": "hCaptcha",
    "google.com": "Google/reCAPTCHA",
    "googleusercontent.com": "Google/reCAPTCHA",
    "facebook.com": "Meta/Facebook",
    "meta.com": "Meta/Facebook",
    "stripe.com": "Stripe",
    "shopify.com": "Shopify",
}
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
_CONTACT_TERMS = ("contact", "contacto", "contactenos", "contactanos")
_MESSAGE_TERMS = ("message", "mensaje", "consulta", "comentario")
_CONTACT_ADDRESS_TYPES = {"email", "tel"}
_VISIBLE_FIELD_TYPES = {
    "email": "email",
    "tel": "phone",
    "textarea": "message",
}
_VISIBLE_NAME_FIELDS = {
    "name": "name",
    "nombre": "name",
    "full name": "name",
    "nombre completo": "name",
}


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


def _public_source_url(value: str) -> str | None:
    """Return a display-safe page URL without credentials, query, or fragment."""

    try:
        parts = urlsplit(value)
        hostname = (parts.hostname or "").lower()
        port = parts.port
    except ValueError:
        return None
    if parts.scheme.lower() not in {"http", "https"} or not hostname:
        return None
    try:
        ip_address(hostname)
    except ValueError:
        pass
    else:
        return None
    default_port = (parts.scheme.lower() == "http" and port == 80) or (
        parts.scheme.lower() == "https" and port == 443
    )
    netloc = hostname if not port or default_port else f"{hostname}:{port}"
    return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", "", ""))


def _inspected_source_urls(contract: EvidenceContract, values: list[str]) -> list[str]:
    """Keep deterministic, safe references to final URLs actually inspected."""

    inspected = {page.url for page in contract.pages}
    sources = {
        safe
        for value in values
        if value in inspected
        for safe in [_public_source_url(value)]
        if safe
    }
    return sorted(sources)


def _visible_field_category(field) -> str | None:
    """Map only conservative, known field metadata to a public category."""

    field_type = _normalize(field.type)
    if field_type in _VISIBLE_FIELD_TYPES:
        return _VISIBLE_FIELD_TYPES[field_type]
    if field_type in {"text", ""}:
        return _VISIBLE_NAME_FIELDS.get(_normalize(field.name))
    return None


def _visible_form_evidence(
    forms: list[tuple[FormEvidence, str | None]], source_url: str | None
) -> dict | None:
    """Minimize form observations from exactly the selected public source."""

    if not source_url:
        return None
    matching = [
        form
        for form, _ in forms
        if _public_source_url(form.source_url) == source_url
    ]
    if not matching:
        return None

    fields = sorted({
        category
        for form in matching
        for field in form.fields
        for category in [_visible_field_category(field)]
        if category
    })
    privacy_link = any(form.privacy_links for form in matching)
    privacy_information = privacy_link or any(
        _contains_phrase(form.nearby_text, _PRIVACY_INFORMATION_TERMS)
        for form in matching
    )
    consent_mechanism = any(
        _contains_phrase(checkbox.label, _CONSENT_TERMS)
        for form in matching
        for checkbox in form.checkboxes
    )
    return {
        "type": "personal_data_form",
        "fields": fields,
        "privacy_link": privacy_link,
        "privacy_information": privacy_information,
        "consent_mechanism": consent_mechanism,
        "source_url": source_url,
    }


def _privacy_match(link: LinkEvidence) -> tuple[bool, str]:
    if _contains_phrase(link.text, _PRIVACY_TERMS):
        return True, "high"
    if _contains_phrase(urlsplit(link.url).path, _PRIVACY_TERMS):
        return True, "medium"
    return False, "low"


def _inspection_sufficient(contract: EvidenceContract) -> bool:
    return contract.target.final_url is not None and contract.inspection.pages_analyzed > 0


def _hostname(url: str) -> str:
    return (urlsplit(url).hostname or "").rstrip(".").lower()


def _same_site(left: str, right: str) -> bool:
    """Recognize the deliberately narrow apex/www relationship used by inspection."""

    return left.removeprefix("www.") == right.removeprefix("www.")


def _provider_name(hostname: str) -> str | None:
    return next(
        (name for domain, name in _KNOWN_PRIVACY_PROVIDERS.items()
         if hostname == domain or hostname.endswith(f".{domain}")),
        None,
    )


def _organization_signals(contract: EvidenceContract) -> tuple[str, ...]:
    target_host = _hostname(contract.target.final_url or contract.target.requested_url)
    label = target_host.removeprefix("www.").split(".", 1)[0]
    signals = {_normalize(label)}
    home = next(
        (page for page in contract.pages if _same_site(_hostname(page.url), target_host)),
        None,
    )
    if home and home.title:
        title = re.split(r"\s*[|\-–—:]\s*", home.title, maxsplit=1)[0]
        signals.add(_normalize(title))
    return tuple(sorted(signal for signal in signals if len(signal) >= 3 and signal not in {"home", "inicio"}))


def _prv003_evidence(
    contract: EvidenceContract,
    candidates: list[tuple[LinkEvidence, str]],
    sufficient: bool,
) -> dict:
    if not sufficient:
        return {"technical_error": True, "confidence": "low"}
    if not candidates:
        return {
            "policy_attribution": "none",
            "attribution_signals": [{"signal": "no_policy_candidate"}],
            "confidence": "high",
        }

    target_host = _hostname(contract.target.final_url or contract.target.requested_url)
    organization_signals = _organization_signals(contract)
    pages = {
        _normalized_url(observed): page
        for page in contract.pages
        for observed in (page.url, page.requested_url)
        if observed
    }
    observations: list[dict[str, str]] = []
    attributions: list[str] = []
    for link, _ in candidates:
        host = _hostname(link.url)
        safe_url = _public_source_url(link.url)
        base = {"hostname": host, "url": safe_url or ""}
        if _same_site(host, target_host):
            attributions.append("own")
            observations.append({**base, "attribution": "own", "signal": "same_site"})
            continue

        normalized_url = _normalized_url(link.url)
        page = pages.get(normalized_url)
        provider = _provider_name(host)
        if provider:
            if page is not None:
                document = f"{page.title or ''} {page.document_text}"
                privacy_document = _contains_phrase(document, _PRIVACY_TERMS)
                organization_mentioned = any(
                    _contains_phrase(document, {signal}) for signal in organization_signals
                )
                if privacy_document and organization_mentioned:
                    attributions.append("own")
                    observations.append({
                        **base,
                        "attribution": "own",
                        "signal": "provider_document_organization_mentioned",
                        "provider": provider,
                    })
                    continue
            attributions.append("third_party")
            observations.append({**base, "attribution": "third_party", "provider": provider})
            continue

        link_organization_mentioned = any(
            _contains_phrase(link.text, {signal}) for signal in organization_signals
        )
        if link_organization_mentioned:
            attributions.append("own")
            observations.append({**base, "attribution": "own", "signal": "organization_mentioned_in_link"})
            continue

        if page is None:
            attributions.append("ambiguous")
            observations.append({**base, "attribution": "ambiguous", "signal": "external_document_not_in_scope"})
            continue
        document = f"{page.title or ''} {page.document_text}"
        privacy_document = _contains_phrase(document, _PRIVACY_TERMS)
        organization_mentioned = any(
            _contains_phrase(document, {signal}) for signal in organization_signals
        )
        if privacy_document and organization_mentioned:
            attributions.append("own")
            observations.append({**base, "attribution": "own", "signal": "organization_mentioned"})
        else:
            attributions.append("ambiguous")
            observations.append({**base, "attribution": "ambiguous", "signal": "insufficient_attribution"})

    if "own" in attributions:
        attribution, confidence = "own", "high"
    elif "ambiguous" in attributions:
        attribution, confidence = "ambiguous", "medium"
    elif attributions and set(attributions) == {"third_party"}:
        attribution, confidence = "third_party", "high"
    else:
        attribution, confidence = "none", "high"
    return {
        "policy_attribution": attribution,
        "attribution_signals": observations,
        "confidence": confidence,
    }


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


def _contact_form(form: FormEvidence, contract: EvidenceContract) -> bool:
    """Recognize an explicit contact page with communication-oriented fields."""

    page = next((page for page in contract.pages if page.url == form.source_url), None)
    page_signal = _contains_phrase(urlsplit(form.source_url).path, _CONTACT_TERMS) or (
        page is not None and _contains_phrase(page.title or "", _CONTACT_TERMS)
    )
    if not page_signal:
        return False

    has_address = any(
        _normalize(field.type) in _CONTACT_ADDRESS_TYPES
        or _contains_phrase(f"{field.name} {field.label}", {"email", "correo", "telefono", "phone"})
        for field in form.fields
    )
    has_message = any(
        _normalize(field.type) == "textarea"
        or _contains_phrase(f"{field.name} {field.label}", _MESSAGE_TERMS)
        for field in form.fields
    )
    return has_address and has_message


def adapt_evidence(contract: EvidenceContract) -> dict[str, dict]:
    """Return deterministic, minimized evidence for the active controls."""
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
        successful_pages = {
            _normalized_url(observed_url): page
            for page in contract.pages
            for observed_url in (page.url, page.requested_url)
            if observed_url
        }
        error_urls = {_normalized_url(error["url"]) for error in contract.inspection.errors if error.get("url")}
        candidate_urls = {_normalized_url(link.url) for link, _ in candidates}
        successful_candidates = candidate_urls & successful_pages.keys()
        failed_candidates = candidate_urls & error_urls
        if successful_candidates:
            prv002["policy_accessible"] = True
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

    prv003 = _prv003_evidence(contract, candidates, sufficient)

    personal_forms = [(form, confidence) for form in contract.forms for matched, confidence in [_personal_form(form)] if matched]
    personal_form_source_urls = _inspected_source_urls(
        contract, [form.source_url for form, _ in personal_forms]
    )
    visible_evidence = _visible_form_evidence(
        personal_forms,
        personal_form_source_urls[0] if personal_form_source_urls else None,
    )
    prv101 = {"confidence": "low"}
    if sufficient:
        prv101["personal_data_form"] = bool(personal_forms)
        prv101["confidence"] = (
            "high" if any(confidence == "high" for _, confidence in personal_forms)
            else "medium" if personal_forms else "high"
        )
        if personal_form_source_urls:
            prv101["source_urls"] = personal_form_source_urls
            prv101["visible_evidence"] = visible_evidence
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
    if personal_form_source_urls:
        prv104["source_urls"] = personal_form_source_urls
        prv104["visible_evidence"] = visible_evidence
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
        prv201["relevant_cookies"] = bool(
            contract.cookies.detected or contract.cookies.set_cookie_names
        )
    else:
        prv201["technical_error"] = True

    explicit_contact = any(
        (
            getattr(contact, "type", None) in {"email", "phone"}
            and bool(getattr(contact, "value", None))
        )
        or bool(getattr(contact, "email", None))
        or bool(getattr(contact, "phone", None))
        for contact in contract.contacts
    )
    contact_visible = explicit_contact or any(
        _contact_form(form, contract) for form in contract.forms
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
    if transport.https is None or (
        transport.https is True and transport.tls_valid is None
    ):
        prv501["technical_error"] = True
        prv501["confidence"] = "low"

    return {
        "PRV-001": prv001,
        "PRV-002": prv002,
        "PRV-003": prv003,
        "PRV-101": prv101,
        "PRV-104": prv104,
        "PRV-201": prv201,
        "PRV-301": prv301,
        "PRV-501": prv501,
    }