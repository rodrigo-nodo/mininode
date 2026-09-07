(() => {
  const originalFetch = window.fetch.bind(window);
  const API_PREFIX = '/api/privacy/data';
  const TOKEN_KEY = 'mininode_privacy_data_token';

  let catalog = null;
  let activities = [];
  let reviewObservations = [];
  let session = null;

  const COMMON_SECURITY = [
    'passwords_device_lock',
    'individual_accounts',
    'two_factor_auth',
    'backups',
    'updates_antivirus',
  ];
  const EXCLUSIVE_SECURITY = ['none', 'unknown'];

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

  function accessComplete() {
    const list = canonicalActivities();
    return list.length > 0 && list.every(activity => (activity.answers?.access_roles || []).length > 0);
  }

  function securityProgress() {
    const list = canonicalActivities();
    const reviewed = list.filter(activity => (activity.answers?.security_measures || []).length > 0).length;
    return {total: list.length, reviewed, complete: list.length > 0 && reviewed === list.length};
  }

  function cacheActivity(activity) {
    if (!activity?.id) return;
    const index = activities.findIndex(item => String(item.id) === String(activity.id));
    if (index >= 0) activities[index] = activity;
    else activities.push(activity);
  }

  function jsonFromClone(response) {
    return response.clone().json().catch(() => null);
  }

  function scheduleEnhance() {
    setTimeout(enhanceActions, 0);
    setTimeout(enhanceActions, 60);
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

  function ensureRightsStage(securityStage) {
    let rights = root()?.querySelector('[data-phase2-rights]');
    if (rights) return rights;
    rights = document.createElement('section');
    rights.className = 'pd-next-stage';
    rights.dataset.phase2Rights = '';
    rights.innerHTML = '<p class="eyebrow">Siguiente etapa</p><h2>Derechos</h2><p>Revisa cómo responderías si una persona solicita acceder, corregir o eliminar sus datos.</p><button class="btn btn--primary" type="button" disabled>Comenzar - Próximamente</button>';
    securityStage.insertAdjacentElement('afterend', rights);
    return rights;
  }

  function updateSecurityStage() {
    if (!accessComplete()) return;
    const stage = findStage('Seguridad');
    if (!stage) return;
    const progress = securityProgress();
    let eyebrow = stage.querySelector('.eyebrow');
    const detail = [...stage.querySelectorAll(':scope > p')].find(item => !item.classList.contains('eyebrow') && !item.hasAttribute('data-security-progress'));
    let progressLine = stage.querySelector('[data-security-progress]');
    let button = stage.querySelector('button');

    if (progress.complete) {
      stage.classList.add('pd-next-stage--done');
      eyebrow?.remove();
      if (detail) detail.textContent = 'Revisada en todas las actividades de tu mapa.';
      progressLine?.remove();
      button?.remove();
      ensureRightsStage(stage);
      return;
    }

    root()?.querySelector('[data-phase2-rights]')?.remove();
    stage.classList.remove('pd-next-stage--done');
    if (!eyebrow) {
      eyebrow = document.createElement('p');
      eyebrow.className = 'eyebrow';
      stage.prepend(eyebrow);
    }
    eyebrow.textContent = 'Siguiente etapa';
    if (detail) detail.textContent = 'Revisa cómo proteges esta información.';

    if (progress.reviewed > 0) {
      if (!progressLine) {
        progressLine = document.createElement('p');
        progressLine.className = 'pd-stage-progress';
        progressLine.dataset.securityProgress = '';
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
    button.textContent = progress.reviewed ? 'Continuar seguridad' : 'Comenzar';
    button.dataset.phase2SecurityStart = '';
  }

  function actionActivity(label) {
    return [...(root()?.querySelectorAll('.pd-action-activity') || [])]
      .find(article => article.querySelector(':scope > h2')?.textContent.trim() === label);
  }

  function cleanupSecurityActions() {
    root()?.querySelectorAll('[data-security-injected]').forEach(item => item.remove());
    root()?.querySelectorAll('[data-security-only-activity]').forEach(article => article.remove());
    root()?.querySelectorAll('.pd-action-item').forEach(item => {
      if (item.querySelector('.pd-action-item__topic')?.textContent.trim() === 'Seguridad') item.remove();
    });
    root()?.querySelectorAll('.pd-action-group').forEach(group => {
      if (!group.querySelector('.pd-action-item')) group.remove();
    });
  }

  function ensureActionsIntro() {
    const view = root()?.querySelector('.pd-actions-view');
    if (!view) return;
    const hasActions = Boolean(view.querySelector('.pd-action-activity .pd-action-item'));
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

  function injectSecurityActions() {
    cleanupSecurityActions();
    const view = root()?.querySelector('.pd-actions-view');
    if (!view) return;
    const observations = reviewObservations.filter(item => ['D09', 'D10'].includes(item.code));

    for (const observation of observations) {
      const activity = canonicalActivities().find(item => String(item.id) === String(observation.activity_id));
      if (!activity) continue;
      const label = activityLabel(activity.activity_type);
      let article = actionActivity(label);
      if (!article) {
        article = document.createElement('article');
        article.className = 'pd-action-activity';
        article.dataset.securityOnlyActivity = '';
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
      item.dataset.securityInjected = '';
      item.innerHTML = `<strong class="pd-action-item__topic">Seguridad</strong><p>${escapeHtml(observation.action || 'Revisa cómo proteges esta información.')}</p><button type="button" class="btn pd-action-cta" data-phase2-review-security="${escapeHtml(activity.id)}">Revisar seguridad</button>`;
      group.append(item);
    }
    ensureActionsIntro();
  }

  function enhanceActions() {
    if (!root()?.querySelector('.pd-actions-view')) return;
    updateSecurityStage();
    injectSecurityActions();
  }

  function optionMarkup(option, selected) {
    return `<label class="pd-option"><input type="checkbox" name="security-measure" value="${escapeHtml(option.code)}" ${selected.includes(option.code) ? 'checked' : ''}><span>${escapeHtml(option.label)}</span></label>`;
  }

  function securityOptions(activity) {
    const options = catalog?.security_measures || [];
    const selected = activity.answers?.security_measures || [];
    const common = options.filter(option => COMMON_SECURITY.includes(option.code));
    const otherPositive = options.filter(option => !COMMON_SECURITY.includes(option.code) && !EXCLUSIVE_SECURITY.includes(option.code));
    const fallback = options.filter(option => EXCLUSIVE_SECURITY.includes(option.code));
    const selectedOther = otherPositive.some(option => selected.includes(option.code));

    return `<fieldset class="pd-people" data-section="security_measures"><legend>Opciones habituales</legend><div class="pd-grid">${common.map(option => optionMarkup(option, selected)).join('')}</div>${otherPositive.length ? `<details ${selectedOther ? 'open' : ''}><summary>Ver otras medidas</summary><div class="pd-grid">${otherPositive.map(option => optionMarkup(option, selected)).join('')}</div></details>` : ''}<div class="pd-micro-question pd-micro-question--secondary"><p class="pd-micro-question__eyebrow">Si ninguna opción describe tu situación</p><div class="pd-grid">${fallback.map(option => optionMarkup(option, selected)).join('')}</div></div></fieldset>`;
  }

  function showSecurity(index, single = false) {
    const list = canonicalActivities();
    const activity = list[index];
    if (!activity) return restoreActions();
    session.index = index;
    session.single = single;
    const last = index === list.length - 1;
    const saveLabel = single || last ? 'Guardar y volver a Acciones' : 'Guardar y continuar';
    root().innerHTML = `<p class="eyebrow">Fase 2 · Seguridad</p><div class="pd-activity-context"><span class="pd-activity-context__count">Actividad ${index + 1} de ${list.length}</span><strong class="pd-activity-context__name">${escapeHtml(activityLabel(activity.activity_type))}</strong><span class="pd-activity-context__question">Seguridad</span></div><h2>¿Qué medidas usas para proteger esta información?</h2><p class="pd-lead">Selecciona todas las opciones que correspondan.</p>${securityOptions(activity)}<div class="pd-actions"><button class="pd-back" type="button" data-phase2-security-back>Volver a Acciones</button><button class="btn btn--primary" type="button" data-phase2-security-save>${saveLabel}</button></div>`;
  }

  function openSecurity(activityId = null) {
    const list = canonicalActivities();
    if (!list.length) return;
    const index = activityId
      ? list.findIndex(activity => String(activity.id) === String(activityId))
      : Math.max(0, list.findIndex(activity => !(activity.answers?.security_measures || []).length));
    session = {previousHtml: root().innerHTML, index: index >= 0 ? index : 0, single: Boolean(activityId)};
    showSecurity(session.index, session.single);
  }

  function showSecurityError(message) {
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

  async function saveSecurity() {
    if (!session) return;
    const list = canonicalActivities();
    const activity = list[session.index];
    if (!activity) return;
    let selected = [...root().querySelectorAll('input[name="security-measure"]:checked')].map(input => input.value);
    if (!selected.length) return showSecurityError('Selecciona al menos una opción de seguridad.');
    if (selected.includes('none')) selected = ['none'];
    else if (selected.includes('unknown')) selected = ['unknown'];

    const answers = structuredClone(activity.answers || {});
    answers.security_measures = selected;
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return showSecurityError('No pudimos encontrar tu mapa.');

    const response = await fetch(`${API_PREFIX}/maps/${token}/activities/${activity.id}`, {
      method: 'PATCH',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({answers}),
    });
    if (!response.ok) return showSecurityError('No pudimos guardar los cambios. Intenta nuevamente.');
    cacheActivity(await response.json());

    if (!session.single && session.index < list.length - 1) {
      showSecurity(session.index + 1, false);
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
    if (input?.name !== 'security-measure' || !input.checked) return;
    const scope = input.closest('fieldset');
    if (!scope) return;
    if (EXCLUSIVE_SECURITY.includes(input.value)) {
      scope.querySelectorAll('input[name="security-measure"]').forEach(option => { option.checked = option === input; });
    } else {
      scope.querySelectorAll('input[name="security-measure"][value="none"],input[name="security-measure"][value="unknown"]').forEach(option => { option.checked = false; });
    }
    root()?.querySelector('.pd-error')?.remove();
  }, true);

  document.addEventListener('click', event => {
    const start = event.target.closest('[data-phase2-security-start]');
    const review = event.target.closest('[data-phase2-review-security]');
    const save = event.target.closest('[data-phase2-security-save]');
    const back = event.target.closest('[data-phase2-security-back]');

    if (start || review || save || back) {
      event.preventDefault();
      event.stopImmediatePropagation();
      if (start) openSecurity();
      else if (review) openSecurity(review.dataset.phase2ReviewSecurity);
      else if (save) saveSecurity();
      else if (back) restoreActions();
      return;
    }
    scheduleEnhance();
  }, true);
})();
