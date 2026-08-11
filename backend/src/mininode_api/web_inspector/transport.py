"""HTTP transport that connects only to an SSRF-validated IP address."""

from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from typing import Iterable

import httpx


VALIDATED_IP_EXTENSION = "mininode_validated_ip"


class MissingValidatedIPError(httpx.TransportError):
    """Raised when code attempts a request without pinning its destination."""


def _connect_pinned(
    pinned_ip: str,
    port: int,
    timeout: float | None,
    source_address: tuple[str, int] | None,
) -> socket.socket:
    """Connect numerically, without even invoking the system DNS resolver."""

    address = ipaddress.ip_address(pinned_ip)
    family = socket.AF_INET6 if address.version == 6 else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        sock.settimeout(timeout)
        if source_address:
            sock.bind(source_address)
        destination = (pinned_ip, port, 0, 0) if address.version == 6 else (pinned_ip, port)
        sock.connect(destination)
    except Exception:
        sock.close()
        raise
    return sock


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, hostname: str, pinned_ip: str, **kwargs: object) -> None:
        super().__init__(hostname, **kwargs)
        self._pinned_ip = pinned_ip

    def connect(self) -> None:
        self.sock = _connect_pinned(self._pinned_ip, self.port, self.timeout, self.source_address)
        if self._tunnel_host:
            self._tunnel()


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to a pinned IP while authenticating the original hostname."""

    def __init__(self, hostname: str, pinned_ip: str, **kwargs: object) -> None:
        super().__init__(hostname, **kwargs)
        self._pinned_ip = pinned_ip

    def connect(self) -> None:
        self.sock = _connect_pinned(self._pinned_ip, self.port, self.timeout, self.source_address)
        if self._tunnel_host:
            self._tunnel()
        # self.host remains the URL hostname, never the pinned address. This is
        # therefore both the TLS SNI value and the certificate-validation name.
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)


class _ResponseStream(httpx.SyncByteStream):
    def __init__(
        self,
        response: http.client.HTTPResponse,
        connection: http.client.HTTPConnection,
        request: httpx.Request,
    ) -> None:
        self._response = response
        self._connection = connection
        self._request = request

    def __iter__(self) -> Iterable[bytes]:
        try:
            while chunk := self._response.read(64 * 1024):
                yield chunk
        except socket.timeout as exc:
            raise httpx.ReadTimeout(str(exc), request=self._request) from exc
        except (OSError, http.client.HTTPException) as exc:
            raise httpx.ReadError(str(exc), request=self._request) from exc

    def close(self) -> None:
        self._response.close()
        self._connection.close()


class PinnedHTTPTransport(httpx.BaseTransport):
    """Use an IP passed by the SSRF guard without performing DNS resolution."""

    def __init__(self, *, ssl_context: ssl.SSLContext | None = None) -> None:
        self._ssl_context = ssl_context or ssl.create_default_context()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        pinned_ip = request.extensions.get(VALIDATED_IP_EXTENSION)
        if not isinstance(pinned_ip, str):
            raise MissingValidatedIPError("A validated destination IP is required")

        hostname = request.url.host
        port = request.url.port
        timeout = request.extensions.get("timeout", {}).get("connect")
        if request.url.scheme == "https":
            connection: http.client.HTTPConnection = _PinnedHTTPSConnection(
                hostname,
                pinned_ip,
                port=port,
                timeout=timeout,
                context=self._ssl_context,
            )
        else:
            connection = _PinnedHTTPConnection(hostname, pinned_ip, port=port, timeout=timeout)

        target = request.url.raw_path.decode("ascii")
        headers = {key.decode("ascii"): value.decode("latin-1") for key, value in request.headers.raw}
        try:
            connection.request(request.method, target, headers=headers)
            response = connection.getresponse()
        except socket.timeout as exc:
            connection.close()
            raise httpx.ConnectTimeout(str(exc), request=request) from exc
        except (OSError, http.client.HTTPException) as exc:
            connection.close()
            raise httpx.ConnectError(str(exc), request=request) from exc
        return httpx.Response(
            response.status,
            headers=response.getheaders(),
            stream=_ResponseStream(response, connection, request),
            request=request,
        )
