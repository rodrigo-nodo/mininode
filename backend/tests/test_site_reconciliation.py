"""Real PostgreSQL regression for manually approved apex/www reconciliation."""
from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import psycopg
import pytest

from mininode_api.services import access, billing
from mininode_api.services import privacy_diagnostic_snapshot as snapshots
from mininode_api.services import site_aliases, site_reconciliation as merge

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"


@pytest.fixture
def pair():
    url = os.environ.get("DATABASE_URL", "")
    if "mininode_test" not in url:
        pytest.skip("Reconciliation mutation tests require disposable mininode_test")

    access.initialize_database()
    snapshots.initialize_database()
    billing.initialize_database()
    # Same migration that Pre-deploy will execute, on preexisting Access tables.
    with psycopg.connect(url) as db:
        for filename in ("20261019_access_site_aliases.sql", "20261020_access_site_reconciliations.sql"):
            db.execute((MIGRATIONS / filename).read_text())
    user, workspace, primary_site, source_site, primary_ws, source_ws = (uuid4() for _ in range(6))
    root = f"example-{uuid4().hex}.com"
    alias = f"www.{root}"
    with psycopg.connect(url) as db:
        db.execute("INSERT INTO access.users (id,email) VALUES (%s,%s)", (user, f"{user}@example.test"))
        db.execute("INSERT INTO access.workspaces (id,name) VALUES (%s,'Reconcile test')", (workspace,))
        db.execute(
            "INSERT INTO access.workspace_members (workspace_id,user_id,role) VALUES (%s,%s,'owner')",
            (workspace, user),
        )
        db.execute(
            """INSERT INTO access.sites (id,hostname,canonical_url)
               VALUES (%s,%s,%s),(%s,%s,%s)""",
            (primary_site, root, "https://" + root, source_site, alias, "https://" + alias),
        )
        db.execute(
            """INSERT INTO access.workspace_sites
               (id,workspace_id,site_id,detached_at)
               VALUES (%s,%s,%s,NULL),(%s,%s,%s,CURRENT_TIMESTAMP)""",
            (primary_ws,workspace,primary_site,source_ws,workspace,source_site),
        )
    first = snapshots.create_diagnostic_snapshot(
        {"site_url": "https://" + root, "score": 48, "evidence": {"key": "original"}},
        workspace_site_id=primary_ws,
    )
    second = snapshots.create_diagnostic_snapshot(
        {"site_url": "https://" + alias, "score": 47, "evidence": {"key": "kept"}},
        workspace_site_id=source_ws,
    )
    data = dict(
        url=url, user=user, workspace=workspace, root=root, alias=alias,
        primary_site=primary_site, source_site=source_site,
        primary_ws=primary_ws, source_ws=source_ws,
        diagnostic_ids=(first.id, second.id),
    )
    yield data

    with psycopg.connect(url) as db:
        db.execute("DELETE FROM access.site_reconciliations WHERE source_site_id = %s", (source_site,))
        db.execute("DELETE FROM access.site_aliases WHERE site_id IN (%s,%s) OR hostname = %s",
                   (primary_site, source_site, alias))
        db.execute("DELETE FROM access.entitlements WHERE workspace_site_id IN (%s,%s)", (primary_ws,source_ws))
        db.execute("DELETE FROM billing.orders WHERE workspace_site_id IN (%s,%s)", (primary_ws,source_ws))
        db.execute("DELETE FROM privacy.diagnostic WHERE id = ANY(%s)", (list(data["diagnostic_ids"]),))
        db.execute("DELETE FROM access.workspace_sites WHERE id IN (%s,%s)", (primary_ws,source_ws))
        db.execute("DELETE FROM access.sites WHERE id IN (%s,%s)", (primary_site,source_site))
        db.execute("DELETE FROM access.workspace_members WHERE workspace_id=%s", (workspace,))
        db.execute("DELETE FROM access.workspaces WHERE id=%s", (workspace,))
        db.execute("DELETE FROM access.users WHERE id=%s", (user,))


def stable(pair):
    return lambda url: SimpleNamespace(
        equivalent=True, requested_hostname=url,
        counterpart_hostname=pair["root"], reason="stable_www_redirect",
    )


def run(pair, *, apply=False, verifier=None):
    return merge.reconcile_existing_www(
        pair["workspace"], pair["root"], pair["alias"],
        apply=apply, verifier=verifier or stable(pair),
    )


def test_dry_run_does_not_write_and_apply_preserves_history(pair):
    dry = run(pair)
    assert dry.status == "ready"
    assert dry.diagnostics == 1
    with psycopg.connect(pair["url"]) as db:
        assert db.execute("SELECT count(*) FROM access.site_reconciliations").fetchone()[0] >= 0
        assert db.execute("SELECT site_id FROM access.workspace_sites WHERE id = %s", (pair["source_ws"],)).fetchone()[0] == pair["source_site"]
        assert db.execute("SELECT count(*) FROM access.site_aliases WHERE hostname = %s", (pair["alias"],)).fetchone()[0] == 0

    result = run(pair, apply=True)
    assert result.status == "applied"
    assert result.primary_site_id == pair["primary_site"]
    assert result.primary_workspace_site_id == pair["primary_ws"]
    assert result.diagnostics == 1
    with psycopg.connect(pair["url"]) as db:
        rows = db.execute(
            """SELECT site_url,score,workspace_site_id,diagnostic_snapshot
               FROM privacy.diagnostic WHERE id = ANY(%s) ORDER BY site_url""",
            (list(pair["diagnostic_ids"]),),
        ).fetchall()
        assert len(rows) == 2
        assert {x[0] for x in rows} == {"https://" + pair["root"], "https://" + pair["alias"]}
        assert {x[1] for x in rows} == {47, 48}
        assert {x[2] for x in rows} == {pair["primary_ws"]}
        assert {x[3]["evidence"]["key"] for x in rows} == {"original", "kept"}
        assert db.execute("SELECT count(*) FROM access.workspace_sites WHERE id=%s", (pair["source_ws"],)).fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM access.sites WHERE id=%s", (pair["source_site"],)).fetchone()[0] == 0
        assert db.execute(
            "SELECT site_id,verification_method FROM access.site_aliases WHERE hostname = %s", (pair["alias"],)
        ).fetchone() == (pair["primary_site"], "stable_redirect")
        assert db.execute(
            "SELECT source_site_id,moved_diagnostics FROM access.site_reconciliations WHERE source_hostname = %s",
            (pair["alias"],),
        ).fetchone() == (pair["source_site"], 1)
        assert site_aliases.resolve_existing_site(db.cursor(), pair["alias"]) == (pair["primary_site"], pair["root"])

    assert run(pair).status == "already_reconciled"
    assert run(pair, apply=True).status == "already_reconciled"
    assert len(snapshots.list_latest_for_workspace(pair["workspace"])) == 1
    assert snapshots.get_latest_for_workspace_site(pair["primary_ws"]).score in (47, 48)


