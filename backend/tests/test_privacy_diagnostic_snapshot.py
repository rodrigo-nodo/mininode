import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest

BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.services import privacy_diagnostic_snapshot as service  # noqa: E402


def fake_connection(monkeypatch, *, rows=()):
    executions = []
    pending_rows = iter(rows)

    class Cursor:
        def execute(self, statement, params=None):
            executions.append((" ".join(statement.split()), params))

        def fetchone(self):
            return next(pending_rows, None)

        def fetchall(self):
            return list(pending_rows)

        def __enter__(self): return self
        def __exit__(self, *args): pass

    @contextmanager
    def connection():
        yield type("Connection", (), {"cursor": lambda self: Cursor()})()

    monkeypatch.setattr(service, "_connection", connection)
    return executions


def diagnostic():
    return {
        "site_url": "https://example.com/", "score": 42, "coverage": 90,
        "status": "Puede mejorar", "controls": [{"control_code": "PRV-001"}],
        "priorities": [], "scope": {"pages_analyzed": 1},
    }


def stored_row(snapshot=None):
    created = datetime.now(timezone.utc)
    return (uuid4(), "https://example.com/", snapshot or diagnostic(), 42, created, created + timedelta(hours=24), None)


def test_initialization_defines_immutable_minimal_diagnostic_table(monkeypatch):
    executions = fake_connection(monkeypatch)
    service.initialize_database()
    sql = executions[0][0]
    assert "CREATE SCHEMA IF NOT EXISTS privacy" in sql
    assert "CREATE TABLE IF NOT EXISTS privacy.diagnostic" in sql
    assert "id UUID PRIMARY KEY" in sql
    assert "site_url TEXT NOT NULL" in sql and "site_url TEXT UNIQUE" not in sql
    assert "diagnostic_snapshot JSONB NOT NULL" in sql
    assert "score BETWEEN 0 AND 100" in sql
    assert "purchase_expires_at TIMESTAMPTZ NOT NULL" in sql
    assert "workspace_site_id UUID NULL REFERENCES access.workspace_sites(id) ON DELETE SET NULL" in sql
    for personal_field in ("email", "user_agent", "ip_address", "name"):
        assert personal_field not in sql
    assert "UPDATE privacy.diagnostic" not in sql


def test_create_stores_snapshot_intact_with_backend_24_hour_expiration(monkeypatch):
    snapshot = diagnostic()
    row = stored_row(snapshot)
    executions = fake_connection(monkeypatch, rows=[row])
    stored = service.create_diagnostic_snapshot(snapshot)
    sql, params = executions[0]
    assert "CURRENT_TIMESTAMP + INTERVAL '24 hours'" in sql
    assert isinstance(params[0], UUID)
    assert params[1] == snapshot["site_url"]
    assert params[2].obj == snapshot
    assert params[3] == 42
    assert params[4] is None
    assert stored.diagnostic_snapshot == snapshot
    assert stored.purchase_expires_at - stored.created_at == timedelta(hours=24)


def test_get_returns_snapshot_without_recalculation(monkeypatch):
    snapshot = diagnostic()
    executions = fake_connection(monkeypatch, rows=[stored_row(snapshot)])
    stored = service.get_diagnostic_snapshot(uuid4())
    assert stored.score == snapshot["score"]
    assert stored.diagnostic_snapshot == snapshot
    assert "SELECT" in executions[0][0]


def test_missing_and_expired_diagnostics_are_controlled(monkeypatch):
    fake_connection(monkeypatch)
    with pytest.raises(service.PrivacyDiagnosticSnapshotNotFoundError):
        service.get_diagnostic_snapshot(uuid4())
    created = datetime.now(timezone.utc) - timedelta(hours=25)
    expired = service.StoredPrivacyDiagnostic(uuid4(), "https://example.com/", diagnostic(), 42, created, created + timedelta(hours=24), None)
    with pytest.raises(service.PrivacyDiagnosticPurchaseExpiredError):
        service.require_purchasable(expired, now=datetime.now(timezone.utc))


def test_latest_workspace_site_orders_newest_first(monkeypatch):
    snapshot = diagnostic()
    row = stored_row(snapshot)
    workspace_site_id = uuid4()
    row = (*row[:-1], workspace_site_id)
    executions = fake_connection(monkeypatch, rows=[row])

    stored = service.get_latest_for_workspace_site(workspace_site_id)

    sql, params = executions[0]
    assert "WHERE workspace_site_id = %s" in sql
    assert "ORDER BY created_at DESC, id DESC" in sql
    assert "LIMIT 1" in sql
    assert params == (workspace_site_id,)
    assert stored.workspace_site_id == workspace_site_id


def test_latest_workspace_site_missing_is_controlled(monkeypatch):
    fake_connection(monkeypatch)
    with pytest.raises(service.PrivacyDiagnosticSnapshotNotFoundError):
        service.get_latest_for_workspace_site(uuid4())


