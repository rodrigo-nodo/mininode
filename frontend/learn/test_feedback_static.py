import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_reader_preserves_markdown_sanitization_and_editable_rating():
    script = (ROOT / "reader.js").read_text()
    assert "window.marked.parse" in script
    assert "window.DOMPurify.sanitize" in script
    assert "method: isUpdate ? 'PATCH' : 'POST'" in script
    assert "star.disabled = true" not in script
    assert "feedback_id" in script
    assert "ebook_id" not in script
    assert "comment: null" not in script
    assert "REQUEST_TIMEOUT_MS = 70000" in script


def test_reader_restores_and_closes_persisted_feedback():
    script = (ROOT / "reader.js").read_text()
    html = (ROOT / "privacy" / "index.html").read_text()
    assert "await request(`/api/learn/feedback/${feedbackId}`)" in script
    assert "response.status === 404" in script
    assert "localStorage.removeItem(STORAGE_KEY)" in script
    assert "JSON.stringify({ feedback_id: id })" in script
    assert "option.checked = option.value === state.topic" in script
    assert "topics.hidden = Boolean(state.topic) && !expandTopics" in script
    assert "renderState({ expandTopics: true })" in script
    assert "+ Agregar un comentario" in html
    assert "✓ Comentario enviado" in html
    assert "state.rating > 3 && !expandComment" in script
    assert "state.rating <= 3" in script
    assert "state.comment !== null" in script
    assert "state.has_comment" not in script


def test_persisted_comment_is_rendered_safely_after_patch_and_restore():
    script = (ROOT / "reader.js").read_text()
    html = (ROOT / "privacy" / "index.html").read_text()
    assert '<p class="learn-comment-value" hidden></p>' in html
    assert "commentValue.textContent = hasComment" in script
    assert "commentValue.innerHTML" not in script
    assert "state.comment = value" in script
    assert "state = await response.json()" in script
    assert "comment.hidden = hasComment" in script
    assert "commentToggle.hidden = hasComment" in script


def test_restore_temporarily_disables_all_feedback_controls():
    script = (ROOT / "reader.js").read_text()
    restore = script[script.index("async function restoreFeedback"):script.index("restoreFeedback();")]
    assert "setControlsDisabled(true)" in restore
    assert "finally" in restore
    assert "setControlsDisabled(false)" in restore
    assert "querySelectorAll('button, input, textarea')" in script


def test_comment_keeps_an_accessible_name_when_visual_label_is_hidden():
    html = (ROOT / "privacy" / "index.html").read_text()
    assert 'aria-label="Comentario opcional"' in html
    assert "¿Qué faltó o qué podría explicarse mejor? <span>Opcional</span>" in html


def test_topics_use_stable_codes_and_theme_styles_remain():
    html = (ROOT / "privacy" / "index.html").read_text()
    css = (ROOT / "learn.css").read_text()
    for code in ("business_data", "website_forms", "files", "policies", "security", "new_law"):
        assert f'value="{code}"' in html
    assert ':root[data-theme="dark"]' in css
    assert "@media (prefers-color-scheme: dark)" in css


def test_proxy_whitelists_feedback_get_and_patch():
    proxy = (ROOT.parent / "functions" / "api" / "[[path]].js").read_text()
    assert "'GET,POST,PATCH,OPTIONS'" in proxy
    assert "learn/feedback" in proxy
    assert "^learn\\/feedback\\/[0-9a-f-]+$" in proxy
    assert "['GET', 'PATCH'].includes" in proxy


