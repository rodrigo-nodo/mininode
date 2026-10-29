const elements = {
  loading: document.querySelector('#plan-loading'), content: document.querySelector('#plan-content'), error: document.querySelector('#plan-error'),
  errorTitle: document.querySelector('#error-title'), errorMessage: document.querySelector('#error-message'), retry: document.querySelector('#retry'), privacyLink: document.querySelector('#privacy-link'),
  site: document.querySelector('#site-url'), currentScore: document.querySelector('#current-score'), currentDate: document.querySelector('#current-date'), currentOrigin: document.querySelector('#current-origin'), scoreBlock: document.querySelector('#state-score-block'), stateDiagnostic: document.querySelector('#state-diagnostic'), stateScope: document.querySelector('#state-scope'), stateAreas: document.querySelector('#state-areas'), stateNotice: document.querySelector('#state-notice'), summaryCount: document.querySelector('#summary-count'),
  prioritySummary: document.querySelector('#priority-summary'), items: document.querySelector('#plan-items'), template: document.querySelector('#plan-item-template'),
  actionsDate: document.querySelector('#actions-date'), actionsNotice: document.querySelector('#actions-notice'), actionsEmpty: document.querySelector('#actions-empty'), actionsVerification: document.querySelector('#actions-verification'), verificationCount: document.querySelector('#actions-verification-count'), verificationList: document.querySelector('#actions-verification-list'),
  checkAvailable: document.querySelector('#check-available'), checkDeadline: document.querySelector('#check-deadline'), checkRecommendation: document.querySelector('#check-recommendation'), checkStart: document.querySelector('#check-start'), checkConfirm: document.querySelector('#check-confirm'), checkCancel: document.querySelector('#check-cancel'), checkSubmit: document.querySelector('#check-submit'), checkProgress: document.querySelector('#check-progress'), checkMessage: document.querySelector('#check-message'), checkResult: document.querySelector('#check-result'), checkComparison: document.querySelector('#check-comparison'), checkNotComparable: document.querySelector('#check-not-comparable'), checkCurrentScore: document.querySelector('#check-current-score'), checkBefore: document.querySelector('#check-before'), checkNow: document.querySelector('#check-now'), checkChange: document.querySelector('#check-change'), checkLower: document.querySelector('#check-lower'), checkCorrected: document.querySelector('#check-corrected'), checkCorrectedLabel: document.querySelector('#check-corrected-label'), checkPending: document.querySelector('#check-pending'), checkPendingLabel: document.querySelector('#check-pending-label'), checkItems: document.querySelector('#check-items'), checkBeforeDate: document.querySelector('#check-before-date'), checkNowDate: document.querySelector('#check-now-date'), checkNotComparableDate: document.querySelector('#check-noncomparable-date'), checkFree: document.querySelector('#check-free'), continuousMonitoring: document.querySelector('#continuous-monitoring'),
};
const requiredItemFields = ['control_code', 'name', 'priority', 'finding', 'recommendation', 'action_steps', 'validation_step'];
const requestTimeoutMs = 10000;
let requestInProgress = false;
let checkInProgress = false;
let currentToken = null;
const requestedSiteId = new URLSearchParams(window.location.search).get('workspace_site_id');
const entitledSiteId = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(requestedSiteId || '') ? requestedSiteId : null;
const waitForAuth = () => window.MininodeAuth
  ? Promise.resolve(window.MininodeAuth)
  : new Promise((resolve) => window.addEventListener('mininode:auth-api-ready',
      () => resolve(window.MininodeAuth), { once: true }));
const authorizedHeaders = async () => {
  const auth = await waitForAuth();
  await auth.ready();
  const token = await auth.getToken();
  if (!token) throw new Error('auth_required');
  return { Accept: 'application/json', Authorization: `Bearer ${token}` };
};


