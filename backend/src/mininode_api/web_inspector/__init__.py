"""Safe, generic web fetching primitives for Mininode."""

from .fetcher import WebFetcher, normalize_url
from .extractor import build_evidence, extract_page
from .models import FetchError, FetchPageResult, InspectionFetchResult
from .selector import select_pages

__all__ = [
    "FetchError",
    "FetchPageResult",
    "InspectionFetchResult",
    "WebFetcher",
    "build_evidence",
    "extract_page",
    "normalize_url",
    "select_pages",
]
