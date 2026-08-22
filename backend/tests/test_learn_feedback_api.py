import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.main import create_app  # noqa: E402
from mininode_api.services import learn_feedback  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("API_KEYS", raising=False)
    return TestClient(create_app())


def test_rating_is_created_with_minimal_fields(client, monkeypatch):
    feedback_id = uuid4()
    calls = []
    monkeypatch.setattr(
        learn_feedback,
        "create_feedback",
        lambda **values: calls.append(values) or feedback_id,
    )

    response = client.post(
        "/learn/feedback",
        json={"ebook_id": "001-privacidad-para-pequenos-negocios", "rating": 5},
    )

    assert response.status_code == 201
    assert response.json() == {"id": str(feedback_id)}
    assert calls == [{"ebook_id": "001-privacidad-para-pequenos-negocios", "rating": 5}]


@pytest.mark.parametrize("rating", [0, 6, 1.5, "five"])
def test_rating_must_be_an_integer_between_one_and_five(client, rating):
    response = client.post(
        "/learn/feedback",
        json={"ebook_id": "001-privacidad-para-pequenos-negocios", "rating": rating},
    )
    assert response.status_code == 422


def test_unknown_ebook_is_rejected(client):
    response = client.post("/learn/feedback", json={"ebook_id": "other", "rating": 4})
    assert response.status_code == 422


def test_topic_is_limited_to_defined_options(client, monkeypatch):
    monkeypatch.setattr(learn_feedback, "update_feedback", lambda *args, **kwargs: True)
    feedback_id = uuid4()

    invalid = client.patch(f"/learn/feedback/{feedback_id}", json={"topic": "Otro"})
    valid = client.patch(f"/learn/feedback/{feedback_id}", json={"topic": "Seguridad"})

    assert invalid.status_code == 422
    assert valid.status_code == 204


def test_comment_length_is_limited(client):
    response = client.patch(
        f"/learn/feedback/{uuid4()}", json={"comment": "a" * 501}
    )
    assert response.status_code == 422


def test_extra_personal_fields_are_rejected(client):
    response = client.post(
        "/learn/feedback",
        json={
            "ebook_id": "001-privacidad-para-pequenos-negocios",
            "rating": 4,
            "email": "person@example.com",
        },
    )
    assert response.status_code == 422


def test_comment_for_high_rating_is_rejected(client, monkeypatch):
    def reject(*args, **kwargs):
        raise ValueError("Comments are only accepted for ratings from 1 to 3")

    monkeypatch.setattr(learn_feedback, "update_feedback", reject)
    response = client.patch(
        f"/learn/feedback/{uuid4()}", json={"comment": "More examples"}
    )
    assert response.status_code == 422
