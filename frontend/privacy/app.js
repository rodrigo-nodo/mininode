const form = document.querySelector('#privacy-form');
const urlInput = document.querySelector('#site-url');
const urlError = document.querySelector('#url-error');
const requestError = document.querySelector('#request-error');
const submitButton = document.querySelector('#privacy-submit');
const loadingCard = document.querySelector('#privacy-loading');
const resultCard = document.querySelector('#privacy-result');
const analyzedUrl = document.querySelector('#analyzed-url');
const privacyScore = document.querySelector('#privacy-score');
const scoreValue = document.querySelector('#score-value');
const scoreStatus = document.querySelector('#score-status');
const diagnosticScope = document.querySelector('#diagnostic-scope');
const diagnosticAreas = document.querySelector('#diagnostic-areas');
const diagnosticControls = document.querySelector('#diagnostic-controls');
const diagnosticPriorities = document.querySelector('#diagnostic-priorities');
const correctionOffer = document.querySelector('#privacy-correction-offer');
const noPrioritiesOffer = document.querySelector('#privacy-no-priorities');
const correctionUnavailable = document.querySelector('#privacy-correction-unavailable');
const correctionUnavailableRetry = document.querySelector('#correction-unavailable-retry');
const orderOpenButton = document.querySelector('#correction-order-open');
const orderForm = document.querySelector('#correction-order-form');
const orderEmail = document.querySelector('#correction-order-email');
const orderSubmit = document.querySelector('#correction-order-submit');
const orderError = document.querySelector('#correction-order-error');
const orderSuccess = document.querySelector('#correction-order-success');
const orderAvailability = document.querySelector('#correction-order-availability');
const orderExpired = document.querySelector('#correction-order-expired');
const orderRetry = document.querySelector('#correction-order-retry');
const helpLink = document.querySelector('#how-it-works');
const headerHelpLink = document.querySelector('#help-link');
const modal = document.querySelector('#privacy-modal');
const modalPanel = modal?.querySelector('.privacy-modal__panel');
const modalTitle = document.querySelector('#privacy-modal-title');
const modalContent = document.querySelector('#privacy-modal-content');
const modalCloseButtons = modal?.querySelectorAll('[data-modal-close]') ?? [];
const focusableSelector = 'button, a[href], input, textarea, select, [tabindex]:not([tabindex="-1"])';
let lastFocusedElement = null;
let isDiagnosing = false;
let currentDiagnosticId = '';

const genericDiagnosticError = 'No pudimos completar el diagnóstico. Intenta nuevamente en unos minutos.';
const renderDiagnosticError = 'Recibimos el diagnóstico, pero no pudimos mostrar el resultado. Intenta nuevamente.';
const privacyAreas = [
  {
    name: 'Transparencia',
    controls: [
      { code: 'PRV-001', name: 'Política de privacidad visible' },
      { code: 'PRV-002', name: 'Política de privacidad accesible' },
      { code: 'PRV-003', name: 'Política atribuible al negocio' },
      { code: 'PRV-004', name: 'Fecha o versión de la política', informational: true },
      { code: 'PRV-005', name: 'Identificación del responsable' },
      { code: 'PRV-006', name: 'Canal para ejercer derechos' },
      { code: 'PRV-007', name: 'Categorías de datos tratados' },
      { code: 'PRV-008', name: 'Finalidades del tratamiento' },
      { code: 'PRV-009', name: 'Base declarada del tratamiento', informational: true },
      { code: 'PRV-010', name: 'Destinatarios o terceros' },
      { code: 'PRV-011', name: 'Derechos de las personas' },
      { code: 'PRV-012', name: 'Conservación de datos' },
      { code: 'PRV-013', name: 'Reclamo ante la Agencia' },
      { code: 'PRV-014', name: 'Retiro del consentimiento' },
    ],
  },
  {
    name: 'Formularios',
    controls: [
      { code: 'PRV-101', name: 'Recopilación de datos personales' },
      { code: 'PRV-104', name: 'Información o consentimiento en formularios' },
    ],
  },
  { name: 'Cookies', controls: [{ code: 'PRV-201', name: 'Uso o información sobre cookies' }] },
  { name: 'Contacto', controls: [{ code: 'PRV-301', name: 'Canal de contacto visible' }] },
  { name: 'Seguridad', controls: [{ code: 'PRV-501', name: 'HTTPS activo' }] },
];

