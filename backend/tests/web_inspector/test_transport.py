import socket

from mininode_api.web_inspector.transport import _PinnedHTTPConnection, _PinnedHTTPSConnection


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
