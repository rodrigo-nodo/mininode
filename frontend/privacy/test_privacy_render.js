const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

class ClassList {
  add() {}
  remove() {}
}

class Element {
  constructor(tagName = 'div') {
    this.tagName = tagName.toUpperCase();
    this.children = [];
    this.hidden = false;
    this.textContent = '';
    this.className = '';
    this.classList = new ClassList();
    this.disabled = false;
    this.value = '';
    this.listeners = new Map();
  }

  append(child) { this.children.push(child); }
  replaceChildren() { this.children = []; }
  setAttribute(name, value) { this[name] = String(value); }
  addEventListener(type, listener) { this.listeners.set(type, listener); }
  trigger(type, event = {}) {
    const listener = this.listeners.get(type);
    return listener?.({ preventDefault() {}, currentTarget: this, ...event });
  }
  querySelector() { return null; }
  querySelectorAll() { return []; }
  scrollIntoView() { this.scrolled = true; }
  focus() { this.focused = true; }
}

const html = fs.readFileSync(`${__dirname}/index.html`, 'utf8');
const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map((match) => match[1]);
const elements = new Map(ids.map((id) => [id, new Element()]));
const modalPanel = new Element('section');
const modalCloseButton = new Element('button');
elements.get('privacy-modal').querySelector = (selector) => selector === '.privacy-modal__panel' ? modalPanel : null;
elements.get('privacy-modal').querySelectorAll = (selector) => selector === '[data-modal-close]' ? [modalCloseButton] : [];
const documentListeners = new Map();
const document = {
  body: new Element('body'),
  activeElement: null,
  createElement: (tagName) => new Element(tagName),
  querySelector: (selector) => selector.startsWith('#') ? elements.get(selector.slice(1)) ?? null : null,
  addEventListener(type, listener) { documentListeners.set(type, listener); },
};

const source = fs.readFileSync(`${__dirname}/app.js`, 'utf8');
const catalog = fs.readFileSync(`${__dirname}/control-ux.js`, 'utf8');
const context = {
  document,
  URL,
  URLSearchParams,
  window: {
    location: { search: '', assign() {} },
    addEventListener() {},
  },
  sessionStorage: {
    setItem() {},
    getItem() { return null; },
    removeItem() {},
  },
  FormData: class {},
  fetch: async () => { throw new Error('not used'); },
};
vm.runInNewContext(`${catalog}
${source}
globalThis.renderDiagnosticForTest = renderDiagnostic;
globalThis.resetCommercialStateForTest = resetCommercialState;
globalThis.currentDiagnosticIdForTest = () => currentDiagnosticId;
globalThis.isValidDiagnosticResponseForTest = isValidDiagnosticResponse;`, context);

const codes = [
  'PRV-001', 'PRV-002', 'PRV-003', 'PRV-004', 'PRV-005', 'PRV-006',
  'PRV-007', 'PRV-008', 'PRV-009', 'PRV-010', 'PRV-011', 'PRV-012',
  'PRV-013', 'PRV-014',
  'PRV-101', 'PRV-102', 'PRV-103', 'PRV-104', 'PRV-201', 'PRV-301', 'PRV-501',
];
const controls = codes.map((control_code, index) => ({
  control_code,
  result: index === 3 ? 'not_evaluable' : index === 8 ? 'not_applicable' : 'detected',
  confidence: 'high',
  evidence: [],
  reason: 'Resultado determinístico del control.',
}));
const baseDiagnostic = {
  diagnostic_id: 'DIAG-A',
  claim_token: 'test-claim-proof-kept-out-of-urls',
  score: 82,
  coverage: 79,
  evaluated_controls: 11,
  applicable_controls: 14,
  status: 'Preparación avanzada',
  controls,
  priorities: [{
    control_code: 'PRV-001',
    name: 'Actualizar la política',
    priority: 'Alta',
    finding: 'No se encontró una política visible.',
    recommendation: 'Publica una versión vigente.',
    action_steps: ['Publica la política.', 'Enlázala desde el pie de página.'],
    validation_step: 'Comprueba que el enlace sea visible.',
  }],
  scope: { pages_requested: 5, pages_analyzed: 4, limited: false },
};

