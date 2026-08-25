import hashlib
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.services import privacy_correction_plan as service  # noqa: E402


PLAN = {
    "version": "1",
    "actions_version": "2026-08-01",
    "initial_score": 26,
    "item_count": 1,
    "items": [{"control_code": "PRV-001", "priority": 1}],
}


def fake_connection(monkeypatch, *, row=None):
    executions = []

    class Cursor:
        def execute(self, statement, params=None):
            executions.append((" ".join(statement.split()), params))

        def fetchone(self):
            return row

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    @contextmanager
    def connection():
        yield type("Connection", (), {"cursor": lambda self: Cursor()})()

    monkeypatch.setattr(service, "_connection", connection)
    return executions


def test_initialization_defines_minimal_privacy_schema(monkeypatch):
    executions = fake_connection(monkeypatch)
    service.initialize_database()
    sql = executions[0][0]
    assert "CREATE SCHEMA IF NOT EXISTS privacy" in sql
    assert "CREATE TABLE IF NOT EXISTS privacy.correction_plan" in sql
    assert "site_url TEXT NOT NULL" in sql
    assert "site_url TEXT UNIQUE" not in sql
    assert "token_hash TEXT NOT NULL UNIQUE" in sql
    assert "plan_snapshot JSONB NOT NULL" in sql
    assert "initial_score BETWEEN 0 AND 100" in sql
    assert "status IN ('active', 'revoked')" in sql


def test_create_stores_hash_and_untouched_snapshot(monkeypatch):
    executions = fake_connection(monkeypatch)
    monkeypatch.setattr(service.secrets, "token_urlsafe", lambda size: "secret-token")

    created = service.create_correction_plan(site_url="https://example.com", plan=PLAN)

    sql, params = executions[0]
    assert "INSERT INTO privacy.correction_plan" in sql
    assert created.access_token == "secret-token"
    assert params[1] == "https://example.com"
    assert params[2] == hashlib.sha256(b"secret-token").hexdigest()
    assert "secret-token" not in params
    assert params[3].obj == PLAN
    assert params[4:7] == ("1", "2026-08-01", 26)


@pytest.mark.parametrize("score", [-1, 101, True])
def test_create_rejects_invalid_initial_score(monkeypatch, score):
    fake_connection(monkeypatch)
    with pytest.raises(ValueError):
        service.create_correction_plan(
            site_url="https://example.com", plan={**PLAN, "initial_score": score}
        )


def test_get_hashes_token_and_returns_only_original_snapshot(monkeypatch):
    plan_id = uuid4()
    created_at = datetime.now(timezone.utc)
    executions = fake_connection(
        monkeypatch,
        row=(plan_id, "https://example.com", created_at, PLAN),
    )

    stored = service.get_correction_plan("secret-token")

    sql, params = executions[0]
    assert "token_hash = %s AND status = 'active'" in sql
    assert params == (hashlib.sha256(b"secret-token").hexdigest(),)
    assert stored == {
        "id": plan_id,
        "site_url": "https://example.com",
        "created_at": created_at,
        "plan": PLAN,
    }
    assert "token_hash" not in stored


@pytest.mark.parametrize("token", ["missing", ""])
def test_get_missing_or_empty_token_is_neutral_not_found(monkeypatch, token):
    fake_connection(monkeypatch)
    with pytest.raises(service.CorrectionPlanNotFoundError, match="Plan not found"):
        service.get_correction_plan(token)
