import httpx

from mininode_api.web_inspector.fetcher import WebFetcher


def public_resolver(hostname: str, port: int) -> set[str]:
    return {"93.184.216.34"}


def run_with_robots(robots_status, robots_body, paths):
    requested = []

    def handler(request):
        requested.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(robots_status, text=robots_body, headers={"content-type": "text/plain"})
        return httpx.Response(200, text="ok", headers={"content-type": "text/html"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = WebFetcher(client=client, resolver=public_resolver).fetch(
        "https://example.com", [f"https://example.com{path}" for path in paths]
    )
    return result, requested


def test_robots_allows_path():
    result, requested = run_with_robots(200, "User-agent: *\nDisallow: /private", ["/public"])
    assert result.pages_fetched == 1
    assert requested == ["/robots.txt", "/public"]


def test_robots_disallows_path_without_bypass():
    result, requested = run_with_robots(200, "User-agent: *\nDisallow: /private", ["/private", "/private/child"])
    assert [page.error.code for page in result.pages] == ["robots_disallowed", "robots_disallowed"]
    assert requested == ["/robots.txt"]


def test_specific_inspector_rule_is_respected():
    result, requested = run_with_robots(200, "User-agent: Mininode-Web-Inspector\nDisallow: /secret", ["/secret"])
    assert result.pages[0].error.code == "robots_disallowed"
    assert requested == ["/robots.txt"]


def test_missing_robots_continues():
    result, requested = run_with_robots(404, "", ["/public"])
    assert result.pages_fetched == 1
    assert requested == ["/robots.txt", "/public"]
