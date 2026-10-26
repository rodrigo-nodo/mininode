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
        assert re.search(r'<link rel="stylesheet" href="(?:\.\./)*styles\.css(?:\?v=[^"]+)?">', html)


def test_tokens_are_the_only_source_of_brand_color_values():
    tokens_path = FRONTEND / "assets" / "css" / "tokens.css"
    tokens = tokens_path.read_text(encoding="utf-8").lower()
    brand_tokens = (
        "--color-primary",
        "--color-primary-hover",
        "--color-primary-soft",
    )
    brand_values = []
    for token in brand_tokens:
        definition = re.search(rf"{re.escape(token)}\s*:\s*([^;]+);", tokens)
        assert definition, f"{token} must be defined in {tokens_path}"
        brand_values.append(definition.group(1).strip())

    for path in FRONTEND.rglob("*"):
        if path == tokens_path or path.suffix not in {".css", ".html"}:
            continue
        contents = path.read_text(encoding="utf-8").lower()
        for value in brand_values:
            assert value not in contents, f"{value} must only be defined in {tokens_path} (found in {path})"


def test_theme_color_is_resolved_from_the_primary_token():
    partial = (FRONTEND / "partials" / "head-common.html").read_text(encoding="utf-8")
    loader = (FRONTEND / "assets" / "js" / "core-head.js").read_text(encoding="utf-8")
    assert 'data-theme-color-token="--color-primary"' in partial
    assert "getPropertyValue(token)" in loader


def test_main_pages_reuse_the_shared_header_and_footer():
    for page in MAIN_PAGES:
        html = page.read_text(encoding="utf-8")
        assert "partials/header-nav.html" in html
        assert "partials/footer.html" in html
        assert 'id="site-header-nav"' not in html
        assert 'id="site-footer"' not in html


def test_shared_header_links_to_resources_at_the_existing_learn_route():
    header = (FRONTEND / "partials" / "header-nav.html").read_text(encoding="utf-8")
    assert re.search(r'<a\b[^>]*href="/learn/"[^>]*>Recursos</a>', header)


def test_shared_design_system_exposes_opt_in_form_and_button_contract():
    css = (FRONTEND / "assets" / "css" / "components.css").read_text(encoding="utf-8")
    tokens = (FRONTEND / "assets" / "css" / "tokens.css").read_text(encoding="utf-8")
    for selector in (
        ".form-field", ".form-label", ".form-control", ".form-control--lg",
        ".form-control[aria-invalid=\"true\"]", ".form-error",
        ".btn--primary", ".btn--secondary", ".btn--ghost", ".card",
        ".form-control:disabled", ".btn:disabled", ".form-control:focus-visible",
    ):
        assert selector in css, f"Missing shared primitive: {selector}"
    for token in (
        "--control-height:", "--control-height-lg:", "--control-padding-x:",
        "--color-danger:", "--color-danger-border:",
    ):
        assert token in tokens
    assert ":root[data-theme=\"dark\"]" in tokens


def test_shared_controls_do_not_force_a_migration_of_unclassed_number_inputs():
    css = (FRONTEND / "assets" / "css" / "components.css").read_text(encoding="utf-8")
    assert ".form-control {" in css
    assert "input[type=\"number\"]" not in css
    assert "select.form-control" in css
    assert "textarea.form-control" in css