assert.equal(context.isValidDiagnosticResponseForTest(baseDiagnostic), true);
assert.doesNotThrow(() => context.renderDiagnosticForTest(baseDiagnostic, 'https://example.com'));
assert.equal(elements.get('score-value').textContent, 82);
assert.equal(elements.get('score-status').textContent, 'Evaluación parcial');
assert.match(elements.get('diagnostic-coverage').textContent, /11 de 14 controles aplicables/);
assert.equal(elements.get('diagnostic-coverage').hidden, false);
assert.equal(elements.get('diagnostic-areas').children.length, 5);
const areaButtons = elements.get('diagnostic-areas').children.map((area) => area.children[0]);
assert.equal(areaButtons.every((button) => button.tagName === 'BUTTON' && button.type === 'button'), true);
assert.deepEqual(areaButtons.map((button) => button.children[1].textContent), ['ⓘ', 'ⓘ', 'ⓘ', 'ⓘ', 'ⓘ']);
assert.equal(areaButtons[0]['aria-label'], 'Información sobre el área Transparencia');
areaButtons[0].trigger('click');
assert.equal(elements.get('privacy-modal').hidden, false);
assert.equal(elements.get('privacy-modal-title').textContent, 'Transparencia');
assert.deepEqual(
  elements.get('privacy-modal-content').children.map((block) => block.children[0].textContent),
  ['Qué revisamos', 'Por qué importa', 'Fundamento normativo'],
);
assert.equal(elements.get('privacy-modal-content').children[2].className, 'privacy-modal__block privacy-modal__block--secondary');
areaButtons[1].trigger('click');
assert.equal(elements.get('privacy-modal-title').textContent, 'Formularios');
assert.match(elements.get('privacy-modal-content').children[0].children[1].textContent, /formularios/);
elements.get('how-it-works').trigger('click');
assert.equal(elements.get('privacy-modal-content').children.every((block) => !block.className.includes('--secondary')), true);
modalCloseButton.trigger('click');
assert.equal(elements.get('privacy-modal').hidden, true);
areaButtons[2].trigger('click');
documentListeners.get('keydown')({ key: 'Escape' });
assert.equal(elements.get('privacy-modal').hidden, true);
assert.match(html, /Ver qué revisamos/);
assert.equal(elements.get('diagnostic-controls').children.length, 5);
assert.equal(
  elements.get('diagnostic-controls').children.reduce((total, area) => total + area.children[1].children.length, 0),
  21,
);
assert.equal(elements.get('diagnostic-priorities').children.length, 1);
assert.equal(elements.get('privacy-correction-offer').hidden, false);
assert.equal(context.currentDiagnosticIdForTest(), 'DIAG-A');
assert.equal(elements.get('privacy-no-priorities').hidden, true);
assert.doesNotMatch(html, /Plan de corrección/);
assert.match(html, /Activar Privacy Web/);
assert.match(html, /Conocer Privacy Data/);
assert.equal(elements.get('request-error').textContent, '');

const controlsWithGaps = controls
  .filter(({ control_code }) => control_code !== 'PRV-002')
  .map((control) => control.control_code === 'PRV-003' ? { ...control, result: 'unexpected_result' } : control);
assert.doesNotThrow(() => context.renderDiagnosticForTest({
  ...baseDiagnostic,
  controls: [null, ...controlsWithGaps, { control_code: 'PRV-999', result: 'detected' }],
  priorities: [{ name: 'Prioridad sin campos opcionales' }, null],
  scope: null,
}, 'https://example.com'));
assert.equal(
  elements.get('diagnostic-controls').children.reduce((total, area) => total + area.children[1].children.length, 0),
  21,
);
const transparencyItems = elements.get('diagnostic-controls').children[0].children[1].children;
assert.equal(transparencyItems[1].children[1].children[0].textContent, 'No pudimos revisarlo');
assert.equal(transparencyItems[2].children[1].children[0].textContent, 'No pudimos revisarlo');
const formItems = elements.get('diagnostic-controls').children[1].children[1].children;
assert.equal(formItems.length, 4);
assert.equal(formItems[0].children[1].children[0].textContent, 'Detectado');
assert.equal(formItems[1].children[1].children[0].textContent, 'Bien');
assert.equal(elements.get('diagnostic-areas').children[2].children[1].textContent, 'Informativo');

