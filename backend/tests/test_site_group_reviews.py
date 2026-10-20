"""Workspace-safe operator review requests without any identity or billing mutations."""
import os
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from mininode_api.services import access, billing, site_group_reviews as reviews


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
