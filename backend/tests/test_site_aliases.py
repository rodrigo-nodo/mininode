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


def test_auto_registration_is_guarded_and_does_not_merge_existing_sites(monkeypatch):
    from mininode_api.services import site_aliases
    from types import SimpleNamespace

    site_id = uuid4()
    class DbCursor:
        def __init__(self, requested=None, counterpart=(site_id, "www.example.com")):
            self.requested = requested
            self.counterpart = counterpart
            self.last = ""
            self.params = None
            self.inserted = []
        def execute(self, sql, params=None):
            self.last, self.params = sql, params
            if "INSERT INTO access.site_aliases" in sql:
                self.inserted.append(params)
        def fetchone(self):
            if "to_regclass" in self.last: return ("access.site_aliases",)
            if "SELECT id FROM access.sites" in self.last: return None
            if "INSERT INTO access.site_aliases" in self.last: return (site_id,)
            return (None,)
    cur = DbCursor()
    def resolve(cursor, host):
        return cur.requested if host == "example.com" else cur.counterpart
    monkeypatch.setattr(site_aliases, "resolve_existing_site", resolve)
    verified = lambda host: SimpleNamespace(
        equivalent=True, requested_hostname=host, counterpart_hostname="www.example.com")
    assert site_aliases.register_verified_www_alias(cur, "example.com", verifier=verified)
    assert len(cur.inserted) == 1 and cur.inserted[0][1:3] == (site_id, "example.com")

    cur2 = DbCursor(requested=(uuid4(), "example.com"))
    cur = cur2
    assert not site_aliases.register_verified_www_alias(cur, "example.com", verifier=verified)
    assert not cur.inserted


def test_auto_registration_rejects_missing_or_invalid_evidence(monkeypatch):
    from mininode_api.services import site_aliases
    from types import SimpleNamespace
    def fake_resolve(_cursor, hostname):
        return None if hostname == "example.com" else (uuid4(), "www.example.com")
    monkeypatch.setattr(site_aliases, "resolve_existing_site", fake_resolve)
    class Cursor:
        def __init__(self, ready=True):
            self.query = ""
            self.ready = ready
        def execute(self, sql, params=None): self.query = sql
        def fetchone(self): return ("access.site_aliases" if self.ready else None,)
    cur = Cursor()
    evidence = lambda host: SimpleNamespace(equivalent=False, requested_hostname=host, counterpart_hostname="www.example.com")
    assert not site_aliases.register_verified_www_alias(cur, "example.com", verifier=evidence)
    assert not site_aliases.register_verified_www_alias(Cursor(False), "example.com", verifier=lambda _: (_ for _ in ()).throw(AssertionError("network")))
    assert not site_aliases.register_verified_www_alias(Cursor(), "shop.example.com", verifier=lambda _: (_ for _ in ()).throw(AssertionError("network")))


def test_both_association_paths_attempt_registration():
    import inspect
    from mininode_api.services import access, privacy_diagnostic_snapshot
    for method in (access.follow_site, privacy_diagnostic_snapshot.claim_anonymous_diagnostic):
        body = inspect.getsource(method)
        assert "register_verified_www_alias(cursor, hostname)" in body