const AREA_INFO = {
  Transparencia: {
    what: 'Si el sitio entrega información clara sobre cómo se tratan los datos personales y quién es responsable de ese tratamiento.',
    why: 'Permite que las personas entiendan qué ocurre con sus datos y conozcan cómo ejercer sus derechos.',
    basis: 'Esta área se relaciona con los deberes de información y transparencia de la normativa sobre protección de datos personales.',
  },
  Formularios: {
    what: 'Cómo el sitio solicita datos personales mediante formularios y qué información entrega al momento de recopilarlos.',
    why: 'Cuando una persona entrega sus datos, necesita información suficiente para comprender su recopilación y uso.',
    basis: 'Esta área se relaciona con los deberes de información y con las condiciones aplicables a la recopilación y tratamiento de datos personales.',
  },
  Cookies: {
    what: 'Señales visibles relacionadas con el uso de cookies y tecnologías similares en el sitio.',
    why: 'Algunas de estas tecnologías pueden recopilar información sobre las personas y su navegación.',
    basis: 'Esta área se relaciona con la transparencia sobre la recopilación y el uso de información asociada a las personas.',
  },
  Contacto: {
    what: 'Si el sitio ofrece medios públicos que permitan comunicarse con el negocio.',
    why: 'Un canal de contacto facilita que las personas puedan realizar consultas y solicitudes relacionadas con sus datos personales.',
    basis: 'Esta área se relaciona con la posibilidad de ejercer derechos y comunicarse con quien trata los datos personales.',
  },
  Seguridad: {
    what: 'Señales técnicas de seguridad que pueden observarse públicamente desde el sitio.',
    why: 'Estas señales ayudan a identificar si la información se transmite bajo condiciones técnicas básicas de protección.',
    basis: 'Esta área se relaciona con el deber de adoptar medidas apropiadas para proteger los datos personales.',
  },
};

const resultLabels = {
  detected: { label: 'Bien', className: 'good' },
  partial: { label: 'Puede mejorar', className: 'improve' },
  not_detected: { label: 'Necesita atención', className: 'attention' },
  not_evaluable: { label: 'No pudimos revisarlo', className: 'neutral' },
  not_applicable: { label: 'No aplica', className: 'neutral' },
};

const normalizeUrl = (value) => {
  const trimmedValue = value.trim();

  if (!trimmedValue) {
    return '';
  }

  if (/^https?:\/\//i.test(trimmedValue)) {
    return trimmedValue;
  }

  return `https://${trimmedValue}`;
};

const isValidUrl = (value) => {
  const normalizedUrl = normalizeUrl(value);

  if (!normalizedUrl) {
    return false;
  }

  try {
    const parsedUrl = new URL(normalizedUrl);
    const hostnameParts = parsedUrl.hostname.split('.').filter(Boolean);
    const hasValidProtocol = parsedUrl.protocol === 'http:' || parsedUrl.protocol === 'https:';
    const hasDomain = hostnameParts.length >= 2;
    const hasLetters = /[a-z]/i.test(parsedUrl.hostname);
    const hasValidHostname = hostnameParts.every((part) => /^[a-z0-9-]+$/i.test(part) && !part.startsWith('-') && !part.endsWith('-'));
    const hasValidTopLevelDomain = /^[a-z]{2,}$/i.test(hostnameParts.at(-1));

    return hasValidProtocol && hasDomain && hasLetters && hasValidHostname && hasValidTopLevelDomain;
  } catch {
    return false;
  }
};

const setSubmitText = (text) => {
  submitButton.innerHTML = `${text} <span aria-hidden="true">→</span>`;
};

