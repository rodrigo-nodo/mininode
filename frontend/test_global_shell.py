from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_shared_header_owns_global_theme_control():
    header = read("partials/header-nav.html")
    learn = read("learn/index.html")
    assert header.count("data-theme-toggle") == 1
    assert "data-theme-toggle" not in learn
    assert "Productos" in header and "Recursos" in header and "Contacto" in header
    assert 'id="header-access-link"' in header
    assert 'id="header-sign-out"' in header


def test_global_theme_has_dark_tokens_and_shared_loader():
    tokens = read("assets/css/tokens.css")
    head = read("assets/js/core-head.js")
    theme = read("assets/js/core-theme.js")
    assert ':root[data-theme="dark"]' in tokens
    assert "assets/js/core-theme.js" in head
    assert "mininode:includes-loaded" in theme


def test_privacy_policy_uses_document_layout_without_changing_version():
    policy = read("legal/privacy/index.html")
    assert 'class="legal-layout"' in policy
    assert 'class="legal-toc"' in policy
    assert 'class="legal-content"' in policy
    assert "Versión 1.2 · Última actualización: septiembre de 2026." in policy
    assert "Cookies y almacenamiento local" in policy


def test_contact_uses_desktop_layout():
    contact = read("contact/index.html")
    assert 'class="container contact-layout"' in contact
    assert 'class="contact-layout__intro"' in contact
    assert 'class="contact-layout__form"' in contact


def test_header_brand_uses_official_mark():
    header = read("partials/header-nav.html")
    assert 'class="brand-mark"' in header
    assert '/assets/mininode-favicon.svg' in header


def test_learn_readers_only_use_global_theme_control():
    readers = [
        "learn/privacy/index.html",
        "learn/briefs/001-nueva-autoridad-de-datos/index.html",
        "learn/briefs/002-evidencia-de-cumplimiento/index.html",
        "learn/briefs/003-datos-personales/index.html",
        "learn/guides/001-proteccion-de-datos-personales/index.html",
    ]
    for path in readers:
        page = read(path)
        assert "data-theme-toggle" not in page
        assert "assets/js/core-theme.js" not in page
