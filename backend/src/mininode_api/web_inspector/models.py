"""In-memory result models produced by the Web Inspector fetcher."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FetchError:
    """A controlled fetch failure suitable for API consumers and logs."""

    code: str
    message: str
    url: str


@dataclass
class FetchPageResult:
    requested_url: str
    final_url: str | None = None
    status_code: int | None = None
    content_type: str | None = None
    html: str | None = None
    elapsed_ms: int = 0
    redirect_count: int = 0
    error: FetchError | None = None


@dataclass
class InspectionFetchResult:
    target_url: str
    pages_requested: int
    pages_fetched: int = 0
    pages: list[FetchPageResult] = field(default_factory=list)
    errors: list[FetchError] = field(default_factory=list)
    limited: bool = False
