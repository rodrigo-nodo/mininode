"""Clerk session-token verification for Mininode Access."""

from __future__ import annotations

import json
import logging
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

logger = logging.getLogger(__name__)


class ClerkIdentityConfigError(Exception):
    """Clerk identity verification is not configured."""


class ClerkIdentityInvalidError(Exception):
    """The Clerk session token is invalid or not accepted."""


class ClerkIdentityUnavailableError(Exception):
    """Clerk signing keys cannot currently be retrieved."""


class ClerkIdentityEmailUnavailableError(Exception):
    """The verified Clerk session token has no usable email claim."""


def _log_verification_failure(stage: str) -> None:
    """Log only the failed verification stage; never token or identity data."""
    logger.warning("Clerk verification failed: %s", stage)


@dataclass(frozen=True)
class ClerkIdentity:
    email: str
    subject: str


def _validate_https_origin(value: str, *, name: str) -> str:
    origin = value.strip().rstrip("/")
    parsed = urlsplit(origin)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ClerkIdentityConfigError(f"{name} must be an HTTPS origin")
    return origin


def _configuration() -> tuple[str, frozenset[str]]:
    issuer = os.getenv("CLERK_ISSUER", "").strip()
    authorized_parties_raw = os.getenv("CLERK_AUTHORIZED_PARTIES", "").strip()
    if not issuer or not authorized_parties_raw:
        raise ClerkIdentityConfigError("Clerk identity is not configured")

    normalized_issuer = _validate_https_origin(issuer, name="CLERK_ISSUER")
    authorized_parties = frozenset(
        _validate_https_origin(value, name="CLERK_AUTHORIZED_PARTIES")
        for value in authorized_parties_raw.split(",")
        if value.strip()
    )
    if not authorized_parties:
        raise ClerkIdentityConfigError("CLERK_AUTHORIZED_PARTIES is empty")

    return normalized_issuer, authorized_parties


@lru_cache(maxsize=4)
def _jwk_client(issuer: str) -> PyJWKClient:
    return PyJWKClient(f"{issuer}/.well-known/jwks.json")


def _validate_token_syntax(token: str) -> None:
    """Reject malformed client-controlled JWTs before any JWKS interaction."""

    parts = token.split(".")
    if len(parts) != 3:
        raise ClerkIdentityInvalidError("Clerk session token is invalid")

    try:
        header_bytes = jwt.utils.base64url_decode(parts[0].encode("ascii"))
        payload_bytes = jwt.utils.base64url_decode(parts[1].encode("ascii"))
        jwt.utils.base64url_decode(parts[2].encode("ascii"))
        header = json.loads(header_bytes.decode("utf-8"))
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ClerkIdentityInvalidError("Clerk session token is invalid") from exc

    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise ClerkIdentityInvalidError("Clerk session token is invalid")

    key_id = header.get("kid")
    if not isinstance(key_id, str) or not key_id.strip():
        raise ClerkIdentityInvalidError("Clerk session token key id is required")


def _resolve_signing_key(client: PyJWKClient, token: str):
    """Resolve a signing key while distinguishing token and provider failures."""

    try:
        return client.get_signing_key_from_jwt(token)
    except PyJWKClientConnectionError as exc:
        raise ClerkIdentityUnavailableError(
            "Clerk signing keys are unavailable"
        ) from exc
    except PyJWKClientError as exc:
        if "Unable to find a signing key that matches" in str(exc):
            raise ClerkIdentityInvalidError(
                "Clerk session token signing key is unknown"
            ) from exc
        raise ClerkIdentityUnavailableError(
            "Clerk signing keys are unavailable"
        ) from exc
    except (ValueError, TypeError) as exc:
        raise ClerkIdentityUnavailableError(
            "Clerk signing keys are unavailable"
        ) from exc
    except PyJWTError as exc:
        raise ClerkIdentityUnavailableError(
            "Clerk signing keys are unavailable"
        ) from exc

def verify_clerk_session(token: str) -> ClerkIdentity:
    if not token or not token.strip():
        _log_verification_failure("token_missing")
        raise ClerkIdentityInvalidError("Clerk session token is required")

    issuer, authorized_parties = _configuration()
    _validate_token_syntax(token)
    client = _jwk_client(issuer)
    signing_key = _resolve_signing_key(client, token)

    try:
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            options={
                "require": ["exp", "nbf", "iss", "sub"],
                "verify_aud": False,
            },
        )
    except PyJWTError as exc:
        _log_verification_failure(f"claims_{type(exc).__name__}")
        raise ClerkIdentityInvalidError("Clerk session token is invalid") from exc

    authorized_party = payload.get("azp")
    if not isinstance(authorized_party, str) or authorized_party not in authorized_parties:
        _log_verification_failure("authorized_party")
        raise ClerkIdentityInvalidError("Clerk authorized party is invalid")

    if payload.get("sts") == "pending":
        _log_verification_failure("session_pending")
        raise ClerkIdentityInvalidError("Clerk session is pending")

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        _log_verification_failure("subject")
        raise ClerkIdentityInvalidError("Clerk subject is required")

    email = payload.get("email")
    if not isinstance(email, str) or not email.strip():
        _log_verification_failure("email")
        raise ClerkIdentityEmailUnavailableError(
            "Verified Clerk session has no email claim"
        )

    return ClerkIdentity(
        email=access.normalize_email(email),
        subject=subject,
    )
