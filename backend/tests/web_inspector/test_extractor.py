from mininode_api.web_inspector.extractor import CONTENT_TEXT_LIMIT, extract_page


def test_extracts_static_page_observations_without_executing_scripts():
    html = """
    <html><head><title> Demo </title><script>cookie; window.evil()</script></head><body>
      <a href="/about">About</a><a href="https://example.com/about">Duplicate</a>
      <a href="mailto:hello@example.com">Email</a><a href="tel:+56 9 1234 5678">Phone</a>
      Contacto: visible@example.org / +56 2 2345 6789
      <form action="/signup" method="post">
        <p>Formulario de registro con información acotada.</p>
        <label for="name">Nombre</label><input id="name" name="name" required>
        <label>Correo <input name="email" type="email"></label>
        <select name="country" aria-label="País"><option>Chile</option></select>
        <textarea name="message" placeholder="Mensaje"></textarea>
        <label><input type="checkbox" name="updates"> Newsletter</label>
        <input type="hidden" name="token">
        <a href="/privacidad">Política de privacidad</a>
      </form>
      <div>Usamos cookies. <button>Configuración de cookies</button></div>
      <img src="http://assets.example/image.png">
    </body></html>
    """
    result = extract_page(html, "https://example.com/")

    assert result.title == "Demo"
    assert [(link.url, link.text) for link in result.links].count(("https://example.com/about", "About")) == 1
    form = result.forms[0]
    assert form.action == "https://example.com/signup"
    assert form.method == "post"
    assert [(field.name, field.type, field.label, field.required) for field in form.fields] == [
        ("name", "text", "Nombre", True),
        ("email", "email", "Correo", False),
        ("country", "select", "País", False),
        ("message", "textarea", "Mensaje", False),
    ]
    assert [(item.name, item.label) for item in form.checkboxes] == [("updates", "Newsletter")]
    assert len(form.nearby_text) <= 500
    assert form.privacy_links[0].url == "https://example.com/privacidad"
    assert {contact.email for contact in result.contacts if contact.email} == {"hello@example.com", "visible@example.org"}
    assert len([contact for contact in result.contacts if contact.phone]) == 2
    assert result.banner_detected is True
    assert result.preferences_detected is True
    assert result.mixed_content is True


def test_malformed_html_is_accepted_and_cookie_in_script_is_not_visible():
    result = extract_page("<title>Broken</title><form><input aria-label='Value'><script>we use cookies", "http://example.com")
    assert result.title == "Broken"
    assert result.forms[0].fields[0].label == "Value"
    assert result.banner_detected is False


def test_form_uses_only_its_nearest_container_as_context():
    html = """
    <section>
      <form><input name="email"><a href="/privacidad">Privacidad</a></form>
      <p>Al enviar este formulario se tratarán sus datos.
        <a href="/privacidad">Política de privacidad</a>
      </p>
    </section>
    <section><a href="/privacy-far">Privacy lejana</a></section>
    """

    form = extract_page(html, "https://example.com/contacto").forms[0]

    assert "Al enviar este formulario" in form.nearby_text
    assert len(form.nearby_text) <= 500
    assert [link.url for link in form.privacy_links] == ["https://example.com/privacidad"]


def test_content_text_prefers_clean_main_without_changing_visible_or_forms():
    html = """
    <header>Nombre Apellido Correo</header><nav>Productos Contacto Cookies</nav>
    <form><label for="email">Correo electrónico</label><input id="email" name="email"></form>
    <main><h1>Política de Privacidad</h1><p>Tratamos datos personales para prestar nuestros servicios.</p></main>
    <footer>contacto@example.com Cookies Terceros Seguridad</footer>
    """

    result = extract_page(html, "https://example.com/privacidad")

    assert "Nombre Apellido Correo" in result.visible_text
    assert "contacto@example.com" in result.visible_text
    assert result.forms[0].fields[0].label == "Correo electrónico"
    assert result.content_text == (
        "Política de Privacidad Tratamos datos personales para prestar nuestros servicios."
    )


def test_content_text_uses_substantive_article_then_clean_div_fallback():
    article = extract_page(
        "<nav>Ruido de navegación</nav><article><h1>Aviso de privacidad</h1>"
        "<p>Este documento explica cómo tratamos información personal.</p></article>",
        "https://example.com/legal",
    )
    legacy = extract_page(
        "<body><nav>Menú extenso</nav><div>Política de privacidad que explica el tratamiento "
        "de datos personales y sus finalidades.</div><footer>Contacto</footer></body>",
        "https://example.com/legal",
    )

    assert article.content_text == (
        "Aviso de privacidad Este documento explica cómo tratamos información personal."
    )
    assert "Menú extenso" not in legacy.content_text
    assert "tratamiento de datos personales" in legacy.content_text


def test_content_text_extends_beyond_legacy_visible_text_limit_but_is_bounded():
    prefix = "Información general sobre nuestra política. " * 120
    late_signals = (
        "El tratamiento se basa en su consentimiento. Puede revocar el consentimiento "
        "en cualquier momento. Derechos, conservación y reclamo ante la autoridad."
    )
    result = extract_page(
        f"<main><h1>Política de privacidad</h1><p>{prefix}</p><p>{late_signals}</p></main>",
        "https://example.com/privacidad",
    )

    assert len(result.visible_text) == 4000
    assert "revocar el consentimiento" not in result.visible_text
    assert "revocar el consentimiento" in result.content_text
    assert len(result.content_text) <= CONTENT_TEXT_LIMIT
