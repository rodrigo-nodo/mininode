from mininode_api.web_inspector.extractor import extract_page


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
