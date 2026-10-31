import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const html = readFileSync(new URL('./index.html', import.meta.url), 'utf8');
const script = readFileSync(new URL('./app.js', import.meta.url), 'utf8');
const uxScript = readFileSync(new URL('../control-ux.js', import.meta.url), 'utf8');
const siteId = '11111111-1111-4111-8111-111111111111';
const path = `/api/privacy/workspace-sites/${siteId}/plan`;
const future = new Date(Date.now() + 3600000).toISOString();
const past = new Date(Date.now() - 3600000).toISOString();

class Node {
  constructor(tagName = '') {
    this.tagName = tagName;
    this.classList = { add: (name) => { this.className = name; } };
    this.textContent = '';
    this.hidden = true;
    this.disabled = false;
    this.children = [];
    this.listeners = new Map();
    this.attributes = new Map();
    this.dataset = {};
    this.content = { cloneNode: () => new Node() };
  }
  addEventListener(name, handler) { this.listeners.set(name, handler); }
  click() {
    const callback = this.listeners.get('click');
    assert.ok(callback, 'expected a click listener');
    return callback({ preventDefault() {} });
  }
  setAttribute(name, value) { this.attributes.set(name, value); }
  focus() { this.focused = true; }
  querySelector() { return new Node(); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren() { this.children = []; }
}

const flush = () => new Promise((done) => setImmediate(done));

function payload(status = 'available', withReview = false) {
  return {
    id: 'plan-one',
    site_url: 'https://example.com/',
    created_at: '2026-10-26T12:00:00Z',
    plan: { version: '1', actions_version: '1', initial_score: 65, item_count: 0, items: [] },
    diagnostic: {
      initial: { score: 65, created_at: '2026-10-25T12:00:00Z',
                 framework_version: '0.11', scoring_version: '0.11' },
      current: {
        score: withReview ? 75 : 65,
        created_at: withReview ? '2026-10-26T13:00:00Z' : '2026-10-25T12:00:00Z',
        source: withReview ? 'review' : 'initial',
        framework_version: '0.11', scoring_version: '0.11',
        scope: { pages_analyzed: 2, limited: false },
        controls: [
          { control_code: 'PRV-001', name: 'Política de privacidad visible',
            area: 'Transparencia', type: 'evaluation',
            result: withReview ? 'detected' : 'not_detected',
            reason: 'Resultado de una revisión pública.',
            confidence: 'high', evidence_summary: 'Evidencia visible del sitio.',
            source_url: 'https://example.com/privacy' },
          { control_code: 'PRV-101', name: 'Formularios públicos',
            area: 'Formularios', type: 'context', result: 'not_evaluable',
            reason: 'No concluyente', evidence_summary: null, source_url: null },
          { control_code: 'PRV-201', name: 'Cookies observadas',
            area: 'Cookies', type: 'context', result: 'not_applicable',
            reason: 'No aplica', evidence_summary: null, source_url: null },
          { control_code: 'PRV-301', name: 'Contacto',
            area: 'Contacto', type: 'evaluation', result: 'detected',
            reason: 'Canal visible', evidence_summary: null, source_url: null },
          { control_code: 'PRV-501', name: 'HTTPS',
            area: 'Seguridad', type: 'evaluation', result: 'partial',
            reason: 'Señal parcial', evidence_summary: null, source_url: null },
        ],
      },
    },
    current_actions: {
      status: 'available', source: withReview ? 'review' : 'initial',
      created_at: withReview ? '2026-10-26T13:00:00Z' : '2026-10-25T12:00:00Z',
      actions_version: '2', item_count: 0, items: [],
      verification_pending_count: 0, verification_pending: [],
    },
    check: {
      status, expires_at: status === 'expired' ? past : future,
      ...(withReview ? { latest_check: {
        created_at: '2026-10-26T13:00:00Z',
        result: {
          version: '2', current_score: 75,
          comparability: { status: 'not_comparable' }, items: [],
        },
      }} : {}),
    },
  };
}

function mount(handler) {
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map((x) => x[1]);
  const nodes = new Map(ids.map((id) => [id, new Node()]));
  const calls = [];
  const context = {
    document: {
      querySelector: (selector) => selector.startsWith('#') ? nodes.get(selector.slice(1)) || null : null,
      createElement: (tag) => new Node(tag),
      createElementNS: (_, tag) => new Node(tag),
    },
    window: {
      location: { pathname: '/privacy/mi-plan/', search: '?workspace_site_id=' + siteId },
      MininodeAuth: { ready: async () => {}, getToken: async () => 'clerk-test-token' },
      addEventListener() {},
    },
    URL, URLSearchParams, AbortController, setTimeout, clearTimeout,
    fetch: async (url, options) => {
      calls.push({ url, options });
      return handler(url, options);
    },
  };
  vm.runInNewContext(uxScript, context);
  vm.runInNewContext(script, context);
  return { nodes, calls, context };
}

test('new active courtesy creates baseline only after authenticated GET misses', async () => {
  const ui = mount((url, options) => ({
    ok: options.method === 'POST', status: options.method === 'GET' ? 409 : 200,
    json: async () => payload(),
  }));
  await flush();
  assert.deepEqual(ui.calls.map((call) => [call.url, call.options.method]),
    [[path, 'GET'], [path, 'POST']]);
  assert.equal(ui.calls[0].options.headers.Authorization, 'Bearer clerk-test-token');
  assert.equal(ui.calls[1].options.headers.Authorization, 'Bearer clerk-test-token');
  assert.equal(ui.nodes.get('plan-content').hidden, false);
  assert.equal(ui.nodes.get('check-start').hidden, false);
  assert.equal(ui.nodes.get('current-score').textContent, '65 / 100');
  assert.match(ui.nodes.get('current-date').textContent, /25 oct 2026/);
  assert.equal(ui.nodes.get('current-origin').textContent, 'Primera revisión del sitio');
  assert.equal(ui.nodes.get('summary-count').textContent, 'Sin mejoras accionables detectadas');
  assert.match(ui.nodes.get('actions-empty').textContent, /no acredita cumplimiento legal/i);
  assert.equal(ui.nodes.get('priority-summary').textContent, '');
});

test('expired entitlement retains latest review read-only without creating or scanning', async () => {
  const ui = mount((url, options) => ({
    ok: true, status: 200, json: async () => payload('expired', true),
  }));
  await flush();
  assert.deepEqual(ui.calls.map((call) => call.options.method), ['GET']);
  assert.equal(ui.nodes.get('plan-content').hidden, false);
  assert.equal(ui.nodes.get('check-result').hidden, false);
  assert.equal(ui.nodes.get('check-start').hidden, true);
  assert.equal(ui.nodes.get('check-free').hidden, false);
  assert.match(ui.nodes.get('check-deadline').textContent, /vigencia/);
});

test('revoked or unauthorized access renders no private plan and never creates it', async () => {
  const ui = mount(() => ({ ok: false, status: 403, json: async () => ({ detail: 'Forbidden' }) }));
  await flush();
  assert.deepEqual(ui.calls.map((call) => call.options.method), ['GET']);
  assert.equal(ui.nodes.get('plan-content').hidden, true);
  assert.equal(ui.nodes.get('plan-error').hidden, false);
  assert.equal(ui.nodes.get('check-start').hidden, true);
});

test('active plan review refreshes C2 after POST and keeps persisted result', async () => {
  let reviewed = false;
  const ui = mount((url, options) => {
    if (options.method === 'POST' && url.endsWith('/check')) {
      reviewed = true;
      return { ok: true, status: 200, json: async () => ({
        status: 'available', expires_at: future,
        created_at: '2026-10-26T14:00:00Z',
        result: { version: '2', current_score: 77,
                  comparability: { status: 'not_comparable' }, items: [] },
      }) };
    }
    const latest = payload('available', reviewed);
    if (reviewed) {
      latest.diagnostic.current.score = 77;
      latest.diagnostic.current.created_at = '2026-10-26T14:00:00Z';
      latest.current_actions.created_at = '2026-10-26T14:00:00Z';
    }
    return { ok: true, status: 200, json: async () => latest };
  });
  await flush();
  ui.nodes.get('check-start').click();
  ui.nodes.get('check-submit').click();
  await flush();
  assert.equal(ui.calls.length, 3);
  assert.deepEqual(ui.calls.map((call) => call.options.method), ['GET', 'POST', 'GET']);
  assert.equal(ui.calls[1].url, path + '/check');
  assert.equal(ui.calls[1].options.headers.Authorization, 'Bearer clerk-test-token');
  assert.equal(ui.calls[2].options.headers.Authorization, 'Bearer clerk-test-token');
  assert.equal(ui.nodes.get('check-result').hidden, false);
  assert.equal(ui.nodes.get('check-current-score').textContent, '77 / 100');
  assert.equal(ui.nodes.get('current-score').textContent, '77 / 100');
  assert.equal(ui.nodes.get('current-origin').textContent, 'Última revisión válida');
  assert.match(ui.nodes.get('check-before-date').textContent, /25 oct 2026/);
  assert.match(ui.nodes.get('check-noncomparable-date').textContent, /26 oct 2026/);
  assert.match(ui.nodes.get('actions-date').textContent, /26 oct 2026/);
});

test('failed C2 refresh after successful POST does not misrepresent old state as current', async () => {
  const ui = mount((url, options) => {
    if (url.endsWith('/check')) return { ok: true, status: 200, json: async () => ({
      status: 'available', created_at: '2026-10-27T14:00:00Z',
      result: { current_score: 80, comparability: { status: 'not_comparable' }, items: [] },
    }) };
    if (ui && ui.calls.length > 2) return { ok: false, status: 503, json: async () => ({}) };
    return { ok: true, status: 200, json: async () => payload() };
  });
  await flush();
  ui.nodes.get('check-start').click();
  ui.nodes.get('check-submit').click();
  await flush();
  assert.equal(ui.nodes.get('check-result').hidden, false);
  assert.equal(ui.nodes.get('state-score-block').hidden, true);
  assert.equal(ui.nodes.get('state-diagnostic').hidden, true);
  assert.equal(ui.nodes.get('state-notice').hidden, false);
  assert.match(ui.nodes.get('state-notice').textContent, /Recarga la página/);
  assert.equal(ui.nodes.get('plan-items').children.length, 0);
  assert.equal(ui.nodes.get('actions-notice').hidden, false);
  assert.match(ui.nodes.get('actions-notice').textContent, /Recarga la página/);
});

test('C1 navigation defaults to state and switches panels without new requests', async () => {
  const ui = mount(() => ({ ok: true, status: 200, json: async () => payload() }));
  await flush();
  assert.equal(ui.nodes.get('plan-panel-state').hidden, false);
  assert.equal(ui.nodes.get('plan-panel-actions').hidden, true);
  assert.equal(ui.nodes.get('plan-panel-progress').hidden, true);
  assert.equal(ui.nodes.get('plan-tab-state').attributes.get('aria-current'), 'page');
  ui.nodes.get('plan-tab-actions').click();
  assert.equal(ui.nodes.get('plan-panel-state').hidden, true);
  assert.equal(ui.nodes.get('plan-panel-actions').hidden, false);
  ui.nodes.get('plan-tab-progress').click();
  assert.equal(ui.nodes.get('plan-panel-progress').hidden, false);
  assert.equal(ui.calls.length, 1);
});

test('compact actions summary lists only nonzero priorities and one recommendation count', async () => {
  const item = (priority) => ({
    control_code: 'PRV-003', name: 'Política de privacidad', priority,
    finding: 'Hallazgo observable', recommendation: 'Revisar el sitio',
    action_steps: ['Publicar información'], validation_step: 'Volver a revisar',
  });
  const data = payload();
  data.current_actions.items = [item('Alta'), item('Alta')];
  data.current_actions.item_count = data.current_actions.items.length;
  const ui = mount(() => ({ ok: true, status: 200, json: async () => data }));
  await flush();
  assert.equal(ui.nodes.get('summary-count').textContent, '2 mejoras pendientes');
  assert.equal(ui.nodes.get('priority-summary').textContent, '2 de prioridad alta');
  assert.equal(ui.nodes.get('plan-items').children.length, 2);
  assert.match(ui.nodes.get('actions-date').textContent, /25 oct 2026/);
  assert.equal(ui.calls.length, 1);
});

test('C2 renders five areas, control evidence and observed scope without scores per area', async () => {
  const ui = mount(() => ({ ok: true, status: 200, json: async () => payload() }));
  await flush();
  const areas = ui.nodes.get('state-areas').children;
  assert.equal(areas.length, 5);
  assert.deepEqual(areas.map((area) => area.children[0].children[0].textContent),
    ['Transparencia', 'Formularios', 'Cookies', 'Contacto', 'Seguridad']);
  assert.match(areas[0].children[0].children[1].textContent, /1 no detectado/);
  const firstControl = areas[0].children[1].children[0];
  assert.equal(firstControl.children[0].children[0].textContent, 'Política de privacidad visible');
  assert.equal(firstControl.children[0].children[1].textContent, 'No detectado');
  const body = firstControl.children[1];
  assert.ok(body.children.some((child) => child.textContent === 'Evidencia visible del sitio.'));
  assert.ok(body.children.some((child) => child.href === 'https://example.com/privacy'));
  assert.match(ui.nodes.get('state-scope').textContent, /2 páginas analizadas/);
  assert.equal(ui.nodes.get('plan-panel-actions').hidden, true);
  assert.equal(ui.calls.length, 1);
});

test('C2 preserves unknown historical controls separately and does not use unsafe links', async () => {
  const data = payload();
  data.diagnostic.current.controls.push({
    control_code: 'PRV-OLD', name: 'Control antiguo', area: null, type: null,
    result: 'not_evaluable', reason: 'Evidencia incompleta', confidence: 'low',
    evidence_summary: null, source_url: 'javascript:alert(1)',
  });
  const ui = mount(() => ({ ok: true, status: 200, json: async () => data }));
  await flush();
  const areas = ui.nodes.get('state-areas').children;
  assert.equal(areas.length, 6);
  assert.equal(areas[5].children[0].children[0].textContent, 'Otros controles de esta revisión');
  const oldBody = areas[5].children[1].children[0].children[1];
  assert.equal(oldBody.children.some((child) => child.href), false);
  assert.match(oldBody.children[0].textContent, /Evidencia incompleta/);
});

test('C2 uses one lightweight list per area and groups non-applicable controls', async () => {
  const data = payload();
  data.diagnostic.current.controls.push(
    { control_code: 'PRV-002', name: 'Política accesible', area: 'Transparencia',
      type: 'conditional_evaluation', result: 'not_applicable',
      reason: 'Depende de la política visible', evidence_summary: null, source_url: null },
    { control_code: 'PRV-003', name: 'Política propia', area: 'Transparencia',
      type: 'evaluation', result: 'not_applicable',
      reason: 'La condición no aplica', evidence_summary: null, source_url: null },
  );
  const ui = mount(() => ({ ok: true, status: 200, json: async () => data }));
  await flush();
  const area = ui.nodes.get('state-areas').children[0];
  const list = area.children[1];
  assert.equal(list.children.length, 2, 'one observed control plus one deferred group');
  assert.equal(list.children[0].children[0].children[0].textContent, 'Política de privacidad visible');
  const deferred = list.children[1];
  assert.equal(deferred.children[0].children[0].textContent, 'Mostrar 2 controles no aplicables');
  assert.equal(deferred.children[1].children.length, 2);
  assert.equal(deferred.children[1].children[0].children[0].children[1].textContent, 'No aplica');
  assert.match(area.children[0].children[1].textContent, /2 no aplicables/);
});

test('Mis avances shows original and latest persisted dates directly beneath comparable scores', async () => {
  const data = payload('available', true);
  data.check.latest_check.result = {
    version: '2', comparability: { status: 'comparable' },
    original_score: 65, current_score: 75, score_change: 10,
    corrected_count: 1, pending_count: 0, items: [],
  };
  const ui = mount(() => ({ ok: true, status: 200, json: async () => data }));
  await flush();
  assert.equal(ui.nodes.get('check-before').textContent, '65 / 100');
  assert.equal(ui.nodes.get('check-now').textContent, '75 / 100');
  assert.match(ui.nodes.get('check-before-date').textContent, /25 oct 2026/);
  assert.match(ui.nodes.get('check-now-date').textContent, /26 oct 2026/);
});

test('incomparable reviews retain current date without presenting a score comparison', async () => {
  const ui = mount(() => ({ ok: true, status: 200, json: async () => payload('available', true) }));
  await flush();
  assert.equal(ui.nodes.get('check-comparison').hidden, true);
  assert.equal(ui.nodes.get('check-not-comparable').hidden, false);
  assert.match(ui.nodes.get('check-noncomparable-date').textContent, /26 oct 2026/);
});

test('C2 displays a safe fallback when an old access lacks the C2a diagnostic contract', async () => {
  const data = payload();
  delete data.diagnostic;
  const ui = mount(() => ({ ok: true, status: 200, json: async () => data }));
  await flush();
  assert.equal(ui.nodes.get('state-score-block').hidden, true);
  assert.match(ui.nodes.get('state-notice').textContent, /no está disponible/);
  assert.equal(ui.nodes.get('check-start').hidden, false);
});

const action = (code, priority = 'Alta') => ({
  control_code: code, name: `Control ${code}`, priority,
  finding: 'Hallazgo de la revisión vigente', recommendation: 'Corregir señal pública',
  action_steps: ['Publicar información'], validation_step: 'Revisar otra vez',
});

test('C3b ignores frozen plan items and shows latest actions in backend order', async () => {
  const data = payload('available', true);
  data.plan.items = [action('PRV-001')];
  data.plan.item_count = 1;
  data.current_actions.items = [action('PRV-003', 'Alta'), action('PRV-501', 'Baja')];
  data.current_actions.item_count = 2;
  const ui = mount(() => ({ ok: true, status: 200, json: async () => data }));
  await flush();
  assert.equal(ui.nodes.get('summary-count').textContent, '2 mejoras pendientes');
  assert.equal(ui.nodes.get('priority-summary').textContent, '1 de prioridad alta · 1 de prioridad baja');
  assert.equal(ui.nodes.get('plan-items').children.length, 2);
  assert.equal(ui.nodes.get('actions-notice').hidden, true);
  assert.match(ui.nodes.get('actions-date').textContent, /última revisión válida/);
  assert.equal(ui.calls.length, 1);
});

test('C3b displays pending verification separately and does not imply correction', async () => {
  const data = payload('available', true);
  data.current_actions.verification_pending = [
    { control_code: 'PRV-003', name: 'Política propia', status: 'pending_verification', reason: 'not_applicable' },
    { control_code: 'PRV-001', name: 'Política visible', status: 'pending_verification', reason: 'missing' },
    { control_code: 'PRV-005', name: 'Información', status: 'pending_verification', reason: 'not_evaluable' },
  ];
  data.current_actions.verification_pending_count = 3;
  const ui = mount(() => ({ ok: true, status: 200, json: async () => data }));
  await flush();
  assert.equal(ui.nodes.get('actions-verification').hidden, false);
  assert.equal(ui.nodes.get('plan-items').children.length, 0);
  assert.match(ui.nodes.get('actions-empty').textContent, /controles sin resultado confirmado/);
  assert.equal(ui.nodes.get('actions-verification-count').textContent, '3 controles requieren verificación');
  assert.equal(ui.nodes.get('actions-verification-list').children.length, 3);
  assert.equal(ui.nodes.get('actions-verification-list').children[0].children[1].textContent, 'No aplica en esta revisión');
  assert.equal(ui.nodes.get('actions-verification-list').children[1].children[1].textContent, 'No evaluado en esta revisión');
  assert.equal(ui.nodes.get('actions-verification-list').children[2].children[1].textContent, 'Resultado no concluyente');
});

test('C3b version mismatch never becomes no pending findings', async () => {
  const data = payload('available', true);
  data.current_actions = {
    status: 'version_mismatch', source: 'review',
    created_at: '2026-10-26T13:00:00Z', item_count: null,
    items: [], actions_version: null,
    verification_pending_count: null, verification_pending: [],
  };
  const ui = mount(() => ({ ok: true, status: 200, json: async () => data }));
  await flush();
  assert.equal(ui.nodes.get('actions-notice').hidden, false);
  assert.match(ui.nodes.get('actions-notice').textContent, /no podemos confirmar/i);
  assert.equal(ui.nodes.get('actions-empty').hidden, true);
  assert.equal(ui.nodes.get('plan-items').children.length, 0);
  assert.equal(ui.nodes.get('actions-verification').hidden, true);
});

test('C3b missing or malformed contract does not fall back to historical actions', async () => {
  for (const invalid of [undefined, { status: 'available', item_count: 0, items: [] }]) {
    const data = payload();
    data.plan.items = [action('PRV-001')];
    data.plan.item_count = 1;
    data.current_actions = invalid;
    const ui = mount(() => ({ ok: true, status: 200, json: async () => data }));
    await flush();
    assert.equal(ui.nodes.get('actions-notice').hidden, false);
    assert.equal(ui.nodes.get('plan-items').children.length, 0);
    assert.equal(ui.nodes.get('actions-empty').hidden, true);
    assert.equal(ui.nodes.get('plan-content').hidden, false);
  }
});

test('C3b successful review refresh replaces pending cards and verification results', async () => {
  let reviewed = false;
  const ui = mount((url, options) => {
    if (url.endsWith('/check')) {
      reviewed = true;
      return { ok: true, status: 200, json: async () => ({
        status: 'available', expires_at: future, created_at: '2026-10-26T15:00:00Z',
        result: { current_score: 82, comparability: { status: 'not_comparable' }, items: [] },
      }) };
    }
    const data = payload('available', reviewed);
    data.plan.items = [action('PRV-001')]; data.plan.item_count = 1;
    data.current_actions.items = reviewed ? [action('PRV-003', 'Media')] : [action('PRV-001', 'Alta')];
    data.current_actions.item_count = 1;
    data.current_actions.created_at = reviewed ? '2026-10-26T15:00:00Z' : '2026-10-25T12:00:00Z';
    data.current_actions.verification_pending = reviewed
      ? [{ control_code: 'PRV-501', name: 'HTTPS', status: 'pending_verification', reason: 'missing' }] : [];
    data.current_actions.verification_pending_count = reviewed ? 1 : 0;
    return { ok: true, status: 200, json: async () => data };
  });
  await flush();
  assert.equal(ui.nodes.get('plan-items').children.length, 1);
  assert.equal(ui.nodes.get('actions-verification').hidden, true);
  ui.nodes.get('check-start').click();
  ui.nodes.get('check-submit').click();
  await flush();
  assert.deepEqual(ui.calls.map((call) => call.options.method), ['GET', 'POST', 'GET']);
  assert.equal(ui.nodes.get('plan-items').children.length, 1, 'replaced, never appended');
  assert.equal(ui.nodes.get('actions-verification').hidden, false);
  assert.equal(ui.nodes.get('actions-verification-list').children.length, 1);
  assert.equal(ui.nodes.get('priority-summary').textContent, '1 de prioridad media');
  assert.match(ui.nodes.get('actions-date').textContent, /26 oct 2026/);
});

test('C3b malformed refresh after saved review does not show stale actions', async () => {
  let reviewed = false;
  const ui = mount((url) => {
    if (url.endsWith('/check')) {
      reviewed = true;
      return { ok: true, status: 200, json: async () => ({
        status: 'available', created_at: '2026-10-26T15:00:00Z',
        result: { current_score: 82, comparability: { status: 'not_comparable' }, items: [] },
      }) };
    }
    const data = payload('available', reviewed);
    if (reviewed) delete data.current_actions;
    if (!reviewed) { data.current_actions.items = [action('PRV-001')]; data.current_actions.item_count = 1; }
    return { ok: true, status: 200, json: async () => data };
  });
  await flush();
  assert.equal(ui.nodes.get('plan-items').children.length, 1);
  ui.nodes.get('check-start').click();
  ui.nodes.get('check-submit').click();
  await flush();
  assert.equal(ui.nodes.get('state-score-block').hidden, false);
  assert.equal(ui.nodes.get('plan-items').children.length, 0);
  assert.equal(ui.nodes.get('actions-notice').hidden, false);
});


test('shared UX catalog updates state, verification and progress without altering codes/results', async () => {
  const data = payload('available', true);
  data.diagnostic.current.controls[0] = {
    ...data.diagnostic.current.controls[0],
    control_code: 'PRV-003', name: 'Política propia del responsable', result: 'not_detected',
  };
  data.current_actions.verification_pending = [
    { control_code: 'PRV-003', name: 'Política propia del responsable',
      status: 'pending_verification', reason: 'not_evaluable' },
  ];
  data.current_actions.verification_pending_count = 1;
  data.check.latest_check.result = {
    version: '2', comparability: { status: 'comparable' }, original_score: 65,
    current_score: 75, score_change: 10, corrected_count: 0, pending_count: 1,
    items: [{ control_id: 'PRV-003', name: 'Política propia del responsable', status: 'still_pending' }],
  };
  const ui = mount(() => ({ ok: true, status: 200, json: async () => data }));
  await flush();
  const detail = ui.nodes.get('state-areas').children[0].children[1].children[0];
  assert.equal(detail.children[0].children[0].textContent,
    'Política de privacidad claramente asociada a la empresa');
  assert.match(detail.children[1].children[0].textContent, /empresa o entidad responsable/);
  assert.equal(ui.nodes.get('actions-verification-list').children[0].children[0].textContent,
    'Política de privacidad claramente asociada a la empresa');
  assert.equal(ui.nodes.get('check-items').children[0].children[1].textContent,
    'Política de privacidad claramente asociada a la empresa');
  assert.equal(ui.nodes.get('plan-panel-progress').hidden, true);
  assert.equal(ui.calls.length, 1);
});

test('unknown historical codes keep their original names and no invented explanations', async () => {
  const data = payload();
  data.diagnostic.current.controls.push({
    control_code: 'PRV-HIST', name: 'Nombre histórico',
    area: null, result: 'not_evaluable', reason: 'No evaluable',
    evidence_summary: null, source_url: null,
  });
  const ui = mount(() => ({ ok: true, status: 200, json: async () => data }));
  await flush();
  const otherArea = ui.nodes.get('state-areas').children[5];
  const historical = otherArea.children[1].children[0];
  assert.equal(historical.children[0].children[0].textContent, 'Nombre histórico');
  assert.equal(historical.children[1].children[0].textContent, 'No evaluable');
});

test('C3 progress uses backend control_id and preserves corrected/pending statuses', async () => {
  // compare_diagnostics() persists control_id, not control_code.
  const data = payload('available', true);
  data.check.latest_check.result = {
    version: '2', comparability: { status: 'comparable' },
    original_score: 47, current_score: 47, score_change: 0,
    corrected_count: 0, pending_count: 2, not_evaluable_count: 0,
    items: [
      { control_id: 'PRV-001', name: 'Política de privacidad visible', status: 'still_pending' },
      { control_id: 'PRV-003', name: 'Política propia del responsable', status: 'still_pending' },
    ],
  };
  const handler = () => ({ ok: true, status: 200, json: async () => data });
  const initial = mount(handler);
  await flush();
  assert.equal(initial.nodes.get('check-change').textContent, 'Sin cambios en el score');
  assert.equal(initial.nodes.get('check-pending').textContent, 2);
  const items = initial.nodes.get('check-items').children;
  assert.equal(items.length, 2);
  assert.equal(items[0].children[1].textContent, 'Política de privacidad visible');
  assert.equal(items[1].children[1].textContent,
    'Política de privacidad claramente asociada a la empresa');
  assert.equal(items[1].children[1].children[0].textContent, 'Sigue pendiente');
  assert.equal(items[1].children[0].textContent, '⚠');
  assert.deepEqual(initial.calls.map((call) => call.options.method), ['GET']);

  // A fresh load reads the saved latest review, without performing another scan.
  const reloaded = mount(handler);
  await flush();
  assert.equal(reloaded.nodes.get('check-items').children[1].children[1].textContent,
    'Política de privacidad claramente asociada a la empresa');
  assert.deepEqual(reloaded.calls.map((call) => call.options.method), ['GET']);
});

test('C3 progress supports prior control_code snapshots and unknown historical IDs', async () => {
  const data = payload('available', true);
  data.check.latest_check.result = {
    version: '2', comparability: { status: 'comparable' },
    original_score: 65, current_score: 75, score_change: 10,
    corrected_count: 1, pending_count: 0, not_evaluable_count: 2,
    items: [
      { control_code: 'PRV-003', name: 'Política propia del responsable', status: 'corrected' },
      { control_id: 'PRV-HIST', name: 'Nombre histórico', status: 'not_evaluable' },
      { control_id: 'PRV-999', name: 'Control sin catálogo UX', status: 'not_evaluable' },
    ],
  };
  const ui = mount(() => ({ ok: true, status: 200, json: async () => data }));
  await flush();
  const items = ui.nodes.get('check-items').children;
  assert.equal(items[0].children[1].textContent,
    'Política de privacidad claramente asociada a la empresa');
  assert.equal(items[0].children[1].children[0].textContent, 'Corregido');
  assert.equal(items[0].children[0].textContent, '✓');
  assert.equal(items[1].children[1].textContent, 'Nombre histórico');
  assert.equal(items[1].children[1].children[0].textContent, 'No fue posible evaluarlo');
  assert.equal(items[2].children[1].textContent, 'Control sin catálogo UX');
});

const comparison = (scoreChange = 0, status = 'comparable') => ({
  comparability: { status },
  score_change: status === 'comparable' ? scoreChange : null,
  changes: [],
});
const progressHistory = () => [
  { kind: 'review', created_at: '2026-10-28T13:00:00Z',
    diagnostic: { score: 75 },
    vs_initial: comparison(10), vs_previous: comparison(0) },
  { kind: 'review', created_at: '2026-10-27T13:00:00Z',
    diagnostic: { score: 75 },
    vs_initial: comparison(10), vs_previous: comparison(10) },
  { kind: 'initial', created_at: '2026-10-25T12:00:00Z',
    diagnostic: { score: 65 }, vs_initial: null, vs_previous: null },
];

test('C4c retains one visible score summary, detailed corrections and accessible history', async () => {
  const data = payload('available', true);
  data.history = progressHistory();
  data.check.latest_check.result = {
    comparability: { status: 'comparable' },
    original_score: 65, current_score: 75, score_change: 10,
    corrected_count: 1, pending_count: 1,
    items: [{control_id:'PRV-001', name:'Política visible', status:'corrected'}],
  };
  const ui = mount(() => ({ ok: true, status: 200, json: async () => data }));
  await flush();
  assert.equal(ui.nodes.get('progress-summary').hidden, false);
  assert.equal(ui.nodes.get('improvement-check').attributes.get('data-progress-summary'), 'true');
  assert.equal(ui.nodes.get('check-result').hidden, false);
  assert.equal(ui.nodes.get('check-corrected').textContent, 1);
  assert.equal(ui.nodes.get('check-items').children.length, 1);
  assert.equal(ui.nodes.get('progress-history-list').children.length, 3);
  assert.equal(ui.nodes.get('progress-chart-section').hidden, false);
  const svg = ui.nodes.get('progress-chart').children[0];
  assert.equal(svg.tagName, 'svg');
  const labels = svg.children.filter((node) => node.tagName === 'text');
  assert.ok(labels.some((node) => node.textContent === '75'));
  assert.ok(labels.some((node) => /28 oct/.test(node.textContent)));
  assert.equal(svg.children.filter((node) => node.tagName === 'line').length, 2);
});

test('C4c keeps initial-only history compact before first review', async () => {
  const data = payload('available');
  data.history = [progressHistory().at(-1)];
  const initial = mount(() => ({ ok: true, status: 200, json: async () => data }));
  await flush();
  assert.equal(initial.nodes.get('progress-summary').hidden, false);
  assert.equal(initial.nodes.get('progress-chart-section').hidden, true);
  assert.equal(initial.nodes.get('improvement-check').attributes.get('data-progress-summary'), 'true');
  assert.equal(initial.nodes.get('improvement-check').hidden, true, 'no empty detail card before first review');
  // The first-review action belongs to a separate section, not to the hidden detail card.
  assert.equal(initial.nodes.get('check-start').hidden, false, 'active entitlement can start its first review');
  assert.equal(initial.nodes.get('check-available').hidden, false);
  initial.nodes.get('plan-tab-progress').click();
  assert.equal(initial.nodes.get('plan-panel-progress').hidden, false);
  assert.equal(initial.nodes.get('check-start').hidden, false);
});

test('first review remains actionable with initial-only history and refreshes the history', async () => {
  let reviewed = false;
  const baseline = progressHistory().at(-1);
  const ui = mount((url, options) => {
    if (url.endsWith('/plan/check') && options.method === 'POST') {
      reviewed = true;
      return { ok: true, status: 200, json: async () => ({
        created_at: '2026-10-28T13:00:00Z', expires_at: future,
        result: payload('available', true).check.latest_check.result,
      }) };
    }
    const data = payload('available', reviewed);
    data.history = reviewed
      ? [{
          kind: 'review', created_at: '2026-10-28T13:00:00Z',
          diagnostic: { score: 75 },
          vs_initial: comparison(10), vs_previous: comparison(10),
        }, baseline]
      : [baseline];
    return { ok: true, status: 200, json: async () => data };
  });
  await flush();
  assert.equal(ui.nodes.get('progress-summary').hidden, false);
  assert.equal(ui.nodes.get('improvement-check').hidden, true);
  ui.nodes.get('plan-tab-progress').click();
  assert.equal(ui.nodes.get('plan-panel-progress').hidden, false);
  assert.equal(ui.nodes.get('check-start').hidden, false);
  ui.nodes.get('check-start').click();
  assert.equal(ui.nodes.get('check-confirm').hidden, false);
  ui.nodes.get('check-submit').click();
  await flush();
  assert.deepEqual(ui.calls.map(call => [call.options.method, call.url]), [
    ['GET', path], ['POST', path + '/check'], ['GET', path],
  ]);
  assert.equal(ui.calls[1].options.headers.Authorization, 'Bearer clerk-test-token');
  assert.equal(ui.nodes.get('progress-history-list').children.length, 2);
  assert.equal(ui.nodes.get('progress-chart-section').hidden, false);
  assert.equal(ui.nodes.get('progress-current').textContent, '75/100');
  assert.equal(ui.nodes.get('check-result').hidden, false);
  assert.equal(ui.nodes.get('check-start').hidden, false);
});

test('C4c labels points but never connects incompatible diagnostic versions', async () => {
  const data = payload('available', true);
  data.history = progressHistory();
  data.history[0].vs_previous = comparison(0, 'not_comparable');
  const ui = mount(() => ({ ok: true, status: 200, json: async () => data }));
  await flush();
  const svg = ui.nodes.get('progress-chart').children[0];
  assert.equal(svg.children.filter((node) => node.tagName === 'line').length, 1);
  assert.equal(svg.children.filter((node) => node.tagName === 'circle').length, 3);
});

test('C4c exposes saved review detail if refreshing history fails after POST', async () => {
  let reviewed = false;
  const ui = mount((url) => {
    if (url.endsWith('/check')) {
      reviewed = true;
      return { ok: true, status: 200, json: async () => ({
        created_at: '2026-10-29T13:00:00Z', expires_at: future,
        result: {comparability:{status:'not_comparable'},current_score:76,items:[]},
      }) };
    }
    if (reviewed) return { ok: false, status: 503 };
    const data = payload('available', true);
    data.history = progressHistory();
    return {ok:true,status:200,json:async () => data};
  });
  await flush();
  assert.equal(ui.nodes.get('progress-summary').hidden, false);
  ui.nodes.get('check-start').click();
  ui.nodes.get('check-submit').click();
  await flush();
  assert.equal(ui.nodes.get('progress-summary').hidden, true);
  assert.equal(ui.nodes.get('progress-chart-section').hidden, true);
  assert.equal(ui.nodes.get('improvement-check').attributes.get('data-progress-summary'), 'false');
  assert.equal(ui.nodes.get('check-result').hidden, false);
  assert.match(ui.nodes.get('progress-history-list').children[0].textContent, /Recarga la página/);
});


const subtreeText = (node) => [node.textContent, ...(node.children || []).map(subtreeText)].join(' ');

test('site history spans periods, labels a new baseline and does not bridge inactive periods', async () => {
  const data = payload('available');
  data.history = [
    { kind: 'baseline', period: 1, created_at: '2026-10-28T13:00:00Z',
      diagnostic: { score: 70 }, vs_initial: comparison(5), vs_previous: comparison(5) },
    { kind: 'review', period: 0, created_at: '2026-07-27T13:00:00Z',
      diagnostic: { score: 65 }, vs_initial: comparison(0), vs_previous: comparison(0) },
    { kind: 'initial', period: 0, created_at: '2026-07-21T13:00:00Z',
      diagnostic: { score: 65 }, vs_initial: null, vs_previous: null },
  ];
  const ui = mount(() => ({ ok: true, status: 200, json: async () => data }));
  await flush();
  assert.equal(ui.nodes.get('progress-history-list').children.length, 3);
  assert.match(subtreeText(ui.nodes.get('progress-history-list').children[0]), /Diagnóstico de reactivación/);
  assert.match(subtreeText(ui.nodes.get('progress-history-list').children[0]), /no implica seguimiento durante la pausa/);
  assert.equal(ui.nodes.get('progress-initial').textContent, '65/100');
  assert.equal(ui.nodes.get('progress-current').textContent, '70/100');
  const svg = ui.nodes.get('progress-chart').children[0];
  assert.equal(svg.children.filter((node) => node.tagName === 'line').length, 1,
    'only the earlier same-period segment is connected');
  assert.match(ui.nodes.get('progress-chart-note').textContent, /períodos de acceso distintos/);
});

test('renewal reusing last observed diagnostic does not add duplicate history point', async () => {
  const data = payload('available');
  data.history = [
    { kind: 'review', period: 0, created_at: '2026-07-28T13:00:00Z',
      diagnostic: { score: 47 }, vs_initial: comparison(0), vs_previous: comparison(0) },
    { kind: 'initial', period: 0, created_at: '2026-07-21T12:00:00Z',
      diagnostic: { score: 47 }, vs_initial: null, vs_previous: null },
  ];
  const ui = mount(() => ({ ok: true, status: 200, json: async () => data }));
  await flush();
  assert.equal(ui.nodes.get('progress-history-list').children.length, 2);
  assert.equal(ui.nodes.get('progress-current').textContent, '47/100');
  assert.doesNotMatch(subtreeText(ui.nodes.get('progress-history-list').children[0]), /Diagnóstico de reactivación/);
});


test('reactivation baseline with comparable versions displays real score change', async () => {
  const data = payload('available');
  data.history = [
    { kind: 'baseline', period: 1, created_at: '2026-10-28T13:00:00Z',
      diagnostic: { score: 72 }, vs_initial: comparison(7), vs_previous: comparison(7) },
    { kind: 'initial', period: 0, created_at: '2026-07-21T13:00:00Z',
      diagnostic: { score: 65 }, vs_initial: null, vs_previous: null },
  ];
  const ui = mount(() => ({ ok: true, status: 200, json: async () => data }));
  await flush();
  assert.equal(ui.nodes.get('progress-current').textContent, '72/100');
  assert.match(ui.nodes.get('progress-delta').textContent, /\+7 puntos respecto del diagnóstico inicial/);
  assert.doesNotMatch(ui.nodes.get('progress-delta').textContent, /versiones incompatibles/);
  assert.equal(ui.nodes.get('progress-counts').textContent, '',
    'a new baseline is not a confirmed correction');
});

test('reactivation baseline with incompatible versions does not compare scores', async () => {
  const data = payload('available');
  data.history = [
    { kind: 'baseline', period: 1, created_at: '2026-10-28T13:00:00Z',
      diagnostic: { score: 72 }, vs_initial: comparison(0, 'not_comparable'),
      vs_previous: comparison(0, 'not_comparable') },
    { kind: 'initial', period: 0, created_at: '2026-07-21T13:00:00Z',
      diagnostic: { score: 65 }, vs_initial: null, vs_previous: null },
  ];
  const ui = mount(() => ({ ok: true, status: 200, json: async () => data }));
  await flush();
  assert.match(ui.nodes.get('progress-delta').textContent, /versiones incompatibles/);
  assert.doesNotMatch(ui.nodes.get('progress-delta').textContent, /\+7 puntos/);
});
