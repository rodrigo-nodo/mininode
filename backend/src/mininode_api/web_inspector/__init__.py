"""Safe, generic web fetching primitives for Mininode."""

from .fetcher import WebFetcher, normalize_url
from .models import FetchError, FetchPageResult, InspectionFetchResult

__all__ = [
    "FetchError",
    "FetchPageResult",
    "InspectionFetchResult",
    "WebFetcher",
    "normalize_url",
]
