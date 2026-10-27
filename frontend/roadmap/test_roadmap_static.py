"""Static regression checks for public-facing roadmap content."""
from pathlib import Path
import unittest

PAGE = Path(__file__).with_name("index.html")
CSS = Path(__file__).with_name("roadmap.css")


class RoadmapPageTests(unittest.TestCase):
    def test_public_sections_and_products(self):
        html = PAGE.read_text(encoding="utf-8")
        for expected in (
            'id="available-title"', 'id="developing-title"',
            'id="upcoming-title"', 'Privacy Web', 'Privacy Data',
            'href="/privacy/"', 'href="/privacy/data/"',
        ):
            self.assertIn(expected, html)

    def test_not_promise_future_features_as_live(self):
        html = PAGE.read_text(encoding="utf-8")
        self.assertIn("En desarrollo", html)
        self.assertIn("Planificado", html)
        self.assertIn("se inician manualmente", html)
        self.assertIn("no constituye una certificación", html)
        for outdated in ("Agente “Contabilidad”", "Webhook de pagos (Flow/MP)", "Etapa 1 (octubre)"):
            self.assertNotIn(outdated, html)

    def test_responsive_styles(self):
        self.assertIn("@media(max-width:600px)", CSS.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
