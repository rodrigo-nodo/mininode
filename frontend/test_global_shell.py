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
    assert 'id="header-auth-control"' in header
    assert header.count('id="header-auth-control"') == 1
    assert 'href="/access/"' in header
    assert 'id="header-access-link"' not in header
    assert 'id="header-sign-out"' not in header


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
    auth = read("assets/js/core-auth.js")
    assert "window.MininodeAuth = api" in auth
    assert "mountSignIn(node, options = {})" in auth
    assert ".access-clerk input" not in styles
    assert "color-scheme:light" not in styles


def test_privacy_web_consumes_shared_mininode_auth():
    app = read("privacy/app.js")
    assert "waitForMininodeAuth" in app
    assert "auth.getToken()" in app
    assert "fetch('/api/access/context'" in app
    assert "Clerk." not in app
    assert "window.Clerk" not in app
    assert "fetch('/clerk-config'" not in app
    assert "@clerk/" not in app



def test_global_shell_owns_identity_session_and_header_state():
    head = read("assets/js/core-head.js")
    auth = read("assets/js/core-auth.js")
    assert "assets/js/core-auth.js?v=" in head
    assert "window.MininodeAuth = api" in auth
    assert "async getToken()" in auth
    assert "async signOut()" in auth
    assert "subscribe(listener" in auth
    assert "mountSignIn(node, options = {})" in auth
    assert "header-auth-control" in auth
    assert "Cerrar sesión" in auth
    assert "Acceder a Mininode" in auth
    assert "window.Clerk.addListener" in auth
    assert "fetch('/clerk-config'" in auth
    assert "@clerk/clerk-js@6" in auth
    assert "path.startsWith(" not in auth
    assert "new MutationObserver" in auth



def test_all_shell_pages_version_global_head_loader():
    pages = [
        "index.html",
        "contact/index.html",
        "learn/index.html",
        "learn/privacy/index.html",
        "learn/briefs/001-nueva-autoridad-de-datos/index.html",
        "learn/briefs/002-evidencia-de-cumplimiento/index.html",
        "learn/briefs/003-datos-personales/index.html",
        "learn/guides/001-proteccion-de-datos-personales/index.html",
        "legal/privacy/index.html",
        "privacy/index.html",
        "privacy/data/index.html",
        "access/index.html",
    ]
    for path in pages:
        page = read(path)
        assert "core-head.js?v=282i" in page


def test_account_uses_standard_shared_shell_without_hiding_public_nav():
    access = read("access/index.html")
    app = read("access/app.js")
    assert 'data-include="../partials/header-nav.html"' in access
    assert 'data-include="../partials/footer.html"' in access
    assert 'data-mininode-auth-ui="clerk"' in access
    assert "nav > a:not(#header-access-link)" not in app
    assert "waitForMininodeAuth" in app
    assert "mininodeAuth.getToken()" in app
    assert "Clerk." not in app
    assert "window.Clerk" not in app
    assert "fetch('/clerk-config'" not in app
    assert "@clerk/" not in app


def test_access_styles_do_not_hide_shared_shell_navigation():
    styles = read("access/styles.css")
    assert "[hidden] { display: none !important; }" not in styles
    assert ".mobile-menu[hidden]" not in styles


def test_privacy_data_uses_global_auth_shell():
    auth = read("assets/js/core-auth.js")
    data = read("privacy/data/index.html")
    assert "core-head.js?v=282i" in data
    assert "path.startsWith(" not in auth


def test_products_do_not_own_clerk_runtime():
    auth = read("assets/js/core-auth.js")
    product_apps = [
        read("access/app.js"),
        read("privacy/app.js"),
    ]
    assert "fetch('/clerk-config'" in auth
    assert "@clerk/clerk-js@6" in auth
    for app in product_apps:
        assert "fetch('/clerk-config'" not in app
        assert "@clerk/" not in app
        assert "Clerk." not in app
        assert "window.Clerk" not in app


def test_mobile_shell_uses_atomic_auth_control_and_stays_full_width():
    styles = read("styles.css")
    header = read("partials/header-nav.html")
    auth = read("assets/js/core-auth.js")
    assert ".header,.footer{width:100%}" in styles
    assert header.count('id="header-auth-control"') == 1
    assert "control.textContent = signedIn ? 'Cerrar sesión' : 'Acceder'" in auth


def test_signed_out_auth_control_keeps_native_access_navigation():
    header = read("partials/header-nav.html")
    auth = read("assets/js/core-auth.js")
    assert '<a id="header-auth-control"' in header
    assert 'href="/access/"' in header
    assert "if (!api.isSignedIn()) return;" in auth
    assert "event.preventDefault()" in auth


def test_workspace_uses_standard_shell_layout_and_resyncs_auth():
    styles = read("access/styles.css")
    auth = read("assets/js/core-auth.js")
    access = read("access/index.html")
    assert "display: flex; flex-direction: column" not in styles
    assert "access-page .access-main { flex: 1; }" not in styles
    assert "syncHeader(Boolean(currentSession))" in auth
    assert "core-head.js?v=282i" in access
    assert "./styles.css?v=282e" in access
    assert "./app.js?v=282h" in access
