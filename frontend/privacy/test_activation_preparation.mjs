import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const html = readFileSync(new URL('./index.html', import.meta.url), 'utf8');
const source = readFileSync(new URL('./app.js', import.meta.url), 'utf8');
const siteId = '11111111-1111-4111-8111-111111111111';
const path = '/api/privacy/workspace-sites/' + siteId + '/prepare-activation';

class Element {
  constructor() {
    this.hidden = false;
    this.disabled = false;
    this.textContent = '';
    this.value = '';
    this.children = [];
    this.listeners = new Map();
    this.classList = { add() {}, remove() {} };
  }
  append(child) { this.children.push(child); }
  replaceChildren() { this.children.length = 0; }
  setAttribute(name, value) { this[name] = String(value); }
  addEventListener(name, callback) { this.listeners.set(name, callback); }
  click() {
    const listener = this.listeners.get('click');
    assert.ok(listener, 'expected a real click handler');
    listener({ preventDefault() {}, currentTarget: this });
  }
  querySelector() { return null; }
  querySelectorAll() { return []; }
  scrollIntoView() {}
  focus() {}
}

const future = () => new Date(Date.now() + 60 * 60 * 1000).toISOString();
const past = () => new Date(Date.now() - 60 * 60 * 1000).toISOString();

function diagnosis(id, expiresAt, score = 82) {
  return {
    site_url: 'https://saved.example/',
    diagnostic_id: id,
    workspace_site_id: siteId,
    purchase_expires_at: expiresAt,
    score,
    controls: [],
    priorities: [{ name: 'Revisar la política de privacidad' }],
    scope: { pages_analyzed: 1 },
  };
}

function mount(search = '') {
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map((m) => m[1]);
  const elements = new Map(ids.map((id) => [id, new Element()]));
  const document = {
    body: new Element(),
    activeElement: null,
    querySelector: (selector) => selector.startsWith('#') ? elements.get(selector.slice(1)) ?? null : null,
    createElement: () => new Element(),
    addEventListener() {},
  };
  const calls = [];
  const windowListeners = new Map();
  const window = {
    location: { search, assign() { throw new Error('unexpected navigation'); } },
    MininodeAuth: {
      ready: async () => {},
      getToken: async () => 'clerk-test-token',
    },
    addEventListener(name, listener) { windowListeners.set(name, listener); },
  };
  const context = {
    document, window, URL, URLSearchParams,
    console: { error() {} },
    sessionStorage: { setItem() {} },
    fetch: async (url, opts) => {
      calls.push({ url, opts });
      throw new Error('fetch response must be configured by test');
    },
  };
  vm.runInNewContext(source + '\nglobalThis.renderSavedForTest = renderDiagnostic; globalThis.diagnosticIdForTest = () => currentDiagnosticId; globalThis.showEntitledForTest = showEntitledPrivacyWeb;', context);
  return {
    elements, context, calls,
    show: (d) => context.renderSavedForTest(d, d.site_url),
    start: () => windowListeners.get('load')?.(),
  };
}

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}
const settle = () => new Promise((resolve) => setImmediate(resolve));

test('recent saved diagnosis uses the same click without a refresh message or new inspection', async () => {
  const ui = mount();
  const original = diagnosis('DIAG-RECENT', future());
  ui.show(original);
  ui.context.fetch = async (url, opts) => {
    ui.calls.push({ url, opts });
    return { ok: true, json: async () => ({ refreshed: false, diagnostic: original }) };
  };
  const button = ui.elements.get('correction-order-open');
  button.click();
  await settle();
  assert.equal(ui.calls.length, 1);
  assert.equal(ui.calls[0].url, path);
  assert.equal(ui.calls[0].opts.method, 'POST');
  assert.equal(ui.calls[0].opts.headers.Authorization, 'Bearer clerk-test-token');
  assert.equal(ui.context.diagnosticIdForTest(), 'DIAG-RECENT');
  assert.equal(ui.elements.get('privacy-activation-notice').textContent,
    'Tu diagnóstico está listo. El pago en línea estará disponible próximamente.');
  assert.equal(button.disabled, false);
});

