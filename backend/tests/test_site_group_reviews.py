"""Workspace-safe operator review requests without any identity or billing mutations."""
import os
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from mininode_api.services import access, billing, privacy_diagnostic_snapshot, site_group_operator as operator, site_group_reviews as reviews


@pytest.fixture
def workspace_pair():
    url = os.getenv("DATABASE_URL", "")
    if "mininode_test" not in url:
        pytest.skip("Review queue integration tests require disposable mininode_test")
    access.initialize_database()
    billing.initialize_database()
    sql = (Path(__file__).resolve().parents[1] / "migrations" /
           "20261020_access_site_group_review_requests.sql").read_text()
    with psycopg.connect(url) as db:
        db.execute(sql)
        for name in ("20261019_access_site_aliases.sql",
                     "20261020_access_site_reconciliations.sql",
                     "20261020_access_site_group_operator.sql"):
            db.execute((Path(__file__).resolve().parents[1] / "migrations" / name).read_text())
    privacy_diagnostic_snapshot.initialize_database()

    user, other, workspace, foreign_workspace = (uuid4() for _ in range(4))
    first_site, second_site, foreign_site = (uuid4() for _ in range(3))
    first_link, second_link, foreign_link = (uuid4() for _ in range(3))
    with psycopg.connect(url) as db:
        db.execute(
            "INSERT INTO access.users(id,email) VALUES (%s,%s),(%s,%s)",
            (user, str(user) + "@example.test", other, str(other) + "@example.test"),
        )
        db.execute(
            "INSERT INTO access.workspaces(id,name) VALUES (%s,'Primary'),(%s,'Other')",
            (workspace, foreign_workspace),
        )
        db.execute(
            """INSERT INTO access.workspace_members(workspace_id,user_id,role)
               VALUES (%s,%s,'owner'),(%s,%s,'owner')""",
            (workspace, user, foreign_workspace, other),
        )
        for site_id, host in (
            (first_site, "example-" + first_site.hex + ".com"),
            (second_site, "www.example-" + second_site.hex + ".com"),
            (foreign_site, "foreign-" + foreign_site.hex + ".com"),
        ):
            db.execute(
                "INSERT INTO access.sites(id,hostname) VALUES (%s,%s)",
                (site_id, host),
            )
        db.execute(
            """INSERT INTO access.workspace_sites(id,workspace_id,site_id)
               VALUES (%s,%s,%s),(%s,%s,%s),(%s,%s,%s)""",
            (first_link, workspace, first_site,
             second_link, workspace, second_site,
             foreign_link, foreign_workspace, foreign_site),
        )
    yield dict(
        url=url, user=user, other=other, workspace=workspace,
        foreign_workspace=foreign_workspace, first=first_link,
        second=second_link, foreign=foreign_link,
        site_ids=[first_site, second_site, foreign_site],
    )
    with psycopg.connect(url) as db:
        db.execute("DELETE FROM access.site_group_operator_merges WHERE workspace_id=%s", (workspace,))
        db.execute("DELETE FROM access.site_aliases WHERE site_id = ANY(%s)", ([first_site, second_site, foreign_site],))
        db.execute("DELETE FROM privacy.diagnostic WHERE workspace_site_id IN (%s,%s,%s)",
                   (first_link, second_link, foreign_link))
        db.execute("DELETE FROM access.entitlements WHERE workspace_site_id IN (%s,%s,%s)",
                   (first_link, second_link, foreign_link))
        db.execute("DELETE FROM access.site_group_review_requests WHERE workspace_id=%s", (workspace,))
        db.execute("DELETE FROM access.workspace_sites WHERE id IN (%s,%s,%s)",
                   (first_link, second_link, foreign_link))
        db.execute("DELETE FROM access.sites WHERE id = ANY(%s)", ([first_site, second_site, foreign_site],))
        db.execute("DELETE FROM access.workspace_members WHERE workspace_id IN (%s,%s)",
                   (workspace, foreign_workspace))
        db.execute("DELETE FROM access.workspaces WHERE id IN (%s,%s)", (workspace, foreign_workspace))
        db.execute("DELETE FROM access.users WHERE id IN (%s,%s)", (user, other))


