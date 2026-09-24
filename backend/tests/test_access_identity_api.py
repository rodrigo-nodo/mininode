import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import jwt
import psycopg
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.main import create_app  # noqa: E402
from mininode_api.services import access, access_identity  # noqa: E402


@pytest.fixture
def client():
    app = create_app()
    app.state.access_ready = True
    return TestClient(app)


def test_access_me_provisions_verified_user(client, monkeypatch):
    user_id = uuid4()
    calls = []
    monkeypatch.setattr(
        access_identity,
        "verify_access_jwt",
        lambda token: access_identity.AccessIdentity(email="person@example.com"),
    )
    monkeypatch.setattr(
        access,
        "get_or_create_user",
        lambda email: calls.append(email)
        or access.StoredUser(id=user_id, email="person@example.com"),
    )

    response = client.get(
        "/access/me",
        headers={"Cf-Access-Jwt-Assertion": "signed-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": str(user_id),
        "email": "person@example.com",
    }
    assert calls == ["person@example.com"]


def test_access_me_requires_cloudflare_assertion_even_with_api_key(client):
    response = client.get("/access/me", headers={"X-Api-Key": "not-identity"})
    assert response.status_code == 401


def test_access_me_returns_401_for_malformed_assertion(client, monkeypatch):
    monkeypatch.setenv("CF_ACCESS_TEAM_DOMAIN", "https://team.cloudflareaccess.com")
    monkeypatch.setenv("CF_ACCESS_AUD", "app-aud")

    class ParsingJwkClient:
        def get_signing_key_from_jwt(self, token):
            jwt.get_unverified_header(token)
            raise AssertionError("malformed token unexpectedly parsed")

    monkeypatch.setattr(
        access_identity,
        "_jwk_client",
        lambda _domain: ParsingJwkClient(),
    )

    response = client.get(
        "/access/me",
        headers={"Cf-Access-Jwt-Assertion": "not-a-jwt"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid Cloudflare Access identity"


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (access_identity.AccessIdentityInvalidError("bad token"), 401),
        (access_identity.AccessIdentityEmailUnavailableError("no email"), 403),
        (access_identity.AccessIdentityConfigError("missing config"), 503),
        (access_identity.AccessIdentityUnavailableError("jwks unavailable"), 503),
    ],
)
def test_access_me_maps_identity_failures(client, monkeypatch, error, status_code):
    def fail(_token):
        raise error

    monkeypatch.setattr(access_identity, "verify_access_jwt", fail)
    response = client.get(
        "/access/me",
        headers={"Cf-Access-Jwt-Assertion": "signed-token"},
    )
    assert response.status_code == status_code


def test_access_me_requires_ready_access_database(monkeypatch):
    app = create_app()
    app.state.access_ready = False
    with TestClient(app) as client:
        app.state.access_ready = False
        response = client.get(
            "/access/me",
            headers={"Cf-Access-Jwt-Assertion": "signed-token"},
        )
    assert response.status_code == 503


def test_access_me_hides_runtime_database_failure(client, monkeypatch):
    monkeypatch.setattr(
        access_identity,
        "verify_access_jwt",
        lambda _token: access_identity.AccessIdentity(email="person@example.com"),
    )

    def fail(_email):
        raise RuntimeError("database connection failed")

    monkeypatch.setattr(access, "get_or_create_user", fail)
    response = client.get(
        "/access/me",
        headers={"Cf-Access-Jwt-Assertion": "signed-token"},
    )
    assert response.status_code == 503
    assert "database" not in response.text.lower()


def _signed_token(private_key, *, audience="app-aud", email="Person@Example.COM"):
    now = datetime.now(timezone.utc)
    payload = {
        "aud": [audience],
        "email": email,
        "exp": now + timedelta(minutes=5),
        "iat": now,
        "nbf": now - timedelta(seconds=1),
        "iss": "https://team.cloudflareaccess.com",
        "type": "app",
        "sub": "cf-user-123",
    }
    return jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )


def _configure_identity(monkeypatch, public_key):
    monkeypatch.setenv("CF_ACCESS_TEAM_DOMAIN", "https://team.cloudflareaccess.com")
    monkeypatch.setenv("CF_ACCESS_AUD", "app-aud")
    monkeypatch.setattr(
        access_identity,
        "_jwk_client",
        lambda _domain: SimpleNamespace(
            get_signing_key_from_jwt=lambda _token: SimpleNamespace(key=public_key)
        ),
    )


def test_verify_access_jwt_checks_signature_issuer_audience_and_normalizes_email(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _configure_identity(monkeypatch, private_key.public_key())

    identity = access_identity.verify_access_jwt(_signed_token(private_key))

    assert identity.email == "person@example.com"


def test_verify_access_jwt_rejects_wrong_audience(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _configure_identity(monkeypatch, private_key.public_key())

    with pytest.raises(access_identity.AccessIdentityInvalidError):
        access_identity.verify_access_jwt(
            _signed_token(private_key, audience="another-app")
        )


def test_verify_access_jwt_rejects_invalid_signature(monkeypatch):
    trusted_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _configure_identity(monkeypatch, trusted_key.public_key())

    with pytest.raises(access_identity.AccessIdentityInvalidError):
        access_identity.verify_access_jwt(_signed_token(other_key))


def test_verify_access_jwt_requires_user_email(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _configure_identity(monkeypatch, private_key.public_key())

    with pytest.raises(access_identity.AccessIdentityEmailUnavailableError):
        access_identity.verify_access_jwt(_signed_token(private_key, email=""))


def test_get_or_create_user_is_idempotent_on_real_postgres():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required for the PostgreSQL integration test")

    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA IF EXISTS access CASCADE")

    try:
        access.initialize_database()
        first = access.get_or_create_user("  Person@Example.COM ")
        second = access.get_or_create_user("person@example.com")

        assert first.id == second.id
        assert first.email == "person@example.com"
        assert second.email == "person@example.com"

        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT id, email FROM access.users")
            rows = cursor.fetchall()
        assert rows == [(first.id, "person@example.com")]
    finally:
        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA IF EXISTS access CASCADE")
