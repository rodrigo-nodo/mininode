"""PW-03 PROD: authenticated Plan coexists with the old token route."""
from pathlib import Path
from html.parser import HTMLParser

FRONT = Path(__file__).resolve().parents[2]
NEW = FRONT / "privacy" / "mi-plan"
LEGACY = FRONT / "privacy" / "plan"
HTML = (NEW / "index.html").read_text(encoding="utf-8")
APP = (NEW / "app.js").read_text(encoding="utf-8")
ACCESS = (FRONT / "access" / "app.js").read_text(encoding="utf-8")
PROXY = (FRONT / "functions" / "api" / "[[path]].js").read_text(encoding="utf-8")


def test_entitled_plan_has_three_tabs_and_private_api_contract():
    for key, label in (("state", "Estado de mi sitio"), ("actions", "Qué debo mejorar"),
                       ("progress", "Mis avances")):
        assert f'id="plan-tab-{key}"' in HTML
        assert f'id="plan-panel-{key}"' in HTML
        assert label in HTML
    assert "setPlanTab('state')" in APP
    assert "/api/privacy/workspace-sites/" in APP
    assert "/plan/check" in APP
    assert "window.MininodeAuth" in APP
    assert "getToken()" in APP
    assert "new URLSearchParams(window.location.search)" in APP


def test_shell_styles_and_private_cache_are_complete():
    assert 'data-include="../../partials/header-nav.html"' in HTML
    assert (FRONT / "partials" / "header-nav.html").is_file()
    assert '/include.js?v=pw03-prod3-1' in HTML
    for file in ("app.js", "base.css", "layout.css", "tabs.css"):
        assert (NEW / file).is_file()
        assert f"/privacy/mi-plan/{file}?v=pw03-prod3-1" in HTML
    assert (FRONT / "privacy" / "control-ux.js").is_file()
    headers = (FRONT / "_headers").read_text(encoding="utf-8")
    assert "/privacy/mi-plan/\n  Cache-Control: no-cache, must-revalidate" in headers
    assert "/privacy/mi-plan/*\n  Cache-Control: no-cache, must-revalidate" in headers


def test_legacy_token_plan_remains_served_until_pr4():
    old_html = (LEGACY / "index.html").read_text(encoding="utf-8")
    old_app = (FRONT / "privacy" / "plan-assets" / "app.js").read_text(encoding="utf-8")
    redirects = (FRONT / "_redirects").read_text(encoding="utf-8")
    assert "/privacy/plan/:token /privacy/plan/ 200" in redirects
    assert "accessTokenFromPath" in old_app
    assert "/api/privacy/correction-plans/" in old_app
    assert 'src="/privacy/plan-assets/app.js?v=7"' in old_html
    assert "isAllowedCorrectionPlan" in PROXY
    assert "isPublicOrderCreation" in PROXY


def test_account_entitlement_check_never_grants_cross_workspace_links():
    assert "/api/billing/workspaces/" in ACCESS
    assert "/entitlements" in ACCESS
    assert "/privacy/mi-plan/?workspace_site_id=" in ACCESS
    assert "if (!entitledIds.has(site.id)) continue;" in ACCESS
    assert "requestId !== latestReviewsRequestId" in ACCESS
    assert "Array.isArray(rights?.active_site_ids)" in ACCESS


def test_new_plan_does_not_use_commercial_tokens_or_checkout():
    assert "/api/privacy/correction-plans/" not in APP
    assert "/api/privacy/correction-plan-orders" not in APP
    assert "localStorage.setItem" not in APP
    assert "checkout" not in APP.lower()


class _PlanMarkup(HTMLParser):
    """Collect real HTML ancestors; JS DOM tests alone don't model containment."""

    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self.stack = []
        self.ancestors = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        node = (tag, attrs.get("id"), set(attrs.get("class", "").split()))
        if node[1]:
            self.ancestors[node[1]] = tuple(self.stack)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        # Fail on accidental mismatched close tags in the Plan's HTML.
        assert self.stack and self.stack[-1][0] == tag, f"Unexpected closing </{tag}>"
        self.stack.pop()


def test_first_review_action_is_outside_hidden_comparison_detail():
    markup = _PlanMarkup()
    markup.feed(HTML)
    assert not markup.stack
    button_parents = markup.ancestors["check-start"]
    assert any(node_id == "plan-panel-progress" for _, node_id, _ in button_parents)
    assert any("plan-progress-review" in classes for _, _, classes in button_parents)
    assert all(node_id != "improvement-check" for _, node_id, _ in button_parents)
    assert any(node_id == "check-available" for _, node_id, _ in button_parents)
    detail_parents = markup.ancestors["check-result"]
    assert any(node_id == "improvement-check" for _, node_id, _ in detail_parents)
    assert all("plan-progress-review" not in classes for _, _, classes in detail_parents)
