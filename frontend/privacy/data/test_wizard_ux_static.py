from pathlib import Path

HERE = Path(__file__).parent
HTML = (HERE / "index.html").read_text()
CSS = (HERE / "wizard.css").read_text()
JS = (HERE / "wizard.js").read_text()


def test_phase_one_assets_are_cache_busted_without_auxiliary_ux_assets():
    assert "wizard.css?v=198a" in HTML
    assert "wizard.js?v=198a" in HTML
    assert "wizard-ux.js" not in HTML
    assert "wizard-tune.css" not in HTML


def test_activity_context_has_three_explicit_levels_directly_in_wizard():
    assert "Actividad ${this.activityIndex + 1} de ${this.selected.length}" in JS
    assert "Pregunta ${question} de ${questions.length}" in JS
    assert "pd-activity-context__name" in JS
    assert ".pd-activity-context__name" in CSS


def test_saved_maps_and_new_maps_keep_progressive_microquestions():
    assert 'personal_data_types"]:not(:has(input:checked)) + .pd-micro-question' in CSS
    assert 'data_origins"]:not(:has(input:checked)) + .pd-micro-question' in CSS


def test_microquestions_are_visually_secondary_without_dom_mutation_layer():
    assert "Un detalle más" in JS
    assert "pd-micro-question--secondary" in JS
    assert ".pd-micro-question--secondary" in CSS
    assert ".pd-micro-question__eyebrow" in CSS
    assert "MutationObserver" not in JS


def test_data_context_uses_plain_business_language_directly():
    assert "¿Para quién manejas esta información?" in JS
    assert "Esto nos ayuda a distinguir los datos que usas para tu negocio de los que manejas al prestar un servicio a un cliente." in JS
    assert "Para mi negocio" in JS
    assert "Para prestar un servicio a un cliente" in JS
    assert "En ambos casos" in JS
    assert 'name="data-context"' in JS


def test_idle_saved_status_is_not_rendered():
    assert "this.saved" not in JS
    assert "pd-save" not in CSS


def test_review_topics_are_rendered_with_final_hierarchy_directly():
    assert "pd-review-item__topic" in JS
    assert "pd-review-item__action" in JS
    assert ".pd-review-group h3" in CSS
    assert ".pd-review-item__topic" in CSS


def test_cleanup_does_not_repeat_catalog_or_activity_reads_for_header():
    assert "loadActivityContext" not in JS
    assert "activityContextPromise" not in JS


def test_correcting_a_selection_clears_the_visible_validation_error():
    assert "this.error = '';" in JS
    assert "this.root.querySelector('.pd-error')?.remove();" in JS


def test_summary_remains_phase_one_while_actions_can_include_conservation():
    assert "phaseOneObservations" in JS
    assert "['D04', 'D05', 'D06', 'D07', 'D08']" in JS
    assert "actionObservations" in JS
    assert "['D01', 'D02', 'D04', 'D05', 'D06', 'D07', 'D08']" in JS
    action_filter = JS.split("const actionObservations", 1)[1].split(";", 1)[0]
    assert "D03" not in action_filter


def test_summary_map_and_actions_are_real_result_views():
    assert 'data-go="result-summary"' in JS
    assert 'data-go="result-map"' in JS
    assert 'data-go="result-actions"' in JS
    assert "this.resultView === 'map'" in JS
    assert "this.resultView === 'actions'" in JS
    assert "mapFlowMarkup(this.catalog, this.activities)" in JS
    assert "actionsMarkup(actionObservations, this.catalog, this.activities" in JS
    assert "Acciones - Próximamente" not in JS
    assert '<nav class="pd-result-nav"' in JS
    assert ".pd-result-nav button.active" in CSS


def test_actions_view_maps_findings_to_direct_questions_and_phase_two():
    assert "export function actionsMarkup" in JS
    assert "D01: {label: 'Revisar conservación', phase2: 'retention'}" in JS
    assert "D02: {label: 'Revisar conservación', phase2: 'retention'}" in JS
    assert "D04: {label: 'Revisar terceros', question: 'third_parties'}" in JS
    assert "D06: {label: 'Revisar datos de menores', question: 'personal_data_types'}" in JS
    assert "D07: {label: 'Aclarar menores', question: 'personal_data_types'}" in JS
    assert "D08: {label: 'Aclarar terceros', question: 'third_parties'}" in JS
    assert 'data-go="review-action"' in JS
    assert 'data-go="review-retention"' in JS
    assert "data-action-activity-id" in JS
    assert "data-action-question" in JS
    assert "Por revisar" in JS
    assert "Ten presente" in JS
    assert "Todo ordenado en lo que ya revisaste ✓" in JS
    assert ".pd-action-item" in CSS
    assert ".pd-action-cta" in CSS


