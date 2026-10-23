"""Independent PDF digital-text reader (no OCR)."""

from .structure import PdfLayoutRegion

from .reader import (
    MAX_PDF_BYTES, MAX_PDF_PAGES, MAX_PDF_CHARACTERS,
    PdfReadError, PdfTextLine, PdfLink, PdfPage, PdfDocument, PdfTable, PdfTableCell, PdfBlock,
    read_pdf_document, read_public_pdf_url,
)

__all__ = [
    "MAX_PDF_BYTES", "MAX_PDF_PAGES", "MAX_PDF_CHARACTERS", "PdfLayoutRegion",
    "PdfReadError", "PdfTextLine", "PdfLink", "PdfPage", "PdfDocument", "PdfTable", "PdfTableCell", "PdfBlock",
    "read_pdf_document", "read_public_pdf_url",
]
