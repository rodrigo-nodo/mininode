from pathlib import Path

HERE = Path(__file__).parent
HTML = (HERE / "index.html").read_text()
CSS = (HERE / "wizard.css").read_text()
JS = (HERE / "wizard.js").read_text()


def test_phase_one_assets_are_cache_busted_without_auxiliary_ux_assets():
    assert "wizard.css?v=194a" in HTML
    assert "wizard.js?v=194a" in HTML
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


def test_phase_one_result_only_uses_findings_from_phase_one_answers():
    assert "phaseOneObservations" in JS
    assert "['D04', 'D05', 'D06', 'D07', 'D08']" in JS
    finish = JS.split("finish() {", 1)[1].split("async loadReview()", 1)[0]
    assert "D01" not in finish
    assert "D02" not in finish
    assert "D03" not in finish


def test_summary_and_map_are_real_result_views_but_actions_remain_future():
    assert 'data-go="result-summary"' in JS
    assert 'data-go="result-map"' in JS
    assert "this.resultView === 'map'" in JS
    assert "mapFlowMarkup(this.catalog, this.activities)" in JS
    assert "Mapa - Próximamente" not in JS
    assert "Acciones - Próximamente" in JS
    assert '<nav class="pd-result-nav"' in JS
    assert ".pd-result-nav button.active" in CSS


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
