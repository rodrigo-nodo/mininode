import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.main import create_app  # noqa: E402
from mininode_api.services import access, access_identity, clerk_identity  # noqa: E402


@pytest.fixture
def client():
    app = create_app()
    app.state.access_ready = True
    return TestClient(app)


def _signed_clerk_token(
    private_key,
    *,
    issuer="https://helping-puma-182.clerk.accounts.dev",
    azp="https://app.mininode.io",
    email="Person@Example.COM",
    subject="user_test_123",
    status=None,
):
    now = datetime.now(timezone.utc)
    payload = {
        "azp": azp,
        "email": email,
        "exp": now + timedelta(minutes=5),
        "iat": now,
        "nbf": now - timedelta(seconds=1),
        "iss": issuer,
        "sid": "sess_test_123",
        "sub": subject,
    }
    if status is not None:
        payload["sts"] = status

    return jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": "clerk-test-key"},
    )


def _configure_clerk(monkeypatch, public_key):
    monkeypatch.setenv(
        "CLERK_ISSUER",
        "https://helping-puma-182.clerk.accounts.dev",
    )
    monkeypatch.setenv(
        "CLERK_AUTHORIZED_PARTIES",
        "https://app.mininode.io,https://preview.example",
    )
    monkeypatch.setattr(
        clerk_identity,
        "_jwk_client",
        lambda _issuer: SimpleNamespace(
            get_signing_key_from_jwt=lambda _token: SimpleNamespace(key=public_key)
        ),
    )


def test_verify_clerk_session_checks_signature_issuer_azp_and_normalizes_email(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _configure_clerk(monkeypatch, private_key.public_key())

    identity = clerk_identity.verify_clerk_session(_signed_clerk_token(private_key))

    assert identity.email == "person@example.com"
    assert identity.subject == "user_test_123"


def test_verify_clerk_session_rejects_wrong_authorized_party(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _configure_clerk(monkeypatch, private_key.public_key())

    with pytest.raises(clerk_identity.ClerkIdentityInvalidError):
        clerk_identity.verify_clerk_session(
            _signed_clerk_token(private_key, azp="https://attacker.example")
        )


def test_verify_clerk_session_rejects_wrong_issuer(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _configure_clerk(monkeypatch, private_key.public_key())

    with pytest.raises(clerk_identity.ClerkIdentityInvalidError):
        clerk_identity.verify_clerk_session(
            _signed_clerk_token(private_key, issuer="https://other.clerk.accounts.dev")
        )


def test_verify_clerk_session_rejects_invalid_signature(monkeypatch):
    trusted_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _configure_clerk(monkeypatch, trusted_key.public_key())

    with pytest.raises(clerk_identity.ClerkIdentityInvalidError):
        clerk_identity.verify_clerk_session(_signed_clerk_token(other_key))


def test_verify_clerk_session_requires_email_claim(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _configure_clerk(monkeypatch, private_key.public_key())

    with pytest.raises(clerk_identity.ClerkIdentityEmailUnavailableError):
        clerk_identity.verify_clerk_session(
            _signed_clerk_token(private_key, email="")
        )


def test_verify_clerk_session_rejects_pending_session(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _configure_clerk(monkeypatch, private_key.public_key())

    with pytest.raises(clerk_identity.ClerkIdentityInvalidError):
        clerk_identity.verify_clerk_session(
            _signed_clerk_token(private_key, status="pending")
        )


def test_access_me_accepts_clerk_bearer_and_provisions_same_canonical_user(
    client,
    monkeypatch,
):
    user_id = uuid4()
    calls = []

    monkeypatch.setattr(
        clerk_identity,
        "verify_clerk_session",
        lambda token: clerk_identity.ClerkIdentity(
            email="person@example.com",
            subject="user_clerk_123",
        ),
    )
    monkeypatch.setattr(
        access,
        "get_or_create_user",
        lambda email: calls.append(email)
        or access.StoredUser(id=user_id, email="person@example.com"),
    )

    response = client.get(
        "/access/me",
        headers={"Authorization": "Bearer signed-clerk-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": str(user_id),
        "email": "person@example.com",
    }
    assert calls == ["person@example.com"]


def test_clerk_bearer_takes_precedence_and_never_falls_back_to_cloudflare(
    client,
    monkeypatch,
):
    cloudflare_calls = []

    def invalid_clerk(_token):
        raise clerk_identity.ClerkIdentityInvalidError("bad token")

    monkeypatch.setattr(clerk_identity, "verify_clerk_session", invalid_clerk)
    monkeypatch.setattr(
        access_identity,
        "verify_access_jwt",
        lambda token: cloudflare_calls.append(token)
        or access_identity.AccessIdentity(email="cloudflare@example.com"),
    )

    response = client.get(
        "/access/me",
        headers={
            "Authorization": "Bearer invalid-clerk-token",
            "Cf-Access-Jwt-Assertion": "valid-cloudflare-token",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid Clerk identity"
    assert cloudflare_calls == []


@pytest.mark.parametrize(
    "authorization",
    [
        "",
        "Basic abc123",
        "Bearer",
        "Bearer ",
        "bearer",
    ],
)
def test_access_me_rejects_malformed_authorization_header(
    client,
    authorization,
):
    headers = {"Authorization": authorization} if authorization else {}
    response = client.get("/access/me", headers=headers)

    assert response.status_code == 401


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (clerk_identity.ClerkIdentityInvalidError("bad token"), 401),
        (clerk_identity.ClerkIdentityEmailUnavailableError("no email"), 403),
        (clerk_identity.ClerkIdentityConfigError("missing config"), 503),
        (clerk_identity.ClerkIdentityUnavailableError("jwks unavailable"), 503),
    ],
)
def test_access_me_maps_clerk_identity_failures(client, monkeypatch, error, status_code):
    def fail(_token):
        raise error

    monkeypatch.setattr(clerk_identity, "verify_clerk_session", fail)

    response = client.get(
        "/access/me",
        headers={"Authorization": "Bearer signed-clerk-token"},
    )

    assert response.status_code == status_code
