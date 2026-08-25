import unittest
from pathlib import Path


PLAN_DIR = Path(__file__).parent
FRONTEND_DIR = PLAN_DIR.parents[1]
HTML = (PLAN_DIR / "index.html").read_text(encoding="utf-8")
APP = (PLAN_DIR / "app.js").read_text(encoding="utf-8")
ROUTE = (FRONTEND_DIR / "functions/privacy/plan/[[token]].js").read_text(encoding="utf-8")
PROXY = (FRONTEND_DIR / "functions/api/[[path]].js").read_text(encoding="utf-8")


class RealCorrectionPlanStaticTests(unittest.TestCase):
    def test_clean_dynamic_route_serves_real_page(self):
        self.assertIn("[[token]].js", str(FRONTEND_DIR / "functions/privacy/plan/[[token]].js"))
        self.assertIn("/privacy/plan/index.html", ROUTE)
        self.assertIn("window.location.pathname", APP)
        self.assertIn(r"^\/privacy\/plan\/([^/]+)\/?$", APP)
        self.assertNotIn("searchParams", APP)

    def test_get_uses_same_origin_proxy_without_api_credentials(self):
        self.assertIn("`/api/privacy/correction-plans/${encodeURIComponent(token)}`", APP)
        self.assertIn("method: 'GET'", APP)
        self.assertNotIn("X-Api-Key", APP)
        self.assertNotIn("api.mininode.io", APP)
        self.assertIn("isAllowedCorrectionPlan", PROXY)
        self.assertIn("if (!isAllowedCorrectionPlan) headers.set('X-Api-Key'", PROXY)

    def test_token_and_snapshot_are_not_persisted_or_logged(self):
        combined = HTML + APP + ROUTE
        for forbidden in ("localStorage", "sessionStorage", "document.cookie", "console.", "analytics"):
            self.assertNotIn(forbidden, combined)

    def test_snapshot_contract_is_validated_before_render(self):
        for field in ("version", "actions_version", "initial_score", "item_count", "items"):
            self.assertIn(field, APP)
        for field in ("control_code", "name", "priority", "finding", "recommendation", "action_steps", "validation_step"):
            self.assertIn(field, APP)
        self.assertIn("plan.item_count !== plan.items.length", APP)
        self.assertLess(APP.index("validPlanResponse(data)"), APP.index("render(data)"))

    def test_snapshot_values_and_every_item_render_in_stored_order(self):
        self.assertIn("friendlySite(siteUrl)", APP)
        self.assertIn("plan.initial_score", APP)
        self.assertIn("plan.item_count", APP)
        self.assertIn("plan.items.forEach(renderItem)", APP)
        self.assertNotIn(".sort(", APP)
        self.assertNotIn("/privacy/diagnose", APP)
        self.assertIn("plan.items.reduce", APP)
        self.assertIn("['Alta', 'Media', 'Baja']", APP)

    def test_full_item_experience_and_humanized_name_are_present(self):
        for copy in ("Qué se encontró", "Qué debería corregirse", "Ver instrucciones", "Pasos recomendados", "Cómo comprobarlo"):
            self.assertIn(copy, HTML)
        self.assertIn('<details class="plan-item__instructions">', HTML)
        self.assertIn("displayNames[item.control_code] || item.name", APP)
        self.assertIn("Política de privacidad claramente asociada a la empresa", APP)
        self.assertIn("plan-item__code", HTML)

    def test_controlled_error_states_are_distinct(self):
        self.assertIn("response.status === 404", APP)
        self.assertIn("if (!response.ok) { showError('unavailable')", APP)
        self.assertIn("Plan no disponible", APP)
        self.assertIn("No pudimos cargar el Plan", APP)
        self.assertIn("No pudimos mostrar este Plan", APP)
        self.assertIn("catch { showError('unavailable'); }", APP)
        self.assertIn("catch { showError('invalid'); return; }", APP)
        self.assertIn('href="/privacy/"', HTML)

    def test_request_timeout_always_finishes_loading(self):
        self.assertIn("const requestTimeoutMs = 10000", APP)
        self.assertIn("new AbortController()", APP)
        self.assertIn("setTimeout(() => controller.abort(), requestTimeoutMs)", APP)
        self.assertIn("signal: controller.signal", APP)
        self.assertIn("finally {", APP)
        self.assertIn("clearTimeout(timeoutId)", APP)
        self.assertIn("elements.loading.hidden = true", APP)

    def test_retry_cannot_start_concurrent_requests(self):
        self.assertIn("if (requestInProgress) return", APP)
        self.assertIn("elements.retry.disabled = true", APP)
        self.assertIn("elements.retry.disabled = false", APP)
        self.assertIn("elements.retry.addEventListener('click', loadPlan)", APP)

    def test_proxy_keeps_correction_plan_get_narrow_and_public(self):
        self.assertIn(r"^privacy\/correction-plans\/[A-Za-z0-9_-]+$", PROXY)
        self.assertIn("isCorrectionPlan && request.method.toUpperCase() === 'GET'", PROXY)
        self.assertIn("!isAllowedCorrectionPlan && !env.MININODE_API_KEY", PROXY)
        self.assertIn("status: upstream.status", PROXY)
        self.assertIn("upstream.headers.get('Content-Type')", PROXY)

    def test_private_page_metadata_and_cache_busted_local_assets(self):
        self.assertIn('<meta name="robots" content="noindex, nofollow">', HTML)
        self.assertIn('<meta name="referrer" content="no-referrer">', HTML)
        self.assertIn('?v=1"', HTML)
        self.assertNotIn("http://", HTML)
        self.assertNotIn("https://", HTML)

    def test_future_product_features_remain_out_of_scope(self):
        combined = (HTML + APP).lower()
        for forbidden in ("solicitar plan de corrección", "checkout", "stripe", "webpay", "mercado pago", "login", "magic link", "recheck", "checkbox"):
            self.assertNotIn(forbidden, combined)
        self.assertNotIn("<form", HTML.lower())


if __name__ == "__main__":
    unittest.main()
