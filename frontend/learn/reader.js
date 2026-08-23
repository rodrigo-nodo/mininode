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
      if (!saved?.feedback_id) throw new Error('Feedback has not been created');
      const response = await fetch(`/api/learn/feedback/${saved.feedback_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!response.ok) throw new Error('Feedback update failed');
    }

    if (saved?.feedback_id && Number.isInteger(saved.rating)) {
      showRating(saved.rating);
      status.textContent = 'Tu valoración ya fue registrada. Gracias.';
    }

    stars.forEach((star) => star.addEventListener('click', async () => {
      const rating = Number(star.dataset.rating);
      const previousRating = saved?.rating;
      showRating(rating);
      stars.forEach((item) => { item.disabled = true; });
      status.textContent = saved?.feedback_id ? 'Actualizando…' : 'Registrando…';
      try {
        const isUpdate = Boolean(saved?.feedback_id);
        const endpoint = isUpdate
          ? `/api/learn/feedback/${saved.feedback_id}`
          : '/api/learn/feedback';
        const payload = isUpdate
          ? { rating, ...(rating > 3 ? { comment: null } : {}) }
          : { content_key: EBOOK_ID, rating };
        const response = await fetch(endpoint, {
          method: isUpdate ? 'PATCH' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error('Feedback submission failed');
        const result = isUpdate ? null : await response.json();
        saved = { feedback_id: saved?.feedback_id || result.feedback_id, rating };
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(saved)); } catch (_error) { /* Storage is optional. */ }
        if (rating > 3) comment.querySelector('textarea').value = '';
        status.textContent = isUpdate
          ? 'Gracias. Tu valoración fue actualizada.'
          : 'Gracias. Tu valoración fue registrada.';
      } catch (_error) {
        if (previousRating) showRating(previousRating);
        status.textContent = 'No pudimos guardar tu valoración. Inténtalo nuevamente.';
      } finally {
        stars.forEach((item) => { item.disabled = false; });
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
