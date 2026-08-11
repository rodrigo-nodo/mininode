import http.client
import socket

import httpx

from mininode_api.web_inspector.transport import (
    VALIDATED_IP_EXTENSION,
    PinnedHTTPTransport,
    _PinnedHTTPConnection,
    _PinnedHTTPSConnection,
)


class FakeSocket:
    def __init__(self, connections):
        self.connections = connections

    def settimeout(self, timeout):
        self.timeout = timeout

    def connect(self, address):
        self.connections.append(address)

    def bind(self, source_address):
        self.source_address = source_address

    def close(self):
        pass


def test_http_connection_uses_pinned_ip_without_dns(monkeypatch):
    connections = []

    def fail_if_resolved(*args, **kwargs):
        raise AssertionError("the pinned transport must not resolve DNS")

    monkeypatch.setattr(socket, "getaddrinfo", fail_if_resolved)
    monkeypatch.setattr(socket, "socket", lambda family, kind: FakeSocket(connections))

    connection = _PinnedHTTPConnection("example.com", "93.184.216.34", port=80)
    connection.connect()

    assert connections == [("93.184.216.34", 80)]


def test_rebinding_dns_cannot_change_effective_connection(monkeypatch):
    connected = []

    # This is the simulated second DNS answer. It must never be consulted.
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(socket.AF_INET, 0, 0, "", ("127.0.0.1", 80))])
    monkeypatch.setattr(socket, "socket", lambda family, kind: FakeSocket(connected))

    _PinnedHTTPConnection("example.com", "93.184.216.34", port=80).connect()

    assert connected == [("93.184.216.34", 80)]


def test_https_connects_to_pin_but_preserves_hostname_for_sni(monkeypatch):
    connected = []
    wrapped = []

    class FakeContext:
        def wrap_socket(self, sock, *, server_hostname):
            wrapped.append((sock, server_hostname))
            return sock

    sock = FakeSocket(connected)
    monkeypatch.setattr(socket, "socket", lambda family, kind: sock)

    connection = _PinnedHTTPSConnection(
        "example.com", "93.184.216.34", port=443, context=FakeContext()
    )
    connection.connect()

    assert connected == [("93.184.216.34", 443)]
    assert wrapped == [(sock, "example.com")]


def test_pinned_https_transport_preserves_tcp_ip_sni_certificate_name_and_host(monkeypatch):
    connected = []
    server_hostnames = []
    sent_headers = {}

    class FakeContext:
        check_hostname = True

        def wrap_socket(self, sock, *, server_hostname):
            server_hostnames.append(server_hostname)
            return sock

    class FakeResponse:
        status = 200

        def getheaders(self):
            return [("content-type", "text/html")]

        def read(self, size):
            return b""

        def close(self):
            pass

    def fail_if_resolved(*args, **kwargs):
        raise AssertionError("HTTPS connection must not resolve the hostname again")

    def fake_request(connection, method, target, body=None, headers=None, **kwargs):
        connection.connect()
        sent_headers.update(headers or {})

    monkeypatch.setattr(socket, "getaddrinfo", fail_if_resolved)
    monkeypatch.setattr(socket, "socket", lambda family, kind: FakeSocket(connected))
    monkeypatch.setattr(http.client.HTTPSConnection, "request", fake_request)
    monkeypatch.setattr(http.client.HTTPSConnection, "getresponse", lambda connection: FakeResponse())

    request = httpx.Request(
        "GET",
        "https://example.com/test",
        extensions={VALIDATED_IP_EXTENSION: "93.184.216.34"},
    )
    ssl_context = FakeContext()
    response = PinnedHTTPTransport(ssl_context=ssl_context).handle_request(request)
    response.close()

    normalized_headers = {key.lower(): value for key, value in sent_headers.items()}
    assert connected == [("93.184.216.34", 443)]
    assert server_hostnames == ["example.com"]
    assert ssl_context.check_hostname is True
    assert normalized_headers["host"] == "example.com"
