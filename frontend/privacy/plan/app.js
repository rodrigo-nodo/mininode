const elements = {
  loading: document.querySelector('#plan-loading'), content: document.querySelector('#plan-content'), error: document.querySelector('#plan-error'),
  errorTitle: document.querySelector('#error-title'), errorMessage: document.querySelector('#error-message'), retry: document.querySelector('#retry'), privacyLink: document.querySelector('#privacy-link'),
  site: document.querySelector('#site-url'), score: document.querySelector('#initial-score'), itemCount: document.querySelector('#item-count'), summaryCount: document.querySelector('#summary-count'), closingCount: document.querySelector('#closing-count'),
  prioritySummary: document.querySelector('#priority-summary'), items: document.querySelector('#plan-items'), template: document.querySelector('#plan-item-template'),
};
const displayNames = { 'PRV-003': 'Política de privacidad claramente asociada a la empresa' };
const requiredItemFields = ['control_code', 'name', 'priority', 'finding', 'recommendation', 'action_steps', 'validation_step'];
const requestTimeoutMs = 10000;
let requestInProgress = false;

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
const showError = (kind) => {
  const states = {
    missing: ['Plan no disponible', 'No fue posible encontrar este Plan de corrección. Verifique que el enlace esté completo.'],
    unavailable: ['No pudimos cargar el Plan', 'El Plan no está disponible temporalmente. Intente nuevamente en unos minutos.'],
    invalid: ['No pudimos mostrar este Plan', 'La información recibida no tiene el formato necesario para mostrar el Plan.'],
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
const render = ({ site_url: siteUrl, plan }) => {
  elements.site.textContent = friendlySite(siteUrl); elements.score.textContent = `${plan.initial_score} / 100`;
  elements.itemCount.textContent = plan.item_count; elements.summaryCount.textContent = plan.item_count; elements.closingCount.textContent = plan.item_count;
  const counts = plan.items.reduce((result, item) => { result[item.priority] = (result[item.priority] || 0) + 1; return result; }, {});
  ['Alta', 'Media', 'Baja'].forEach((priority) => { const li = document.createElement('li'); const strong = document.createElement('strong'); const span = document.createElement('span'); strong.textContent = counts[priority] || 0; span.textContent = `prioridad ${priority.toLowerCase()}`; li.append(strong, span); elements.prioritySummary.append(li); });
  plan.items.forEach(renderItem); elements.loading.hidden = true; elements.content.hidden = false;
};
const loadPlan = async () => {
  if (requestInProgress) return;
  const token = accessTokenFromPath();
  if (!token) { showError('missing'); return; }

  requestInProgress = true;
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
loadPlan();
