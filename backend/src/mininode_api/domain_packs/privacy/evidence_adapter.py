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
    "PRV-004",
    "PRV-005",
    "PRV-006",
    "PRV-007",
    "PRV-008",
    "PRV-010",
    "PRV-011",
    "PRV-012",
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
_LEGAL_ENTITY_PATTERN = re.compile(
    r"(?:^|\s)(?:[a-z0-9]+\s+){1,6}(?:spa|s a|sa|ltda|limitada|eirl|"
    r"sociedad anonima|sociedad por acciones|llc|inc|corporation|corp)(?:$|\s)"
)
_IDENTIFICATION_CONTEXT_TERMS = (
    "responsable", "razon social", "titular", "somos", "corresponde a",
)
_GENERIC_RESPONSIBLE_TERMS = (
    "la empresa", "nuestra empresa", "nuestra organizacion", "la organizacion",
    "este sitio", "este sitio web", "el responsable", "responsable del sitio",
)
_POLICY_DATE_CONTEXT_TERMS = (
    "ultima actualizacion", "actualizado", "fecha de actualizacion",
    "fecha de publicacion", "vigente desde", "entrada en vigor", "revision",
    "last updated", "updated", "effective date", "effective as of",
    "published", "publication date", "revision", "revised",
)
_POLICY_DATE_PATTERN = re.compile(
    r"\b(?:\d{1,2}(?:[/-]|\s)\d{1,2}(?:[/-]|\s)\d{4}|"
    r"\d{4}(?:-|\s)\d{1,2}(?:-|\s)\d{1,2}|"
    r"\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
    r"septiembre|octubre|noviembre|diciembre)\s+de\s+\d{4}|"
    r"(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|"
    r"noviembre|diciembre)\s+(?:de\s+)?\d{4}|"
    r"(?:january|february|march|april|may|june|july|august|september|october|"
    r"november|december)(?:\s+\d{1,2},?)?\s+\d{4})\b",
    re.I,
)
_POLICY_VERSION_PATTERN = re.compile(
    r"\b(?:version|revision)\s*(?:n(?:o|umero)?\.?\s*)?v?\d+(?:\.\d+)*\b|"
    r"\b(?:politica de privacidad|privacy policy)\s+v\s*\d+(?:\.\d+)*\b",
    re.I,
)
_RIGHTS_CONTEXT_TERMS = (
    "ejercer derechos", "ejercicio de derechos", "derechos de acceso",
    "derechos arcop", "derechos arco", "solicitudes de privacidad",
    "derechos", "privacidad", "proteccion de datos", "datos personales",
    "privacy", "privacy request",
    "data protection", "data subject rights",
)
_CHANNEL_WORDS = (
    "correo", "email", "e mail", "telefono", "phone", "formulario de contacto",
    "direccion postal", "domicilio", "escriba", "contacte", "contactenos",
)
_EMAIL_PATTERN = re.compile(r"\b[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9.-]+\.[a-z]{2,}\b", re.I)
_PHONE_PATTERN = re.compile(r"(?:\+?\d[\d ()-]{6,}\d)")
_CONCRETE_DATA_CATEGORIES = (
    "nombre", "name", "apellido", "surname", "correo", "correo electronico",
    "email", "e mail", "telefono", "phone", "celular", "movil", "direccion",
    "address", "rut", "run", "dni", "documento de identidad", "datos de pago",
    "payment data", "tarjeta de credito", "credit card", "datos bancarios",
    "bank details", "navegacion", "browsing data", "direccion ip", "ip address",
    "cookies", "cookie", "geolocalizacion", "location data", "fecha de nacimiento",
    "date of birth",
)
_GENERIC_PERSONAL_DATA_TERMS = (
    "datos personales", "informacion personal", "personal data", "personal information",
)
_CONCRETE_PROCESSING_PURPOSES = (
    "responder consultas", "atender consultas", "gestionar cuentas",
    "administrar cuentas", "procesar compras", "gestionar compras",
    "procesar pagos", "gestionar pagos", "prestar servicios",
    "proporcionar servicios", "brindar servicios", "dar soporte",
    "prestar soporte", "mejorar la seguridad", "garantizar la seguridad",
    "prevenir fraudes", "enviar comunicaciones", "enviar promociones",
    "realizar marketing", "fines de marketing", "respond inquiries",
    "manage accounts", "process purchases", "process payments",
    "provide services", "provide support", "improve security",
    "prevent fraud", "send communications", "marketing purposes",
)
_GENERIC_PROCESSING_PURPOSE_TERMS = (
    "tratamos datos", "tratamos sus datos", "tratamiento de datos",
    "usamos datos", "usamos sus datos", "uso de datos",
    "procesamos datos", "procesamiento de datos", "process personal data",
    "processing of personal data", "use personal data", "use your data",
)
_RECIPIENT_COMMUNICATION_TERMS = (
    "compartir", "compartimos", "compartirlos", "compartirlas", "compartirse",
    "comunicar", "comunicamos",
    "transferir", "transferimos", "revelar", "revelamos", "proporcionar",
    "proporcionamos", "share", "shared", "sharing", "disclose", "disclosed",
    "transfer", "transferred", "provide", "provided",
)
_GENERIC_RECIPIENT_TERMS = (
    "terceros", "tercero", "third parties", "third party", "proveedores",
    "proveedor", "providers", "provider", "destinatarios", "destinatario",
    "recipients", "recipient", "otras organizaciones", "other organizations",
)
_EXPLICIT_RECIPIENT_CATEGORIES = (
    "proveedores de servicios", "service providers", "encargados",
    "encargado del tratamiento", "procesadores", "processors",
    "proveedores tecnologicos", "technology providers", "servicios de pago",
    "payment services", "proveedores de pago", "payment providers", "hosting",
    "infraestructura", "infrastructure", "analitica", "analytics", "marketing",
    "entidades relacionadas", "related entities", "autoridades", "authorities",
    "socios comerciales", "business partners",
)
_NEGATED_COMMUNICATION_PATTERN = re.compile(
    r"(?:^|\s)(?:(?:no|nunca|jamas)(?:\s+(?:los|las))?|do not|does not|"
    r"don t|doesn t|never)\s+(?:compartir|compartimos|compartirlos|"
    r"compartirlas|comunicar|comunicamos|transferir|transferimos|revelar|"
    r"revelamos|proporcionar|proporcionamos|share|shares|disclose|discloses|"
    r"transfer|transfers|provide|provides)(?:\s|$)"
)
_CONCRETE_DATA_SUBJECT_RIGHTS = (
    ("acceso", "derecho de acceso", "access", "right of access"),
    ("rectificacion", "derecho de rectificacion", "rectify", "rectification"),
    ("supresion", "eliminacion", "derecho de supresion", "delete", "deletion", "erasure"),
    ("oposicion", "derecho de oposicion", "object", "objection"),
    ("portabilidad", "derecho a la portabilidad", "portability"),
    ("limitacion", "limitar el tratamiento", "restriction of processing"),
)
_DATA_SUBJECT_RIGHTS_SECTION_TERMS = (
    "derechos del titular", "derechos de los titulares", "sus derechos sobre sus datos",
    "derechos sobre datos personales", "data subject rights", "your privacy rights",
)
_GENERIC_DATA_SUBJECT_RIGHTS_TERMS = (
    "sus derechos", "ejercer sus derechos", "ejercicio de derechos",
    "derechos del interesado", "your rights", "exercise your rights",
)
_RETENTION_DATA_TERMS = (
    "datos", "informacion", "data", "information", "personal data",
    "personal information",
)
_RETENTION_TERMS = (
    "conservar", "conservacion", "conservamos", "conservaremos", "conservaran",
    "conservarse", "retener", "retencion", "retenemos", "mantener", "mantendremos",
    "almacenar", "almacenamiento", "almacenados", "guardar", "eliminar", "eliminacion",
    "eliminaremos", "eliminados", "retention", "retain", "retained", "storage", "store",
    "stored", "keep", "deletion", "delete", "deleted",
)
_RETENTION_PERIOD_PATTERN = re.compile(
    r"\b(?:durante|por|for)?\s*\d+\s+(?:dias?|mes(?:es)?|anos?|days?|months?|years?)\b"
)
_RETENTION_CRITERIA_PATTERNS = tuple(
    re.compile(pattern) for pattern in (
        r"\b(?:mientras|durante|hasta|while|during|until)\b.{0,80}\b(?:relacion|cuenta|account|servicio|service|contractual|contrato|cerrad[ao]|closed|activ[aoe])\b",
        r"\b(?:mientras|durante|as long as|for as long as|while)\b.{0,80}\b(?:necesari[oa]s?|necessary|needed)\b",
        r"\b(?:plazo|period|periodo|obligacion)\b.{0,80}\b(?:ley|legal|normativa|law|applicable law)\b",
        r"\b(?:required by|exigido por)\b.{0,30}\b(?:law|ley|normativa)\b",
        r"\b(?:despues de|after)\b.{0,60}\b(?:cerrar|cierre|closed?|closing)\b",
        r"\b(?:cuando|when)\b.{0,60}\b(?:dejen? de ser|no longer)\b.{0,30}\b(?:necesari[oa]s?|necessary|needed)\b",
    )
)


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


