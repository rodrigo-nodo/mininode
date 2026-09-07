import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

BACKEND_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.main import create_app  # noqa: E402
from mininode_api.privacy_data.services import data_maps  # noqa: E402


NOW = datetime.now(timezone.utc)


def stored_map(*, expired=False):
    return data_maps.StoredDataMap(
        uuid4(), "draft", None, None, "1", NOW, NOW,
        NOW - timedelta(seconds=1) if expired else NOW + timedelta(days=7),
    )


def answers(**changes):
    value = {
        "people_categories": [], "may_include_minors": False,
        "personal_data_types": [], "storage_locations": [], "data_channels": [],
        "purposes": [], "access_roles": [], "has_third_parties": False,
        "third_parties": [],
        "retention": {
            "status": "unknown", "value": None, "unit": None, "note": None,
            "reviewed": False,
        },
    }
    value.update(changes)
    return value


def activity(data_map, *, position=0, activity_type="sales", activity_answers=None):
    return data_maps.StoredActivity(
        uuid4(), data_map.id, activity_type, "own_operations", position,
        activity_answers or answers(), NOW, NOW,
    )


@pytest.fixture
def client():
    app = create_app()
    app.state.privacy_data_ready = True
    return TestClient(app)


def test_initialization_defines_activities_table_fk_and_index():
    sql = " ".join(data_maps.INITIALIZE_SQL.split())
    assert "CREATE TABLE IF NOT EXISTS privacy_data.activities" in sql
    assert "data_map_id UUID NOT NULL REFERENCES privacy_data.data_maps(id) ON DELETE CASCADE" in sql
    assert "ON privacy_data.activities (data_map_id, position)" in sql


def test_create_activity_is_associated_with_token_map_and_never_exposes_internal_fields(client, monkeypatch):
    data_map = stored_map()
    captured = {}
    monkeypatch.setattr(data_maps, "get_data_map", lambda token: data_map)

    def create(resolved_map, payload):
        captured.update(map=resolved_map, payload=payload)
        return activity(resolved_map, activity_answers=payload["answers"])

    monkeypatch.setattr(data_maps, "create_activity", create)
    response = client.post("/privacy/data/maps/token/activities", json={
        "activity_type": "sales", "data_context": "own_operations", "answers": answers()
    })
    assert response.status_code == 201
    assert captured["map"].id == data_map.id
    assert "data_map_id" not in response.text
    assert "public_token_hash" not in response.text


@pytest.mark.parametrize("payload", [
    {"activity_type": "invalid", "data_context": "own_operations", "answers": answers()},
    {"activity_type": "sales", "data_context": "invalid", "answers": answers()},
    {"activity_type": "sales", "data_context": "own_operations", "answers": answers(people_categories=["invalid"])},
    {"activity_type": "sales", "data_context": "own_operations", "answers": answers(data_origins=["invalid"])},
    {"activity_type": "sales", "data_context": "own_operations", "answers": answers(access_roles=["owner_only", "sales"])},
    {"activity_type": "sales", "data_context": "own_operations", "answers": answers(access_roles=["unknown", "administration"])},
    {"activity_type": "sales", "data_context": "own_operations", "answers": answers(
        has_third_parties=True, third_parties=[{"type": "technology_provider", "relationships": ["unknown", "access"]}])},
    {"activity_type": "sales", "data_context": "own_operations", "answers": answers(
        third_parties=[{"type": "technology_provider", "relationships": ["access"]}])},
    {"activity_type": "sales", "data_context": "own_operations", "answers": answers(
        retention={"status": "defined", "value": None, "unit": None, "reviewed": True})},
])
def test_invalid_activity_payloads_return_422(client, payload):
    assert client.post("/privacy/data/maps/token/activities", json=payload).status_code == 422


