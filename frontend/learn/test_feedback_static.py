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
