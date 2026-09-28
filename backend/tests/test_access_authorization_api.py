import os
from concurrent.futures import ThreadPoolExecutor
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

            cursor.execute("SAVEPOINT cross_workspace_company")
            with pytest.raises(psycopg.errors.ForeignKeyViolation):
                cursor.execute(
                    """
                    INSERT INTO access.workspace_sites (id, workspace_id, site_id, company_id)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (uuid4(), alpha_workspace, other_site, other_company),
                )
            cursor.execute("ROLLBACK TO SAVEPOINT cross_workspace_company")

            # Company is optional grouping: deleting it must keep the private tracking.
            cursor.execute("DELETE FROM access.companies WHERE id = %s", (alpha_company,))
            cursor.execute(
                "SELECT workspace_id, site_id, company_id FROM access.workspace_sites WHERE id = %s",
                (alpha_workspace_site,),
            )
            assert cursor.fetchone() == (alpha_workspace, alpha_site, None)

        context = access.list_authorized_context(allowed_user.id)

        assert [(workspace.name, workspace.role) for workspace in context] == [
            ("Alpha", "owner"),
            ("Beta", "member"),
        ]
        assert context[0].sites[0].hostname == "alpha.example"
        assert context[0].sites[0].company_id is None
        assert context[0].sites[0].company_name is None
        assert context[1].sites == ()

        authorized = access.get_authorized_site(allowed_user.id, alpha_workspace_site)
        assert authorized == access.AuthorizedSite(
            workspace_site_id=alpha_workspace_site,
            site_id=alpha_site,
            company_id=None,
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


def test_access_onboarding_creates_or_reuses_personal_workspace(client, monkeypatch):
    user_id = _verified_user(monkeypatch)
    workspace_id = uuid4()
    calls = []

    def onboard(resolved_user_id):
        calls.append(resolved_user_id)
        return access.PersonalWorkspace(id=workspace_id, name="Mi espacio", role=access.ROLE_OWNER)

    monkeypatch.setattr(access, "get_or_create_personal_workspace", onboard)

    response = client.post(
        "/access/onboarding",
        headers={"Cf-Access-Jwt-Assertion": "signed-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "workspace_id": str(workspace_id),
        "name": "Mi espacio",
        "role": "owner",
    }
    assert calls == [user_id]


def test_access_onboarding_requires_verified_identity(client):
    response = client.post("/access/onboarding")
    assert response.status_code == 401


def test_personal_workspace_is_idempotent_on_real_postgres():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required for the PostgreSQL integration test")

    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA IF EXISTS access CASCADE")

    try:
        access.initialize_database()
        user = access.get_or_create_user("new-user@example.com")

        first = access.get_or_create_personal_workspace(user.id)
        second = access.get_or_create_personal_workspace(user.id)

        assert first == second
        assert first.name == "Mi espacio"
        assert first.role == access.ROLE_OWNER

        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM access.workspaces")
            assert cursor.fetchone()[0] == 1
            cursor.execute(
                "SELECT count(*) FROM access.workspace_members WHERE user_id = %s AND role = %s",
                (user.id, access.ROLE_OWNER),
            )
            assert cursor.fetchone()[0] == 1
            cursor.execute("SELECT count(*) FROM access.entitlements")
            assert cursor.fetchone()[0] == 0
    finally:
        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA IF EXISTS access CASCADE")


def test_personal_workspace_concurrent_onboarding_creates_one_workspace_on_real_postgres():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required for the PostgreSQL integration test")

    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA IF EXISTS access CASCADE")

    try:
        access.initialize_database()
        user = access.get_or_create_user("concurrent-user@example.com")

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(access.get_or_create_personal_workspace, user.id)
                for _ in range(2)
            ]
            results = [future.result(timeout=10) for future in futures]

        assert results[0].id == results[1].id
        assert all(result.name == "Mi espacio" for result in results)
        assert all(result.role == access.ROLE_OWNER for result in results)

        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM access.workspaces")
            assert cursor.fetchone()[0] == 1
            cursor.execute(
                "SELECT count(*) FROM access.workspace_members WHERE user_id = %s AND role = %s",
                (user.id, access.ROLE_OWNER),
            )
            assert cursor.fetchone()[0] == 1
            cursor.execute("SELECT count(*) FROM access.entitlements")
            assert cursor.fetchone()[0] == 0
    finally:
        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA IF EXISTS access CASCADE")


def test_follow_site_normalizes_public_url():
    assert access.normalize_site_url(" Example.COM/path?q=1 ") == ("example.com", "https://example.com")
    assert access.normalize_site_url("http://WWW.Example.com/a") == ("www.example.com", "http://www.example.com")
    with pytest.raises(ValueError):
        access.normalize_site_url("localhost")
    with pytest.raises(ValueError):
        access.normalize_site_url("https://user:pass@example.com")
    for value in (
        "127.0.0.1",
        "169.254.169.254",
        "10.0.0.1",
        "192.168.1.1",
        "https://bad_host.example",
        "https://-bad.example",
        "https://bad-.example",
        "https://example.123",
    ):
        with pytest.raises(ValueError):
            access.normalize_site_url(value)
    assert access.normalize_site_url("https://8.8.8.8/path") == ("8.8.8.8", "https://8.8.8.8")


def test_follow_site_is_idempotent_and_isolated_on_real_postgres():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required for the PostgreSQL integration test")
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA IF EXISTS access CASCADE")
    try:
        access.initialize_database()
        owner = access.get_or_create_user("site-owner@example.com")
        other = access.get_or_create_user("other-owner@example.com")
        workspace = access.get_or_create_personal_workspace(owner.id)
        other_workspace = access.get_or_create_personal_workspace(other.id)

        first = access.follow_site(owner.id, workspace.id, "https://Example.COM/path")
        second = access.follow_site(owner.id, workspace.id, "example.com/other")
        shared = access.follow_site(other.id, other_workspace.id, "example.com")

        assert first.id == second.id
        assert first.site_id == second.site_id == shared.site_id
        assert first.id != shared.id
        assert access.follow_site(other.id, workspace.id, "blocked.example") is None

        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM access.sites")
            assert cursor.fetchone()[0] == 1
            cursor.execute("SELECT count(*) FROM access.workspace_sites")
            assert cursor.fetchone()[0] == 2
            cursor.execute("SELECT count(*) FROM access.entitlements")
            assert cursor.fetchone()[0] == 0
    finally:
        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA IF EXISTS access CASCADE")
