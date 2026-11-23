"""Deterministic selection of a small, relevant same-host page set."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from .fetcher import normalize_url
from .models import LinkEvidence

PRIVACY = ("privacidad", "privacy", "politica de privacidad", "proteccion de datos", "datos personales")
CONTACT = ("contacto", "contact", "contactanos")
ADDITIONAL = (
    "registro", "registrarse", "inscripcion", "suscripcion", "newsletter", "cotizar",
    "cotizacion", "reserva", "reservar", "compra", "comprar", "checkout", "postulacion",
    "trabaja con nosotros", "empleo",
    "signup", "sign up", "subscribe", "start free", "free trial", "try free",
    "prueba gratis", "prueba gratuita", "request demo", "get a demo", "book a demo",
    "schedule a demo", "solicita demo", "solicitar demo", "agenda demo", "agendar demo",
    "request a meeting", "book a meeting", "schedule a meeting", "talk to sales",
    "talk to an expert",
)
EXCLUDED_WORDS = ("blog", "noticias", "news", "tags", "categorias", "paginacion", "archives")
EXCLUDED_EXTENSIONS = (".pdf", ".zip", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg")


@dataclass(frozen=True)
class PageCandidate:
    """A classified page that may be selected by a planning policy."""

    url: str
    category: Literal["privacy", "contact", "action"]
    rank: tuple[str, ...]


def _plain(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[\W_]+", " ", value).strip()


def _has_signal(text: str, signal: str) -> bool:
    return f" {_plain(signal)} " in f" {text} "


def policy_candidate_priority(url: str, text: str = "") -> int:
    """Prefer canonical general privacy documents over thematic or commercial pages.

    Only public link text and URL paths are used; no host-specific exemptions.
    A long, topic-qualified policy label is not an exact general-policy label.
    """
    path = urlsplit(url).path.lower().strip("/")
    label = _plain(text)
    segments = path.split("/") if path else []

    # Generic names are meaningful only at the root (or after a language
    # locale). A nested /california/privacy-policy is not a general policy.
    document_names = {
        "privacy-policy", "privacy-notice", "politica-de-privacidad",
        "politica-de-proteccion-de-datos", "aviso-de-privacidad",
    }
    general_names = {
        "privacy", "privacidad", "proteccion-de-datos", "data-protection",
    }
    languages = {
        "en", "es", "pt", "fr", "de", "it", "nl", "ca",
        "ja", "ko", "zh", "pl", "sv",
    }
    is_locale = bool(segments and (
        segments[0] in languages or
        any(re.fullmatch(fr"{language}-[a-z]{{2}}", segments[0]) for language in languages)
    ))
    relative = segments[1:] if is_locale else segments
    locale_offset = 1 if is_locale else 0

    # The label is a weak signal: an ambiguous "Data Protection" anchor
    # cannot prove that a service page is a legal privacy declaration.
    commercial_signals = (
        "privacy web", "servicios", "services", "consultoria", "consulting",
        "soluciones", "solutions", "software", "productos", "products",
        "diagnostico", "assessment", "compliance",
    )
    if any(_has_signal(label, term) for term in commercial_signals):
        return 6

    # Explicit legal-document directories carry more weight than ambiguous
    # generic paths (e.g. commercial /privacy). Limit this to the root or
    # one language prefix: /california/legal/privacy-policy stays thematic.
    legal_directories = {"legal", "policies", "politicas"}
    if (
        len(relative) == 2
        and relative[0] in legal_directories
        and relative[1] in (document_names | general_names)
    ):
        return 0 + locale_offset
    if len(relative) == 1 and relative[0] in document_names:
        return 0 + locale_offset
    if len(relative) == 1 and relative[0] in general_names:
        return 2 + locale_offset

    # Regional, thematic and nested pages never outrank a general document,
    # even when their anchor happens to say "Privacy policy".
    if any(_has_signal(_plain(path), term) for term in PRIVACY):
        return 4
    if any(_has_signal(label, term) for term in PRIVACY):
        return 5
    return 7


def candidate_identity(url: str) -> str:
    """Return selector-only identity, treating a non-root trailing slash as optional.

    The normalized URL itself remains the URL that is requested. Query strings
    are preserved, so functionally different URLs retain different identities.
    """

    parsed = urlsplit(url)
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, ""))


def classify_page_candidates(
    home_url: str,
    links: Iterable[LinkEvidence | dict[str, str] | str],
) -> list[PageCandidate]:
    """Normalize and classify every relevant same-host page deterministically."""

    home = normalize_url(home_url)
    hostname = urlsplit(home).hostname
    by_identity: dict[str, tuple[str, str, str]] = {}
    home_identity = candidate_identity(home)
    for link in links:
        if isinstance(link, str):
            raw_url, text = link, ""
        elif isinstance(link, dict):
            raw_url, text = link.get("url", ""), link.get("text", "")
        else:
            raw_url, text = link.url, link.text
        try:
            url = normalize_url(raw_url)
        except (TypeError, ValueError):
            continue
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or parsed.hostname != hostname:
            continue
        if parsed.path.lower().endswith(EXCLUDED_EXTENSIONS):
            continue
        signal = _plain(f"{text} {parsed.path} {parsed.query}")
        if any(_has_signal(signal, word) for word in EXCLUDED_WORDS):
            continue
        identity = candidate_identity(url)
        if identity == home_identity:
            continue
        # Input order cannot decide which spelling survives: retain the
        # lexicographically smallest normalized URL and its associated signal.
        previous = by_identity.get(identity)
        if previous is None or url < previous[0]:
            by_identity[identity] = (url, signal, text)

    candidates: list[PageCandidate] = []
    categories = (("privacy", PRIVACY), ("contact", CONTACT), ("action", ADDITIONAL))
    for url, signal, text in sorted(by_identity.values()):
        for category, terms in categories:
            if any(_has_signal(signal, term) for term in terms):
                candidates.append(PageCandidate(url, category, (str(policy_candidate_priority(url, text)), url) if category == "privacy" else (url,)))
                break
    return candidates


def select_pages(home_url: str, links: Iterable[LinkEvidence | dict[str, str] | str], limit: int = 5) -> list[str]:
    """Select home, privacy, contact, then at most two relevant action pages."""

    if limit <= 0:
        return []
    home = normalize_url(home_url)
    candidates = classify_page_candidates(home, links)

    selected = [home]
    used = {home}
    for category in ("privacy", "contact"):
        match = min((item for item in candidates if item.category == category),
                    key=lambda item: item.rank, default=None)
        if match and len(selected) < limit:
            selected.append(match.url)
            used.add(match.url)
    additional = [item.url for item in candidates if item.category == "action" and item.url not in used]
    selected.extend(additional[: min(2, max(0, limit - len(selected)))])
    return selected[:limit]
