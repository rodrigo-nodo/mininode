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

    monkeypatch.setattr(
        access,
        "list_authorized_context",
        lambda resolved_user_id: (
            access.WorkspaceContext(
                id=workspace_id,
                name="Rodrigo",
                role=access.ROLE_OWNER,
                companies=(
                    access.CompanyContext(
                        id=company_id,
                        name="Empresa A",
                        sites=(
                            access.SiteContext(
                                id=site_id,
                                hostname="empresa-a.cl",
                            ),
                        ),
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
                "companies": [
                    {
                        "id": str(company_id),
                        "name": "Empresa A",
                        "sites": [
                            {
                                "id": str(site_id),
                                "hostname": "empresa-a.cl",
                            }
                        ],
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
                INSERT INTO access.sites (id, company_id, hostname)
                VALUES (%s, %s, %s)
                """,
                [
                    (alpha_site, alpha_company, "alpha.example"),
                    (hidden_site, hidden_company, "hidden.example"),
                    (other_site, other_company, "other.example"),
                ],
            )

        context = access.list_authorized_context(allowed_user.id)

        assert [(workspace.name, workspace.role) for workspace in context] == [
            ("Alpha", "owner"),
            ("Beta", "member"),
        ]
        assert context[0].companies[0].name == "Alpha Company"
        assert context[0].companies[0].sites[0].hostname == "alpha.example"
        assert context[1].companies == ()

        authorized = access.get_authorized_site(allowed_user.id, alpha_site)
        assert authorized == access.AuthorizedSite(
            site_id=alpha_site,
            company_id=alpha_company,
            workspace_id=alpha_workspace,
            role="owner",
        )
        assert access.get_authorized_site(allowed_user.id, hidden_site) is None
        assert access.get_authorized_site(allowed_user.id, other_site) is None
        assert access.get_authorized_site(allowed_user.id, uuid4()) is None
    finally:
        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA IF EXISTS access CASCADE")
