"""Cloudflare Access identity verification for Mininode Access."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlsplit

import jwt
from jwt import PyJWKClient
from jwt.exceptions import (
    PyJWKClientConnectionError,
    PyJWKClientError,
    PyJWTError,
)

from mininode_api.services import access


class AccessIdentityConfigError(Exception):
    """Cloudflare Access identity verification is not configured."""


class AccessIdentityInvalidError(Exception):
    """The Cloudflare Access assertion is missing, invalid, or not an app token."""


class AccessIdentityUnavailableError(Exception):
    """Cloudflare Access signing keys cannot currently be retrieved."""


class AccessIdentityEmailUnavailableError(Exception):
    """The verified Access application token has no user email."""


@dataclass(frozen=True)
class AccessIdentity:
    email: str


def _configuration() -> tuple[str, str]:
    team_domain = os.getenv("CF_ACCESS_TEAM_DOMAIN", "").strip().rstrip("/")
    audience = os.getenv("CF_ACCESS_AUD", "").strip()
    if not team_domain or not audience:
        raise AccessIdentityConfigError("Cloudflare Access identity is not configured")

    parsed = urlsplit(team_domain)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise AccessIdentityConfigError("CF_ACCESS_TEAM_DOMAIN must be an HTTPS origin")
    return team_domain, audience


@lru_cache(maxsize=4)
def _jwk_client(team_domain: str) -> PyJWKClient:
    return PyJWKClient(f"{team_domain}/cdn-cgi/access/certs")


def verify_access_jwt(token: str) -> AccessIdentity:
    if not token or not token.strip():
        raise AccessIdentityInvalidError("Cloudflare Access assertion is required")

    team_domain, audience = _configuration()
    client = _jwk_client(team_domain)
    try:
        signing_key = client.get_signing_key_from_jwt(token)
    except PyJWKClientConnectionError as exc:
        raise AccessIdentityUnavailableError(
            "Cloudflare Access signing keys are unavailable"
        ) from exc
    except PyJWKClientError as exc:
        raise AccessIdentityInvalidError("Cloudflare Access assertion is invalid") from exc

    try:
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=team_domain,
            options={"require": ["exp", "iss", "aud"]},
        )
    except PyJWTError as exc:
        raise AccessIdentityInvalidError("Cloudflare Access assertion is invalid") from exc

    if payload.get("type") != "app":
        raise AccessIdentityInvalidError("Cloudflare Access application token is required")

    email = payload.get("email")
    if not isinstance(email, str) or not email.strip():
        raise AccessIdentityEmailUnavailableError(
            "Verified Cloudflare Access identity has no email"
        )

    return AccessIdentity(email=access.normalize_email(email))