def test_review_request_idempotent_authorized_and_noncommercial(workspace_pair):
    p = workspace_pair
    with psycopg.connect(p["url"]) as db:
        original_ids = db.execute(
            "SELECT id, site_id FROM access.workspace_sites WHERE workspace_id=%s ORDER BY id",
            (p["workspace"],),
        ).fetchall()
    first = reviews.create_review_request(p["user"], p["workspace"], p["second"], p["first"])
    again = reviews.create_review_request(p["user"], p["workspace"], p["first"], p["second"])
    assert first == again
    assert first.status == "pending"
    assert set((first.first_workspace_site_id, first.second_workspace_site_id)) == {p["first"], p["second"]}
    assert reviews.list_review_requests(p["user"], p["workspace"]) == (first,)
    with psycopg.connect(p["url"]) as db:
        assert db.execute(
            "SELECT id, site_id FROM access.workspace_sites WHERE workspace_id=%s ORDER BY id",
            (p["workspace"],),
        ).fetchall() == original_ids
        assert db.execute(
            "SELECT COUNT(*) FROM access.entitlements WHERE workspace_site_id IN (%s,%s)",
            (p["first"], p["second"]),
        ).fetchone()[0] == 0
        assert db.execute(
            "SELECT COUNT(*) FROM access.site_group_review_requests WHERE workspace_id=%s",
            (p["workspace"],),
        ).fetchone()[0] == 1


def test_review_rejects_foreign_and_unauthorized_sites(workspace_pair):
    p = workspace_pair
    assert reviews.create_review_request(p["other"], p["workspace"], p["first"], p["second"]) is None
    assert reviews.create_review_request(p["user"], p["workspace"], p["first"], p["foreign"]) is None
    assert reviews.list_review_requests(p["other"], p["workspace"]) is None
    with pytest.raises(ValueError, match="distintos"):
        reviews.create_review_request(p["user"], p["workspace"], p["first"], p["first"])


def test_review_does_not_expose_detached_sites(workspace_pair):
    p = workspace_pair
    reviews.create_review_request(p["user"], p["workspace"], p["first"], p["second"])
    with psycopg.connect(p["url"]) as db:
        db.execute(
            "UPDATE access.workspace_sites SET detached_at = CURRENT_TIMESTAMP WHERE id = %s",
            (p["second"],),
        )
    assert reviews.list_review_requests(p["user"], p["workspace"]) == ()
    assert reviews.create_review_request(p["user"], p["workspace"], p["first"], p["second"]) is None


def test_detachment_invalidates_pending_and_relink_does_not_restore_it(workspace_pair):
    """Covers the real endpoint persistence path, not just read filtering."""
    p = workspace_pair
    initial = reviews.create_review_request(p["user"], p["workspace"], p["first"], p["second"])
    assert access.unlink_workspace_site(p["user"], p["workspace"], p["second"]) is True
    with psycopg.connect(p["url"]) as db:
        assert db.execute(
            """SELECT status, invalidated_at IS NOT NULL
               FROM access.site_group_review_requests WHERE id = %s""", (initial.id,),
        ).fetchone() == ("invalidated", True)
        hostname = db.execute(
            """SELECT s.hostname FROM access.workspace_sites ws
               JOIN access.sites s ON s.id=ws.site_id WHERE ws.id=%s""",
            (p["second"],),
        ).fetchone()[0]
    assert reviews.list_review_requests(p["user"], p["workspace"]) == ()
    restored = access.follow_site(p["user"], p["workspace"], "https://" + hostname)
    assert restored.id == p["second"]
    after_relink = reviews.list_review_requests(p["user"], p["workspace"])
    assert len(after_relink) == 1
    assert after_relink[0].status == "invalidated"
    # No pending request reappears just because the same association was restored.
    assert not any(row.status == "pending" for row in after_relink)
    resubmitted = reviews.create_review_request(p["user"], p["workspace"], p["second"], p["first"])
    assert resubmitted.id == initial.id
    assert resubmitted.status == "pending"
    with psycopg.connect(p["url"]) as db:
        assert db.execute(
            "SELECT invalidated_at FROM access.site_group_review_requests WHERE id=%s",
            (initial.id,),
        ).fetchone()[0] is None


