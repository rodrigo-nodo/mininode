import hashlib
from types import SimpleNamespace

import pytest

from mininode_api.content_reader import (
    ContentReadError, read_html_document, read_public_html_url,
    MAX_DOCUMENT_NODES, MAX_DOM_DEPTH,
)


def test_preserves_content_after_legacy_limit_and_document_order():
    filler = "A" * 14_000
    html = f"""<html><head><title>Política</title></head><body>
    <nav>Inicio</nav><main><h1>Política de privacidad</h1>
    <p>Texto con <strong>énfasis</strong> y <a href='/derechos'>derechos</a>.</p>
    <p>{filler}</p><h2>Menores</h2>
    <p>EDAD CLARAMENTE MENCIONADA</p>
    <ul><li>Primera condición</li><li>Segunda condición</li></ul></main>
    <footer>(Agrega información de contacto relevante)</footer>
    <script>alert('NO_PUBLICAR')</script><style>NO_TEXTO_CSS</style>
    </body></html>"""
    doc = read_html_document(
        html, "https://example.cl/privacidad", requested_url="https://example.cl/p",
    )
    assert doc.title == "Política"
    assert doc.requested_url == "https://example.cl/p"
    assert doc.final_url == "https://example.cl/privacidad"
    assert doc.text.index("Inicio") < doc.text.index("Política de privacidad")
    assert "Texto con énfasis y derechos." in doc.text
    assert doc.text.index("Menores") > 12_000
    assert "EDAD CLARAMENTE MENCIONADA" in doc.text
    assert "(Agrega información de contacto relevante)" in doc.text
    assert "- Primera condición" in doc.text
    assert "NO_PUBLICAR" not in doc.text and "NO_TEXTO_CSS" not in doc.text
    assert doc.links[0].url == "https://example.cl/derechos"
    assert doc.content_sha256 == hashlib.sha256(doc.text.encode("utf-8")).hexdigest()
    assert doc.character_count == len(doc.text)
    assert doc.truncated is False and doc.extraction_scope == "static_html"


def test_oversized_document_fails_instead_of_silent_truncation():
    with pytest.raises(ContentReadError, match="document_too_large"):
        read_html_document(
            "<body><p>" + "x" * 200 + "</p></body>",
            "https://example.cl", max_characters=100,
        )


def test_empty_or_script_only_document_fails():
    with pytest.raises(ContentReadError, match="empty_document"):
        read_html_document(
            "<html><body><script>javascript_only()</script></body></html>",
            "https://example.cl",
        )


def test_header_footer_form_table_and_nested_links_are_preserved():
    doc = read_html_document(
        "<header>Encabezado legal</header><form><p>Consentimiento</p></form>"
        "<table><tr><th>Tratamiento</th><th>Plazo</th></tr>"
        "<tr><td>Datos</td><td>12 meses</td></tr></table>"
        "<footer>Contacto de privacidad</footer>"
        "<a href='/visible'>Visible</a>"
        "<div hidden><a href='/hidden'>Oculto</a></div>",
        "https://example.cl",
    )
    for expected in ("Encabezado legal", "Consentimiento", "Tratamiento",
                     "Plazo", "12 meses", "Contacto de privacidad"):
        assert expected in doc.text
    assert [link.url for link in doc.links] == ["https://example.cl/visible", "https://example.cl/hidden"]


def test_url_adapter_reuses_existing_fetcher_and_surfaces_errors():
    calls = []

    class FakeFetcher:
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def fetch(self, target, candidates):
            calls.append((target, candidates))
            return SimpleNamespace(pages=[SimpleNamespace(
                error=None, html="<body><p>Texto íntegro.</p></body>",
                final_url="https://example.cl/policy",
            )])

    doc = read_public_html_url(
        "https://example.cl/privacy", fetcher_factory=FakeFetcher,
    )
    assert calls == [("https://example.cl/privacy", ["https://example.cl/privacy"])]
    assert doc.requested_url == "https://example.cl/privacy"
    assert doc.final_url == "https://example.cl/policy"
    assert doc.text == "Texto íntegro."

    class ErrorFetcher(FakeFetcher):
        def fetch(self, target, candidates):
            return SimpleNamespace(pages=[SimpleNamespace(
                error=SimpleNamespace(code="robots_disallowed"),
                html=None, final_url=None,
            )])

    with pytest.raises(ContentReadError, match="robots_disallowed"):
        read_public_html_url(
            "https://example.cl/privacy", fetcher_factory=ErrorFetcher,
        )


def test_comments_and_hidden_html_are_excluded():
    doc = read_html_document(
        "<body><!-- secret --><p>Visible</p>"
        "<p hidden>Oculto</p><div aria-hidden='true'>No visible</div>"
        "<p>Final</p></body>", "https://example.cl",
    )
    assert "Visible" in doc.text and "Final" in doc.text
    assert "Oculto" in doc.text and "No visible" in doc.text
    assert "secret" not in doc.text


def test_inline_boundaries_use_html_structure_not_capitalization():
    doc = read_html_document(
        "<body><p>e<strong>Mail</strong> i<strong>Phone</strong> "
        "anti<strong>fraude</strong></p>"
        "<p>abc<span>revisa</span> ABC<span>Revisa</span></p>"
        "<p>Mis compras<span>Haz seguimiento</span></p>"
        "<p>Mi Tarjeta abc<span>Revisa tus movimientos</span></p></body>",
        "https://example.cl",
    )
    assert "eMail" in doc.text
    assert "iPhone" in doc.text
    assert "antifraude" in doc.text
    assert "abcrevisa" in doc.text
    assert "ABCRevisa" in doc.text
    assert "Mis comprasHaz seguimiento" in doc.text
    assert "Mi Tarjeta abcRevisa tus movimientos" in doc.text


