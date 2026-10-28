import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

// Execute the actual public-priority renderer with a minimal DOM, independently
// of unrelated commercial/auth flows on the diagnosis page.
const app = readFileSync(new URL('./app.js', import.meta.url), 'utf8');
const catalog = readFileSync(new URL('./control-ux.js', import.meta.url), 'utf8');
const startMarker = 'const renderPriorities = (priorities) => {';
const endMarker = '\nconst resetCommercialState = () => {';
const start = app.indexOf(startMarker);
const end = app.indexOf(endMarker, start);
assert.ok(start >= 0 && end > start, 'actual renderPriorities function exists');

class Node {
  constructor() { this.children = []; this.textContent = ''; this.className = ''; }
  append(child) { this.children.push(child); }
  replaceChildren() { this.children = []; }
}

const context = {
  window: {},
  diagnosticPriorities: new Node(),
  actionsTitle: new Node(),
  appendTextElement(parent, tag, value, className) {
    const node = new Node();
    node.tagName = tag;
    node.textContent = value;
    node.className = className || '';
    parent.append(node);
    return node;
  },
};
vm.runInNewContext(catalog, context);
vm.runInNewContext(app.slice(start, end) + '\nglobalThis.renderPrioritiesForTest = renderPriorities;', context);

test('PRV-003 title comes from shared UX catalog; instructions remain unchanged', () => {
  context.renderPrioritiesForTest([{
    control_code: 'PRV-003',
    name: 'Política propia del responsable',
    priority: 'Alta',
    recommendation: 'Recomendación original',
    action_steps: ['Paso original'],
    validation_step: 'Validación original',
  }]);
  const cards = context.diagnosticPriorities.children;
  assert.equal(cards.length, 1);
  assert.equal(context.actionsTitle.textContent, '1 cosa que haría primero');
  const content = cards[0].children[1];
  assert.equal(content.children[0].textContent, 'Política de privacidad claramente asociada a la empresa');
  assert.equal(content.children[1].textContent, 'Recomendación original');
  const steps = content.children[2].children[1];
  assert.equal(steps.children[1].children[0].textContent, 'Paso original');
  assert.equal(steps.children[2].children[1].textContent, 'Validación original');
});

test('historical and missing control codes retain safe, meaningful fallback labels', () => {
  context.renderPrioritiesForTest([
    { control_code: 'PRV-HIST', name: 'Nombre histórico', finding: 'Hallazgo original' },
    { name: 'Acción sin código' },
    { control_code: 'PRV-FUTURE' },
  ]);
  const cards = context.diagnosticPriorities.children;
  assert.equal(cards.length, 3);
  assert.equal(cards[0].children[1].children[0].textContent, 'Nombre histórico');
  assert.equal(cards[0].children[1].children[1].textContent, 'Hallazgo original');
  assert.equal(cards[1].children[1].children[0].textContent, 'Acción sin código');
  assert.equal(cards[2].children[1].children[0].textContent, 'Acción prioritaria');
});