def test_direct_sql_detachment_also_invalidates_pending_review(workspace_pair):
    p = workspace_pair
    initial = reviews.create_review_request(p["user"], p["workspace"], p["first"], p["second"])
    with psycopg.connect(p["url"]) as db:
        db.execute(
            "UPDATE access.workspace_sites SET detached_at = CURRENT_TIMESTAMP WHERE id = %s",
            (p["first"],),
        )
        assert db.execute(
            "SELECT status FROM access.site_group_review_requests WHERE id=%s",
            (initial.id,),
        ).fetchone()[0] == "invalidated"


def test_database_rejects_cross_workspace_review_even_if_service_is_bypassed(workspace_pair):
    p = workspace_pair
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with psycopg.connect(p["url"]) as db:
            db.execute(
                """INSERT INTO access.site_group_review_requests
                      (id, workspace_id, first_workspace_site_id,
                       second_workspace_site_id, requested_by_user_id)
                   VALUES (%s,%s,%s,%s,%s)""",
                (uuid4(), p["workspace"], min(p["first"], p["foreign"]),
                 max(p["first"], p["foreign"]), p["user"]),
            )
    with psycopg.connect(p["url"]) as db:
        assert db.execute(
            "SELECT COUNT(*) FROM access.site_group_review_requests WHERE workspace_id=%s",
            (p["workspace"],),
        ).fetchone()[0] == 0


def _prepare_operator_pair(pair):
    """Use a uniquely named apex/www pair and persist source evidence."""
    apex = "group-" + pair["first"].hex + ".cl"
    alias = "www." + apex
    with psycopg.connect(pair["url"]) as db:
        db.execute("UPDATE access.sites SET hostname=%s WHERE id=%s",
                   (apex, pair["site_ids"][0]))
        db.execute("UPDATE access.sites SET hostname=%s WHERE id=%s",
                   (alias, pair["site_ids"][1]))
    return apex, alias


def test_operator_approval_moves_only_noncommercial_history_and_keeps_audit(workspace_pair, monkeypatch):
    p = workspace_pair
    apex, alias = _prepare_operator_pair(p)
    request = reviews.create_review_request(p["user"], p["workspace"], p["first"], p["second"])
    monkeypatch.setattr(operator, "_stable_redirect", lambda a, b: (alias, apex))
    diagnostic_id = uuid4()
    with psycopg.connect(p["url"]) as db:
        db.execute("""
            INSERT INTO privacy.diagnostic(id,site_url,requested_url,diagnostic_snapshot,
                    score,purchase_expires_at,workspace_site_id)
            VALUES (%s,%s,%s,'{}'::jsonb,72,NOW() + INTERVAL '1 day',%s)
        """, (diagnostic_id, "https://" + apex, "https://" + alias, p["second"]))
    result = operator.decide(request.id, p["user"], "approved", "Redirección HTTPS verificada")
    assert result["status"] == "approved" and result["moved_diagnostics"] == 1
    with psycopg.connect(p["url"]) as db:
        assert db.execute(
            "SELECT workspace_site_id FROM privacy.diagnostic WHERE id=%s",
            (diagnostic_id,),
        ).fetchone()[0] == p["first"]
        assert db.execute(
            "SELECT detached_at IS NOT NULL FROM access.workspace_sites WHERE id=%s",
            (p["second"],),
        ).fetchone()[0] is True
        assert db.execute(
            "SELECT site_id FROM access.site_aliases WHERE hostname=%s",
            (alias,),
        ).fetchone()[0] == p["site_ids"][0]
        assert db.execute(
            "SELECT source_site_snapshot->>'hostname' FROM access.site_group_operator_merges WHERE review_id=%s",
            (request.id,),
        ).fetchone()[0] == alias
        assert db.execute(
            "SELECT status,reviewed_by_user_id FROM access.site_group_review_requests WHERE id=%s",
            (request.id,),
        ).fetchone() == ("approved", p["user"])
    assert access.follow_site(p["user"], p["workspace"], "https://" + alias).id == p["first"]
    assert [r.status for r in reviews.list_review_requests(p["user"], p["workspace"])] == ["approved"]
    with pytest.raises(operator.OperatorConflict):
        operator.decide(request.id, p["user"], "approved", "Second approval")