const setUrlError = (isInvalid) => {
  urlError.hidden = !isInvalid;
  urlInput.setAttribute('aria-invalid', String(isInvalid));
};

const setRequestError = (message = '') => {
  requestError.textContent = message;
  requestError.hidden = !message;
};

const appendTextElement = (parent, tagName, text, className) => {
  const element = document.createElement(tagName);
  element.textContent = text;
  if (className) {
    element.className = className;
  }
  parent.append(element);
  return element;
};

const getAreaResult = (area, controlsByCode) => {
  const results = area.controls
    .filter((control) => !control.informational)
    .map((control) => controlsByCode.get(control.code)?.result)
    .filter(Boolean);

  if (results.length === 0 || results.every((result) => result === 'not_evaluable')) {
    return 'not_evaluable';
  }
  if (results.every((result) => result === 'not_applicable')) {
    return 'not_applicable';
  }
  if (results.includes('not_detected')) {
    return 'not_detected';
  }
  if (results.includes('partial')) {
    return 'partial';
  }

  const evaluable = results.filter((result) => result !== 'not_evaluable' && result !== 'not_applicable');
  return evaluable.length > 0 && evaluable.every((result) => result === 'detected')
    ? 'detected'
    : 'not_evaluable';
};

const renderAreasAndControls = (controls) => {
  diagnosticAreas.replaceChildren();
  diagnosticControls.replaceChildren();
  const controlsByCode = new Map(
    (Array.isArray(controls) ? controls : [])
      .filter((control) => control && typeof control.control_code === 'string')
      .map((control) => [control.control_code, control]),
  );

  privacyAreas.forEach((area) => {
    const areaResult = resultLabels[getAreaResult(area, controlsByCode)];
    const areaSummary = appendTextElement(diagnosticAreas, 'article', '', 'privacy-area');
    const areaInfoButton = appendTextElement(areaSummary, 'button', '', 'privacy-area__info');
    areaInfoButton.type = 'button';
    areaInfoButton.setAttribute('aria-label', `Información sobre el área ${area.name}`);
    appendTextElement(areaInfoButton, 'span', area.name);
    appendTextElement(areaInfoButton, 'span', 'ⓘ', 'privacy-area__info-icon').setAttribute('aria-hidden', 'true');
    areaInfoButton.addEventListener('click', () => openAreaInfo(area.name, areaInfoButton));
    appendTextElement(areaSummary, 'p', areaResult.label, `privacy-state privacy-state--${areaResult.className}`);

    const areaDetail = appendTextElement(diagnosticControls, 'section', '', 'privacy-control-area');
    appendTextElement(areaDetail, 'h4', `${area.name} · ${area.controls.length} ${area.controls.length === 1 ? 'punto' : 'puntos'}`);
    const list = appendTextElement(areaDetail, 'ul', '', 'privacy-control-list');

    area.controls.forEach((control) => {
      const item = appendTextElement(list, 'li', '', 'privacy-control');
      appendTextElement(item, 'span', control.name, 'privacy-control__name');
      const result = resultLabels[controlsByCode.get(control.code)?.result] || resultLabels.not_evaluable;
      const badges = appendTextElement(item, 'span', '', 'privacy-control__badges');
      appendTextElement(badges, 'span', result.label, `privacy-state privacy-state--${result.className}`);
      if (control.informational) {
        appendTextElement(badges, 'span', 'Informativo · no afecta el resultado', 'privacy-control__note');
      }
    });
  });
};

const getHumanStatus = (score) => {
  if (score >= 70) {
    return 'Bien';
  }
  if (score >= 40) {
    return 'Hay aspectos que puedes mejorar';
  }
  return 'Hay aspectos importantes por mejorar';
};

