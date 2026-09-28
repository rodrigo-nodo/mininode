import importlib.util
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
SCRIPT = BACKEND / "scripts" / "run_migration.py"
SPEC = importlib.util.spec_from_file_location("run_migration", SCRIPT)
run_migration = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(run_migration)


def test_resolve_migration_accepts_approved_directory_file():
    path = run_migration.resolve_migration(
        str(BACKEND / "migrations" / "20260928_access_a2_1_workspace_sites.sql")
    )
    assert path.parent == (BACKEND / "migrations").resolve()


@pytest.mark.parametrize(
    "path",
    [
        "README.md",
        "../outside.sql",
        "migrations/not-sql.txt",
        "migrations/nested/file.sql",
    ],
)
def test_resolve_migration_rejects_non_migration_paths(path):
    with pytest.raises((ValueError, FileNotFoundError)):
        run_migration.resolve_migration(path)