def test_operator_reject_audits_without_merging(workspace_pair, monkeypatch):
    p = workspace_pair
    request = reviews.create_review_request(p["user"], p["workspace"], p["first"], p["second"])
    monkeypatch.setattr(operator, "_stable_redirect", lambda a, b: (_ for _ in ()).throw(AssertionError("unexpected probe")))
    result = operator.decide(request.id, p["user"], "rejected", "No corresponde")
    assert result == {"id": request.id, "status": "rejected", "moved_diagnostics": 0}
    with psycopg.connect(p["url"]) as db:
        assert db.execute("SELECT count(*) FROM access.site_group_operator_merges WHERE review_id=%s",
                          (request.id,)).fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM access.workspace_sites WHERE workspace_id=%s AND detached_at IS NULL",
                          (p["workspace"],)).fetchone()[0] == 2


def test_operator_rejects_commercial_pair_without_side_effects(workspace_pair, monkeypatch):
    p = workspace_pair
    apex, alias = _prepare_operator_pair(p)
    request = reviews.create_review_request(p["user"], p["workspace"], p["first"], p["second"])
    monkeypatch.setattr(operator, "_stable_redirect", lambda a, b: (alias, apex))
    with psycopg.connect(p["url"]) as db:
        db.execute("""
            INSERT INTO access.entitlements (id,workspace_site_id,product_code,
                    active_from,active_until,status,source)
            VALUES (%s,%s,'privacy_web',NOW(),NOW()+INTERVAL '1 month','active','test')
        """, (uuid4(), p["second"]))
    with pytest.raises(operator.OperatorConflict, match="entitlements"):
        operator.decide(request.id, p["user"], "approved", "Verificado, pero contratado")
    with psycopg.connect(p["url"]) as db:
        assert db.execute("SELECT status FROM access.site_group_review_requests WHERE id=%s",
                          (request.id,)).fetchone()[0] == "pending"
        assert db.execute("SELECT count(*) FROM access.site_group_operator_merges WHERE review_id=%s",
                          (request.id,)).fetchone()[0] == 0


def test_operator_fails_closed_without_proven_redirect(workspace_pair, monkeypatch):
    p = workspace_pair
    request = reviews.create_review_request(p["user"], p["workspace"], p["first"], p["second"])
    monkeypatch.setattr(operator, "_stable_redirect", lambda a,b: None)
    with pytest.raises(operator.OperatorConflict, match="evidencia"):
        operator.decide(request.id, p["user"], "approved", "Sin prueba")
    assert reviews.list_review_requests(p["user"], p["workspace"])[0].status == "pending"


def test_operator_notification_requires_configuration_and_is_idempotent(workspace_pair, monkeypatch):
    p = workspace_pair
    request = reviews.create_review_request(p["user"], p["workspace"], p["first"], p["second"])
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    assert operator.notify_pending(request.id) is False
    monkeypatch.setenv("RESEND_API_KEY", "test-only")
    monkeypatch.setenv("MININODE_CONTACT_EMAIL", "contacto@example.test")
    monkeypatch.setenv("MININODE_REVIEW_FROM_EMAIL", "notifications@example.test")
    sent = []
    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
    monkeypatch.setattr(operator, "urlopen", lambda req, timeout: sent.append(req) or Response())
    assert operator.notify_pending(request.id) is True
    assert operator.notify_pending(request.id) is False
    assert len(sent) == 1
    with psycopg.connect(p["url"]) as db:
        assert db.execute("SELECT notification_sent_at IS NOT NULL FROM access.site_group_review_requests WHERE id=%s",
                          (request.id,)).fetchone()[0] is True