def test_hidden_and_aria_hidden_static_text_is_retained():
    doc = read_html_document(
        "<body><p>Visible</p><span hidden>Texto hidden</span>"
        "<span aria-hidden='true'>Texto accesibilidad</span>"
        "<script>NO_JS</script><style>NO_CSS</style></body>",
        "https://example.cl",
    )
    assert "Texto hidden" in doc.text
    assert "Texto accesibilidad" in doc.text
    assert "NO_JS" not in doc.text
    assert "NO_CSS" not in doc.text


def test_links_and_punctuation_are_not_semantically_rewritten():
    doc = read_html_document(
        "<body><p>Consulta <a href='/p'>política</a>.</p>"
        "<p>anti<strong>fraude</strong>, datos: 12 meses.</p></body>",
        "https://example.cl",
    )
    assert "Consulta política." in doc.text
    assert "antifraude, datos: 12 meses." in doc.text
    assert doc.links[0].url == "https://example.cl/p"


def test_abc_real_html_span_label_followed_by_raw_text():
    doc = read_html_document(
        "<body><p><a href='/seguimiento'><span>Mis compras</span>"
        "Haz seguimiento</a></p><p><a href='/tarjeta'>"
        "<span>Mi Tarjeta abc</span>Revisa tus movimientos</a></p></body>",
        "https://example.cl",
    )
    assert "Mis comprasHaz seguimiento" in doc.text
    assert "Mi Tarjeta abcRevisa tus movimientos" in doc.text
    assert [link.url for link in doc.links] == [
        "https://example.cl/seguimiento", "https://example.cl/tarjeta",
    ]

def test_exact_dom_fragments_are_primary_fidelity_contract():
    doc = read_html_document(
        "<body><a href='/track'><span>Mis compras</span>Haz seguimiento</a>"
        "<p>anti<span>virus</span> <span>e</span>Mail "
        "<a href='/web'>web</a>site <time>20</time>26</p>"
        "<p hidden aria-hidden='true'>¿Quién?  ¡Sí! &amp; más.</p></body>",
        "https://example.cl/",
    )
    assert doc.source_text == (
        "Mis comprasHaz seguimiento"
        "antivirus eMail website 2026"
        "¿Quién?  ¡Sí! & más."
    )
    assert [n.text for n in doc.nodes if n.kind == "text"] == [
        "Mis compras", "Haz seguimiento", "anti", "virus", " ", "e",
        "Mail ", "web", "site ", "20", "26", "¿Quién?  ¡Sí! & más.",
    ]
    assert doc.source_sha256 == hashlib.sha256(doc.source_text.encode()).hexdigest()
    assert doc.source_character_count == len(doc.source_text)
    assert [n.href for n in doc.nodes if n.kind == "element" and n.href] == [
        "https://example.cl/track", "https://example.cl/web",
    ]
    assert any(n.hidden and n.aria_hidden for n in doc.nodes)
    assert doc.text.startswith("Mis comprasHaz seguimiento")


def test_exact_punctuation_and_spacing_remain_in_source_nodes():
    doc = read_html_document(
        "<body><p>Uno,  dos.<em>¡Tres!</em></p><p>A &amp; B</p></body>",
        "https://example.cl",
    )
    assert doc.source_text == "Uno,  dos.¡Tres!A & B"
    assert "Uno, dos.¡Tres!" in doc.text


def test_dom_node_limit_is_explicit_and_inclusive():
    html = "<body><p>texto</p></body>"  # body, p, text
    doc = read_html_document(html, "https://example.cl", max_nodes=3)
    assert len(doc.nodes) == 3
    with pytest.raises(ContentReadError) as error:
        read_html_document(html, "https://example.cl", max_nodes=2)
    assert error.value.code == "document_too_complex"


def test_empty_elements_cannot_bypass_dom_node_limit():
    html = "<body>" + "<span></span>" * 250 + "<p>texto</p></body>"
    with pytest.raises(ContentReadError, match="document_too_complex"):
        read_html_document(html, "https://example.cl", max_nodes=100)


def test_dom_depth_limit_rejects_deep_nesting_without_recursion_error():
    html = "<body>" + "<div>" * 1100 + "texto" + "</div>" * 1100 + "</body>"
    with pytest.raises(ContentReadError) as error:
        read_html_document(html, "https://example.cl", max_depth=128)
    assert error.value.code == "document_too_complex"


def test_dom_depth_boundary_and_invalid_limits():
    doc = read_html_document(
        "<body><div><p>texto</p></div></body>",
        "https://example.cl", max_depth=3,
    )
    assert doc.source_text == "texto"
    with pytest.raises(ContentReadError, match="document_too_complex"):
        read_html_document(
            "<body><div><p>texto</p></div></body>",
            "https://example.cl", max_depth=2,
        )
    for kwargs in ({"max_nodes": 0}, {"max_depth": 0}):
        with pytest.raises(ValueError):
            read_html_document("<body>texto</body>", "https://example.cl", **kwargs)


def test_dom_defaults_are_bounded():
    assert MAX_DOCUMENT_NODES == 50_000
    assert MAX_DOM_DEPTH == 128
