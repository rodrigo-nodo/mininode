"""Real PostgreSQL contract tests for anonymous diagnostic claims."""
import hashlib
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))
from mininode_api.services import access, privacy_diagnostic_snapshot as snapshot  # noqa: E402

MIGRATION = SRC.parent / "migrations" / "20261013_privacy_anonymous_claim.sql"


@pytest.fixture
def pg_claim():
    url = os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL required")
    access.initialize_database()
    snapshot.initialize_database()
    sql = MIGRATION.read_text(encoding="utf-8")
    for _ in range(2):
        with psycopg.connect(url) as connection, connection.cursor() as cursor:
            cursor.execute(sql)
    user1, user2, workspace1, workspace2 = (uuid4() for _ in range(4))
    host = f"claim-{uuid4().hex}.example"
    token = "test-claim-proof-" + uuid4().hex
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute("INSERT INTO access.users (id,email) VALUES (%s,%s),(%s,%s)",
                       (user1, f"{user1}@example.test", user2, f"{user2}@example.test"))
        cursor.execute("INSERT INTO access.workspaces (id,name) VALUES (%s,'Private 1'),(%s,'Private 2')",
                       (workspace1, workspace2))
        cursor.execute("INSERT INTO access.workspace_members (workspace_id,user_id,role) VALUES (%s,%s,'owner'),(%s,%s,'owner')",
                       (workspace1, user1, workspace2, user2))
    result = snapshot.create_diagnostic_snapshot({"site_url": f"https://{host}/", "score": 77, "controls": [{"code": "example"}]}, claim_token=token)
    yield url, result.id, token, user1, user2, workspace1, workspace2, host
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute("DELETE FROM privacy.diagnostic WHERE id=%s", (result.id,))
        cursor.execute("DELETE FROM access.workspace_sites WHERE workspace_id IN (%s,%s)", (workspace1, workspace2))
        cursor.execute("DELETE FROM access.sites WHERE hostname=%s", (host,))
        cursor.execute("DELETE FROM access.workspace_members WHERE workspace_id IN (%s,%s)", (workspace1, workspace2))
        cursor.execute("DELETE FROM access.workspaces WHERE id IN (%s,%s)", (workspace1, workspace2))
        cursor.execute("DELETE FROM access.users WHERE id IN (%s,%s)", (user1, user2))


def test_claim_atomic_and_snapshot_unchanged(pg_claim):
    url, did, token, owner, other, workspace, foreign, host = pg_claim
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT diagnostic_snapshot FROM privacy.diagnostic WHERE id=%s", (did,))
        original = cursor.fetchone()[0]
    with pytest.raises(snapshot.PrivacyDiagnosticClaimRejectedError):
        snapshot.claim_anonymous_diagnostic(did, token, owner, foreign)
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM access.workspace_sites WHERE workspace_id=%s", (foreign,))
        assert cursor.fetchone()[0] == 0
    linked = snapshot.claim_anonymous_diagnostic(did, token, owner, workspace)
    assert snapshot.claim_anonymous_diagnostic(did, token, owner, workspace) == linked
    with pytest.raises(snapshot.PrivacyDiagnosticClaimRejectedError):
        snapshot.claim_anonymous_diagnostic(did, token, other, foreign)
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT diagnostic_snapshot, workspace_site_id, claimed_by_user_id FROM privacy.diagnostic WHERE id=%s", (did,))
        stored, site_id, claimant = cursor.fetchone()
        assert stored == original and site_id == linked and claimant == owner


def test_claim_rolls_back_site_on_update_failure(pg_claim):
    url, did, token, owner, other, workspace, foreign, host = pg_claim
    # Database trigger simulates failure after both Access inserts, before diagnostic update.
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute("""CREATE OR REPLACE FUNCTION pg_temp.reject_claim() RETURNS trigger
                          LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'forced claim failure'; END $$""")
        # Temporary triggers are not shared by the service connection, so use a
        # permanent, uniquely named constraint instead to force UPDATE failure.
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute("ALTER TABLE privacy.diagnostic ADD CONSTRAINT claim_test_reject CHECK (claimed_by_user_id IS NULL) NOT VALID")
    try:
        with pytest.raises(psycopg.errors.CheckViolation):
            snapshot.claim_anonymous_diagnostic(did, token, owner, workspace)
        with psycopg.connect(url) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM access.workspace_sites WHERE workspace_id=%s", (workspace,))
            assert cursor.fetchone()[0] == 0
            cursor.execute("SELECT workspace_site_id FROM privacy.diagnostic WHERE id=%s", (did,))
            assert cursor.fetchone()[0] is None
    finally:
        with psycopg.connect(url) as connection, connection.cursor() as cursor:
            cursor.execute("ALTER TABLE privacy.diagnostic DROP CONSTRAINT IF EXISTS claim_test_reject")


def test_concurrent_claim_only_one_owner(pg_claim):
    url, did, token, owner, other, workspace, foreign, host = pg_claim
    # Both users must be authorized for the same destination to isolate proof ownership.
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute("INSERT INTO access.workspace_members (workspace_id,user_id,role) VALUES (%s,%s,'member')", (workspace, other))
    def attempt(uid):
        try:
            return snapshot.claim_anonymous_diagnostic(did, token, uid, workspace)
        except snapshot.PrivacyDiagnosticClaimRejectedError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, (owner, other)))
    assert sum(value is not None for value in results) == 1

def test_migration_from_previous_schema_preserves_existing_snapshot(pg_claim):
    """Recreate the old schema inside a rolled-back transaction, then migrate twice."""
    url, did, token, owner, other, workspace, foreign, host = pg_claim
    migration_sql = MIGRATION.read_text(encoding="utf-8")
    # The migration runner supplies the transaction boundary in this test.
    migration_sql = migration_sql.removeprefix("BEGIN;").removesuffix("COMMIT;").strip()
    with psycopg.connect(url) as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT diagnostic_snapshot, score, site_url FROM privacy.diagnostic WHERE id=%s", (did,))
                before = cursor.fetchone()
                cursor.execute("ALTER TABLE privacy.diagnostic DROP COLUMN claim_token_hash")
                cursor.execute("ALTER TABLE privacy.diagnostic DROP COLUMN claimed_by_user_id")
                cursor.execute(migration_sql)
                cursor.execute(migration_sql)
                cursor.execute("SELECT diagnostic_snapshot, score, site_url FROM privacy.diagnostic WHERE id=%s", (did,))
                assert cursor.fetchone() == before
                cursor.execute("""
                    SELECT count(*) FROM pg_constraint c
                    JOIN pg_attribute a ON a.attrelid=c.conrelid
                    WHERE c.conrelid='privacy.diagnostic'::regclass
                      AND c.contype='f' AND c.conkey=ARRAY[a.attnum]::smallint[]
                      AND a.attname='claimed_by_user_id'
                """)
                assert cursor.fetchone()[0] == 1
        finally:
            connection.rollback()

