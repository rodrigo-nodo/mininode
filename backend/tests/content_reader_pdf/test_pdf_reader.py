import hashlib
import io
from types import SimpleNamespace

import pytest
import httpx

from mininode_api.web_inspector.fetcher import WebFetcher
from reportlab.pdfgen import canvas

from mininode_api.content_reader_pdf import PdfReadError, read_pdf_document, read_public_pdf_url


def make_pdf(*pages):
    stream = io.BytesIO()
    pdf = canvas.Canvas(stream)
    for i, lines in enumerate(pages):
        for j, value in enumerate(lines):
            pdf.drawString(72, 760 - j * 24, value)
        if not lines:
            # Materialize an image-only page; a truly blank ReportLab page
            # may not be serialized into the resulting PDF.
            pdf.rect(70, 700, 40, 40, stroke=1, fill=0)
        if i < len(pages) - 1:
            pdf.showPage()
    pdf.save()
    return stream.getvalue()


def test_digital_pdf_preserves_pages_source_hashes_and_locations():
    data = make_pdf(("Politica de privacidad", "Datos personales y derechos"), ("Conservacion y seguridad",))
    doc = read_pdf_document(data, final_url="https://example.cl/policy.pdf")
    assert doc.page_count == 2
    assert [p.number for p in doc.pages] == [1, 2]
    assert "Datos personales y derechos" in doc.pages[0].lines[1].text
    assert "Conservacion y seguridad" in doc.pages[1].lines[0].text
    assert doc.pages[0].lines[0].bbox[0] > 0
    assert doc.file_sha256 == hashlib.sha256(data).hexdigest()
    assert doc.text_sha256 == hashlib.sha256(doc.text.encode()).hexdigest()
    assert doc.character_count == len(doc.text)
    assert doc.truncated is False
    assert doc.extraction_scope == "digital_pdf"


def test_textless_or_mixed_pages_rejected_not_partial():
    for data in (
        make_pdf(("Pagina digital",), ()),
        make_pdf((), ("Pagina digital",)),
        make_pdf((),),
    ):
        with pytest.raises(PdfReadError, match="pdf_page_without_text"):
            read_pdf_document(data)


def test_explicit_size_page_character_and_format_guards():
    data = make_pdf(("Primera pagina",), ("Segunda pagina",))
    for keyword, code in [
        ({"max_bytes": 10}, "pdf_too_large"),
        ({"max_pages": 1}, "pdf_too_many_pages"),
        ({"max_characters": 5}, "pdf_text_too_large"),
    ]:
        with pytest.raises(PdfReadError) as exc:
            read_pdf_document(data, **keyword)
        assert exc.value.code == code
    with pytest.raises(PdfReadError, match="invalid_pdf"):
        read_pdf_document(b"not a PDF")
    for keyword in ({"max_bytes": 0}, {"max_pages": 0}, {"max_characters": 0}):
        with pytest.raises(ValueError):
            read_pdf_document(data, **keyword)


def test_malformed_pdf_rejected():
    with pytest.raises(PdfReadError, match="pdf_parse_failed"):
        read_pdf_document(b"%PDF-broken")


def test_public_adapter_uses_opt_in_pdf_and_fails_closed():
    data = make_pdf(("Documento publico",))
    class FakeFetcher:
        called = None
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def fetch(self, url, urls, *, accept_pdf=False):
            self.called = (url, urls, accept_pdf)
            return SimpleNamespace(pages=[SimpleNamespace(
                error=None, binary_content=data, final_url="https://example.cl/policy.pdf"
            )])
    fake = FakeFetcher()
    result = read_public_pdf_url("https://example.cl/policy.pdf", fetcher_factory=lambda: fake)
    assert fake.called == ("https://example.cl/policy.pdf", ["https://example.cl/policy.pdf"], True)
    assert result.page_count == 1

    class RejectFetcher(FakeFetcher):
        def fetch(self, url, urls, *, accept_pdf=False):
            return SimpleNamespace(pages=[SimpleNamespace(
                error=SimpleNamespace(code="robots_disallowed"), binary_content=None, final_url=None
            )])
    with pytest.raises(PdfReadError, match="robots_disallowed"):
        read_public_pdf_url("https://example.cl/policy.pdf", fetcher_factory=RejectFetcher)


