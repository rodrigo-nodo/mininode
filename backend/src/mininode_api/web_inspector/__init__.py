"""Safe, generic web fetching primitives for Mininode."""

from .fetcher import WebFetcher, normalize_url
from .extractor import build_evidence, extract_page
from .models import (
    CheckboxEvidence,
    ContactEvidence,
    CookieEvidence,
    EvidenceContract,
    FetchError,
    FetchPageResult,
    FieldEvidence,
    FormEvidence,
    InspectionEvidence,
    InspectionFetchResult,
    LinkEvidence,
    PageEvidence,
    TargetEvidence,
    TransportEvidence,
)
from .selector import select_pages

__all__ = [
    "CheckboxEvidence",
    "ContactEvidence",
    "CookieEvidence",
    "EvidenceContract",
    "FetchError",
    "FetchPageResult",
    "FieldEvidence",
    "FormEvidence",
    "InspectionEvidence",
    "InspectionFetchResult",
    "LinkEvidence",
    "PageEvidence",
    "TargetEvidence",
    "TransportEvidence",
    "WebFetcher",
    "build_evidence",
    "extract_page",
    "normalize_url",
    "select_pages",
]
