(function () {
  'use strict';

  const reader = document.querySelector('[data-markdown-source]');
  const errorMessage = document.querySelector('#learn-error');
  const EBOOK_ID = '001-privacidad-para-pequenos-negocios';
  const STORAGE_KEY = `mininode-learn-feedback:${EBOOK_ID}`;
  const REQUEST_TIMEOUT_MS = 70000;
  const TOPIC_LABELS = {
    business_data: 'Datos que maneja el negocio',
    website_forms: 'Sitio web y formularios',
    files: 'Excel, WhatsApp y archivos',
    policies: 'Políticas y documentos',
    security: 'Seguridad',
    new_law: 'Nueva ley'
  };

  async function request(url, options = {}) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    try {
      return await fetch(url, { ...options, signal: controller.signal });
    } finally {
      clearTimeout(timeout);
    }
  }

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
    const topics = feedback.querySelector('.learn-topics');
    const topicSummary = feedback.querySelector('.learn-topic-summary');
    const comment = feedback.querySelector('.learn-comment');
    const commentToggle = feedback.querySelector('.learn-comment-toggle');
    const commentSent = feedback.querySelector('.learn-comment-sent');
    let state = null;
    let feedbackId = null;

    try {
      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
      feedbackId = typeof stored === 'string' ? stored : stored?.feedback_id;
    } catch (_error) { feedbackId = null; }

    function persistId(id) {
      feedbackId = id;
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ feedback_id: id })); } catch (_error) { /* Storage is optional. */ }
    }

    function clearId() {
      feedbackId = null;
      state = null;
      try { localStorage.removeItem(STORAGE_KEY); } catch (_error) { /* Storage is optional. */ }
    }

    function setControlsDisabled(disabled) {
      feedback.querySelectorAll('button, input, textarea').forEach((control) => {
        control.disabled = disabled;
      });
    }

    function showRating(rating) {
      stars.forEach((star) => {
        const selected = Number(star.dataset.rating) === rating;
        star.textContent = Number(star.dataset.rating) <= rating ? '★' : '☆';
        star.setAttribute('aria-checked', String(selected));
      });
    }

    function renderState({ expandTopics = false, expandComment = false } = {}) {
      if (!state) {
        showRating(0);
        followup.hidden = true;
        status.textContent = '';
        return;
      }
      showRating(state.rating);
      followup.hidden = false;
      status.textContent = '✓ Gracias por tu feedback.';
      feedback.querySelectorAll('[name="learn-topic"]').forEach((option) => {
        option.checked = option.value === state.topic;
      });
      topics.hidden = Boolean(state.topic) && !expandTopics;
      topicSummary.hidden = !state.topic || expandTopics;
      if (state.topic) topicSummary.querySelector('strong').textContent = TOPIC_LABELS[state.topic];

      commentSent.hidden = !state.has_comment;
      comment.hidden = state.has_comment || (state.rating > 3 && !expandComment);
      commentToggle.hidden = state.has_comment || state.rating <= 3 || expandComment;
      comment.querySelector('label').hidden = state.rating > 3;
      comment.querySelector('textarea').placeholder = state.rating > 3 ? 'Escribe un comentario...' : '';
    }

    async function updateFeedback(payload) {
      if (!feedbackId) throw new Error('Feedback has not been created');
      const response = await request(`/api/learn/feedback/${feedbackId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!response.ok) throw new Error('Feedback update failed');
    }

    stars.forEach((star) => star.addEventListener('click', async () => {
      const rating = Number(star.dataset.rating);
      const previousState = state && { ...state };
      showRating(rating);
      stars.forEach((item) => { item.disabled = true; });
      status.textContent = feedbackId ? 'Actualizando…' : 'Registrando…';
      try {
        const isUpdate = Boolean(feedbackId);
        const response = await request(isUpdate ? `/api/learn/feedback/${feedbackId}` : '/api/learn/feedback', {
          method: isUpdate ? 'PATCH' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(isUpdate ? { rating } : { content_key: EBOOK_ID, rating })
        });
        if (!response.ok) throw new Error('Feedback submission failed');
        if (!isUpdate) persistId((await response.json()).feedback_id);
        state = { rating, topic: state?.topic || null, has_comment: state?.has_comment || false };
        renderState();
      } catch (_error) {
        state = previousState;
        if (state) showRating(state.rating);
        status.textContent = 'No pudimos guardar tu valoración. Inténtalo nuevamente.';
      } finally {
        stars.forEach((item) => { item.disabled = false; });
      }
    }));

    feedback.querySelectorAll('[name="learn-topic"]').forEach((option) => {
      option.addEventListener('change', async () => {
        topics.disabled = true;
        try {
          await updateFeedback({ topic: option.value });
          state.topic = option.value;
          renderState();
        } catch (_error) {
          topics.disabled = false;
          status.textContent = 'No pudimos guardar el tema. Inténtalo nuevamente.';
        } finally {
          topics.disabled = false;
        }
      });
    });

    topicSummary.querySelector('button').addEventListener('click', () => renderState({ expandTopics: true }));
    commentToggle.addEventListener('click', () => renderState({ expandComment: true }));

    comment.addEventListener('submit', async (event) => {
      event.preventDefault();
      const textarea = comment.querySelector('textarea');
      const value = textarea.value.trim();
      if (!value) return;
      const submit = comment.querySelector('button');
      submit.disabled = true;
      try {
        await updateFeedback({ comment: value });
        state.has_comment = true;
        textarea.value = '';
        renderState();
      } catch (_error) {
        status.textContent = 'No pudimos guardar el comentario. Inténtalo nuevamente.';
      } finally {
        submit.disabled = false;
      }
    });

    async function restoreFeedback() {
      if (!feedbackId) return;
      setControlsDisabled(true);
      status.textContent = 'Recuperando tu feedback…';
      try {
        const response = await request(`/api/learn/feedback/${feedbackId}`);
        if (response.status === 404) {
          clearId();
          renderState();
          return;
        }
        if (!response.ok) throw new Error('Feedback retrieval failed');
        state = await response.json();
        persistId(feedbackId);
        renderState();
      } catch (_error) {
        status.textContent = 'No pudimos recuperar tu feedback. Puedes intentarlo nuevamente.';
      } finally {
        setControlsDisabled(false);
      }
    }

    restoreFeedback();
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
      const response = await fetch(reader.dataset.markdownSource, { headers: { Accept: 'text/markdown' } });
      if (!response.ok) throw new Error('Content unavailable');
      const rendered = window.marked.parse(await response.text(), { gfm: true });
      reader.innerHTML = window.DOMPurify.sanitize(rendered, { USE_PROFILES: { html: true } });
      reader.setAttribute('aria-busy', 'false');
      initializeFeedback();
    } catch (_error) { showError(); }
  }

  renderBook();
}());
