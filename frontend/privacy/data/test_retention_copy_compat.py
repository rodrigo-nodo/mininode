from pathlib import Path

HERE = Path(__file__).parent
HTML = (HERE / "index.html").read_text()
COMPAT = (HERE / "retention-compat.js").read_text()


def test_completed_retention_copy_is_neutral_not_success_state():
    assert "Conservación ✓" in COMPAT
    assert "heading.textContent = 'Conservación'" in COMPAT
    assert "Revisada en todas las actividades de tu mapa." in COMPAT
    assert "retention-compat.js?v=198e" in HTML


def test_copy_adjustment_survives_async_rerenders():
    assert "MutationObserver" in COMPAT
    assert "observer.observe(root, {childList: true, subtree: true})" in COMPAT
    assert "normalizeCompletedRetentionCopy();" in COMPAT
