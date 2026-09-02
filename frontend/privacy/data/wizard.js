const API = '/api/privacy/data';
const TOKEN_KEY = 'mininode_privacy_data_token';

export const emptyAnswers = () => ({
  people_categories: [], may_include_minors: false, personal_data_types: [],
  storage_locations: [], data_channels: [], purposes: [], access_roles: [],
  has_third_parties: false, third_parties: [],
  retention: {status: 'unknown', value: null, unit: null, note: null},
});

export function exclusive(values, code) {
  const exclusiveCodes = ['owner_only', 'unknown'];
  if (exclusiveCodes.includes(code)) return values.includes(code) ? [code] : [];
  return values.filter(value => !exclusiveCodes.includes(value));
}

export function buildThirdParties(types, relationships, existing = []) {
  return types.map(type => {
    const previous = existing.find(thirdParty => thirdParty.type === type);
    const values = relationships[type] || [];
    const selected = values.includes('unknown') ? ['unknown'] : values;
    return {...(previous?.id ? {id: previous.id} : {}), type, relationships: selected};
  });
}

export function totals(activities) {
  const fields = ['people_categories', 'personal_data_types', 'storage_locations', 'data_channels'];
  const result = {activities: activities.length};
  for (const field of fields) result[field] = new Set(activities.flatMap(a => a.answers[field] || [])).size;
  result.third_party_types = new Set(activities.flatMap(a => (a.answers.third_parties || []).map(t => t.type))).size;
  return result;
}

class FriendlyError extends Error {
  constructor(status, message) {
    super(message || (status === 503 ? 'Privacy Data no está disponible temporalmente.'
      : status === 410 ? 'Este mapa temporal ya venció.'
      : status === 404 ? 'Este mapa ya no está disponible.'
      : status === 422 ? 'Revisa esta respuesta antes de continuar.'
      : 'No pudimos guardar los cambios. Intenta nuevamente.'));
    this.status = status;
  }
}

export async function request(path, options = {}) {
  let response;
  try { response = await fetch(API + path, {headers: {'Content-Type': 'application/json'}, ...options}); }
  catch { throw new FriendlyError(0); }
  if (!response.ok) throw new FriendlyError(response.status);
  return response.status === 204 ? null : response.json();
}

const questions = [
  ['people_categories', '¿De qué personas tienes información en esta actividad?', 'people_categories'],
  ['may_include_minors', '¿Podría haber información de menores de edad?', null],
  ['personal_data_types', '¿Qué tipo de información manejas?', 'personal_data_types'],
  ['storage_locations', '¿Dónde guardas esta información?', 'storage_locations'],
  ['data_channels', '¿Por qué medios se mueve o comparte esta información?', 'data_channels'],
  ['purposes', '¿Para qué utilizas esta información?', 'purposes'],
  ['access_roles', '¿Quién puede acceder a esta información dentro de tu negocio?', 'access_roles'],
  ['third_parties', '¿Alguna persona o empresa externa participa en el manejo de esta información?', null],
  ['retention', '¿Sabes por cuánto tiempo guardas esta información?', null],
];

