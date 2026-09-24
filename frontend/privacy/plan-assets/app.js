const elements = {
  loading: document.querySelector('#plan-loading'), content: document.querySelector('#plan-content'), error: document.querySelector('#plan-error'),
  errorTitle: document.querySelector('#error-title'), errorMessage: document.querySelector('#error-message'), retry: document.querySelector('#retry'), privacyLink: document.querySelector('#privacy-link'),
  site: document.querySelector('#site-url'), score: document.querySelector('#initial-score'), itemCount: document.querySelector('#item-count'), summaryCount: document.querySelector('#summary-count'), closingCount: document.querySelector('#closing-count'),
  prioritySummary: document.querySelector('#priority-summary'), items: document.querySelector('#plan-items'), template: document.querySelector('#plan-item-template'),
  checkAvailable: document.querySelector('#check-available'), checkDeadline: document.querySelector('#check-deadline'), checkRecommendation: document.querySelector('#check-recommendation'), checkStart: document.querySelector('#check-start'), checkConfirm: document.querySelector('#check-confirm'), checkCancel: document.querySelector('#check-cancel'), checkSubmit: document.querySelector('#check-submit'), checkProgress: document.querySelector('#check-progress'), checkMessage: document.querySelector('#check-message'), checkResult: document.querySelector('#check-result'), checkComparison: document.querySelector('#check-comparison'), checkNotComparable: document.querySelector('#check-not-comparable'), checkCurrentScore: document.querySelector('#check-current-score'), checkBefore: document.querySelector('#check-before'), checkNow: document.querySelector('#check-now'), checkChange: document.querySelector('#check-change'), checkLower: document.querySelector('#check-lower'), checkCorrected: document.querySelector('#check-corrected'), checkCorrectedLabel: document.querySelector('#check-corrected-label'), checkPending: document.querySelector('#check-pending'), checkPendingLabel: document.querySelector('#check-pending-label'), checkItems: document.querySelector('#check-items'), checkCreated: document.querySelector('#check-created'), checkFree: document.querySelector('#check-free'), continuousMonitoring: document.querySelector('#continuous-monitoring'),
};
const displayNames = { 'PRV-003': 'Política de privacidad claramente asociada a la empresa' };
const requiredItemFields = ['control_code', 'name', 'priority', 'finding', 'recommendation', 'action_steps', 'validation_step'];
const requestTimeoutMs = 10000;
let requestInProgress = false;
let checkInProgress = false;
let currentToken = null;

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
  fragment.querySelector('.plan-item__name').textContent = displayNames[item.control_code] || item.name;
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
    elements.checkCreated.textContent = friendlyDate(review.created_at);
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
    content.textContent = item.name;
    status.textContent = corrected ? 'Corregido' : item.status === 'still_pending' ? 'Sigue pendiente' : 'No fue posible evaluarlo';
    content.append(status);
    li.append(icon, content);
    elements.checkItems.append(li);
  });
  elements.checkCreated.textContent = friendlyDate(review.created_at);
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
const performCheck = async () => {
  if (checkInProgress || !currentToken) return;
  checkInProgress = true;
  elements.checkSubmit.disabled = true;
  elements.checkCancel.disabled = true;
  elements.checkProgress.hidden = false;
  elements.checkMessage.hidden = true;
  try {
    const response = await fetch(`/api/privacy/correction-plans/${encodeURIComponent(currentToken)}/check`, {
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
  if (!token) { showError('missing'); return; }

  currentToken = token; requestInProgress = true;
  elements.retry.disabled = true;
  elements.error.hidden = true;
  elements.content.hidden = true;
  elements.loading.hidden = false;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), requestTimeoutMs);

  try {
    const response = await fetch(`/api/privacy/correction-plans/${encodeURIComponent(token)}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    });
    if (response.status === 404) { showError('missing'); return; }
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
