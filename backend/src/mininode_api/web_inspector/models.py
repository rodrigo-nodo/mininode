"""In-memory result models produced by the Web Inspector fetcher."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
    set_cookie_names: list[str] = field(default_factory=list)
    error: FetchError | None = None


@dataclass
class InspectionFetchResult:
    target_url: str
    pages_requested: int
    pages_fetched: int = 0
    pages: list[FetchPageResult] = field(default_factory=list)
    errors: list[FetchError] = field(default_factory=list)
    limited: bool = False


@dataclass(frozen=True)
class TargetEvidence:
    requested_url: str
    final_url: str
    domain: str


@dataclass(frozen=True)
class InspectionEvidence:
    pages_requested: int
    pages_analyzed: int
    limited: bool
    errors: list[dict[str, str]]


@dataclass(frozen=True)
class PageEvidence:
    url: str
    status_code: int
    title: str | None
    content_type: str


@dataclass(frozen=True)
class LinkEvidence:
    url: str
    text: str
    source_url: str


@dataclass(frozen=True)
class FieldEvidence:
    name: str
    type: str
    label: str
    required: bool


@dataclass(frozen=True)
class CheckboxEvidence:
    name: str
    label: str


@dataclass(frozen=True)
class FormEvidence:
    source_url: str
    action: str
    method: str
    fields: list[FieldEvidence]
    checkboxes: list[CheckboxEvidence]
    nearby_text: str
    privacy_links: list[str]


@dataclass(frozen=True)
class CookieEvidence:
    detected: bool
    set_cookie_names: list[str]
    banner_detected: bool
    preferences_detected: bool


@dataclass(frozen=True)
class ContactEvidence:
    type: str
    value: str
    source_url: str


@dataclass(frozen=True)
class TransportEvidence:
    https: bool
    tls_valid: bool | None
    http_redirects_to_https: bool | None
    mixed_content: bool | None


@dataclass(frozen=True)
class EvidenceContract:
    target: TargetEvidence
    inspection: InspectionEvidence
    pages: list[PageEvidence]
    transport: TransportEvidence
    links: list[LinkEvidence]
    forms: list[FormEvidence]
    cookies: CookieEvidence
    contacts: list[ContactEvidence]

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic, JSON-compatible representation."""

        from dataclasses import asdict

        return asdict(self)