def test_action_edit_returns_to_actions_and_refreshes_review():
    assert "returnToActions: false" in JS
    assert "this.returnToActions = true" in JS
    assert "if (this.returnToActions)" in JS
    assert "this.resultView = 'actions'" in JS
    assert "this.reviewObservations = null" in JS
    assert "await this.loadReview()" in JS
    assert "questions.findIndex(([key]) => key === event.target.dataset.actionQuestion)" in JS


def test_conservation_is_real_progressive_phase_two_flow():
    assert "export function retentionProgress" in JS
    assert "reviewed: false" in JS
    assert "if (this.screen === 'retention') return this.retention();" in JS
    assert "retentionActivities()" in JS
    assert "Fase 2 · Conservación" in JS
    assert "¿Tienes definido cuánto tiempo necesitas conservar esta información?" in JS
    assert "this.options('retention.statuses', selected, 'radio', 'retention-status')" in JS
    assert 'data-retention-fields' in JS
    assert 'name="retention-value"' in JS
    assert 'name="retention-unit"' in JS
    assert 'data-go="start-retention"' in JS
    assert 'data-go="retention-save"' in JS
    assert 'data-go="retention-back"' in JS
    assert "reviewed: true" in JS
    assert "this.retentionIndex += 1" in JS
    assert ".pd-retention-fields" in CSS


def test_conservation_completion_unlocks_access_as_next_placeholder():
    assert "Conservación ✓" in JS
    assert "Revisaste la conservación en todas las actividades de tu mapa." in JS
    assert "Accesos" in JS
    assert "Revisa quién necesita acceder a esta información." in JS
    assert "Comenzar - Próximamente" in JS
    assert "disabled" in JS
    assert ".pd-next-stage" in CSS


def test_map_flow_uses_phase_one_data_without_new_backend_reads():
    assert "export function mapFlowMarkup" in JS
    assert "De dónde viene" in JS
    assert "Personas y datos" in JS
    assert "Para qué" in JS
    assert "Dónde está" in JS
    assert "Con quién" in JS
    assert "data_origins" in JS
    assert "people_categories" in JS
    assert "personal_data_types" in JS
    assert "purposes" in JS
    assert "storage_locations" in JS
    assert "third_party_types" in JS
    assert "Esta vista es solo de lectura por ahora." in JS
    assert ".pd-map-activities" in CSS
    assert ".pd-map-stage" in CSS
    assert ".pd-map-readonly" in CSS
    assert "request(`/maps/${this.token}/map`)" not in JS


def test_map_flow_is_responsive_and_shows_missing_values_without_inference():
    assert ".pd-grid,.pd-cards,.pd-map-activities{grid-template-columns:1fr}" in CSS
    assert "No indicado" in JS
    assert "No participan terceros" in JS
    assert "No estoy seguro" in JS


def test_map_activity_container_is_visually_lightweight():
    assert ".pd-map-activity{border:0;" in CSS
    assert "background:transparent" in CSS
    assert ".pd-map-stage{border:1px solid var(--border)" in CSS


def test_phase_one_delivers_value_after_each_completed_activity():
    assert "activity-complete" in JS
    assert "progress-map" in JS
    assert "lista ✓" in JS
    assert "Ya agregamos esta actividad a tu mapa." in JS
    assert 'data-go="view-progress-map"' in JS
    assert 'data-go="continue-next-activity"' in JS
    assert "completedActivities()" in JS
    assert "mapFlowMarkup(this.catalog, this.completedActivities())" in JS
    assert "this.activityIndex === this.selected.length - 1" in JS
    assert "this.screen = 'activity-complete'" in JS
    assert "this.activityIndex += 1" in JS


def test_progressive_map_does_not_add_fake_resume_or_backend_completion_state():
    assert "Terminar por ahora" not in JS
    assert "phase_one_completed" not in JS
    assert "completed_activity" not in JS
