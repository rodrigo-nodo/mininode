import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

BACKEND_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.main import create_app  # noqa: E402
from mininode_api.privacy_data.services import data_maps  # noqa: E402


def stored_row(*, expired=False):
    created = datetime.now(timezone.utc)
    expires = created - timedelta(seconds=1) if expired else created + timedelta(days=7)
    return (uuid4(), "draft", None, None, "1", created, created, expires)


def fake_connection(monkeypatch, rows=()):
    executions = []
    pending = iter(rows)

    class Cursor:
        def execute(self, statement, params=None):
            executions.append((" ".join(statement.split()), params))

        def fetchone(self):
            return next(pending, None)

        def __enter__(self): return self
        def __exit__(self, *args): pass

    @contextmanager
    def connection():
        yield type("Connection", (), {"cursor": lambda self: Cursor()})()

    monkeypatch.setattr(data_maps, "_connection", connection)
    return executions


def test_initialization_defines_data_map_table(monkeypatch):
    executions = fake_connection(monkeypatch)
    data_maps.initialize_database()
    sql = executions[0][0]
    assert "CREATE SCHEMA IF NOT EXISTS privacy_data" in sql
    assert "CREATE TABLE IF NOT EXISTS privacy_data.data_maps" in sql
    assert "public_token_hash TEXT UNIQUE NOT NULL" in sql
    assert "status IN ('draft', 'completed')" in sql
    assert "metadata JSONB" in sql


def test_create_stores_only_token_hash_and_seven_day_expiration(monkeypatch):
    row = stored_row()
    executions = fake_connection(monkeypatch, [row])
    created = data_maps.create_data_map()
    sql, params = executions[0]
    assert created.data_map.status == "draft"
    assert created.token != str(created.data_map.id)
    assert len(created.token) >= 40
    assert "INTERVAL '7 days'" in sql
    assert isinstance(params[0], UUID)
    assert params[1] == data_maps.hash_token(created.token)
    assert created.token not in params
    assert created.data_map.expires_at - created.data_map.created_at == timedelta(days=7)


def test_lookup_hashes_token_and_handles_missing_or_expired(monkeypatch):
    token = "secret-capability"
    executions = fake_connection(monkeypatch, [stored_row()])
    found = data_maps.get_data_map(token)
    assert found.status == "draft"
    assert executions[0][1] == (data_maps.hash_token(token),)

    fake_connection(monkeypatch)
    with pytest.raises(data_maps.DataMapNotFoundError):
        data_maps.get_data_map("invalid")

    fake_connection(monkeypatch, [stored_row(expired=True)])
    with pytest.raises(data_maps.DataMapExpiredError):
        data_maps.get_data_map(token)


@pytest.fixture
def client():
    app = create_app()
    app.state.privacy_data_ready = True
    return TestClient(app)


def test_catalog_v1_contains_product_and_transversal_sections(client):
    response = client.get("/privacy/data/catalog")
    assert response.status_code == 200
    catalog = response.json()
    assert catalog["catalog_version"] == "1"
    assert {item["code"] for item in catalog["industry_profiles"]} >= {"commerce_ecommerce", "health"}
    assert {item["code"] for item in catalog["activity_types"]} >= {"sales", "digital_users"}
    assert [item["code"] for item in catalog["retention"]["units"]] == ["days", "months", "years"]
    assert "customers" in {item["code"] for item in catalog["people_categories"]}
    assert "identification" in {item["code"] for item in catalog["personal_data_types"]}
    messaging = next(item for item in catalog["data_channels"] if item["code"] == "messaging")
    assert messaging["label"] == "WhatsApp u otra mensajería"


def test_map_api_round_trip_never_exposes_hash(client, monkeypatch):
    row = stored_row()
    created = data_maps.CreatedDataMap("public-token", data_maps.StoredDataMap(*row))
    monkeypatch.setattr(data_maps, "create_data_map", lambda: created)
    monkeypatch.setattr(data_maps, "get_data_map", lambda token: created.data_map)

    response = client.post("/privacy/data/maps")
    assert response.status_code == 201
    body = response.json()
    assert body["token"] == "public-token"
    assert body["map"]["status"] == "draft"
    assert "public_token_hash" not in response.text

    response = client.get("/privacy/data/maps/public-token")
    assert response.status_code == 200
    assert response.json()["id"] == str(row[0])
    assert "public_token_hash" not in response.text


def test_map_api_reports_invalid_and_expired_tokens(client, monkeypatch):
    monkeypatch.setattr(data_maps, "get_data_map", lambda token: (_ for _ in ()).throw(data_maps.DataMapNotFoundError("Data map not found")))
    assert client.get("/privacy/data/maps/invalid").status_code == 404
    monkeypatch.setattr(data_maps, "get_data_map", lambda token: (_ for _ in ()).throw(data_maps.DataMapExpiredError("Data map has expired")))
    assert client.get("/privacy/data/maps/expired").status_code == 410
