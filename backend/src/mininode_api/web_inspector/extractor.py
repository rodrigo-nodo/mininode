"""Static extraction of bounded observations from untrusted HTML data."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from .models import (
    CheckboxEvidence, ContactEvidence, CookieEvidence, EvidenceContract, FieldEvidence,
    FormEvidence, InspectionEvidence, InspectionFetchResult, LinkEvidence, PageEvidence,
    TargetEvidence, TransportEvidence,
)

PRIVACY_SIGNALS = ("privacidad", "privacy", "protección de datos", "proteccion de datos", "datos personales")
PREFERENCE_SIGNALS = (
    "preferencias de cookies", "configuración de cookies", "configuracion de cookies",
    "gestionar cookies", "administrar cookies", "cookie settings", "manage cookies",
)
COOKIE_BANNER_SIGNALS = (
    "usamos cookies", "utilizamos cookies", "uso de cookies", "aceptar cookies",
    "aceptar todas las cookies", "cookie consent", "we use cookies",
)
TECHNICAL_INPUT_TYPES = {"hidden", "submit", "button", "reset", "image"}
EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
PHONE_RE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{5,}\d(?!\w)")


@dataclass
class PageExtraction:
    title: str | None
    links: list[LinkEvidence] = field(default_factory=list)
    forms: list[FormEvidence] = field(default_factory=list)
    contacts: list[ContactEvidence] = field(default_factory=list)
    banner_detected: bool = False
    preferences_detected: bool = False
    mixed_content: bool = False


def _text(tag: Tag) -> str:
    return " ".join(tag.get_text(" ", strip=True).split())


def _label(control: Tag, soup: BeautifulSoup) -> str:
    identifier = control.get("id")
    if identifier:
        explicit = soup.find("label", attrs={"for": identifier})
        if isinstance(explicit, Tag):
            return _text(explicit)
    parent = control.find_parent("label")
    if isinstance(parent, Tag):
        return _text(parent)
    return str(control.get("aria-label") or control.get("placeholder") or "").strip()


def _links(soup: BeautifulSoup, source_url: str) -> list[LinkEvidence]:
    result: list[LinkEvidence] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"]).strip()
        if not href or href.startswith("#") or urlsplit(href).scheme.lower() in {"javascript", "data", "mailto", "tel"}:
            continue
        url = urljoin(source_url, href)
        if url not in seen:
            seen.add(url)
            result.append(LinkEvidence(url, _text(anchor), source_url))
    return result


def _forms(soup: BeautifulSoup, source_url: str) -> list[FormEvidence]:
    results: list[FormEvidence] = []
    for form in soup.find_all("form"):
        fields: list[FieldEvidence] = []
        checkboxes: list[CheckboxEvidence] = []
        for control in form.find_all(["input", "select", "textarea"]):
            kind = str(control.get("type") or ("select" if control.name == "select" else "textarea" if control.name == "textarea" else "text")).lower()
            if kind in TECHNICAL_INPUT_TYPES:
                continue
            name = str(control.get("name") or "")
            label = _label(control, soup)
            if kind == "checkbox":
                checkboxes.append(CheckboxEvidence(name, label))
            else:
                fields.append(FieldEvidence(name, kind, label, control.has_attr("required")))
        nearby = _text(form)[:500]
        privacy_links: list[LinkEvidence] = []
        for anchor in form.find_all("a", href=True):
            signal = f"{_text(anchor)} {anchor['href']}".lower()
            if any(term in signal for term in PRIVACY_SIGNALS):
                privacy_links.append(LinkEvidence(urljoin(source_url, str(anchor["href"])), _text(anchor), source_url))
        results.append(FormEvidence(
            source_url=source_url,
            action=urljoin(source_url, str(form.get("action") or source_url)),
            method=str(form.get("method") or "get").lower(),
            fields=fields,
            checkboxes=checkboxes,
            nearby_text=nearby,
            privacy_links=privacy_links,
        ))
    return results


def _contacts(soup: BeautifulSoup, source_url: str) -> list[ContactEvidence]:
    emails: set[str] = set()
    phones: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        if href.lower().startswith("mailto:"):
            value = href[7:].split("?", 1)[0].strip()
            if EMAIL_RE.fullmatch(value):
                emails.add(value)
        elif href.lower().startswith("tel:"):
            value = href[4:].strip()
            if sum(character.isdigit() for character in value) >= 7:
                phones.add(value)
    visible = _text(soup)
    emails.update(EMAIL_RE.findall(visible))
    for match in PHONE_RE.findall(visible):
        value = match.strip()
        if sum(character.isdigit() for character in value) >= 7:
            phones.add(value)
    return [ContactEvidence(source_url, email=value) for value in sorted(emails)] + [ContactEvidence(source_url, phone=value) for value in sorted(phones)]


def extract_page(html: str, source_url: str) -> PageExtraction:
    """Parse HTML as inert data; this function performs no I/O or execution."""

    soup = BeautifulSoup(html, "lxml")
    title_tag = soup.find("title")
    title = _text(title_tag) if isinstance(title_tag, Tag) else None
    mixed = urlsplit(source_url).scheme == "https" and any(
        str(tag.get(attribute, "")).lower().startswith("http://")
        for tag_name, attribute in (("img", "src"), ("script", "src"), ("link", "href"), ("iframe", "src"), ("source", "src"))
        for tag in soup.find_all(tag_name)
    )
    for removable in soup.find_all(["script", "style", "template"]):
        removable.decompose()
    visible = _text(soup).lower()
    return PageExtraction(
        title=title,
        links=_links(soup, source_url),
        forms=_forms(soup, source_url),
        contacts=_contacts(soup, source_url),
        banner_detected=any(signal in visible for signal in COOKIE_BANNER_SIGNALS),
        preferences_detected=any(signal in visible for signal in PREFERENCE_SIGNALS),
        mixed_content=mixed,
    )


def build_evidence(fetch_result: InspectionFetchResult) -> EvidenceContract:
    """Build Evidence Contract v0.1 from an existing bounded fetch result."""

    pages: list[PageEvidence] = []
    links: list[LinkEvidence] = []
    forms: list[FormEvidence] = []
    contacts: list[ContactEvidence] = []
    cookie_names: list[str] = []
    banner = preferences = False
    https_mixed: list[bool] = []
    successful = [page for page in fetch_result.pages if page.error is None and page.html is not None and page.final_url]
    for page in successful:
        assert page.final_url is not None and page.html is not None
        extracted = extract_page(page.html, page.final_url)
        pages.append(PageEvidence(page.final_url, page.status_code, extracted.title, page.content_type))
        links.extend(extracted.links)
        forms.extend(extracted.forms)
        contacts.extend(extracted.contacts)
        banner |= extracted.banner_detected
        preferences |= extracted.preferences_detected
        for name in page.set_cookie_names:
            if name not in cookie_names:
                cookie_names.append(name)
        if urlsplit(page.final_url).scheme == "https":
            https_mixed.append(extracted.mixed_content)

    final_url = successful[0].final_url if successful else next((page.final_url for page in fetch_result.pages if page.final_url), None)
    requested_scheme = urlsplit(fetch_result.target_url).scheme.lower()
    final_scheme = urlsplit(final_url).scheme.lower() if final_url else ""
    redirects_to_https = (final_scheme == "https") if requested_scheme == "http" and final_url else None
    errors = [{"code": error.code, "message": error.message, "url": error.url} for error in fetch_result.errors]
    return EvidenceContract(
        target=TargetEvidence(fetch_result.target_url, final_url, urlsplit(final_url or fetch_result.target_url).hostname),
        inspection=InspectionEvidence(fetch_result.pages_requested, len(successful), fetch_result.limited, errors),
        pages=pages,
        transport=TransportEvidence(
            https=(final_scheme == "https") if final_url else None,
            tls_valid=True if any(page.tls_valid is True for page in successful) else None,
            http_redirects_to_https=redirects_to_https,
            mixed_content=any(https_mixed) if https_mixed else None,
        ),
        links=links,
        forms=forms,
        cookies=CookieEvidence(bool(cookie_names), cookie_names, banner, preferences),
        contacts=contacts,
    )
