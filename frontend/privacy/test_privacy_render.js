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
vm.runInNewContext(`${source}\nglobalThis.renderDiagnosticForTest = renderDiagnostic;`, context);

const codes = [
  'PRV-001', 'PRV-002', 'PRV-003', 'PRV-004', 'PRV-005', 'PRV-006',
  'PRV-007', 'PRV-008', 'PRV-009', 'PRV-010', 'PRV-011', 'PRV-012',
  'PRV-101', 'PRV-104', 'PRV-201', 'PRV-301', 'PRV-501',
];
const controls = codes.map((control_code, index) => ({
  control_code,
  result: index === 3 ? 'not_evaluable' : index === 8 ? 'not_applicable' : 'detected',
}));
const baseDiagnostic = {
  score: 82,
  coverage: 94,
  status: 'Preparación avanzada',
  controls,
  priorities: [{ name: 'Actualizar la política', recommendation: 'Publica una versión vigente.' }],
  scope: { pages_requested: 5, pages_analyzed: 4, limited: false },
};

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

assert.doesNotThrow(() => context.renderDiagnosticForTest({ ...baseDiagnostic, priorities: [] }, 'https://example.com'));
assert.equal(elements.get('diagnostic-priorities').children.length, 1);
assert.match(elements.get('diagnostic-priorities').children[0].textContent, /No se identificaron acciones prioritarias/);