assert.doesNotThrow(() => context.renderDiagnosticForTest({ ...baseDiagnostic, priorities: [] }, 'https://example.com'));
assert.equal(elements.get('diagnostic-priorities').children.length, 1);
assert.match(elements.get('diagnostic-priorities').children[0].textContent, /No se identificaron acciones prioritarias/);
assert.equal(elements.get('privacy-correction-offer').hidden, true);
assert.equal(elements.get('privacy-no-priorities').hidden, false);

// A new diagnosis resets the previous result without changing persisted history.
context.resetCommercialStateForTest();
assert.equal(context.currentDiagnosticIdForTest(), '');
assert.equal(elements.get('privacy-correction-offer').hidden, true);

// The following result can only rebuild an offer for its own diagnostic id.
context.renderDiagnosticForTest({ ...baseDiagnostic, diagnostic_id: 'DIAG-B' }, 'https://site-b.example');
assert.equal(context.currentDiagnosticIdForTest(), 'DIAG-B');
assert.equal(elements.get('privacy-correction-offer').hidden, false);

// A visual result without an id never reuses A and replaces the priced card
// with a clear, non-technical recovery state.
context.resetCommercialStateForTest();
context.renderDiagnosticForTest({ ...baseDiagnostic, diagnostic_id: undefined }, 'https://site-c.example');
assert.equal(context.currentDiagnosticIdForTest(), '');
assert.equal(elements.get('privacy-correction-offer').hidden, true);
assert.equal(elements.get('privacy-correction-unavailable').hidden, false);
assert.match(html, /Privacy Web no disponible/);
assert.match(html, /Realizar nuevo diagnóstico/);
// B2: the recovery CTA must return to the diagnosis form and focus the URL.
assert.equal(elements.get('privacy-form').scrolled, undefined);
assert.equal(elements.get('site-url').focused, undefined);
elements.get('correction-unavailable-retry').trigger('click');
assert.equal(elements.get('privacy-form').scrolled, true);
assert.equal(elements.get('site-url').focused, true);

for (const score of [26, 100]) {
  assert.doesNotThrow(() => context.renderDiagnosticForTest({ ...baseDiagnostic, score, priorities: [] }, 'https://example.com'));
  assert.match(html, /<section class="privacy-data-next-step"/);
  assert.match(html, /href="\/privacy\/data\/">Conocer Privacy Data<\/a>/);
}
assert.equal(context.isValidDiagnosticResponseForTest({ score: 50, controls: null, priorities: null }), true);
assert.equal(context.isValidDiagnosticResponseForTest({ score: null }), false);

// Full coverage keeps the score and existing human-friendly status.
context.renderDiagnosticForTest({
  ...baseDiagnostic, coverage: 100, evaluated_controls: 14, applicable_controls: 14,
}, 'https://example.com');
assert.equal(elements.get('score-value').textContent, 82);
assert.equal(elements.get('score-status').textContent, 'Bien');
assert.equal(elements.get('diagnostic-coverage').hidden, true);

// No evaluable controls must not look like a failure with score 0.
context.renderDiagnosticForTest({
  ...baseDiagnostic, score: 0, coverage: 0, evaluated_controls: 0, applicable_controls: 12,
}, 'https://example.com');
assert.equal(elements.get('score-value').textContent, '—');
assert.equal(elements.get('score-status').textContent, 'Sin evidencia suficiente');
assert.match(elements.get('diagnostic-coverage').textContent, /No es una calificación negativa/);

// Historical snapshots without coverage still render their score, with an explanation.
const { coverage: _coverage, evaluated_controls: _evaluated, applicable_controls: _applicable,
  ...historical } = baseDiagnostic;
context.renderDiagnosticForTest(historical, 'https://example.com');
assert.equal(elements.get('score-value').textContent, 82);
assert.match(elements.get('diagnostic-coverage').textContent, /No hay información de cobertura/);

// A partially checked area may not show "Bien" without qualifications.
const partialAreaControls = controls.map((item) => item.control_code === 'PRV-005'
  ? { ...item, result: 'not_evaluable' } : item);
