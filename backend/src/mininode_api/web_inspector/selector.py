"""Deterministic selection of up to five same-host page candidates."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import PurePosixPath
import re
from urllib.parse import urlsplit

from .fetcher import normalize_url
from .models import LinkEvidence

PRIVACY = ("privacidad", "privacy", "protección de datos", "proteccion de datos", "datos personales")
CONTACT = ("contacto", "contact", "contáctanos", "contactanos")
ADDITIONAL = (
    "registro", "registrarse", "inscripción", "inscripcion", "suscripción", "suscripcion", "newsletter",
    "cotizar", "cotización", "cotizacion", "reserva", "reservar", "compra", "comprar", "checkout",
    "postulación", "postulacion", "trabaja con nosotros", "empleo",
)
NOISY = ("blog", "noticias", "news", "tags", "categorías", "categorias", "paginación", "paginacion", "archives")
EXCLUDED_SUFFIXES = {".pdf", ".zip", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}


def select_pages(home_url: str, links: Iterable[LinkEvidence], limit: int = 5) -> list[str]:
    """Return home, one privacy page, one contact page, and two useful extras."""

    home = normalize_url(home_url)
    hostname = urlsplit(home).hostname
    candidates: list[tuple[str, str]] = []
    seen = {home}
    for link in links:
        try:
            url = normalize_url(link.url)
        except ValueError:
            continue
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or parsed.hostname != hostname or url in seen:
            continue
        if PurePosixPath(parsed.path.lower()).suffix in EXCLUDED_SUFFIXES:
            continue
        signal = f"{link.text} {parsed.path} {parsed.query}".casefold()
        if any(re.search(rf"\b{re.escape(term)}\b", signal) for term in NOISY):
            continue
        candidates.append((url, signal))
        seen.add(url)

    def ranked(signals: tuple[str, ...]) -> list[str]:
        return sorted(url for url, text in candidates if any(signal in text for signal in signals))

    chosen = [home]
    privacy = ranked(PRIVACY)
    contact = ranked(CONTACT)
    if privacy:
        chosen.append(privacy[0])
    if contact and contact[0] not in chosen:
        chosen.append(contact[0])
    extras = [url for url in ranked(ADDITIONAL) if url not in chosen]
    chosen.extend(extras[:2])
    return chosen[: min(limit, 5)]
