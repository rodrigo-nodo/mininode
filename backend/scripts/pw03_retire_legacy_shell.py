"""Manual, fail-closed PW-03 legacy retirement from the PROD Render Shell.

This module is NOT imported by the app and is NEVER a Render Pre-deploy step.
Its only destructive entry point requires --execute, an interactive terminal,
an explicit operator confirmation and separate PO authorization.
No authorization fingerprint is calculated or sent to PostgreSQL.
"""
from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path
import re
import sys
import warnings

import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_SQL = ROOT / "operations" / "pw03_pr5_readonly_preflight.sql"
RETIREMENT_SQL = ROOT / "operations" / "pw03_pr5_retire_legacy_commerce.sql"

EXPECTED_SERVICE_ID = "srv-d3p5n1je5dus738gi5mg"
EXPECTED_POSTGRES_ID = "dpg-da5fjmbm8hqs73chdceg-a"
# Exact private endpoint expected from Render Internal Database URL. No
# prefix matching, alternate domains, external endpoints or IP overrides.
# If Render changes this hostname, stop and re-review the endpoint in a PR.
EXPECTED_INTERNAL_HOST = "dpg-da5fjmbm8hqs73chdceg-a"
ALLOWED_CONNINFO = frozenset({
    "host", "port", "dbname", "user", "password", "sslmode",
})
EXPECTED_DATABASE = "mininode"
EXPECTED_DB_USER = "mininode_user"
DELETE_ACK = "DELETE_2_PAID_1_PENDING_LEGACY_ORDERS"
EXPLICIT_APPROVAL = "ELIMINAR_3_TABLAS_LEGACY_PROD_SIN_RESPALDO"
HEX40 = re.compile(r"^[0-9a-f]{40}$")

# The Render human-readable service name is not an immutable identity:
# production is pinned by RENDER_SERVICE_ID plus repo, branch, type,
# public hostname and deployed SHA. Do not fail on RENDER_SERVICE_NAME.
EXPECTED_RENDER = {
    "RENDER": "true",
    "RENDER_SERVICE_ID": EXPECTED_SERVICE_ID,
    "RENDER_SERVICE_TYPE": "web",
    "RENDER_GIT_BRANCH": "main",
    "RENDER_GIT_REPO_SLUG": "rodrigo-nodo/mininode",
    "RENDER_EXTERNAL_HOSTNAME": "mininode-ocz1.onrender.com",
    "IS_PULL_REQUEST": "false",
}
OLD_TABLES = (
    "privacy.correction_plan",
    "privacy.correction_plan_order",
    "privacy.correction_plan_check",
)
PRESERVED_TABLES = (
    "privacy.diagnostic",
    "privacy.entitled_plan",
    "privacy.entitled_plan_check",
    "access.entitlements",
    "billing.orders",
)


class GuardError(Exception):
    """A deliberate fail-closed refusal; do not expose credentials or hashes."""


def validate_render_env(env: dict[str, str]) -> str:
    for name, value in EXPECTED_RENDER.items():
        if env.get(name) != value:
            raise GuardError("Entorno Render PROD no coincide: " + name)
    deployed_sha = env.get("RENDER_GIT_COMMIT", "")
    if not HEX40.fullmatch(deployed_sha):
        raise GuardError("No se pudo identificar el commit desplegado en Render")
    return deployed_sha


