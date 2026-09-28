import os
import sys
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
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


def _verified_user(monkeypatch, user_id=None):
    user_id = user_id or uuid4()
    monkeypatch.setattr(
        access_identity,
        "verify_access_jwt",
        lambda _token: access_identity.AccessIdentity(email="person@example.com"),
    )
    monkeypatch.setattr(
        access,
        "get_or_create_user",
        lambda _email: access.StoredUser(id=user_id, email="person@example.com"),
    )
    return user_id


def test_access_context_returns_only_authorized_hierarchy(client, monkeypatch):
    user_id = _verified_user(monkeypatch)
    workspace_id = uuid4()
    company_id = uuid4()
    site_id = uuid4()
    workspace_site_id = uuid4()

    monkeypatch.setattr(
        access,
        "list_authorized_context",
        lambda resolved_user_id: (
            access.WorkspaceContext(
                id=workspace_id,
                name="Rodrigo",
                role=access.ROLE_OWNER,
                sites=(
                    access.SiteContext(
                        id=workspace_site_id,
                        site_id=site_id,
                        hostname="empresa-a.cl",
                        company_id=company_id,
                        company_name="Empresa A",
                    ),
                ),
            ),
        )
        if resolved_user_id == user_id
        else (),
    )

    response = client.get(
        "/access/context",
        headers={"Cf-Access-Jwt-Assertion": "signed-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "workspaces": [
            {
                "id": str(workspace_id),
                "name": "Rodrigo",
                "role": "owner",
                "sites": [
                    {
                        "id": str(workspace_site_id),
                        "site_id": str(site_id),
                        "hostname": "empresa-a.cl",
                        "company_id": str(company_id),
                        "company_name": "Empresa A",
                    }
                ],
            }
        ]
    }


def test_access_context_returns_empty_for_user_without_memberships(client, monkeypatch):
    _verified_user(monkeypatch)
    monkeypatch.setattr(access, "list_authorized_context", lambda _user_id: ())

    response = client.get(
        "/access/context",
        headers={"Cf-Access-Jwt-Assertion": "signed-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"workspaces": []}


def test_access_context_requires_verified_identity(client):
    response = client.get("/access/context")
    assert response.status_code == 401


def test_access_context_hides_database_failure(client, monkeypatch):
    _verified_user(monkeypatch)

    def fail(_user_id):
        raise RuntimeError("database connection failed")

    monkeypatch.setattr(access, "list_authorized_context", fail)

    response = client.get(
        "/access/context",
        headers={"Cf-Access-Jwt-Assertion": "signed-token"},
    )

    assert response.status_code == 503
    assert "database" not in response.text.lower()


def test_authorization_context_and_site_guard_on_real_postgres():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required for the PostgreSQL integration test")

    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA IF EXISTS access CASCADE")

    try:
        access.initialize_database()

        allowed_user = access.get_or_create_user("allowed@example.com")
        other_user = access.get_or_create_user("other@example.com")

        alpha_workspace = uuid4()
        beta_workspace = uuid4()
        hidden_workspace = uuid4()
        other_workspace = uuid4()
        alpha_company = uuid4()
        hidden_company = uuid4()
        other_company = uuid4()
        alpha_site = uuid4()
        hidden_site = uuid4()
        other_site = uuid4()
        alpha_workspace_site = uuid4()
        hidden_workspace_site = uuid4()
        other_workspace_site = uuid4()
        shared_other_workspace_site = uuid4()

        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO access.workspaces (id, name) VALUES (%s, %s)",
                [
                    (alpha_workspace, "Alpha"),
                    (beta_workspace, "Beta"),
                    (hidden_workspace, "Hidden"),
                    (other_workspace, "Other"),
                ],
            )
            cursor.executemany(
                """
                INSERT INTO access.workspace_members (workspace_id, user_id, role)
                VALUES (%s, %s, %s)
                """,
                [
                    (alpha_workspace, allowed_user.id, access.ROLE_OWNER),
                    (beta_workspace, allowed_user.id, access.ROLE_MEMBER),
                    (hidden_workspace, allowed_user.id, "admin"),
                    (other_workspace, other_user.id, access.ROLE_OWNER),
                ],
            )
            cursor.executemany(
                """
                INSERT INTO access.companies (id, workspace_id, name)
                VALUES (%s, %s, %s)
                """,
                [
                    (alpha_company, alpha_workspace, "Alpha Company"),
                    (hidden_company, hidden_workspace, "Hidden Company"),
                    (other_company, other_workspace, "Other Company"),
                ],
            )
            cursor.executemany(
                """
                INSERT INTO access.sites (id, hostname)
                VALUES (%s, %s)
                """,
                [
                    (alpha_site, "alpha.example"),
                    (hidden_site, "hidden.example"),
                    (other_site, "other.example"),
                ],
            )
            cursor.executemany(
                """
                INSERT INTO access.workspace_sites (id, workspace_id, site_id, company_id)
                VALUES (%s, %s, %s, %s)
                """,
                [
                    (alpha_workspace_site, alpha_workspace, alpha_site, alpha_company),
                    (hidden_workspace_site, hidden_workspace, hidden_site, hidden_company),
                    (other_workspace_site, other_workspace, other_site, other_company),
                    (shared_other_workspace_site, other_workspace, alpha_site, other_company),
                ],
            )

        context = access.list_authorized_context(allowed_user.id)

        assert [(workspace.name, workspace.role) for workspace in context] == [
            ("Alpha", "owner"),
            ("Beta", "member"),
        ]
        assert context[0].sites[0].hostname == "alpha.example"
        assert context[0].sites[0].company_name == "Alpha Company"
        assert context[1].sites == ()

        authorized = access.get_authorized_site(allowed_user.id, alpha_workspace_site)
        assert authorized == access.AuthorizedSite(
            workspace_site_id=alpha_workspace_site,
            site_id=alpha_site,
            company_id=alpha_company,
            workspace_id=alpha_workspace,
            role="owner",
        )
        assert access.get_authorized_site(allowed_user.id, hidden_workspace_site) is None
        assert access.get_authorized_site(allowed_user.id, other_workspace_site) is None
        # The same public site can be followed independently by another workspace.
        assert access.get_authorized_site(allowed_user.id, shared_other_workspace_site) is None
        assert access.get_authorized_site(allowed_user.id, uuid4()) is None
    finally:
        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA IF EXISTS access CASCADE")
