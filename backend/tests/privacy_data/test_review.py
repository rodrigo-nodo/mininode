import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

BACKEND_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.main import create_app  # noqa: E402
from mininode_api.privacy_data.review import review_data_map  # noqa: E402
from mininode_api.privacy_data.services import data_maps  # noqa: E402

NOW = datetime.now(timezone.utc)


def stored_map(*, expired=False):
    return data_maps.StoredDataMap(
        uuid4(), "draft", None, None, "1", NOW, NOW,
        NOW - timedelta(seconds=1) if expired else NOW + timedelta(days=7),
    )


def activity(data_map, activity_type="sales", **changes):
    answers = {
        "retention": {"status": "defined"}, "access_roles": ["owner_only"],
        "has_third_parties": False, "third_parties": [], "may_include_minors": False,
    }
    answers.update(changes)
    return data_maps.StoredActivity(
        uuid4(), data_map.id, activity_type, "own_operations", 0, answers, NOW, NOW,
    )


def codes(*activities):
    return [item.code for item in review_data_map(stored_map(), list(activities))]


@pytest.mark.parametrize(("changes", "code", "topic", "action"), [
    (
        {"retention": {"status": "unknown"}},
        "D01", "Conservación",
        "Define cuánto tiempo necesitas conservar estos datos.",
    ),
    (
        {"retention": {"status": "variable"}},
        "D02", "Conservación",
        "Define criterios para decidir cuánto tiempo conservarlos según cada caso.",
    ),
    (
        {"access_roles": ["unknown"]},
        "D03", "Accesos",
        "Identifica quién necesita acceder a ellos.",
    ),
    (
        {
            "has_third_parties": True,
            "third_parties": [{"type": "other", "relationships": ["unknown"]}],
        },
        "D04", "Terceros",
        "Aclara qué información recibe o puede consultar este tercero.",
    ),
    (
        {"has_third_parties": True},
        "D05", "Terceros",
        "Mantén identificados los terceros que participan.",
    ),
    (
        {"may_include_minors": True},
        "D06", "Menores",
        "Revisa qué datos de menores manejas y para qué.",
    ),
])
def test_observations_include_topic_and_action(changes, code, topic, action):
    data_map = stored_map()
    observations = review_data_map(data_map, [activity(data_map, **changes)])
    observation = next(item for item in observations if item.code == code)
    assert (observation.topic, observation.action) == (topic, action)


@pytest.mark.parametrize(("status", "expected"), [
    ("unknown", ["D01"]), ("variable", ["D02"]), ("defined", []),
])
def test_retention_rules_activate_only_for_their_status(status, expected):
    data_map = stored_map()
    assert codes(activity(data_map, retention={"status": status})) == expected


def test_access_unknown_activates_d03():
    data_map = stored_map()
    assert codes(activity(data_map, access_roles=["unknown"])) == ["D03"]


def test_third_party_unknown_activates_d04_once_and_d05_can_coexist():
    data_map = stored_map()
    observations = review_data_map(data_map, [activity(
        data_map,
        has_third_parties=True,
        third_parties=[{
            "type": "technology_provider",
            "relationships": ["unknown", "unknown"],
        }],
    )])
    assert [item.code for item in observations] == ["D05", "D04"]
    assert observations[1].third_party_type == "technology_provider"


def test_d04_requires_third_parties_flag_and_unknown_relationship():
    data_map = stored_map()
    without_flag = activity(data_map, third_parties=[{"type": "other", "relationships": ["unknown"]}])
    known = activity(data_map, has_third_parties=True, third_parties=[{"type": "other", "relationships": ["access"]}])
    assert "D04" not in codes(without_flag)
    assert codes(known) == ["D05"]


def test_d05_activates_when_third_parties_exist():
    data_map = stored_map()
    assert codes(activity(data_map, has_third_parties=True)) == ["D05"]


def test_d06_activates_only_when_minors_is_true():
    data_map = stored_map()
    assert codes(activity(data_map, may_include_minors=True)) == ["D06"]
    assert codes(activity(data_map, may_include_minors=False)) == []


def test_one_activity_can_generate_multiple_observations():
    data_map = stored_map()
    result = review_data_map(data_map, [activity(
        data_map, retention={"status": "unknown"}, access_roles=["unknown"],
        may_include_minors=True,
    )])
    assert [item.code for item in result] == ["D01", "D03", "D06"]


def test_different_activities_generate_independent_observations():
    data_map = stored_map()
    result = review_data_map(data_map, [
        activity(data_map, "sales", may_include_minors=True),
        activity(data_map, "marketing", may_include_minors=True),
    ])
    assert [(item.code, item.activity_type) for item in result] == [
        ("D06", "sales"), ("D06", "marketing"),
    ]
    assert result[0].activity_id != result[1].activity_id


def test_map_without_signals_returns_empty_list():
    data_map = stored_map()
    assert review_data_map(data_map, [activity(data_map)]) == []


@pytest.fixture
def client():
    app = create_app()
    app.state.privacy_data_ready = True
    return TestClient(app)


def test_review_endpoint_accepts_normal_and_recovery_tokens_without_exposing_hashes(client, monkeypatch):
    data_map = stored_map()
    seen = []
    monkeypatch.setattr(data_maps, "get_data_map", lambda token: seen.append(token) or data_map)
    monkeypatch.setattr(data_maps, "list_activities", lambda current: [activity(current, may_include_minors=True)])
    for token in ("normal-token", "recovery-token"):
        response = client.get(f"/privacy/data/maps/{token}/review")
        assert response.status_code == 200
        observation = response.json()[0]
        assert observation["code"] == "D06"
        assert observation["topic"] == "Menores"
        assert observation["action"] == "Revisa qué datos de menores manejas y para qué."
        assert "title" in observation
        assert "description" in observation
        assert "hash" not in response.text.lower()
        assert "data_map_id" not in response.text
    assert seen == ["normal-token", "recovery-token"]


@pytest.mark.parametrize(("error", "status"), [
    (data_maps.DataMapNotFoundError("Data map not found"), 404),
    (data_maps.DataMapExpiredError("Data map has expired"), 410),
])
def test_review_endpoint_preserves_token_errors(client, monkeypatch, error, status):
    monkeypatch.setattr(data_maps, "get_data_map", lambda token: (_ for _ in ()).throw(error))
    assert client.get("/privacy/data/maps/token/review").status_code == status


def test_review_endpoint_preserves_database_unavailable(client):
    client.app.state.privacy_data_ready = False
    assert client.get("/privacy/data/maps/token/review").status_code == 503
