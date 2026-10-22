"""PW-02 contract tests: operator-only mutations and unified renewal."""
import inspect
from uuid import uuid4

import pytest
from fastapi import HTTPException

from mininode_api.api import access as api
from mininode_api.services import admin_grants, billing


def test_grant_endpoints_require_operator(monkeypatch):
    monkeypatch.setattr(api.site_group_operator, "is_operator", lambda email: False)
    user = type("User", (), {"id": uuid4(), "email": "member@example.com"})()
    with pytest.raises(HTTPException) as exc:
        api.operator_create_grant(api.AdminGrantRequest(
            workspace_site_id=uuid4(), reason="Cortesía de prueba"), user)
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException) as exc:
        api.operator_grant_sites("example.com", user)
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException) as exc:
        api.operator_revoke_grant(uuid4(), api.AdminRevokeRequest(reason="Fin de prueba"), user)
    assert exc.value.status_code == 403


def test_grants_are_audited_and_lock_site():
    sql = inspect.getsource(admin_grants.grant)
    assert "FOR UPDATE" in sql
    assert "internal_grant" in sql
    assert "entitlement_admin_events" in sql
    assert "future" in sql


def test_revocation_does_not_delete_entitlement():
    source = inspect.getsource(admin_grants.revoke)
    assert "status='revoked'" in source
    assert "DELETE FROM" not in source
    assert "entitlement_admin_events" in source


def test_billing_checks_future_periods_across_sources():
    source = inspect.getsource(billing.payment_confirmed)
    assert "active_from > %s" in source
    assert "source = 'payment'" not in source[source.index("SELECT max(active_until)"):source.index("start = max(")]


# Behavioral integration tests run against the PostgreSQL service in Access CI.
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import datetime, timedelta, timezone
import os
import psycopg
from mininode_api.services import access, privacy_diagnostic_snapshot
from test_billing_core import _seed


def _prepared():
    db, operator, site, diagnostic, now = _seed()
    admin_grants.initialize_database()
    return db, operator, site, diagnostic, now


def _periods(db, site):
    with psycopg.connect(db) as conn:
        return conn.execute("""
            SELECT id, active_from, active_until, status, source
            FROM access.entitlements WHERE workspace_site_id=%s
            ORDER BY active_from, id
        """, (site,)).fetchall()


def test_postgres_grant_revoke_and_audit():
    db, operator, site, _, _ = _prepared()
    first = admin_grants.grant(site, operator, "Cortesía comercial", days=12)
    rows = _periods(db, site)
    assert len(rows) == 1
    assert rows[0][0] == first
    assert rows[0][3:] == ("active", "internal_grant")
    assert timedelta(days=12) == rows[0][2] - rows[0][1]
    admin_grants.revoke(first, operator, "Fin de cortesía")
    assert _periods(db, site)[0][3] == "revoked"
    with psycopg.connect(db) as conn:
        events = conn.execute("""
            SELECT action, operator_user_id, reason FROM access.entitlement_admin_events
            WHERE entitlement_id=%s ORDER BY created_at, action
        """, (first,)).fetchall()
    assert {row[0] for row in events} == {"granted", "revoked"}
    assert all(row[1] == operator for row in events)
    assert {row[2] for row in events} == {"Cortesía comercial", "Fin de cortesía"}
    with pytest.raises(admin_grants.GrantConflict):
        admin_grants.revoke(first, operator, "Otra revocación")


def test_postgres_free_then_paid_continuity_and_future_limit():
    db, operator, site, diagnostic, now = _prepared()
    grant_id = admin_grants.grant(site, operator, "Primera cortesía", days=10)
    order = billing.create_order(operator, site, diagnostic)
    paid_id = billing.payment_confirmed(
        order.id, provider="test", provider_order_id="pw02-paid",
        verified_paid_at=now + timedelta(hours=1))
    rows = _periods(db, site)
    assert len(rows) == 2
    assert rows[0][0] == grant_id and rows[1][0] == paid_id
    assert rows[1][1] == rows[0][2]
    assert rows[1][2] == billing.add_calendar_month(rows[1][1])
    with pytest.raises(admin_grants.GrantConflict):
        admin_grants.grant(site, operator, "Exceso de períodos", days=7)
    with psycopg.connect(db) as conn:
        assert conn.execute("SELECT count(*) FROM access.entitlement_admin_events").fetchone()[0] == 1


def test_postgres_paid_then_free_continuity_and_future_limit():
    db, operator, site, diagnostic, now = _prepared()
    order = billing.create_order(operator, site, diagnostic)
    paid_id = billing.payment_confirmed(
        order.id, provider="test", provider_order_id="pw02-first",
        verified_paid_at=now + timedelta(hours=1))
    grant_id = admin_grants.grant(site, operator, "Cortesía posterior", days=9)
    rows = _periods(db, site)
    assert [row[0] for row in rows] == [paid_id, grant_id]
    assert rows[1][1] == rows[0][2]
    with pytest.raises(admin_grants.GrantConflict):
        admin_grants.grant(site, operator, "Exceso de períodos", days=9)


def test_postgres_concurrent_grant_and_payment_serialized():
    db, operator, site, diagnostic, now = _prepared()
    # Existing current period ensures both competing operations try to reserve
    # the single future slot; exactly one can succeed.
    admin_grants.grant(site, operator, "Período vigente", days=10)
    order = billing.create_order(operator, site, diagnostic)
    barrier = Barrier(2)

    def courtesy():
        barrier.wait()
        try:
            return ("grant", admin_grants.grant(site, operator, "Reserva futura", days=8))
        except (ValueError, admin_grants.GrantConflict):
            return ("grant_rejected", None)

    def payment():
        barrier.wait()
        try:
            return ("payment", billing.payment_confirmed(
                order.id, provider="test", provider_order_id="pw02-race",
                verified_paid_at=now + timedelta(hours=1)))
        except ValueError:
            return ("payment_rejected", None)

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(courtesy)
        b = pool.submit(payment)
        outcomes = [a.result(timeout=15), b.result(timeout=15)]
    assert sum(label in {"grant", "payment"} for label, _ in outcomes) == 1
    rows = _periods(db, site)
    assert len(rows) == 2
    assert rows[1][1] == rows[0][2]
    assert sum(row[1] > datetime.now(timezone.utc) for row in rows) == 1
    with psycopg.connect(db) as conn:
        paid = conn.execute("SELECT status FROM billing.orders WHERE id=%s", (order.id,)).fetchone()[0]
        assert paid == ("paid" if any(label == "payment" for label, _ in outcomes) else "pending")
        count = conn.execute("SELECT count(*) FROM access.entitlement_admin_events").fetchone()[0]
        assert count == (2 if any(label == "grant" for label, _ in outcomes) else 1)