def _responsible_identification(contract: EvidenceContract, attribution: dict) -> dict:
    """Inspect only the policy selected by PRV-003 and retain no document text."""

    source_urls = (
        attribution.get("source_urls") or []
        if attribution.get("policy_attribution") in {"own", "ambiguous"}
        else []
    )
    if not source_urls:
        return {"responsible_identification": "none", "confidence": "high"}

    selected_url = source_urls[0]
    selected_page = next(
        (
            page
            for page in contract.pages
            if any(
                observed and _public_source_url(observed) == selected_url
                for observed in (page.url, page.requested_url)
            )
        ),
        None,
    )
    evidence = {"source_urls": [selected_url]}
    if selected_page is None:
        return {
            **evidence,
            "responsible_identification": "unknown",
            "technical_error": True,
            "confidence": "low",
        }

    document = _normalize(
        f"{selected_page.title or ''} {selected_page.visible_text or ''}"
    )
    organization_named = any(
        re.search(rf"(?:^|\s){re.escape(term)}(?:$|\s)", document)
        for term in _organization_terms(contract)
    )
    legal_entity_named = bool(
        _LEGAL_ENTITY_PATTERN.search(document)
        and _contains_phrase(document, _IDENTIFICATION_CONTEXT_TERMS)
    )
    if organization_named or legal_entity_named:
        identification = "clear"
        confidence = "high"
    elif _contains_phrase(document, _GENERIC_RESPONSIBLE_TERMS):
        identification = "ambiguous"
        confidence = "medium"
    else:
        identification = "none"
        confidence = "high"
    return {
        **evidence,
        "responsible_identification": identification,
        "confidence": confidence,
    }