class Wizard {
  constructor(root) { Object.assign(this, {root, catalog: null, map: null, activities: [], selected: [], screen: 'landing', activityIndex: 0, q: -1, error: '', pendingRemoval: [], minorsUnanswered: new Set(), thirdPartiesUnanswered: new Set()}); }
  async init() {
    try {
      this.catalog = await request('/catalog');
      const token = localStorage.getItem(TOKEN_KEY);
      if (token) {
        try {
          this.token = token;
          this.map = await request(`/maps/${token}`);
          this.activities = await request(`/maps/${token}/activities`);
          this.selected = this.activities.map(a => a.activity_type);
          this.screen = 'resume';
        } catch (error) {
          if ([404, 410].includes(error.status)) { localStorage.removeItem(TOKEN_KEY); this.error = error.message; }
          else throw error;
        }
      }
    } catch (error) { this.error = error.message; }
    this.render();
  }
  async run(action) {
    this.error = ''; this.saving = true; this.render();
    try { await action(); this.saved = true; }
    catch (error) { this.error = error.message; }
    finally { this.saving = false; this.render(); }
  }
  progress(active) { return `<nav class="pd-progress" aria-label="Progreso">${['Rubro', 'Actividades', 'Mapa', 'Final'].map(x => `<span class="${x === active ? 'active' : ''}">${x}</span>`).join('')}</nav>`; }
  choices(section) { return section.split('.').reduce((value, key) => value[key], this.catalog); }
  options(section, selected, type = 'checkbox', name = 'choice') {
    return `<fieldset class="pd-grid" data-section="${section}"><legend class="visually-hidden">Opciones</legend>${this.choices(section).map(option => `<label class="pd-option"><input type="${type}" name="${name}" value="${option.code}" ${selected.includes(option.code) ? 'checked' : ''}><span>${option.label}</span></label>`).join('')}</fieldset>`;
  }
  booleanOptions(selected, name) { return `<fieldset class="pd-grid"><legend class="visually-hidden">Selecciona Sí o No</legend><label class="pd-option"><input type="radio" name="${name}" value="yes" ${selected ? 'checked' : ''}><span>Sí</span></label><label class="pd-option"><input type="radio" name="${name}" value="no" ${selected === false ? 'checked' : ''}><span>No</span></label></fieldset>`; }
  shell(body) { this.root.innerHTML = `${this.error ? `<p class="pd-error" role="alert">${this.error}</p>` : ''}${body}<p class="pd-save" role="status">${this.saving ? 'Guardando…' : this.saved ? 'Guardado' : ''}</p>`; }
  render() {
    if (!this.catalog) return this.shell(`<h1>Privacy Data</h1><p>${this.error || 'Cargando…'}</p>`);
    if (['landing', 'resume'].includes(this.screen)) return this.landing();
    if (this.screen === 'industry') return this.industry();
    if (this.screen === 'activities') return this.activitySelection();
    if (this.screen === 'map') return this.activity();
    if (this.screen === 'size') return this.size();
    return this.finish();
  }
  landing() { this.shell(`<p class="eyebrow">Privacy Data</p><h1>Ordena cómo tu negocio maneja los datos personales por dentro.</h1><p class="pd-lead">Construye un mapa simple de dónde aparecen los datos personales en tu negocio y cómo los utilizas.</p><ul class="pd-benefits"><li>Gratis</li><li>Sin registro</li><li>No pedimos datos personales reales</li><li>Tu mapa estará disponible temporalmente</li></ul><div class="pd-actions"><button class="btn btn--primary" data-go="${this.screen === 'resume' ? 'resume' : 'create'}">${this.screen === 'resume' ? 'Continuar mi mapa' : 'Crear mi mapa'}</button></div>`); }
  industry() { this.shell(`${this.progress('Rubro')}<h2>¿A qué se dedica principalmente tu negocio?</h2><p class="pd-lead">Esto nos ayuda a mostrar ejemplos más cercanos a tu realidad.</p>${this.options('industry_profiles', this.map.industry_profile ? [this.map.industry_profile] : [], 'radio')}<div class="pd-actions"><button class="pd-back" data-go="landing">Atrás</button><button class="btn btn--primary" data-go="save-industry">Guardar y continuar</button></div>`); }
  activitySelection() {
    const confirmation = this.pendingRemoval.length ? `<section class="pd-confirm" role="alert"><strong>Quitaste una actividad que ya tenía información guardada.</strong><p>Si continúas, eliminaremos esa actividad del mapa.</p><div class="pd-actions"><button class="pd-back" data-go="cancel-removal">Cancelar</button><button class="btn btn--primary" data-go="confirm-removal">Eliminar y continuar</button></div></section>` : '';
    this.shell(`${this.progress('Actividades')}<h2>¿En qué actividades de tu negocio aparecen datos personales?</h2><p class="pd-lead">Selecciona todas las que correspondan. Después revisaremos cada una por separado.</p>${this.options('activity_types', this.selected)}${confirmation}<div class="pd-actions"><button class="pd-back" data-go="industry">Atrás</button><button class="btn btn--primary" data-go="start-map">Continuar</button></div>`);
  }
  thirdParties(answers) {
    const yes = answers.has_third_parties;
    const cards = this.catalog.third_party_types.map(type => {
      const existing = answers.third_parties.find(item => item.type === type.code);
      return `<section class="pd-third ${existing ? 'is-selected' : ''}"><label class="pd-option"><input type="checkbox" name="third-type" value="${type.code}" ${existing ? 'checked' : ''}><span>${type.label}</span></label><div class="pd-third__relationships"><p>¿Qué ocurre con la información?</p>${this.options('third_party_relationships', existing?.relationships || [], 'checkbox', `relationship-${type.code}`)}</div></section>`;
    }).join('');
    return `${this.booleanOptions(yes, 'has-third-parties')}<div class="pd-third-list" ${yes ? '' : 'hidden'}><h3>¿Qué tipo de persona o empresa externa participa?</h3>${cards}</div>`;
  }
  activity() {
    const type = this.selected[this.activityIndex];
    const existing = this.activities.find(a => a.activity_type === type);
    const label = this.label('activity_types', type);
    if (this.q < 0) return this.shell(`${this.progress('Mapa')}<p class="pd-subprogress">${label} · De quién son los datos</p><h2>¿De quién son principalmente los datos que manejas aquí?</h2><p class="pd-note">No ingreses nombres, RUT ni datos personales de personas. Solo necesitamos saber qué tipos de información maneja tu negocio.</p>${this.options('data_context', existing ? [existing.data_context] : [], 'radio')}<div class="pd-actions"><button class="pd-back" data-go="activities">Atrás</button><button class="btn btn--primary" data-go="context">Guardar y continuar</button></div>`);
    const [key, title, section] = questions[this.q];
    const answers = existing.answers;
    let content;
    if (key === 'may_include_minors') content = `<p>Por ejemplo, hijos de clientes, estudiantes, pacientes menores o personas bajo tutela.</p>${this.booleanOptions(this.minorsUnanswered.has(existing.id) ? null : answers.may_include_minors, 'minors')}`;
    else if (key === 'purposes') content = `<label class="pd-filter">Buscar una finalidad<input class="pd-search" type="search" data-purpose-filter placeholder="Buscar una finalidad"></label>${this.options('purposes', answers.purposes || [])}`;
    else if (section) content = this.options(section, answers[key] || []);
    else if (key === 'third_parties') content = this.thirdParties(this.thirdPartiesUnanswered.has(existing.id) ? {...answers, has_third_parties: null} : answers);
    else content = `${this.options('retention.statuses', [answers.retention.status], 'radio')}<div class="pd-fields"><label>Valor<input type="number" min="1" name="retention-value" value="${answers.retention.value || ''}"></label><label>Unidad<select name="retention-unit"><option value="">Selecciona</option>${this.catalog.retention.units.map(x => `<option value="${x.code}" ${answers.retention.unit === x.code ? 'selected' : ''}>${x.label}</option>`).join('')}</select></label><label>Nota opcional<input name="retention-note" value="${answers.retention.note || ''}"></label></div>`;
    this.shell(`${this.progress('Mapa')}<p class="pd-subprogress">${label} · ${this.q + 1} de ${questions.length}</p><h2>${title}</h2>${key === 'access_roles' ? '<p>Puede ser usted, personas que trabajan con usted o áreas de su organización.</p>' : ''}${content}<div class="pd-actions"><button class="pd-back" data-go="question-back">Atrás</button><button class="btn btn--primary" data-go="question-save">Guardar y continuar</button></div>`);
  }
  checked(section, name = 'choice') { return [...(this.root.querySelector(`[data-section="${section}"]`)?.querySelectorAll(`input[name="${name}"]:checked`) || [])].map(input => input.value); }
  async saveQuestion() {
    const activity = this.activities.find(a => a.activity_type === this.selected[this.activityIndex]);
    const [key, , section] = questions[this.q];
    const answers = structuredClone(activity.answers);
    if (key === 'may_include_minors') {
      const response = this.root.querySelector('input[name="minors"]:checked');
      if (!response) throw new FriendlyError(422, 'Responde si podría haber información de menores de edad.');
      answers.may_include_minors = response.value === 'yes';
      this.minorsUnanswered.delete(activity.id);
    } else if (key === 'third_parties') {
      const response = this.root.querySelector('input[name="has-third-parties"]:checked');
      if (!response) throw new FriendlyError(422, 'Selecciona Sí o No.');
      answers.has_third_parties = response.value === 'yes';
      this.thirdPartiesUnanswered.delete(activity.id);
      if (!answers.has_third_parties) answers.third_parties = [];
      else {
        const types = [...this.root.querySelectorAll('input[name="third-type"]:checked')].map(input => input.value);
        if (!types.length) throw new FriendlyError(422, 'Selecciona al menos un tipo de persona o empresa externa.');
        const relationships = Object.fromEntries(types.map(type => [type, [...this.root.querySelectorAll(`input[name="relationship-${type}"]:checked`)].map(input => input.value)]));
        if (Object.values(relationships).some(values => !values.length)) throw new FriendlyError(422, 'Selecciona qué ocurre con la información para cada tercero.');
        answers.third_parties = buildThirdParties(types, relationships, answers.third_parties);
      }
    } else if (key === 'retention') {
      const status = this.checked('retention.statuses')[0];
      const value = Number(this.root.querySelector('[name=retention-value]').value) || null;
      const unit = this.root.querySelector('[name=retention-unit]').value || null;
      if (status === 'defined' && (!value || !unit)) throw new FriendlyError(422);
      answers.retention = {status, value: status === 'defined' ? value : null, unit: status === 'defined' ? unit : null, note: this.root.querySelector('[name=retention-note]').value || null};
    } else {
      let values = this.checked(section);
      if (key === 'access_roles' && values.some(value => ['owner_only', 'unknown'].includes(value))) values = exclusive(values, values.find(value => ['owner_only', 'unknown'].includes(value)));
      answers[key] = values;
    }
    await this.patchActivity(activity, answers);
    if (++this.q === questions.length) { this.q = -1; if (++this.activityIndex === this.selected.length) this.screen = 'size'; }
  }
  async patchActivity(activity, answers) { const updated = await request(`/maps/${this.token}/activities/${activity.id}`, {method: 'PATCH', body: JSON.stringify({answers})}); this.activities = this.activities.map(a => a.id === updated.id ? updated : a); }
  size() { this.shell(`${this.progress('Final')}<h2>Para ajustar mejor el contexto, ¿qué tamaño tiene tu negocio?</h2><p>Es opcional y no cambia tus respuestas.</p>${this.options('business_size', this.map.business_size ? [this.map.business_size] : [], 'radio')}<div class="pd-actions"><button class="pd-back" data-go="map-back">Atrás</button><button class="pd-back" data-go="skip-size">Omitir</button><button class="btn btn--primary" data-go="save-size">Continuar</button></div>`); }
  finish() { const summary = totals(this.activities); const stats = [['activities', 'actividades'], ['people_categories', 'tipos de personas'], ['personal_data_types', 'tipos de datos'], ['storage_locations', 'lugares de almacenamiento'], ['data_channels', 'canales'], ['third_party_types', 'tipos de terceros']]; this.shell(`${this.progress('Final')}<h1>Tu mapa está listo</h1><p class="pd-lead">Ya organizamos las principales actividades donde aparecen datos personales en tu negocio.</p><div class="pd-summary">${stats.map(([key, label]) => `<div class="pd-stat"><strong>${summary[key]}</strong>${label}</div>`).join('')}</div><div class="pd-cards">${this.activities.map(a => `<article class="pd-card"><h3>${this.label('activity_types', a.activity_type)}</h3>${['people_categories', 'personal_data_types', 'storage_locations', 'data_channels', 'access_roles'].map(section => `<p>${(a.answers[section] || []).map(code => this.label(section, code)).join(' · ') || 'Sin selección'}</p>`).join('')}</article>`).join('')}</div><p class="pd-note">El siguiente paso será revisar este mapa para detectar aspectos que conviene ordenar.</p>`); }
  label(section, code) { return this.catalog[section]?.find(item => item.code === code)?.label || code; }
  bind() {
    this.root.addEventListener('click', event => this.action(event));
    this.root.addEventListener('input', event => { if (event.target.matches('[data-purpose-filter]')) { const query = event.target.value.trim().toLocaleLowerCase('es'); this.root.querySelectorAll('[data-section="purposes"] .pd-option').forEach(option => { option.hidden = !option.textContent.toLocaleLowerCase('es').includes(query); }); } });
    this.root.addEventListener('change', event => {
      if (event.target.name?.startsWith('relationship-') && event.target.checked) { const group = event.target.closest('fieldset'); if (event.target.value === 'unknown') group.querySelectorAll('input').forEach(input => { input.checked = input === event.target; }); else group.querySelector('input[value="unknown"]').checked = false; }
      if (event.target.name === 'choice' && event.target.type === 'checkbox' && event.target.checked) { const group = event.target.closest('fieldset'); if (['owner_only', 'unknown'].includes(event.target.value)) group.querySelectorAll('input').forEach(input => { input.checked = input === event.target; }); else group.querySelectorAll('input[value="owner_only"],input[value="unknown"]').forEach(input => { input.checked = false; }); }
      if (event.target.name === 'has-third-parties') this.root.querySelector('.pd-third-list').hidden = event.target.value === 'no';
      if (event.target.name === 'third-type') event.target.closest('.pd-third').classList.toggle('is-selected', event.target.checked);
    });
  }
  async action(event) {
    const go = event.target.dataset.go; if (!go) return;
    if (go === 'create') return this.run(async () => { const created = await request('/maps', {method: 'POST', body: '{}'}); this.token = created.token; this.map = created.map; localStorage.setItem(TOKEN_KEY, this.token); this.screen = 'industry'; });
    if (go === 'resume') { this.screen = this.map.industry_profile ? 'activities' : 'industry'; return this.render(); }
    if (['landing', 'industry', 'activities'].includes(go)) { this.screen = go; this.pendingRemoval = []; return this.render(); }
    if (go === 'save-industry') { const value = this.checked('industry_profiles')[0]; if (!value) { this.error = 'Selecciona un rubro.'; return this.render(); } return this.run(async () => { this.map = await request(`/maps/${this.token}`, {method: 'PATCH', body: JSON.stringify({industry_profile: value})}); this.screen = 'activities'; }); }
    if (go === 'start-map') {
      const chosen = this.checked('activity_types');
      if (!chosen.length) { this.error = 'Selecciona al menos una actividad.'; return this.render(); }
      this.pendingSelection = chosen;
      this.pendingRemoval = this.activities.filter(activity => !chosen.includes(activity.activity_type));
      this.selected = chosen;
      if (this.pendingRemoval.length) return this.render();
      this.activityIndex = 0; this.q = -1; this.screen = 'map'; return this.render();
    }
    if (go === 'cancel-removal') { this.selected = [...new Set([...this.pendingSelection, ...this.pendingRemoval.map(a => a.activity_type)])]; this.pendingRemoval = []; return this.render(); }
    if (go === 'confirm-removal') return this.run(async () => { for (const activity of this.pendingRemoval) await request(`/maps/${this.token}/activities/${activity.id}`, {method: 'DELETE'}); const removed = new Set(this.pendingRemoval.map(a => a.id)); this.activities = this.activities.filter(a => !removed.has(a.id)); this.selected = this.pendingSelection; this.pendingRemoval = []; this.activityIndex = 0; this.q = -1; this.screen = 'map'; });
    if (go === 'context') { const context = this.checked('data_context')[0]; if (!context) { this.error = 'Selecciona de quién son los datos.'; return this.render(); } return this.run(async () => { let activity = this.activities.find(a => a.activity_type === this.selected[this.activityIndex]); if (!activity) { activity = await request(`/maps/${this.token}/activities`, {method: 'POST', body: JSON.stringify({activity_type: this.selected[this.activityIndex], data_context: context, position: this.activityIndex, answers: emptyAnswers()})}); this.activities.push(activity); this.minorsUnanswered.add(activity.id); this.thirdPartiesUnanswered.add(activity.id); } else if (activity.data_context !== context) { activity = await request(`/maps/${this.token}/activities/${activity.id}`, {method: 'PATCH', body: JSON.stringify({data_context: context})}); this.activities = this.activities.map(a => a.id === activity.id ? activity : a); } this.q = 0; }); }
    if (go === 'question-back') { this.q = this.q > 0 ? this.q - 1 : -1; return this.render(); }
    if (go === 'question-save') return this.run(() => this.saveQuestion());
    if (go === 'map-back') { this.screen = 'map'; this.activityIndex = this.selected.length - 1; this.q = questions.length - 1; return this.render(); }
    if (['skip-size', 'save-size'].includes(go)) return this.run(async () => { const value = go === 'skip-size' ? null : this.checked('business_size')[0]; this.map = await request(`/maps/${this.token}`, {method: 'PATCH', body: JSON.stringify({business_size: value || null})}); this.screen = 'finish'; });
  }
}

if (typeof document !== 'undefined') { const root = document.querySelector('#privacy-data'); if (root) { const app = new Wizard(root); app.bind(); app.init(); } }
