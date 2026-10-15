"""Fail-closed, allowlisted Render pre-deploy PostgreSQL migrator.

No allowlist => no database connection or DDL. Explicit approvals are scoped
to one Render service through its MIGRATION_APPROVED_FILES environment variable.
Existing historical migrations must not be enrolled without verifying DB state.
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import psycopg

MIGRATIONS_DIR = (Path(__file__).resolve().parents[1] / "migrations").resolve()
NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_\-]*\.sql$")
# Each PostgreSQL transaction holds this advisory lock until commit/rollback.
LOCK_ID = 741981024234
# These files predate the versioned runner and must never run via Pre-deploy.
# In particular A2.1 contains DROP TABLE; existing database state is unknown.
BLOCKED_LEGACY = frozenset({
    "20260928_access_a2_1_workspace_sites.sql",
    "20260928_access_a3_2_privacy_workspace_site.sql",
    "20261006_a4_billing_core.sql",
})
# Reviewed content only; new migrations require an explicit code-reviewed catalog change.
APPROVED_CHECKSUMS = {
    "20261013_privacy_anonymous_claim.sql": "16fc03e290c6b7812d30b8965aa491f25d8e8ea988f1be2932ed83e7b574b544",
    "20261015_privacy_workspace_site_fk_dedup.sql": "695f22d5bfb1a5f9c8164e17240859bb0504d0b6f1bb222f737d4b99a354594f",
}

def parse_approved(raw: str) -> list[str]:
    if not raw.strip():
        return []
    names = [name.strip() for name in raw.split(",")]
    if not all(NAME.fullmatch(n) for n in names) or len(set(names)) != len(names):
        raise ValueError("MIGRATION_APPROVED_FILES requires unique flat .sql filenames")
    if names != sorted(names):
        raise ValueError("MIGRATION_APPROVED_FILES must be sorted")
    return names

def load_sql(name: str) -> tuple[str, str]:
    if name in BLOCKED_LEGACY:
        raise ValueError(f"Legacy migration blocked from Pre-deploy: {name}")
    expected = APPROVED_CHECKSUMS.get(name)
    if expected is None:
        raise ValueError(f"Migration not in reviewed catalog: {name}")
    path = (MIGRATIONS_DIR / name).resolve()
    if path.parent != MIGRATIONS_DIR or not path.is_file():
        raise ValueError(f"Migration file not found in migrations directory: {name}")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    sql = raw.decode("utf-8-sig")
    # Existing checked-in migrations wrap their contents in BEGIN/COMMIT.
    # Remove only standalone outer transaction lines, never arbitrary SQL.
    lines = sql.splitlines()
    active = [(i, line.strip().upper()) for i, line in enumerate(lines)
              if line.strip() and not line.lstrip().startswith("--")]
    if active and active[0][1] == "BEGIN;" and active[-1][1] == "COMMIT;":
        lines[active[0][0]] = ""
        lines[active[-1][0]] = ""
        sql = "\n".join(lines)
    elif any(line.strip().upper() in ("BEGIN;", "COMMIT;", "ROLLBACK;") for line in lines):
        raise ValueError(f"Unsafe transaction delimiters in {name}")
    if digest != expected:
        raise ValueError(f"Migration catalog checksum mismatch: {name}")
    return sql, digest

def migrate(database_url: str, names: list[str]) -> None:
    # Validate *all* files before opening a database connection.
    migrations = [(n, *load_sql(n)) for n in names]
    with psycopg.connect(database_url, autocommit=True) as conn:
        # One transaction per migration. Lock also serializes the history check.
        for name, sql, checksum in migrations:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_ID,))
                    cur.execute("""CREATE TABLE IF NOT EXISTS public.schema_migrations (
                        filename TEXT PRIMARY KEY,
                        checksum_sha256 CHAR(64) NOT NULL,
                        applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )""")
                    cur.execute("SELECT checksum_sha256 FROM public.schema_migrations WHERE filename = %s", (name,))
                    row = cur.fetchone()
                    if row:
                        if row[0] != checksum:
                            raise RuntimeError(f"Migration checksum changed: {name}")
                        print(f"Already applied: {name}")
                        continue
                    cur.execute(sql)
                    cur.execute("INSERT INTO public.schema_migrations (filename, checksum_sha256) VALUES (%s, %s)", (name, checksum))
                    print(f"Applied: {name}")

def main() -> int:
    names = parse_approved(os.getenv("MIGRATION_APPROVED_FILES", ""))
    if not names:
        print("No migrations approved for this environment; skip")
        return 0
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required when migrations are approved")
    migrate(url, names)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