def test_pdf_links_and_page_metadata():
    stream = io.BytesIO()
    c = canvas.Canvas(stream)
    c.drawString(70, 760, "Consultar politica")
    c.linkURL("https://example.cl/legal", (65, 746, 190, 777), relative=0)
    c.save()
    doc = read_pdf_document(stream.getvalue())
    assert len(doc.pages[0].links) == 1
    assert doc.pages[0].links[0].url == "https://example.cl/legal"
    assert doc.pages[0].links[0].page == 1


def test_safe_pdf_fetch_only_when_explicitly_enabled():
    data = make_pdf(("Descarga segura",))
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404, headers={"content-type": "text/plain"})
        return httpx.Response(200, content=data, headers={"content-type": "application/pdf"})
    kwargs = dict(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        resolver=lambda hostname, port: {"93.184.216.34"},
    )
    with WebFetcher(**kwargs) as fetcher:
        denied = fetcher.fetch("https://example.cl/a.pdf", ["https://example.cl/a.pdf"])
        allowed = fetcher.fetch("https://example.cl/a.pdf", ["https://example.cl/a.pdf"], accept_pdf=True)
    assert denied.pages[0].error.code == "unsupported_content_type"
    assert denied.pages[0].binary_content is None
    assert allowed.pages[0].error is None
    assert allowed.pages[0].binary_content == data
    assert allowed.pages[0].html is None


def test_safe_pdf_fetch_respects_robots_and_ssrf():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /blocked.pdf\n", headers={"content-type": "text/plain"})
        return httpx.Response(200, content=make_pdf(("Texto",)), headers={"content-type": "application/pdf"})
    with WebFetcher(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        resolver=lambda hostname, port: {"93.184.216.34"},
    ) as fetcher:
        blocked = fetcher.fetch("https://example.cl/blocked.pdf", ["https://example.cl/blocked.pdf"], accept_pdf=True)
    assert blocked.pages[0].error.code == "robots_disallowed"

    with WebFetcher(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        resolver=lambda hostname, port: {"127.0.0.1"},
    ) as fetcher:
        unsafe = fetcher.fetch("https://example.cl/a.pdf", ["https://example.cl/a.pdf"], accept_pdf=True)
    assert unsafe.pages[0].error.code == "blocked_by_ssrf"


def test_safe_pdf_fetch_rejects_oversized_and_wrong_mime():
    from mininode_api.web_inspector.fetcher import MAX_RESPONSE_BYTES
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404, headers={"content-type": "text/plain"})
        if request.url.path == "/huge.pdf":
            return httpx.Response(200, content=b"x" * (MAX_RESPONSE_BYTES + 1), headers={"content-type": "application/pdf"})
        return httpx.Response(200, content=b"%PDF-fake", headers={"content-type": "text/html"})
    with WebFetcher(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        resolver=lambda hostname, port: {"93.184.216.34"},
    ) as fetcher:
        huge = fetcher.fetch("https://example.cl/huge.pdf", ["https://example.cl/huge.pdf"], accept_pdf=True)
        fake = fetcher.fetch("https://example.cl/fake.pdf", ["https://example.cl/fake.pdf"], accept_pdf=True)
    assert huge.pages[0].error.code == "response_too_large"
    assert fake.pages[0].binary_content is None
    assert fake.pages[0].html is not None


def test_character_limit_includes_page_separator():
    data = make_pdf(("Uno",), ("Dos",))
    doc = read_pdf_document(data)
    assert doc.text == "Uno\n\nDos"
    assert doc.character_count == 8
    assert read_pdf_document(data, max_characters=8).character_count == 8
    with pytest.raises(PdfReadError, match="pdf_text_too_large"):
        read_pdf_document(data, max_characters=7)


