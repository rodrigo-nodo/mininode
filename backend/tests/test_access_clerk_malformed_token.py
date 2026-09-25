import base64
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.main import create_app  # noqa: E402
from mininode_api.services import clerk_identity  # noqa: E402


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def test_malformed_clerk_payload_is_401_before_jwks_lookup(monkeypatch):
    header = _b64url(
        json.dumps(
            {"alg": "RS256", "kid": "clerk-test-key", "typ": "JWT"},
            separators=(",", ":"),
        ).encode()
    )
    malformed_payload = _b64url(b"not-json")
    token = f"{header}.{malformed_payload}.signature"

    monkeypatch.setenv(
        "CLERK_ISSUER",
        "https://helping-puma-182.clerk.accounts.dev",
    )
    monkeypatch.setenv(
        "CLERK_AUTHORIZED_PARTIES",
        "https://app.mininode.io",
    )

    def unexpected_jwks_lookup(_issuer):
        raise AssertionError("malformed client token reached JWKS lookup")

    monkeypatch.setattr(clerk_identity, "_jwk_client", unexpected_jwks_lookup)

    app = create_app()
    app.state.access_ready = True

    with TestClient(app) as client:
        app.state.access_ready = True
        response = client.get(
            "/access/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid Clerk identity"
