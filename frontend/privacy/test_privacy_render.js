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
  scrollIntoView() {}
  focus() {}
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
const context = {
  document,
  URL,
  FormData: class {},
  fetch: async () => { throw new Error('not used'); },
};
vm.runInNewContext(`${source}
globalThis.renderDiagnosticForTest = renderDiagnostic;
globalThis.resetCommercialStateForTest = resetCommercialState;
globalThis.currentDiagnosticIdForTest = () => currentDiagnosticId;
globalThis.isValidDiagnosticResponseForTest = isValidDiagnosticResponse;`, context);

const codes = [
  'PRV-001', 'PRV-002', 'PRV-003', 'PRV-004', 'PRV-005', 'PRV-006',
  'PRV-007', 'PRV-008', 'PRV-009', 'PRV-010', 'PRV-011', 'PRV-012',
  'PRV-101', 'PRV-104', 'PRV-201', 'PRV-301', 'PRV-501',
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
  score: 82,
  coverage: 94,
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
  17,
);
assert.equal(elements.get('diagnostic-priorities').children.length, 1);
assert.equal(elements.get('privacy-correction-offer').hidden, false);
assert.equal(elements.get('correction-order-open').disabled, false);
assert.equal(context.currentDiagnosticIdForTest(), 'DIAG-A');
assert.equal(elements.get('privacy-no-priorities').hidden, true);
assert.match(html, /Plan de corrección/);
assert.match(html, /Obtener plan de corrección/);
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
  17,
);
const transparencyItems = elements.get('diagnostic-controls').children[0].children[1].children;
assert.equal(transparencyItems[1].children[1].children[0].textContent, 'No pudimos revisarlo');
assert.equal(transparencyItems[2].children[1].children[0].textContent, 'No pudimos revisarlo');

assert.doesNotThrow(() => context.renderDiagnosticForTest({ ...baseDiagnostic, priorities: [] }, 'https://example.com'));
assert.equal(elements.get('diagnostic-priorities').children.length, 1);
assert.match(elements.get('diagnostic-priorities').children[0].textContent, /No se identificaron acciones prioritarias/);
assert.equal(elements.get('privacy-correction-offer').hidden, true);
assert.equal(elements.get('privacy-no-priorities').hidden, false);

// A new diagnosis removes every commercial state before its request starts.
elements.get('correction-order-open').trigger('click');
elements.get('correction-order-email').value = 'previous@example.com';
elements.get('correction-order-error').textContent = 'Previous error';
elements.get('correction-order-error').hidden = false;
elements.get('correction-order-success').hidden = false;
context.resetCommercialStateForTest();
assert.equal(context.currentDiagnosticIdForTest(), '');
assert.equal(elements.get('privacy-correction-offer').hidden, true);
assert.equal(elements.get('correction-order-form').hidden, true);
assert.equal(elements.get('correction-order-email').value, '');
assert.equal(elements.get('correction-order-error').hidden, true);
assert.equal(elements.get('correction-order-success').hidden, true);

// The following result can only rebuild an offer for its own diagnostic id.
context.renderDiagnosticForTest({ ...baseDiagnostic, diagnostic_id: 'DIAG-B' }, 'https://site-b.example');
assert.equal(context.currentDiagnosticIdForTest(), 'DIAG-B');
assert.equal(elements.get('privacy-correction-offer').hidden, false);
assert.equal(elements.get('correction-order-open').disabled, false);

// A visual result without an id never reuses A and replaces the priced card
// with a clear, non-technical recovery state.
context.resetCommercialStateForTest();
context.renderDiagnosticForTest({ ...baseDiagnostic, diagnostic_id: undefined }, 'https://site-c.example');
assert.equal(context.currentDiagnosticIdForTest(), '');
assert.equal(elements.get('privacy-correction-offer').hidden, true);
assert.equal(elements.get('privacy-correction-unavailable').hidden, false);
assert.match(html, /Plan de corrección no disponible/);
assert.match(html, /Realizar nuevo diagnóstico/);

let orderRequests = [];
context.fetch = async (url, options) => {
  orderRequests.push({ url, body: JSON.parse(options.body) });
  return { ok: true, status: 201 };
};
elements.get('correction-order-form').trigger('submit');
assert.equal(orderRequests.length, 0);

context.renderDiagnosticForTest({ ...baseDiagnostic, diagnostic_id: 'DIAG-B' }, 'https://site-b.example');
elements.get('correction-order-email').value = 'buyer@example.com';
elements.get('correction-order-form').hidden = false;
elements.get('correction-order-form').trigger('submit');
assert.equal(orderRequests.length, 1);
assert.equal(orderRequests[0].body.diagnostic_id, 'DIAG-B');

for (const score of [26, 100]) {
  assert.doesNotThrow(() => context.renderDiagnosticForTest({ ...baseDiagnostic, score, priorities: [] }, 'https://example.com'));
  assert.match(html, /<section class="privacy-data-next-step"/);
  assert.match(html, /href="\/privacy\/data\/">Conocer Privacy Data<\/a>/);
}
assert.equal(context.isValidDiagnosticResponseForTest({ score: 50, controls: null, priorities: null }), true);
assert.equal(context.isValidDiagnosticResponseForTest({ score: null }), false);