def test_third_party_id_is_generated_and_preserved(client, monkeypatch):
    data_map = stored_map()
    captured = []
    monkeypatch.setattr(data_maps, "get_data_map", lambda token: data_map)
    monkeypatch.setattr(data_maps, "create_activity", lambda dm, payload: captured.append(payload) or activity(dm, activity_answers=payload["answers"]))
    payload = {"activity_type": "sales", "data_context": "both", "answers": answers(
        has_third_parties=True,
        third_parties=[{"type": "technology_provider", "relationships": ["access"]}],
    )}
    first = client.post("/privacy/data/maps/token/activities", json=payload)
    assert first.status_code == 201
    generated = first.json()["answers"]["third_parties"][0]["id"]
    payload["answers"]["third_parties"][0]["id"] = generated
    second = client.post("/privacy/data/maps/token/activities", json=payload)
    assert second.json()["answers"]["third_parties"][0]["id"] == generated


def test_data_origins_round_trip_and_legacy_answers_default(client, monkeypatch):
    data_map = stored_map()
    monkeypatch.setattr(data_maps, "get_data_map", lambda token: data_map)
    monkeypatch.setattr(
        data_maps,
        "create_activity",
        lambda dm, payload: activity(dm, activity_answers=payload["answers"]),
    )

    response = client.post("/privacy/data/maps/token/activities", json={
        "activity_type": "sales",
        "data_context": "own_operations",
        "answers": answers(data_origins=["direct_person", "business_systems"]),
    })
    assert response.status_code == 201
    assert response.json()["answers"]["data_origins"] == [
        "direct_person", "business_systems",
    ]

    legacy = activity(data_map)
    legacy.answers.pop("data_origins", None)
    monkeypatch.setattr(data_maps, "list_activities", lambda dm: [legacy])
    response = client.get("/privacy/data/maps/token/activities")
    assert response.status_code == 200
    assert response.json()[0]["answers"]["data_origins"] == []


def test_retention_phase_two_round_trip_and_legacy_review_default(client, monkeypatch):
    data_map = stored_map()
    monkeypatch.setattr(data_maps, "get_data_map", lambda token: data_map)
    monkeypatch.setattr(
        data_maps,
        "create_activity",
        lambda dm, payload: activity(dm, activity_answers=payload["answers"]),
    )
    response = client.post("/privacy/data/maps/token/activities", json={
        "activity_type": "sales",
        "data_context": "own_operations",
        "answers": answers(retention={
            "status": "not_defined", "value": None, "unit": None, "note": None,
            "reviewed": True,
        }),
    })
    assert response.status_code == 201
    assert response.json()["answers"]["retention"] == {
        "status": "not_defined", "value": None, "unit": None, "note": None,
        "reviewed": True,
    }

    legacy = activity(data_map)
    legacy.answers["retention"].pop("reviewed", None)
    monkeypatch.setattr(data_maps, "list_activities", lambda dm: [legacy])
    response = client.get("/privacy/data/maps/token/activities")
    assert response.status_code == 200
    assert response.json()[0]["answers"]["retention"]["reviewed"] is False


@pytest.mark.parametrize("field", ["may_include_minors", "has_third_parties"])
def test_uncertain_boolean_answers_are_accepted(client, monkeypatch, field):
    data_map = stored_map()
    monkeypatch.setattr(data_maps, "get_data_map", lambda token: data_map)
    monkeypatch.setattr(
        data_maps,
        "create_activity",
        lambda dm, payload: activity(dm, activity_answers=payload["answers"]),
    )
    response = client.post("/privacy/data/maps/token/activities", json={
        "activity_type": "sales",
        "data_context": "own_operations",
        "answers": answers(**{field: "unknown"}),
    })
    assert response.status_code == 201
    assert response.json()["answers"][field] == "unknown"


@pytest.mark.parametrize("has_third_parties", [False, None, "unknown"])
def test_third_parties_require_explicit_true(client, has_third_parties):
    payload = {
        "activity_type": "sales",
        "data_context": "own_operations",
        "answers": answers(
            has_third_parties=has_third_parties,
            third_parties=[{"type": "technology_provider", "relationships": ["access"]}],
        ),
    }
    assert client.post("/privacy/data/maps/token/activities", json=payload).status_code == 422


