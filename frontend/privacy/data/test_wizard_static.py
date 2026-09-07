from pathlib import Path

HERE = Path(__file__).parent
HTML = (HERE / "index.html").read_text()
JS = (HERE / "wizard.js").read_text()


def test_accessible_shell_and_privacy_copy():
    assert 'lang="es"' in HTML
    assert 'aria-live="polite"' in HTML
    assert "No pedimos datos personales reales" in JS
    assert "No ingreses nombres, RUT ni datos personales" not in JS
    assert 'type="${type}"' in JS


def test_catalog_and_map_contracts_are_consumed():
    assert "request('/catalog')" in JS
    assert "request('/maps', {method: 'POST'" in JS
    assert "request(`/maps/${token}`)" in JS
    assert "request(`/maps/${token}/activities`)" in JS
    assert "method: 'PATCH'" in JS
    assert "method: 'POST'" in JS


def test_token_is_local_only_and_not_rendered():
    assert "mininode_privacy_data_token" in JS
    assert "localStorage.setItem(TOKEN_KEY, this.token)" in JS
    assert "this.shell(`${this.token}" not in JS


def test_out_of_scope_features_absent():
    lowered = (HTML + JS).lower()
    for word in ("scoring", "recommendations", "r01"):
        assert word not in lowered


def test_errors_are_friendly_and_expired_tokens_removed():
    for status in (404, 410, 422, 503):
        assert str(status) in JS
    assert "localStorage.removeItem(TOKEN_KEY)" in JS
    assert "response.json()" in JS


def test_initial_loading_error_has_one_retry_and_its_own_message():
    assert "withOneInitialRetry" in JS
    retry_body = JS.split("export async function withOneInitialRetry", 1)[1].split("const questions", 1)[0]
    assert retry_body.count("return operation()") == 1
    assert "No pudimos cargar Privacy Data. Intenta nuevamente." in JS
    assert "No pudimos recuperar tu mapa. Intenta nuevamente." in JS
    assert 'data-go="retry-initial"' in JS
    assert "if (go === 'retry-initial') return this.init()" in JS
    initial_catch = JS.split("async init()", 1)[1].split("async run(action)", 1)[0]
    assert "No pudimos guardar los cambios" not in initial_catch


def test_save_errors_keep_their_specific_message():
    assert "No pudimos guardar los cambios. Intenta nuevamente." in JS


def test_minors_and_third_parties_support_uncertainty_in_phase_one():
    assert "¿Podría haber menores de edad entre estas personas?" in JS
    assert "Responde si podría haber menores de edad entre estas personas." in JS
    assert "¿Alguna persona o empresa fuera de tu negocio" in JS
    assert "No estoy seguro" in JS
    assert "has-third-parties" in JS
    assert "answers.third_parties = []" in JS


def test_removal_confirmation_and_contextual_purposes_exist():
    assert "Quitaste una actividad que ya tenía información guardada." in JS
    assert "method: 'DELETE'" in JS
    assert "cancel-removal" in JS
    assert "PURPOSES_BY_ACTIVITY" in JS
    assert "Ver otras opciones" in JS


def test_boolean_recovery_preserves_false_and_pending():
    assert "unansweredBooleanActivities(this.activities)" in JS
    assert "activity.answers.may_include_minors == null" in JS
    assert "activity.answers.has_third_parties == null" in JS
    assert "this.minorsUnanswered = unanswered.minors" in JS
    assert "this.thirdPartiesUnanswered = unanswered.thirdParties" in JS


def test_contextual_people_keeps_catalog_as_source_of_truth():
    assert "PEOPLE_BY_ACTIVITY" in JS
    assert "PEOPLE_BY_INDUSTRY" in JS
    assert "this.catalog.people_categories" in JS
    assert "Opciones habituales" in JS
    assert "Ver otras opciones" in JS


def test_save_does_not_render_before_reading_dom():
    run_body = JS.split("async run(action) {", 1)[1].split("progress(active)", 1)[0]
    assert "this.saving = true; this.render()" not in run_body
    assert "finally { this.saving = false; this.render(); }" in run_body


