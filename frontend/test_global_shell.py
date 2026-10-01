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


def test_header_has_no_literal_newline_escape_and_has_mobile_menu():
    header = read("partials/header-nav.html")
    assert r"\\n" not in header
    assert 'class="nav-toggle"' in header
    assert 'id="site-mobile-menu"' in header
    include = read("include.js")
    assert "aria-expanded" in include
    assert "Abrir menú" in include


def test_global_head_resolves_versioned_script_urls():
    head = read("assets/js/core-head.js")
    access = read("access/index.html")
    assert "core-head\\.js(?:[?#].*)?$" in head
    assert "core-head.js?v=" in access


def test_clerk_sign_in_follows_mininode_theme():
    app = read("access/app.js")
    styles = read("access/styles.css")
    assert "appearance: signInAppearance()" in app
    assert "theme: 'simple'" in app
    assert "colorBorder:" in app
    assert "socialButtonsBlockButton:" in app
    assert "backgroundColor: dark ?" in app
    assert "borderColor: dark ?" in app
    assert "function mininodeTheme()" in app
    assert "colorInput:" in app
    assert "colorInputBackground" not in app
    clerk_load = app.split("await Clerk.load({", 1)[1].split("Clerk.addListener", 1)[0]
    assert "appearance:" not in clerk_load
    assert ".access-clerk input" not in styles
    assert "color-scheme:light" not in styles


def test_privacy_header_reflects_clerk_session_without_workspace_site_query():
    app = read("privacy/app.js")
    assert "syncPrivacyHeader(Boolean(window.Clerk?.session))" in app
    assert "if (!requestedWorkspaceSiteId) {" in app
    assert "syncPrivacyHeader(Boolean(Clerk.session))" in app
    assert "Clerk.addListener(({ session }) => syncPrivacyHeader(Boolean(session))" in app
    assert "requestedWorkspaceSiteId && window.Clerk?.session" not in app


def test_global_shell_reflects_clerk_session_on_public_pages():
    head = read("assets/js/core-head.js")
    auth = read("assets/js/core-auth.js")
    assert "assets/js/core-auth.js?v=" in head
    assert "Boolean(clerk.session)" in auth
    assert "header-access-link" in auth
    assert "header-sign-out" in auth
    assert "await window.Clerk?.signOut()" in auth
    assert "path.startsWith('/access')" in auth
    assert "path.startsWith('/privacy/')" in auth
    assert "new MutationObserver" in auth
    assert "initializeWhenHeaderReady" in auth
