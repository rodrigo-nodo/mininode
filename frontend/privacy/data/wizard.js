const API = '/api/privacy/data';
const TOKEN_KEY = 'mininode_privacy_data_token';
const DEBUG = typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('debug') === '1';

export const emptyAnswers = () => ({
  people_categories: [], may_include_minors: null, personal_data_types: [],
  data_origins: [], storage_locations: [], data_channels: [], purposes: [], access_roles: [],
  has_third_parties: null, third_parties: [],
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

export function unansweredBooleanActivities(activities) {
  return {
    minors: new Set(activities.filter(activity => activity.answers.may_include_minors == null).map(activity => activity.id)),
    thirdParties: new Set(activities.filter(activity => activity.answers.has_third_parties == null).map(activity => activity.id)),
  };
}

const PEOPLE_BY_ACTIVITY = {
  sales: ['customers', 'prospects', 'contacts', 'company_representatives', 'users'],
  marketing: ['customers', 'prospects', 'contacts', 'users'],
  customer_support: ['customers', 'contacts', 'users', 'company_representatives'],
  service_delivery: ['customers', 'contacts', 'users', 'company_representatives', 'client_workers', 'related_third_persons'],
  collaborators: ['employees', 'contractors', 'candidates', 'former_employees'],
  suppliers: ['suppliers_individuals', 'company_representatives', 'contacts'],
  finance_accounting: ['customers', 'suppliers_individuals', 'employees', 'contractors', 'company_representatives'],
  digital_users: ['users', 'customers', 'prospects', 'contacts'],
  other: ['customers', 'contacts', 'employees', 'suppliers_individuals', 'users'],
};
const PEOPLE_BY_INDUSTRY = {
  health: ['patients', 'guardians_tutors'],
  education_training: ['students_participants', 'guardians_tutors'],
};

export function recoveryTokenFromHash(hash) {
  const params = new URLSearchParams((hash || '').replace(/^#/, ''));
  const token = params.get('recover');
  return token && /^[A-Za-z0-9_-]{40,}$/.test(token) ? token : null;
}

export function peopleSuggestions(activityType, industryProfile) {
  const industry = PEOPLE_BY_INDUSTRY[industryProfile] || [];
  return [...new Set([...industry, ...(PEOPLE_BY_ACTIVITY[activityType] || [])])].slice(0, 6);
}

const DATA_BY_ACTIVITY = {
  sales: ['identification', 'contact', 'financial', 'commercial_behavior', 'documents'],
  marketing: ['identification', 'contact', 'commercial_behavior', 'digital', 'image_media'],
  collaborators: ['identification', 'contact', 'employment', 'financial', 'tax', 'documents'],
  finance_accounting: ['identification', 'financial', 'tax', 'documents', 'legal_contractual'],
};
const PURPOSES_BY_ACTIVITY = {
  sales: ['quotation', 'sales_contracting', 'commercial_follow_up', 'billing', 'collections', 'shipping_delivery'],
  marketing: ['marketing_communications', 'promotions_campaigns', 'commercial_follow_up', 'loyalty'],
  collaborators: ['recruitment', 'employment_management', 'payroll', 'attendance', 'benefits', 'training'],
  finance_accounting: ['billing', 'collections', 'payments', 'accounting', 'tax_compliance', 'reporting'],
};
const STORAGE_BY_ACTIVITY = {
  sales: ['spreadsheets', 'local_files', 'cloud_storage', 'business_system', 'website_platform', 'messaging_apps'],
  marketing: ['spreadsheets', 'cloud_storage', 'business_system', 'website_platform', 'messaging_apps'],
  collaborators: ['spreadsheets', 'local_files', 'cloud_storage', 'business_system', 'paper'],
  finance_accounting: ['spreadsheets', 'local_files', 'cloud_storage', 'accounting_system', 'paper'],
};
const THIRD_PARTIES_BY_ACTIVITY = {
  sales: ['payment_provider', 'delivery_provider', 'technology_provider', 'accounting_advisor', 'service_provider'],
  marketing: ['marketing_provider', 'technology_provider', 'service_provider', 'external_professional'],
  collaborators: ['accounting_advisor', 'hr_labor_provider', 'technology_provider', 'external_professional'],
  finance_accounting: ['accounting_advisor', 'technology_provider', 'payment_provider', 'public_authority'],
};
const DEFAULT_SUGGESTIONS = {
  personal_data_types: ['identification', 'contact', 'financial', 'documents', 'digital'],
  purposes: ['service_delivery', 'customer_support', 'billing', 'reporting', 'legal_contract_management'],
  storage_locations: ['spreadsheets', 'local_files', 'cloud_storage', 'business_system', 'website_platform', 'messaging_apps'],
  third_party_types: ['technology_provider', 'accounting_advisor', 'service_provider', 'external_professional'],
};

export function contextualSuggestions(section, activityType) {
  const groups = {personal_data_types: DATA_BY_ACTIVITY, purposes: PURPOSES_BY_ACTIVITY, storage_locations: STORAGE_BY_ACTIVITY, third_party_types: THIRD_PARTIES_BY_ACTIVITY};
  return (groups[section]?.[activityType] || DEFAULT_SUGGESTIONS[section] || []).slice(0, 6);
}

export function totals(activities) {
  const fields = ['people_categories', 'personal_data_types', 'storage_locations', 'data_channels'];
  const result = {activities: activities.length};
  for (const field of fields) result[field] = new Set(activities.flatMap(a => a.answers[field] || [])).size;
  result.third_party_types = new Set(activities.flatMap(a => (a.answers.third_parties || []).map(t => t.type))).size;
  return result;
}

const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, character => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
})[character]);

export function canonicalActivities(activities = []) {
  const timestamp = value => {
    const parsed = Date.parse(value || '');
    return Number.isNaN(parsed) ? -Infinity : parsed;
  };
  const newest = (left, right) => {
    const updated = timestamp(right.updated_at) - timestamp(left.updated_at);
    if (updated) return updated;
    const created = timestamp(right.created_at) - timestamp(left.created_at);
    if (created) return created;
    return String(right.id ?? '').localeCompare(String(left.id ?? ''));
  };
  const byType = new Map();
  for (const activity of activities) {
    const current = byType.get(activity.activity_type);
    if (!current || newest(activity, current) < 0) byType.set(activity.activity_type, activity);
  }
  return [...byType.values()].sort((left, right) =>
    (left.position ?? Number.MAX_SAFE_INTEGER) - (right.position ?? Number.MAX_SAFE_INTEGER)
    || String(left.activity_type ?? '').localeCompare(String(right.activity_type ?? ''))
    || String(left.id ?? '').localeCompare(String(right.id ?? '')));
}

export function visibleReviewAction(observation, catalog) {
  const action = observation.action || '';
  if (observation.code !== 'D04' || observation.third_party_type === 'unknown') return action;
  const thirdParty = catalog?.third_party_types?.find(item => item.code === observation.third_party_type)?.label?.trim();
  if (!thirdParty || thirdParty === 'No estoy seguro') return action;
  const article = /^(Empresa|Entidad)\b/.test(thirdParty) ? 'la' : 'el';
  const naturalLabel = thirdParty.charAt(0).toLocaleLowerCase('es') + thirdParty.slice(1);
  return action.replace('este tercero', `${article} ${naturalLabel}`);
}

export function reviewMarkup(observations, catalog, activities = [], state = {}) {
  if (state.loading) return '<section class="pd-review" aria-live="polite"><p role="status">Revisando tu mapa…</p></section>';
  if (state.error) return '<section class="pd-review" aria-live="polite"><p>No pudimos completar la revisión del mapa en este momento.</p><button class="btn btn--primary" data-go="retry-review">Reintentar revisión</button></section>';

  const label = (section, code) => catalog?.[section]?.find(item => item.code === code)?.label || '';
  const canonical = canonicalActivities(activities);
  const canonicalIds = new Set(canonical.map(activity => String(activity.id)));
  const visible = (observations || []).filter(observation => canonicalIds.has(String(observation.activity_id)));
  if (!visible.length) return '<section class="pd-review"><strong>No encontramos aspectos pendientes dentro de esta primera revisión.</strong><p>Esto no significa que exista cumplimiento completo. La revisión considera únicamente la información incluida en este mapa.</p></section>';

  const activityBlock = activity => {
    let items = visible.filter(observation => String(observation.activity_id) === String(activity.id));
    const unclearThirdParty = items.some(observation => observation.code === 'D04');
    if (unclearThirdParty) items = items.filter(observation => observation.code !== 'D05');
    const group = (type, heading) => {
      const grouped = items.filter(observation => observation.type === type);
      if (!grouped.length) return '';
      const rows = grouped.map(observation =>
        `<p class="pd-review-item"><strong class="pd-review-item__topic">${escapeHtml(observation.topic)}</strong><span class="pd-review-item__action">${escapeHtml(visibleReviewAction(observation, catalog))}</span></p>`).join('');
      return `<section class="pd-review-group"><h3>${heading}</h3>${rows}</section>`;
    };
    const people = (activity.answers?.people_categories || []).map(code => label('people_categories', code)).filter(Boolean);
    const data = (activity.answers?.personal_data_types || []).map(code => label('personal_data_types', code)).filter(Boolean);
    const context = `${people.length ? `<p class="pd-review-activity__context"><strong>Personas:</strong> ${people.map(escapeHtml).join(' · ')}</p>` : ''}${data.length ? `<p class="pd-review-activity__context"><strong>Datos:</strong> ${data.map(escapeHtml).join(' · ')}</p>` : ''}`;
    return `<article class="pd-review-activity"><h2>${escapeHtml(label('activity_types', activity.activity_type))}</h2>${context}${group('review', 'Conviene revisar')}${group('notice', 'Ten presente')}</article>`;
  };
  const shown = canonical.filter(activity => visible.some(observation => String(observation.activity_id) === String(activity.id)));
  const summary = shown.length === 1 ? 'Encontramos temas para ordenar en esta actividad.' : `Encontramos temas para ordenar en ${shown.length} actividades.`;
  return `<section class="pd-review"><p class="pd-review__summary">${summary}</p>${shown.map(activityBlock).join('')}</section>`;
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
  const started = typeof performance !== 'undefined' ? performance.now() : null;
  let response;
  try {
    try { response = await fetch(API + path, {headers: {'Content-Type': 'application/json'}, ...options}); }
    catch { throw new FriendlyError(0); }
    if (!response.ok) throw new FriendlyError(response.status);
    return response.status === 204 ? null : response.json();
  } finally {
    if (DEBUG && started != null) {
      const method = options.method || 'GET';
      console.info(`[Privacy Data] ${method} ${path}: ${Math.round(performance.now() - started)} ms`);
    }
  }
}

const transientInitialError = error => !error?.status || error.status >= 500;
export async function withOneInitialRetry(operation, wait = 1000) {
  try { return await operation(); }
  catch (error) {
    if (!transientInitialError(error)) throw error;
    await new Promise(resolve => setTimeout(resolve, wait));
    return operation();
  }
}

export const phaseOneQuestions = [
  ['people_categories', '¿De qué personas manejas información en esta actividad?', 'people_categories'],
  ['personal_data_types', '¿Qué tipo de información manejas?', 'personal_data_types'],
  ['purposes', '¿Para qué utilizas esta información?', 'purposes'],
  ['data_origins', '¿De dónde obtienes esta información?', 'data_origins'],
  ['storage_locations', '¿Dónde guardas o utilizas esta información?', 'storage_locations'],
  ['third_parties', '¿Alguna persona o empresa fuera de tu negocio recibe, puede ver o utiliza esta información?', null],
];
const questions = phaseOneQuestions;

class Wizard {
  constructor(root) { Object.assign(this, {root, catalog: null, map: null, activities: [], selected: [], screen: 'landing', activityIndex: 0, q: -1, error: '', initialLoadError: '', pendingRemoval: [], minorsUnanswered: new Set(), thirdPartiesUnanswered: new Set(), recoveryUrl: '', copyStatus: '', reviewObservations: null, reviewLoading: false, reviewError: false}); }
  loading(title, detail) { this.shell(`<p class="eyebrow">Privacy Data</p><h1>Ordena cómo tu negocio maneja los datos personales por dentro.</h1><p class="pd-lead">Construye un mapa simple de dónde aparecen los datos personales en tu negocio y cómo los utilizas.</p><ul class="pd-benefits"><li>Gratis</li><li>Sin registro</li><li>No pedimos datos personales reales</li><li>Tu mapa estará disponible temporalmente</li></ul><section class="pd-loading" role="status"><strong>${title}</strong><p>${detail}</p></section>`); }
  async init() {
    this.initialLoadError = '';
    const recoveryToken = typeof window !== 'undefined' ? recoveryTokenFromHash(window.location.hash) : null;
    if (recoveryToken) {
      localStorage.setItem(TOKEN_KEY, recoveryToken);
      history.replaceState(null, '', window.location.pathname + window.location.search);
    }
    const token = recoveryToken || localStorage.getItem(TOKEN_KEY);
    this.loading(token ? 'Recuperando tu mapa…' : 'Preparando tu mapa…', token ? 'Cargando tus respuestas anteriores.' : 'Estamos revisando si ya existe un mapa guardado en este navegador.');
    try { await withOneInitialRetry(async () => {
      if (token) {
        try {
          this.token = token;
          [this.catalog, this.map, this.activities] = await Promise.all([
            request('/catalog'),
            request(`/maps/${token}`),
            request(`/maps/${token}/activities`),
          ]);
          const unanswered = unansweredBooleanActivities(this.activities);
          this.minorsUnanswered = unanswered.minors;
          this.thirdPartiesUnanswered = unanswered.thirdParties;
          this.selected = this.activities.map(a => a.activity_type);
          this.screen = 'resume';
        } catch (error) {
          if ([404, 410].includes(error.status)) {
            localStorage.removeItem(TOKEN_KEY);
            this.token = null;
            this.map = null;
            this.activities = [];
            this.selected = [];
            this.catalog = await request('/catalog');
            this.error = error.message;
          } else { error.initialOperation = 'recovery'; throw error; }
        }
      } else {
        this.catalog = await request('/catalog');
      }
    });
    } catch (error) {
      this.initialLoadError = error.initialOperation === 'recovery'
        ? 'No pudimos recuperar tu mapa. Intenta nuevamente.'
        : 'No pudimos cargar Privacy Data. Intenta nuevamente.';
    }
    this.render();
  }
  async run(action) {
    this.error = ''; this.saving = true;
    try { await action(); }
    catch (error) { this.error = error.message; }
    finally { this.saving = false; this.render(); }
  }
  progress(active) { return `<nav class="pd-progress" aria-label="Progreso">${['Rubro', 'Actividades', 'Mapa', 'Final'].map(x => `<span class="${x === active ? 'active' : ''}">${x}</span>`).join('')}</nav>`; }
  activityHeader(label, question) {
    return `<div class="pd-activity-context"><span class="pd-activity-context__count">Actividad ${this.activityIndex + 1} de ${this.selected.length}</span><strong class="pd-activity-context__name">${escapeHtml(label)}</strong><span class="pd-activity-context__question">Pregunta ${question} de ${questions.length}</span></div>`;
  }
  choices(section) { return section.split('.').reduce((value, key) => value[key], this.catalog); }
  options(section, selected, type = 'checkbox', name = 'choice') {
    return `<fieldset class="pd-grid" data-section="${section}"><legend class="visually-hidden">Opciones</legend>${this.choices(section).map(option => `<label class="pd-option"><input type="${type}" name="${name}" value="${option.code}" ${selected.includes(option.code) ? 'checked' : ''}><span>${option.label}</span></label>`).join('')}</fieldset>`;
  }
  dataContextOptions(selected) {
    const labels = {
      own_operations: 'Para mi negocio',
      client_service: 'Para prestar un servicio a un cliente',
      both: 'En ambos casos',
    };
    const options = this.choices('data_context').filter(option => labels[option.code]);
    return `<fieldset class="pd-grid" data-section="data_context"><legend class="visually-hidden">Selecciona una respuesta</legend>${options.map(option => `<label class="pd-option"><input type="radio" name="data-context" value="${option.code}" ${selected.includes(option.code) ? 'checked' : ''}><span>${labels[option.code]}</span></label>`).join('')}</fieldset>`;
  }
  contextualOptions(section, selected, activityType, summary) {
    const suggested = contextualSuggestions(section, activityType);
    const all = this.catalog[section];
    const primary = all.filter(option => suggested.includes(option.code));
    const other = all.filter(option => !suggested.includes(option.code));
    const render = options => options.map(option => `<label class="pd-option"><input type="checkbox" name="choice" value="${option.code}" ${selected.includes(option.code) ? 'checked' : ''}><span>${option.label}</span></label>`).join('');
    const hasSelectedOther = other.some(option => selected.includes(option.code));
    return `<fieldset class="pd-people" data-section="${section}"><legend>Opciones habituales</legend><div class="pd-grid">${render(primary)}</div><details ${hasSelectedOther ? 'open' : ''}><summary>${summary}</summary><div class="pd-grid">${render(other)}</div></details></fieldset>`;
  }
  peopleOptions(selected, activityType) {
    const suggested = peopleSuggestions(activityType, this.map?.industry_profile);
    const all = this.catalog.people_categories;
    const valid = new Set(all.map(option => option.code));
    const primaryCodes = suggested.filter(code => valid.has(code));
    const primary = all.filter(option => primaryCodes.includes(option.code));
    const other = all.filter(option => !primaryCodes.includes(option.code));
    const render = options => options.map(option => `<label class="pd-option"><input type="checkbox" name="choice" value="${option.code}" ${selected.includes(option.code) ? 'checked' : ''}><span>${option.label}</span></label>`).join('');
    const hasSelectedOther = other.some(option => selected.includes(option.code));
    return `<fieldset class="pd-people" data-section="people_categories"><legend>Opciones habituales</legend><div class="pd-grid">${render(primary)}</div><details ${hasSelectedOther ? 'open' : ''}><summary>Ver otras opciones</summary><div class="pd-grid">${render(other)}</div></details></fieldset>`;
  }
  triStateOptions(selected, name) { return `<fieldset class="pd-grid"><legend class="visually-hidden">Selecciona una respuesta</legend><label class="pd-option"><input type="radio" name="${name}" value="yes" ${selected === true ? 'checked' : ''}><span>Sí</span></label><label class="pd-option"><input type="radio" name="${name}" value="no" ${selected === false ? 'checked' : ''}><span>No</span></label><label class="pd-option"><input type="radio" name="${name}" value="unknown" ${selected === 'unknown' ? 'checked' : ''}><span>No estoy seguro</span></label></fieldset>`; }
  shell(body) { this.root.innerHTML = `${this.error ? `<p class="pd-error" role="alert">${this.error}</p>` : ''}${body}`; }
  render() {
    if (!this.catalog) return this.shell(`<h1>Privacy Data</h1><p>${this.initialLoadError || 'Cargando…'}</p>${this.initialLoadError ? '<div class="pd-actions"><button class="btn btn--primary" data-go="retry-initial">Reintentar</button></div>' : ''}`);
    if (['landing', 'resume'].includes(this.screen)) return this.landing();
    if (this.screen === 'industry') return this.industry();
    if (this.screen === 'activities') return this.activitySelection();
    if (this.screen === 'map') return this.activity();
    if (this.screen === 'size') return this.size();
    return this.finish();
  }
  landing() { const hasMap = Boolean(this.map && this.token); this.shell(`<p class="eyebrow">Privacy Data</p><h1>Ordena cómo tu negocio maneja los datos personales por dentro.</h1><p class="pd-lead">Construye un mapa simple de dónde aparecen los datos personales en tu negocio y cómo los utilizas.</p><ul class="pd-benefits"><li>Gratis</li><li>Sin registro</li><li>No pedimos datos personales reales</li><li>Tu mapa estará disponible temporalmente</li></ul><div class="pd-actions"><button class="btn btn--primary" data-go="${hasMap ? 'resume' : 'create'}">${hasMap ? 'Continuar mi mapa' : 'Crear mi mapa'}</button></div>`); }
  industry() { this.shell(`${this.progress('Rubro')}<h2>¿A qué se dedica principalmente tu negocio?</h2><p class="pd-lead">Esto nos ayuda a mostrar ejemplos más cercanos a tu realidad.</p>${this.options('industry_profiles', this.map.industry_profile ? [this.map.industry_profile] : [], 'radio')}<div class="pd-actions"><button class="pd-back" data-go="landing">Atrás</button><button class="btn btn--primary" data-go="save-industry">Guardar y continuar</button></div>`); }
  activitySelection() {
    const confirmation = this.pendingRemoval.length ? `<section class="pd-confirm" role="alert"><strong>Quitaste una actividad que ya tenía información guardada.</strong><p>Si continúas, eliminaremos esa actividad del mapa.</p><div class="pd-actions"><button class="pd-back" data-go="cancel-removal">Cancelar</button><button class="btn btn--primary" data-go="confirm-removal">Eliminar y continuar</button></div></section>` : '';
    this.shell(`${this.progress('Actividades')}<h2>¿En qué actividades de tu negocio aparecen datos personales?</h2><p class="pd-lead">Selecciona todas las que correspondan. Después revisaremos cada una por separado.</p>${this.options('activity_types', this.selected)}${confirmation}<div class="pd-actions"><button class="pd-back" data-go="industry">Atrás</button><button class="btn btn--primary" data-go="start-map">Continuar</button></div>`);
  }
  thirdParties(answers) {
    const yes = answers.has_third_parties;
    const activityType = this.selected[this.activityIndex];
    const suggestions = contextualSuggestions('third_party_types', activityType);
    const ordered = [...this.catalog.third_party_types].sort((a, b) => {
      const ai = suggestions.indexOf(a.code); const bi = suggestions.indexOf(b.code);
      return (ai < 0 ? 99 : ai) - (bi < 0 ? 99 : bi);
    });
    const card = type => {
      const existing = answers.third_parties.find(item => item.type === type.code);
      return `<section class="pd-third ${existing ? 'is-selected' : ''}"><label class="pd-option"><input type="checkbox" name="third-type" value="${type.code}" ${existing ? 'checked' : ''}><span>${type.label}</span></label><div class="pd-third__relationships"><p>¿Qué ocurre con la información?</p>${this.options('third_party_relationships', existing?.relationships || [], 'checkbox', `relationship-${type.code}`)}</div></section>`;
    };
    const primary = ordered.filter(type => suggestions.includes(type.code)).map(card).join('');
    const other = ordered.filter(type => !suggestions.includes(type.code)).map(card).join('');
    return `${this.triStateOptions(yes, 'has-third-parties')}<div class="pd-third-list" data-third-list ${yes === true ? '' : 'inert style="display:none"'}><h3>¿Qué tipo de persona o empresa externa participa?</h3>${primary}<details ${answers.third_parties.some(item => !suggestions.includes(item.type)) ? 'open' : ''}><summary>Ver otros terceros</summary>${other}</details></div>`;
  }
  activity() {
    const type = this.selected[this.activityIndex];
    const existing = this.activities.find(a => a.activity_type === type);
    const label = this.label('activity_types', type);
    const [key, title, section] = questions[this.q];
    const answers = existing.answers;
    let content;
    if (key === 'people_categories') content = this.peopleOptions(answers.people_categories || [], type);
    else if (key === 'personal_data_types') content = `${this.contextualOptions(section, answers[key] || [], type, 'Ver otros tipos de información')}<section class="pd-micro-question pd-micro-question--secondary"><p class="pd-micro-question__eyebrow">Un detalle más</p><h3>¿Podría haber menores de edad entre estas personas?</h3>${this.triStateOptions(this.minorsUnanswered.has(existing.id) ? null : answers.may_include_minors, 'minors')}</section>`;
    else if (key === 'purposes') content = this.contextualOptions(section, answers[key] || [], type, 'Ver otras opciones');
    else if (key === 'data_origins') content = `${this.options(section, answers[key] || [])}<section class="pd-micro-question pd-micro-question--secondary"><p class="pd-micro-question__eyebrow">Un detalle más</p><h3>¿Para quién manejas esta información?</h3><p>Esto nos ayuda a distinguir los datos que usas para tu negocio de los que manejas al prestar un servicio a un cliente.</p>${this.dataContextOptions(existing.data_context === 'unconfirmed' ? [] : [existing.data_context])}</section>`;
    else if (key === 'storage_locations') content = this.contextualOptions(section, answers[key] || [], type, 'Ver otros lugares');
    else if (section) content = this.options(section, answers[key] || []);
    else if (key === 'third_parties') content = this.thirdParties(this.thirdPartiesUnanswered.has(existing.id) ? {...answers, has_third_parties: null} : answers);
    else content = `${this.options('retention.statuses', [answers.retention.status], 'radio')}<div class="pd-fields" data-retention-fields ${answers.retention.status === 'defined' ? '' : 'inert style="display:none"'}><label>Valor<input type="number" min="1" name="retention-value" value="${answers.retention.value || ''}"></label><label>Unidad<select name="retention-unit"><option value="">Selecciona</option>${this.catalog.retention.units.map(x => `<option value="${x.code}" ${answers.retention.unit === x.code ? 'selected' : ''}>${x.label}</option>`).join('')}</select></label><label>Nota opcional<input name="retention-note" value="${answers.retention.note || ''}"></label></div>`;
    this.shell(`${this.progress('Mapa')}${this.activityHeader(label, this.q + 1)}<h2>${title}</h2>${content}<div class="pd-actions"><button class="pd-back" data-go="question-back">Atrás</button><button class="btn btn--primary" data-go="question-save">Guardar y continuar</button></div>`);
  }
  checked(section, name = 'choice') { return [...(this.root.querySelector(`[data-section="${section}"]`)?.querySelectorAll(`input[name="${name}"]:checked`) || [])].map(input => input.value); }
  async saveQuestion() {
    const activity = this.activities.find(a => a.activity_type === this.selected[this.activityIndex]);
    const [key, , section] = questions[this.q];
    const answers = structuredClone(activity.answers);
    if (key === 'personal_data_types') {
      const response = this.root.querySelector('input[name="minors"]:checked');
      if (!response) throw new FriendlyError(422, 'Responde si podría haber menores de edad entre estas personas.');
      answers.may_include_minors = response.value === 'unknown' ? 'unknown' : response.value === 'yes';
      answers.personal_data_types = this.checked(section);
      this.minorsUnanswered.delete(activity.id);
    } else if (key === 'data_origins') {
      const dataContext = this.checked('data_context', 'data-context')[0];
      if (!dataContext) throw new FriendlyError(422, 'Selecciona para quién manejas esta información.');
      answers.data_origins = this.checked(section);
      await this.patchActivity(activity, answers, {data_context: dataContext});
      return this.advanceQuestion();
    } else if (key === 'third_parties') {
      const response = this.root.querySelector('input[name="has-third-parties"]:checked');
      if (!response) throw new FriendlyError(422, 'Selecciona Sí, No o No estoy seguro.');
      answers.has_third_parties = response.value === 'unknown' ? 'unknown' : response.value === 'yes';
      this.thirdPartiesUnanswered.delete(activity.id);
      if (answers.has_third_parties !== true) answers.third_parties = [];
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
    await this.advanceQuestion();
  }
  async advanceQuestion() {
    if (++this.q === questions.length) {
      this.q = 0;
      if (++this.activityIndex === this.selected.length) {
        this.screen = 'finish';
        this.reviewObservations = null;
        this.reviewLoading = true;
        this.reviewError = false;
        await Promise.allSettled([this.loadReview(), this.generateRecoveryLink()]);
      }
    }
  }
  async patchActivity(activity, answers, changes = {}) { const updated = await request(`/maps/${this.token}/activities/${activity.id}`, {method: 'PATCH', body: JSON.stringify({...changes, answers})}); this.activities = this.activities.map(a => a.id === updated.id ? updated : a); }
  size() { this.shell(`${this.progress('Final')}<h2>Para ajustar mejor el contexto, ¿qué tamaño tiene tu negocio?</h2><p>Es opcional y no cambia tus respuestas.</p>${this.options('business_size', this.map.business_size ? [this.map.business_size] : [], 'radio')}<div class="pd-actions"><button class="pd-back" data-go="map-back">Atrás</button><button class="pd-back" data-go="skip-size">Omitir</button><button class="btn btn--primary" data-go="save-size">Continuar</button></div>`); }
  finish() {
    const recovery = this.recoveryUrl
      ? `<label class="pd-recovery__label">Tu enlace<input class="pd-recovery__input" value="${this.recoveryUrl}" readonly></label><div class="pd-actions"><button class="btn btn--primary" data-go="copy-recovery-link">Copiar enlace</button></div><p class="pd-copy-status" role="status">${this.copyStatus}</p><p class="pd-warning">Quien tenga este enlace podrá acceder al mapa. Guárdalo de forma segura.</p>`
      : `<p class="pd-copy-status" role="status">${this.copyStatus || 'Preparando tu enlace…'}</p><div class="pd-actions"><button class="btn btn--primary" data-go="generate-recovery-link">Reintentar</button></div>`;
    const phaseOneObservations = this.reviewObservations?.filter(observation => ['D04', 'D05', 'D06', 'D07', 'D08'].includes(observation.code)) ?? this.reviewObservations;
    const review = reviewMarkup(phaseOneObservations, this.catalog, this.activities, {loading: this.reviewLoading, error: this.reviewError});
    this.shell(`${this.progress('Final')}<p class="eyebrow">Fase 1 terminada</p><h1>Este es tu primer mapa</h1><p class="pd-lead">Ya organizamos las personas, los datos, sus usos, su origen, los lugares y los terceros de tu negocio. Puedes revisar este resultado antes de profundizar.</p><p><strong>Resumen</strong> · Mapa - Próximamente · Acciones - Próximamente</p>${review}<section class="pd-recovery"><h2>Guarda tu mapa para continuar después</h2><p>Tu mapa está guardado temporalmente en este navegador. También puedes guardar este enlace para abrirlo desde otro dispositivo.</p>${recovery}</section><div class="pd-actions"><button class="pd-back" data-go="edit-map">Volver y editar mi mapa</button></div>`);
  }
  async loadReview() {
    this.reviewLoading = true;
    this.reviewError = false;
    this.render();
    try { this.reviewObservations = await request(`/maps/${this.token}/review`); }
    catch { this.reviewObservations = null; this.reviewError = true; }
    finally { this.reviewLoading = false; this.render(); }
  }
  async generateRecoveryLink() {
    try {
      const created = await request(`/maps/${this.token}/recovery-link`, {method: 'POST', body: '{}'});
      this.recoveryUrl = `${window.location.origin}${window.location.pathname}#recover=${encodeURIComponent(created.recovery_token)}`;
      this.copyStatus = '';
    } catch { this.copyStatus = 'No pudimos generar el enlace. Intenta nuevamente.'; }
    this.render();
  }
  label(section, code) { return this.catalog[section]?.find(item => item.code === code)?.label || code; }
  bind() {
    this.root.addEventListener('click', event => this.action(event));
    this.root.addEventListener('change', event => {
      if (this.error) {
        this.error = '';
        this.root.querySelector('.pd-error')?.remove();
      }
      if (event.target.name?.startsWith('relationship-') && event.target.checked) { const group = event.target.closest('fieldset'); if (event.target.value === 'unknown') group.querySelectorAll('input').forEach(input => { input.checked = input === event.target; }); else group.querySelector('input[value="unknown"]').checked = false; }
      if (event.target.name === 'choice' && event.target.type === 'checkbox' && event.target.checked) { const group = event.target.closest('fieldset'); if (['owner_only', 'unknown'].includes(event.target.value)) group.querySelectorAll('input').forEach(input => { input.checked = input === event.target; }); else group.querySelectorAll('input[value="owner_only"],input[value="unknown"]').forEach(input => { input.checked = false; }); }
      if (event.target.name === 'has-third-parties') {
        const list = this.root.querySelector('[data-third-list]');
        if (list) { const show = event.target.value === 'yes'; list.style.display = show ? 'grid' : 'none'; list.inert = !show; }
      }
      if (event.target.closest('[data-section="retention.statuses"]')) {
        const fields = this.root.querySelector('[data-retention-fields]');
        if (fields) { const show = event.target.value === 'defined'; fields.style.display = show ? 'flex' : 'none'; fields.inert = !show; }
      }
      if (event.target.name === 'third-type') event.target.closest('.pd-third').classList.toggle('is-selected', event.target.checked);
    });
  }
  async action(event) {
    const go = event.target.dataset.go; if (!go) return;
    if (go === 'retry-initial') return this.init();
    if (go === 'create') return this.run(async () => { this.activities = []; this.selected = []; this.pendingRemoval = []; this.minorsUnanswered = new Set(); this.thirdPartiesUnanswered = new Set(); this.activityIndex = 0; this.q = -1; const created = await request('/maps', {method: 'POST', body: '{}'}); this.token = created.token; this.map = created.map; localStorage.setItem(TOKEN_KEY, this.token); this.screen = 'industry'; });
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
      return this.run(async () => {
        for (const [position, activityType] of chosen.entries()) {
          if (this.activities.some(activity => activity.activity_type === activityType)) continue;
          const activity = await request(`/maps/${this.token}/activities`, {method: 'POST', body: JSON.stringify({activity_type: activityType, data_context: 'unconfirmed', position, answers: emptyAnswers()})});
          this.activities.push(activity); this.minorsUnanswered.add(activity.id); this.thirdPartiesUnanswered.add(activity.id);
        }
        this.activityIndex = 0; this.q = 0; this.screen = 'map';
      });
    }
    if (go === 'cancel-removal') { this.selected = [...new Set([...this.pendingSelection, ...this.pendingRemoval.map(a => a.activity_type)])]; this.pendingRemoval = []; return this.render(); }
    if (go === 'confirm-removal') return this.run(async () => { for (const activity of this.pendingRemoval) await request(`/maps/${this.token}/activities/${activity.id}`, {method: 'DELETE'}); const removed = new Set(this.pendingRemoval.map(a => a.id)); this.activities = this.activities.filter(a => !removed.has(a.id)); this.selected = this.pendingSelection; this.pendingRemoval = []; for (const [position, activityType] of this.selected.entries()) { if (this.activities.some(activity => activity.activity_type === activityType)) continue; const activity = await request(`/maps/${this.token}/activities`, {method: 'POST', body: JSON.stringify({activity_type: activityType, data_context: 'unconfirmed', position, answers: emptyAnswers()})}); this.activities.push(activity); this.minorsUnanswered.add(activity.id); this.thirdPartiesUnanswered.add(activity.id); } this.activityIndex = 0; this.q = 0; this.screen = 'map'; });
    if (go === 'question-back') { if (this.q > 0) this.q -= 1; else this.screen = 'activities'; return this.render(); }
    if (go === 'question-save') return this.run(() => this.saveQuestion());
    if (go === 'map-back') { this.screen = 'map'; this.activityIndex = this.selected.length - 1; this.q = questions.length - 1; return this.render(); }
    if (go === 'generate-recovery-link') {
      this.copyStatus = 'Preparando tu enlace…';
      this.render();
      return this.generateRecoveryLink();
    }
    if (go === 'retry-review') return this.loadReview();
    if (go === 'copy-recovery-link') {
      try {
        await navigator.clipboard.writeText(this.recoveryUrl);
        this.copyStatus = 'Enlace copiado.';
      } catch {
        this.copyStatus = 'No pudimos copiarlo automáticamente. Selecciona el enlace y cópialo manualmente.';
      }
      return this.render();
    }
    if (go === 'edit-map') { this.screen = 'activities'; this.pendingRemoval = []; return this.render(); }
    if (['skip-size', 'save-size'].includes(go)) return this.run(async () => {
      const value = go === 'skip-size' ? null : this.checked('business_size')[0];
      this.map = await request(`/maps/${this.token}`, {method: 'PATCH', body: JSON.stringify({business_size: value || null})});
      this.screen = 'finish';
      this.reviewObservations = null;
      this.reviewLoading = true;
      this.reviewError = false;
      this.render();
      await Promise.allSettled([this.loadReview(), this.generateRecoveryLink()]);
    });
  }
}

if (typeof document !== 'undefined') { const root = document.querySelector('#privacy-data'); if (root) { const app = new Wizard(root); app.bind(); app.init(); } }
