import httpx

from mininode_api.web_inspector.extractor import build_evidence
from mininode_api.web_inspector.fetcher import WebFetcher
from mininode_api.web_inspector.include_discovery import (
    MAX_INCLUDES_PER_PAGE,
    discover_include_links,
)
from mininode_api.web_inspector.models import FetchPageResult, InspectionFetchResult
from mininode_api.web_inspector.selector import select_pages

HOME = "https://example.com/"


def public_resolver(hostname: str, port: int) -> set[str]:
    return {"93.184.216.34"}


def discover(home_html, bodies, *, resolver=public_resolver, budget=lambda: 30.0):
    requested = []

    def handler(request):
        requested.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(404, headers={"content-type": "text/plain"})
        body = bodies.get(request.url.path)
        if isinstance(body, Exception):
            raise body
        if body is None:
            return httpx.Response(404, headers={"content-type": "text/html"})
        if isinstance(body, tuple):
            content_type, body = body
        else:
            content_type = "text/html"
        return httpx.Response(200, text=body, headers={"content-type": content_type})

    def factory(inspection_budget):
        client = httpx.Client(transport=httpx.MockTransport(handler))
        return WebFetcher(client=client, resolver=resolver, inspection_budget=inspection_budget)

    links = discover_include_links(home_html, HOME, factory, budget)
    return links, requested


def test_relative_include_and_root_based_data_rel_reach_selector():
    links, requested = discover(
        '<div data-include="partials/footer.html"></div>',
        {
            "/partials/footer.html": """
                <a href="#" data-rel="contact/index.html">Contacto</a>
                <a href="#" data-rel="legal/privacy/index.html">Política de privacidad</a>
            """,
        },
    )

    assert [link.url for link in links] == [
        "https://example.com/contact/index.html",
        "https://example.com/legal/privacy/index.html",
    ]
    assert select_pages(HOME, links) == [
        HOME,
        "https://example.com/legal/privacy/index.html",
        "https://example.com/contact/index.html",
    ]
    assert "https://example.com/partials/footer.html" in requested


def test_include_links_enter_evidence_without_turning_fragment_into_a_page():
    links, _ = discover(
        '<div data-include="partials/footer.html"></div>',
        {
            "/partials/footer.html": (
                '<a href="#" data-rel="legal/privacy/index.html">'
                "Política de privacidad</a>"
            ),
        },
    )
    fetched = InspectionFetchResult(
        target_url=HOME,
        pages_requested=1,
        pages_fetched=1,
        pages=[
            FetchPageResult(
                requested_url=HOME,
                final_url=HOME,
                status_code=200,
                content_type="text/html",
                html='<div data-include="partials/footer.html"></div>',
            )
        ],
    )

    evidence = build_evidence(fetched, additional_links=links)

    assert [(link.url, link.text, link.source_url) for link in evidence.links] == [
        (
            "https://example.com/legal/privacy/index.html",
            "Política de privacidad",
            "https://example.com/partials/footer.html",
        )
    ]
    assert [page.url for page in evidence.pages] == [HOME]
    assert evidence.inspection.pages_analyzed == 1


def test_absolute_same_hostname_include_and_normal_href_are_supported():
    links, _ = discover(
        '<div data-include="https://example.com/partials/footer.html"></div>',
        {"/partials/footer.html": '<a href="../contact">Contacto</a>'},
    )
    assert [link.url for link in links] == ["https://example.com/contact"]


def test_external_include_is_rejected_without_creating_a_fetcher():
    links, requested = discover(
        '<div data-include="https://outside.example/footer.html"></div>', {}
    )
    assert links == []
    assert requested == []


def test_private_dns_answer_is_blocked_by_web_fetcher_ssrf_guard():
    links, requested = discover(
        '<div data-include="/footer.html"></div>',
        {"/footer.html": '<a href="/contact">Contacto</a>'},
        resolver=lambda hostname, port: {"127.0.0.1"},
    )
    assert links == []
    assert requested == []


def test_at_most_five_unique_includes_are_fetched_and_duplicates_are_removed():
    includes = ['<div data-include="/p0.html"></div>']
    includes += [f'<div data-include="/p{i}.html"></div>' for i in range(7)]
    bodies = {f"/p{i}.html": f'<a href="/contact{i}">Contact {i}</a>' for i in range(7)}
    links, requested = discover("".join(includes), bodies)

    fragment_requests = [url for url in requested if not url.endswith("/robots.txt")]
    assert len(fragment_requests) == MAX_INCLUDES_PER_PAGE
    assert fragment_requests.count("https://example.com/p0.html") == 1
    assert len(links) == MAX_INCLUDES_PER_PAGE


def test_nested_include_is_not_followed():
    links, requested = discover(
        '<div data-include="/first.html"></div>',
        {
            "/first.html": '<div data-include="/second.html"></div><a href="/contact">Contacto</a>',
            "/second.html": '<a href="/privacy">Privacidad</a>',
        },
    )
    assert [link.url for link in links] == ["https://example.com/contact"]
    assert "https://example.com/second.html" not in requested


def test_external_data_rel_is_discarded_instead_of_becoming_internal():
    links, _ = discover(
        '<div data-include="/footer.html"></div>',
        {"/footer.html": '<a href="#" data-rel="https://outside.example/contact">Contacto</a>'},
    )
    assert links == []


def test_failed_include_is_ignored_and_other_links_remain_available():
    links, _ = discover(
        '<div data-include="/slow.html"></div><div data-include="/footer.html"></div>',
        {
            "/slow.html": httpx.ReadTimeout("slow"),
            "/footer.html": '<a href="/contact">Contacto</a>',
        },
    )
    assert [link.url for link in links] == ["https://example.com/contact"]


def test_exhausted_shared_budget_skips_auxiliary_fetches():
    links, requested = discover(
        '<div data-include="/footer.html"></div>',
        {"/footer.html": '<a href="/contact">Contacto</a>'},
        budget=lambda: 0.0,
    )
    assert links == []
    assert requested == []


def test_non_html_include_is_ignored():
    links, _ = discover(
        '<div data-include="/footer.json"></div>',
        {"/footer.json": ("application/json", "{}")},
    )
    assert links == []
