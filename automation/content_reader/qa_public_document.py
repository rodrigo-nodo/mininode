"""One-shot Content Reader QA against the same public HTML capture.

The independent reference is DOM text from BeautifulSoup.stripped_strings, not
Content Reader output. It measures complete static text, never privacy findings.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Comment, NavigableString

from mininode_api.content_reader import ContentReadError, read_html_document
from mininode_api.web_inspector import WebFetcher

TARGET = os.environ.get("CONTENT_READER_QA_URL", "https://www.smileykidsfood.com/politica-de-privacidad")
OUT = Path("content-reader-qa-output")
OUT.mkdir(exist_ok=True)


def canonical_words(text: str) -> list[str]:
    folded = unicodedata.normalize("NFKC", text).casefold()
    return re.findall(r"\w+(?:[-'’]\w+)*", folded, re.UNICODE)


def independent_reference(html: str) -> str:
    """Independent DOM-only baseline; intentionally avoids the Reader renderer."""
    tree = BeautifulSoup(html, "lxml")
    root = tree.body or tree
    for element in list(root.find_all(True)):
        if element.parent is None or element is root:
            continue
        if (
            element.name in {"script", "style", "template", "svg", "canvas"}
        ):
            element.decompose()
    return "".join(
        str(node)
        for node in root.descendants
        if isinstance(node, NavigableString)
        and not isinstance(node, Comment)
        and node.parent is not None
    )


def save(report: dict, *, ref_text: str = "", reader_text: str = "") -> None:
    (OUT / "summary.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if ref_text:
        (OUT / "reference.txt").write_text(ref_text, encoding="utf-8")
    if reader_text:
        (OUT / "content-reader.txt").write_text(reader_text, encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)


def main() -> int:
    # Public, passive GET only: existing robots, SSRF, time and response caps.
    with WebFetcher() as fetcher:
        fetched = fetcher.fetch(TARGET, [TARGET])
    page = fetched.pages[0] if fetched.pages else None
    if not page or page.error or page.html is None or not page.final_url:
        error_code = page.error.code if page and page.error else "no_html"
        save({"status": "CAPTURE_FAILED", "target": TARGET,
              "reason": error_code, "reader_executed": False})
        return 2

    source_hash = hashlib.sha256(page.html.encode("utf-8")).hexdigest()
    reference = independent_reference(page.html)

    try:
        document = read_html_document(
            page.html, page.final_url, requested_url=TARGET
        )
    except ContentReadError as exc:
        save({"status": "NEEDS_REVIEW", "target": TARGET,
              "final_url": page.final_url, "html_sha256": source_hash,
              "reason": exc.code, "reader_executed": True},
             ref_text=reference)
        return 1

    soup = BeautifulSoup(page.html, "lxml")
    root = soup.body or soup
    links_baseline = []
    for anchor in root.find_all("a", href=True):
        if any(p.name in {"script", "style", "template", "svg", "canvas"} for p in (anchor, *anchor.parents)):
            continue
        href_raw = str(anchor.get("href") or "").strip()
        if not href_raw:
            continue
        resolved = urljoin(page.final_url, href_raw)
        if urlsplit(resolved).scheme.lower() in {"http", "https", "mailto", "tel"}:
            links_baseline.append(resolved)
    links_reader = [link.url for link in document.links]
    # Primary oracle: exact concatenated DOM text, including punctuation,
    # whitespace and mixed inline node boundaries. Never join with spaces.
    actual_source = document.source_text
    baseline = canonical_words(reference)
    actual = canonical_words(actual_source)
    exact_source = reference == actual_source
    # Independent DOM preorder structural trace (tag names, parent indices,
    # exact text values). Built without the ContentReader implementation.
    from bs4 import Tag
    expected_trace = []
    def visit(node, parent):
        if isinstance(node, Comment):
            return
        if isinstance(node, NavigableString):
            expected_trace.append(("text", parent, None, str(node)))
            return
        if not isinstance(node, Tag) or node.name in {"script", "style", "template", "svg", "canvas"}:
            return
        idx = len(expected_trace)
        expected_trace.append(("element", parent, node.name, None))
        for child in node.children:
            visit(child, idx)
    visit(root, None)
    actual_trace = [(n.kind, n.parent_id, n.tag, n.text) for n in document.nodes]
    structure_match = expected_trace == actual_trace
    baseline_counts = Counter(baseline)
    actual_counts = Counter(actual)
    omitted = baseline_counts - actual_counts
    added = actual_counts - baseline_counts
    matched_count = sum((baseline_counts & actual_counts).values())

    # SequenceMatcher is independent of the Reader and estimates order fidelity.
    # Exact equality has priority and avoids misleading heuristic matching.
    exact_word_order = baseline == actual
    if exact_word_order:
        matched_order = len(baseline)
    else:
        matcher = SequenceMatcher(None, baseline, actual, autojunk=True)
        matched_order = sum(block.size for block in matcher.get_matching_blocks())

    links_match = links_baseline == links_reader
    report = {
        "target": TARGET,
        "final_url": page.final_url,
        "status": "PASS" if exact_source and structure_match and links_match else "NEEDS_REVIEW",
        "reader_executed": True,
        "comparison_scope": "exact_dom_source_text_nodes_and_links",
        "exact_source_text": exact_source,
        "exact_dom_structure": structure_match,
        "source_node_count": len(document.nodes),
        "reference_node_count": len(expected_trace),
        "html_sha256": source_hash,
        "reference_sha256": hashlib.sha256(reference.encode("utf-8")).hexdigest(),
        "reader_sha256": document.source_sha256,
        "reference_words": len(baseline),
        "reader_words": len(actual),
        "reference_characters": len(reference),
        "reader_characters": document.source_character_count,
        "reference_word_coverage_pct": (
            round(100 * matched_count / len(baseline), 3) if baseline else 100
        ),
        "ordered_word_coverage_pct": (
            round(100 * matched_order / len(baseline), 3) if baseline else 100
        ),
        "exact_word_order": exact_word_order,
        "missing_word_occurrences": sum(omitted.values()),
        "additional_word_occurrences": sum(added.values()),
        "missing_word_samples": omitted.most_common(20),
        "additional_word_samples": added.most_common(20),
        "link_count": len(document.links),
        "reference_link_count": len(links_baseline),
        "exact_link_destinations_and_order": links_match,
        "reader_scope": document.extraction_scope,
        "reader_truncated": document.truncated,
        "comment": (
            "Needs manual inspection of full diff: baseline joins independent "
            "HTML text nodes with spaces, which can differ from browser inline rendering."
            if not exact_word_order else
            "Exact source text and DOM trace evaluated independently from the readable view."
        ),
    }
    save(report, ref_text=reference, reader_text=actual_source)
    return 0 if exact_source and structure_match and links_match else 1


if __name__ == "__main__":
    sys.exit(main())
