"""Contract: only demonstrated apex/www redirect equivalence is accepted."""
from types import SimpleNamespace

import pytest

from mininode_api.services.site_equivalence import inspect_www_equivalence


class FakeFetcher:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def _fetch_page(self, url, hostname, *, deadline=None):
        self.calls.append((url, hostname))
        return self.pages[url]


def page(host, redirects=0, *, error=None, status=200, scheme="https"):
    return SimpleNamespace(error=error, status_code=status,
                           final_url=f"{scheme}://{host}/", redirect_count=redirects)


@pytest.mark.parametrize("pages, expected", [
    ({"https://example.com/": page("www.example.com", 1),
      "https://www.example.com/": page("www.example.com")}, True),
    ({"https://example.com/": page("example.com"),
      "https://www.example.com/": page("www.example.com")}, False),
    ({"https://example.com/": page("example.com"),
      "https://www.example.com/": page("example.com", 1)}, True),
    ({"https://example.com/": page("www.example.com", 1),
      "https://www.example.com/": page("example.com", 1)}, False),
    ({"https://example.com/": page("www.example.com", 1),
      "https://www.example.com/": page("www.example.com", error=Exception())}, False),
    ({"https://example.com/": page("www.example.com", 1),
      "https://www.example.com/": page("www.example.com", status=403)}, False),
    ({"https://example.com/": page("www.example.com", 1),
      "https://www.example.com/": page("www.example.com", scheme="http")}, False),
])
def test_www_proof_requires_successful_convergence_and_redirect(pages, expected):
    fetcher = FakeFetcher(pages)
    result = inspect_www_equivalence("https://example.com/", fetcher=fetcher)
    assert result.equivalent is expected
    assert len(fetcher.calls) == 2
    assert all(hostname == "example.com" for _, hostname in fetcher.calls)


def test_www_subdomains_not_merged_by_inference():
    fetcher = FakeFetcher({})
    result = inspect_www_equivalence("shop.example.com", fetcher=fetcher)
    assert not result.equivalent
    assert fetcher.calls == []


@pytest.mark.parametrize("url", ["localhost", "http://127.0.0.1", "http://admin:pass@example.com", "file:///etc/hosts"])
def test_unsafe_input_rejected_without_fetch(url):
    with pytest.raises(ValueError):
        inspect_www_equivalence(url, fetcher=FakeFetcher({}))
