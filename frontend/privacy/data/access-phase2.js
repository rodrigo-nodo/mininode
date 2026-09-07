(() => {
  const originalFetch = window.fetch.bind(window);
  const API_PREFIX = '/api/privacy/data';
  const TOKEN_KEY = 'mininode_privacy_data_token';

  let catalog = null;
  let activities = [];
  let reviewObservations = [];
  let session = null;

  const ACCESS_BY_ACTIVITY = {
    sales: ['owner_only', 'owner_management', 'sales', 'administration', 'technology_it', 'unknown'],
    marketing: ['owner_only', 'owner_management', 'marketing', 'administration', 'technology_it', 'unknown'],
    customer_support: ['owner_only', 'owner_management', 'customer_support', 'supervisors_management', 'technology_it', 'unknown'],
    service_delivery: ['owner_only', 'owner_management', 'service_professionals', 'operations', 'supervisors_management', 'unknown'],
    collaborators: ['owner_only', 'owner_management', 'hr', 'supervisors_management', 'administration', 'unknown'],
    suppliers: ['owner_only', 'owner_management', 'administration', 'operations', 'finance_accounting', 'unknown'],
    finance_accounting: ['owner_only', 'owner_management', 'finance_accounting', 'administration', 'technology_it', 'unknown'],
    digital_users: ['owner_only', 'owner_management', 'technology_it', 'customer_support', 'operations', 'unknown'],
    other: ['owner_only', 'owner_management', 'administration', 'operations', 'technology_it', 'unknown'],
  };

  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[character]);

  function root() {
    return document.querySelector('#privacy-data');
  }

  function canonicalActivities() {
    const byType = new Map();
    for (const activity of activities) {
      const current = byType.get(activity.activity_type);
      if (!current) byType.set(activity.activity_type, activity);
      else {
        const currentTime = Date.parse(current.updated_at || current.created_at || '') || 0;
        const nextTime = Date.parse(activity.updated_at || activity.created_at || '') || 0;
        if (nextTime >= currentTime) byType.set(activity.activity_type, activity);
      }
    }
    return [...byType.values()].sort((left, right) =>
      (left.position ?? Number.MAX_SAFE_INTEGER) - (right.position ?? Number.MAX_SAFE_INTEGER)
      || String(left.activity_type || '').localeCompare(String(right.activity_type || '')));
  }

  function activityLabel(activityType) {
    return catalog?.activity_types?.find(item => item.code === activityType)?.label || activityType;
  }

  function retentionComplete() {
    const list = canonicalActivities();
    return list.length > 0 && list.every(activity => activity.answers?.retention?.reviewed === true);
  }

  function accessProgress() {
    const list = canonicalActivities();
    const reviewed = list.filter(activity => (activity.answers?.access_roles || []).length > 0).length;
    return {total: list.length, reviewed, complete: list.length > 0 && reviewed === list.length};
  }

  function cacheActivity(activity) {
    if (!activity?.id) return;
    const index = activities.findIndex(item => String(item.id) === String(activity.id));
    if (index >= 0) activities[index] = activity;
    else activities.push(activity);
  }

  function scheduleEnhance() {
    setTimeout(enhanceActions, 0);
  }

  function jsonFromClone(response) {
    return response.clone().json().catch(() => null);
  }

  window.fetch = async (input, init = {}) => {
    const url = typeof input === 'string' ? input : input?.url || '';
    const response = await originalFetch(input, init);
    if (!response.ok || response.status === 204 || !url.startsWith(API_PREFIX)) return response;

    if (url.endsWith('/catalog')) {
      const data = await jsonFromClone(response);
      if (data) catalog = data;
      scheduleEnhance();
      return response;
    }

    if (/\/activities(?:\/[^/]+)?$/.test(url)) {
      const data = await jsonFromClone(response);
      if (Array.isArray(data)) activities = data;
      else if (data) cacheActivity(data);
      scheduleEnhance();
      return response;
    }

    if (url.endsWith('/review')) {
      const data = await jsonFromClone(response);
      if (Array.isArray(data)) reviewObservations = data;
      scheduleEnhance();
      return response;
    }

    return response;
  };

  function findStage(title) {
    return [...(root()?.querySelectorAll('.pd-next-stage') || [])]
      .find(section => section.querySelector('h2')?.textContent.trim() === title);
  }

  function ensureSecurityStage(accessStage) {
    let security = root()?.querySelector('[data-phase2-security]');
    if (security) return security;
    security = document.createElement('section');
    security.className = 'pd-next-stage';
    security.dataset.phase2Security = '';
    security.innerHTML = '<p class="eyebrow">Siguiente etapa</p><h2>Seguridad</h2><p>Revisa cómo proteges esta información.</p><button class="btn btn--primary" type="button" disabled>Comenzar - Próximamente</button>';
    accessStage.insertAdjacentElement('afterend', security);
    return security;
  }

  function updateAccessStage() {
    if (!retentionComplete()) return;
    const stage = findStage('Accesos');
    if (!stage) return;
    const progress = accessProgress();
    const eyebrow = stage.querySelector('.eyebrow');
    const detail = [...stage.querySelectorAll(':scope > p')].find(item => !item.classList.contains('eyebrow'));
    let progressLine = stage.querySelector('[data-access-progress]');
    let button = stage.querySelector('button');

    if (progress.complete) {
      stage.classList.add('pd-next-stage--done');
      if (eyebrow) eyebrow.textContent = 'Fase 2';
      if (detail) detail.textContent = 'Revisada en todas las actividades de tu mapa.';
      progressLine?.remove();
      button?.remove();
      ensureSecurityStage(stage);
      return;
    }

    root()?.querySelector('[data-phase2-security]')?.remove();
    stage.classList.remove('pd-next-stage--done');
    if (eyebrow) eyebrow.textContent = 'Siguiente etapa';
    if (detail) detail.textContent = 'Revisa quién necesita acceder a esta información.';
    if (progress.reviewed > 0) {
      if (!progressLine) {
        progressLine = document.createElement('p');
        progressLine.className = 'pd-stage-progress';
        progressLine.dataset.accessProgress = '';
        detail?.insertAdjacentElement('afterend', progressLine);
      }
      progressLine.textContent = `${progress.reviewed} de ${progress.total} actividades revisadas.`;
    } else progressLine?.remove();

    if (!button) {
      button = document.createElement('button');
      button.className = 'btn btn--primary';
      button.type = 'button';
      stage.append(button);
    }
    button.disabled = false;
    button.textContent = progress.reviewed ? 'Continuar accesos' : 'Comenzar';
    button.dataset.phase2AccessStart = '';
  }

  function actionActivity(label) {
    return [...(root()?.querySelectorAll('.pd-action-activity') || [])]
      .find(article => article.querySelector(':scope > h2')?.textContent.trim() === label);
  }

  function cleanupInjectedAccessActions() {
    root()?.querySelectorAll('[data-access-injected]').forEach(item => item.remove());
    root()?.querySelectorAll('[data-access-only-activity]').forEach(article => article.remove());
    root()?.querySelectorAll('.pd-action-group').forEach(group => {
      if (!group.querySelector('.pd-action-item')) group.remove();
    });
  }

  function ensureActionsIntro() {
    const view = root()?.querySelector('.pd-actions-view');
    if (!view) return;
    const hasActions = Boolean(view.querySelector('.pd-action-activity'));
    const lead = view.querySelector(':scope > .pd-actions-view__lead');
    const success = [...view.querySelectorAll(':scope > p')]
      .find(item => item.querySelector('strong')?.textContent.includes('Todo ordenado'));

    if (hasActions) {
      success?.remove();
      if (lead) lead.textContent = 'Estas acciones nacen de lo que identificaste en tu mapa.';
      return;
    }

    if (!success) {
      const status = document.createElement('p');
      status.innerHTML = '<strong>Todo ordenado en lo que ya revisaste ✓</strong>';
      view.querySelector('h2')?.insertAdjacentElement('afterend', status);
    }
    if (lead) lead.textContent = 'No encontramos acciones pendientes en la información que ya revisaste.';
  }

  function injectAccessActions() {
    cleanupInjectedAccessActions();
    const view = root()?.querySelector('.pd-actions-view');
    if (!view) return;
    const d03 = reviewObservations.filter(item => item.code === 'D03');

    for (const observation of d03) {
      const activity = canonicalActivities().find(item => String(item.id) === String(observation.activity_id));
      if (!activity) continue;
      const label = activityLabel(activity.activity_type);
      let article = actionActivity(label);
      if (!article) {
        article = document.createElement('article');
        article.className = 'pd-action-activity';
        article.dataset.accessOnlyActivity = '';
        article.innerHTML = `<h2>${escapeHtml(label)}</h2>`;
        view.append(article);
      }
      let group = [...article.querySelectorAll('.pd-action-group')]
        .find(section => section.querySelector('h3')?.textContent.trim() === 'Por revisar');
      if (!group) {
        group = document.createElement('section');
        group.className = 'pd-action-group';
        group.innerHTML = '<h3>Por revisar</h3>';
        article.append(group);
      }
      const item = document.createElement('div');
      item.className = 'pd-action-item';
      item.dataset.accessInjected = '';
      item.innerHTML = `<strong class="pd-action-item__topic">Accesos</strong><p>${escapeHtml(observation.action || 'Identifica quién necesita acceder a esta información.')}</p><button type="button" class="btn pd-action-cta" data-phase2-review-access="${escapeHtml(activity.id)}">Revisar accesos</button>`;
      group.append(item);
    }
    ensureActionsIntro();
  }

  function enhanceActions() {
    if (!root()?.querySelector('.pd-actions-view')) return;
    updateAccessStage();
    injectAccessActions();
  }

  function accessOptions(activity) {
    const options = catalog?.access_roles || [];
    const suggestedCodes = ACCESS_BY_ACTIVITY[activity.activity_type] || ACCESS_BY_ACTIVITY.other;
    const suggested = options.filter(option => suggestedCodes.includes(option.code));
    const other = options.filter(option => !suggestedCodes.includes(option.code));
    const selected = activity.answers?.access_roles || [];
    const render = list => list.map(option => `<label class="pd-option"><input type="checkbox" name="access-role" value="${escapeHtml(option.code)}" ${selected.includes(option.code) ? 'checked' : ''}><span>${escapeHtml(option.label)}</span></label>`).join('');
    const selectedOther = other.some(option => selected.includes(option.code));
    return `<fieldset class="pd-people" data-section="access_roles"><legend>Opciones habituales</legend><div class="pd-grid">${render(suggested)}</div><details ${selectedOther ? 'open' : ''}><summary>Ver otras opciones</summary><div class="pd-grid">${render(other)}</div></details></fieldset>`;
  }

  function showAccess(index, single = false) {
    const list = canonicalActivities();
    const activity = list[index];
    if (!activity) return restoreActions();
    session.index = index;
    session.single = single;
    const last = index === list.length - 1;
    const saveLabel = single || last ? 'Guardar y volver a Acciones' : 'Guardar y continuar';
    root().innerHTML = `<p class="eyebrow">Fase 2 · Accesos</p><div class="pd-activity-context"><span class="pd-activity-context__count">Actividad ${index + 1} de ${list.length}</span><strong class="pd-activity-context__name">${escapeHtml(activityLabel(activity.activity_type))}</strong><span class="pd-activity-context__question">Accesos</span></div><h2>¿Quién puede acceder a esta información dentro de tu negocio?</h2><p class="pd-lead">Selecciona todas las opciones que correspondan.</p>${accessOptions(activity)}<div class="pd-actions"><button class="pd-back" type="button" data-phase2-access-back>Volver a Acciones</button><button class="btn btn--primary" type="button" data-phase2-access-save>${saveLabel}</button></div>`;
  }

  function openAccess(activityId = null) {
    const list = canonicalActivities();
    if (!list.length) return;
    const index = activityId
      ? list.findIndex(activity => String(activity.id) === String(activityId))
      : Math.max(0, list.findIndex(activity => !(activity.answers?.access_roles || []).length));
    session = {previousHtml: root().innerHTML, index: index >= 0 ? index : 0, single: Boolean(activityId)};
    showAccess(session.index, session.single);
  }

  function showAccessError(message) {
    root()?.querySelector('.pd-error')?.remove();
    const error = document.createElement('p');
    error.className = 'pd-error';
    error.role = 'alert';
    error.textContent = message;
    root()?.prepend(error);
  }

  async function refreshReview() {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return;
    const response = await fetch(`${API_PREFIX}/maps/${token}/review`, {headers: {'Content-Type': 'application/json'}});
    if (response.ok) reviewObservations = await response.json();
  }

  async function saveAccess() {
    if (!session) return;
    const list = canonicalActivities();
    const activity = list[session.index];
    if (!activity) return;
    let selected = [...root().querySelectorAll('input[name="access-role"]:checked')].map(input => input.value);
    if (!selected.length) return showAccessError('Selecciona al menos una opción de acceso.');
    if (selected.includes('owner_only')) selected = ['owner_only'];
    else if (selected.includes('unknown')) selected = ['unknown'];

    const answers = structuredClone(activity.answers || {});
    answers.access_roles = selected;
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return showAccessError('No pudimos encontrar tu mapa.');

    const response = await fetch(`${API_PREFIX}/maps/${token}/activities/${activity.id}`, {
      method: 'PATCH',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({answers}),
    });
    if (!response.ok) return showAccessError('No pudimos guardar los cambios. Intenta nuevamente.');
    cacheActivity(await response.json());

    if (!session.single && session.index < list.length - 1) {
      showAccess(session.index + 1, false);
      return;
    }
    await refreshReview();
    restoreActions();
  }

  function restoreActions() {
    if (!session) return;
    const previous = session.previousHtml;
    session = null;
    root().innerHTML = previous;
    scheduleEnhance();
  }

  document.addEventListener('change', event => {
    const input = event.target;
    if (input?.name !== 'access-role' || !input.checked) return;
    const group = input.closest('fieldset');
    if (!group) return;
    if (['owner_only', 'unknown'].includes(input.value)) {
      group.querySelectorAll('input[name="access-role"]').forEach(option => { option.checked = option === input; });
    } else {
      group.querySelectorAll('input[name="access-role"][value="owner_only"],input[name="access-role"][value="unknown"]').forEach(option => { option.checked = false; });
    }
    root()?.querySelector('.pd-error')?.remove();
  }, true);

  document.addEventListener('click', event => {
    const start = event.target.closest('[data-phase2-access-start]');
    const review = event.target.closest('[data-phase2-review-access]');
    const save = event.target.closest('[data-phase2-access-save]');
    const back = event.target.closest('[data-phase2-access-back]');

    if (start || review || save || back) {
      event.preventDefault();
      event.stopImmediatePropagation();
      if (start) openAccess();
      else if (review) openAccess(review.dataset.phase2ReviewAccess);
      else if (save) saveAccess();
      else if (back) restoreActions();
      return;
    }
    scheduleEnhance();
  }, true);
})();
