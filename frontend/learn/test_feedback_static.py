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


def test_topics_use_stable_codes_and_theme_styles_remain():
    html = (ROOT / "privacy" / "index.html").read_text()
    css = (ROOT / "learn.css").read_text()
    for code in ("business_data", "website_forms", "files", "policies", "security", "new_law"):
        assert f'value="{code}"' in html
    assert ':root[data-theme="dark"]' in css
    assert "@media (prefers-color-scheme: dark)" in css


def test_proxy_whitelists_feedback_and_patch():
    proxy = (ROOT.parent / "functions" / "api" / "[[path]].js").read_text()
    assert "'GET,POST,PATCH,OPTIONS'" in proxy
    assert "learn/feedback" in proxy
    assert "^learn\\/feedback\\/[0-9a-f-]+$" in proxy