const renderPriorities = (priorities) => {
  diagnosticPriorities.replaceChildren();
  const visiblePriorities = (Array.isArray(priorities) ? priorities : [])
    .filter((priority) => priority && typeof priority === 'object')
    .slice(0, 3);

  if (visiblePriorities.length === 0) {
    appendTextElement(
      diagnosticPriorities,
      'p',
      'No se identificaron acciones prioritarias dentro del alcance de este diagnóstico inicial.',
    );
    return;
  }

  visiblePriorities.forEach((priority, index) => {
    const item = appendTextElement(diagnosticPriorities, 'article', '', 'privacy-priority');
    appendTextElement(item, 'span', String(index + 1), 'privacy-priority__number');
    const content = appendTextElement(item, 'div', '', 'privacy-priority__content');
    appendTextElement(content, 'h4', priority.name || 'Acción prioritaria');
    if (priority.recommendation) {
      appendTextElement(content, 'p', priority.recommendation);
    } else if (priority.finding) {
      appendTextElement(content, 'p', priority.finding);
    }

    const actionSteps = Array.isArray(priority.action_steps) ? priority.action_steps : [];
    if (actionSteps.length > 0) {
      const actionPlan = appendTextElement(content, 'details', '', 'privacy-action-plan');
      appendTextElement(actionPlan, 'summary', 'Ver primeros pasos');

      const actionPlanContent = appendTextElement(actionPlan, 'div', '', 'privacy-action-plan__content');
      appendTextElement(actionPlanContent, 'h5', 'Primeros pasos');
      const steps = appendTextElement(actionPlanContent, 'ol', '', 'privacy-action-plan__steps');
      actionSteps.forEach((step) => {
        appendTextElement(steps, 'li', step);
      });

      if (typeof priority.validation_step === 'string' && priority.validation_step.trim()) {
        const validation = appendTextElement(actionPlanContent, 'div', '', 'privacy-action-plan__validation');
        appendTextElement(validation, 'h5', 'Cómo validar');
        appendTextElement(validation, 'p', priority.validation_step);
      }
    }
  });
};

const resetCommercialState = () => {
  currentDiagnosticId = '';
  correctionOffer.hidden = true;
  noPrioritiesOffer.hidden = true;
  correctionUnavailable.hidden = true;
  orderOpenButton.hidden = false;
  orderOpenButton.disabled = true;
  orderForm.hidden = true;
  orderEmail.value = '';
  orderError.textContent = '';
  orderError.hidden = true;
  orderSuccess.hidden = true;
  orderExpired.hidden = true;
  orderSubmit.disabled = false;
  orderAvailability.textContent = 'Disponible para activar durante 24 horas después de este diagnóstico.';
};

const renderCommercialOffer = (priorities) => {
  const hasPriorities = Array.isArray(priorities) && priorities.length > 0;
  const planAvailable = hasPriorities && Boolean(currentDiagnosticId);
  correctionOffer.hidden = !planAvailable;
  noPrioritiesOffer.hidden = hasPriorities;
  correctionUnavailable.hidden = !hasPriorities || planAvailable;
};

const renderDiagnostic = (diagnostic, websiteUrl) => {
  const score = diagnostic.score;
  const pagesAnalyzed = diagnostic.scope?.pages_analyzed;
  const humanStatus = getHumanStatus(score);

  analyzedUrl.textContent = websiteUrl;
  currentDiagnosticId = typeof diagnostic.diagnostic_id === 'string' ? diagnostic.diagnostic_id.trim() : '';
  orderOpenButton.disabled = !currentDiagnosticId;
  orderOpenButton.hidden = false;
  orderForm.hidden = true;
  orderSuccess.hidden = true;
  orderExpired.hidden = true;
  orderAvailability.textContent = 'Disponible para activar durante 24 horas después de este diagnóstico.';
  scoreValue.textContent = score;
  scoreStatus.textContent = humanStatus;
  diagnosticScope.textContent = Number.isFinite(pagesAnalyzed)
    ? `${pagesAnalyzed} ${pagesAnalyzed === 1 ? 'página pública relevante analizada' : 'páginas públicas relevantes analizadas'}`
    : 'Muestra acotada de páginas públicas relevantes';
  privacyScore.setAttribute('aria-label', `Privacy Score estimado: ${score} de 100. Estado: ${humanStatus}.`);
  renderAreasAndControls(diagnostic.controls);
  renderPriorities(diagnostic.priorities);
  renderCommercialOffer(diagnostic.priorities);
};

