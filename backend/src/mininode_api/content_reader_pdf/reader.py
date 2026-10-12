"""Independent digital-PDF reader. No OCR, no semantic classification."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from typing import Callable

import pdfplumber

from mininode_api.web_inspector.fetcher import WebFetcher

MAX_PDF_BYTES = 2 * 1024 * 1024  # Matches the protected HTTP fetch cap.
MAX_PDF_PAGES = 50
MAX_PDF_CHARACTERS = 200_000
MAX_PDF_CHARS_PER_PAGE = 20_000


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
class PdfPage:
    number: int
    width: float
    height: float
    lines: tuple[PdfTextLine, ...]
    links: tuple[PdfLink, ...]
    image_count: int
    extraction_status: str = "digital_text"


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


def read_pdf_document(
    data: bytes,
    *,
    final_url: str | None = None,
    requested_url: str | None = None,
    max_bytes: int = MAX_PDF_BYTES,
    max_pages: int = MAX_PDF_PAGES,
    max_characters: int = MAX_PDF_CHARACTERS,
) -> PdfDocument:
    """Read all digital-text pages, rejecting incomplete or ambiguous documents.

    Coordinates are PDF page-local points, reported exactly as the extraction
    library exposes them. Lines are derived layout groups, not source objects.
    """
    if min(max_bytes, max_pages, max_characters) < 1:
        raise ValueError("PDF limits must be positive")
    if len(data) > max_bytes:
        raise PdfReadError("pdf_too_large")
    if not data.startswith(b"%PDF-"):
        raise PdfReadError("invalid_pdf")
    pages: list[PdfPage] = []
    texts: list[str] = []
    count = 0
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            if len(pdf.pages) == 0:
                raise PdfReadError("empty_pdf")
            if len(pdf.pages) > max_pages:
                raise PdfReadError("pdf_too_many_pages")
            for number, page in enumerate(pdf.pages, start=1):
                # Per-character coordinates are preserved by the library;
                # grouping into lines is only a readable derived representation.
                if len(page.chars) > MAX_PDF_CHARS_PER_PAGE:
                    raise PdfReadError("pdf_too_complex")
                words = page.extract_words(
                    keep_blank_chars=False,
                    use_text_flow=False,
                    return_chars=False,
                )
                if not words:
                    raise PdfReadError("pdf_page_without_text")
                lines_by_position: dict[tuple[float, float], list[dict]] = {}
                for word in words:
                    key = (round(float(word["top"]), 1), round(float(word["bottom"]), 1))
                    lines_by_position.setdefault(key, []).append(word)
                lines: list[PdfTextLine] = []
                for key in sorted(lines_by_position):
                    row = sorted(lines_by_position[key], key=lambda w: float(w["x0"]))
                    line = " ".join(str(w["text"]) for w in row)
                    lines.append(PdfTextLine(
                        page=number,
                        text=line,
                        bbox=(min(float(w["x0"]) for w in row), min(float(w["top"]) for w in row),
                              max(float(w["x1"]) for w in row), max(float(w["bottom"]) for w in row)),
                    ))
                text = "\n".join(line.text for line in lines)
                if not text.strip():
                    raise PdfReadError("pdf_page_without_text")
                count += len(text)
                if count > max_characters:
                    raise PdfReadError("pdf_text_too_large")
                texts.append(text)
                links: list[PdfLink] = []
                for link in page.hyperlinks:
                    uri = link.get("uri")
                    if isinstance(uri, str) and uri.startswith(("https://", "http://", "mailto:", "tel:")):
                        links.append(PdfLink(
                            page=number,
                            url=uri,
                            bbox=(float(link.get("x0") or 0), float(link.get("top") or 0),
                                  float(link.get("x1") or 0), float(link.get("bottom") or 0)),
                        ))
                pages.append(PdfPage(
                    number=number,
                    width=float(page.width),
                    height=float(page.height),
                    lines=tuple(lines),
                    links=tuple(links),
                    image_count=len(page.images),
                ))
    except PdfReadError:
        raise
    except Exception as exc:
        raise PdfReadError("pdf_parse_failed") from exc

    full_text = "\n\n".join(texts)
    return PdfDocument(
        requested_url=requested_url or final_url,
        final_url=final_url,
        pages=tuple(pages),
        text=full_text,
        file_sha256=hashlib.sha256(data).hexdigest(),
        text_sha256=hashlib.sha256(full_text.encode("utf-8")).hexdigest(),
        character_count=len(full_text),
        page_count=len(pages),
    )


def read_public_pdf_url(
    url: str,
    *,
    fetcher_factory: Callable[[], WebFetcher] = WebFetcher,
) -> PdfDocument:
    """Fetch a public PDF via the established robots/SSRF/pinned-IP guard."""
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
