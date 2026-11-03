"""Manual, fail-closed PW-03 legacy retirement from the PROD Render Shell.

This module is NOT imported by the app and is NEVER a Render Pre-deploy step.
Its only destructive entry point requires --execute, an interactive terminal,
independently approved fingerprints and a separate operator authorization.
No CLI argument, environment variable or log contains the approval fingerprints.
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
HEX64 = re.compile(r"^[0-9a-f]{64}$")

EXPECTED_RENDER = {
    "RENDER": "true",
    "RENDER_SERVICE_ID": EXPECTED_SERVICE_ID,
    "RENDER_SERVICE_NAME": "mininode-backend-prod",
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

    The exact internal hostname is pinned independently of the resource-ID
    prompt and the SQL cluster/row fingerprints; none is sufficient alone.
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
    # Never fall back to echoing authorization fingerprints in the terminal.
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        return getpass.getpass(prompt).strip()


def read_approved_values(deployed_sha: str) -> tuple[str, str]:
    """Read a prior external approval; never derive it from this connection."""
    print("REQUIERE autorización destructiva específica previa, fuera de esta consola.")
    render_id = input("postgresId Render primario aprobado: ").strip()
    approved_sha = input("SHA completo del backend LIVE aprobado: ").strip()
    if render_id != EXPECTED_POSTGRES_ID or approved_sha != deployed_sha:
        raise GuardError("Identidad del recurso/commit no coincide con la aprobación")
    cluster = _hidden_input("Huella SHA-256 de clúster aprobada (oculta): ")
    inventory = _hidden_input("Huella SHA-256 de filas aprobada (oculta): ")
    if not HEX64.fullmatch(cluster) or not HEX64.fullmatch(inventory):
        raise GuardError("Faltan huellas SHA-256 aprobadas válidas")
    phrase = _hidden_input("Autorización destructiva específica (oculta): ")
    if phrase != EXPLICIT_APPROVAL:
        raise GuardError("Falta la autorización destructiva específica")
    return cluster, inventory


def _validate_connected_database(conn: psycopg.Connection) -> None:
    row = conn.execute("SELECT current_database() AS db, current_user AS db_user").fetchone()
    if row["db"] != EXPECTED_DATABASE or row["db_user"] != EXPECTED_DB_USER:
        raise GuardError("La sesión no corresponde a la base/rol autorizado")


def check_only(conn: psycopg.Connection) -> dict[str, int]:
    """Read-only summary; no IDs, email addresses or fingerprints in output."""
    conn.execute("SET default_transaction_read_only = on")
    _validate_connected_database(conn)
    with conn.cursor() as cur:
        cur.execute(PREFLIGHT_SQL.read_text(encoding="utf-8"))
        row = cur.fetchone()
    if (not row or not row["cluster_fingerprint_sha256"]
            or not row["legacy_inventory_sha256"]):
        raise GuardError("Preflight incompleto; abortar")
    # This is an expected-structure check, NOT independent approval of the
    # full row fingerprint or evidence of rights/payouts.
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
    if (not check["id"] or check["order_id"] not in {o["id"] for o in paid}
            or check["correction_plan_id"] not in plan_ids
            or not check["original_diagnostic_id"]
            or not check["check_diagnostic_id"]):
        raise GuardError("Preflight: revisión antigua inconsistente")
    return {
        "planes_antiguos": len(plans),
        "ordenes_antiguas": len(orders),
        "revisiones_antiguas": len(checks),
    }


def execute_retirement(conn: psycopg.Connection, cluster: str, inventory: str) -> None:
    """Execute the exact reviewed SQL once, in the same validated DB session.

    The SQL file owns BEGIN / COMMIT and ACCESS EXCLUSIVE NOWAIT. An exception
    aborts before COMMIT; an error during verification AFTER COMMIT must be
    investigated, not blindly retried.
    """
    if not HEX64.fullmatch(cluster) or not HEX64.fullmatch(inventory):
        raise GuardError("Huella aprobada inválida")
    if not conn.autocommit:
        raise GuardError("Se requiere conexión autocommit para la transacción SQL manual")
    _validate_connected_database(conn)
    for name, value in (
        ("mininode.pw03_pr5_target_database", EXPECTED_DATABASE),
        ("mininode.pw03_pr5_target_cluster_sha256", cluster),
        ("mininode.pw03_pr5_approved_inventory_sha256", inventory),
        ("mininode.pw03_pr5_ack", DELETE_ACK),
    ):
        conn.execute("SELECT set_config(%s, %s, false)", (name, value))
    try:
        # No server-side bindings: psycopg sends multiple statements from
        # the reviewed SQL file in one command on the SAME connection.
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
        approved = None
        if args.execute:
            _require_interactive_tty()
            approved = read_approved_values(sha)
        # One connection; no modification to the Render environment or
        # migration catalog. The connection string is NEVER printed.
        with psycopg.connect(
            env["DATABASE_URL"], autocommit=True, row_factory=dict_row,
            connect_timeout=10,
        ) as conn:
            if args.check:
                summary = check_only(conn)
                print("PASS: lectura e inventario estructural esperado; no es autorización para borrar. " + sha[:12])
                print(" / ".join(f"{key}={value}" for key, value in summary.items()))
            else:
                execute_retirement(conn, *approved)
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