def test_unconfirmed_data_context_can_be_created_then_updated(client, monkeypatch):
    data_map = stored_map()
    created = activity(data_map)
    seen = []
    monkeypatch.setattr(data_maps, "get_data_map", lambda token: data_map)

    def create(dm, payload):
        seen.append(payload["data_context"])
        return data_maps.StoredActivity(
            created.id, dm.id, payload["activity_type"], payload["data_context"], 0,
            payload["answers"], NOW, NOW,
        )

    def update(dm, activity_id, values):
        seen.append(values["data_context"])
        return data_maps.StoredActivity(
            activity_id, dm.id, created.activity_type, values["data_context"], 0,
            created.answers, NOW, NOW,
        )

    monkeypatch.setattr(data_maps, "create_activity", create)
    monkeypatch.setattr(data_maps, "update_activity", update)
    response = client.post("/privacy/data/maps/token/activities", json={
        "activity_type": "sales", "data_context": "unconfirmed",
    })
    assert response.status_code == 201
    assert response.json()["data_context"] == "unconfirmed"

    for context in ("own_operations", "client_service", "both"):
        response = client.patch(
            f"/privacy/data/maps/token/activities/{created.id}",
            json={"data_context": context},
        )
        assert response.status_code == 200
        assert response.json()["data_context"] == context
    assert seen == ["unconfirmed", "own_operations", "client_service", "both"]


def test_list_patch_delete_and_cross_map_protection(client, monkeypatch):
    first_map, second_map = stored_map(), stored_map()
    rows = [activity(first_map, position=4), activity(first_map, position=1)]
    monkeypatch.setattr(data_maps, "get_data_map", lambda token: first_map if token == "first" else second_map)
    monkeypatch.setattr(data_maps, "list_activities", lambda dm: sorted(rows, key=lambda item: item.position))
    response = client.get("/privacy/data/maps/first/activities")
    assert [item["position"] for item in response.json()] == [1, 4]

    patched = activity(first_map, position=2, activity_type="marketing")
    monkeypatch.setattr(data_maps, "update_activity", lambda dm, activity_id, values: patched if dm.id == first_map.id else (_ for _ in ()).throw(data_maps.ActivityNotFoundError()))
    assert client.patch(f"/privacy/data/maps/first/activities/{patched.id}", json={"position": 2}).status_code == 200
    assert client.patch(f"/privacy/data/maps/second/activities/{patched.id}", json={"position": 2}).status_code == 404

    deleted = []
    monkeypatch.setattr(data_maps, "delete_activity", lambda dm, activity_id: deleted.append((dm.id, activity_id)))
    assert client.delete(f"/privacy/data/maps/first/activities/{patched.id}").status_code == 204
    assert deleted == [(first_map.id, patched.id)]


def test_activity_endpoints_report_invalid_and_expired_tokens(client, monkeypatch):
    monkeypatch.setattr(data_maps, "get_data_map", lambda token: (_ for _ in ()).throw(data_maps.DataMapNotFoundError()))
    assert client.get("/privacy/data/maps/bad/activities").status_code == 404
    monkeypatch.setattr(data_maps, "get_data_map", lambda token: (_ for _ in ()).throw(data_maps.DataMapExpiredError()))
    assert client.get("/privacy/data/maps/expired/activities").status_code == 410


def test_patch_map_validates_catalog_and_supports_nullable_fields(client, monkeypatch):
    data_map = stored_map()
    monkeypatch.setattr(data_maps, "get_data_map", lambda token: data_map)

    def update(dm, changes):
        return data_maps.StoredDataMap(
            dm.id, dm.status, changes.get("industry_profile", dm.industry_profile),
            changes.get("business_size", dm.business_size), dm.catalog_version,
            dm.created_at, dm.updated_at, dm.expires_at,
        )

    monkeypatch.setattr(data_maps, "update_data_map", update)
    response = client.patch("/privacy/data/maps/token", json={"industry_profile": "commerce_ecommerce"})
    assert response.status_code == 200
    assert response.json()["industry_profile"] == "commerce_ecommerce"
    assert client.patch("/privacy/data/maps/token", json={"industry_profile": "invalid"}).status_code == 422
    response = client.patch("/privacy/data/maps/token", json={"business_size": "small"})
    assert response.status_code == 200
    assert response.json()["business_size"] == "small"
    assert "public_token_hash" not in response.text