"""Foundational contract for logical-site aliases; no external fetch or payment."""
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
    assert "UPDATE access.sites" not in SQL


@pytest.mark.parametrize("matches, expected", [
    ([], None),
    ([uuid4()], "one"),
])
def test_resolve_existing_site(monkeypatch, matches, expected):
    class Cursor:
        def execute(self, sql, params):
            assert "access.sites" in sql and "access.site_aliases" in sql
            assert params == ("www.example.com", "www.example.com")
        def fetchall(self):
            return [(m,) for m in matches]
    @contextmanager
    def connection():
        class Connection:
            def cursor(self):
                @contextmanager
                def context():
                    yield Cursor()
                return context()
        yield Connection()
    monkeypatch.setattr(site_aliases.access, "_connection", connection)
    result = site_aliases.resolve_site_id("https://WWW.Example.com/")
    assert result == (matches[0] if expected else None)


def test_conflicting_primary_and_alias_fail_closed(monkeypatch):
    class Cursor:
        def execute(self, sql, params):
            pass
        def fetchall(self):
            return [(uuid4(),), (uuid4(),)]
    @contextmanager
    def connection():
        class Connection:
            def cursor(self):
                @contextmanager
                def context():
                    yield Cursor()
                return context()
        yield Connection()
    monkeypatch.setattr(site_aliases.access, "_connection", connection)
    with pytest.raises(ValueError, match="conflicting"):
        site_aliases.resolve_site_id("example.com")


def test_non_public_hostname_rejected_before_db(monkeypatch):
    def unexpected():
        raise AssertionError("database should not be opened")
    monkeypatch.setattr(site_aliases.access, "_connection", unexpected)
    with pytest.raises(ValueError):
        site_aliases.resolve_site_id("http://localhost")