def validate_database_url(url: str, env: dict[str, str]) -> None:
    """Reject every libpq routing override before opening any DB connection.

    The exact internal hostname is pinned independently of the resource ID
    entered interactively. A matching DB name alone is not sufficient.
    No client defaults, connection services, IP routing, multi-host failover,
    Unix socket paths, alternate ports or unexpected URI options are allowed.
    """
    if not url or not url.startswith(("postgresql://", "postgres://")):
        raise GuardError("DATABASE_URL interno no disponible o no es URL PostgreSQL")
    # libpq reads PGHOSTADDR even when host was set explicitly in the URI.
    # Reject all PG* environment variables, not just known routing flags:
    # future libpq versions may introduce additional connection overrides.
    if any(name.startswith("PG") and value for name, value in env.items()):
        raise GuardError("Variables PG* de libpq no permitidas en esta operación")
    try:
        info = conninfo_to_dict(url)
    except Exception as exc:
        raise GuardError("DATABASE_URL tiene formato no válido") from exc
    if set(info) - ALLOWED_CONNINFO:
        raise GuardError("DATABASE_URL contiene parámetros libpq no autorizados")
    if info.get("dbname") != EXPECTED_DATABASE or info.get("user") != EXPECTED_DB_USER:
        raise GuardError("Base o usuario PostgreSQL no coinciden con PROD")
    if not info.get("password"):
        raise GuardError("DATABASE_URL debe incluir la contraseña administrada por Render")
    if info.get("host") != EXPECTED_INTERNAL_HOST:
        raise GuardError("Host PostgreSQL interno completo no coincide con Render")
    if info.get("port", "5432") != "5432":
        raise GuardError("Puerto PostgreSQL no autorizado")
    if info.get("sslmode") not in (None, "require"):
        raise GuardError("Modo TLS PostgreSQL no autorizado")


def _require_interactive_tty() -> None:
    if not (sys.stdin.isatty() and sys.stderr.isatty()):
        raise GuardError("La ejecución destructiva requiere una terminal interactiva")


def _hidden_input(prompt: str) -> str:
    # Do not display an explicit destructive confirmation in the terminal.
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        return getpass.getpass(prompt).strip()


def confirm_destructive_approval(deployed_sha: str) -> None:
    """Requires prior explicit authorization from the PO, outside this tool."""
    print("REQUIERE autorización destructiva específica previa, fuera de esta consola.")
    render_id = input("postgresId Render primario aprobado: ").strip()
    approved_sha = input("SHA completo del backend LIVE aprobado: ").strip()
    if render_id != EXPECTED_POSTGRES_ID or approved_sha != deployed_sha:
        raise GuardError("Identidad del recurso/commit no coincide con la aprobación")
    phrase = _hidden_input("Autorización destructiva específica (oculta): ")
    if phrase != EXPLICIT_APPROVAL:
        raise GuardError("Falta la autorización destructiva específica")


def _validate_connected_database(conn: psycopg.Connection) -> None:
    row = conn.execute("""
        SELECT current_database() AS db, current_user AS db_user,
               pg_is_in_recovery() AS is_replica
    """).fetchone()
    if (not row or row["db"] != EXPECTED_DATABASE
            or row["db_user"] != EXPECTED_DB_USER or row["is_replica"]):
        raise GuardError("La sesión no corresponde a la base/rol primario autorizado")


def inspect_inventory(conn: psycopg.Connection) -> dict[str, int]:
    """Read current structural inventory; never print IDs or personal data."""
    _validate_connected_database(conn)
    with conn.cursor() as cur:
        cur.execute(PREFLIGHT_SQL.read_text(encoding="utf-8"))
        row = cur.fetchone()
    if (not row or row["plans_manifest"] is None
            or row["orders_manifest"] is None
            or row["checks_manifest"] is None):
        raise GuardError("Preflight incompleto; abortar")
    # The shape/status checks are intentional: they do NOT protect against
    # row content changes that preserve all counts and relationships.
    plans, orders, checks = (
        row["plans_manifest"], row["orders_manifest"], row["checks_manifest"],
    )
    if len(plans) != 2 or any(p["status"] != "active" for p in plans):
        raise GuardError("Preflight: inventario de planes inesperado")
    plan_ids = {p["id"] for p in plans}
    if len(plan_ids) != 2 or len(orders) != 3 or len(checks) != 1:
        raise GuardError("Preflight: recuentos o IDs inesperados")
    paid = [o for o in orders if o["status"] == "paid"]
    pending = [o for o in orders if o["status"] == "pending_payment"]
    if (len(paid) != 2 or len(pending) != 1
            or len({o["id"] for o in orders}) != 3
            or any(
                not o["paid_at_present"]
                or o["correction_plan_id"] not in plan_ids
                or not o["diagnostic_id"]
                for o in paid
            )
            or any(
                o["paid_at_present"] or o["correction_plan_id"] is not None
                or not o["diagnostic_id"]
                for o in pending
            )):
        raise GuardError("Preflight: órdenes antiguas no coinciden")
    check = checks[0]
    paid_by_id = {o["id"]: o for o in paid}
    if (len({o["correction_plan_id"] for o in paid}) != 2
            or not check["id"] or check["order_id"] not in paid_by_id
            or check["correction_plan_id"] !=
                paid_by_id[check["order_id"]]["correction_plan_id"]
            or not check["original_diagnostic_id"]
            or not check["check_diagnostic_id"]):
        raise GuardError("Preflight: revisión antigua inconsistente")
    return {
        "planes_antiguos": len(plans),
        "ordenes_antiguas": len(orders),
        "revisiones_antiguas": len(checks),
    }