const isValidDiagnosticResponse = (diagnostic) => diagnostic !== null
  && typeof diagnostic === 'object'
  && Number.isFinite(diagnostic.score);

const reportFlowError = (code, error) => {
  // Do not log the submitted URL, response payload, evidence, or form contents.
  console.error(`[privacy] ${code}`, error);
};

const finishDiagnosis = () => {
  isDiagnosing = false;
  submitButton.disabled = false;
  setSubmitText('Iniciar diagnóstico');
};

const getFocusableElements = () => {
  if (!modalPanel) {
    return [];
  }

  return Array.from(modalPanel.querySelectorAll(focusableSelector)).filter((element) => !element.disabled && !element.hidden);
};

const appendModalBlock = (title, text, modifier = '') => {
  const className = `privacy-modal__block${modifier ? ` privacy-modal__block--${modifier}` : ''}`;
  const block = appendTextElement(modalContent, 'div', '', className);
  appendTextElement(block, 'h3', title);
  appendTextElement(block, 'p', text);
};

const renderHowItWorks = () => {
  modalTitle.textContent = '¿Cómo funciona el diagnóstico?';
  modalContent.replaceChildren();
  appendModalBlock('Analizamos', 'Información pública y visible del sitio web, como formularios, cookies, políticas de privacidad y textos relacionados con el tratamiento de datos personales.');
  appendModalBlock('No analizamos', 'Bases de datos, sistemas internos, archivos privados ni información protegida por autenticación.');
  appendModalBlock('Resultado', 'Privacy Score, señales detectadas y acciones iniciales recomendadas.');
  appendTextElement(modalContent, 'p', 'Privacy Score es un indicador desarrollado por Mininode que estima el nivel de preparación de un sitio web a partir de señales públicas, documentación visible y buenas prácticas relacionadas con la protección de datos personales.', 'privacy-modal__highlight');
  const disclaimer = appendTextElement(modalContent, 'p', '');
  appendTextElement(disclaimer, 'strong', 'No constituye una certificación legal ni una auditoría completa.');
};

const openModal = (trigger) => {
  if (!modal || !modalPanel) {
    return;
  }

  lastFocusedElement = trigger;
  modal.hidden = false;
  document.body.classList.add('privacy-modal-open');
  modalPanel.focus();
};

const openAreaInfo = (areaName, trigger) => {
  const info = AREA_INFO[areaName];
  if (!info) {
    return;
  }

  modalTitle.textContent = areaName;
  modalContent.replaceChildren();
  appendModalBlock('Qué revisamos', info.what);
  appendModalBlock('Por qué importa', info.why);
  appendModalBlock('Fundamento normativo', info.basis, 'secondary');
  openModal(trigger);
};

const closeModal = () => {
  if (!modal) {
    return;
  }

  modal.hidden = true;
  document.body.classList.remove('privacy-modal-open');

  if (lastFocusedElement && typeof lastFocusedElement.focus === 'function') {
    lastFocusedElement.focus();
  }
};

const handleHelpModalTrigger = (event) => {
  event.preventDefault();
  renderHowItWorks();
  openModal(event.currentTarget);
};

const trapFocus = (event) => {
  if (event.key !== 'Tab' || !modal || modal.hidden || !modalPanel) {
    return;
  }

  const focusableElements = getFocusableElements();

  if (focusableElements.length === 0) {
    event.preventDefault();
    modalPanel.focus();
    return;
  }

  const firstElement = focusableElements[0];
  const lastElement = focusableElements[focusableElements.length - 1];

  if (event.shiftKey && document.activeElement === firstElement) {
    event.preventDefault();
    lastElement.focus();
  } else if (!event.shiftKey && document.activeElement === lastElement) {
    event.preventDefault();
    firstElement.focus();
  }
};