def test_loading_copy_is_visible_before_and_during_recovery():
    assert "Preparando tu mapa…" in HTML
    assert "Recuperando tu mapa…" in JS


def test_existing_map_is_resumed_from_landing_instead_of_recreated():
    assert "const hasMap = Boolean(this.map && this.token)" in JS
    assert "hasMap ? 'resume' : 'create'" in JS
    assert "this.activities = []; this.selected = []" in JS


def test_data_context_copy_is_plain_language():
    assert "¿Para quién manejas esta información?" in JS
    assert "Esto nos ayuda a distinguir los datos que usas para tu negocio de los que manejas al prestar un servicio a un cliente." in JS
    assert "Para mi negocio" in JS
    assert "Para prestar un servicio a un cliente" in JS
    assert "En ambos casos" in JS
    assert "Selecciona para quién manejas esta información." in JS


def test_phase_one_is_separate_and_preserves_legacy_channels():
    phase_one = JS.split("export const phaseOneQuestions", 1)[1].split("];", 1)[0]
    assert "data_origins" in phase_one
    assert "storage_locations" in phase_one
    assert "data_channels" not in phase_one
    assert "access_roles" not in phase_one
    assert "retention" not in phase_one
    assert "data_channels: []" in JS
    assert "Fase 1 terminada" in JS
    assert "Resumen" in JS and "Mapa" in JS and "Acciones" in JS


def test_new_activities_do_not_silently_confirm_data_context():
    assert "data_context: 'own_operations'" not in JS
    assert "data_context: 'unconfirmed'" in JS
    assert "¿Para quién manejas esta información?" in JS
    assert "{data_context: dataContext}" in JS


def test_loading_keeps_hero_visible_and_supports_debug_timing():
    assert "Ordena cómo tu negocio maneja los datos personales por dentro." in HTML
    assert "Preparando tu mapa…" in HTML
    assert "Recuperando tu mapa…" in JS
    assert "debug" in JS
    assert "[Privacy Data]" in JS


def test_people_options_have_plain_grouping_without_default_fieldset_box():
    assert 'class="pd-people"' in JS


def test_third_parties_and_retention_are_conditionally_interactive():
    assert "data-third-list" in JS
    assert "inert style=\"display:none\"" in JS
    assert "data-retention-fields" in JS
    assert "event.target.value === 'defined'" in JS


def test_finish_shows_automatic_review_and_keeps_editing_available():
    assert "Este es tu primer mapa" in JS
    assert "Revisión del mapa - Próximamente" not in JS
    assert "request(`/maps/${this.token}/review`)" in JS
    assert "reviewMarkup(phaseOneObservations, this.catalog, this.activities" in JS
    assert "Volver y editar mi mapa" in JS
    assert "data-go=\"edit-map\"" in JS


def test_review_and_recovery_load_independently_each_time_wizard_finishes():
    finish_action = JS.split("if (['skip-size', 'save-size'].includes(go))", 1)[1]
    assert "this.reviewObservations = null" in finish_action
    assert "Promise.allSettled([this.loadReview(), this.generateRecoveryLink()])" in finish_action
    assert "retry-review" in JS
    assert "this.generateRecoveryLink()" in finish_action


def test_recovery_link_is_separate_capability_and_uses_url_fragment():
    assert "recoveryTokenFromHash" in JS
    assert "#recover=" in JS
    assert "history.replaceState" in JS
    assert "localStorage.setItem(TOKEN_KEY, recoveryToken)" in JS
    assert "?token=" not in JS


def test_finish_generates_and_can_copy_recovery_link():
    assert "/recovery-link" in JS
    assert "Preparando tu enlace…" in JS
    assert "Reintentar" in JS
    assert "Copiar enlace" in JS
    assert "Quien tenga este enlace podrá acceder al mapa." in JS
    assert "navigator.clipboard.writeText" in JS
