from pathlib import Path

HERE = Path(__file__).parent
HTML = (HERE / "index.html").read_text()
ACCESS = (HERE / "access-phase2.js").read_text()


def test_access_controller_loads_before_wizard_and_after_retention_compat():
    assert "access-phase2.js?v=199a" in HTML
    assert HTML.index("retention-compat.js") < HTML.index("access-phase2.js") < HTML.index("wizard.js")


def test_access_uses_existing_backend_contract_without_new_fields():
    assert "answers.access_roles = selected" in ACCESS
    assert "method: 'PATCH'" in ACCESS
    assert "reviewed_access" not in ACCESS
    assert "access_reviewed" not in ACCESS
    assert "access_roles" in ACCESS


def test_access_progress_distinguishes_unasked_from_explicit_unknown():
    assert "(activity.answers?.access_roles || []).length > 0" in ACCESS
    assert "selected.includes('unknown')" in ACCESS
    assert "selected = ['unknown']" in ACCESS


def test_access_question_is_progressive_by_activity():
    assert "Fase 2 · Accesos" in ACCESS
    assert "Actividad ${index + 1} de ${list.length}" in ACCESS
    assert "¿Quién puede acceder a esta información dentro de tu negocio?" in ACCESS
    assert "Selecciona todas las opciones que correspondan." in ACCESS
    assert "Guardar y continuar" in ACCESS
    assert "Guardar y volver a Acciones" in ACCESS


def test_access_keeps_large_catalog_out_of_the_main_screen():
    assert "ACCESS_BY_ACTIVITY" in ACCESS
    assert "Opciones habituales" in ACCESS
    assert "Ver otras opciones" in ACCESS
    assert "catalog?.access_roles" in ACCESS


def test_owner_only_and_unknown_are_exclusive_access_choices():
    assert "['owner_only', 'unknown'].includes(input.value)" in ACCESS
    assert "value=\"owner_only\"" in ACCESS
    assert "value=\"unknown\"" in ACCESS


def test_d03_becomes_a_direct_access_action():
    assert "item.code === 'D03'" in ACCESS
    assert "Accesos" in ACCESS
    assert "Revisar accesos" in ACCESS
    assert "data-phase2-review-access" in ACCESS


def test_access_completion_is_neutral_and_security_is_next():
    assert "Revisada en todas las actividades de tu mapa." in ACCESS
    assert "Seguridad" in ACCESS
    assert "Revisa cómo proteges esta información." in ACCESS
    assert "Comenzar - Próximamente" in ACCESS
    assert "Accesos ✓" not in ACCESS


def test_access_controller_does_not_add_mutation_observer_or_backend_migration():
    assert "MutationObserver" not in ACCESS
    assert "migration" not in ACCESS.lower()
