(() => {
  const originalFetch = window.fetch.bind(window);
  const API_PREFIX = '/api/privacy/data';
  const NOTE_PREFIX = '__mininode_retention_v2__:';
  const RETENTION_CHOICES = ['defined', 'variable', 'not_defined', 'unknown'];
  const reviewedActivityIds = new Set();

  const markerPattern = new RegExp(`^${NOTE_PREFIX}(defined|variable|not_defined|unknown)(?:\\n|$)`);

  function withoutMarker(note) {
    if (!note) return null;
    const cleaned = String(note).replace(markerPattern, '').trim();
    return cleaned || null;
  }

  function withMarker(choice, note) {
    const cleanNote = withoutMarker(note);
    return `${NOTE_PREFIX}${choice}${cleanNote ? `\n${cleanNote}` : ''}`;
  }

  function decodeRetention(retention = {}) {
    const note = retention.note || null;
    const match = String(note || '').match(markerPattern);
    if (match) {
      retention.status = match[1];
      retention.reviewed = true;
      retention.note = withoutMarker(note);
      return retention;
    }
    retention.reviewed = ['defined', 'variable'].includes(retention.status);
    return retention;
  }

  function normalizeActivity(activity) {
    if (!activity?.answers) return activity;
    activity.answers.retention = decodeRetention(activity.answers.retention || {});
    if (activity.answers.retention.reviewed === true && activity.id != null) {
      reviewedActivityIds.add(String(activity.id));
    }
    return activity;
  }

  function prepareActivityPayload(payload) {
    const retention = payload?.answers?.retention;
    if (!retention) return payload;
    const choice = RETENTION_CHOICES.includes(retention.status) ? retention.status : 'unknown';
    if (retention.reviewed === true) {
      retention.note = withMarker(choice, retention.note);
      retention.status = choice === 'not_defined' ? 'unknown' : choice;
    }
    delete retention.reviewed;
    return payload;
  }

  function normalizeCatalog(catalog) {
    const statuses = catalog?.retention?.statuses;
    if (!Array.isArray(statuses)) return catalog;
    const defined = statuses.find(item => item.code === 'defined');
    if (defined) defined.label = 'Sí, tengo un plazo definido';
    if (!statuses.some(item => item.code === 'not_defined')) {
      const unknownIndex = statuses.findIndex(item => item.code === 'unknown');
      statuses.splice(unknownIndex >= 0 ? unknownIndex : statuses.length, 0, {
        code: 'not_defined',
        label: 'No lo tengo definido',
      });
    }
    return catalog;
  }

  function normalizeCompletedRetentionCopy() {
    const section = document.querySelector('#privacy-data .pd-next-stage--done');
    if (!section) return;
    const heading = section.querySelector('h2');
    if (heading?.textContent.trim() === 'Conservación ✓') heading.textContent = 'Conservación';
    const detail = [...section.querySelectorAll(':scope > p')]
      .find(item => !item.classList.contains('eyebrow'));
    if (detail?.textContent.trim() === 'Revisaste la conservación en todas las actividades de tu mapa.') {
      detail.textContent = 'Revisada en todas las actividades de tu mapa.';
    }
  }

  function scheduleCompletedRetentionCopy() {
    setTimeout(normalizeCompletedRetentionCopy, 0);
  }

  function jsonResponse(response, data) {
    const headers = new Headers(response.headers);
    headers.delete('content-length');
    headers.delete('content-encoding');
    headers.set('content-type', 'application/json');
    scheduleCompletedRetentionCopy();
    return new Response(JSON.stringify(data), {
      status: response.status,
      statusText: response.statusText,
      headers,
    });
  }

  document.addEventListener('click', scheduleCompletedRetentionCopy, true);

  window.fetch = async (input, init = {}) => {
    const url = typeof input === 'string' ? input : input?.url || '';
    let nextInit = init;

    if (url.startsWith(API_PREFIX) && typeof init.body === 'string') {
      try {
        const payload = JSON.parse(init.body);
        if (/\/activities(?:\/[^/]+)?$/.test(url)) {
          prepareActivityPayload(payload);
          nextInit = {...init, body: JSON.stringify(payload)};
        }
      } catch {
        // Leave non-JSON bodies untouched.
      }
    }

    const response = await originalFetch(input, nextInit);
    if (!response.ok || response.status === 204 || !url.startsWith(API_PREFIX)) return response;

    if (url.endsWith('/catalog')) {
      return jsonResponse(response, normalizeCatalog(await response.json()));
    }

    if (/\/activities(?:\/[^/]+)?$/.test(url)) {
      const data = await response.json();
      const normalized = Array.isArray(data) ? data.map(normalizeActivity) : normalizeActivity(data);
      return jsonResponse(response, normalized);
    }

    if (url.endsWith('/review')) {
      const data = await response.json();
      const filtered = Array.isArray(data)
        ? data.filter(item => !['D01', 'D02'].includes(item.code) || reviewedActivityIds.has(String(item.activity_id)))
        : data;
      return jsonResponse(response, filtered);
    }

    return response;
  };
})();
