import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.exceptions import PyJWKClientError

BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.services import clerk_identity  # noqa: E402


@pytest.fixture
def configured_clerk(monkeypatch):
    monkeypatch.setenv(
        "CLERK_ISSUER",
        "https://helping-puma-182.clerk.accounts.dev",
    )
    monkeypatch.setenv(
        "CLERK_AUTHORIZED_PARTIES",
        "https://app.mininode.io",
    )


def _token():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "azp": "https://app.mininode.io",
            "email": "person@example.com",
            "exp": now + timedelta(minutes=5),
            "iat": now,
            "nbf": now - timedelta(seconds=1),
            "iss": "https://helping-puma-182.clerk.accounts.dev",
            "sub": "user_test_123",
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )


def test_unusable_jwks_is_provider_unavailable(configured_clerk, monkeypatch):
    def no_keys(_token):
        raise PyJWKClientError("The JWKS endpoint did not contain any signing keys")

    monkeypatch.setattr(
        clerk_identity,
        "_jwk_client",
        lambda _issuer: SimpleNamespace(get_signing_key_from_jwt=no_keys),
    )

    with pytest.raises(clerk_identity.ClerkIdentityUnavailableError):
        clerk_identity.verify_clerk_session(_token())


def test_malformed_jwks_is_provider_unavailable(configured_clerk, monkeypatch):
    def malformed(_token):
        raise json.JSONDecodeError("bad jwks", "{", 1)

    monkeypatch.setattr(
        clerk_identity,
        "_jwk_client",
        lambda _issuer: SimpleNamespace(get_signing_key_from_jwt=malformed),
    )

    with pytest.raises(clerk_identity.ClerkIdentityUnavailableError):
        clerk_identity.verify_clerk_session(_token())


def test_unknown_kid_remains_invalid_identity(configured_clerk, monkeypatch):
    def unknown_key(_token):
        raise PyJWKClientError(
            'Unable to find a signing key that matches: "unknown-key"'
        )

    monkeypatch.setattr(
        clerk_identity,
        "_jwk_client",
        lambda _issuer: SimpleNamespace(get_signing_key_from_jwt=unknown_key),
    )

    with pytest.raises(clerk_identity.ClerkIdentityInvalidError):
        clerk_identity.verify_clerk_session(_token())
