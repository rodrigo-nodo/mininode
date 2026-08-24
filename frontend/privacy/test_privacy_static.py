import json
import re
import subprocess
import unittest
from pathlib import Path


PRIVACY_DIR = Path(__file__).parent
APP = (PRIVACY_DIR / "app.js").read_text(encoding="utf-8")
HTML = (PRIVACY_DIR / "index.html").read_text(encoding="utf-8")


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
        self.assertIn('/contact/?source=privacy&amp;intent=correction', HTML)
        self.assertIn("Plan de corrección automático", HTML)
        self.assertIn("$49.900 CLP", HTML)
        self.assertIn("Solicitar plan de corrección", HTML)
        self.assertIn("La implementación técnica no está incluida.", HTML)
        self.assertNotIn("acompañamiento para resolver dudas", HTML.lower())
        self.assertIn("¿Necesita que alguien realice los cambios?", HTML)
        self.assertIn("Consultar apoyo técnico", HTML)
        self.assertIn('id="privacy-no-priorities"', HTML)

    def test_privacy_data_is_an_unconditional_next_step(self):
        self.assertIn('href="/privacy/data/">Conocer Privacy Data</a>', HTML)
        self.assertEqual(HTML.count('href="/privacy/data/"'), 1)
        self.assertIn("En desarrollo", HTML)
        privacy_data = HTML.split('<section class="privacy-data-next-step"', 1)[1]
        self.assertNotIn("score", privacy_data.split("</section>", 1)[0])
        self.assertNotIn("priorities", privacy_data.split("</section>", 1)[0])

    def test_commercial_section_uses_privacy_identity_and_formal_language(self):
        commercial = HTML.split('id="privacy-correction-offer"', 1)[1].split('class="privacy-result__note"', 1)[0]
        self.assertNotRegex(commercial.lower(), r"\b(tu|te|quieres|obtén)\b")
        self.assertIn("#176b78", (PRIVACY_DIR / "styles.css").read_text(encoding="utf-8").lower())
        self.assertNotRegex(commercial.lower(), r"violet|purple|#6c4df4")

    def test_api_and_backend_score_remain_inputs(self):
        self.assertIn("fetch('/api/privacy/diagnose'", APP)
        self.assertIn("const score = diagnostic.score;", APP)
        self.assertNotRegex(APP, r"diagnostic\.score\s*=")

    def test_app_script_is_cache_busted_with_the_result_markup(self):
        self.assertIn('<script src="app.js?v=106" defer></script>', HTML)

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
