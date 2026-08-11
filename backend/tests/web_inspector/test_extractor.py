from mininode_api.web_inspector.extractor import NEARBY_TEXT_LIMIT, extract_page


HTML = """
<html><head><title>  Contacto Empresa  </title></head><body>
  <a href="/privacidad?utm_source=test">Política de privacidad</a>
  <a href="https://example.com/privacidad">Política de privacidad</a>
  <a href="javascript:alert('no')">No ejecutar</a>
  <section>
    <p>Los datos serán utilizados para responder la consulta.</p>
    <form action="/enviar" method="post">
      <label for="name">Nombre completo</label><input id="name" name="name" required>
      <label>Correo <input name="email" type="email"></label>
      <select name="topic" aria-label="Tema"><option>Uno</option></select>
      <textarea name="message" placeholder="Mensaje"></textarea>
      <input name="company" aria-label="Empresa">
      <label><input type="checkbox" name="terms"> Acepto las condiciones</label>
      <a href="/privacidad">Privacidad y datos personales</a>
    </form>
  </section>
  <a href="mailto:contacto@example.com">Email</a>
  <a href="tel:+56-2-2345-6789">Teléfono</a>
  <p>Alternativo: ventas@example.com / +56 9 8765 4321</p>
  <div>Usamos cookies. <button>Configurar preferencias de cookies</button></div>
  <img src="http://static.example.com/logo.png">
  <script>window.executed = true</script>
</body></html>
"""


def test_extracts_title_links_and_deduplicates_normalized_urls():
    page, links, *_ = extract_page(HTML, "https://example.com/contacto")

    assert page.title == "Contacto Empresa"
    privacy = [link for link in links if link.url == "https://example.com/privacidad"]
    assert len(privacy) == 1
    assert privacy[0].source_url == "https://example.com/contacto"
    assert all(not link.url.startswith("javascript:") for link in links)


def test_extracts_form_fields_labels_checkbox_and_bounded_context():
    _, _, forms, *_ = extract_page(HTML, "https://example.com/contacto")

    form = forms[0]
    assert form.action == "https://example.com/enviar"
    assert form.method == "post"
    assert [(field.name, field.type, field.label, field.required) for field in form.fields] == [
        ("name", "text", "Nombre completo", True),
        ("email", "email", "Correo", False),
        ("topic", "select", "Tema", False),
        ("message", "textarea", "Mensaje", False),
        ("company", "text", "Empresa", False),
    ]
    assert form.checkboxes[0].name == "terms"
    assert "Acepto las condiciones" in form.checkboxes[0].label
    assert "Los datos serán utilizados" in form.nearby_text
    assert len(form.nearby_text) <= NEARBY_TEXT_LIMIT
    assert form.privacy_links == ["https://example.com/privacidad"]


def test_extracts_contacts_cookie_signals_and_static_mixed_content():
    *_, cookies, contacts, mixed_content = extract_page(
        HTML, "https://example.com/contacto", set_cookie_names=["session", "prefs", "session"]
    )

    values = {(contact.type, contact.value) for contact in contacts}
    assert ("email", "contacto@example.com") in values
    assert ("email", "ventas@example.com") in values
    assert ("phone", "+56-2-2345-6789") in values
    assert ("phone", "+56 9 8765 4321") in values
    assert cookies.detected is True
    assert cookies.set_cookie_names == ["prefs", "session"]
    assert cookies.banner_detected is True
    assert cookies.preferences_detected is True
    assert mixed_content is True


def test_plain_malformed_html_has_no_cookie_or_preference_signal_and_never_executes_script():
    html = "<html><title>Broken</title><body><p>Contenido<script>raise Exception('executed')</script>"
    page, links, forms, cookies, contacts, mixed_content = extract_page(html, "http://example.com/")

    assert page.title == "Broken"
    assert links == []
    assert forms == []
    assert contacts == []
    assert cookies.banner_detected is False
    assert cookies.preferences_detected is False
    assert mixed_content is False
