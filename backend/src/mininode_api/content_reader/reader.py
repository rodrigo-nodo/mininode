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
MAX_DOCUMENT_NODES = 50_000
MAX_DOM_DEPTH = 128
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
class ContentNode:
    """One source-order DOM node, with unaltered text and parent provenance.

    Node IDs are preorder indices within ContentDocument.nodes. A text node's
    parent_id identifies its owning element, even when tags are inline.
    """

    id: int
    parent_id: int | None
    kind: str  # "element" or "text"
    tag: str | None = None
    text: str | None = None
    href: str | None = None
    hidden: bool = False
    aria_hidden: bool = False


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
    # Primary fidelity contract: ordered DOM nodes and exact source fragments.
    nodes: tuple[ContentNode, ...] = ()
    source_text: str = ""
    source_sha256: str = ""
    source_character_count: int = 0


def _is_hidden(node: Tag) -> bool:
    # Preserve source text even when hidden/aria-hidden; this is not a
    # browser renderer, and aria-hidden does not mean visually hidden.
    return node.name in _SKIP_ELEMENTS


def _check_dom_complexity(
    root: Tag, *, max_nodes: int, max_depth: int,
) -> None:
    """Bound DOM traversal before constructing nodes or rendering text.

    Count the same in-scope element and text nodes exposed by ContentNode.
    Use iterative traversal so deeply nested HTML fails with a controlled
    error rather than causing recursion exhaustion during extraction.
    """
    # Iterators, not whole child lists, keep memory bounded by DOM depth.
    frames = [(iter((root,)), 0)]
    count = 0
    while frames:
        iterator, parent_depth = frames[-1]
        node = next(iterator, None)
        if node is None:
            frames.pop()
            continue
        if isinstance(node, Comment):
            continue
        if isinstance(node, NavigableString):
            count += 1
        elif isinstance(node, Tag) and not _is_hidden(node):
            depth = parent_depth + 1
            if depth > max_depth:
                raise ContentReadError("document_too_complex")
            count += 1
            if count > max_nodes:
                raise ContentReadError("document_too_complex")
            frames.append((iter(node.children), depth))
            continue
        if count > max_nodes:
            raise ContentReadError("document_too_complex")


def _render(node: Tag | NavigableString, output: list[str]) -> None:
    if isinstance(node, Comment):
        return
    if isinstance(node, NavigableString):
        output.append(re.sub(r"\s+", " ", str(node)))
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


def _capture_dom_nodes(root: Tag, final_url: str) -> tuple[ContentNode, ...]:
    """Capture preorder DOM structure and exact text without inferred spaces."""

    nodes: list[ContentNode] = []

    def visit(node: Tag | NavigableString, parent_id: int | None) -> None:
        if isinstance(node, Comment):
            return
        if isinstance(node, NavigableString):
            nodes.append(ContentNode(
                id=len(nodes), parent_id=parent_id, kind="text", text=str(node),
            ))
            return
        if not isinstance(node, Tag) or _is_hidden(node):
            return

        node_id = len(nodes)
        href: str | None = None
        if node.name == "a" and node.has_attr("href"):
            href_raw = str(node.get("href") or "").strip()
            if href_raw:
                resolved = urljoin(final_url, href_raw)
                if urlsplit(resolved).scheme.lower() in {"http", "https", "mailto", "tel"}:
                    href = resolved

        nodes.append(ContentNode(
            id=node_id, parent_id=parent_id, kind="element", tag=node.name,
            href=href, hidden=node.has_attr("hidden"),
            aria_hidden=node.get("aria-hidden") == "true",
        ))
        for child in node.children:
            visit(child, node_id)

    visit(root, None)
    return tuple(nodes)


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
    max_nodes: int = MAX_DOCUMENT_NODES,
    max_depth: int = MAX_DOM_DEPTH,
) -> ContentDocument:
    """Preserve complete static HTML text and DOM structure, without inference.

    nodes/source_text are the fidelity contract; text is a derived readable
    view that preserves explicit whitespace and block boundaries but does not
    guess visual whitespace between adjacent inline fragments. Browser-generated
    content and CSS-dependent layout are outside this scope. Node count and
    nesting limits are checked iteratively before recursive extraction.
    """
    if max_characters < 1:
        raise ValueError("max_characters must be positive")
    if max_nodes < 1:
        raise ValueError("max_nodes must be positive")
    if max_depth < 1:
        raise ValueError("max_depth must be positive")
    soup = BeautifulSoup(html, "lxml")
    title_node = soup.find("title")
    title = (
        " ".join(title_node.get_text(" ", strip=True).split())
        if isinstance(title_node, Tag)
        else None
    )
    root = soup.body if isinstance(soup.body, Tag) else soup
    _check_dom_complexity(root, max_nodes=max_nodes, max_depth=max_depth)
    chunks: list[str] = []
    _render(root, chunks)
    text = _clean_lines(chunks)
    nodes = _capture_dom_nodes(root, final_url)
    source_text = "".join(
        node.text for node in nodes if node.kind == "text" and node.text is not None
    )
    if not source_text.strip():
        raise ContentReadError("empty_document")
    if len(text) > max_characters or len(source_text) > max_characters:
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
        nodes=nodes,
        source_text=source_text,
        source_sha256=hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        source_character_count=len(source_text),
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
