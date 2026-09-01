"""Static extraction of bounded observations from untrusted HTML data."""

from __future__ import annotations

import re
from copy import deepcopy
from collections.abc import Iterable
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from .fetcher import normalize_url
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
CONTENT_TEXT_LIMIT = 12000
FORM_HEADING_LIMIT = 160
FORM_LEGEND_LIMIT = 160
FORM_INTRODUCTORY_TEXT_LIMIT = 300
FORM_SUBMIT_TEXT_LIMIT = 120
_FORM_LOCAL_SIBLING_LIMIT = 3
_SUBSTANTIVE_TEXT_LENGTH = 40
_CONTENT_NOISE_ELEMENTS = ("script", "style", "template", "header", "nav", "footer", "aside", "form")


@dataclass
class PageExtraction:
    title: str | None
    visible_text: str = ""
    links: list[LinkEvidence] = field(default_factory=list)
    forms: list[FormEvidence] = field(default_factory=list)
    contacts: list[ContactEvidence] = field(default_factory=list)
    banner_detected: bool = False
    preferences_detected: bool = False
    mixed_content: bool = False
    content_text: str | None = None


def _text(tag: Tag) -> str:
    return " ".join(tag.get_text(" ", strip=True).split())


def _clean_content_text(soup: BeautifulSoup) -> str | None:
    """Return a bounded main-content sample without mutating extraction DOM."""

    mains = soup.find_all("main")
    candidate = mains[0] if len(mains) == 1 else None
    if not isinstance(candidate, Tag) or len(_text(candidate)) < _SUBSTANTIVE_TEXT_LENGTH:
        substantive_articles = [
            article for article in soup.find_all("article")
            if isinstance(article, Tag) and len(_text(article)) >= _SUBSTANTIVE_TEXT_LENGTH
        ]
        candidate = max(substantive_articles, key=lambda article: len(_text(article)), default=None)

    def cleaned_text(root: Tag) -> str:
        clean_root = deepcopy(root)
        for removable in clean_root.find_all(_CONTENT_NOISE_ELEMENTS):
            removable.decompose()
        return _text(clean_root)

    content = cleaned_text(candidate) if isinstance(candidate, Tag) else ""
    if len(content) < _SUBSTANTIVE_TEXT_LENGTH:
        fallback = soup.body if isinstance(soup.body, Tag) else soup
        content = cleaned_text(fallback)
    return content[:CONTENT_TEXT_LIMIT] if len(content) >= _SUBSTANTIVE_TEXT_LENGTH else None


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


def _bounded_text(tag: Tag, limit: int) -> str | None:
    value = _text(tag)
    return value[:limit] if value else None


def _external_form_context(form: Tag) -> tuple[str | None, str | None]:
    """Return only context from a small, unambiguous preceding-sibling window."""

    parent = form.parent
    if not isinstance(parent, Tag) or parent.name in {"body", "html", "header", "nav", "footer"}:
        return None, None

    heading: str | None = None
    introduction: str | None = None
    inspected = 0
    for sibling in form.previous_siblings:
        if not isinstance(sibling, Tag):
            continue
        if sibling.name == "form":
            # Text floating between two forms is not sufficiently associated.
            return None, None
        if sibling.name in {f"h{level}" for level in range(1, 7)}:
            heading = _bounded_text(sibling, FORM_HEADING_LIMIT)
            break
        if sibling.name not in {"p", "small", "div"} or sibling.find("form"):
            break
        inspected += 1
        if inspected > _FORM_LOCAL_SIBLING_LIMIT:
            break
        if introduction is None and not sibling.find(
            ["input", "select", "textarea", "button", "label", "legend"]
        ):
            introduction = _bounded_text(sibling, FORM_INTRODUCTORY_TEXT_LIMIT)
    return heading, introduction


def _form_heading(form: Tag) -> str | None:
    internal = form.find([f"h{level}" for level in range(1, 7)])
    if isinstance(internal, Tag):
        value = _bounded_text(internal, FORM_HEADING_LIMIT)
        if value:
            return value
    return _external_form_context(form)[0]