def test_two_columns_are_rejected_instead_of_interleaved():
    stream = io.BytesIO()
    p = canvas.Canvas(stream, pagesize=(600, 800))
    for n in range(5):
        p.drawString(40, 720 - n * 25, "Izquierda contenido extenso numero " + str(n))
        p.drawString(345, 720 - n * 25, "Derecha contenido extenso numero " + str(n))
    p.save()
    with pytest.raises(PdfReadError, match="pdf_layout_ambiguous"):
        read_pdf_document(stream.getvalue())


def test_grid_table_preserves_row_column_associations():
    stream = io.BytesIO()
    p = canvas.Canvas(stream, pagesize=(600, 800))
    for x in (40, 280, 560):
        p.line(x, 600, x, 720)
    for y in (600, 640, 680, 720):
        p.line(40, y, 560, y)
    for y, left, right in [
        (692, "Servicio", "Dato personal"),
        (652, "Urgencias", "Contacto"),
        (612, "Imagenologia", "Diagnostico"),
    ]:
        p.drawString(55, y, left)
        p.drawString(295, y, right)
    p.save()
    result = read_pdf_document(stream.getvalue())
    assert len(result.pages[0].tables) == 1
    table = result.pages[0].tables[0]
    assert table.rows == (
        ("Servicio", "Dato personal"),
        ("Urgencias", "Contacto"),
        ("Imagenologia", "Diagnostico"),
    )
    assert [(c.row, c.column, c.text) for c in table.cells] == [
        (0, 0, "Servicio"), (0, 1, "Dato personal"),
        (1, 0, "Urgencias"), (1, 1, "Contacto"),
        (2, 0, "Imagenologia"), (2, 1, "Diagnostico"),
    ]
    assert result.pages[0].blocks[0].kind == "table"


def test_mixed_digital_text_plus_image_is_not_declared_integrity_verified():
    from PIL import Image, ImageDraw
    from reportlab.lib.utils import ImageReader
    stream = io.BytesIO()
    p = canvas.Canvas(stream)
    p.drawString(72, 770, "Encabezado seleccionable")
    image = Image.new("RGB", (200, 50), "white")
    ImageDraw.Draw(image).text((10, 15), "Texto solo como imagen", fill="black")
    p.drawImage(ImageReader(image), 72, 630, width=200, height=50)
    p.save()
    doc = read_pdf_document(stream.getvalue())
    assert doc.pages[0].image_count >= 1
    assert doc.pages[0].extraction_status == "digital_text_with_images"
    assert doc.integrity_status == "unverified_visual_content"
    assert "Texto solo como imagen" not in doc.text


def test_highly_compressed_digital_glyph_bomb_is_rejected():
    stream = io.BytesIO()
    p = canvas.Canvas(stream, pageCompression=1)
    p.setFont("Helvetica", 8)
    for row in range(50):
        p.drawString(30, 760 - row * 14, "0123456789" * 50)
    p.save()
    data = stream.getvalue()
    assert len(data) < 50_000
    with pytest.raises(PdfReadError, match="pdf_too_complex"):
        read_pdf_document(data)


def test_subprocess_timeout_yields_controlled_error(monkeypatch):
    import subprocess
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("pdf-worker", 15)
    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(PdfReadError, match="pdf_processing_timeout"):
        read_pdf_document(make_pdf(("Documento",)))


def test_short_parallel_columns_are_rejected():
    stream = io.BytesIO()
    p = canvas.Canvas(stream, pagesize=(600, 800))
    for n in range(4):
        p.drawString(45, 740 - n * 32, "A" + str(n))
        p.drawString(355, 740 - n * 32, "B" + str(n))
    p.save()
    with pytest.raises(PdfReadError, match="pdf_layout_ambiguous"):
        read_pdf_document(stream.getvalue())


