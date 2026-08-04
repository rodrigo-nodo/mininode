const form = document.querySelector('#privacy-form');
const submitButton = document.querySelector('#privacy-submit');
const loadingCard = document.querySelector('#privacy-loading');
const resultCard = document.querySelector('#privacy-result');
const analyzedUrl = document.querySelector('#analyzed-url');

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

form.addEventListener('submit', (event) => {
  event.preventDefault();

  const formData = new FormData(form);
  const websiteUrl = normalizeUrl(formData.get('siteUrl'));

  analyzedUrl.textContent = websiteUrl;
  resultCard.hidden = true;
  loadingCard.hidden = false;
  submitButton.disabled = true;
  submitButton.textContent = 'Analizando...';

  window.setTimeout(() => {
    loadingCard.hidden = true;
    resultCard.hidden = false;
    submitButton.disabled = false;
    submitButton.textContent = 'Obtener diagnóstico gratuito';
    resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, 1400);
});
