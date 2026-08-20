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
    "PRV-005",
    "PRV-006",
    "PRV-007",
    "PRV-008",
    "PRV-011",
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
_KNOWN_PROVIDER_POLICIES = {
    "hcaptcha.com": ("/privacy",),
    "google.com": ("/policies/privacy", "/privacy", "/recaptcha/about"),
    "www.google.com": ("/policies/privacy", "/privacy", "/recaptcha/about"),
    "policies.google.com": ("/privacy",),
    "g.co": ("/recaptcha",),
    "facebook.com": ("/privacy", "/policy"),
    "www.facebook.com": ("/privacy", "/policy"),
    "stripe.com": ("/privacy",),
    "www.shopify.com": ("/legal/privacy",),
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
_RESPONSIBLE_LABELS = ("responsable", "controlador", "controller", "titular del sitio")
_LEGAL_ENTITY_TERMS = ("spa", "s a", "ltda", "limitada", "sociedad", "fundacion", "corporacion")
_AMBIGUOUS_ORGANIZATIONS = ("nuestra empresa", "la empresa", "la organizacion", "este sitio")
_DATA_CATEGORY_TERMS = (
    "nombre", "apellido", "correo", "email", "telefono", "direccion", "rut", "dni",
    "datos de cuenta", "datos de pago", "informacion de pago", "identificador",
    "datos de navegacion", "informacion de navegacion", "cookies", "direccion ip",
    "informacion enviada", "datos de contacto",
)
_PURPOSE_TERMS = (
    "responder consultas", "atender consultas", "procesar compras", "procesar pagos",
    "gestionar cuentas", "administrar cuentas", "prestar servicios", "proveer servicios",
    "brindar servicios", "soporte", "marketing", "mercadotecnia", "analitica",
    "seguridad", "administrar solicitudes", "gestionar solicitudes", "enviar comunicaciones",
    "contactar", "mejorar nuestros servicios",
)
_GENERIC_USE_TERMS = (
    "uso de datos", "usar sus datos", "usamos sus datos", "utilizamos sus datos",
    "tratamos sus datos",
)
_RIGHT_TERMS = (
    "acceso", "rectificacion", "actualizacion", "eliminacion", "supresion", "oposicion",
    "portabilidad", "cancelacion", "revocacion",
)
_GENERIC_RIGHT_TERMS = ("derechos del titular", "sus derechos", "ejercicio de derechos")


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


def _same_site(left: str, right: str) -> bool:
    left = left.lower().removeprefix("www.")
    right = right.lower().removeprefix("www.")
    return left == right


def _organization_terms(contract: EvidenceContract) -> tuple[str, ...]:
    hostname = (contract.target.domain or urlsplit(contract.target.requested_url).hostname or "")
    label = hostname.lower().removeprefix("www.").split(".")[0]
    normalized = _normalize(label)
    return (normalized,) if len(normalized) >= 4 else ()


def _known_general_provider_policy(url: str) -> bool:
    parts = urlsplit(url)
    hostname = (parts.hostname or "").lower()
    paths = _KNOWN_PROVIDER_POLICIES.get(hostname)
    path = parts.path.rstrip("/").lower() or "/"
    return bool(paths and any(path == expected or path.startswith(f"{expected}/") for expected in paths))


def _policy_attribution(contract: EvidenceContract, candidates: list[tuple[LinkEvidence, str]]) -> dict:
    """Attribute the best visible policy using only already-inspected evidence."""
    if not candidates:
        return {
            "policy_attribution": "none",
            "attribution_signals": ["no_policy_candidate"],
            "confidence": "high" if _inspection_sufficient(contract) else "low",
        }

    pages = {
        _normalized_url(observed): page
        for page in contract.pages
        for observed in (page.url, page.requested_url)
        if observed
    }
    target_host = (contract.target.domain or urlsplit(contract.target.requested_url).hostname or "").lower()
    organization_terms = _organization_terms(contract)
    ambiguous = False
    uninspected = False
    third_party_urls: list[str] = []
    ambiguous_urls: list[str] = []
    uninspected_urls: list[str] = []
    for link, _ in candidates:
        hostname = (urlsplit(link.url).hostname or "").lower()
        safe_url = _public_source_url(link.url)
        if _same_site(hostname, target_host):
            return {
                "policy_attribution": "own",
                "attribution_signals": ["same_site_hostname"],
                "source_urls": [safe_url] if safe_url else [],
                "confidence": "high",
            }
        if _known_general_provider_policy(link.url):
            if safe_url:
                third_party_urls.append(safe_url)
            continue

        page = pages.get(_normalized_url(link.url))
        if page is None:
            uninspected = True
            if safe_url:
                uninspected_urls.append(safe_url)
            continue
        document = _normalize(f"{page.title or ''} {page.visible_text or ''}")
        attributed = any(
            re.search(rf"(?:^|\s){re.escape(term)}(?:$|\s)", document)
            for term in organization_terms
        )
        privacy_document = _contains_phrase(document, _PRIVACY_INFORMATION_TERMS)
        if attributed and privacy_document:
            return {
                "policy_attribution": "own",
                "attribution_signals": ["external_document_names_organization", "privacy_document"],
                "source_urls": [safe_url] if safe_url else [],
                "confidence": "high",
            }
        ambiguous = True
        if safe_url:
            ambiguous_urls.append(safe_url)

    if third_party_urls and not ambiguous and not uninspected:
        return {
            "policy_attribution": "third_party",
            "attribution_signals": ["known_provider_general_policy"],
            "source_urls": sorted(set(third_party_urls)),
            "confidence": "high",
        }
    if ambiguous:
        return {
            "policy_attribution": "ambiguous",
            "attribution_signals": ["external_document_without_clear_attribution"],
            "source_urls": sorted(set(ambiguous_urls)),
            "confidence": "medium",
        }
    return {
        "policy_attribution": "unknown",
        "attribution_signals": ["external_policy_not_inspected"],
        "source_urls": sorted(set(uninspected_urls)),
        "technical_error": True,
        "confidence": "low",
    }


def _policy_document(contract: EvidenceContract, candidates: list[tuple[LinkEvidence, str]]):
    """Return one already-inspected policy page; never expands inspection scope."""

    pages = {
        _normalized_url(observed): page
        for page in contract.pages
        for observed in (page.url, page.requested_url)
        if observed
    }
    for link, _ in candidates:
        page = pages.get(_normalized_url(link.url))
        if page is not None:
            return page
    return None


def _substantive_policy_evidence(contract: EvidenceContract, candidates) -> dict[str, dict]:
    page = _policy_document(contract, candidates)
    codes = ("PRV-005", "PRV-006", "PRV-007", "PRV-008", "PRV-011")
    if page is None or not (page.visible_text or "").strip():
        return {
            code: {"technical_error": True, "confidence": "low"}
            for code in codes
        }

    text = _normalize(f"{page.title or ''} {page.visible_text or ''}")
    source = _public_source_url(page.url)
    common = {"confidence": "high", "source_urls": [source] if source else []}
    organization_terms = _organization_terms(contract)
    raw_text = page.visible_text or ""
    identification_text = re.sub(r"\b[^\s@]+@[^\s@]+\.[a-z]{2,}\b", "", raw_text, flags=re.I)
    named_for_site = any(
        _contains_phrase(identification_text, {term}) for term in organization_terms
    )
    labelled_responsible = _contains_phrase(text, _RESPONSIBLE_LABELS)
    legal_entity = _contains_phrase(text, _LEGAL_ENTITY_TERMS)
    named_legal_entity = bool(re.search(
        r"\b[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ&.-]+(?:\s+[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ&.-]+){0,4}\s+(?:SpA|S\.?A\.?|Ltda\.?|Limitada)\b",
        raw_text,
    ))
    responsible_name = re.search(
        r"(?i:\bresponsable(?:\s+del\s+tratamiento)?\s*(?::|-|es)\s*)"
        r"([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ&.-]+)",
        raw_text,
    )
    explicitly_named_responsible = bool(
        responsible_name
        and _normalize(responsible_name.group(1)) not in {"la", "nuestra", "este"}
    )
    ambiguous_organization = _contains_phrase(text, _AMBIGUOUS_ORGANIZATIONS)

    email_match = re.search(r"\b[^\s@]+@[^\s@]+\.[a-z]{2,}\b", raw_text, re.I)
    email = bool(email_match)
    phone = bool(re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", raw_text))
    form_or_address = _contains_phrase(text, ("formulario", "direccion postal", "domicilio"))
    channel = email or phone or form_or_address
    explicit_channel = bool(channel and re.search(
        r"(?:para\s+(?:ejercer|consultas?|solicitudes?)\b.{0,80}|"
        r"(?:correo|email|contacto|formulario|direccion)\s+(?:de|para|sobre)\s+"
        r"(?:privacidad|datos personales|derechos)|"
        r"(?:privacidad|datos personales|derechos)\s*[:\-]\s*(?:correo|email|contacto|formulario|direccion))",
        _normalize(raw_text),
    ))
    if email_match and re.search(r"(?:privacy|privacidad|datos|derechos)", email_match.group(), re.I):
        explicit_channel = True
    if form_or_address and _contains_phrase(text, (
        "formulario de privacidad", "formulario para ejercer", "direccion de privacidad",
        "direccion para ejercer", "domicilio para ejercer",
    )):
        explicit_channel = True

    category_matches = sorted(term for term in _DATA_CATEGORY_TERMS if _contains_phrase(text, {term}))
    category_context = _contains_phrase(text, (
        "categorias de datos", "tipos de datos", "datos que recopilamos", "informacion que recopilamos",
        "recopilamos", "recolectamos", "incluyen", "tales como",
    ))
    categories = category_matches if category_context or len(category_matches) >= 2 else []
    purposes = sorted(term for term in _PURPOSE_TERMS if _contains_phrase(text, {term}))
    rights = sorted(term for term in _RIGHT_TERMS if _contains_phrase(text, {term}))

    return {
        "PRV-005": {
            **common,
            "responsible_identification": (
                "clear" if named_for_site or named_legal_entity or explicitly_named_responsible or (labelled_responsible and legal_entity)
                else "ambiguous" if labelled_responsible or legal_entity or ambiguous_organization
                else "none"
            ),
        },
        "PRV-006": {
            **common,
            "rights_channel": "explicit" if explicit_channel else "generic" if channel else "none",
        },
        "PRV-007": {
            **common,
            "data_categories": categories,
            "generic_personal_data": _contains_phrase(text, ("datos personales", "personal data")),
        },
        "PRV-008": {
            **common,
            "treatment_purposes": purposes,
            "generic_data_use": _contains_phrase(text, _GENERIC_USE_TERMS),
        },
        "PRV-011": {
            **common,
            "holder_rights": rights,
            "generic_rights_reference": _contains_phrase(text, _GENERIC_RIGHT_TERMS),
        },
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

    prv003 = _policy_attribution(contract, candidates)
    if not sufficient:
        prv003["technical_error"] = True
        prv003["confidence"] = "low"
    substantive = _substantive_policy_evidence(contract, candidates)
    if not sufficient:
        substantive = {
            code: {"technical_error": True, "confidence": "low"}
            for code in substantive
        }

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
        # Keep the legacy key to preserve the API evidence shape. Its value means
        # only that a cookie was observed in an inspected response.
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
        **substantive,
        "PRV-101": prv101,
        "PRV-104": prv104,
        "PRV-201": prv201,
        "PRV-301": prv301,
        "PRV-501": prv501,
    }