def test_vertically_offset_parallel_columns_are_rejected():
    stream = io.BytesIO()
    p = canvas.Canvas(stream, pagesize=(600, 800))
    for n in range(5):
        p.drawString(40, 740 - n * 36, "Parrafo izquierda numero " + str(n))
        p.drawString(350, 718 - n * 36, "Parrafo derecha numero " + str(n))
    p.save()
    with pytest.raises(PdfReadError, match="pdf_layout_ambiguous"):
        read_pdf_document(stream.getvalue())


def test_narrow_sixteen_point_column_gap_rejected_without_interleaving():
    from reportlab.pdfbase.pdfmetrics import stringWidth

    stream = io.BytesIO()
    p = canvas.Canvas(stream, pagesize=(600, 800))
    left = "Texto izquierdo numero 0"
    right_x = 40 + stringWidth(left, "Helvetica", 12) + 16
    for n in range(5):
        p.drawString(40, 740 - n * 27, left)
        p.drawString(right_x, 740 - n * 27, "Texto derecho numero 0")
    p.save()
    with pytest.raises(PdfReadError, match="pdf_layout_ambiguous"):
        read_pdf_document(stream.getvalue())


def test_numbered_list_keeps_single_reading_order():
    stream = io.BytesIO()
    p = canvas.Canvas(stream, pagesize=(600, 800))
    for n in range(5):
        p.drawString(40, 740 - n * 27, str(n + 1) + ".")
        p.drawString(77, 740 - n * 27, "Elemento de lista con texto normal")
    p.save()
    doc = read_pdf_document(stream.getvalue())
    assert doc.page_count == 1
    assert len(doc.pages[0].lines) == 5
    assert [line.text for line in doc.pages[0].lines] == [
        str(n + 1) + ". Elemento de lista con texto normal" for n in range(5)
    ]


def test_seven_point_parallel_columns_reject_full_document():
    from reportlab.pdfbase.pdfmetrics import stringWidth
    stream = io.BytesIO()
    pdf = canvas.Canvas(stream, pagesize=(600, 800))
    for index in range(5):
        left = f"Izquierda numero {index}"
        right = f"Derecha numero {index}"
        pdf.drawString(40, 730 - index * 27, left)
        pdf.drawString(40 + stringWidth(left, "Helvetica", 12) + 7, 730 - index * 27, right)
    pdf.save()
    with pytest.raises(PdfReadError, match="pdf_layout_ambiguous"):
        read_pdf_document(stream.getvalue())


@pytest.mark.parametrize("markers", [
    ["-", "-", "-", "-", "-"],
    ["a)", "b)", "c)", "d)", "e)"],
])
def test_common_lists_are_read_as_sequential_text(markers):
    stream = io.BytesIO()
    pdf = canvas.Canvas(stream, pagesize=(600, 800))
    for index, marker in enumerate(markers):
        pdf.drawString(40, 730 - index * 27, marker)
        pdf.drawString(75, 730 - index * 27, f"Elemento de lista numero {index}")
    pdf.save()
    document = read_pdf_document(stream.getvalue())
    assert document.page_count == 1
    assert [line.text for line in document.pages[0].lines] == [
        f"{marker} Elemento de lista numero {index}"
        for index, marker in enumerate(markers)
    ]


@pytest.mark.parametrize("markers", [
    ["◦"] * 5,
    ["▪"] * 5,
    ["(a)", "(b)", "(c)", "(d)", "(e)"],
    ["I.", "II.", "III.", "IV.", "V."],
])
def test_unicode_and_roman_lists_keep_unambiguous_reading_order(markers):
    from pathlib import Path
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_file = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    assert font_file.is_file(), "CI must provide a real Unicode font"
    if "MininodeQABullets" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("MininodeQABullets", str(font_file)))
    stream = io.BytesIO()
    pdf = canvas.Canvas(stream, pagesize=(600, 800))
    pdf.setFont("MininodeQABullets", 12)
    for index, marker in enumerate(markers):
        pdf.drawString(40, 730 - index * 27, marker)
        pdf.drawString(86, 730 - index * 27, f"Descripcion del elemento {index}")
    pdf.save()
    doc = read_pdf_document(stream.getvalue())
    assert doc.page_count == 1
    assert [line.text for line in doc.pages[0].lines] == [
        f"{marker} Descripcion del elemento {index}"
        for index, marker in enumerate(markers)
    ]


