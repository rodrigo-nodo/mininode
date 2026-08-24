import json
import unittest
from pathlib import Path


DEMO_DIR = Path(__file__).parent
PRIVACY_DOMAIN_DIR = (
    DEMO_DIR.parents[2] / "backend/src/mininode_api/domain_packs/privacy"
)
HTML = (DEMO_DIR / "index.html").read_text(encoding="utf-8")
APP = (DEMO_DIR / "app.js").read_text(encoding="utf-8")
STYLES = (DEMO_DIR / "styles.css").read_text(encoding="utf-8")
FIXTURE = json.loads((DEMO_DIR / "fixture.json").read_text(encoding="utf-8"))
CONTROLS_CATALOG = json.loads(
    (PRIVACY_DOMAIN_DIR / "controls.json").read_text(encoding="utf-8")
)
ACTIONS_CATALOG = json.loads(
    (PRIVACY_DOMAIN_DIR / "actions.json").read_text(encoding="utf-8")
)


class PlanDemoStaticTests(unittest.TestCase):
    def test_demo_files_exist(self):
        for filename in ("index.html", "styles.css", "app.js", "fixture.json"):
            self.assertTrue((DEMO_DIR / filename).is_file())

    def test_fixture_matches_plan_contract_and_catalogs(self):
        self.assertEqual(
            set(FIXTURE),
            {"version", "actions_version", "initial_score", "item_count", "items"},
        )
        self.assertEqual(FIXTURE["version"], "1")
        self.assertEqual(FIXTURE["actions_version"], ACTIONS_CATALOG["version"])
        self.assertEqual(FIXTURE["item_count"], len(FIXTURE["items"]))
        self.assertEqual(FIXTURE["item_count"], 7)
        self.assertGreater(FIXTURE["item_count"], 3)

        controls = {
            control["code"]: control for control in CONTROLS_CATALOG["controls"]
        }
        required = {
            "control_code", "name", "priority", "result", "finding",
            "recommendation", "action_steps", "validation_step",
        }
        priority_by_impact = {
            "muy_alto": "Alta", "alto": "Alta", "medio": "Media", "bajo": "Baja"
        }
        for item in FIXTURE["items"]:
            self.assertEqual(set(item), required)
            self.assertTrue(item["action_steps"])
            control = controls[item["control_code"]]
            action = ACTIONS_CATALOG["actions"][item["control_code"]][item["result"]]
            self.assertEqual(item["name"], control["name"])
            self.assertEqual(item["priority"], priority_by_impact[control["impact"]])
            self.assertEqual(item["finding"], control["criteria"][item["result"]])
            self.assertEqual(item["recommendation"], control["base_recommendation"])
            self.assertEqual(item["action_steps"], action["action_steps"])
            self.assertEqual(item["validation_step"], action["validation_step"])

    def test_page_has_user_facing_sections_demo_label_and_disclaimer(self):
        for heading in (
            "Qué se encontró", "Qué debería corregirse",
            "Pasos recomendados", "Cómo comprobarlo",
        ):
            self.assertIn(heading, HTML)
        self.assertIn("Vista demo", HTML)
        self.assertIn("No es una certificación legal", HTML)
        self.assertIn("no reemplaza una revisión jurídica", HTML)
        self.assertNotIn("action_steps", HTML)
        self.assertNotIn("validation_step", HTML)

    def test_fixture_drives_all_plan_content_and_priority_counts(self):
        self.assertIn("fetch('fixture.json')", APP)
        self.assertIn("plan.items.forEach(renderPlanItem)", APP)
        self.assertIn("plan.initial_score", APP)
        self.assertIn("plan.item_count", APP)
        self.assertIn("plan.items.reduce", APP)
        self.assertNotIn(".slice(", APP)

    def test_detailed_instructions_use_native_collapsible_disclosure(self):
        details = HTML.split('<details class="plan-item__instructions"', 1)[1]
        self.assertNotIn(" open", details.split(">", 1)[0])
        self.assertIn("<summary>", details)
        self.assertIn("Ver instrucciones", details)
        self.assertIn("Ocultar instrucciones", details)
        self.assertIn("Pasos recomendados", details)
        self.assertIn("Cómo comprobarlo", details)
        self.assertLess(HTML.index("Qué se encontró"), HTML.index("<details"))
        self.assertLess(HTML.index("Qué debería corregirse"), HTML.index("<details"))

    def test_summary_explains_the_value_beyond_the_free_diagnostic(self):
        self.assertIn(
            "El diagnóstico gratuito muestra las principales prioridades.", HTML
        )
        self.assertIn("Este plan detalla todas las mejoras detectadas", HTML)

    def test_prv_003_has_a_presentational_name_without_changing_contract(self):
        prv_003 = next(
            control for control in CONTROLS_CATALOG["controls"]
            if control["code"] == "PRV-003"
        )
        self.assertEqual(prv_003["name"], "Política propia del responsable")
        self.assertIn("'PRV-003'", APP)
        self.assertIn(
            "Política de privacidad claramente asociada a la empresa", APP
        )
        self.assertIn("displayNames[item.control_code] || item.name", APP)

    def test_demo_has_no_commercial_or_future_infrastructure(self):
        combined = (HTML + APP).lower()
        for forbidden in (
            "/api/", "http://", "https://", "localstorage", "sessionstorage",
            "solicitar plan de corrección", "comprar", "pagar", "login",
            "checkbox", "recheck",
        ):
            self.assertNotIn(forbidden, combined)
        self.assertNotIn("<form", HTML.lower())
        self.assertNotIn("<button", HTML.lower())

    def test_local_assets_are_cache_busted_and_no_external_assets_exist(self):
        self.assertIn('href="styles.css?v=1"', HTML)
        self.assertIn('src="app.js?v=1"', HTML)
        self.assertNotIn("url(", STYLES.lower())

    def test_visible_copy_uses_formal_third_person_language(self):
        self.assertNotRegex(HTML.lower(), r"\b(tú|tu|te|usted|su sitio debe|corrige)\b")
        self.assertIn("La implementación técnica de los cambios no está incluida.", HTML)


if __name__ == "__main__":
    unittest.main()