const accessTokenFromPath = () => {
  const match = window.location.pathname.match(/^\/privacy\/plan\/([^/]+)\/?$/);
  if (!match) return null;
  try { return decodeURIComponent(match[1]); } catch { return null; }
};
const validPlanResponse = (data) => {
  if (!data || typeof data.site_url !== 'string' || !data.site_url || !data.plan) return false;
  const plan = data.plan;
  if (typeof plan.version !== 'string' || typeof plan.actions_version !== 'string' || !Number.isInteger(plan.initial_score) || !Number.isInteger(plan.item_count) || !Array.isArray(plan.items) || plan.item_count !== plan.items.length) return false;
  return plan.items.every((item) => item && requiredItemFields.every((field) => Object.hasOwn(item, field)) && typeof item.control_code === 'string' && typeof item.name === 'string' && typeof item.priority === 'string' && typeof item.finding === 'string' && typeof item.recommendation === 'string' && Array.isArray(item.action_steps) && item.action_steps.every((step) => typeof step === 'string') && typeof item.validation_step === 'string');
};
const friendlySite = (siteUrl) => { try { return new URL(siteUrl).host || siteUrl; } catch { return siteUrl; } };
const friendlyDate = (value) => new Intl.DateTimeFormat('es-CL', { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(value));
// A missing or malformed C3a contract is not equivalent to zero pending findings.
const validCurrentActions = (value) => {
  if (!value || !['available', 'version_mismatch'].includes(value.status)
      || !['initial', 'review'].includes(value.source)
      || typeof value.created_at !== 'string'
      || !Number.isFinite(Date.parse(value.created_at))) return false;
  if (value.status === 'version_mismatch') {
    return value.item_count === null && value.verification_pending_count === null
      && value.actions_version === null && Array.isArray(value.items)
      && value.items.length === 0 && Array.isArray(value.verification_pending)
      && value.verification_pending.length === 0;
  }
  return typeof value.actions_version === 'string'
    && Number.isInteger(value.item_count) && value.item_count >= 0
    && Array.isArray(value.items) && value.item_count === value.items.length
    && value.items.every((item) => item && requiredItemFields.every((field) => Object.hasOwn(item, field))
      && typeof item.control_code === 'string' && typeof item.name === 'string'
      && ['Alta', 'Media', 'Baja'].includes(item.priority)
      && typeof item.finding === 'string' && typeof item.recommendation === 'string'
      && Array.isArray(item.action_steps) && item.action_steps.every((step) => typeof step === 'string')
      && typeof item.validation_step === 'string')
    && Number.isInteger(value.verification_pending_count)
    && value.verification_pending_count >= 0
    && Array.isArray(value.verification_pending)
    && value.verification_pending_count === value.verification_pending.length
    && value.verification_pending.every((item) => item && typeof item.control_code === 'string'
      && typeof item.name === 'string' && item.status === 'pending_verification'
      && ['not_evaluable', 'not_applicable', 'missing'].includes(item.reason));
};
const unavailableActions = (message) => {
  elements.items.replaceChildren();
  elements.verificationList.replaceChildren();
  elements.actionsVerification.hidden = true;
  elements.actionsEmpty.hidden = true;
  elements.actionsDate.hidden = true;
  elements.summaryCount.textContent = '';
  elements.prioritySummary.textContent = '';
  elements.actionsNotice.textContent = message;
  elements.actionsNotice.hidden = false;
};
const renderCurrentActions = (currentActions, legacyPlan) => {
  const legacy = Boolean(!entitledSiteId && legacyPlan);
  const actions = legacy
    ? { status: 'available', source: 'initial', items: legacyPlan.items,
        item_count: legacyPlan.item_count, verification_pending: [], verification_pending_count: 0 }
    : currentActions;
  if (!legacy && !validCurrentActions(actions)) {
    unavailableActions('No pudimos cargar las recomendaciones vigentes. Recarga la página para volver a consultarlas.');
    return;
  }
  if (actions.status === 'version_mismatch') {
    unavailableActions('La última revisión utiliza una versión del análisis que no permite generar recomendaciones confiables. No podemos confirmar que no existan mejoras pendientes.');
    return;
  }
  elements.actionsNotice.hidden = true;
  elements.items.replaceChildren();
  elements.verificationList.replaceChildren();
  elements.actionsDate.hidden = false;
  elements.actionsDate.textContent = legacy
    ? 'Recomendaciones del diagnóstico inicial (acceso anterior; no reflejan revisiones posteriores).'
    : `${actions.source === 'initial' ? 'Basado en el diagnóstico inicial' : 'Basado en la última revisión válida'} · ${friendlyDate(actions.created_at)}`;
  elements.summaryCount.textContent = actions.item_count === 0
    ? 'Sin mejoras accionables detectadas'
    : `${actions.item_count} ${actions.item_count === 1 ? 'mejora pendiente' : 'mejoras pendientes'}`;
  const counts = actions.items.reduce((result, item) => {
    result[item.priority] = (result[item.priority] || 0) + 1;
    return result;
  }, {});
  elements.prioritySummary.textContent = ['Alta', 'Media', 'Baja']
    .filter((priority) => counts[priority] > 0)
    .map((priority) => `${counts[priority]} de prioridad ${priority.toLowerCase()}`)
    .join(' · ');
  actions.items.forEach(renderItem);
  elements.actionsVerification.hidden = legacy || actions.verification_pending_count === 0;
  if (!legacy && actions.verification_pending_count > 0) {
    const count = actions.verification_pending_count;
    elements.verificationCount.textContent = `${count} ${count === 1 ? 'control requiere' : 'controles requieren'} verificación`;
    const labels = {
      not_evaluable: 'Resultado no concluyente',
      not_applicable: 'No aplica en esta revisión',
      missing: 'No evaluado en esta revisión',
    };
    actions.verification_pending.forEach((item) => {
      const row = addText(elements.verificationList, 'li', '', 'plan-actions__verification-item');
      addText(row, 'span', window.MininodePrivacyControlUX?.name(item.control_code, item.name) ?? item.name);
      addText(row, 'small', labels[item.reason], 'plan-actions__verification-reason');
    });
  }
  elements.actionsEmpty.hidden = actions.item_count !== 0;
  if (actions.item_count === 0) {
    elements.actionsEmpty.textContent = actions.verification_pending_count > 0
      ? 'No se detectaron mejoras concretas en esta revisión, pero hay controles sin resultado confirmado.'
      : 'No se detectaron mejoras pendientes en el alcance observado. Esto no acredita cumplimiento legal.';
  }
};
const diagnosticAreas = ['Transparencia', 'Formularios', 'Cookies', 'Contacto', 'Seguridad'];
const diagnosticStates = {
  detected: 'Detectado',
  partial: 'Parcialmente detectado',
  not_detected: 'No detectado',
  not_evaluable: 'No concluyente',
  not_applicable: 'No aplica',
};
const addText = (parent, tag, value, className) => {
  const element = document.createElement(tag);
  element.textContent = value;
  if (className) element.className = className;
  parent.append(element);
  return element;
};
const validDiagnostic = (diagnostic) => {
  const current = diagnostic?.current;
  return diagnostic?.initial && Number.isInteger(diagnostic.initial.score)
    && current && Number.isInteger(current.score) && current.score >= 0 && current.score <= 100
    && (current.source === 'initial' || current.source === 'review')
    && typeof current.created_at === 'string' && Number.isFinite(Date.parse(current.created_at))
    && Array.isArray(current.controls)
    && current.controls.every((item) => item && typeof item.control_code === 'string'
      && typeof item.name === 'string' && typeof item.result === 'string'
      && (item.area === null || typeof item.area === 'string')
      && (item.reason == null || typeof item.reason === 'string')
      && (item.evidence_summary == null || typeof item.evidence_summary === 'string')
      && (item.source_url == null || typeof item.source_url === 'string'));
};
const unavailableState = (message) => {
  elements.scoreBlock.hidden = true;
  elements.stateDiagnostic.hidden = true;
  elements.stateAreas.replaceChildren();
  elements.stateNotice.textContent = message;
  elements.stateNotice.hidden = false;
};
const safeEvidenceUrl = (value) => {
  if (typeof value !== 'string') return null;
  try {
    const url = new URL(value);
    if (!['https:', 'http:'].includes(url.protocol) || !url.hostname
        || url.username || url.password) return null;
    url.search = '';
    url.hash = '';
    return url.href;
  } catch { return null; }
};
const renderState = (diagnostic) => {
  if (!diagnostic) {
    unavailableState('El detalle del diagnóstico no está disponible para este acceso. Las mejoras y revisiones existentes siguen disponibles.');
    return;
  }
  if (!validDiagnostic(diagnostic)) {
    unavailableState('No pudimos mostrar el diagnóstico actual. Actualiza la página para intentarlo nuevamente.');
    return;
  }
  const current = diagnostic.current;
  elements.stateNotice.hidden = true;
  elements.scoreBlock.hidden = false;
  elements.stateDiagnostic.hidden = false;
  elements.currentScore.textContent = `${current.score} / 100`;
  elements.currentDate.textContent = friendlyDate(current.created_at);
  elements.currentOrigin.textContent = current.source === 'initial'
    ? 'Primera revisión del sitio' : 'Última revisión válida';
  const pages = current.scope?.pages_analyzed;
  const notes = [];
  if (Number.isInteger(pages) && pages >= 0) notes.push(`${pages} ${pages === 1 ? 'página analizada' : 'páginas analizadas'}`);
  if (current.scope?.limited === true) notes.push('Revisión con alcance limitado');
  elements.stateScope.textContent = notes.join(' · ') || 'Resultados de los controles observables del sitio';
  elements.stateAreas.replaceChildren();

  const groups = [...diagnosticAreas];
  if (current.controls.some((item) => !diagnosticAreas.includes(item.area))) {
    groups.push('Otros controles de esta revisión');
  }
  groups.forEach((area) => {
    const controls = current.controls.filter((item) =>
      area === 'Otros controles de esta revisión'
        ? !diagnosticAreas.includes(item.area) : item.area === area);
    const container = addText(elements.stateAreas, 'details', '', 'plan-state__area');
    const summary = addText(container, 'summary', '', 'plan-state__area-summary');
    addText(summary, 'strong', area);
    const counts = Object.keys(diagnosticStates).map((code) => {
      const amount = controls.filter((item) => item.result === code).length;
      return amount ? `${amount} ${amount === 1 ? diagnosticStates[code].toLowerCase() : ({
        detected: 'detectados', partial: 'parcialmente detectados',
        not_detected: 'no detectados', not_evaluable: 'no concluyentes',
        not_applicable: 'no aplicables',
      })[code]}` : null;
    }).filter(Boolean);
    const unknown = controls.filter((item) => !Object.hasOwn(diagnosticStates, item.result)).length;
    if (unknown) counts.push(`${unknown} sin resultado reconocido`);
    addText(summary, 'small', counts.join(' · ') || 'Sin controles registrados');
    const list = addText(container, 'div', '', 'plan-state__controls');
    if (controls.length === 0) {
      addText(list, 'p', 'No hay controles registrados para esta área en la revisión.', 'plan-state__empty');
      return;
    }
    const renderControl = (target, item) => {
      const detail = addText(target, 'details', '', 'plan-state__control');
      const heading = addText(detail, 'summary', '', 'plan-state__control-summary');
      addText(heading, 'span', window.MininodePrivacyControlUX?.name(item.control_code, item.name) ?? item.name, 'plan-state__control-name');
      addText(heading, 'span', diagnosticStates[item.result] || 'Sin resultado reconocido', 'plan-state__result');
      const body = addText(detail, 'div', '', 'plan-state__control-body');
      const description = window.MininodePrivacyControlUX?.description(item.control_code);
      if (description) addText(body, 'p', description, 'plan-state__description');
      addText(body, 'p', item.reason || 'No se registró una explicación para este resultado.');
      if (item.evidence_summary) {
        addText(body, 'p', 'Evidencia observada', 'plan-state__field');
        addText(body, 'p', item.evidence_summary);
      } else {
        addText(body, 'p', 'Sin resumen adicional de evidencia disponible para esta revisión.', 'plan-state__muted');
      }
      const source = safeEvidenceUrl(item.source_url);
      if (source) {
        const link = addText(body, 'a', 'Consultar página observada');
        link.href = source;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
      }
      if (item.type === 'context') addText(body, 'p', 'Control informativo: no determina por sí solo el score.', 'plan-state__muted');
      if (item.result === 'not_evaluable') addText(body, 'p', 'La evaluación no permite concluir el resultado de este control.', 'plan-state__muted');
      if (item.confidence === 'low') addText(body, 'p', 'Confianza de evaluación: baja.', 'plan-state__muted');
      addText(body, 'p', item.control_code, 'plan-state__code');
    };
    controls.filter((item) => item.result !== 'not_applicable')
      .forEach((item) => renderControl(list, item));
    const notApplicable = controls.filter((item) => item.result === 'not_applicable');
    if (notApplicable.length) {
      const deferred = addText(list, 'details', '', 'plan-state__deferred');
      const toggle = addText(deferred, 'summary', '', 'plan-state__deferred-summary');
      addText(toggle, 'span', `Mostrar ${notApplicable.length} ${notApplicable.length === 1 ? 'control no aplicable' : 'controles no aplicables'}`);
      const contents = addText(deferred, 'div', '', 'plan-state__deferred-controls');
      notApplicable.forEach((item) => renderControl(contents, item));
    }
  });
};

// Dates come from the stored diagnostic, never inferred from Plan creation.
const progressDate = (value) => typeof value === 'string' && Number.isFinite(Date.parse(value))
  ? friendlyDate(value) : 'Fecha no disponible';
const renderProgressDates = (diagnostic, review) => {
  // null denotes a review POST waiting for the refreshed read: keep the original date.
  if (diagnostic !== null) elements.checkBeforeDate.textContent = progressDate(diagnostic?.initial?.created_at);
  const currentAt = diagnostic?.current?.created_at || review?.created_at;
  elements.checkNowDate.textContent = progressDate(currentAt);
  elements.checkNotComparableDate.textContent = progressDate(currentAt);
};
const showError = (kind) => {
  const states = {
    missing: ['Privacy Web no disponible', 'No fue posible encontrar este acceso a Privacy Web. Verifique que el enlace esté completo.'],
    unavailable: ['No pudimos cargar Privacy Web', 'Privacy Web no está disponible temporalmente. Intente nuevamente en unos minutos.'],
    invalid: ['No pudimos mostrar Privacy Web', 'La información recibida no tiene el formato necesario para mostrar Privacy Web.'],
  };
  elements.loading.hidden = true; elements.content.hidden = true; elements.error.hidden = false;
  [elements.errorTitle.textContent, elements.errorMessage.textContent] = states[kind];
  elements.privacyLink.hidden = kind !== 'missing'; elements.retry.hidden = kind !== 'unavailable';
};
const renderItem = (item, index) => {
  const fragment = elements.template.content.cloneNode(true);
  fragment.querySelector('.plan-item__number').textContent = index + 1; fragment.querySelector('.plan-item__code').textContent = item.control_code;
  fragment.querySelector('.plan-item__name').textContent = window.MininodePrivacyControlUX?.name(item.control_code, item.name) ?? item.name;
  const priority = fragment.querySelector('.plan-item__priority'); priority.textContent = `Prioridad ${item.priority.toLowerCase()}`; priority.dataset.priority = item.priority.toLowerCase();
  fragment.querySelector('.plan-item__finding').textContent = item.finding; fragment.querySelector('.plan-item__recommendation').textContent = item.recommendation;
  fragment.querySelector('.plan-item__validation p').textContent = item.validation_step;
  item.action_steps.forEach((step) => { const li = document.createElement('li'); li.textContent = step; fragment.querySelector('.plan-item__steps').append(li); });
  elements.items.append(fragment);
};
const renderCheckResult = (review) => {
  const result = review.result;
  elements.checkResult.hidden = false;
  elements.checkMessage.hidden = true;
  elements.continuousMonitoring.hidden = false;
  const notComparable = result.comparability?.status === 'not_comparable';
  elements.checkComparison.hidden = notComparable;
  elements.checkNotComparable.hidden = !notComparable;
  if (notComparable) {
    elements.checkLower.hidden = true;
    elements.checkItems.replaceChildren();
    elements.checkCurrentScore.textContent = `${result.current_score} / 100`;

    return;
  }
  elements.checkBefore.textContent = `${result.original_score} / 100`;
  elements.checkNow.textContent = `${result.current_score} / 100`;
  elements.checkChange.textContent = result.score_change === 0
    ? 'Sin cambios en el score'
    : `${result.score_change > 0 ? '+' : ''}${result.score_change} puntos`;
  elements.checkLower.hidden = result.score_change >= 0;
  elements.checkCorrected.textContent = result.corrected_count;
  elements.checkCorrectedLabel.textContent = result.corrected_count === 1 ? 'mejora corregida' : 'mejoras corregidas';
  elements.checkPending.textContent = result.pending_count;
  elements.checkPendingLabel.textContent = result.pending_count === 1 ? 'todavía pendiente' : 'todavía pendientes';
  elements.checkItems.replaceChildren();
  result.items.forEach((item) => {
    const li = document.createElement('li');
    const corrected = item.status === 'corrected';
    const icon = document.createElement('span');
    const content = document.createElement('span');
    const status = document.createElement('small');
    icon.className = `check-item__icon check-item__icon--${corrected ? 'corrected' : 'pending'}`;
    icon.textContent = corrected ? '✓' : '⚠';
    icon.setAttribute('aria-hidden', 'true');
    content.textContent = window.MininodePrivacyControlUX?.name(item.control_id ?? item.control_code, item.name) ?? item.name;
    status.textContent = corrected ? 'Corregido' : item.status === 'still_pending' ? 'Sigue pendiente' : 'No fue posible evaluarlo';
    content.append(status);
    li.append(icon, content);
    elements.checkItems.append(li);
  });

};
const renderCheck = (check) => {
  if (!check) {
    document.querySelector('#improvement-check').hidden = true;
    return;
  }
  elements.checkAvailable.hidden = false;
  elements.checkConfirm.hidden = true;
  elements.checkMessage.hidden = true;
  elements.checkFree.hidden = true;
  elements.checkRecommendation.hidden = false;
  elements.checkStart.hidden = true;
  elements.checkResult.hidden = true;
  elements.continuousMonitoring.hidden = true;

  if (check.latest_check) {
    renderCheckResult(check.latest_check);
  }
  if (check.expires_at) {
    elements.checkDeadline.textContent = `Activo hasta: ${friendlyDate(check.expires_at)}`;
  }
  if (check.status === 'expired') {
    elements.checkDeadline.textContent = 'La vigencia de Privacy Web ha finalizado.';
    elements.checkRecommendation.hidden = true;
    elements.checkFree.hidden = false;
    return;
  }
  elements.checkStart.hidden = false;
};

const progressUI = {
  summary: document.querySelector('#progress-summary'),
  initial: document.querySelector('#progress-initial'),
  current: document.querySelector('#progress-current'),
  initialDate: document.querySelector('#progress-initial-date'),
  currentDate: document.querySelector('#progress-current-date'),
  delta: document.querySelector('#progress-delta'),
  counts: document.querySelector('#progress-counts'),
  history: document.querySelector('#progress-history-list'),
  chartSection: document.querySelector('#progress-chart-section'),
  chart: document.querySelector('#progress-chart'),
  chartNote: document.querySelector('#progress-chart-note'),
};
const progressLabels = { improved: 'Mejora', regressed: 'Retroceso',
  changed: 'Cambio', not_conclusive: 'No concluyente' };
const renderProgressComparison = (parent, comparison, heading) => {
  addText(parent, 'h4', heading);
  if (!comparison || comparison.comparability?.status !== 'comparable') {
    addText(parent, 'p', 'No se pueden comparar estas revisiones por diferencias de versión o información insuficiente.');
    return;
  }
  const delta = comparison.score_change;
  addText(parent, 'p', delta === 0 ? 'Sin variación en el score'
    : Number.isInteger(delta) ? `${delta > 0 ? '+' : ''}${delta} puntos` : 'Variación no disponible');
  const changes = Array.isArray(comparison.changes) ? comparison.changes : [];
  if (changes.length === 0) {
    addText(parent, 'p', 'Sin cambios detectados entre los controles comparables.');
    return;
  }
  const list = addText(parent, 'ul', '');
  changes.forEach((change) => {
    const name = window.MininodePrivacyControlUX?.name(change.control_code, change.control_code) ?? change.control_code;
    addText(list, 'li', `${name} (${change.control_code}) — ${progressLabels[change.status] || 'Cambio'}`);
  });
};
const renderProgressChart = (chronological) => {
  progressUI.chart.replaceChildren();
  progressUI.chartSection.hidden = chronological.length < 2;
  if (chronological.length < 2) return;
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', '0 0 560 135');
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', 'Evolución histórica del Privacy Score');
  svg.classList.add('plan-progress-svg');
  const points = chronological.map((entry, i) => ({
    x: 20 + 520 * i / (chronological.length - 1),
    y: 110 - entry.diagnostic.score * 0.9,
  }));
  for (let i = 1; i < points.length; i += 1) {
    if (chronological[i].vs_previous?.comparability?.status !== 'comparable') continue;
    const line = document.createElementNS(ns, 'line');
    line.setAttribute('x1', points[i - 1].x);
    line.setAttribute('y1', points[i - 1].y);
    line.setAttribute('x2', points[i].x);
    line.setAttribute('y2', points[i].y);
    line.setAttribute('class', 'plan-progress-line');
    svg.append(line);
  }
  chronological.forEach((entry, i) => {
    const circle = document.createElementNS(ns, 'circle');
    circle.setAttribute('cx', points[i].x);
    circle.setAttribute('cy', points[i].y);
    circle.setAttribute('r', 4);
    circle.setAttribute('class', 'plan-progress-dot');
    const tip = document.createElementNS(ns, 'title');
    tip.textContent = `${progressDate(entry.created_at)}: ${entry.diagnostic.score}/100`;
    circle.append(tip);
    svg.append(circle);
  });
  progressUI.chart.append(svg);
  progressUI.chartNote.textContent = 'Cada punto representa una revisión. No se unen resultados de versiones incompatibles.';
};
const invalidateProgressHistory = () => {
  // A successful POST has changed the persisted history. Never show stale data as current.
  progressUI.summary.hidden = true;
  progressUI.chartSection.hidden = true;
  progressUI.history.replaceChildren();
  const notice = addText(progressUI.history, 'p',
    'La revisión se guardó, pero no pudimos actualizar tus avances. Recarga la página para ver los resultados más recientes.');
  notice.setAttribute('role', 'status');
};
const renderProgressHistory = (history) => {
  progressUI.history.replaceChildren();
  progressUI.summary.hidden = true;
  progressUI.chartSection.hidden = true;
  if (!Array.isArray(history) || history.length === 0) {
    addText(progressUI.history, 'p', 'El historial no está disponible para este acceso.');
    return;
  }
  const initial = history[history.length - 1];
  const latest = history[0];
  if (!initial?.diagnostic || !latest?.diagnostic) return;
  progressUI.summary.hidden = false;
  progressUI.initial.textContent = `${initial.diagnostic.score}/100`;
  progressUI.current.textContent = `${latest.diagnostic.score}/100`;
  progressUI.initialDate.textContent = progressDate(initial.created_at);
  progressUI.currentDate.textContent = progressDate(latest.created_at);
  const compared = latest.kind === 'review' ? latest.vs_initial : null;
  progressUI.delta.textContent = latest.kind === 'initial'
    ? 'Este es tu punto de partida. Todavía no hay revisiones adicionales.'
    : compared?.comparability?.status !== 'comparable'
      ? 'Los diagnósticos utilizan versiones incompatibles; no corresponde comparar puntuaciones.'
      : compared.score_change === 0 ? 'Sin variación respecto del diagnóstico inicial.'
        : `${compared.score_change > 0 ? '+' : ''}${compared.score_change} puntos respecto del diagnóstico inicial.`;
  if (latest.kind === 'review' && compared?.comparability?.status === 'comparable') {
    const changes = compared.changes || [];
    const count = (status) => changes.filter(item => item.status === status).length;
    progressUI.counts.textContent = `${count('improved')} mejoras · ${count('regressed')} retrocesos · ${count('not_conclusive')} no concluyentes`;
  } else progressUI.counts.textContent = '';
  history.forEach((entry) => {
    const details = addText(progressUI.history, 'details', '', 'plan-progress-entry');
    const summary = addText(details, 'summary', '');
    addText(summary, 'strong', `${entry.kind === 'initial' ? 'Diagnóstico inicial' : 'Revisión'} · ${entry.diagnostic.score}/100`);
    addText(summary, 'small', progressDate(entry.created_at));
    if (entry.kind === 'initial') {
      addText(details, 'p', 'Punto de partida del seguimiento.');
      return;
    }
    const detail = addText(details, 'div', '', 'plan-progress-entry-detail');
    renderProgressComparison(detail, entry.vs_previous, 'Frente a la revisión anterior');
    renderProgressComparison(detail, entry.vs_initial, 'Frente al diagnóstico inicial');
  });
  renderProgressChart([...history].reverse());
};

const render = ({ site_url: siteUrl, plan, check, diagnostic, current_actions: currentActions, history }) => {
  elements.site.textContent = friendlySite(siteUrl);
  renderState(diagnostic);
  renderCurrentActions(currentActions, entitledSiteId ? null : plan);
  renderCheck(check);
  renderProgressHistory(entitledSiteId ? history : null);
  renderProgressDates(diagnostic, check?.latest_check);
  elements.loading.hidden = true;
  elements.content.hidden = false;
};
const performCheck = async () => {
  if (checkInProgress || (!currentToken && !entitledSiteId)) return;
  checkInProgress = true;
  elements.checkSubmit.disabled = true;
  elements.checkCancel.disabled = true;
  elements.checkProgress.hidden = false;
  elements.checkMessage.hidden = true;
  try {
    const response = entitledSiteId
      ? await fetch(`/api/privacy/workspace-sites/${encodeURIComponent(entitledSiteId)}/plan/check`, {
        method: 'POST',
        headers: await authorizedHeaders(),
      })
      : await fetch(`/api/privacy/correction-plans/${encodeURIComponent(currentToken)}/check`, {
        method: 'POST',
        headers: { Accept: 'application/json' },
      });
    const data = await response.json();
    if (!response.ok) {
      elements.checkMessage.textContent = data.detail || 'No pudimos completar la revisión. Intente nuevamente en unos minutos.';
      elements.checkMessage.hidden = false;
      if (response.status === 410) {
        elements.checkDeadline.textContent = 'La vigencia de Privacy Web ha finalizado.';
        elements.checkRecommendation.hidden = true;
        elements.checkConfirm.hidden = true;
        elements.checkStart.hidden = true;
        elements.checkFree.hidden = false;
      }
      return;
    }
    renderCheckResult(data);
    renderProgressDates(null, data);
    if (entitledSiteId) {
      // The review is persisted. Do not keep presenting pre-review actions.
      unavailableActions('La revisión se guardó. Actualizando las recomendaciones vigentes…');
      const refreshController = new AbortController();
      const refreshTimeout = setTimeout(() => refreshController.abort(), requestTimeoutMs);
      try {
        // A completed review is persisted; refresh C2 without another scan.
        const refreshed = await fetch(
          `/api/privacy/workspace-sites/${encodeURIComponent(entitledSiteId)}/plan`,
          { method: 'GET', headers: await authorizedHeaders(), signal: refreshController.signal },
        );
        if (!refreshed.ok) throw new Error('current_diagnostic_unavailable');
        const latest = await refreshed.json();
        if (!validDiagnostic(latest?.diagnostic)) throw new Error('invalid_diagnostic');
        renderState(latest.diagnostic);
        renderCurrentActions(latest.current_actions, null);
        renderProgressHistory(latest.history);
        renderProgressDates(latest.diagnostic, data);
      } catch {
        invalidateProgressHistory();
        unavailableState('La revisión se guardó, pero no pudimos actualizar el diagnóstico actual. Recarga la página para consultarlo.');
        unavailableActions('La revisión se guardó, pero no pudimos actualizar las recomendaciones vigentes. Recarga la página.');
      } finally {
        clearTimeout(refreshTimeout);
      }
    }
    if (data.expires_at) {
      elements.checkDeadline.textContent = `Activo hasta: ${friendlyDate(data.expires_at)}`;
    }
    elements.checkConfirm.hidden = true;
    elements.checkStart.hidden = false;
    elements.checkRecommendation.hidden = false;
    elements.checkFree.hidden = true;
  } catch {
    elements.checkMessage.textContent = 'No pudimos completar la revisión. Intente nuevamente en unos minutos.';
    elements.checkMessage.hidden = false;
  } finally {
    checkInProgress = false;
    elements.checkSubmit.disabled = false;
    elements.checkCancel.disabled = false;
    elements.checkProgress.hidden = true;
  }
};
const loadPlan = async () => {
  if (requestInProgress) return;
  const token = accessTokenFromPath();
  if (!token && !entitledSiteId) { showError('missing'); return; }

  currentToken = token; requestInProgress = true;
  elements.retry.disabled = true;
  elements.error.hidden = true;
  elements.content.hidden = true;
  elements.loading.hidden = false;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), requestTimeoutMs);

  try {
    // Prefer a read: naturally expired plans remain visible with their last
    // review, but never permit another inspection. Create only when active
    // entitlement has no baseline yet.
    let response;
    if (entitledSiteId) {
      const path = `/api/privacy/workspace-sites/${encodeURIComponent(entitledSiteId)}/plan`;
      const headers = await authorizedHeaders();
      response = await fetch(path, { method: 'GET', headers, signal: controller.signal });
      if (response.status === 409) {
        response = await fetch(path, { method: 'POST', headers, signal: controller.signal });
      }
    } else {
      response = await fetch(`/api/privacy/correction-plans/${encodeURIComponent(token)}`, {
        method: 'GET',
        headers: { Accept: 'application/json' },
        signal: controller.signal,
      });
    }
    if ([401, 403, 404, 409].includes(response.status)) { showError('missing'); return; }
    if (!response.ok) { showError('unavailable'); return; }
    let data;
    try { data = await response.json(); } catch { showError('invalid'); return; }
    if (!validPlanResponse(data)) { showError('invalid'); return; } render(data);
  } catch { showError('unavailable'); }
  finally {
    clearTimeout(timeoutId);
    requestInProgress = false;
    elements.retry.disabled = false;
    elements.loading.hidden = true;
  }
};
elements.retry.addEventListener('click', loadPlan);
elements.checkStart.addEventListener('click', () => { elements.checkStart.hidden = true; elements.checkConfirm.hidden = false; });
elements.checkCancel.addEventListener('click', () => { if (!checkInProgress) { elements.checkConfirm.hidden = true; elements.checkStart.hidden = false; } });
elements.checkSubmit.addEventListener('click', performCheck);
loadPlan();

const planTabIds = ['state', 'actions', 'progress'];
const setPlanTab = (selected) => {
  planTabIds.forEach((id) => {
    const button = document.querySelector(`#plan-tab-${id}`);
    const panel = document.querySelector(`#plan-panel-${id}`);
    const active = id === selected;
    panel.hidden = !active;
    button.setAttribute('aria-current', active ? 'page' : 'false');
    button.tabIndex = active ? 0 : -1;
  });
};
planTabIds.forEach((id, index) => {
  const button = document.querySelector(`#plan-tab-${id}`);
  button.addEventListener('click', () => setPlanTab(id));
  button.addEventListener('keydown', (event) => {
    if (!['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? planTabIds.length - 1
      : (index + (event.key === 'ArrowRight' ? 1 : -1) + planTabIds.length) % planTabIds.length;
    setPlanTab(planTabIds[next]);
    document.querySelector(`#plan-tab-${planTabIds[next]}`).focus();
  });
});
setPlanTab('state');
