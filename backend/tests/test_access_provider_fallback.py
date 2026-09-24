import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.main import create_app  # noqa: E402
from mininode_api.services import access, access_identity, clerk_identity  # noqa: E402


def test_non_bearer_authorization_keeps_cloudflare_fallback(monkeypatch):
    app = create_app()
    app.state.access_ready = True
    client = TestClient(app)
    user_id = uuid4()
    clerk_calls = []
    cloudflare_calls = []

    monkeypatch.setattr(
        clerk_identity,
        "verify_clerk_session",
        lambda token: clerk_calls.append(token),
    )
    monkeypatch.setattr(
        access_identity,
        "verify_access_jwt",
        lambda token: cloudflare_calls.append(token)
        or access_identity.AccessIdentity(email="cloudflare@example.com"),
    )
    monkeypatch.setattr(
        access,
        "get_or_create_user",
        lambda email: access.StoredUser(id=user_id, email=email),
    )

    response = client.get(
        "/access/me",
        headers={
            "Authorization": "Basic unrelated-value",
            "Cf-Access-Jwt-Assertion": "valid-cloudflare-token",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": str(user_id),
        "email": "cloudflare@example.com",
    }
    assert clerk_calls == []
    assert cloudflare_calls == ["valid-cloudflare-token"]