test('stale saved diagnosis shows exact copy, waits, and renders new snapshot on success', async () => {
  const ui = mount();
  ui.show(diagnosis('DIAG-OLD', past(), 70));
  const awaiting = deferred();
  ui.context.fetch = async (url, opts) => {
    ui.calls.push({ url, opts });
    return awaiting.promise;
  };

  const button = ui.elements.get('correction-order-open');
  button.click();
  await settle();
  assert.equal(ui.calls.length, 1);
  assert.equal(button.disabled, true);
  assert.equal(ui.elements.get('privacy-activation-notice').hidden, false);
  assert.equal(ui.elements.get('privacy-activation-notice').textContent,
    'Estamos actualizando el diagnóstico de tu sitio antes de continuar.');
  assert.equal(ui.context.diagnosticIdForTest(), 'DIAG-OLD');
  button.click();
  await settle();
  assert.equal(ui.calls.length, 1, 'duplicate click must not start another inspection');

  awaiting.resolve({
    ok: true,
    json: async () => ({ refreshed: true, diagnostic: diagnosis('DIAG-NEW', future(), 89) }),
  });
  await settle();
  assert.equal(ui.context.diagnosticIdForTest(), 'DIAG-NEW');
  assert.equal(ui.elements.get('score-value').textContent, 89);
  assert.equal(button.disabled, false);
  assert.equal(ui.elements.get('privacy-activation-notice').textContent,
    'Tu diagnóstico está listo. El pago en línea estará disponible próximamente.');
});

test('failed refresh retains old saved result, shows error, and retries same action', async () => {
  const ui = mount();
  ui.show(diagnosis('DIAG-PRESERVED', past(), 66));
  let attempts = 0;
  ui.context.fetch = async (url, opts) => {
    ui.calls.push({ url, opts });
    attempts += 1;
    if (attempts === 1) return { ok: false, status: 503 };
    return { ok: true, json: async () => ({
      refreshed: true, diagnostic: diagnosis('DIAG-RETRIED', future(), 91),
    }) };
  };
  const button = ui.elements.get('correction-order-open');
  button.click();
  await settle();
  assert.equal(ui.context.diagnosticIdForTest(), 'DIAG-PRESERVED');
  assert.equal(ui.elements.get('score-value').textContent, 66);
  assert.equal(ui.elements.get('privacy-activation-notice').hidden, false);
  assert.equal(ui.elements.get('privacy-activation-notice').textContent,
    'No pudimos actualizar el diagnóstico. Intenta nuevamente para continuar.');
  assert.equal(button.disabled, false);
  assert.equal(ui.calls.length, 1);

  button.click();
  await settle();
  assert.equal(ui.calls.length, 2);
  assert.equal(ui.context.diagnosticIdForTest(), 'DIAG-RETRIED');
  assert.equal(ui.elements.get('score-value').textContent, 91);
  assert.equal(button.disabled, false);
  assert.equal(ui.elements.get('privacy-activation-notice').textContent,
    'Tu diagnóstico está listo. El pago en línea estará disponible próximamente.');
});

test('invalid preparation response must fail closed and keep the old result', async () => {
  const ui = mount();
  ui.show(diagnosis('DIAG-OLD', past()));
  ui.context.fetch = async () => ({ ok: true, json: async () => ({
    refreshed: true, diagnostic: { score: 90, site_url: 'https://saved.example/' },
  }) });
  ui.elements.get('correction-order-open').click();
  await settle();
  assert.equal(ui.context.diagnosticIdForTest(), 'DIAG-OLD');
  assert.match(ui.elements.get('privacy-activation-notice').textContent, /Intenta nuevamente/);
  assert.equal(ui.elements.get('correction-order-open').disabled, false);
});

