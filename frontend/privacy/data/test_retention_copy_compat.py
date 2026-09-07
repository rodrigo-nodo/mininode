from pathlib import Path

HERE = Path(__file__).parent
HTML = (HERE / "index.html").read_text()
COMPAT = (HERE / "retention-compat.js").read_text()


def test_completed_retention_copy_is_neutral_not_success_state():
    assert "Conservación ✓" in COMPAT
    assert "heading.textContent = 'Conservación'" in COMPAT
    assert "Revisada en todas las actividades de tu mapa." in COMPAT
    assert "retention-compat.js?v=198d" in HTML


def test_copy_adjustment_does_not_use_mutation_observer():
    assert "MutationObserver" not in COMPAT
