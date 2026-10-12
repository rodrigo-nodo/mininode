"""Generic reader of complete static HTML body content.

It does not select relevant sections or interpret meaning. URL/network safety is
delegated to the existing WebFetcher.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from mininode_api.web_inspector.fetcher import WebFetcher

MAX_DOCUMENT_CHARACTERS = 200_000
_SKIP_ELEMENTS = frozenset({"script", "style", "template", "svg", "canvas"})
_BLOCK_ELEMENTS = frozenset({
    "address", "article", "aside", "blockquote", "body", "dd", "div", "dl", "dt",
    "fieldset", "figcaption", "figure", "footer", "form", "header", "main",
    "nav", "ol", "p", "pre", "section", "table", "ul",
})


class ContentReadError(ValueError):
    """A controlled failure; never report partial text as a complete document."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ContentLink:
    text: str
    url: str


@dataclass(frozen=True)
class ContentDocument:
    requested_url: str
    final_url: str
    title: str | None
    text: str
    links: tuple[ContentLink, ...]
    content_sha256: str
    character_count: int
    extraction_scope: str = "static_html"
    truncated: bool = False


def _is_hidden(node: Tag) -> bool:
    return (
        node.name in _SKIP_ELEMENTS
        or node.has_attr("hidden")
        or node.get("aria-hidden") == "true"
    )


def _render(node: Tag | NavigableString, output: list[str]) -> None:
    if isinstance(node, Comment):
        return
    if isinstance(node, NavigableString):
        value = re.sub(r"\s+", " ", str(node))
        if (
            value
            and output
            and output[-1]
            and not output[-1][-1].isspace()
            and not value[0].isspace()
            and value[0].isupper()
            and (output[-1][-1].islower() or output[-1][-1] in "?!")
        ):
            # Some sites omit separators between adjacent inline labels:
            # <span>Mis compras</span><span>Haz seguimiento</span>.
            # Do not insert spaces unconditionally: anti<strong>fraude</strong>
            # deliberately forms one word.
            output.append(" ")
        output.append(value)
        return
    if not isinstance(node, Tag) or _is_hidden(node):
        return

    name = node.name or ""
    if name == "br":
        output.append("\n")
        return
    if name == "hr":
        output.append("\n---\n")
        return

    heading = name in {"h1", "h2", "h3", "h4", "h5", "h6"}
    if heading:
        output.append("\n\n" + "#" * int(name[1]) + " ")
    elif name == "li":
        output.append("\n- ")
    elif name in {"tr", "dt"}:
        output.append("\n")
    elif name in {"td", "th"}:
        output.append(" | ")
    elif name in _BLOCK_ELEMENTS:
        output.append("\n\n")

    for child in node.children:
        _render(child, output)

    if heading or name in _BLOCK_ELEMENTS:
        output.append("\n\n")
    elif name == "li":
        output.append("\n")


def _clean_lines(chunks: list[str]) -> str:
    lines = [
        re.sub(r"[ \t]+", " ", line).strip()
        for line in "".join(chunks).splitlines()
    ]
    result: list[str] = []
    for line in lines:
        if line or (result and result[-1]):
            result.append(line)
    return "\n".join(result).strip()


def read_html_document(
    html: str,
    final_url: str,
    *,
    requested_url: str | None = None,
    max_characters: int = MAX_DOCUMENT_CHARACTERS,
) -> ContentDocument:
    """Read the entire static HTML body without semantic filtering or truncation.

    Browser-generated content and CSS-dependent visibility are outside this
    scope. Content above the size limit fails explicitly instead of truncating.
    """
    if max_characters < 1:
        raise ValueError("max_characters must be positive")
    soup = BeautifulSoup(html, "lxml")
    title_node = soup.find("title")
    title = (
        " ".join(title_node.get_text(" ", strip=True).split())
        if isinstance(title_node, Tag)
        else None
    )
    root = soup.body if isinstance(soup.body, Tag) else soup
    chunks: list[str] = []
    _render(root, chunks)
    text = _clean_lines(chunks)
    if not text:
        raise ContentReadError("empty_document")
    if len(text) > max_characters:
        raise ContentReadError("document_too_large")

    links: list[ContentLink] = []
    for anchor in root.find_all("a", href=True):
        if any(
            _is_hidden(parent)
            for parent in (anchor, *anchor.parents)
            if isinstance(parent, Tag)
        ):
            continue
        href_value = str(anchor.get("href") or "").strip()
        if not href_value:
            continue
        href = urljoin(final_url, href_value)
        if urlsplit(href).scheme.lower() in {"http", "https", "mailto", "tel"}:
            links.append(
                ContentLink(
                    " ".join(anchor.get_text(" ", strip=True).split()), href
                )
            )

    return ContentDocument(
        requested_url=requested_url or final_url,
        final_url=final_url,
        title=title,
        text=text,
        links=tuple(links),
        content_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        character_count=len(text),
    )


def read_public_html_url(
    url: str,
    *,
    fetcher_factory: Callable[[], WebFetcher] = WebFetcher,
) -> ContentDocument:
    """Use existing robots-aware SSRF-protected fetching for one public URL."""
    with fetcher_factory() as fetcher:
        fetched = fetcher.fetch(url, [url])
    page = fetched.pages[0] if fetched.pages else None
    if page is None:
        raise ContentReadError("inspection_failed")
    if page.error is not None:
        raise ContentReadError(page.error.code)
    if page.html is None or page.final_url is None:
        raise ContentReadError("inspection_failed")
    return read_html_document(page.html, page.final_url, requested_url=url)
