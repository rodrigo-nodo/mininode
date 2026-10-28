import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const html = readFileSync(new URL('./index.html', import.meta.url), 'utf8');
const script = readFileSync(new URL('../plan-assets/app.js', import.meta.url), 'utf8');
const siteId = '11111111-1111-4111-8111-111111111111';
const path = `/api/privacy/workspace-sites/${siteId}/plan`;
const future = new Date(Date.now() + 3600000).toISOString();
const past = new Date(Date.now() - 3600000).toISOString();

class Node {
  constructor() {
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
  append(node) { this.children.push(node); }
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
      createElement: () => new Node(),
    },
    window: {
      location: { pathname: '/privacy/plan/', search: '?workspace_site_id=' + siteId },
      MininodeAuth: { ready: async () => {}, getToken: async () => 'clerk-test-token' },
      addEventListener() {},
    },
    URL, URLSearchParams, AbortController, setTimeout, clearTimeout,
    fetch: async (url, options) => {
      calls.push({ url, options });
      return handler(url, options);
    },
  };
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
  assert.equal(ui.nodes.get('summary-count').textContent, 'Sin mejoras recomendadas');
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
  data.plan.items = [item('Alta'), item('Alta')];
  data.plan.item_count = data.plan.items.length;
  const ui = mount(() => ({ ok: true, status: 200, json: async () => data }));
  await flush();
  assert.equal(ui.nodes.get('summary-count').textContent, '2 mejoras recomendadas');
  assert.equal(ui.nodes.get('priority-summary').textContent, '2 de prioridad alta');
  assert.equal(ui.nodes.get('plan-items').children.length, 2);
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

test('C2 displays a safe fallback when an old access lacks the C2a diagnostic contract', async () => {
  const data = payload();
  delete data.diagnostic;
  const ui = mount(() => ({ ok: true, status: 200, json: async () => data }));
  await flush();
  assert.equal(ui.nodes.get('state-score-block').hidden, true);
  assert.match(ui.nodes.get('state-notice').textContent, /no está disponible/);
  assert.equal(ui.nodes.get('check-start').hidden, false);
});