context.renderDiagnosticForTest({
  ...baseDiagnostic, controls: partialAreaControls,
}, 'https://example.com');
assert.equal(elements.get('diagnostic-areas').children[0].children[1].textContent, 'Evaluación parcial');

// Historical not_applicable for observational Cookies is neutral.
const oldCookies = controls.map((item) => item.control_code === 'PRV-201'
  ? { ...item, result: 'not_applicable' } : item);
context.renderDiagnosticForTest({ ...baseDiagnostic, controls: oldCookies }, 'https://example.com');
assert.equal(elements.get('diagnostic-areas').children[2].children[1].textContent, 'Informativo');
assert.equal(elements.get('diagnostic-controls').children[2].children[1].children[0]
  .children[1].children[0].textContent, 'No detectado');


// B1: simulate the actual Access handoff to a saved site, without contacting APIs.
const savedSite = 'SITE-TEST-1';
const makeSavedReviewHarness = (search, review) => {
  const nodes = new Map(ids.map((id) => [id, new Element()]));
  const doc = {
    body: new Element('body'),
    querySelector: (selector) => selector.startsWith('#') ? nodes.get(selector.slice(1)) ?? null : null,
    addEventListener() {},
    createElement: (tagName) => new Element(tagName),
  };
  const responses = [];
  const auth = { ready: async () => {}, getToken: async () => 'test-token' };
  const sandbox = {
    document: doc, URL, URLSearchParams,
    sessionStorage: { setItem() {}, removeItem() {}, getItem() { return null; } },
    window: { location: { search, assign() {} }, MininodeAuth: auth, addEventListener() {} },
    fetch: async (url) => {
      responses.push(url);
      if (url === '/api/access/context') {
        return { ok: true, json: async () => ({ workspaces: [
          { sites: [{ id: savedSite, hostname: 'example.com' }] },
        ] }) };
      }
      if (url === `/api/privacy/workspace-sites/${savedSite}/latest-review`) {
        return { ok: true, json: async () => review };
      }
      throw new Error(`Unexpected request: ${url}`);
    },
  };
  vm.runInNewContext(`${catalog}
${source}\nglobalThis.runSavedReviewForTest = initializeAuthenticatedSite;`, sandbox);
  return { nodes, sandbox, responses };
};

const testActivationAfterLogin = async () => {
  const fresh = { ...baseDiagnostic, workspace_site_id: savedSite,
    purchase_expires_at: '2999-01-01T00:00:00Z' };
  const pending = makeSavedReviewHarness(
    `?workspace_site_id=${savedSite}&view=latest&activation=pending`, fresh);
  await pending.sandbox.runSavedReviewForTest();
  assert.equal(pending.nodes.get('privacy-result').hidden, false);
  assert.equal(pending.nodes.get('privacy-activation-notice').hidden, false,
    'B1: Access activation intent must show confirmation after saving');
  assert.deepEqual(pending.responses, ['/api/access/context',
    `/api/privacy/workspace-sites/${savedSite}/latest-review`]);

  const ordinary = makeSavedReviewHarness(`?workspace_site_id=${savedSite}&view=latest`, fresh);
  await ordinary.sandbox.runSavedReviewForTest();
  assert.equal(ordinary.nodes.get('privacy-activation-notice').hidden, true,
    'Ordinary saved review must not announce an activation attempt');

  const noOffer = makeSavedReviewHarness(
    `?workspace_site_id=${savedSite}&view=latest&activation=pending`,
    { ...fresh, priorities: [] });
  await noOffer.sandbox.runSavedReviewForTest();
  assert.equal(noOffer.nodes.get('privacy-activation-notice').hidden, true,
    'No action priorities means no activation intent can be confirmed');

  const expired = makeSavedReviewHarness(
    `?workspace_site_id=${savedSite}&view=latest&activation=pending`,
    { ...fresh, purchase_expires_at: '2000-01-01T00:00:00Z' });
  await expired.sandbox.runSavedReviewForTest();
  assert.equal(expired.nodes.get('privacy-activation-notice').hidden, true,
    'An expired activation window cannot claim preparation is still pending');
};

void testActivationAfterLogin().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
