import json
import re
import unittest
from pathlib import Path


PRIVACY_DIR = Path(__file__).parent
REPO_ROOT = PRIVACY_DIR.parents[1]
APP = (PRIVACY_DIR / "app.js").read_text(encoding="utf-8")
HTML = (PRIVACY_DIR / "index.html").read_text(encoding="utf-8")
UX = (PRIVACY_DIR / "control-ux.js").read_text(encoding="utf-8")
CONTROLS = json.loads(
    (REPO_ROOT / "backend" / "src" / "mininode_api" / "domain_packs" / "privacy" / "controls.json").read_text(encoding="utf-8")
)


class PrivacyFrameworkSyncTests(unittest.TestCase):
    def test_single_renderer_matches_all_backend_controls_and_shared_names(self):
        backend_codes = {control["code"] for control in CONTROLS["controls"]}
        block = APP.split("const privacyAreas = [", 1)[1].split("const AREA_INFO", 1)[0]
        app_codes = re.findall(r"code: '(PRV-\d+)'", block)
        ux_codes = re.findall(r"'(PRV-\d+)': Object.freeze", UX)
        self.assertEqual(CONTROLS["version"], "0.12")
        self.assertEqual(len(backend_codes), 21)
        self.assertEqual(len(app_codes), len(set(app_codes)))
        self.assertEqual(set(app_codes), backend_codes)
        self.assertEqual(len(ux_codes), len(set(ux_codes)))
        self.assertEqual(set(ux_codes), backend_codes)
        self.assertEqual(len(re.findall(r"code: 'PRV-10[1-4]'", block)), 4)

    def test_informational_flags_follow_backend_semantics(self):
        expected = {control["code"] for control in CONTROLS["controls"]
                    if control["type"] == "context"}
        block = APP.split("const privacyAreas = [", 1)[1].split("const AREA_INFO", 1)[0]
        contextual = set(re.findall(r"code: '(PRV-\d+)', informational: true", block))
        self.assertEqual(expected, {"PRV-004", "PRV-009", "PRV-101", "PRV-103", "PRV-104", "PRV-201"})
        self.assertEqual(contextual, expected)
        self.assertIn("if (!control.informational)", APP)
        self.assertIn("informational: { label: 'Informativo', className: 'neutral' }", APP)
        self.assertIn("control.code === 'PRV-201' && value === 'not_applicable'", APP)
        self.assertIn("isAreaPartial", APP)

    def test_shared_catalog_loads_before_renderer_without_patch_script(self):
        ux_tag = re.search(r'<script src="control-ux\.js\?v=[^"]+" defer></script>', HTML)
        app_tag = re.search(r'<script src="app\.js\?v=[^"]+" defer></script>', HTML)
        self.assertIsNotNone(ux_tag)
        self.assertIsNotNone(app_tag)
        self.assertLess(ux_tag.start(), app_tag.start())
        self.assertNotIn("framework-v0.6.js", HTML)
        self.assertFalse((PRIVACY_DIR / "framework-v0.6.js").exists())
        self.assertNotIn("MutationObserver", APP)
        self.assertIn("Revisamos 21 puntos de tu sitio en 5 áreas.", HTML)
        self.assertIn("21 puntos en 5 áreas", HTML)


if __name__ == "__main__":
    unittest.main()
