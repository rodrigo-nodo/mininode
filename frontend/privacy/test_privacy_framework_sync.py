import json
import re
import unittest
from pathlib import Path


PRIVACY_DIR = Path(__file__).parent
REPO_ROOT = PRIVACY_DIR.parents[1]
APP = (PRIVACY_DIR / "app.js").read_text(encoding="utf-8")
HTML = (PRIVACY_DIR / "index.html").read_text(encoding="utf-8")
SYNC = (PRIVACY_DIR / "framework-v0.6.js").read_text(encoding="utf-8")
CONTROLS = json.loads(
    (REPO_ROOT / "backend" / "src" / "mininode_api" / "domain_packs" / "privacy" / "controls.json").read_text(encoding="utf-8")
)


class PrivacyFrameworkSyncTests(unittest.TestCase):
    def test_runtime_matrix_matches_backend_framework_0_10(self):
        backend_controls = CONTROLS["controls"]
        backend_codes = {control["code"] for control in backend_controls}
        form_codes = {
            control["code"]
            for control in backend_controls
            if control["domain"] == "Formularios"
        }

        app_config = APP.split("const privacyAreas = [", 1)[1].split("const resultLabels", 1)[0]
        app_codes = set(re.findall(r"code: '(PRV-\d+)'", app_config))
        sync_codes = set(re.findall(r"code: '(PRV-\d+)'", SYNC))
        runtime_codes = (app_codes - form_codes) | sync_codes

        self.assertEqual(CONTROLS["version"], "0.10")
        self.assertEqual(len(backend_codes), 21)
        self.assertEqual(form_codes, {"PRV-101", "PRV-102", "PRV-103", "PRV-104"})
        self.assertEqual(sync_codes, form_codes)
        self.assertEqual(runtime_codes, backend_codes)

    def test_v1_informational_form_controls_do_not_drive_area_status(self):
        backend_forms = {
            control["code"]: control
            for control in CONTROLS["controls"]
            if control["domain"] == "Formularios"
        }
        contextual = {
            code
            for code, control in backend_forms.items()
            if control.get("type") == "context" and control.get("score_weight") == 0
        }

        self.assertEqual(contextual, {"PRV-101", "PRV-103", "PRV-104"})
        for code in {"PRV-101", "PRV-103", "PRV-104"}:
            self.assertRegex(SYNC, rf"code: '{code}'.*informational: true")
        self.assertNotRegex(SYNC, r"code: 'PRV-102'.*informational: true")

    def test_informational_controls_use_neutral_non_adverse_labels(self):
        self.assertIn("['Bien', 'Detectado']", SYNC)
        self.assertIn("['Puede mejorar', 'Parcialmente detectado']", SYNC)
        self.assertIn("['Necesita atención', 'No detectado']", SYNC)
        self.assertIn("['No pudimos revisarlo', 'No pudimos revisarlo']", SYNC)
        self.assertIn("['No aplica', 'No aplica']", SYNC)
        self.assertIn("if (!control.informational)", SYNC)
        self.assertIn("state.classList.add('privacy-state--neutral')", SYNC)
        self.assertIn("new MutationObserver(relabelInformationalControlsV06)", SYNC)

    def test_sync_runs_after_app_and_updates_visible_scope(self):
        self.assertIn('<script src="framework-v0.6.js?v=2" defer></script>', HTML)
        self.assertLess(
            HTML.index('<script src="app.js?v=113" defer></script>'),
            HTML.index('<script src="framework-v0.6.js?v=2" defer></script>'),
        )
        self.assertIn("formsAreaV06.controls = FORM_CONTROLS_V06;", SYNC)
        self.assertIn("Revisamos 21 puntos de tu sitio en 5 áreas.", SYNC)
        self.assertIn("21 puntos en 5 áreas", SYNC)


if __name__ == "__main__":
    unittest.main()