def test_rejects_unproven_redirect_and_malformed_pair_without_writes(pair):
    rejected = lambda _: SimpleNamespace(
        equivalent=False, requested_hostname=pair["alias"],
        counterpart_hostname=pair["root"], reason="insufficient_redirect_evidence",
    )
    with pytest.raises(merge.ReconciliationBlocked, match="evidence"):
        run(pair, apply=True, verifier=rejected)
    with pytest.raises(merge.ReconciliationBlocked, match="Only exact"):
        merge.reconcile_existing_www(pair["workspace"], "www." + pair["root"], pair["root"])
    with psycopg.connect(pair["url"]) as db:
        assert db.execute("SELECT count(*) FROM access.sites WHERE id = %s", (pair["source_site"],)).fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM access.site_reconciliations WHERE source_site_id=%s", (pair["source_site"],)).fetchone()[0] == 0


def test_rejects_undetched_source_and_foreign_workspace(pair):
    with psycopg.connect(pair["url"]) as db:
        db.execute("UPDATE access.workspace_sites SET detached_at = NULL WHERE id=%s", (pair["source_ws"],))
    with pytest.raises(merge.ReconciliationBlocked, match="unlink"):
        run(pair, apply=True)
    with psycopg.connect(pair["url"]) as db:
        db.execute("UPDATE access.workspace_sites SET detached_at = CURRENT_TIMESTAMP WHERE id=%s", (pair["source_ws"],))
    other_user, other_ws, other_link = uuid4(), uuid4(), uuid4()
    with psycopg.connect(pair["url"]) as db:
        db.execute("INSERT INTO access.users(id,email) VALUES (%s,%s)", (other_user, f"{other_user}@example.test"))
        db.execute("INSERT INTO access.workspaces(id,name) VALUES (%s,'Other')", (other_ws,))
        db.execute("INSERT INTO access.workspace_sites(id,workspace_id,site_id) VALUES (%s,%s,%s)", (other_link,other_ws,pair["source_site"]))
    try:
        with pytest.raises(merge.ReconciliationBlocked, match="only to the selected workspace"):
            run(pair, apply=True)
        with psycopg.connect(pair["url"]) as db:
            assert db.execute("SELECT count(*) FROM access.site_reconciliations WHERE source_site_id=%s", (pair["source_site"],)).fetchone()[0] == 0
    finally:
        with psycopg.connect(pair["url"]) as db:
            db.execute("DELETE FROM access.workspace_sites WHERE id=%s", (other_link,))
            db.execute("DELETE FROM access.workspaces WHERE id=%s", (other_ws,))
            db.execute("DELETE FROM access.users WHERE id=%s", (other_user,))


def test_commercial_references_and_source_aliases_block(pair):
    with psycopg.connect(pair["url"]) as db:
        db.execute(
            """INSERT INTO access.entitlements
               (id,workspace_site_id,product_code,active_from,active_until,status,source)
               VALUES (%s,%s,'privacy_web',CURRENT_TIMESTAMP - INTERVAL '90 days',
                       CURRENT_TIMESTAMP - INTERVAL '60 days','active','test')""",
            (uuid4(),pair["primary_ws"]),
        )
    with pytest.raises(merge.ReconciliationBlocked, match="Commercial"):
        run(pair, apply=True)
    with psycopg.connect(pair["url"]) as db:
        db.execute("DELETE FROM access.entitlements WHERE workspace_site_id=%s", (pair["primary_ws"],))
        db.execute(
            """INSERT INTO access.site_aliases (id,site_id,hostname,verification_method)
               VALUES (%s,%s,%s,'stable_redirect')""",
            (uuid4(),pair["source_site"],"other-" + pair["alias"]),
        )
    with pytest.raises(merge.ReconciliationBlocked, match="site aliases"):
        run(pair, apply=True)


def test_catalog_digest_is_correct():
    from importlib.util import module_from_spec, spec_from_file_location
    script = Path(__file__).resolve().parents[1] / "scripts" / "predeploy_migrations.py"
    spec = spec_from_file_location("predeploy_migrations_reconciliation_test", script)
    runner = module_from_spec(spec)
    spec.loader.exec_module(runner)
    sql, digest = runner.load_sql("20261020_access_site_reconciliations.sql")
    assert digest == runner.APPROVED_CHECKSUMS["20261020_access_site_reconciliations.sql"]
    assert "CREATE TABLE IF NOT EXISTS access.site_reconciliations" in sql
