"""Disposable PostgreSQL 18 end-to-end promotion smoke test."""
import os
from pathlib import Path
from uuid import uuid4
import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from mininode_api.services import access, billing, privacy_diagnostic_snapshot
from test_predeploy_migrations import runner

A = (
    "20261019_access_site_aliases.sql",
    "20261019_access_workspace_site_unlink.sql",
    "20261020_access_site_group_review_requests.sql",
    "20261020_access_site_reconciliations.sql",
    "20261020_privacy_requested_url.sql",
    "20261022_access_entitlement_admin_events.sql",
)
B = ["20261020_access_site_group_operator.sql"]


@pytest.fixture
def disposable():
    base = os.getenv("DATABASE_URL", "")
    if not base or conninfo_to_dict(base).get("dbname") != "mininode_test":
        pytest.skip("Only the CI mininode_test database is allowed")
    name = "mininode_test_promotion_" + uuid4().hex[:12]
    with psycopg.connect(base, autocommit=True) as admin:
        assert int(admin.execute("SHOW server_version_num").fetchone()[0]) // 10000 == 18
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            yield make_conninfo(base, dbname=name)
        finally:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def test_promotion_two_batches_idempotent_and_preserving(disposable):
    with psycopg.connect(disposable) as conn:
        conn.execute(access.INITIALIZE_SQL)
        conn.execute(privacy_diagnostic_snapshot.INITIALIZE_SQL)
        conn.execute(billing.SCHEMA_SQL)
        user, workspace, site, linked, diagnostic = [uuid4() for _ in range(5)]
        conn.execute("INSERT INTO access.users (id,email) VALUES (%s,'sample@example.invalid')", (user,))
        conn.execute("INSERT INTO access.workspaces (id,name) VALUES (%s,'Sample')", (workspace,))
        conn.execute("INSERT INTO access.sites (id,hostname) VALUES (%s,'sample.example.invalid')", (site,))
        conn.execute("INSERT INTO access.workspace_sites (id,workspace_id,site_id) VALUES (%s,%s,%s)", (linked,workspace,site))
        conn.execute("""INSERT INTO privacy.diagnostic
             (id,site_url,diagnostic_snapshot,score,purchase_expires_at,workspace_site_id)
             VALUES (%s,'https://sample.example.invalid','{}'::jsonb,72,now()+interval '1 day',%s)""",(diagnostic,linked))
    tables=("access.users","access.workspaces","access.sites","access.workspace_sites","privacy.diagnostic","access.entitlements","billing.orders")
    def counts():
        with psycopg.connect(disposable) as conn:
            return tuple(conn.execute("SELECT count(*) FROM "+table).fetchone()[0] for table in tables)
    initial=counts()
    assert initial == (1,1,1,1,1,0,0)
    with pytest.raises(psycopg.errors.UndefinedTable):
        runner.migrate(disposable,B)
    runner.migrate(disposable,list(A))
    assert counts()==initial
    runner.migrate(disposable,B)
    with psycopg.connect(disposable) as conn:
        history=conn.execute("SELECT filename,checksum_sha256,applied_at FROM public.schema_migrations ORDER BY filename").fetchall()
        assert len(history)==7
        assert {r[0] for r in history}==set(A+B)
        assert all(r[1]==runner.APPROVED_CHECKSUMS[r[0]] for r in history)
        for table in ("access.site_aliases","access.site_group_review_requests","access.site_group_operator_merges","access.site_reconciliations","access.entitlement_admin_events"):
            assert conn.execute("SELECT to_regclass(%s)",(table,)).fetchone()[0] is not None
        assert len(conn.execute("""SELECT 1 FROM information_schema.columns
          WHERE (table_schema='access' AND table_name='workspace_sites' AND column_name='detached_at')
             OR (table_schema='privacy' AND table_name='diagnostic' AND column_name='requested_url')""").fetchall())==2
    runner.migrate(disposable,list(A))
    runner.migrate(disposable,B)
    with psycopg.connect(disposable) as conn:
        assert conn.execute("SELECT filename,checksum_sha256,applied_at FROM public.schema_migrations ORDER BY filename").fetchall()==history
    assert counts()==initial


def test_promotion_failure_rolls_back_in_disposable_database(disposable,monkeypatch,tmp_path):
    from hashlib import sha256
    name="broken_example.sql"
    body="CREATE TABLE public.rollback_probe (id int); SELECT 1/0;"
    (tmp_path/name).write_text(body)
    monkeypatch.setattr(runner,"MIGRATIONS_DIR",tmp_path)
    monkeypatch.setitem(runner.APPROVED_CHECKSUMS,name,sha256(body.encode()).hexdigest())
    with pytest.raises(psycopg.errors.DivisionByZero):
        runner.migrate(disposable,[name])
    with psycopg.connect(disposable) as conn:
        assert conn.execute("SELECT to_regclass('public.rollback_probe')").fetchone()[0] is None
        assert conn.execute("SELECT to_regclass('public.schema_migrations')").fetchone()[0] is None
