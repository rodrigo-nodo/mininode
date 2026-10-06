import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
import pytest

from mininode_api.services import access, billing, privacy_diagnostic_snapshot


def test_privacy_web_price_is_server_side():
    assert billing.PRODUCT == "privacy_web"
    assert billing.PRICE_CLP == 9900


def test_calendar_month_is_not_fixed_30_days():
    assert billing.add_calendar_month(datetime(2026, 1, 31, tzinfo=timezone.utc)) == datetime(2026, 2, 28, tzinfo=timezone.utc)
    assert billing.add_calendar_month(datetime(2026, 12, 6, tzinfo=timezone.utc)) == datetime(2027, 1, 6, tzinfo=timezone.utc)


def test_frontend_cannot_set_price():
    from mininode_api.api.billing import CreateOrderRequest
    assert set(CreateOrderRequest.model_fields) == {"workspace_site_id", "diagnostic_id"}


def _seed():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required for Billing PostgreSQL integration tests")

    with psycopg.connect(database_url) as conn, conn.cursor() as cur:
        cur.execute("DROP SCHEMA IF EXISTS billing CASCADE")
        cur.execute("DROP SCHEMA IF EXISTS privacy CASCADE")
        cur.execute("DROP SCHEMA IF EXISTS access CASCADE")

    access.initialize_database()
    privacy_diagnostic_snapshot.initialize_database()
    billing.initialize_database()

    user_id, workspace_id, site_id, workspace_site_id, diagnostic_id = (uuid4() for _ in range(5))
    now = datetime.now(timezone.utc)

    with psycopg.connect(database_url) as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO access.users (id,email) VALUES (%s,%s)", (user_id, f"{user_id}@example.com"))
        cur.execute("INSERT INTO access.workspaces (id,name) VALUES (%s,'Billing')", (workspace_id,))
        cur.execute(
            "INSERT INTO access.workspace_members (workspace_id,user_id,role) VALUES (%s,%s,'owner')",
            (workspace_id, user_id),
        )
        cur.execute("INSERT INTO access.sites (id,hostname) VALUES (%s,%s)", (site_id, f"{site_id}.example.com"))
        cur.execute(
            "INSERT INTO access.workspace_sites (id,workspace_id,site_id) VALUES (%s,%s,%s)",
            (workspace_site_id, workspace_id, site_id),
        )
        cur.execute(
            """
            INSERT INTO privacy.diagnostic
              (id,site_url,diagnostic_snapshot,score,created_at,purchase_expires_at,workspace_site_id)
            VALUES (%s,%s,'{}'::jsonb,80,%s,%s,%s)
            """,
            (diagnostic_id, "https://example.com", now, now + timedelta(hours=24), workspace_site_id),
        )

    return database_url, user_id, workspace_site_id, diagnostic_id, now


def test_payment_confirmed_real_postgres_idempotent_and_within_window():
    database_url, user_id, workspace_site_id, diagnostic_id, now = _seed()
    order = billing.create_order(user_id, workspace_site_id, diagnostic_id)

    first = billing.payment_confirmed(
        order.id, provider="test", provider_order_id="pay-1", verified_paid_at=now + timedelta(hours=1)
    )
    second = billing.payment_confirmed(
        order.id, provider="test", provider_order_id="pay-1", verified_paid_at=now + timedelta(hours=1)
    )

    assert second == first
    with psycopg.connect(database_url) as conn:
        assert conn.execute("SELECT count(*) FROM access.entitlements WHERE source_id=%s", (str(order.id),)).fetchone()[0] == 1


def test_payment_confirmed_rejects_expired_diagnostic_without_side_effects():
    database_url, user_id, workspace_site_id, diagnostic_id, now = _seed()
    order = billing.create_order(user_id, workspace_site_id, diagnostic_id)

    with pytest.raises(ValueError, match="Diagnostic purchase window expired"):
        billing.payment_confirmed(
            order.id, provider="test", provider_order_id="pay-expired", verified_paid_at=now + timedelta(hours=25)
        )

    with psycopg.connect(database_url) as conn:
        row = conn.execute("SELECT status, paid_at FROM billing.orders WHERE id=%s", (order.id,)).fetchone()
        assert row == ("pending", None)
        assert conn.execute("SELECT count(*) FROM access.entitlements").fetchone()[0] == 0


def test_one_early_renewal_allowed_but_second_future_period_rejected():
    database_url, user_id, workspace_site_id, diagnostic_id, now = _seed()
    order1 = billing.create_order(user_id, workspace_site_id, diagnostic_id)
    first = billing.payment_confirmed(
        order1.id, provider="test", provider_order_id="pay-1", verified_paid_at=now + timedelta(hours=1)
    )

    diagnostic2 = uuid4()
    diagnostic3 = uuid4()
    with psycopg.connect(database_url) as conn, conn.cursor() as cur:
        for diag in (diagnostic2, diagnostic3):
            cur.execute(
                """
                INSERT INTO privacy.diagnostic
                  (id,site_url,diagnostic_snapshot,score,created_at,purchase_expires_at,workspace_site_id)
                VALUES (%s,%s,'{}'::jsonb,80,%s,%s,%s)
                """,
                (diag, "https://example.com", now, now + timedelta(hours=24), workspace_site_id),
            )

    order2 = billing.create_order(user_id, workspace_site_id, diagnostic2)
    second = billing.payment_confirmed(
        order2.id, provider="test", provider_order_id="pay-2", verified_paid_at=now + timedelta(hours=2)
    )

    with psycopg.connect(database_url) as conn:
        rows = conn.execute(
            "SELECT id,active_from,active_until FROM access.entitlements WHERE id IN (%s,%s) ORDER BY active_from",
            (first, second),
        ).fetchall()
        assert rows[1][1] == rows[0][2]

    order3 = billing.create_order(user_id, workspace_site_id, diagnostic3)
    with pytest.raises(ValueError, match="already has one future period paid"):
        billing.payment_confirmed(
            order3.id, provider="test", provider_order_id="pay-3", verified_paid_at=now + timedelta(hours=3)
        )
