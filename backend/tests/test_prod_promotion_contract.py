"""Prevent accidental production payment-provider activation in DEV promotion."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "src" / "mininode_api" / "api" / "billing.py"
OPERATOR = ROOT / "src" / "mininode_api" / "services" / "site_group_operator.py"


def test_prod_promotion_keeps_live_mercadopago_endpoints_out_of_scope():
    src = API.read_text(encoding="utf-8")
    assert '"/orders/{order_id}/checkout"' not in src
    assert '"/webhooks/mercadopago"' not in src
    assert "mercadopago.create_checkout" not in src
    assert "mercadopago.process_order_notification" not in src


def test_operator_fallback_points_at_production_admin():
    src = OPERATOR.read_text(encoding="utf-8")
    assert "https://mininode.io/admin/" in src
    assert "https://dev.mininode.io/operator/site-reviews/" not in src


def test_prod_promotion_preserves_old_paths_until_explicit_retirement():
    from mininode_api.main import create_app
    app = create_app()
    routes = {(method, route.path) for route in app.routes
              for method in (getattr(route, "methods", set()) or set())}
    assert ("POST", "/privacy/correction-plan-orders") in routes
    assert ("GET", "/privacy/workspace-sites/{workspace_site_id}/plan") in routes
    assert ("POST", "/privacy/workspace-sites/{workspace_site_id}/plan") in routes
    assert ("POST", "/privacy/workspace-sites/{workspace_site_id}/plan/check") in routes
    assert ("POST", "/privacy/workspace-sites/{workspace_site_id}/prepare-activation") in routes
    assert ("GET", "/billing/workspaces/{workspace_id}/entitlements") in routes
    assert not any("webhooks/mercadopago" in route.path for route in app.routes)
