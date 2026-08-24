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
  }

  append(child) { this.children.push(child); }
  replaceChildren() { this.children = []; }
  setAttribute(name, value) { this[name] = String(value); }
  addEventListener() {}
  querySelector() { return null; }
  querySelectorAll() { return []; }
  scrollIntoView() {}
  focus() {}
}

const html = fs.readFileSync(`${__dirname}/index.html`, 'utf8');
const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map((match) => match[1]);
const elements = new Map(ids.map((id) => [id, new Element()]));
const document = {
  body: new Element('body'),
  activeElement: null,
  createElement: (tagName) => new Element(tagName),
  querySelector: (selector) => selector.startsWith('#') ? elements.get(selector.slice(1)) ?? null : null,
  addEventListener() {},
};

const source = fs.readFileSync(`${__dirname}/app.js`, 'utf8');
const context = {
  document,
  URL,
  FormData: class {},
  fetch: async () => { throw new Error('not used'); },
};
vm.runInNewContext(`${source}\nglobalThis.renderDiagnosticForTest = renderDiagnostic; globalThis.isValidDiagnosticResponseForTest = isValidDiagnosticResponse;`, context);

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
assert.match(html, /Ver qué revisamos/);
assert.equal(elements.get('diagnostic-controls').children.length, 5);
assert.equal(
  elements.get('diagnostic-controls').children.reduce((total, area) => total + area.children[1].children.length, 0),
  17,
);
assert.equal(elements.get('diagnostic-priorities').children.length, 1);
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
assert.equal(context.isValidDiagnosticResponseForTest({ score: 50, controls: null, priorities: null }), true);
assert.equal(context.isValidDiagnosticResponseForTest({ score: null }), false);
