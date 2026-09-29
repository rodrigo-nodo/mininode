import unittest
from pathlib import Path

FRONTEND = Path(__file__).parent
HEAD = (FRONTEND / "partials" / "head-common.html").read_text(encoding="utf-8")

class HeadCommonTests(unittest.TestCase):
    def test_favicon_is_centralized(self):
        self.assertEqual(HEAD.count('rel="icon"'), 1)
        self.assertIn('data-href="assets/mininode-favicon.svg"', HEAD)
        for page in ("access/index.html", "privacy/index.html"):
            html = (FRONTEND / page).read_text(encoding="utf-8")
            self.assertNotIn('rel="icon"', html)

if __name__ == "__main__":
    unittest.main()
