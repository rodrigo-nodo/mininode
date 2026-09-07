from pathlib import Path

HERE = Path(__file__).parent
HTML = (HERE / "index.html").read_text()
SECURITY = (HERE / "security-phase2.js").read_text()


def test_security_controller_is_loaded_before_resume_and_wizard():
    assert "security-phase2.js?v=201a" in HTML
    assert HTML.index("security-phase2.js") < HTML.index("resume-map.js")
    assert HTML.index("security-phase2.js") < HTML.index("wizard.js")


def test_security_uses_existing_backend_contract():
    assert "security_measures" in SECURITY
    assert "answers.security_measures = selected" in SECURITY
    assert "method: 'PATCH'" in SECURITY
    assert "/activities/${activity.id}" in SECURITY
    assert "POST" not in SECURITY


def test_security_flow_is_progressive_by_activity():
    assert "Actividad ${index + 1} de ${list.length}" in SECURITY
    assert "Guardar y continuar" in SECURITY
    assert "Guardar y volver a Acciones" in SECURITY
    assert "Continuar seguridad" in SECURITY
    assert "securityProgress" in SECURITY


def test_security_question_and_plain_language_options_are_catalog_driven():
    assert "¿Qué medidas usas para proteger esta información?" in SECURITY
    assert "catalog?.security_measures" in SECURITY
    assert "Opciones habituales" in SECURITY
    assert "Ver otras medidas" in SECURITY
    assert "Si ninguna opción describe tu situación" in SECURITY


def test_none_and_unknown_are_exclusive():
    assert "EXCLUSIVE_SECURITY = ['none', 'unknown']" in SECURITY
    assert "option.checked = option === input" in SECURITY
    assert "value=\"none\"" in SECURITY
    assert "value=\"unknown\"" in SECURITY


def test_security_review_actions_use_d09_and_d10():
    assert "['D09', 'D10']" in SECURITY
    assert "Revisar seguridad" in SECURITY
    assert "data-phase2-review-security" in SECURITY
    assert "refreshReview" in SECURITY


def test_security_completion_is_neutral_and_rights_is_next():
    assert "Revisada en todas las actividades de tu mapa." in SECURITY
    assert "<h2>Derechos</h2>" in SECURITY
    assert "Siguiente etapa" in SECURITY
    assert "Comenzar - Próximamente" in SECURITY
    assert "eyebrow?.remove()" in SECURITY
