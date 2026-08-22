(function () {
  'use strict';

  const reader = document.querySelector('[data-markdown-source]');
  const errorMessage = document.querySelector('#learn-error');
  const EBOOK_ID = '001-privacidad-para-pequenos-negocios';
  const STORAGE_KEY = `mininode-learn-feedback:${EBOOK_ID}`;

  function initializeFeedback() {
    const template = document.querySelector('#learn-feedback-template');
    const cta = [...reader.querySelectorAll('h2')]
      .find((heading) => heading.textContent.includes('¿Quieres verlo aplicado'));
    if (!template || !cta) return;

    const feedback = template.content.firstElementChild.cloneNode(true);
    cta.before(feedback);
    const stars = [...feedback.querySelectorAll('[data-rating]')];
    const status = feedback.querySelector('.learn-feedback__status');
    const followup = feedback.querySelector('.learn-feedback__followup');
    const comment = feedback.querySelector('.learn-comment');
    let saved;
    try { saved = JSON.parse(localStorage.getItem(STORAGE_KEY)); } catch (_error) { saved = null; }

    function showRating(rating) {
      stars.forEach((star) => {
        const selected = Number(star.dataset.rating) === rating;
        star.textContent = Number(star.dataset.rating) <= rating ? '★' : '☆';
        star.setAttribute('aria-checked', String(selected));
      });
      followup.hidden = false;
      comment.hidden = rating > 3;
    }

    async function updateFeedback(payload) {
      const response = await fetch(`/api/learn/feedback/${saved.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!response.ok) throw new Error('Feedback update failed');
    }

    if (saved?.id && Number.isInteger(saved.rating)) {
      showRating(saved.rating);
      stars.forEach((star) => { star.disabled = true; });
      status.textContent = 'Tu valoración ya fue registrada. Gracias.';
    }

    stars.forEach((star) => star.addEventListener('click', async () => {
      if (saved?.id) return;
      const rating = Number(star.dataset.rating);
      showRating(rating);
      stars.forEach((item) => { item.disabled = true; });
      status.textContent = 'Registrando…';
      try {
        const response = await fetch('/api/learn/feedback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ebook_id: EBOOK_ID, rating })
        });
        if (!response.ok) throw new Error('Feedback submission failed');
        const result = await response.json();
        saved = { id: result.id, rating };
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(saved)); } catch (_error) { /* Storage is optional. */ }
        status.textContent = 'Gracias. Tu valoración fue registrada.';
      } catch (_error) {
        stars.forEach((item) => { item.disabled = false; });
        status.textContent = 'No pudimos registrar tu valoración. Inténtalo nuevamente.';
      }
    }));

    feedback.querySelectorAll('[name="learn-topic"]').forEach((option) => {
      option.addEventListener('change', async () => {
        try {
          await updateFeedback({ topic: option.value });
          status.textContent = 'Gracias. Guardamos tu preferencia.';
        } catch (_error) {
          status.textContent = 'No pudimos guardar el tema. Inténtalo nuevamente.';
        }
      });
    });

    comment.addEventListener('submit', async (event) => {
      event.preventDefault();
      const textarea = comment.querySelector('textarea');
      const value = textarea.value.trim();
      if (!value) return;
      try {
        await updateFeedback({ comment: value });
        textarea.disabled = true;
        comment.querySelector('button').disabled = true;
        status.textContent = 'Gracias por ayudarnos a mejorar.';
      } catch (_error) {
        status.textContent = 'No pudimos guardar el comentario. Inténtalo nuevamente.';
      }
    });
  }

  function showError() {
    reader?.setAttribute('hidden', '');
    if (errorMessage) errorMessage.hidden = false;
  }

  async function renderBook() {
    if (!reader || !window.marked || !window.DOMPurify) {
      showError();
      return;
    }

    try {
      const response = await fetch(reader.dataset.markdownSource, {
        headers: { Accept: 'text/markdown' }
      });
      if (!response.ok) throw new Error('Content unavailable');

      const markdown = await response.text();
      const rendered = window.marked.parse(markdown, { gfm: true });
      const sanitized = window.DOMPurify.sanitize(rendered, {
        USE_PROFILES: { html: true }
      });

      reader.innerHTML = sanitized;
      reader.setAttribute('aria-busy', 'false');
      initializeFeedback();
    } catch (_error) {
      showError();
    }
  }

  renderBook();
}());
