(function () {
  'use strict';

  const reader = document.querySelector('[data-markdown-source]');
  const errorMessage = document.querySelector('#learn-error');

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
      const rendered = window.marked.parse(markdown, {
        gfm: true,
        headerIds: false,
        mangle: false
      });
      const sanitized = window.DOMPurify.sanitize(rendered, {
        USE_PROFILES: { html: true }
      });

      reader.innerHTML = sanitized;
      reader.setAttribute('aria-busy', 'false');
    } catch (_error) {
      showError();
    }
  }

  renderBook();
}());
