"""In-memory fetch and evidence models produced by the Web Inspector."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
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
    tls_valid: bool | None = None
    error: FetchError | None = None
    network_family: str | None = None
    transport_error_class: str | None = None
    failure_phase: str | None = None
    resolved_addresses: tuple[str, ...] = ()
    rejected_addresses: tuple[str, ...] = ()


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
    final_url: str | None
    domain: str | None


@dataclass(frozen=True)
class InspectionEvidence:
    pages_requested: int
    pages_analyzed: int
    limited: bool
    errors: list[dict[str, str]]


@dataclass(frozen=True)
class PageEvidence:
    url: str
    status_code: int | None
    title: str | None
    content_type: str | None
    requested_url: str | None = None


@dataclass(frozen=True)
class TransportEvidence:
    https: bool | None
    tls_valid: bool | None
    http_redirects_to_https: bool | None
    mixed_content: bool | None


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
    privacy_links: list[LinkEvidence]


@dataclass(frozen=True)
class CookieEvidence:
    detected: bool
    set_cookie_names: list[str]
    banner_detected: bool
    preferences_detected: bool


@dataclass(frozen=True)
class ContactEvidence:
    source_url: str
    email: str | None = None
    phone: str | None = None


@dataclass(frozen=True)
class EvidenceContract:
    """Evidence Contract v0.1; deliberately observational and in-memory only."""

    target: TargetEvidence
    inspection: InspectionEvidence
    pages: list[PageEvidence]
    transport: TransportEvidence
    links: list[LinkEvidence]
    forms: list[FormEvidence]
    cookies: CookieEvidence
    contacts: list[ContactEvidence]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation of the contract."""

        return asdict(self)
