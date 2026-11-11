const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const window = {};
vm.runInNewContext(fs.readFileSync(__dirname + '/score-presentation.js', 'utf8'), { window });
const presentation = window.MininodePrivacyScorePresentation;
assert.ok(presentation);
const codes = [...Object.keys(presentation.SCORING_WEIGHTS), ...presentation.CONTEXT_CODES];
const scoring = Object.keys(presentation.SCORING_WEIGHTS);
const full = () => Object.fromEntries(codes.map((code) => [code, 'detected']));

function fixture(overrides = {}, extras = {}) {
  const states = { ...full(), ...overrides };
  const controls = codes.map((control_code) => ({ control_code, result: states[control_code] }));
  const weighted = scoring.filter((code) => states[code] !== 'not_applicable');
  const evaluated = weighted.filter((code) => states[code] !== 'not_evaluable');
  const weightSum = evaluated.reduce((sum, code) => sum + presentation.SCORING_WEIGHTS[code], 0);
  const earned = evaluated.reduce((sum, code) => sum +
    presentation.SCORING_WEIGHTS[code] * ({ detected: 1, partial: 0.5, not_detected: 0 }[states[code]]), 0);
  return {
    framework_version: '0.13', scoring_version: '0.3', controls,
    score: weightSum ? Math.round(100 * earned / weightSum) : 0,
    evaluated_controls: evaluated.length, applicable_controls: weighted.length,
    coverage: weighted.length ? Math.round(100 * evaluated.length / weighted.length) : 100,
    scope: { pages_requested: 3, pages_analyzed: 3, limited: false },
    ...extras,
  };
}
const assess = (overrides, extras) => presentation.assess(fixture(overrides, extras));
const check = (overrides, expected, extras) => {
  const result = assess(overrides, extras);
  assert.equal(result.state, expected);
  return result;
};

assert.equal(check({}, 'complete').label, 'Preparación destacada');
assert.equal(check({ 'PRV-101': 'not_detected', 'PRV-102': 'not_applicable' }, 'complete').applicable, 14);
assert.equal(check({ 'PRV-014': 'not_applicable' }, 'complete').applicable, 14);
assert.equal(check({ 'PRV-101': 'not_detected', 'PRV-102': 'not_applicable',
  'PRV-014': 'not_applicable' }, 'complete').applicable, 13);
assert.equal(check({ 'PRV-004': 'not_evaluable', 'PRV-103': 'not_evaluable' }, 'complete').evaluated, 15);

const policyDependents = ['PRV-005', 'PRV-006', 'PRV-007', 'PRV-008', 'PRV-010',
  'PRV-011', 'PRV-012', 'PRV-013', 'PRV-014'];
const absent = Object.fromEntries(policyDependents.map((code) => [code, 'not_applicable']));
const policyAbsent = check({ ...absent, 'PRV-003': 'not_detected',
  'PRV-101': 'not_detected', 'PRV-102': 'not_applicable' }, 'complete');
assert.equal(policyAbsent.score, 73);
assert.equal(policyAbsent.label, 'Hay aspectos importantes por corregir');
assert.ok(policyAbsent.critical.includes('PRV-003'));

const allBad = Object.fromEntries(scoring.map((code) => [code, 'not_detected']));
const allBadApplicable = { ...allBad, 'PRV-002': 'not_applicable', ...absent,
  'PRV-102': 'not_applicable' };
assert.equal(check(allBadApplicable, 'complete').score, 0);

assert.equal(check({ 'PRV-301': 'not_evaluable' }, 'partial').missingWeight, 1);
assert.equal(check({ 'PRV-005': 'not_evaluable', 'PRV-007': 'not_evaluable',
  'PRV-010': 'not_evaluable' }, 'partial').missingWeight, 9);
assert.equal(check({ 'PRV-006': 'not_evaluable', 'PRV-005': 'not_evaluable',
  'PRV-007': 'not_evaluable' }, 'limited').missingWeight, 10);
assert.equal(check({ 'PRV-006': 'not_evaluable', 'PRV-008': 'not_evaluable' }, 'partial').missingWeight, 8);
assert.equal(check({ 'PRV-001': 'not_evaluable', 'PRV-002': 'not_evaluable' }, 'limited').essentialMissing, true);
const missingPolicy = Object.fromEntries(policyDependents.map((code) => [code, 'not_evaluable']));
assert.equal(check({ ...missingPolicy, 'PRV-003': 'not_evaluable' }, 'limited').essentialMissing, true);
assert.equal(check(Object.fromEntries(scoring.map((code) => [code, 'not_evaluable'])), 'limited').evaluated, 0);
assert.equal(check({}, 'complete', { scope: { pages_requested: 5, pages_analyzed: 4, limited: true } }).state, 'complete');
assert.equal(check({ 'PRV-006': 'not_evaluable', 'PRV-007': 'not_evaluable',
  'PRV-010': 'not_evaluable' }, 'limited', { scope: { limited: true } }).state, 'limited');

const sensitive = check({ 'PRV-005': 'not_evaluable', 'PRV-007': 'not_evaluable',
  'PRV-010': 'not_evaluable' }, 'partial');
assert.equal(sensitive.sensitive, true); // Unseen controls could cross the new 85-point boundary.
const stable = check({ 'PRV-301': 'not_evaluable',
  'PRV-005': 'not_detected', 'PRV-007': 'not_detected',
  'PRV-010': 'not_detected' }, 'partial');
assert.equal(stable.sensitive, false);

const criticalPartial = check({ 'PRV-501': 'not_detected', 'PRV-301': 'not_evaluable' }, 'partial');
assert.ok(criticalPartial.critical.includes('PRV-501'));
const partialNotFailed = check({ 'PRV-501': 'partial' }, 'complete');
assert.equal(partialNotFailed.critical.length, 0);
assert.equal(partialNotFailed.label, 'Preparación destacada');

for (const [score, expected] of [
  [0, 'Preparación inicial'], [39, 'Preparación inicial'],
  [40, 'Preparación en desarrollo'], [69, 'Preparación en desarrollo'],
  [70, 'Preparación avanzada'], [84, 'Preparación avanzada'],
  [85, 'Preparación destacada'], [100, 'Preparación destacada'],
]) {
  assert.equal(presentation.labelForScore(score), expected);
}
const previous = fixture();
assert.equal(presentation.assess({ ...previous, framework_version: '0.11' }).state, 'unverified');
assert.equal(presentation.assess({ ...previous, framework_version: '0.11' }).label, 'Cobertura no verificable');
assert.equal(presentation.assess({ ...previous, controls: null }).state, 'unverified');
assert.equal(presentation.assess({ ...previous, applicable_controls: 14 }).state, 'unverified');
assert.equal(presentation.assess({ ...previous, coverage: 40 }).state, 'unverified');
assert.equal(presentation.assess({ ...previous,
  controls: [...previous.controls, previous.controls[0]] }).state, 'unverified');
assert.equal(presentation.assess({ ...previous, scoring_version: '0.2' }).state, 'unverified');
assert.equal(presentation.assess({ ...previous, controls: [] }).state, 'unverified');
assert.equal(presentation.assess({ ...previous, score: 98, controls: null }).score, 98);

const none = fixture(Object.fromEntries(scoring.map((code) => [code, 'not_applicable'])));
assert.equal(presentation.assess(none).state, 'limited');
assert.equal(presentation.assess(none).applicable, 0);
console.log('PW-QA-01 presentation rules: PASS');
