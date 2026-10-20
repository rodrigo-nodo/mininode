"""Operator-only apex/www reconciliation. Dry-run unless explicitly confirmed.

Examples:
  python scripts/reconcile_existing_www.py --workspace-id UUID --primary gurbana.cl --alias www.gurbana.cl
  python scripts/reconcile_existing_www.py --workspace-id UUID --primary gurbana.cl --alias www.gurbana.cl \
    --apply --confirm 'UUID:gurbana.cl:www.gurbana.cl'

Never expose this script as a public endpoint. Only disposable test or DEV DB.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from uuid import UUID

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mininode_api.services.site_reconciliation import reconcile_existing_www  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run by default; no automatic site merges.")
    parser.add_argument("--workspace-id", type=UUID, required=True)
    parser.add_argument("--primary", required=True)
    parser.add_argument("--alias", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        parser.error("DATABASE_URL must be configured")
    # Prevent accidental execution on production or a newly pointed database.
    with psycopg.connect(db_url) as conn:
        db_name = conn.info.dbname
    if db_name not in ("mininode_db_dev", "mininode_test"):
        parser.error("Refusing to access non-DEV/non-test PostgreSQL database")
    if args.apply and args.confirm != f"{args.workspace_id}:{args.primary}:{args.alias}":
        parser.error("Apply requires --confirm WORKSPACE_UUID:PRIMARY:ALIAS (exact match)")

    result = reconcile_existing_www(
        args.workspace_id, args.primary, args.alias, apply=args.apply,
    )
    print(json.dumps({
        "status": result.status,
        "workspace_id": str(result.workspace_id),
        "primary_site_id": str(result.primary_site_id),
        "source_site_id": str(result.source_site_id),
        "primary_workspace_site_id": str(result.primary_workspace_site_id),
        "source_workspace_site_id": str(result.source_workspace_site_id),
        "diagnostics": result.diagnostics,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
