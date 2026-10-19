"""Logical site alias resolution without network requests or implicit claims."""
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import pytest

from mininode_api.services import site_aliases

SQL = (Path(__file__).resolve().parents[1] / "migrations" /
       "20261019_access_site_aliases.sql").read_text(encoding="utf-8")


def test_additive_schema_contract():
    assert "CREATE TABLE IF NOT EXISTS access.site_aliases" in SQL
    assert "REFERENCES access.sites(id) ON DELETE RESTRICT" in SQL
    assert "hostname TEXT NOT NULL UNIQUE" in SQL
    assert "verification_status = 'verified'" in SQL
    assert "stable_redirect" in SQL and "reviewed_evidence" in SQL
    assert "DROP TABLE" not in SQL and "DELETE FROM" not in SQL


class Cursor:
    def __init__(self, rows, *, aliases_ready=True):
        self.rows = rows
        self.aliases_ready = aliases_ready
        self.last_sql = ""
        self.statements = []

    def execute(self, sql, params=None):
        self.last_sql = sql
        self.statements.append((sql, params))
        if params:
            assert params == ("www.example.com", "www.example.com") or params == ("www.example.com",)

    def fetchone(self):
        return ("access.site_aliases" if self.aliases_ready else None,)

    def fetchall(self):
        return self.rows


@pytest.mark.parametrize("aliases_ready, rows", [
    (True, []),
    (True, [(uuid4(), "example.com")]),
    (False, [(uuid4(), "www.example.com")]),
    (False, []),
])
def test_lookup_uses_verified_aliases_only_if_schema_ready(monkeypatch, aliases_ready, rows):
    cursor = Cursor(rows, aliases_ready=aliases_ready)

    @contextmanager
    def connection():
        class Connection:
            def cursor(self):
                @contextmanager
                def context():
                    yield cursor
                return context()
        yield Connection()

    monkeypatch.setattr(site_aliases.access, "_connection", connection)
    result = site_aliases.resolve_site_id("https://WWW.Example.com/")
    assert result == (rows[0][0] if rows else None)
    assert "to_regclass" in cursor.statements[0][0]
    lookup_sql = cursor.statements[1][0]
    assert ("access.site_aliases" in lookup_sql) is aliases_ready
    if aliases_ready:
        assert "verification_status = 'verified'" in lookup_sql


def test_conflicting_primary_and_alias_fail_closed():
    cursor = Cursor([(uuid4(), "example.com"), (uuid4(), "different.example")])
    with pytest.raises(ValueError, match="conflicting"):
        site_aliases.resolve_existing_site(cursor, "www.example.com")


def test_non_public_hostname_rejected_before_db(monkeypatch):
    def unexpected():
        raise AssertionError("database should not be opened")
    monkeypatch.setattr(site_aliases.access, "_connection", unexpected)
    with pytest.raises(ValueError):
        site_aliases.resolve_site_id("http://localhost")


def test_all_association_entrypoints_use_same_resolver():
    from mininode_api.services import access, privacy_diagnostic_snapshot
    import inspect

    assert "resolve_existing_site(cursor, hostname)" in inspect.getsource(access.follow_site)
    assert "resolve_existing_site(cursor, hostname)" in inspect.getsource(
        privacy_diagnostic_snapshot.claim_anonymous_diagnostic
    )
