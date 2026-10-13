"""Independent digital PDF reader; no OCR or semantic interpretation.

The public API isolates untrusted PDF parsing in a time/memory/CPU limited
child process. Reader HTML's contract and behavior are unchanged.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import Callable

from mininode_api.web_inspector.fetcher import WebFetcher

MAX_PDF_BYTES = 2 * 1024 * 1024
MAX_PDF_PAGES = 50
MAX_PDF_CHARACTERS = 200_000
MAX_PDF_CHARS_PER_PAGE = 20_000
MAX_PDF_WALL_SECONDS = 15
MAX_PDF_CPU_SECONDS = 10
MAX_PDF_MEMORY_MB = 768


class PdfReadError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class PdfTextLine:
    page: int
    text: str
    bbox: tuple[float, float, float, float]


@dataclass(frozen=True)
class PdfLink:
    page: int
    url: str
    bbox: tuple[float, float, float, float]


@dataclass(frozen=True)
class PdfTableCell:
    row: int
    column: int
    text: str
    bbox: tuple[float, float, float, float]


@dataclass(frozen=True)
class PdfTable:
    page: int
    bbox: tuple[float, float, float, float]
    rows: tuple[tuple[str, ...], ...]
    cells: tuple[PdfTableCell, ...]


@dataclass(frozen=True)
class PdfBlock:
    page: int
    kind: str  # text | table
    text: str
    bbox: tuple[float, float, float, float]
    table_index: int | None = None


@dataclass(frozen=True)
class PdfPage:
    number: int
    width: float
    height: float
    lines: tuple[PdfTextLine, ...]
    links: tuple[PdfLink, ...]
    image_count: int
    tables: tuple[PdfTable, ...] = ()
    blocks: tuple[PdfBlock, ...] = ()
    extraction_status: str = "digital_text"  # may be digital_text_with_images


@dataclass(frozen=True)
class PdfDocument:
    requested_url: str | None
    final_url: str | None
    pages: tuple[PdfPage, ...]
    text: str
    file_sha256: str
    text_sha256: str
    character_count: int
    page_count: int
    extraction_scope: str = "digital_pdf"
    truncated: bool = False
    integrity_status: str = "not_visually_verified"


def _validate_limits(data: bytes, max_bytes: int, max_pages: int, max_characters: int) -> None:
    if min(max_bytes, max_pages, max_characters) < 1:
        raise ValueError("PDF limits must be positive")
    if len(data) > max_bytes:
        raise PdfReadError("pdf_too_large")
    if not data.startswith(b"%PDF-"):
        raise PdfReadError("invalid_pdf")



def _has_ambiguous_parallel_columns(words: list[dict], page_width: float) -> bool:
    """Detect sustained parallel text lanes without requiring shared baselines.

    Work on *non-table* words. A whitespace corridor running between two
    vertically overlapping groups indicates independent reading regions.
    Scan short consecutive vertical windows so a full-width title does not
    hide two columns farther down the page. This check deliberately fails
    closed: it does not claim to infer reading order from whitespace.
    """
    if len(words) < 4:
        return False

    by_baseline: dict[float, list[dict]] = {}
    for word in words:
        baseline = round((float(word["top"]) + float(word["bottom"])) / 2, 1)
        by_baseline.setdefault(baseline, []).append(word)
    bands = [by_baseline[key] for key in sorted(by_baseline)]

    def is_numbered_list(left: list[dict], right: list[dict]) -> bool:
        """Recognize short, aligned list markers, not an independent column.

        Require short explicit markers (numbers, letters, bullets or dashes)
        on the same baselines as adjacent text, and a narrow marker lane.
        A0/B0 labels are not markers and must still be treated as ambiguous.
        """
        if len(left) < 2:
            return False
        marker = re.compile(r"(?:\(\d{1,3}\)|\d{1,3}[.)]|\([A-Za-z]\)|[A-Za-z][.)]|[IVXLCDMivxlcdm]{1,6}[.)]|[-–—•◦▪*])")
        if not all(marker.fullmatch(str(word["text"])) for word in left):
            return False
        if max(float(w["x1"]) for w in left) - min(float(w["x0"]) for w in left) > page_width * 0.07:
            return False
        return all(
            any(abs((float(l["top"]) + float(l["bottom"])) -
                    (float(r["top"]) + float(r["bottom"]))) <= 5 for r in right)
            for l in left
        )

    def is_parallel(window: list[dict]) -> bool:
        # Compare gaps with the visual font height, not the page width:
        # a 7-point column gutter in a 600-point page is still meaningful.
        # Repeated vertical separation and a list-marker guard are required;
        # a single ordinary gap between words is not enough.
        occupied = sorted((float(w["x0"]), float(w["x1"])) for w in window)
        if len(occupied) < 4:
            return False
        merged: list[list[float]] = []
        for x0, x1 in occupied:
            if merged and x0 <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], x1)
            else:
                merged.append([x0, x1])
        typical_word_height = sorted(float(w["bottom"]) - float(w["top"]) for w in window)[len(window) // 2]
        minimum_corridor = max(3.5, typical_word_height * 0.45)
        for left_region, right_region in zip(merged, merged[1:]):
            if right_region[0] - left_region[1] < minimum_corridor:
                continue
            divider = (left_region[1] + right_region[0]) / 2
            left = [w for w in window if float(w["x1"]) <= divider]
            right = [w for w in window if float(w["x0"]) >= divider]
            if len(left) < 2 or len(right) < 2:
                continue
            if is_numbered_list(left, right):
                continue

            def baselines(items: list[dict]) -> set[float]:
                return {
                    round((float(w["top"]) + float(w["bottom"])) / 2, 1)
                    for w in items
                }

            if len(baselines(left)) < 2 or len(baselines(right)) < 2:
                continue
            overlap = (
                min(max(float(w["bottom"]) for w in left),
                    max(float(w["bottom"]) for w in right))
                - max(min(float(w["top"]) for w in left),
                      min(float(w["top"]) for w in right))
            )
            if overlap > 8:
                return True
        return False

    # Eight visual baselines suffice for two short columns even when their
    # rows are offset. Sliding windows also handle multicolumn subsections.
    for start in range(len(bands)):
        window = [w for band in bands[start:start + 8] for w in band]
        if is_parallel(window):
            return True
    return False


def _parse_pdf_in_worker(
    data: bytes, final_url: str | None, requested_url: str | None,
    max_bytes: int, max_pages: int, max_characters: int,
) -> PdfDocument:
    """Only call after the subprocess installs resource limits."""
    import io
    import pdfplumber

    _validate_limits(data, max_bytes, max_pages, max_characters)
    pages: list[PdfPage] = []
    page_texts: list[str] = []
    count = 0
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            if not pdf.pages:
                raise PdfReadError("empty_pdf")
            if len(pdf.pages) > max_pages:
                raise PdfReadError("pdf_too_many_pages")
            for number, page in enumerate(pdf.pages, 1):
                # This count is a *functional* cap. The process CPU/RAM limits
                # protect evaluation of pdfplumber's lazy page.chars itself.
                chars = page.chars
                if len(chars) > MAX_PDF_CHARS_PER_PAGE:
                    raise PdfReadError("pdf_too_complex")
                words = page.extract_words(keep_blank_chars=False, use_text_flow=False)
                if not words:
                    raise PdfReadError("pdf_page_without_text")

                found = []
                for candidate in page.find_tables(table_settings={
                    "vertical_strategy": "lines", "horizontal_strategy": "lines",
                }):
                    rows = candidate.extract()
                    if len(rows) >= 2 and all(len(row) >= 2 for row in rows):
                        found.append(candidate)
                found.sort(key=lambda table: (table.bbox[1], table.bbox[0]))
                if len(found) > 30:
                    raise PdfReadError("pdf_too_complex")

                tables: list[PdfTable] = []
                blocks: list[PdfBlock] = []
                for table in found:
                    rows = tuple(tuple((str(cell) if cell is not None else "") for cell in row)
                                 for row in table.extract())
                    if sum(len(row) for row in rows) > 5000:
                        raise PdfReadError("pdf_too_complex")
                    cells = []
                    for r, table_row in enumerate(table.rows):
                        for col, bbox in enumerate(table_row.cells):
                            if bbox is None:
                                if rows[r][col].strip():
                                    raise PdfReadError("pdf_layout_ambiguous")
                                continue
                            cells.append(PdfTableCell(
                                r, col, rows[r][col], tuple(float(p) for p in bbox),
                            ))
                    b = tuple(float(v) for v in table.bbox)
                    table_index = len(tables)
                    tables.append(PdfTable(number, b, rows, tuple(cells)))
                    text = "\n".join(" | ".join(row) for row in rows)
                    blocks.append(PdfBlock(number, "table", text, b, table_index))

                def within_table(w: dict) -> bool:
                    cx = (float(w["x0"]) + float(w["x1"])) / 2
                    cy = (float(w["top"]) + float(w["bottom"])) / 2
                    return any(t.bbox[0] <= cx <= t.bbox[2] and t.bbox[1] <= cy <= t.bbox[3]
                               for t in tables)

                remaining = [w for w in words if not within_table(w)]
                by_y: dict[tuple[float, float], list[dict]] = {}
                for word in remaining:
                    key = (round(float(word["top"]), 1), round(float(word["bottom"]), 1))
                    by_y.setdefault(key, []).append(word)

                # Detect repeated separate text runs that pdfplumber may join
                # when their gap is smaller than its word-spacing threshold.
                # Require the same complete two-field strings on 3+ lines;
                # unlike a mere kerning gap, each field must be independently
                # delimited by a nonspace glyph gap and recur at the same x.
                glyph_lines: dict[float, list[dict]] = {}
                for ch in chars:
                    if not str(ch.get("text", "")).strip():
                        continue
                    center_x = (float(ch["x0"]) + float(ch["x1"])) / 2
                    center_y = (float(ch["top"]) + float(ch["bottom"])) / 2
                    if any(t.bbox[0] <= center_x <= t.bbox[2] and t.bbox[1] <= center_y <= t.bbox[3] for t in tables):
                        continue
                    glyph_lines.setdefault(round(center_y, 1), []).append(ch)
                narrow_seams: dict[tuple[float, str, str], int] = {}
                for glyphs in glyph_lines.values():
                    glyphs.sort(key=lambda ch: float(ch["x0"]))
                    for index in range(3, len(glyphs) - 3):
                        left_glyph, right_glyph = glyphs[index - 1], glyphs[index]
                        gap = float(right_glyph["x0"]) - float(left_glyph["x1"])
                        if not 2.5 <= gap <= 5.0:
                            continue
                        lhs = "".join(ch["text"] for ch in glyphs[:index]).strip()
                        rhs = "".join(ch["text"] for ch in glyphs[index:]).strip()
                        if not (3 <= len(lhs) <= 40 and 3 <= len(rhs) <= 40):
                            continue
                        if " " in lhs or " " in rhs:
                            continue
                        seam_key = (round((float(left_glyph["x1"]) + float(right_glyph["x0"])) / 2),
                                    lhs, rhs)
                        narrow_seams[seam_key] = narrow_seams.get(seam_key, 0) + 1
                if any(repeated >= 3 for repeated in narrow_seams.values()):
                    raise PdfReadError("pdf_layout_ambiguous")

                # Never silently interleave horizontally independent columns.
                # A vertical offset or short labels must not bypass detection.
                if _has_ambiguous_parallel_columns(remaining, float(page.width)):
                    raise PdfReadError("pdf_layout_ambiguous")

                lines = []
                for key in sorted(by_y):
                    row = sorted(by_y[key], key=lambda w: float(w["x0"]))
                    text = " ".join(str(w["text"]) for w in row)
                    b = (
                        min(float(w["x0"]) for w in row),
                        min(float(w["top"]) for w in row),
                        max(float(w["x1"]) for w in row),
                        max(float(w["bottom"]) for w in row),
                    )
                    lines.append(PdfTextLine(number, text, b))
                    blocks.append(PdfBlock(number, "text", text, b))

                blocks.sort(key=lambda b: (b.bbox[1], b.bbox[0]))
                text = "\n".join(block.text for block in blocks)
                if not text.strip():
                    raise PdfReadError("pdf_page_without_text")
                count += len(text) + (2 if page_texts else 0)
                if count > max_characters:
                    raise PdfReadError("pdf_text_too_large")
                page_texts.append(text)

                links = []
                for link in page.hyperlinks:
                    uri = link.get("uri")
                    if isinstance(uri, str) and uri.startswith(
                        ("https://", "http://", "mailto:", "tel:")
                    ):
                        links.append(PdfLink(
                            number, uri, (float(link.get("x0") or 0), float(link.get("top") or 0),
                                          float(link.get("x1") or 0), float(link.get("bottom") or 0)),
                        ))
                pages.append(PdfPage(
                    number, float(page.width), float(page.height), tuple(lines),
                    tuple(links), len(page.images), tuple(tables), tuple(blocks),
                    "digital_text_with_images" if page.images else "digital_text",
                ))
    except PdfReadError:
        raise
    except Exception as exc:
        raise PdfReadError("pdf_parse_failed") from exc

    full_text = "\n\n".join(page_texts)
    return PdfDocument(
        requested_url or final_url, final_url, tuple(pages), full_text,
        hashlib.sha256(data).hexdigest(),
        hashlib.sha256(full_text.encode("utf-8")).hexdigest(),
        len(full_text), len(pages),
        integrity_status=(
            "unverified_visual_content" if any(p.image_count for p in pages)
            else "text_extracted_not_visually_verified"
        ),
    )


def _decode_worker_document(value: dict) -> PdfDocument:
    pages = []
    for item in value["pages"]:
        lines = tuple(PdfTextLine(**line) for line in item["lines"])
        links = tuple(PdfLink(**link) for link in item["links"])
        tables = tuple(
            PdfTable(
                page=t["page"], bbox=tuple(t["bbox"]),
                rows=tuple(tuple(row) for row in t["rows"]),
                cells=tuple(PdfTableCell(**cell) for cell in t["cells"]),
            ) for t in item["tables"]
        )
        blocks = tuple(PdfBlock(**block) for block in item["blocks"])
        pages.append(PdfPage(
            number=item["number"], width=item["width"], height=item["height"],
            lines=lines, links=links, image_count=item["image_count"],
            tables=tables, blocks=blocks, extraction_status=item["extraction_status"],
        ))
    return PdfDocument(
        requested_url=value["requested_url"], final_url=value["final_url"],
        pages=tuple(pages), text=value["text"], file_sha256=value["file_sha256"],
        text_sha256=value["text_sha256"], character_count=value["character_count"],
        page_count=value["page_count"], extraction_scope=value["extraction_scope"],
        truncated=value["truncated"], integrity_status=value["integrity_status"],
    )


def read_pdf_document(
    data: bytes, *, final_url: str | None = None,
    requested_url: str | None = None, max_bytes: int = MAX_PDF_BYTES,
    max_pages: int = MAX_PDF_PAGES,
    max_characters: int = MAX_PDF_CHARACTERS,
) -> PdfDocument:
    """Parse untrusted bytes in a CPU, memory and wall-clock constrained worker."""
    _validate_limits(data, max_bytes, max_pages, max_characters)
    args = json.dumps({
        "final_url": final_url, "requested_url": requested_url,
        "max_bytes": max_bytes, "max_pages": max_pages,
        "max_characters": max_characters,
    })
    try:
        result = subprocess.run(
            [sys.executable, "-m", "mininode_api.content_reader_pdf._worker", args],
            input=data, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=MAX_PDF_WALL_SECONDS, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise PdfReadError("pdf_processing_timeout") from exc
    except OSError as exc:
        raise PdfReadError("pdf_worker_failed") from exc
    if result.returncode != 0:
        raise PdfReadError("pdf_resource_limit" if result.returncode < 0 else "pdf_worker_failed")
    try:
        payload = json.loads(result.stdout)
        if payload.get("error"):
            raise PdfReadError(str(payload["error"]))
        return _decode_worker_document(payload["document"])
    except PdfReadError:
        raise
    except (ValueError, KeyError, TypeError) as exc:
        raise PdfReadError("pdf_worker_failed") from exc


def read_public_pdf_url(
    url: str, *, fetcher_factory: Callable[[], WebFetcher] = WebFetcher,
) -> PdfDocument:
    """Fetch a public PDF through the existing robots/SSRF/pinned-IP guard."""
    with fetcher_factory() as fetcher:
        fetched = fetcher.fetch(url, [url], accept_pdf=True)
    page = fetched.pages[0] if fetched.pages else None
    if page is None:
        raise PdfReadError("inspection_failed")
    if page.error is not None:
        raise PdfReadError(page.error.code)
    if page.binary_content is None or page.final_url is None:
        raise PdfReadError("unsupported_content_type")
    return read_pdf_document(page.binary_content, final_url=page.final_url, requested_url=url)