test('active entitlement opens private plan instead of preparing another purchase', async () => {
  const ui = mount();
  const original = diagnosis('DIAG-ACTIVE', future());
  ui.show(original);
  let navigation = '';
  ui.context.window.location.assign = (url) => { navigation = url; };
  const button = ui.elements.get('correction-order-open');
  ui.context.showEntitledForTest();
  assert.equal(button.textContent, 'Abrir Privacy Web →');
  assert.equal(ui.elements.get('privacy-correction-offer').hidden, false);
  assert.equal(ui.elements.get('correction-order-availability').hidden, true);
  assert.equal(ui.elements.get('correction-order-validity').hidden, true);
  button.click();
  await settle();
  assert.equal(ui.calls.length, 0, 'an active entitlement must not prepare a new purchase');
  assert.equal(navigation, '/privacy/plan/?workspace_site_id=' + siteId);
});

test('entitlement HTTP failure preserves saved diagnosis and offers real retry', async () => {
  const ui = mount('?workspace_site_id=' + siteId + '&view=latest');
  const old = diagnosis('DIAG-SAVED', future(), 71);
  let entitlementRequests = 0;
  let actualInspections = 0;
  ui.context.fetch = async (url, opts) => {
    if (url === '/api/access/context') {
      return { ok: true, json: async () => ({
        workspaces: [{ sites: [{ id: siteId, hostname: 'saved.example' }] }],
      }) };
    }
    if (url.endsWith('/latest-review')) return { ok: true, json: async () => old };
    if (url.endsWith('/entitlement')) {
      entitlementRequests += 1;
      if (entitlementRequests === 1) return { ok: false, status: 503 };
      return { ok: true, json: async () => ({ active: true, source: 'internal_grant' }) };
    }
    if (url.endsWith('/prepare-activation')) actualInspections += 1;
    throw new Error('unexpected endpoint: ' + url);
  };
  ui.start();
  await settle();
  const button = ui.elements.get('correction-order-open');
  const notice = ui.elements.get('privacy-activation-notice');
  assert.equal(ui.elements.get('privacy-result').hidden, false);
  assert.equal(ui.elements.get('score-value').textContent, 71);
  assert.equal(ui.context.diagnosticIdForTest(), 'DIAG-SAVED');
  assert.equal(button.textContent, 'Reintentar acceso →');
  assert.equal(button.disabled, false);
  assert.match(notice.textContent, /No pudimos verificar tu acceso/);
  button.click();
  await settle();
  assert.equal(entitlementRequests, 2);
  assert.equal(button.textContent, 'Abrir Privacy Web →');
  assert.equal(notice.hidden, true);
  assert.equal(ui.context.diagnosticIdForTest(), 'DIAG-SAVED');
  assert.equal(actualInspections, 0);
});

for (const failure of ['network', 'invalid_json']) {
  test('entitlement ' + failure + ' shows retry without losing the visible diagnosis', async () => {
    const ui = mount('?workspace_site_id=' + siteId + '&view=latest');
    const old = diagnosis('DIAG-SAVED', future(), 67);
    let attempt = 0;
    ui.context.fetch = async (url) => {
      if (url === '/api/access/context') return { ok: true, json: async () => ({
        workspaces: [{ sites: [{ id: siteId, hostname: 'saved.example' }] }],
      }) };
      if (url.endsWith('/latest-review')) return { ok: true, json: async () => old };
      if (url.endsWith('/entitlement')) {
        attempt += 1;
        if (attempt === 1 && failure === 'network') throw new Error('Network unavailable');
        if (attempt === 1) return { ok: true, json: async () => { throw new SyntaxError('Bad JSON'); } };
        return { ok: true, json: async () => ({ active: false }) };
      }
      throw new Error('unexpected');
    };
    ui.start();
    await settle();
    assert.equal(ui.elements.get('score-value').textContent, 67);
    assert.equal(ui.elements.get('privacy-result').hidden, false);
    const button = ui.elements.get('correction-order-open');
    assert.equal(button.textContent, 'Reintentar acceso →');
    button.click();
    await settle();
    assert.equal(attempt, 2);
    assert.equal(button.textContent, 'Continuar →');
    assert.equal(ui.elements.get('privacy-activation-notice').hidden, true);
    assert.equal(ui.context.diagnosticIdForTest(), 'DIAG-SAVED');
  });
}
