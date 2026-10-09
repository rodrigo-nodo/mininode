"""A4 Billing Core contract checks; PostgreSQL integration runs when DATABASE_URL is set."""
import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from mininode_api.services import access, billing, privacy_diagnostic_snapshot


def test_calendar_month_handles_end_of_month_and_leap_year():
    assert billing.add_calendar_month(datetime(2026, 1, 31, tzinfo=timezone.utc)) == datetime(2026, 2, 28, tzinfo=timezone.utc)
    assert billing.add_calendar_month(datetime(2028, 1, 31, tzinfo=timezone.utc)) == datetime(2028, 2, 29, tzinfo=timezone.utc)
    assert billing.add_calendar_month(datetime(2026, 12, 31, tzinfo=timezone.utc)) == datetime(2027, 1, 31, tzinfo=timezone.utc)


def test_schema_is_provider_independent_and_entitlement_is_unique():
    assert "CREATE TABLE IF NOT EXISTS billing.orders" in billing.SCHEMA_SQL
    assert "REFERENCES access.workspace_sites(id)" in billing.SCHEMA_SQL
    assert "REFERENCES privacy.diagnostic(id)" in billing.SCHEMA_SQL
    assert "ON access.entitlements (source, source_id)" in billing.SCHEMA_SQL


def test_payment_requires_trusted_reference():
    with pytest.raises(ValueError):
        billing.payment_confirmed(uuid4(), provider="", provider_order_id="x", verified_paid_at=datetime.now(timezone.utc))


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="PostgreSQL integration requires DATABASE_URL")
def test_paid_order_idempotent_and_entitlement_persisted():
    import psycopg
    from psycopg.types.json import Jsonb
    access.initialize_database()
    privacy_diagnostic_snapshot.initialize_database()
    billing.initialize_database()
    uid, wid, sid, wsid, did, oid = (uuid4() for _ in range(6))
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute("INSERT INTO access.users(id,email) VALUES (%s,%s)", (uid, f"billing-{uid}@example.com"))
        conn.execute("INSERT INTO access.workspaces(id,name) VALUES (%s,'Billing test')", (wid,))
        conn.execute("INSERT INTO access.workspace_members(workspace_id,user_id,role) VALUES (%s,%s,'owner')", (wid,uid))
        conn.execute("INSERT INTO access.sites(id,hostname) VALUES (%s,%s)", (sid,f"{sid}.example.com"))
        conn.execute("INSERT INTO access.workspace_sites(id,workspace_id,site_id) VALUES (%s,%s,%s)", (wsid,wid,sid))
        conn.execute("""INSERT INTO privacy.diagnostic(id,site_url,diagnostic_snapshot,score,purchase_expires_at,workspace_site_id)
          VALUES (%s,'https://example.com',%s,80,CURRENT_TIMESTAMP + INTERVAL '24 hours',%s)""", (did,Jsonb({}),wsid))
    try:
        order = billing.create_order(uid,wsid,did)
        assert order.amount == 9900 and order.currency == "CLP"
        paid_at = datetime.now(timezone.utc)
        entitlement = billing.payment_confirmed(order.id,provider="test",provider_order_id=str(oid),verified_paid_at=paid_at)
        assert billing.payment_confirmed(order.id,provider="test",provider_order_id=str(oid),verified_paid_at=paid_at) == entitlement
        assert billing.get_order(uid,order.id).status == "paid"
        assert billing.current_entitlement(uid,wsid)[0] == entitlement
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
            count = conn.execute("SELECT count(*) FROM access.entitlements WHERE source='payment' AND source_id=%s",(str(order.id),)).fetchone()[0]
            assert count == 1
    finally:
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
            conn.execute("DELETE FROM billing.orders WHERE workspace_site_id=%s",(wsid,))
            conn.execute("DELETE FROM access.entitlements WHERE workspace_site_id=%s",(wsid,))
            conn.execute("DELETE FROM privacy.diagnostic WHERE workspace_site_id=%s",(wsid,))
            conn.execute("DELETE FROM access.workspace_sites WHERE id=%s",(wsid,))
            conn.execute("DELETE FROM access.sites WHERE id=%s",(sid,))
            conn.execute("DELETE FROM access.workspace_members WHERE workspace_id=%s",(wid,))
            conn.execute("DELETE FROM access.workspaces WHERE id=%s",(wid,))
            conn.execute("DELETE FROM access.users WHERE id=%s",(uid,))
