from pathlib import Path

HERE = Path(__file__).parent
HTML = (HERE / "index.html").read_text()
RIGHTS = (HERE / "rights-phase2.js").read_text()


def test_rights_controller_is_loaded_before_resume_and_wizard():
    assert "rights-phase2.js?v=203a" in HTML
    assert HTML.index("rights-phase2.js") < HTML.index("resume-map.js")
    assert HTML.index("rights-phase2.js") < HTML.index("wizard.js")


def test_rights_uses_existing_backend_contract():
    assert "rights_handling" in RIGHTS
    assert "answers.rights_handling = selected" in RIGHTS
    assert "method: 'PATCH'" in RIGHTS
    assert "/activities/${activity.id}" in RIGHTS
    assert "POST" not in RIGHTS


def test_rights_flow_is_progressive_by_activity():
    assert "Actividad ${index + 1} de ${list.length}" in RIGHTS
    assert "Guardar y continuar" in RIGHTS
    assert "Guardar y volver a Acciones" in RIGHTS
    assert "Continuar derechos" in RIGHTS
    assert "rightsProgress" in RIGHTS


def test_rights_question_is_single_choice_and_catalog_driven():
    assert "Si una persona te pide acceder, corregir o eliminar sus datos, ¿sabes cómo responder?" in RIGHTS
    assert "catalog?.rights_handling" in RIGHTS
    assert 'type="radio"' in RIGHTS
    assert 'name="rights-handling"' in RIGHTS


def test_rights_review_actions_use_d11_d12_d13():
    assert "['D11', 'D12', 'D13']" in RIGHTS
    assert "Revisar derechos" in RIGHTS
    assert "data-phase2-review-rights" in RIGHTS
    assert "refreshReview" in RIGHTS


def test_rights_completion_is_neutral_and_closes_phase_two_review():
    assert "Revisada en todas las actividades de tu mapa." in RIGHTS
    assert "Revisión de Fase 2 terminada" in RIGHTS
    assert "Revisaste Conservación, Accesos, Seguridad y Derechos." in RIGHTS
    assert "Las acciones pendientes siguen disponibles arriba." in RIGHTS
    assert "Siguiente etapa" in RIGHTS


def test_unasked_rights_is_distinct_from_explicit_answers():
    assert "activity.answers?.rights_handling != null" in RIGHTS
    assert "activity.answers?.rights_handling == null" in RIGHTS
