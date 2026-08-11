"""Deterministic selection of a small, relevant same-host page set."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from urllib.parse import urlsplit

from .fetcher import normalize_url
from .models import LinkEvidence

PRIVACY = ("privacidad", "privacy", "politica de privacidad", "proteccion de datos", "datos personales")
CONTACT = ("contacto", "contact", "contactanos")
ADDITIONAL = (
    "registro", "registrarse", "inscripcion", "suscripcion", "newsletter", "cotizar",
    "cotizacion", "reserva", "reservar", "compra", "comprar", "checkout", "postulacion",
    "trabaja con nosotros", "empleo",
)
EXCLUDED_WORDS = ("blog", "noticias", "news", "tags", "categorias", "paginacion", "archives")
EXCLUDED_EXTENSIONS = (".pdf", ".zip", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg")


def _plain(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[\W_]+", " ", value).strip()


def _has_signal(text: str, signal: str) -> bool:
    return f" {_plain(signal)} " in f" {text} "


def select_pages(home_url: str, links: Iterable[LinkEvidence | dict[str, str] | str], limit: int = 5) -> list[str]:
    """Select home, privacy, contact, then at most two relevant action pages."""

    if limit <= 0:
        return []
    home = normalize_url(home_url)
    hostname = urlsplit(home).hostname
    candidates: list[tuple[str, str]] = []
    seen = {home}
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
        if parsed.path.lower().endswith(EXCLUDED_EXTENSIONS) or url in seen:
            continue
        signal = _plain(f"{text} {parsed.path} {parsed.query}")
        if any(_has_signal(signal, word) for word in EXCLUDED_WORDS):
            continue
        seen.add(url)
        candidates.append((url, signal))

    def first_matching(signals: tuple[str, ...], used: set[str]) -> str | None:
        matches = [(url, signal) for url, signal in candidates if url not in used and any(_has_signal(signal, term) for term in signals)]
        return min(matches, key=lambda item: item[0])[0] if matches else None

    selected = [home]
    used = {home}
    for signals in (PRIVACY, CONTACT):
        match = first_matching(signals, used)
        if match and len(selected) < limit:
            selected.append(match)
            used.add(match)
    additional = sorted(url for url, signal in candidates if url not in used and any(_has_signal(signal, term) for term in ADDITIONAL))
    selected.extend(additional[: min(2, max(0, limit - len(selected)))])
    return selected[:limit]