def _form_introductory_text(form: Tag) -> str | None:
    for candidate in form.find_all(True):
        if candidate.name in {"input", "select", "textarea", "button"}:
            break
        if candidate.name not in {"p", "small", "div"}:
            continue
        if candidate.find(["form", "input", "select", "textarea", "button", "label", "legend"]):
            continue
        if candidate.find([f"h{level}" for level in range(1, 7)]):
            continue
        if candidate.find("a", href=True):
            continue
        value = _bounded_text(candidate, FORM_INTRODUCTORY_TEXT_LIMIT)
        if value:
            return value
    return _external_form_context(form)[1]


def _form_submit_text(form: Tag) -> str | None:
    values: list[str] = []
    for control in form.find_all(["button", "input"]):
        kind = str(control.get("type") or ("submit" if control.name == "button" else "text")).lower()
        if kind != "submit":
            continue
        value = _text(control) if control.name == "button" else str(control.get("value") or "").strip()
        value = " ".join(value.split())
        if value and value not in values:
            values.append(value)
    combined = " | ".join(values)
    return combined[:FORM_SUBMIT_TEXT_LIMIT] or None


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
        context = form.find_parent(["div", "section", "article"])
        context = context if isinstance(context, Tag) else form
        nearby = _text(context)[:500]
        privacy_links: list[LinkEvidence] = []
        seen_privacy_links: set[str] = set()
        for anchor in context.find_all("a", href=True):
            signal = f"{_text(anchor)} {anchor['href']}".lower()
            if any(term in signal for term in PRIVACY_SIGNALS):
                url = urljoin(source_url, str(anchor["href"]))
                if url not in seen_privacy_links:
                    seen_privacy_links.add(url)
                    privacy_links.append(LinkEvidence(url, _text(anchor), source_url))
        results.append(FormEvidence(
            source_url=source_url,
            action=urljoin(source_url, str(form.get("action") or source_url)),
            method=str(form.get("method") or "get").lower(),
            fields=fields,
            checkboxes=checkboxes,
            nearby_text=nearby,
            privacy_links=privacy_links,
            heading=_form_heading(form),
            legend=next((
                value for item in form.find_all("legend")
                if (value := _bounded_text(item, FORM_LEGEND_LIMIT))
            ), None),
            introductory_text=_form_introductory_text(form),
            submit_text=_form_submit_text(form),
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
    visible_text = _text(soup)
    content_text = _clean_content_text(soup)
    visible = visible_text.lower()
    return PageExtraction(
        title=title,
        # Bounded document text lets domain packs retain deterministic signals
        # without retaining the complete untrusted document.
        visible_text=visible_text[:4000],
        content_text=content_text,
        links=_links(soup, source_url),
        forms=_forms(soup, source_url),
        contacts=_contacts(soup, source_url),
        banner_detected=any(signal in visible for signal in COOKIE_BANNER_SIGNALS),
        preferences_detected=any(signal in visible for signal in PREFERENCE_SIGNALS),
        mixed_content=mixed,
    )


def build_evidence(
    fetch_result: InspectionFetchResult,
    additional_links: Iterable[LinkEvidence] | None = None,
) -> EvidenceContract:
    """Build Evidence Contract v0.2 from an existing bounded fetch result."""

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
        pages.append(PageEvidence(
            url=page.final_url,
            status_code=page.status_code,
            title=extracted.title,
            content_type=page.content_type,
            requested_url=page.requested_url,
            visible_text=extracted.visible_text,
            content_text=extracted.content_text,
        ))
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

    links.extend(additional_links or [])
    deduplicated_links: list[LinkEvidence] = []
    seen_links: set[tuple[str, str, str]] = set()
    for link in links:
        identity = (link.url, link.text, link.source_url)
        if identity not in seen_links:
            seen_links.add(identity)
            deduplicated_links.append(link)

    try:
        normalized_target = normalize_url(fetch_result.target_url)
    except ValueError:
        normalized_target = fetch_result.target_url
    target_page = next(
        (
            page
            for page in fetch_result.pages
            if _normalized_or_original(page.requested_url) == normalized_target
        ),
        None,
    )
    final_url = target_page.final_url if target_page is not None else None
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
            tls_valid=target_page.tls_valid if target_page is not None else None,
            http_redirects_to_https=redirects_to_https,
            mixed_content=any(https_mixed) if https_mixed else None,
        ),
        links=deduplicated_links,
        forms=forms,
        cookies=CookieEvidence(bool(cookie_names), cookie_names, banner, preferences),
        contacts=contacts,
    )


def _normalized_or_original(url: str) -> str:
    try:
        return normalize_url(url)
    except ValueError:
        return url
