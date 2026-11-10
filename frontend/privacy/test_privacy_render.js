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
const catalogSource = fs.readFileSync(`${__dirname}/control-ux.js`, 'utf8');
const presentationSource = fs.readFileSync(`${__dirname}/score-presentation.js`, 'utf8');
const context = {
  window: { location: { search: '' }, addEventListener() {} },
  document,
  URL,
  URLSearchParams,
  FormData: class {},
  fetch: async () => { throw new Error('not used'); },
};
vm.runInNewContext(catalogSource, context);
vm.runInNewContext(presentationSource, context);
vm.runInNewContext(`${source}
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
const controls = codes.map((control_code) => ({
  control_code,
  result: ['PRV-004', 'PRV-301', 'PRV-102', 'PRV-012'].includes(control_code)
    ? 'not_evaluable' : ['PRV-009', 'PRV-014'].includes(control_code)
      ? 'not_applicable' : ['PRV-008', 'PRV-011'].includes(control_code)
        ? 'partial' : control_code === 'PRV-005' ? 'not_detected' : 'detected',
  confidence: 'high',
  evidence: [],
  reason: 'Resultado determinístico del control.',
}));
const baseDiagnostic = {
  framework_version: '0.13',
  scoring_version: '0.3',
  diagnostic_id: 'DIAG-A',
  claim_token: 'test-pending-claim',
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
const policyControl = elements.get('diagnostic-controls').children[0].children[1].children[2];
assert.equal(policyControl.children[0].children[0].textContent,
  'Política de privacidad claramente asociada a la empresa');
assert.match(policyControl.children[0].children[1].textContent, /empresa o entidad responsable/);

assert.equal(
  elements.get('diagnostic-controls').children.reduce((total, area) => total + area.children[1].children.length, 0),
  21,
);
assert.equal(elements.get('diagnostic-priorities').children.length, 1);
assert.equal(elements.get('privacy-correction-offer').hidden, false);
assert.equal(elements.get('correction-order-open').disabled, false);
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

assert.doesNotThrow(() => context.renderDiagnosticForTest({ ...baseDiagnostic, priorities: [] }, 'https://example.com'));
assert.equal(elements.get('diagnostic-priorities').children.length, 1);
assert.match(elements.get('diagnostic-priorities').children[0].textContent, /No se identificaron acciones prioritarias/);
assert.equal(elements.get('privacy-correction-offer').hidden, true);
assert.equal(elements.get('privacy-no-priorities').hidden, false);

// Complete coverage uses the approved four-tier scale and explains applicability.
const fullCoverageControls = controls.map((control) =>
  ['PRV-301', 'PRV-102', 'PRV-012'].includes(control.control_code)
    ? { ...control, result: 'detected' } : control);
context.renderDiagnosticForTest({ ...baseDiagnostic, score: 84,
  controls: fullCoverageControls, coverage: 100,
  evaluated_controls: 14, applicable_controls: 14 }, 'https://example.com');
assert.equal(elements.get('score-value').textContent, '84');
assert.equal(elements.get('score-status').textContent, 'Preparación avanzada');
assert.match(elements.get('diagnostic-coverage').textContent, /14 de 14/);
assert.equal(elements.get('diagnostic-score-alert').hidden, true);

// Zero evaluated controls are not presented as a negative 0/100.
const noEvaluableControls = controls.map((control) => ({
  ...control,
  result: control.control_code === 'PRV-014' ? 'not_applicable' : 'not_evaluable',
}));
context.renderDiagnosticForTest({ ...baseDiagnostic, score: 0, coverage: 0,
  controls: noEvaluableControls, evaluated_controls: 0, applicable_controls: 14 }, 'https://example.com');
assert.equal(elements.get('score-value').textContent, '—');
assert.equal(elements.get('score-status').textContent, 'Evaluación limitada');
assert.match(elements.get('diagnostic-coverage').textContent, /no significa que el sitio incumpla/i);

// Historical snapshots with missing metadata remain readable.
const { coverage: _coverage, evaluated_controls: _evaluated, applicable_controls: _applicable,
  ...historical } = baseDiagnostic;
context.renderDiagnosticForTest(historical, 'https://example.com');
assert.equal(elements.get('score-value').textContent, 82);
assert.match(elements.get('diagnostic-coverage').textContent, /No contamos con información suficiente/);

// Some checks were evaluated, while others within the same area could not be.
const partialAreaControls = controls.map((item) => item.control_code === 'PRV-005'
  ? { ...item, result: 'not_evaluable' } : item);
context.renderDiagnosticForTest({ ...baseDiagnostic, controls: partialAreaControls }, 'https://example.com');
assert.equal(elements.get('diagnostic-areas').children[0].children[1].textContent, 'Evaluación parcial');

// Context controls are neutral; the DEV catalog still displays descriptions.
const cookieHistory = controls.map((item) => item.control_code === 'PRV-201'
  ? { ...item, result: 'not_applicable' } : item);
context.renderDiagnosticForTest({ ...baseDiagnostic, controls: cookieHistory }, 'https://example.com');
assert.equal(elements.get('diagnostic-areas').children[2].children[1].textContent, 'Informativo');
assert.equal(elements.get('diagnostic-controls').children[2].children[1].children[0]
  .children[1].children[0].textContent, 'No detectado');
assert.match(elements.get('diagnostic-controls').children[1].children[1].children[2]
  .children[0].children[1].textContent, /formulario/i);

// PW-QA-01: validated limited coverage never presents the backend 100 as a pass.
const limitedControls = fullCoverageControls.map((control) =>
  ['PRV-006', 'PRV-005', 'PRV-007'].includes(control.control_code)
    ? { ...control, result: 'not_evaluable' } : control);
context.renderDiagnosticForTest({
  ...baseDiagnostic, score: 100, controls: limitedControls,
  applicable_controls: 14, evaluated_controls: 11, coverage: 79,
}, 'https://example.com');
assert.equal(elements.get('score-value').textContent, '—');
assert.equal(elements.get('score-status').textContent, 'Evaluación limitada');
assert.doesNotMatch(elements.get('privacy-score')['aria-label'], /100 de 100/);
assert.match(elements.get('diagnostic-coverage').textContent, /11 de 14/);

// A confirmed missing own privacy policy must not be masked by a high score.
const policyDependencies = new Set([
  'PRV-004', 'PRV-005', 'PRV-006', 'PRV-007', 'PRV-008', 'PRV-009',
  'PRV-010', 'PRV-011', 'PRV-012', 'PRV-013', 'PRV-014',
]);
const absentPolicyControls = codes.map((control_code) => ({
  control_code, result: policyDependencies.has(control_code) || control_code === 'PRV-102'
    ? 'not_applicable' : control_code === 'PRV-003'
      ? 'not_detected' : control_code === 'PRV-101'
        ? 'not_detected' : 'detected',
}));
context.renderDiagnosticForTest({
  ...baseDiagnostic, score: 73, controls: absentPolicyControls,
  applicable_controls: 5, evaluated_controls: 5, coverage: 100,
}, 'https://example.com');
assert.equal(elements.get('score-value').textContent, '73');
assert.equal(elements.get('score-status').textContent, 'Hay aspectos importantes por corregir');
assert.match(elements.get('diagnostic-score-alert').textContent, /privacidad/i);
assert.equal(elements.get('diagnostic-score-alert').hidden, false);
assert.match(elements.get('diagnostic-coverage').textContent, /5 de 5/);

// Partial very-high findings stay visible through recommendations, without a global override.
const partialCriticalControls = fullCoverageControls.map((control) =>
  control.control_code === 'PRV-501' ? { ...control, result: 'partial' } : control);
context.renderDiagnosticForTest({
  ...baseDiagnostic, score: 80, controls: partialCriticalControls,
  applicable_controls: 14, evaluated_controls: 14, coverage: 100,
}, 'https://example.com');
assert.equal(elements.get('score-status').textContent, 'Preparación avanzada');
assert.equal(elements.get('diagnostic-score-alert').hidden, true);

// Tracing limitation must not be confused with evidence insufficiency.
context.renderDiagnosticForTest({
  ...baseDiagnostic, score: 84, controls: fullCoverageControls, coverage: 100,
  applicable_controls: 14, evaluated_controls: 14,
  scope: { pages_analyzed: 5, limited: true },
}, 'https://example.com');
assert.match(elements.get('diagnostic-scope').textContent, /Alcance del rastreo limitado/);
assert.equal(elements.get('score-status').textContent, 'Preparación avanzada');

// Counts inconsistent with the stored controls fall back to a conservative historical view.
context.renderDiagnosticForTest({
  ...baseDiagnostic, controls: fullCoverageControls, coverage: 100,
  applicable_controls: 15, evaluated_controls: 15,
}, 'https://example.com');
assert.equal(elements.get('score-status').textContent, 'Diagnóstico anterior');

// DEV: saved reviews can still be opened, and old purchase timestamps
// do not suppress their stored diagnosis or suggest a completed checkout.
context.renderDiagnosticForTest({
  ...baseDiagnostic,
  diagnostic_id: 'DIAG-EXPIRED',
  workspace_site_id: 'SITE-A',
  purchase_expires_at: '2026-10-01T21:57:00Z',
}, 'https://expired.example');
assert.equal(elements.get('correction-order-open').hidden, false);
assert.equal(elements.get('correction-order-open').disabled, false);
assert.equal(elements.get('privacy-saved-note').hidden, false);
assert.equal(elements.get('privacy-save-note').hidden, true);
assert.equal(context.currentDiagnosticIdForTest(), 'DIAG-EXPIRED');

// Starting a new review clears prior commercial state without making orders.
context.resetCommercialStateForTest();
assert.equal(context.currentDiagnosticIdForTest(), '');
assert.equal(elements.get('privacy-correction-offer').hidden, true);
assert.equal(elements.get('privacy-activation-notice').hidden, true);

// A fresh result restores only its own diagnostic id.
context.renderDiagnosticForTest({ ...baseDiagnostic, diagnostic_id: 'DIAG-B' }, 'https://site-b.example');
assert.equal(context.currentDiagnosticIdForTest(), 'DIAG-B');
assert.equal(elements.get('privacy-correction-offer').hidden, false);
assert.equal(elements.get('correction-order-open').disabled, false);

// No id: the offer is not available and the result cannot reuse old state.
context.resetCommercialStateForTest();
context.renderDiagnosticForTest({ ...baseDiagnostic, diagnostic_id: undefined }, 'https://site-c.example');
assert.equal(context.currentDiagnosticIdForTest(), '');
assert.equal(elements.get('privacy-correction-offer').hidden, true);
assert.equal(elements.get('privacy-correction-unavailable').hidden, false);
assert.match(html, /Privacy Web no disponible/);

for (const score of [26, 100]) {
  assert.doesNotThrow(() => context.renderDiagnosticForTest({
    ...baseDiagnostic, score, priorities: [], coverage: 100,
    evaluated_controls: 14, applicable_controls: 14,
  }, 'https://example.com'));
  assert.match(html, /<section class="privacy-data-next-step"/);
  assert.match(html, /href="\/privacy\/data\/">Conocer Privacy Data<\/a>/);
}
assert.equal(context.isValidDiagnosticResponseForTest({ score: 50, controls: null, priorities: null }), true);
assert.equal(context.isValidDiagnosticResponseForTest({ score: null }), false);
