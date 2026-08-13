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
const diagnosticStatus = document.querySelector('#diagnostic-status');
const diagnosticCoverage = document.querySelector('#diagnostic-coverage');
const diagnosticScope = document.querySelector('#diagnostic-scope');
const detectedSignals = document.querySelector('#detected-signals');
const diagnosticPriorities = document.querySelector('#diagnostic-priorities');
const helpLink = document.querySelector('#how-it-works');
const headerHelpLink = document.querySelector('#help-link');
const modal = document.querySelector('#privacy-modal');
const modalPanel = modal?.querySelector('.privacy-modal__panel');
const modalCloseButtons = modal?.querySelectorAll('[data-modal-close]') ?? [];
const focusableSelector = 'button, a[href], input, textarea, select, [tabindex]:not([tabindex="-1"])';
let lastFocusedElement = null;
let isDiagnosing = false;

const genericDiagnosticError = 'No pudimos completar el diagnóstico. Intenta nuevamente en unos minutos.';
const signalLabels = {
  'PRV-001': 'Política de privacidad visible',
  'PRV-101': 'Formularios que recopilan datos personales',
  'PRV-201': 'Uso de cookies o información sobre cookies observada',
  'PRV-301': 'Canal de contacto visible',
  'PRV-501': 'HTTPS activo',
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

const renderSignals = (controls) => {
  detectedSignals.replaceChildren();

  const signals = (Array.isArray(controls) ? controls : [])
    .filter(({ control_code: code, result }) => signalLabels[code]
      && (result === 'detected' || (code === 'PRV-201' && result === 'partial')))
    .slice(0, 5);

  if (signals.length === 0) {
    appendTextElement(detectedSignals, 'li', 'No se identificaron señales claras para resumir dentro del alcance inicial.');
    return;
  }

  signals.forEach(({ control_code: code }) => {
    appendTextElement(detectedSignals, 'li', signalLabels[code]);
  });
};

const renderPriorities = (priorities) => {
  diagnosticPriorities.replaceChildren();
  const visiblePriorities = (Array.isArray(priorities) ? priorities : []).slice(0, 3);

  if (visiblePriorities.length === 0) {
    appendTextElement(
      diagnosticPriorities,
      'p',
      'No se identificaron acciones prioritarias dentro del alcance de este diagnóstico inicial.',
    );
    return;
  }

  visiblePriorities.forEach((priority) => {
    const item = appendTextElement(diagnosticPriorities, 'article', '', 'privacy-priority');
    appendTextElement(item, 'h4', priority.name || 'Acción prioritaria');
    if (priority.source_url) {
      try {
        const source = new URL(priority.source_url);
        const page = source.pathname === '/' ? 'página principal' : source.pathname;
        appendTextElement(item, 'p', `Detectado en: ${page}`);
      } catch {
        // Ignore malformed optional trace data rather than displaying it.
      }
    }
    if (priority.evidence_summary) {
      appendTextElement(item, 'p', `Evidencia: ${priority.evidence_summary}`);
    }
    if (priority.finding) {
      appendTextElement(item, 'p', `Hallazgo: ${priority.finding}`);
    }
    if (priority.recommendation) {
      appendTextElement(item, 'p', `Recomendación: ${priority.recommendation}`);
    }
  });
};

const renderDiagnostic = (diagnostic, websiteUrl) => {
  const score = diagnostic.score;
  const status = diagnostic.status;
  const coverage = diagnostic.coverage;
  const pagesAnalyzed = diagnostic.scope?.pages_analyzed;

  analyzedUrl.textContent = websiteUrl;
  scoreValue.textContent = `${score} / 100`;
  scoreStatus.textContent = status;
  diagnosticStatus.textContent = status;
  diagnosticCoverage.textContent = `${coverage}%`;
  diagnosticScope.textContent = Number.isFinite(pagesAnalyzed)
    ? `${pagesAnalyzed} ${pagesAnalyzed === 1 ? 'página pública relevante analizada' : 'páginas públicas relevantes analizadas'}`
    : 'Muestra acotada de páginas públicas relevantes';
  privacyScore.setAttribute('aria-label', `Privacy Score estimado: ${score} de 100. Estado: ${status}.`);
  renderSignals(diagnostic.controls);
  renderPriorities(diagnostic.priorities);
};

const getFocusableElements = () => {
  if (!modalPanel) {
    return [];
  }

  return Array.from(modalPanel.querySelectorAll(focusableSelector)).filter((element) => !element.disabled && !element.hidden);
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

const handleModalTrigger = (event) => {
  event.preventDefault();
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
  resultCard.hidden = true;
  loadingCard.hidden = false;
  isDiagnosing = true;
  submitButton.disabled = true;
  submitButton.textContent = 'Analizando...';

  try {
    const response = await fetch('/api/privacy/diagnose', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url: websiteUrl }),
    });
    const diagnostic = await response.json().catch(() => ({}));

    if (!response.ok) {
      const responseError = new Error(typeof diagnostic.message === 'string' && diagnostic.message.trim()
        ? diagnostic.message
        : genericDiagnosticError);
      responseError.isUserFacing = true;
      throw responseError;
    }

    if (!Number.isFinite(diagnostic.score)
      || !Number.isFinite(diagnostic.coverage)
      || typeof diagnostic.status !== 'string') {
      const invalidResponseError = new Error(genericDiagnosticError);
      invalidResponseError.isUserFacing = true;
      throw invalidResponseError;
    }

    renderDiagnostic(diagnostic, websiteUrl);
    loadingCard.hidden = true;
    resultCard.hidden = false;
    resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) {
    loadingCard.hidden = true;
    setRequestError(error instanceof Error && error.isUserFacing ? error.message : genericDiagnosticError);
    requestError.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  } finally {
    isDiagnosing = false;
    submitButton.disabled = false;
    setSubmitText('Iniciar diagnóstico');
  }
});

[helpLink, headerHelpLink].forEach((trigger) => {
  trigger?.addEventListener('click', handleModalTrigger);
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