def _policy_date_or_version(contract: EvidenceContract, attribution: dict) -> dict:
    """Classify dating/version signals only in PRV-003's selected policy."""

    source_urls = (
        attribution.get("source_urls") or []
        if attribution.get("policy_attribution") in {"own", "ambiguous"}
        else []
    )
    if not source_urls:
        return {"policy_document_reference": "none", "confidence": "high"}

    selected_url = source_urls[0]
    selected_page = next(
        (
            page for page in contract.pages
            if any(
                observed and _public_source_url(observed) == selected_url
                for observed in (page.url, page.requested_url)
            )
        ),
        None,
    )
    evidence = {"source_urls": [selected_url]}
    if selected_page is None:
        return {
            **evidence, "policy_document_reference": "unknown",
            "technical_error": True, "confidence": "low",
        }

    raw_document = f"{selected_page.title or ''}\n{selected_page.visible_text or ''}"
    document = _normalize(raw_document)
    if _POLICY_VERSION_PATTERN.search(document):
        return {
            **evidence, "policy_document_reference": "dated",
            "reference_type": "version", "confidence": "high",
        }
    segments = [
        _normalize(segment)
        for segment in re.split(r"(?<=[.!?;])\s+|[\n\r]+", raw_document)
        if segment.strip()
    ]
    if any(
        _POLICY_DATE_PATTERN.search(segment)
        and _contains_phrase(segment, _POLICY_DATE_CONTEXT_TERMS)
        for segment in segments
    ):
        return {
            **evidence, "policy_document_reference": "dated",
            "reference_type": "date", "confidence": "high",
        }
    if _contains_phrase(document, _POLICY_DATE_CONTEXT_TERMS):
        return {
            **evidence, "policy_document_reference": "ambiguous",
            "confidence": "medium",
        }
    return {**evidence, "policy_document_reference": "none", "confidence": "high"}


def _rights_channel(contract: EvidenceContract, attribution: dict) -> dict:
    """Inspect only PRV-003's selected policy and retain channel classification only."""

    source_urls = (
        attribution.get("source_urls") or []
        if attribution.get("policy_attribution") in {"own", "ambiguous"}
        else []
    )
    if not source_urls:
        return {"rights_channel": "none", "confidence": "high"}

    selected_url = source_urls[0]
    selected_page = next(
        (
            page for page in contract.pages
            if any(
                observed and _public_source_url(observed) == selected_url
                for observed in (page.url, page.requested_url)
            )
        ),
        None,
    )
    evidence = {"source_urls": [selected_url]}
    if selected_page is None:
        return {
            **evidence, "rights_channel": "unknown", "technical_error": True,
            "confidence": "low",
        }

    raw_document = selected_page.visible_text or ""
    segments = [
        segment
        for segment in re.split(r"(?<=[.!?;])\s+|[\n\r]+", raw_document)
        if segment.strip()
    ]

    def has_channel(value: str) -> bool:
        return bool(
            _EMAIL_PATTERN.search(value)
            or _PHONE_PATTERN.search(value)
            or _contains_phrase(value, _CHANNEL_WORDS)
        )

    channel_segments = [
        f"{segments[index - 1]} {segment}" if index else segment
        for index, segment in enumerate(segments)
        if has_channel(segment)
    ]
    explicit = any(
        _contains_phrase(segment, _RIGHTS_CONTEXT_TERMS)
        for segment in channel_segments
    )
    if explicit:
        channel, confidence = "explicit", "high"
    elif channel_segments:
        channel, confidence = "generic", "medium"
    else:
        channel, confidence = "none", "high"
    return {**evidence, "rights_channel": channel, "confidence": confidence}