def test_catalog_and_brief_reuse_reader_with_content_specific_feedback():
    catalog = (ROOT / "index.html").read_text()
    brief = (ROOT / "briefs" / "001-nueva-autoridad-de-datos" / "index.html").read_text()
    brief_002 = (ROOT / "briefs" / "002-evidencia-de-cumplimiento" / "index.html").read_text()
    brief_003 = (ROOT / "briefs" / "003-datos-personales" / "index.html").read_text()
    script = (ROOT / "reader.js").read_text()
    markdown = (ROOT / "content" / "briefs" / "001-nueva-autoridad-de-datos.md").read_text()
    relationships = (ROOT / "content" / "relationships.json").read_text()

    assert "Lecturas breves de 3 a 5 minutos." in catalog
    assert "Lecturas prácticas de 15 a 25 minutos." in catalog
    assert "Lecturas compactas para profundizar en un tema." in catalog
    assert 'href="/learn/privacy"' in catalog
    assert "MININODE LEARN" not in catalog
    assert "<p>RECURSOS</p>" in catalog
    assert "<title>Recursos - Briefs, Guides y Micro-ebooks | Mininode</title>" in catalog
    assert '<span class="learn-card__duration">4 min</span>' in catalog
    assert '<span class="learn-card__duration">30 min</span>' in catalog
    assert "<li>4 min</li>" not in catalog
    assert "<li>30 min</li>" not in catalog
    assert 'href="/learn/briefs/001-nueva-autoridad-de-datos"' in catalog
    assert 'href="/learn/briefs/002-evidencia-de-cumplimiento"' in catalog
    assert 'href="/learn/briefs/003-datos-personales"' in catalog
    assert 'href="/learn/guides/001-proteccion-de-datos-personales"' in catalog
    assert "Datos personales" in catalog
    assert "La información que una organización no siempre ve" in catalog
    assert "<li>Datos</li>" in catalog
    assert 'data-content-type="brief"' in brief
    assert "<title>Nueva autoridad de datos - Brief 001 | Mininode</title>" in brief
    assert '<a class="learn-back" href="/learn">← Recursos</a>' in brief
    assert "← Learn" not in brief
    assert "Volver a Learn" not in brief
    assert "¿Te resultó útil?" in brief
    assert "learn-comment" not in brief
    assert 'data-content-key="brief-002-evidencia-de-cumplimiento"' in brief_002
    assert 'data-content-type="brief"' in brief_002
    assert "<title>Evidencia de cumplimiento - Brief 002 | Mininode</title>" in brief_002
    assert "¿Te resultó útil?" in brief_002
    assert "learn-comment" not in brief_002
    assert 'data-content-key="brief-003-datos-personales"' in brief_003
    assert 'data-content-type="brief"' in brief_003
    assert 'data-markdown-source="../../content/briefs/003-datos-personales.md"' in brief_003
    assert "<title>Datos personales - Brief 003 | Mininode</title>" in brief_003
    assert "¿Te resultó útil?" in brief_003
    assert brief_003.count('data-rating="') == 5
    assert "learn-comment" not in brief_003
    assert "content_key: CONTENT_KEY" in script
    assert "MININODE BRIEF ${metadata.id}" in script
    assert "metadata + content" not in markdown
    assert "¿Te resultó útil?" not in markdown
    assert '"related": ["001"]' in relationships


def test_guide_reuses_reader_and_preserves_source_content():
    guide = (ROOT / "guides" / "001-proteccion-de-datos-personales" / "index.html").read_text()
    markdown = (ROOT / "content" / "guides" / "001-proteccion-de-datos-personales.md").read_text()
    script = (ROOT / "reader.js").read_text()
    css = (ROOT / "learn.css").read_text()

    assert 'data-content-type="guide"' in guide
    assert 'data-markdown-source="../../content/guides/001-proteccion-de-datos-personales.md"' in guide
    assert guide.count('data-rating="') == 5
    assert markdown.startswith("---\nid: 001\ntype: guide\n")
    assert "title: Protección de datos personales - Una guía para comenzar\n" in markdown
    assert "subtitle: Una introducción práctica" in markdown
    assert "country: CL\n" in markdown
    assert "updated: 2026-08\n" in markdown
    assert "reading_time: 15-20\n" in markdown
    assert "guideHeader(documentSource.metadata)" in script
    guide_header = script[script.index("function guideHeader"):script.index("async function renderRelated")]
    assert "GUIDE ${metadata.id}" in guide_header
    assert "${metadata.reading_time} min · ${country} · Actualizado ${monthName} ${year}" in guide_header
    assert "querySelector" not in guide_header
    assert "textContent" not in guide_header
    assert "<strong>" not in guide_header
    assert "CONTENT_TYPE === 'guide'" in script
    assert "undefined" not in guide_header
    assert "País:" not in markdown
    assert "minutosPaís" not in markdown
    assert markdown.count("## Parte 1") == 1
    assert markdown.count("## Parte 2") == 1
    assert '.learn-reader[data-content-type="guide"] .learn-reader__header h1' in css
    assert '.learn-reader[data-content-type="guide"] > h2' in css
    assert '.learn-reader[data-content-type="guide"] > .learn-reader__header + h2' in css


