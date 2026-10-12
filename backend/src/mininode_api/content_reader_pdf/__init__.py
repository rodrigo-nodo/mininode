"""Independent PDF digital-text reader (no OCR)."""

from .reader import (
    MAX_PDF_BYTES, MAX_PDF_PAGES, MAX_PDF_CHARACTERS,
    PdfReadError, PdfTextLine, PdfLink, PdfPage, PdfDocument,
    read_pdf_document, read_public_pdf_url,
)

__all__ = [
    "MAX_PDF_BYTES", "MAX_PDF_PAGES", "MAX_PDF_CHARACTERS",
    "PdfReadError", "PdfTextLine", "PdfLink", "PdfPage", "PdfDocument",
    "read_pdf_document", "read_public_pdf_url",
]
