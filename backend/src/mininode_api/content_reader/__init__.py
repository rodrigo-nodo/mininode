"""Generic content reading without semantic evaluation."""

from .reader import (
    MAX_DOCUMENT_CHARACTERS,
    ContentDocument,
    ContentLink,
    ContentNode,
    ContentReadError,
    read_html_document,
    read_public_html_url,
)

__all__ = [
    "MAX_DOCUMENT_CHARACTERS",
    "ContentDocument",
    "ContentLink",
    "ContentNode",
    "ContentReadError",
    "read_html_document",
    "read_public_html_url",
]
