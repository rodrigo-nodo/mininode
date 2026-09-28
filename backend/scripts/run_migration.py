"""Explicit database migration runner.

Usage:
    python scripts/run_migration.py migrations/<approved-file>.sql

The runner never discovers or applies migrations automatically. It accepts only
a file inside backend/migrations, executes it as one transaction/script through
DATABASE_URL, and logs only the migration filename (never credentials).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg

MIGRATIONS_DIR = (Path(__file__).resolve().parents[1] / "migrations").resolve()


def resolve_migration(argument: str) -> Path:
    requested = (Path.cwd() / argument).resolve()
    if requested.parent != MIGRATIONS_DIR or requested.suffix != ".sql":
        raise ValueError("migration must be a .sql file directly inside backend/migrations")
    if not requested.is_file():
        raise FileNotFoundError(f"migration not found: {requested.name}")
    return requested


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/run_migration.py migrations/<approved-file>.sql", file=sys.stderr)
        return 2

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not configured", file=sys.stderr)
        return 2

    try:
        migration = resolve_migration(sys.argv[1])
    except (ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Applying migration: {migration.name}")
    sql = migration.read_text(encoding="utf-8")
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(sql)
    print(f"Migration applied: {migration.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
