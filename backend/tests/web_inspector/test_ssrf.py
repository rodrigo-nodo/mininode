import pytest

from mininode_api.web_inspector.ssrf import (
    DNSResolutionError,
    InvalidTargetError,
    UnsafeTargetError,
    UnsupportedSchemeError,
    validate_url,
)


def public_resolver(hostname: str, port: int) -> set[str]:
    return {"93.184.216.34"}


def test_allows_public_https_destination():
    assert validate_url("https://example.com/path", public_resolver) == {"93.184.216.34"}


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost",
        "http://127.0.0.1",
        "http://10.2.3.4",
        "http://172.16.2.3",
        "http://192.168.4.5",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]",
        "http://[fc00::1]",
        "http://[fe80::1]",
    ],
)
def test_rejects_non_public_destinations(url):
    with pytest.raises(UnsafeTargetError):
        validate_url(url, public_resolver)


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/file"])
def test_rejects_unsupported_schemes(url):
    with pytest.raises(UnsupportedSchemeError):
        validate_url(url, public_resolver)


def test_rejects_embedded_credentials():
    with pytest.raises(InvalidTargetError):
        validate_url("https://user:password@example.com", public_resolver)


def test_rejects_hostname_resolving_to_private_ip():
    with pytest.raises(UnsafeTargetError):
        validate_url("https://apparently-public.example", lambda hostname, port: {"10.0.0.7"})


def test_rejects_mixed_public_and_private_dns_answers():
    with pytest.raises(UnsafeTargetError) as raised:
        validate_url("https://example.com", lambda hostname, port: {"93.184.216.34", "127.0.0.1"})
    assert raised.value.resolved_addresses == ("127.0.0.1", "93.184.216.34")
    assert raised.value.rejected_addresses == ("127.0.0.1",)


def test_dns_resolution_failure_has_a_distinct_error():
    def failing_resolver(hostname, port):
        raise OSError("resolver unavailable")

    with pytest.raises(DNSResolutionError) as raised:
        validate_url("https://example.com", failing_resolver)
    assert raised.value.hostname == "example.com"