@pytest.mark.parametrize("gap", [4.0, 3.0])
def test_repeated_close_unruled_fields_are_ambiguous(gap):
    from reportlab.pdfbase.pdfmetrics import stringWidth

    stream = io.BytesIO()
    pdf = canvas.Canvas(stream, pagesize=(600, 800))
    for index in range(5):
        x_left = 40
        x_right = x_left + stringWidth("Ventas", "Helvetica", 12) + gap
        y = 730 - index * 27
        pdf.drawString(x_left, y, "Ventas")
        pdf.drawString(x_right, y, "Costos")
    pdf.save()
    with pytest.raises(PdfReadError, match="pdf_layout_ambiguous"):
        read_pdf_document(stream.getvalue())


def test_single_two_word_sentence_is_not_automatically_two_columns():
    document = read_pdf_document(make_pdf(("Ventas Costos",)))
    assert document.pages[0].lines[0].text == "Ventas Costos"


def test_native_layout_candidates_retain_source_character_provenance():
    data = make_pdf(("Texto de una linea", "Otra linea independiente"))
    document = read_pdf_document(data)
    page = document.pages[0]
    assert page.layout_regions
    assert all(region.page == 1 and region.bbox[2] > region.bbox[0]
               for region in page.layout_regions)
    assert [line.text for line in page.lines] == [
        "Texto de una linea", "Otra linea independiente",
    ]
    assert all(line.source_char_indices for line in page.lines)
    # Provenance refers to positions in the PDF's original character array.
    assert set(page.lines[0].source_char_indices).isdisjoint(
        page.lines[1].source_char_indices
    )
    assert page.structure_tag_error is None or isinstance(page.structure_tag_error, str)


def test_ruled_table_cells_preserve_original_character_references():
    stream = io.BytesIO()
    pdf = canvas.Canvas(stream, pagesize=(600, 800))
    for x in (40, 280, 560):
        pdf.line(x, 600, x, 720)
    for y in (600, 640, 680, 720):
        pdf.line(40, y, 560, y)
    for y, left, right in (
        (692, "Servicio", "Dato"),
        (652, "Formulario", "Nombre"),
        (612, "Consulta", "Correo"),
    ):
        pdf.drawString(55, y, left)
        pdf.drawString(295, y, right)
    pdf.save()
    document = read_pdf_document(stream.getvalue())
    page = document.pages[0]
    table = page.tables[0]
    assert len(table.cells) == 6
    assert all(cell.source_char_indices for cell in table.cells)
    assert len(set(index for cell in table.cells
                   for index in cell.source_char_indices)) == sum(
                       len(cell.source_char_indices) for cell in table.cells
                   )
    assert not set(index for line in page.lines
                   for index in line.source_char_indices).intersection(
                       index for cell in table.cells
                       for index in cell.source_char_indices
                   )


def test_structural_evidence_checks_glyph_coverage_not_semantic_order():
    from mininode_api.content_reader_pdf.structure import source_coverage_counts
    chars = [{"text": "A"}, {"text": " "}, {"text": "B"}]
    line = lambda *items: SimpleNamespace(source_char_indices=tuple(items))
    assert source_coverage_counts(chars, [line(0, 2)], []) == (0, 0)
    assert source_coverage_counts(chars, [line(0)], []) == (1, 0)
    assert source_coverage_counts(chars, [line(0, 2), line(2)], []) == (0, 1)
    document = read_pdf_document(make_pdf(("Una frase digital",)))
    assert document.pages[0].source_coverage_status == "all_nonwhitespace_glyphs_covered"
    assert document.pages[0].repeated_source_refs >= 0
