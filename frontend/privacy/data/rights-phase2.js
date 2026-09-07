(() => {
  const originalFetch = window.fetch.bind(window);
  const API_PREFIX = '/api/privacy/data';
  const TOKEN_KEY = 'mininode_privacy_data_token';

  let catalog = null;
  let activities = [];
  let reviewObservations = [];
  let session = null;

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

  function securityComplete() {
    const list = canonicalActivities();
    return list.length > 0 && list.every(activity => (activity.answers?.security_measures || []).length > 0);
  }

  function rightsProgress() {
    const list = canonicalActivities();
    const reviewed = list.filter(activity => activity.answers?.rights_handling != null).length;
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
    setTimeout(enhanceActions, 80);
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

  function ensurePhase2End(rightsStage) {
    let ending = root()?.querySelector('[data-phase2-review-complete]');
    if (ending) return ending;
    ending = document.createElement('section');
    ending.className = 'pd-next-stage pd-next-stage--done';
    ending.dataset.phase2ReviewComplete = '';
    ending.innerHTML = '<h2>Revisión de Fase 2 terminada</h2><p>Revisaste Conservación, Accesos, Seguridad y Derechos. Las acciones pendientes siguen disponibles arriba.</p>';
    rightsStage.insertAdjacentElement('afterend', ending);
    return ending;
  }

  function updateRightsStage() {
    if (!securityComplete()) return;
    const stage = findStage('Derechos');
    if (!stage) return;
    const progress = rightsProgress();
    let eyebrow = stage.querySelector('.eyebrow');
    const detail = [...stage.querySelectorAll(':scope > p')]
      .find(item => !item.classList.contains('eyebrow') && !item.hasAttribute('data-rights-progress'));
    let progressLine = stage.querySelector('[data-rights-progress]');
    let button = stage.querySelector('button');

    if (progress.complete) {
      stage.classList.add('pd-next-stage--done');
      eyebrow?.remove();
      if (detail) detail.textContent = 'Revisada en todas las actividades de tu mapa.';
      progressLine?.remove();
      button?.remove();
      ensurePhase2End(stage);
      return;
    }

    root()?.querySelector('[data-phase2-review-complete]')?.remove();
    stage.classList.remove('pd-next-stage--done');
    if (!eyebrow) {
      eyebrow = document.createElement('p');
      eyebrow.className = 'eyebrow';
      stage.prepend(eyebrow);
    }
    eyebrow.textContent = 'Siguiente etapa';
    if (detail) detail.textContent = 'Revisa cómo responderías si una persona solicita acceder, corregir o eliminar sus datos.';

    if (progress.reviewed > 0) {
      if (!progressLine) {
        progressLine = document.createElement('p');
        progressLine.className = 'pd-stage-progress';
        progressLine.dataset.rightsProgress = '';
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
    button.textContent = progress.reviewed ? 'Continuar derechos' : 'Comenzar';
    button.dataset.phase2RightsStart = '';
  }

  function actionActivity(label) {
    return [...(root()?.querySelectorAll('.pd-action-activity') || [])]
      .find(article => article.querySelector(':scope > h2')?.textContent.trim() === label);
  }

  function cleanupRightsActions() {
    root()?.querySelectorAll('[data-rights-injected]').forEach(item => item.remove());
    root()?.querySelectorAll('[data-rights-only-activity]').forEach(article => article.remove());
    root()?.querySelectorAll('.pd-action-item').forEach(item => {
      if (item.querySelector('.pd-action-item__topic')?.textContent.trim() === 'Derechos') item.remove();
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

  function injectRightsActions() {
    cleanupRightsActions();
    const view = root()?.querySelector('.pd-actions-view');
    if (!view) return;
    const observations = reviewObservations.filter(item => ['D11', 'D12', 'D13'].includes(item.code));

    for (const observation of observations) {
      const activity = canonicalActivities().find(item => String(item.id) === String(observation.activity_id));
      if (!activity) continue;
      const label = activityLabel(activity.activity_type);
      let article = actionActivity(label);
      if (!article) {
        article = document.createElement('article');
        article.className = 'pd-action-activity';
        article.dataset.rightsOnlyActivity = '';
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
      item.dataset.rightsInjected = '';
      item.innerHTML = `<strong class="pd-action-item__topic">Derechos</strong><p>${escapeHtml(observation.action || 'Define cómo responder a solicitudes sobre datos personales.')}</p><button type="button" class="btn pd-action-cta" data-phase2-review-rights="${escapeHtml(activity.id)}">Revisar derechos</button>`;
      group.append(item);
    }
    ensureActionsIntro();
  }

  function enhanceActions() {
    if (!root()?.querySelector('.pd-actions-view')) return;
    updateRightsStage();
    injectRightsActions();
  }

  function rightsOptions(activity) {
    const options = catalog?.rights_handling || [];
    const selected = activity.answers?.rights_handling ?? '';
    return `<fieldset class="pd-people" data-section="rights_handling"><legend>Selecciona la opción que mejor describe tu situación</legend><div class="pd-grid">${options.map(option => `<label class="pd-option"><input type="radio" name="rights-handling" value="${escapeHtml(option.code)}" ${selected === option.code ? 'checked' : ''}><span>${escapeHtml(option.label)}</span></label>`).join('')}</div></fieldset>`;
  }

  function showRights(index, single = false) {
    const list = canonicalActivities();
    const activity = list[index];
    if (!activity) return restoreActions();
    session.index = index;
    session.single = single;
    const last = index === list.length - 1;
    const saveLabel = single || last ? 'Guardar y volver a Acciones' : 'Guardar y continuar';
    root().innerHTML = `<p class="eyebrow">Fase 2 · Derechos</p><div class="pd-activity-context"><span class="pd-activity-context__count">Actividad ${index + 1} de ${list.length}</span><strong class="pd-activity-context__name">${escapeHtml(activityLabel(activity.activity_type))}</strong><span class="pd-activity-context__question">Derechos</span></div><h2>Si una persona te pide acceder, corregir o eliminar sus datos, ¿sabes cómo responder?</h2><p class="pd-lead">Elige la opción que mejor representa cómo lo manejas hoy.</p>${rightsOptions(activity)}<div class="pd-actions"><button class="pd-back" type="button" data-phase2-rights-back>Volver a Acciones</button><button class="btn btn--primary" type="button" data-phase2-rights-save>${saveLabel}</button></div>`;
  }

  function openRights(activityId = null) {
    const list = canonicalActivities();
    if (!list.length) return;
    const index = activityId
      ? list.findIndex(activity => String(activity.id) === String(activityId))
      : Math.max(0, list.findIndex(activity => activity.answers?.rights_handling == null));
    session = {previousHtml: root().innerHTML, index: index >= 0 ? index : 0, single: Boolean(activityId)};
    showRights(session.index, session.single);
  }

  function showRightsError(message) {
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

  async function saveRights() {
    if (!session) return;
    const list = canonicalActivities();
    const activity = list[session.index];
    if (!activity) return;
    const selected = root().querySelector('input[name="rights-handling"]:checked')?.value;
    if (!selected) return showRightsError('Selecciona una opción antes de continuar.');

    const answers = structuredClone(activity.answers || {});
    answers.rights_handling = selected;
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return showRightsError('No pudimos encontrar tu mapa.');

    const response = await fetch(`${API_PREFIX}/maps/${token}/activities/${activity.id}`, {
      method: 'PATCH',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({answers}),
    });
    if (!response.ok) return showRightsError('No pudimos guardar los cambios. Intenta nuevamente.');
    cacheActivity(await response.json());

    if (!session.single && session.index < list.length - 1) {
      showRights(session.index + 1, false);
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
    if (event.target?.name !== 'rights-handling') return;
    root()?.querySelector('.pd-error')?.remove();
  }, true);

  document.addEventListener('click', event => {
    const start = event.target.closest('[data-phase2-rights-start]');
    const review = event.target.closest('[data-phase2-review-rights]');
    const save = event.target.closest('[data-phase2-rights-save]');
    const back = event.target.closest('[data-phase2-rights-back]');

    if (start || review || save || back) {
      event.preventDefault();
      event.stopImmediatePropagation();
      if (start) openRights();
      else if (review) openRights(review.dataset.phase2ReviewRights);
      else if (save) saveRights();
      else if (back) restoreActions();
      return;
    }
    scheduleEnhance();
  }, true);
})();