def test_ebook_uses_resources_navigation_and_normalized_title():
    ebook = (ROOT / "privacy" / "index.html").read_text()

    assert "<title>Privacidad para pequeños negocios - Micro-ebook 001 | Mininode</title>" in ebook
    assert '<a class="learn-back" href="/learn">← Recursos</a>' in ebook
    assert "← Learn" not in ebook
    assert "Volver a Learn" not in ebook


def test_related_briefs_resolve_catalog_slugs_and_ignore_incomplete_entries():
    script = (ROOT / "reader.js").read_text()
    relationships = json.loads((ROOT / "content" / "relationships.json").read_text())
    brief = relationships["briefs"]["001"]
    brief_002 = relationships["briefs"]["002"]
    brief_003 = relationships["briefs"]["003"]

    assert brief["slug"] == "001-nueva-autoridad-de-datos"
    assert brief["title"] == "Nueva autoridad de datos"
    assert brief["subtitle"] == "El nuevo escenario de privacidad en Chile"
    assert brief["related"] == ["002"]
    assert brief_002 == {
        "slug": "002-evidencia-de-cumplimiento",
        "title": "Evidencia de cumplimiento",
        "subtitle": "Cumplir también significa demostrar",
        "related": ["001"],
    }
    assert brief_003 == {
        "slug": "003-datos-personales",
        "title": "Datos personales",
        "subtitle": "La información que una organización no siempre ve",
        "related": [],
    }
    assert '/learn/briefs/${id}' not in script
    assert '/learn/briefs/${item.slug}' in script
    assert "catalog[id]" in script
    assert "typeof item.slug === 'string'" in script
    assert "typeof item.title === 'string'" in script
    assert "typeof item.subtitle === 'string'" in script
    assert "if (!related.length) return" in script


def test_brief_related_presentation_and_official_sources():
    css = (ROOT / "learn.css").read_text()
    markdown = (ROOT / "content" / "briefs" / "002-evidencia-de-cumplimiento.md").read_text()

    assert ".learn-related ul { list-style: none" in css
    assert ".learn-related strong { display: block; }" in css
    assert ".learn-related span { display: block; }" in css
    assert ".learn-related span { font-style: italic;" in css
    assert ".learn-feedback--brief { margin: 56px 0 0;" in css
    assert "https://www.bcn.cl/leychile/navegar?idNorma=1209272" in markdown
    assert "https://www.bcn.cl/leychile/" in markdown


def test_brief_003_has_expected_metadata_and_content():
    markdown = (ROOT / "content" / "briefs" / "003-datos-personales.md").read_text()

    assert markdown.startswith("---\nid: 003\ntype: brief\n")
    assert "title: Datos personales\n" in markdown
    assert "subtitle: La información que una organización no siempre ve\n" in markdown
    assert "  - privacidad\n  - datos\n" in markdown
    assert "country: CL\nupdated: 2026-08\nreading_time: 4\n---\n" in markdown
    assert "Los datos personales forman parte de la operación cotidiana" in markdown
    assert "https://www.bcn.cl/leychile/Navegar?idNorma=1209272" in markdown
