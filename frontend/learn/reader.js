(function () {
  'use strict';

  const reader = document.querySelector('[data-markdown-source]');
  const errorMessage = document.querySelector('#learn-error');
  const CONTENT_KEY = reader?.dataset.contentKey || '001-privacidad-para-pequenos-negocios';
  const CONTENT_TYPE = reader?.dataset.contentType || 'ebook';
  const STORAGE_KEY = `mininode-learn-feedback:${CONTENT_KEY}`;
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
    const ratingOnly = CONTENT_TYPE === 'brief' || CONTENT_TYPE === 'guide';
    const cta = ratingOnly
      ? reader.querySelector('.learn-related')
      : [...reader.querySelectorAll('h2')]
        .find((heading) => heading.textContent.includes('¿Quieres verlo aplicado'));
    if (!template || (!ratingOnly && !cta)) return;

    const feedback = template.content.firstElementChild.cloneNode(true);
    if (cta) cta.before(feedback);
    else reader.append(feedback);
    const stars = [...feedback.querySelectorAll('[data-rating]')];
    const status = feedback.querySelector('.learn-feedback__status');
    const followup = feedback.querySelector('.learn-feedback__followup');
    const topics = feedback.querySelector('.learn-topics');
    const topicSummary = feedback.querySelector('.learn-topic-summary');
    const comment = feedback.querySelector('.learn-comment');
    const commentToggle = feedback.querySelector('.learn-comment-toggle');
    const commentSent = feedback.querySelector('.learn-comment-sent');
    const commentValue = feedback.querySelector('.learn-comment-value');
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
      status.textContent = '✓ Gracias por tu feedback.';
      if (ratingOnly) return;
      followup.hidden = false;
      feedback.querySelectorAll('[name="learn-topic"]').forEach((option) => {
        option.checked = option.value === state.topic;
      });
      topics.hidden = Boolean(state.topic) && !expandTopics;
      topicSummary.hidden = !state.topic || expandTopics;
      if (state.topic) topicSummary.querySelector('strong').textContent = TOPIC_LABELS[state.topic];

      const hasComment = state.comment !== null;
      commentSent.hidden = !hasComment;
      commentValue.hidden = !hasComment;
      commentValue.textContent = hasComment ? `“${state.comment}”` : '';
      comment.hidden = hasComment || (state.rating > 3 && !expandComment);
      commentToggle.hidden = hasComment || state.rating <= 3 || expandComment;
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
          body: JSON.stringify(isUpdate ? { rating } : { content_key: CONTENT_KEY, rating })
        });
        if (!response.ok) throw new Error('Feedback submission failed');
        if (!isUpdate) persistId((await response.json()).feedback_id);
        state = { rating, topic: state?.topic || null, comment: state?.comment ?? null };
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

    topicSummary?.querySelector('button')?.addEventListener('click', () => renderState({ expandTopics: true }));
    commentToggle?.addEventListener('click', () => renderState({ expandComment: true }));

    comment?.addEventListener('submit', async (event) => {
      event.preventDefault();
      const textarea = comment.querySelector('textarea');
      const value = textarea.value.trim();
      if (!value) return;
      const submit = comment.querySelector('button');
      submit.disabled = true;
      try {
        await updateFeedback({ comment: value });
        state.comment = value;
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

  function parseDocument(source) {
    if (!source.startsWith('---\n')) return { metadata: null, markdown: source };
    const end = source.indexOf('\n---\n', 4);
    if (end < 0) return { metadata: null, markdown: source };
    const metadata = {};
    let listKey = null;
    source.slice(4, end).split('\n').forEach((line) => {
      const item = line.match(/^\s+-\s+(.+)$/);
      if (item && listKey) {
        metadata[listKey].push(item[1].trim());
        return;
      }
      const field = line.match(/^([a-z_]+):\s*(.*)$/);
      if (!field) return;
      listKey = field[2] ? null : field[1];
      metadata[field[1]] = field[2] || [];
    });
    return { metadata, markdown: source.slice(end + 5) };
  }

  function briefHeader(metadata) {
    const header = document.createElement('header');
    header.className = 'learn-reader__header';
    const country = metadata.country === 'CL' ? 'Chile' : metadata.country;
    const topics = (metadata.topics || []).map((topic) =>
      `<span>${topic.charAt(0).toUpperCase() + topic.slice(1)}</span>`).join('');
    header.innerHTML = window.DOMPurify.sanitize(`
      <p class="learn-reader__eyebrow">MININODE BRIEF ${metadata.id}</p>
      <h1>${metadata.title}</h1>
      <p class="learn-reader__subtitle">${metadata.subtitle}</p>
      <p class="learn-reader__details">${metadata.reading_time} min · Actualizado ${metadata.updated} · ${country}</p>
      <div class="learn-reader__topics">${topics}</div>
    `, { USE_PROFILES: { html: true } });
    return header;
  }

  function guideHeader(metadata) {
    const country = metadata.country === 'CL' ? 'Chile' : metadata.country;
    const [year, month] = metadata.updated.split('-');
    const monthNames = {
      '01': 'enero',
      '02': 'febrero',
      '03': 'marzo',
      '04': 'abril',
      '05': 'mayo',
      '06': 'junio',
      '07': 'julio',
      '08': 'agosto',
      '09': 'septiembre',
      '10': 'octubre',
      '11': 'noviembre',
      '12': 'diciembre'
    };
    const updated = `${monthNames[month]} ${year}`;
    const header = document.createElement('header');
    header.className = 'learn-reader__header';
    header.innerHTML = window.DOMPurify.sanitize(`
      <p class="learn-reader__eyebrow">GUIDE ${metadata.id}</p>
      <h1>${metadata.title}</h1>
      <p class="learn-reader__subtitle">${metadata.subtitle}</p>
      <p class="learn-reader__details">${metadata.reading_time} min · ${country} · Actualizado ${updated}</p>
    `, { USE_PROFILES: { html: true } });
    return header;
  }

  async function renderRelated(metadata) {
    if (!metadata || metadata.type !== 'brief') return;
    try {
      const response = await fetch(reader.dataset.relationshipsSource);
      if (!response.ok) return;
      const catalog = (await response.json()).briefs || {};
      const relatedIds = catalog[metadata.id]?.related;
      if (!Array.isArray(relatedIds)) return;
      const related = relatedIds.map((id) => ({ id, ...catalog[id] })).filter((item) =>
        typeof item.id === 'string'
        && typeof item.slug === 'string' && item.slug.length > 0
        && typeof item.title === 'string' && item.title.length > 0
        && typeof item.subtitle === 'string' && item.subtitle.length > 0);
      if (!related.length) return;
      const section = document.createElement('section');
      section.className = 'learn-related';
      section.innerHTML = window.DOMPurify.sanitize(`<h2>Relacionado</h2><ul>${related.map((item) =>
        `<li><a href="/learn/briefs/${item.slug}"><strong>${item.id} - ${item.title}</strong><span>${item.subtitle}</span></a></li>`).join('')}</ul>`);
      reader.append(section);
    } catch (_error) { /* Relationships are optional supporting content. */ }
  }

  async function renderBook() {
    if (!reader || !window.marked || !window.DOMPurify) {
      showError();
      return;
    }
    try {
      const response = await fetch(reader.dataset.markdownSource, { headers: { Accept: 'text/markdown' } });
      if (!response.ok) throw new Error('Content unavailable');
      const documentSource = parseDocument(await response.text());
      const rendered = window.marked.parse(documentSource.markdown, { gfm: true });
      reader.innerHTML = window.DOMPurify.sanitize(rendered, { USE_PROFILES: { html: true } });
      if (documentSource.metadata?.type === 'brief') {
        reader.prepend(briefHeader(documentSource.metadata));
      } else if (documentSource.metadata?.type === 'guide') {
        reader.prepend(guideHeader(documentSource.metadata));
      }
      reader.setAttribute('aria-busy', 'false');
      await renderRelated(documentSource.metadata);
      initializeFeedback();
    } catch (_error) { showError(); }
  }

  renderBook();
}());