def _data_categories(contract: EvidenceContract, attribution: dict) -> dict:
    """Classify data categories only in PRV-003's selected inspected policy."""

    source_urls = (
        attribution.get("source_urls") or []
        if attribution.get("policy_attribution") in {"own", "ambiguous"}
        else []
    )
    if not source_urls:
        return {"data_categories": "none", "confidence": "high"}

    selected_url = source_urls[0]
    selected_page = next(
        (
            page for page in contract.pages
            if any(
                observed and _public_source_url(observed) == selected_url
                for observed in (page.url, page.requested_url)
            )
        ),
        None,
    )
    evidence = {"source_urls": [selected_url]}
    if selected_page is None:
        return {
            **evidence, "data_categories": "unknown", "technical_error": True,
            "confidence": "low",
        }

    document = selected_page.visible_text or ""
    if _contains_phrase(document, _CONCRETE_DATA_CATEGORIES):
        category, confidence = "concrete", "high"
    elif _contains_phrase(document, _GENERIC_PERSONAL_DATA_TERMS):
        category, confidence = "generic", "medium"
    else:
        category, confidence = "none", "high"
    return {**evidence, "data_categories": category, "confidence": confidence}


def _processing_purposes(contract: EvidenceContract, attribution: dict) -> dict:
    """Classify purposes only in PRV-003's selected inspected policy."""

    source_urls = (
        attribution.get("source_urls") or []
        if attribution.get("policy_attribution") in {"own", "ambiguous"}
        else []
    )
    if not source_urls:
        return {"processing_purposes": "none", "confidence": "high"}

    selected_url = source_urls[0]
    selected_page = next(
        (
            page for page in contract.pages
            if any(
                observed and _public_source_url(observed) == selected_url
                for observed in (page.url, page.requested_url)
            )
        ),
        None,
    )
    evidence = {"source_urls": [selected_url]}
    if selected_page is None:
        return {
            **evidence, "processing_purposes": "unknown", "technical_error": True,
            "confidence": "low",
        }

    document = selected_page.visible_text or ""
    if _contains_phrase(document, _CONCRETE_PROCESSING_PURPOSES):
        purposes, confidence = "concrete", "high"
    elif _contains_phrase(document, _GENERIC_PROCESSING_PURPOSE_TERMS):
        purposes, confidence = "generic", "medium"
    else:
        purposes, confidence = "none", "high"
    return {**evidence, "processing_purposes": purposes, "confidence": confidence}


def _data_recipients(contract: EvidenceContract, attribution: dict) -> dict:
    """Classify recipients only in PRV-003's selected inspected policy."""

    source_urls = (
        attribution.get("source_urls") or []
        if attribution.get("policy_attribution") in {"own", "ambiguous"}
        else []
    )
    if not source_urls:
        return {"data_recipients": "none", "confidence": "high"}

    selected_url = source_urls[0]
    selected_page = next(
        (
            page for page in contract.pages
            if any(
                observed and _public_source_url(observed) == selected_url
                for observed in (page.url, page.requested_url)
            )
        ),
        None,
    )
    evidence = {"source_urls": [selected_url]}
    if selected_page is None:
        return {
            **evidence, "data_recipients": "unknown", "technical_error": True,
            "confidence": "low",
        }

    segments = re.split(r"(?<=[.!?;])\s+|[\n\r]+", selected_page.visible_text or "")
    communication_segments = [
        segment for segment in segments
        if _contains_phrase(segment, _RECIPIENT_COMMUNICATION_TERMS)
        and _contains_phrase(
            segment, _GENERIC_RECIPIENT_TERMS + _EXPLICIT_RECIPIENT_CATEGORIES
        )
    ]
    negated_segments = [
        segment for segment in communication_segments
        if _NEGATED_COMMUNICATION_PATTERN.search(_normalize(segment))
    ]
    positive_segments = [
        segment for segment in communication_segments
        if segment not in negated_segments
    ]
    if any(
        _contains_phrase(segment, _EXPLICIT_RECIPIENT_CATEGORIES)
        for segment in positive_segments
    ):
        recipients, confidence = "explicit", "high"
    elif positive_segments:
        recipients, confidence = "generic", "medium"
    elif negated_segments:
        recipients, confidence = "explicit_none", "high"
    else:
        recipients, confidence = "none", "high"
    return {**evidence, "data_recipients": recipients, "confidence": confidence}


