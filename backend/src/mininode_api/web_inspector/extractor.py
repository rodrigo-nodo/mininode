"""Deterministic extraction of observable facts from already-fetched HTML."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from .fetcher import normalize_url
from .models import (
    CheckboxEvidence,
    ContactEvidence,
    CookieEvidence,
    EvidenceContract,
    FieldEvidence,
    FormEvidence,
    InspectionEvidence,
    InspectionFetchResult,
    LinkEvidence,
    PageEvidence,
    TargetEvidence,
    TransportEvidence,
)

NEARBY_TEXT_LIMIT = 500
PRIVACY_SIGNALS = ("privacidad", "privacy", "protección de datos", "proteccion de datos", "datos personales")
PREFERENCE_SIGNALS = (
    "preferencias de cookies",
    "preferencias de cookie",
    "configuración de cookies",
    "configuracion de cookies",
    "gestionar cookies",
    "administrar cookies",
    "cookie settings",
    "manage cookies",
)
EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.-])")
PHONE_RE = re.compile(
    r"(?<!\w)(?:\+\d{1,3}(?:[\s.-]\d{1,4}){2,4}|\(?\d{2,4}\)?[\s.-]\d{3,4}[\s.-]\d{3,4})(?!\w)"
)


def _clean_text(value: str, limit: int | None = None) -> str:
    text = " ".join(value.split())
    return text if limit is None else text[:limit]


def _absolute_url(source_url: str, value: str) -> str:
    return normalize_url(urljoin(source_url, value))


def _label(element: Tag, soup: BeautifulSoup) -> str:
    identifier = element.get("id")
    if identifier:
        explicit = soup.find("label", attrs={"for": identifier})
        if explicit:
            return _clean_text(explicit.get_text(" ", strip=True))
    parent = element.find_parent("label")
    if parent:
        return _clean_text(parent.get_text(" ", strip=True))
    return _clean_text(str(element.get("aria-label") or element.get("placeholder") or ""))


def _privacy_link(tag: Tag) -> bool:
    signal_text = f"{tag.get_text(' ', strip=True)} {tag.get('href', '')}".casefold()
    return any(signal in signal_text for signal in PRIVACY_SIGNALS)


def extract_page(
    html: str,
    source_url: str,
    *,
    status_code: int = 200,
    content_type: str = "text/html",
    set_cookie_names: list[str] | None = None,
) -> tuple[PageEvidence, list[LinkEvidence], list[FormEvidence], CookieEvidence, list[ContactEvidence], bool]:
    """Parse untrusted HTML as data; no resources or scripts are executed."""

    soup = BeautifulSoup(html, "lxml")
    title_tag = soup.find("title")
    page = PageEvidence(source_url, status_code, _clean_text(title_tag.get_text(" ")) if title_tag else None, content_type)

    links: list[LinkEvidence] = []
    seen_links: set[str] = set()
    for tag in soup.find_all("a", href=True):
        href = str(tag["href"]).strip()
        if not href or href.startswith("#") or urlsplit(href).scheme.lower() in {"javascript", "data", "mailto", "tel"}:
            continue
        try:
            absolute = _absolute_url(source_url, href)
        except ValueError:
            continue
        text = _clean_text(tag.get_text(" ", strip=True))
        if absolute not in seen_links and text:
            links.append(LinkEvidence(absolute, text, source_url))
            seen_links.add(absolute)

    forms: list[FormEvidence] = []
    for form in soup.find_all("form"):
        fields: list[FieldEvidence] = []
        checkboxes: list[CheckboxEvidence] = []
        for element in form.find_all(["input", "select", "textarea"]):
            logical_type = element.name if element.name != "input" else str(element.get("type", "text")).lower()
            name = str(element.get("name", ""))
            label = _label(element, soup)
            if logical_type == "checkbox":
                checkboxes.append(CheckboxEvidence(name, label))
            elif logical_type not in {"hidden", "submit", "button", "reset", "image"}:
                fields.append(FieldEvidence(name, logical_type, label, element.has_attr("required")))
        context = form.parent if isinstance(form.parent, Tag) else form
        privacy_links = sorted(
            {_absolute_url(source_url, str(tag["href"])) for tag in context.find_all("a", href=True) if _privacy_link(tag)}
        )
        forms.append(
            FormEvidence(
                source_url=source_url,
                action=_absolute_url(source_url, str(form.get("action") or source_url)),
                method=str(form.get("method", "get")).lower(),
                fields=fields,
                checkboxes=checkboxes,
                nearby_text=_clean_text(context.get_text(" ", strip=True), NEARBY_TEXT_LIMIT),
                privacy_links=privacy_links,
            )
        )

    for unwanted in soup.find_all(["script", "style", "template"]):
        unwanted.decompose()
    visible_text = _clean_text(soup.get_text(" ", strip=True))
    lower_text = visible_text.casefold()
    contacts: list[ContactEvidence] = []
    seen_contacts: set[tuple[str, str]] = set()

    def add_contact(kind: str, value: str) -> None:
        cleaned = value.strip()
        key = (kind, cleaned.casefold())
        if cleaned and key not in seen_contacts:
            contacts.append(ContactEvidence(kind, cleaned, source_url))
            seen_contacts.add(key)

    for tag in soup.find_all("a", href=True):
        href = str(tag["href"])
        if href.lower().startswith("mailto:"):
            add_contact("email", href[7:].split("?", 1)[0])
        elif href.lower().startswith("tel:"):
            add_contact("phone", href[4:].split("?", 1)[0])
    for email in EMAIL_RE.findall(visible_text):
        add_contact("email", email)
    for phone in PHONE_RE.findall(visible_text):
        digits = re.sub(r"\D", "", phone)
        if 7 <= len(digits) <= 15:
            add_contact("phone", _clean_text(phone))

    cookie_names = sorted(set(set_cookie_names or []))
    banner_detected = "cookie" in lower_text
    cookies = CookieEvidence(
        detected=bool(cookie_names),
        set_cookie_names=cookie_names,
        banner_detected=banner_detected,
        preferences_detected=any(signal in lower_text for signal in PREFERENCE_SIGNALS),
    )
    mixed_content = False
    if urlsplit(source_url).scheme == "https":
        resource_attributes = (("img", "src"), ("script", "src"), ("link", "href"), ("iframe", "src"), ("source", "src"))
        mixed_content = any(
            str(tag.get(attribute, "")).lower().startswith("http://")
            for tag_name, attribute in resource_attributes
            for tag in BeautifulSoup(html, "lxml").find_all(tag_name)
        )
    return page, links, forms, cookies, contacts, mixed_content


def build_evidence(fetch_result: InspectionFetchResult) -> EvidenceContract:
    """Compose the evidence contract from safe, already-fetched page results."""

    pages: list[PageEvidence] = []
    links: list[LinkEvidence] = []
    forms: list[FormEvidence] = []
    contacts: list[ContactEvidence] = []
    cookie_names: set[str] = set()
    banner = preferences = False
    mixed_observations: list[bool] = []
    successful = [page for page in fetch_result.pages if not page.error and page.html is not None and page.final_url]
    for fetched in successful:
        extracted = extract_page(
            fetched.html or "",
            fetched.final_url or fetched.requested_url,
            status_code=fetched.status_code or 0,
            content_type=fetched.content_type or "",
            set_cookie_names=fetched.set_cookie_names,
        )
        page, page_links, page_forms, page_cookies, page_contacts, mixed = extracted
        pages.append(page)
        links.extend(page_links)
        forms.extend(page_forms)
        contacts.extend(page_contacts)
        cookie_names.update(page_cookies.set_cookie_names)
        banner = banner or page_cookies.banner_detected
        preferences = preferences or page_cookies.preferences_detected
        if urlsplit(page.url).scheme == "https":
            mixed_observations.append(mixed)

    final_url = successful[0].final_url if successful else fetch_result.target_url
    requested_scheme = urlsplit(fetch_result.target_url).scheme
    final_scheme = urlsplit(final_url or fetch_result.target_url).scheme
    errors = [{"code": error.code, "message": error.message, "url": error.url} for error in fetch_result.errors]
    unique_links = list({(link.url, link.text, link.source_url): link for link in links}.values())
    unique_contacts = list({(item.type, item.value.casefold(), item.source_url): item for item in contacts}.values())
    return EvidenceContract(
        target=TargetEvidence(fetch_result.target_url, final_url or fetch_result.target_url, urlsplit(final_url or fetch_result.target_url).hostname or ""),
        inspection=InspectionEvidence(fetch_result.pages_requested, len(pages), fetch_result.limited, errors),
        pages=pages,
        transport=TransportEvidence(
            https=final_scheme == "https",
            tls_valid=True if final_scheme == "https" and bool(successful) else None,
            http_redirects_to_https=(requested_scheme == "http" and final_scheme == "https") if successful else None,
            mixed_content=any(mixed_observations) if mixed_observations else None,
        ),
        links=unique_links,
        forms=forms,
        cookies=CookieEvidence(bool(cookie_names), sorted(cookie_names), banner, preferences),
        contacts=unique_contacts,
    )