urlInput.addEventListener('input', () => {
  if (isValidUrl(urlInput.value)) {
    setUrlError(false);
  }
});

orderOpenButton?.addEventListener('click', () => {
  orderOpenButton.hidden = true;
  orderForm.hidden = false;
  orderEmail.focus();
});

orderForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const diagnosticId = currentDiagnosticId;
  if (!diagnosticId || correctionOffer.hidden) {
    return;
  }
  orderError.hidden = true;
  orderSubmit.disabled = true;

  try {
    const response = await fetch('/api/privacy/correction-plan-orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ diagnostic_id: diagnosticId, email: orderEmail.value }),
    });
    if (response.status === 410) {
      orderForm.hidden = true;
      orderExpired.hidden = false;
      return;
    }
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    orderForm.hidden = true;
    orderSuccess.hidden = false;
  } catch (error) {
    reportFlowError('order_request_failed', error);
    orderError.textContent = 'No pudimos preparar la solicitud. Intente nuevamente.';
    orderError.hidden = false;
  } finally {
    orderSubmit.disabled = false;
  }
});

orderRetry?.addEventListener('click', () => {
  orderExpired.hidden = true;
  resultCard.hidden = true;
  form.scrollIntoView({ behavior: 'smooth', block: 'start' });
  urlInput.focus();
});

correctionUnavailableRetry?.addEventListener('click', () => {
  form.scrollIntoView({ behavior: 'smooth', block: 'start' });
  urlInput.focus();
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();

  if (isDiagnosing) {
    return;
  }

  const formData = new FormData(form);
  const websiteUrl = normalizeUrl(formData.get('siteUrl'));

  if (!isValidUrl(websiteUrl)) {
    setUrlError(true);
    urlInput.focus();
    return;
  }

  setUrlError(false);
  setRequestError();
  resetCommercialState();
  resultCard.hidden = true;
  loadingCard.hidden = false;
  isDiagnosing = true;
  submitButton.disabled = true;
  submitButton.textContent = 'Analizando...';

  let response;
  try {
    response = await fetch('/api/privacy/diagnose', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url: websiteUrl }),
    });
  } catch (error) {
    reportFlowError('api_request_failed', error);
    loadingCard.hidden = true;
    setRequestError(genericDiagnosticError);
    requestError.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    finishDiagnosis();
    return;
  }

  let diagnostic;
  try {
    diagnostic = await response.json();
  } catch (error) {
    reportFlowError(response.ok ? 'invalid_api_response' : 'api_request_failed', error);
    loadingCard.hidden = true;
    setRequestError(genericDiagnosticError);
    requestError.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    finishDiagnosis();
    return;
  }

  if (!response.ok) {
    reportFlowError('api_request_failed', new Error(`HTTP ${response.status}`));
    loadingCard.hidden = true;
    setRequestError(typeof diagnostic?.message === 'string' && diagnostic.message.trim()
      ? diagnostic.message
      : genericDiagnosticError);
    requestError.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    finishDiagnosis();
    return;
  }

  if (!isValidDiagnosticResponse(diagnostic)) {
    reportFlowError('invalid_api_response', new Error('Response does not match the Privacy diagnostic contract'));
    loadingCard.hidden = true;
    setRequestError(renderDiagnosticError);
    requestError.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    finishDiagnosis();
    return;
  }

  try {
    renderDiagnostic(diagnostic, websiteUrl);
    loadingCard.hidden = true;
    resultCard.hidden = false;
    resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) {
    reportFlowError('render_failed', error);
    loadingCard.hidden = true;
    resultCard.hidden = true;
    setRequestError(renderDiagnosticError);
    requestError.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  } finally {
    finishDiagnosis();
  }
});

[helpLink, headerHelpLink].forEach((trigger) => {
  trigger?.addEventListener('click', handleHelpModalTrigger);
});

modalCloseButtons.forEach((button) => {
  button.addEventListener('click', closeModal);
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && modal && !modal.hidden) {
    closeModal();
    return;
  }

  trapFocus(event);
});
