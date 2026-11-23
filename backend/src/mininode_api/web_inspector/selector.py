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
    path = urlsplit(url).path.lower().rstrip("/")
    label = _plain(text)
    canonical_paths = (
        "/proteccion-de-datos", "/politica-de-privacidad",
        "/politica-de-proteccion-de-datos", "/privacy-policy",
        "/data-protection", "/legal/privacy",
    )
    if any(path.endswith(value) for value in canonical_paths):
        return 0
    # A qualified URL is thematic even if its short anchor says "Privacy policy".
    filename = path.rsplit("/", 1)[-1]
    if any(filename.startswith(prefix) for prefix in (
        "politica-de-privacidad-", "privacy-policy-",
        "proteccion-de-datos-", "data-protection-",
    )):
        return 1
    if label in {
        "politica de privacidad", "aviso de privacidad",
        "politica de proteccion de datos", "proteccion de datos",
        "privacy policy", "data protection", "privacy notice",
    }:
        return 0
    if any(_has_signal(_plain(path), term) for term in PRIVACY):
        return 1
    if any(_has_signal(label, term) for term in PRIVACY):
        return 1
    return 2


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
