import json
import re
import subprocess
import unittest
from pathlib import Path


PRIVACY_DIR = Path(__file__).parent
APP = (PRIVACY_DIR / "app.js").read_text(encoding="utf-8")
HTML = (PRIVACY_DIR / "index.html").read_text(encoding="utf-8")
DATA_HTML = (PRIVACY_DIR / "data" / "index.html").read_text(encoding="utf-8")
HOME_HTML = (PRIVACY_DIR.parent / "index.html").read_text(encoding="utf-8")


class PrivacyResultStaticTests(unittest.TestCase):
    def test_human_status_uses_backend_score_boundaries(self):
        function = re.search(
            r"const getHumanStatus = \(score\) => \{.*?\n\};",
            APP,
            re.DOTALL,
        ).group()
        boundaries = [0, 39, 40, 69, 70, 84, 85, 100]
        script = f"{function}\nconsole.log(JSON.stringify({boundaries}.map(getHumanStatus)));"
        result = subprocess.run(
            ["node", "-e", script],
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(json.loads(result.stdout), [
            "Hay aspectos importantes por mejorar",
            "Hay aspectos importantes por mejorar",
            "Hay aspectos que puedes mejorar",
            "Hay aspectos que puedes mejorar",
            "Bien",
            "Bien",
            "Bien",
            "Bien",
        ])

    def test_human_status_does_not_interpret_backend_status_text(self):
        function = APP.split("const getHumanStatus", 1)[1].split("const renderPriorities", 1)[0]

        self.assertNotIn("status", function)
        self.assertNotIn("includes", function)
        self.assertIn("getHumanStatus(score)", APP)

    def test_configures_the_complete_matrix_in_five_areas(self):
        config = APP.split("const privacyAreas = [", 1)[1].split("const resultLabels", 1)[0]
        codes = re.findall(r"code: '(PRV-\d+)'", config)

        self.assertEqual(len(codes), 17)
        self.assertEqual(len(set(codes)), 17)
        self.assertEqual(config.count("name: 'Transparencia'"), 1)
        self.assertEqual(config.count("name: 'Formularios'"), 1)
        self.assertEqual(config.count("name: 'Cookies'"), 1)
        self.assertEqual(config.count("name: 'Contacto'"), 1)
        self.assertEqual(config.count("name: 'Seguridad'"), 1)
        self.assertEqual(config.count("name: '") - 17, 5)
        self.assertEqual(len(re.findall(r"PRV-0\d\d", config)), 12)
        self.assertEqual(len(re.findall(r"PRV-10[14]", config)), 2)
        self.assertEqual(config.count("PRV-201"), 1)
        self.assertEqual(config.count("PRV-301"), 1)
        self.assertEqual(config.count("PRV-501"), 1)

    def test_context_controls_are_informational(self):
        self.assertRegex(APP, r"code: 'PRV-004'.*informational: true")
        self.assertRegex(APP, r"code: 'PRV-009'.*informational: true")
        self.assertIn("Informativo · no afecta el resultado", APP)

    def test_all_backend_results_have_human_labels(self):
        expected = {
            "detected": "Bien",
            "partial": "Puede mejorar",
            "not_detected": "Necesita atención",
            "not_evaluable": "No pudimos revisarlo",
            "not_applicable": "No aplica",
        }
        for result, label in expected.items():
            self.assertRegex(APP, rf"{result}: {{ label: '{label}'")

    def test_result_ui_hides_codes_and_technical_coverage(self):
        self.assertNotIn("PRV-", HTML)
        self.assertNotIn("diagnostic-coverage", HTML)
        self.assertIn("Ver qué revisamos", HTML)
        self.assertIn("17 puntos en 5 áreas", HTML)

    def test_priorities_and_commercial_paths_are_preserved(self):
        self.assertIn(".slice(0, 3)", APP)
        self.assertIn("Array.isArray(priorities) && priorities.length > 0", APP)
        self.assertIn("Plan de corrección", HTML)
        self.assertIn("$49.900", HTML)
        self.assertIn("pago único", HTML)
        self.assertIn("Todas las mejoras detectadas", HTML)
        self.assertIn("1 comprobación de mejoras incluida", HTML)
        self.assertNotIn("1 nueva revisión", HTML.lower())
        self.assertNotIn("Nueva revisión automática", HTML)
        self.assertIn("comparar el sitio con el diagnóstico original", HTML)
        self.assertIn("Disponible durante 90 días desde la compra.", HTML)
        self.assertIn("Obtener plan de corrección", HTML)
        self.assertIn('name="email"', HTML)
        self.assertIn("Se utilizará para gestionar la solicitud y entregar el plan.", HTML)
        self.assertIn("fetch('/api/privacy/correction-plan-orders'", APP)
        self.assertIn("JSON.stringify({ diagnostic_id: currentDiagnosticId, email: orderEmail.value })", APP)
        self.assertNotIn("site_url:", APP)
        self.assertNotIn("amount:", APP)
        self.assertNotIn("currency:", APP)
        self.assertNotIn("product_code:", APP)
        self.assertIn("Solicitud preparada", HTML)
        self.assertIn("El pago en línea estará disponible próximamente.", HTML)
        self.assertIn("Disponible para comprar durante 24 horas después de este diagnóstico.", HTML)
        self.assertIn("Este diagnóstico tiene más de 24 horas.", HTML)
        self.assertIn("Revisar nuevamente", HTML)
        self.assertNotIn("countdown", APP.lower())
        self.assertNotIn("recheck", APP.lower())
        self.assertNotIn("recheck_expires_at", HTML)
        self.assertNotIn("Le queda 1 revisión", HTML)
        self.assertNotIn("Última revisión", HTML)
        self.assertNotIn("Solo puede volver a analizar una vez", HTML)
        self.assertIn("La implementación técnica no está incluida.", HTML)
        self.assertNotIn("acompañamiento para resolver dudas", HTML.lower())
        self.assertIn("¿Necesita que alguien realice los cambios?", HTML)
        self.assertIn("Consultar apoyo técnico", HTML)
        self.assertIn('id="privacy-no-priorities"', HTML)

    def test_privacy_data_is_an_unconditional_next_step(self):
        self.assertIn('href="/privacy/data/">Conocer Privacy Data</a>', HTML)
        self.assertEqual(HTML.count('href="/privacy/data/"'), 1)
        self.assertIn("Próximamente", HTML)
        privacy_data = HTML.split('<section class="privacy-data-next-step"', 1)[1]
        self.assertNotIn("score", privacy_data.split("</section>", 1)[0])
        self.assertNotIn("priorities", privacy_data.split("</section>", 1)[0])

    def test_product_names_and_privacy_data_public_copy(self):
        self.assertIn('<p class="privacy-tag">Privacy Web</p>', HTML)
        self.assertNotIn("Mininode Privacy", HTML)
        self.assertIn('<form class="privacy-form" id="privacy-form">', HTML)
        self.assertIn("fetch('/api/privacy/diagnose'", APP)
        self.assertIn("Plan de corrección", HTML)
        self.assertIn('<span class="product-row__name">Privacy Web</span>', HOME_HTML)
        self.assertIn('<span class="product-row__name">Privacy Data</span>', HOME_HTML)
        self.assertNotIn("Mininode Privacy", HOME_HTML)
        self.assertIn('<span class="product-status">Próximamente</span>', HOME_HTML)
        self.assertIn("Ordena cómo manejas los datos personales por dentro.", DATA_HTML)
        self.assertIn('<p class="data-state">Próximamente</p>', DATA_HTML)
        self.assertIn(
            "Privacy Data ayuda a pequeñas empresas a entender y ordenar el manejo interno de datos personales.",
            DATA_HTML,
        )
        self.assertNotIn("En desarrollo", HOME_HTML)
        self.assertNotIn("En desarrollo", DATA_HTML)

        for technical_name in (
            "Metadata Scanner",
            "Data Classifier",
            "Data Mapper",
            "Risk Engine",
            "Connectors",
            "Local Scanner",
        ):
            self.assertNotIn(technical_name, DATA_HTML)

    def test_order_form_minimizes_data_and_keeps_commercial_fields_server_side(self):
        order_form = HTML.split('id="correction-order-form"', 1)[1].split("</form>", 1)[0]
        self.assertEqual(order_form.count("<input"), 1)
        self.assertIn('name="email"', order_form)
        for field in ('name="name"', 'name="empresa"', 'name="rut"', 'name="telefono"', 'name="site_url"'):
            self.assertNotIn(field, order_form)

        request = APP.split("fetch('/api/privacy/correction-plan-orders'", 1)[1].split("});", 1)[0]
        self.assertIn("diagnostic_id: currentDiagnosticId", request)
        self.assertIn("email: orderEmail.value", request)
        for field in ("site_url", "amount", "currency", "status", "product_code", "score", "snapshot"):
            self.assertNotIn(f"{field}:", request)

    def test_commercial_section_uses_privacy_identity_and_formal_language(self):
        commercial = HTML.split('id="privacy-correction-offer"', 1)[1].split('class="privacy-result__note"', 1)[0]
        self.assertNotRegex(commercial.lower(), r"\b(tu|te|quieres|obtén)\b")
        styles = (PRIVACY_DIR / "styles.css").read_text(encoding="utf-8").lower()
        self.assertIn("var(--color-primary)", styles)
        self.assertNotRegex(commercial.lower(), r"violet|purple|#6c4df4")

    def test_api_and_backend_score_remain_inputs(self):
        self.assertIn("fetch('/api/privacy/diagnose'", APP)
        self.assertIn("const score = diagnostic.score;", APP)
        self.assertNotRegex(APP, r"diagnostic\.score\s*=")

    def test_app_script_is_cache_busted_with_the_result_markup(self):
        self.assertIn('<script src="app.js?v=109" defer></script>', HTML)

    def test_local_stylesheet_is_cache_busted(self):
        self.assertRegex(
            HTML,
            r'<link rel="stylesheet" href="styles\.css\?v=[^"&]+">',
        )

    def test_flow_errors_are_distinguished_without_exposing_internal_codes(self):
        for code in ("api_request_failed", "invalid_api_response", "render_failed"):
            self.assertIn(f"reportFlowError('{code}'", APP)
            self.assertNotIn(code, HTML)
        self.assertIn("Recibimos el diagnóstico, pero no pudimos mostrar el resultado.", APP)


if __name__ == "__main__":
    unittest.main()
