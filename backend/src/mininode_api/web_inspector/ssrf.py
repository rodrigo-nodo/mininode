"""URL and DNS validation used before every Web Inspector request."""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Iterable
from urllib.parse import urlsplit


class SSRFGuardError(ValueError):
    """Base class for rejected or unresolvable destinations."""

    def __init__(
        self,
        message: str,
        *,
        hostname: str | None = None,
        resolved_addresses: Iterable[str] = (),
        rejected_addresses: Iterable[str] = (),
    ) -> None:
        super().__init__(message)
        self.hostname = hostname
        self.resolved_addresses = tuple(sorted(resolved_addresses))
        self.rejected_addresses = tuple(sorted(rejected_addresses))


class UnsupportedSchemeError(SSRFGuardError):
    pass


class InvalidTargetError(SSRFGuardError):
    pass


class UnsafeTargetError(SSRFGuardError):
    pass


class DNSResolutionError(SSRFGuardError):
    pass


Resolver = Callable[[str, int], Iterable[str]]


def system_resolver(hostname: str, port: int) -> set[str]:
    """Resolve every address so the guard can reject mixed public/private DNS."""

    try:
        answers = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise DNSResolutionError(f"DNS resolution failed for {hostname}", hostname=hostname) from exc
    addresses = {answer[4][0] for answer in answers}
    if not addresses:
        raise DNSResolutionError(f"DNS returned no addresses for {hostname}", hostname=hostname)
    return addresses


def is_public_address(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    # is_global excludes private, loopback, link-local, multicast, reserved,
    # unspecified, documentation, and other non-public IPv4/IPv6 ranges.
    return ip.is_global


def validate_url(url: str, resolver: Resolver = system_resolver) -> set[str]:
    """Validate syntax and all current DNS answers before an HTTP request."""

    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise InvalidTargetError(f"Invalid URL: {url}") from exc
    if parsed.scheme.lower() not in {"http", "https"}:
        raise UnsupportedSchemeError(f"Unsupported URL scheme: {parsed.scheme or '(missing)'}")
    if parsed.username is not None or parsed.password is not None:
        raise InvalidTargetError("Embedded URL credentials are not allowed")
    hostname = parsed.hostname
    if not hostname:
        raise InvalidTargetError("URL must include a hostname")
    hostname = hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise UnsafeTargetError(f"Unsafe target hostname: {hostname}", hostname=hostname)
    effective_port = port or (443 if parsed.scheme.lower() == "https" else 80)
    try:
        literal = ipaddress.ip_address(hostname)
        addresses = {str(literal)}
    except ValueError:
        try:
            addresses = set(resolver(hostname, effective_port))
        except DNSResolutionError:
            raise
        except (OSError, socket.gaierror) as exc:
            raise DNSResolutionError(f"DNS resolution failed for {hostname}", hostname=hostname) from exc
    if not addresses:
        raise DNSResolutionError(f"DNS returned no addresses for {hostname}", hostname=hostname)
    unsafe = sorted(address for address in addresses if not is_public_address(address))
    if unsafe:
        raise UnsafeTargetError(
            f"Target resolves to a non-public address: {', '.join(unsafe)}",
            hostname=hostname,
            resolved_addresses=addresses,
            rejected_addresses=unsafe,
        )
    return addresses
