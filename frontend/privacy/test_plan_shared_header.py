"""PW-03B Plan uses the real shared Mininode shell, not a local fallback."""
from pathlib import Path
import re
import unittest
from urllib.parse import urljoin, urlparse

FRONTEND = Path(__file__).resolve().parents[1]
PLAN = (FRONTEND / "privacy" / "plan" / "index.html").read_text(encoding="utf-8")


class PlanSharedHeaderTests(unittest.TestCase):
    def test_plan_includes_existing_shared_header_and_footer(self):
        page_url = "https://preview.example/privacy/plan/"
        for partial in ("header-nav.html", "footer.html"):
            match = re.search(r'data-include="([^"]*' + partial + r')"', PLAN)
            self.assertIsNotNone(match)
            url = urlparse(urljoin(page_url, match.group(1)))
            self.assertEqual(url.path, "/partials/" + partial)
            self.assertTrue((FRONTEND / url.path.lstrip("/")).is_file())

    def test_plan_loads_shared_include_script_without_fallback_header(self):
        page_url = "https://preview.example/privacy/plan/"
        match = re.search(r'<script src="([^"]*include\\.js[^"]*)" defer></script>', PLAN)
        self.assertIsNotNone(match)
        self.assertEqual(urlparse(urljoin(page_url, match.group(1))).path, "/include.js")
        self.assertIn('id="site-header-nav"', (FRONTEND / "partials" / "header-nav.html").read_text())
        self.assertNotIn('class="plan-header"', PLAN)
        self.assertNotIn('<header class="header', PLAN)


if __name__ == "__main__":
    unittest.main()
