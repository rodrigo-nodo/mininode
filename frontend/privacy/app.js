const form = document.querySelector('#privacy-form');
const urlInput = document.querySelector('#site-url');
const urlError = document.querySelector('#url-error');
const submitButton = document.querySelector('#privacy-submit');
const loadingCard = document.querySelector('#privacy-loading');
const resultCard = document.querySelector('#privacy-result');
const analyzedUrl = document.querySelector('#analyzed-url');
const helpLink = document.querySelector('#how-it-works');
const headerHelpLink = document.querySelector('#help-link');
const modal = document.querySelector('#privacy-modal');
const modalPanel = modal?.querySelector('.privacy-modal__panel');
const modalCloseButtons = modal?.querySelectorAll('[data-modal-close]') ?? [];
const focusableSelector = 'button, a[href], input, textarea, select, [tabindex]:not([tabindex="-1"])';
let lastFocusedElement = null;

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

form.addEventListener('submit', (event) => {
  event.preventDefault();

  const formData = new FormData(form);
  const websiteUrl = normalizeUrl(formData.get('siteUrl'));

  if (!isValidUrl(websiteUrl)) {
    setUrlError(true);
    urlInput.focus();
    return;
  }

  setUrlError(false);
  analyzedUrl.textContent = websiteUrl;
  resultCard.hidden = true;
  loadingCard.hidden = false;
  submitButton.disabled = true;
  submitButton.textContent = 'Analizando...';

  window.setTimeout(() => {
    loadingCard.hidden = true;
    resultCard.hidden = false;
    submitButton.disabled = false;
    setSubmitText('Iniciar diagnóstico');
    resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, 1400);
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