def _data_subject_rights(contract: EvidenceContract, attribution: dict) -> dict:
    """Classify rights only in PRV-003's selected inspected policy."""

    source_urls = (
        attribution.get("source_urls") or []
        if attribution.get("policy_attribution") in {"own", "ambiguous"}
        else []
    )
    if not source_urls:
        return {"data_subject_rights": "none", "confidence": "high"}

    selected_url = source_urls[0]
    selected_page = next(
        (
            page for page in contract.pages
            if any(
                observed and _public_source_url(observed) == selected_url
                for observed in (page.url, page.requested_url)
            )
        ),
        None,
    )
    evidence = {"source_urls": [selected_url]}
    if selected_page is None:
        return {
            **evidence, "data_subject_rights": "unknown", "technical_error": True,
            "confidence": "low",
        }

    document = selected_page.visible_text or ""
    concrete_count = sum(
        _contains_phrase(document, set(equivalents))
        for equivalents in _CONCRETE_DATA_SUBJECT_RIGHTS
    )
    explicit_section = _contains_phrase(document, _DATA_SUBJECT_RIGHTS_SECTION_TERMS)
    generic_reference = _contains_phrase(document, _GENERIC_DATA_SUBJECT_RIGHTS_TERMS)
    if concrete_count >= 2:
        rights, confidence = "multiple", "high"
    elif explicit_section and concrete_count:
        rights, confidence = "section", "high"
    elif concrete_count == 1:
        rights, confidence = "single", "medium"
    elif explicit_section or generic_reference:
        rights, confidence = "generic", "medium"
    else:
        rights, confidence = "none", "high"
    return {**evidence, "data_subject_rights": rights, "confidence": confidence}


def _data_retention(contract: EvidenceContract, attribution: dict) -> dict:
    """Classify retention language only in PRV-003's selected inspected policy."""

    source_urls = (
        attribution.get("source_urls") or []
        if attribution.get("policy_attribution") in {"own", "ambiguous"}
        else []
    )
    if not source_urls:
        return {"data_retention": "none", "confidence": "high"}

    selected_url = source_urls[0]
    selected_page = next(
        (
            page for page in contract.pages
            if any(
                observed and _public_source_url(observed) == selected_url
                for observed in (page.url, page.requested_url)
            )
        ),
        None,
    )
    evidence = {"source_urls": [selected_url]}
    if selected_page is None:
        return {
            **evidence, "data_retention": "unknown", "technical_error": True,
            "confidence": "low",
        }

    segments = re.split(r"(?<=[.!?;])\s+|[\n\r]+", selected_page.visible_text or "")
    contextual = [
        _normalize(segment) for segment in segments
        if _contains_phrase(segment, _RETENTION_DATA_TERMS)
        and _contains_phrase(segment, _RETENTION_TERMS)
    ]
    explicit = any(
        _RETENTION_PERIOD_PATTERN.search(segment)
        or any(pattern.search(segment) for pattern in _RETENTION_CRITERIA_PATTERNS)
        for segment in contextual
    )
    if explicit:
        retention, confidence = "explicit", "high"
    elif contextual:
        retention, confidence = "generic", "medium"
    else:
        retention, confidence = "none", "high"
    return {**evidence, "data_retention": retention, "confidence": confidence}


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

    prv004 = _policy_date_or_version(contract, prv003)
    prv005 = _responsible_identification(contract, prv003)
    prv006 = _rights_channel(contract, prv003)
    prv007 = _data_categories(contract, prv003)
    prv008 = _processing_purposes(contract, prv003)
    prv010 = _data_recipients(contract, prv003)
    prv011 = _data_subject_rights(contract, prv003)
    prv012 = _data_retention(contract, prv003)

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
        "PRV-004": prv004,
        "PRV-005": prv005,
        "PRV-006": prv006,
        "PRV-007": prv007,
        "PRV-008": prv008,
        "PRV-010": prv010,
        "PRV-011": prv011,
        "PRV-012": prv012,
        "PRV-101": prv101,
        "PRV-104": prv104,
        "PRV-201": prv201,
        "PRV-301": prv301,
        "PRV-501": prv501,
    }
