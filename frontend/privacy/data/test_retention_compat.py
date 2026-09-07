from pathlib import Path

HERE = Path(__file__).parent
HTML = (HERE / "index.html").read_text()
COMPAT = (HERE / "retention-compat.js").read_text()


def test_retention_compat_loads_before_phase_two_wizard():
    assert 'retention-compat.js?v=198c' in HTML
    assert HTML.index('retention-compat.js?v=198c') < HTML.index('wizard.js?v=198a')


def test_retention_compat_keeps_current_backend_contract():
    assert "delete retention.reviewed" in COMPAT
    assert "choice === 'not_defined' ? 'unknown' : choice" in COMPAT
    assert "__mininode_retention_v2__:" in COMPAT


def test_retention_compat_restores_phase_two_state_from_persisted_answers():
    assert "retention.reviewed = true" in COMPAT
    assert "reviewedActivityIds.add" in COMPAT
    assert "['D01', 'D02']" in COMPAT


def test_retention_catalog_adds_explicit_not_defined_choice_in_frontend():
    assert "Sí, tengo un plazo definido" in COMPAT
    assert "code: 'not_defined'" in COMPAT
    assert "label: 'No lo tengo definido'" in COMPAT