def test_list_latest_for_workspace_returns_one_row_shape_per_site(monkeypatch):
    workspace_id = uuid4()
    site_a = uuid4()
    site_b = uuid4()
    row_a = (*stored_row(diagnostic())[:-1], site_a)
    second = {**diagnostic(), "site_url": "https://second.example/", "score": 77}
    row_b_base = stored_row(second)
    row_b = (*row_b_base[:-1], site_b)
    executions = fake_connection(monkeypatch, rows=[row_a, row_b])

    stored = service.list_latest_for_workspace(workspace_id)

    sql, params = executions[0]
    assert "SELECT DISTINCT ON (d.workspace_site_id)" in sql
    assert "JOIN access.workspace_sites AS ws ON ws.id = d.workspace_site_id" in sql
    assert "WHERE ws.workspace_id = %s" in sql
    assert "d.created_at DESC" in sql
    assert params == (workspace_id,)
    assert [item.workspace_site_id for item in stored] == [site_a, site_b]


def test_anonymous_claim_proof_is_hashed_at_rest(monkeypatch):
    token = "a" * 43
    executions = fake_connection(monkeypatch, rows=[stored_row()])
    service.create_diagnostic_snapshot(diagnostic(), claim_token=token)
    sql, params = executions[0]
    assert "claim_token_hash" in sql
    assert token not in str(params)
    assert len(params[-1]) == 64


def test_claim_rejects_invalid_token_without_database_access(monkeypatch):
    executions = fake_connection(monkeypatch)
    with pytest.raises(service.PrivacyDiagnosticClaimRejectedError):
        service.claim_anonymous_diagnostic(uuid4(), "short", uuid4())
    assert executions == []


def test_claim_rejects_wrong_proof(monkeypatch):
    executions = fake_connection(monkeypatch, rows=[("https://example.com/", "0" * 64, None, None, True)])
    with pytest.raises(service.PrivacyDiagnosticClaimRejectedError):
        service.claim_anonymous_diagnostic(uuid4(), "a" * 43, uuid4(), uuid4())
    assert "pg_advisory_xact_lock" in executions[0][0]
    assert not any("UPDATE privacy.diagnostic" in sql for sql, _ in executions)


def test_claim_rejects_expired_proof(monkeypatch):
    import hashlib
    token = "a" * 43
    fake_connection(monkeypatch, rows=[
        ("https://example.com/", hashlib.sha256(token.encode()).hexdigest(), None, None, False),
        (1,),
    ])
    with pytest.raises(service.PrivacyDiagnosticPurchaseExpiredError):
        service.claim_anonymous_diagnostic(uuid4(), token, uuid4(), uuid4())


def test_claim_rejects_unauthorized_workspace(monkeypatch):
    import hashlib
    token = "a" * 43
    fake_connection(monkeypatch, rows=[
        ("https://example.com/", hashlib.sha256(token.encode()).hexdigest(), None, None, True),
        None,
    ])
    with pytest.raises(service.PrivacyDiagnosticClaimRejectedError):
        service.claim_anonymous_diagnostic(uuid4(), token, uuid4(), uuid4())


def test_claim_rejects_other_user_even_in_same_workspace(monkeypatch):
    import hashlib
    token = "a" * 43
    fake_connection(monkeypatch, rows=[
        ("https://example.com/", hashlib.sha256(token.encode()).hexdigest(), uuid4(), uuid4(), True),
        (1,),
    ])
    with pytest.raises(service.PrivacyDiagnosticClaimRejectedError):
        service.claim_anonymous_diagnostic(uuid4(), token, uuid4(), uuid4())


def test_claim_is_idempotent_for_original_owner(monkeypatch):
    import hashlib
    token = "a" * 43
    owner, site = uuid4(), uuid4()
    fake_connection(monkeypatch, rows=[
        ("https://example.com/", hashlib.sha256(token.encode()).hexdigest(), site, owner, True),
        (1,), (1,),
    ])
    assert service.claim_anonymous_diagnostic(uuid4(), token, owner, uuid4()) == site


def test_claim_associates_new_workspace_site(monkeypatch):
    import hashlib
    token = "a" * 43
    user, workspace, site, workspace_site = uuid4(), uuid4(), uuid4(), uuid4()
    executions = fake_connection(monkeypatch, rows=[
        ("https://example.com/", hashlib.sha256(token.encode()).hexdigest(), None, None, True),
        (1,), (site,), (workspace_site,), (workspace_site,),
    ])
    assert service.claim_anonymous_diagnostic(uuid4(), token, user, workspace) == workspace_site
    updates = [(sql, params) for sql, params in executions if "UPDATE privacy.diagnostic" in sql]
    assert len(updates) == 1
    assert updates[0][1][:2] == (workspace_site, user)
    assert any("INSERT INTO access.workspace_sites" in sql for sql, _ in executions)