def check_only(conn: psycopg.Connection) -> dict[str, int]:
    """Read-only mode: no DDL and no authorization payloads."""
    conn.execute("SET default_transaction_read_only = on")
    return inspect_inventory(conn)


def execute_retirement(conn: psycopg.Connection) -> None:
    """Run guarded, atomic legacy retirement only after manual confirmation.

    The reviewed SQL owns BEGIN/COMMIT, short locks, live inventory checks
    and the three exact DROP RESTRICT statements. Post-commit errors require
    independent read-only investigation; never retry automatically.
    """
    if not conn.autocommit:
        raise GuardError("Se requiere conexión autocommit para la transacción SQL manual")
    _validate_connected_database(conn)
    # Only public target/acknowledgement constants are bound to PostgreSQL.
    # No private SHA-256 fingerprint or customer data is transmitted.
    for name, value in (
        ("mininode.pw03_pr5_target_database", EXPECTED_DATABASE),
        ("mininode.pw03_pr5_target_user", EXPECTED_DB_USER),
        ("mininode.pw03_pr5_ack", DELETE_ACK),
    ):
        conn.execute("SELECT set_config(%s, %s, false)", (name, value))
    try:
        conn.execute(RETIREMENT_SQL.read_text(encoding="utf-8"))
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except psycopg.Error:
            pass
        raise

    for table in OLD_TABLES:
        if conn.execute("SELECT to_regclass(%s) AS target", (table,)).fetchone()["target"] is not None:
            raise GuardError("POST-COMMIT: aún existe una tabla antigua; investigar")
    for table in PRESERVED_TABLES:
        if conn.execute("SELECT to_regclass(%s) AS target", (table,)).fetchone()["target"] is None:
            raise GuardError("POST-COMMIT: falta una tabla protegida; investigar")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PW-03 Render Shell — operación manual")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true", help="Inspección segura; solo SELECT")
    modes.add_argument("--execute", action="store_true", help="Borrado irreversible, con autorización")
    args = parser.parse_args(argv)
    if not (args.check or args.execute):
        parser.print_usage()
        print("Sin operación. Usar --check; --execute requiere autorización separada.")
        return 0
    try:
        env = dict(os.environ)
        sha = validate_render_env(env)
        validate_database_url(env.get("DATABASE_URL", ""), env)
        if args.execute:
            _require_interactive_tty()
        # One exact internal connection. No environment or migration changes.
        with psycopg.connect(
            env["DATABASE_URL"], autocommit=True, row_factory=dict_row,
            connect_timeout=10,
        ) as conn:
            if args.check:
                summary = check_only(conn)
                print("PASS: lectura e inventario estructural esperado; no es autorización para borrar. " + sha[:12])
                print(" / ".join(f"{key}={value}" for key, value in summary.items()))
            else:
                summary = inspect_inventory(conn)
                print("Inventario previo verificado: " +
                      " / ".join(f"{key}={value}" for key, value in summary.items()))
                confirm_destructive_approval(sha)
                execute_retirement(conn)
                print("PASS: retiro manual confirmado; 3 tablas antiguas ausentes")
        return 0
    except (GuardError, psycopg.Error, OSError, EOFError, KeyboardInterrupt,
            getpass.GetPassWarning):
        # Do not leak DSNs, hashes or data in exception diagnostics.
        print(
            "FAIL: operación no confirmada. No reintentar automáticamente; "
            "revisar conector PostgreSQL de solo lectura y estado de transacción.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
