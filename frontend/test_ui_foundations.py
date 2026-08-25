import re
from pathlib import Path


FRONTEND = Path(__file__).parent
MAIN_PAGES = (
    FRONTEND / "index.html",
    FRONTEND / "privacy" / "index.html",
    FRONTEND / "learn" / "index.html",
)


def test_global_styles_load_the_ui_foundations():
    styles = (FRONTEND / "styles.css").read_text(encoding="utf-8")
    assert '@import url("assets/css/tokens.css");' in styles
    assert '@import url("assets/css/components.css");' in styles
    assert (FRONTEND / "assets" / "css" / "tokens.css").is_file()

    for page in MAIN_PAGES:
        html = page.read_text(encoding="utf-8")
        assert re.search(r'<link rel="stylesheet" href="(?:\.\./)*styles\.css">', html)


def test_main_pages_reuse_the_shared_header_and_footer():
    for page in MAIN_PAGES:
        html = page.read_text(encoding="utf-8")
        assert "partials/header-nav.html" in html
        assert "partials/footer.html" in html
        assert 'id="site-header-nav"' not in html
        assert 'id="site-footer"' not in html


def test_page_styles_do_not_redeclare_the_primary_hex():
    for stylesheet in (
        FRONTEND / "privacy" / "styles.css",
        FRONTEND / "learn" / "learn.css",
        FRONTEND / "assets" / "css" / "agents.page.css",
    ):
        assert "#176b78" not in stylesheet.read_text(encoding="utf-8").lower()
