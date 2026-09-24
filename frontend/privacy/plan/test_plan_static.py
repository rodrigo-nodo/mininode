import unittest
from pathlib import Path


PLAN_DIR = Path(__file__).parent
FRONTEND_DIR = PLAN_DIR.parents[1]
ASSETS_DIR = FRONTEND_DIR / "privacy/plan-assets"
HTML = (PLAN_DIR / "index.html").read_text(encoding="utf-8")
APP = (ASSETS_DIR / "app.js").read_text(encoding="utf-8")
ROUTE_PATH = FRONTEND_DIR / "functions/privacy/plan/[token].js"
OPTIONAL_ROUTE_PATH = FRONTEND_DIR / "functions/privacy/plan/[[token]].js"
REDIRECTS_PATH = FRONTEND_DIR / "_redirects"
REDIRECTS = REDIRECTS_PATH.read_text(encoding="utf-8")
PROXY = (FRONTEND_DIR / "functions/api/[[path]].js").read_text(encoding="utf-8")


class RealCorrectionPlanStaticTests(unittest.TestCase):
    def test_clean_dynamic_route_uses_static_rewrite(self):
        self.assertTrue(REDIRECTS_PATH.is_file())
        self.assertFalse(ROUTE_PATH.exists())
        self.assertFalse(OPTIONAL_ROUTE_PATH.exists())

        rules = [line.split() for line in REDIRECTS.splitlines()
                 if line.strip() and not line.lstrip().startswith("#")]
        plan_rules = [rule for rule in rules if rule[0] == "/privacy/plan/:token"]
        self.assertEqual(plan_rules, [["/privacy/plan/:token", "/privacy/plan/", "200"]])
        self.assertNotIn(["/privacy/plan/*", "/privacy/plan/", "200"], rules)
        self.assertNotIn(plan_rules[0][2], {"301", "302", "307", "308"})

        plan_rule_index = rules.index(plan_rules[0])
        catch_all_indexes = [index for index, rule in enumerate(rules)
                             if rule[0] in {"/*", "*"}]
        self.assertTrue(all(plan_rule_index < index for index in catch_all_indexes))

        self.assertIn("window.location.pathname", APP)
        self.assertIn(r"^\/privacy\/plan\/([^/]+)\/?$", APP)
        self.assertNotIn("searchParams", APP)

    def test_static_plan_page_and_api_function_remain_available(self):
        self.assertTrue((PLAN_DIR / "index.html").is_file())
        self.assertTrue((FRONTEND_DIR / "functions/api/[[path]].js").is_file())
        self.assertTrue((ASSETS_DIR / "app.js").read_text(encoding="utf-8").startswith("const elements"))
        self.assertIn("new AbortController()", APP)
        self.assertIn("requestTimeoutMs", APP)
        self.assertTrue((ASSETS_DIR / "styles.css").read_text(encoding="utf-8").startswith(".plan-loading"))
        self.assertFalse((ASSETS_DIR / "app.js").read_text(encoding="utf-8").startswith("<!doctype html>"))
        self.assertFalse((ASSETS_DIR / "styles.css").read_text(encoding="utf-8").startswith("<!doctype html>"))
        self.assertFalse((PLAN_DIR / "app.js").exists())
        self.assertFalse((PLAN_DIR / "styles.css").exists())

    def test_dynamic_page_assets_are_absolute(self):
        for asset in (
            '/styles.css',
            '/privacy/plan-demo/styles.css?v=1',
            '/privacy/plan-assets/styles.css?v=5',
            '/include.js',
            '/privacy/plan-assets/app.js?v=7',
        ):
            self.assertIn(asset, HTML)

    def test_only_token_request_matches_plan_rewrite(self):
        source = "/privacy/plan/:token"

        def matches(path):
            source_parts = source.strip("/").split("/")
            path_parts = path.strip("/").split("/")
            return len(source_parts) == len(path_parts) and all(
                expected.startswith(":") or expected == actual
                for expected, actual in zip(source_parts, path_parts)
            )

        self.assertTrue(matches("/privacy/plan/ABC123"))
        self.assertFalse(matches("/privacy/plan-assets/app.js"))
        self.assertFalse(matches("/privacy/plan-assets/styles.css"))

    def test_get_uses_same_origin_proxy_without_api_credentials(self):
        self.assertIn("`/api/privacy/correction-plans/${encodeURIComponent(token)}`", APP)
        self.assertIn("method: 'GET'", APP)
        self.assertNotIn("X-Api-Key", APP)
        self.assertNotIn("api.mininode.io", APP)
        self.assertIn("isAllowedCorrectionPlan", PROXY)
        self.assertIn("if (!isAllowedCorrectionPlan && !isPublicOrderCreation) headers.set('X-Api-Key'", PROXY)

    def test_token_and_snapshot_are_not_persisted_or_logged(self):
        combined = HTML + APP + REDIRECTS
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
        self.assertIn("Privacy Web no disponible", APP)
        self.assertIn("No pudimos cargar Privacy Web", APP)
        self.assertIn("No pudimos mostrar Privacy Web", APP)
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
        self.assertIn(r"^\/api\/privacy\/correction-plans\/[A-Za-z0-9_-]+\/?$", PROXY)
        self.assertIn(".test(url.pathname)", PROXY)
        self.assertIn("isCorrectionPlan && method === 'GET'", PROXY)
        self.assertIn("!isAllowedCorrectionPlan && !isPublicOrderCreation && !env.MININODE_API_KEY", PROXY)
        self.assertIn("status: upstream.status", PROXY)
        self.assertIn("upstream.headers.get('Content-Type')", PROXY)

    def test_private_page_metadata_and_cache_busted_local_assets(self):
        self.assertIn('<meta name="robots" content="noindex, nofollow">', HTML)
        self.assertIn('<meta name="referrer" content="no-referrer">', HTML)
        self.assertIn('src="/privacy/plan-assets/app.js?v=7"', HTML)
        self.assertNotIn('src="/privacy/plan-assets/app.js?v=1"', HTML)
        self.assertNotIn("http://", HTML)
        self.assertNotIn("https://", HTML)

    def test_future_product_features_remain_out_of_scope(self):
        combined = (HTML + APP).lower()
        for forbidden in ("solicitar plan de corrección", "checkout", "stripe", "webpay", "mercado pago", "login", "magic link", "recheck", "checkbox"):
            self.assertNotIn(forbidden, combined)
        self.assertNotIn("<form", HTML.lower())

    def test_shared_header_footer_and_plan_disclaimers_are_present(self):
        self.assertIn('data-include="/partials/header-nav.html"', HTML)
        self.assertIn('data-include="/partials/footer.html"', HTML)
        self.assertIn('src="/include.js"', HTML)
        self.assertIn("Privacy Score es un indicador desarrollado por Mininode.", HTML)
        self.assertIn("no reemplaza una revisión jurídica o especializada", HTML)

    def test_active_privacy_web_keeps_review_cta_and_confirmation(self):
        self.assertNotIn("1 comprobación incluida.", HTML)
        self.assertIn('id="check-deadline"', HTML)
        self.assertIn("Mientras Privacy Web esté activo, puedes volver a revisar el sitio", HTML)
        self.assertIn("Revisa nuevamente el sitio después de aplicar cambios", HTML)
        self.assertIn(">Revisar nuevamente</button>", HTML)
        self.assertIn("Se realizará una nueva revisión del sitio y se comparará con el diagnóstico original.", HTML)
        self.assertIn("elements.checkStart.hidden = false", APP)
        self.assertIn("check.latest_check", APP)
        self.assertIn("Activo hasta:", APP)

    def test_latest_result_formats_score_counts_and_keeps_repeat_cta(self):
        self.assertIn("result.score_change === 0", APP)
        self.assertIn("result.score_change > 0 ? '+' : ''", APP)
        self.assertIn("result.corrected_count === 1 ? 'mejora corregida' : 'mejoras corregidas'", APP)
        self.assertIn("result.pending_count === 1 ? 'todavía pendiente' : 'todavía pendientes'", APP)
        self.assertIn("result.items.forEach", APP)
        self.assertIn("elements.checkAvailable.hidden = false", APP)
        self.assertIn("elements.checkCreated.textContent = friendlyDate(review.created_at)", APP)
        self.assertIn("renderCheckResult(data);", APP)
        self.assertIn("elements.checkStart.hidden = false", APP)

    def test_incomparable_result_shows_only_current_score_and_explanation(self):
        self.assertIn('id="check-not-comparable" hidden', HTML)
        self.assertIn("Esta revisión utiliza una versión diferente del análisis.", HTML)
        self.assertIn("Score de la revisión actual:", HTML)
        branch = APP[APP.index("if (notComparable)"):APP.index("elements.checkBefore.textContent")]
        self.assertIn("checkComparison.hidden = notComparable", APP)
        self.assertIn("checkNotComparable.hidden = !notComparable", APP)
        self.assertIn("checkCurrentScore.textContent = `${result.current_score} / 100`", branch)
        self.assertIn("return;", branch)
        self.assertNotIn("score_change", branch)
        self.assertNotIn("corrected_count", branch)
        self.assertNotIn("pending_count", branch)
        self.assertNotIn("Sin cambios en el score", branch)
        self.assertNotIn("+", branch)

    def test_legacy_v1_result_without_comparability_uses_historical_rendering(self):
        self.assertIn("result.comparability?.status === 'not_comparable'", APP)
        self.assertIn("elements.checkBefore.textContent = `${result.original_score} / 100`", APP)
        self.assertIn("elements.checkNow.textContent = `${result.current_score} / 100`", APP)

    def test_expired_check_keeps_cta_disabled(self):
        expired_branch = APP[APP.index("if (check.status === 'expired')"):APP.index("elements.checkStart.hidden = false")]
        self.assertIn("La vigencia de Privacy Web ha finalizado.", expired_branch)
        self.assertNotIn("checkStart.hidden = false", expired_branch)

    def test_continuous_monitoring_is_only_revealed_after_a_review(self):
        self.assertIn('id="continuous-monitoring"', HTML)
        self.assertIn('aria-labelledby="continuous-monitoring-title" hidden', HTML)
        self.assertIn("elements.continuousMonitoring.hidden = true", APP)
        self.assertIn("elements.continuousMonitoring.hidden = false", APP)
        self.assertIn("if (check.latest_check)", APP)
        self.assertIn("renderCheckResult(check.latest_check)", APP)

    def test_continuous_monitoring_uses_roadmap_copy_without_cta_or_price(self):
        monitoring = HTML[HTML.index('<section class="continuous-monitoring"'):HTML.index('</section>', HTML.index('<section class="continuous-monitoring"'))]
        self.assertIn("Próximamente", monitoring)
        self.assertIn("Seguimiento automático", monitoring)
        self.assertIn("Mininode podrá revisar periódicamente el sitio y avisar si aparecen nuevas señales o si alguna mejora vuelve a quedar pendiente.", monitoring)
        self.assertNotIn("<button", monitoring)
        self.assertNotIn("<a ", monitoring)
        self.assertNotIn("$", monitoring)

    def test_continuous_monitoring_does_not_add_requests_or_change_check_result(self):
        self.assertEqual(APP.count("fetch("), 2)
        for assignment in (
            "elements.checkBefore.textContent = `${result.original_score} / 100`",
            "elements.checkNow.textContent = `${result.current_score} / 100`",
            "elements.checkCorrected.textContent = result.corrected_count",
            "elements.checkPending.textContent = result.pending_count",
            "elements.checkCreated.textContent = friendlyDate(review.created_at)",
        ):
            self.assertIn(assignment, APP)


if __name__ == "__main__":
    unittest.main()
