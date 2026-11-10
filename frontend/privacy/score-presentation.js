// PW-QA-01: frontend presentation only. Backend scoring 0.3 is authoritative.
// Keep this static table in sync with backend controls.json + scoring.json (CI verifies it).
(() => {
  const FRAMEWORK_VERSION = '0.13';
  const SCORING_VERSION = '0.3';
  const SCORING_WEIGHTS = Object.freeze({
    'PRV-001': 4, 'PRV-002': 2, 'PRV-003': 4, 'PRV-005': 3,
    'PRV-006': 4, 'PRV-007': 3, 'PRV-008': 4, 'PRV-010': 3,
    'PRV-011': 4, 'PRV-012': 2, 'PRV-013': 3, 'PRV-014': 3,
    'PRV-102': 2, 'PRV-301': 1, 'PRV-501': 4,
  });
  const CONTEXT_CODES = Object.freeze([
    'PRV-004', 'PRV-009', 'PRV-101', 'PRV-103', 'PRV-104', 'PRV-201',
  ]);
  const RESULTS = new Set(['detected', 'partial', 'not_detected', 'not_evaluable', 'not_applicable']);
  const FACTORS = Object.freeze({ detected: 1, partial: 0.5, not_detected: 0 });
  const RANGES = Object.freeze([
    { min: 0, max: 39, label: 'Preparación inicial' },
    { min: 40, max: 69, label: 'Preparación en desarrollo' },
    { min: 70, max: 84, label: 'Preparación avanzada' },
    { min: 85, max: 100, label: 'Preparación destacada' },
  ]);

  const labelForScore = (score) =>
    RANGES.find((range) => score >= range.min && score <= range.max)?.label || 'Resultado no verificable';

  const unverified = (score) => ({
    state: 'unverified', score, label: 'Diagnóstico anterior', evaluated: null,
    applicable: null, sensitive: false, critical: [],
  });

  const assess = (diagnostic) => {
    const score = diagnostic?.score;
    if (!Number.isInteger(score) || score < 0 || score > 100 ||
        diagnostic.framework_version !== FRAMEWORK_VERSION ||
        diagnostic.scoring_version !== SCORING_VERSION ||
        !Array.isArray(diagnostic.controls)) {
      return unverified(score);
    }
    const byCode = new Map();
    for (const control of diagnostic.controls) {
      if (!control || typeof control.control_code !== 'string' ||
          !RESULTS.has(control.result) || byCode.has(control.control_code)) {
        return unverified(score);
      }
      byCode.set(control.control_code, control.result);
    }
    const allCodes = [...Object.keys(SCORING_WEIGHTS), ...CONTEXT_CODES];
    if (byCode.size !== allCodes.length || allCodes.some((code) => !byCode.has(code))) {
      return unverified(score);
    }

    let applicable = 0;
    let evaluated = 0;
    let totalWeight = 0;
    let missingWeight = 0;
    let earnedWeight = 0;
    const critical = [];
    for (const [code, weight] of Object.entries(SCORING_WEIGHTS)) {
      const result = byCode.get(code);
      if (result === 'not_applicable') continue;
      applicable += 1;
      totalWeight += weight;
      if (result === 'not_evaluable') {
        missingWeight += weight;
      } else {
        evaluated += 1;
        earnedWeight += weight * FACTORS[result];
        if (weight === 4 && result === 'not_detected') critical.push(code);
      }
    }
    const reportedEvaluated = diagnostic.evaluated_controls;
    const reportedApplicable = diagnostic.applicable_controls;
    const reportedCoverage = diagnostic.coverage;
    const coverage = applicable > 0 ? Math.round(100 * evaluated / applicable) : 100;
    if (!Number.isInteger(reportedEvaluated) || !Number.isInteger(reportedApplicable) ||
        reportedEvaluated !== evaluated || reportedApplicable !== applicable ||
        !Number.isInteger(reportedCoverage) || Math.abs(reportedCoverage - coverage) > 1) {
      return unverified(score);
    }

    if (applicable === 0 || evaluated === 0) {
      return { state: 'limited', score, evaluated, applicable, sensitive: false,
        critical, essentialMissing: false };
    }
    const essentialMissing = ['PRV-001', 'PRV-003']
      .some((code) => byCode.get(code) === 'not_evaluable');
    const state = evaluated === applicable ? 'complete'
      : (essentialMissing || 5 * missingWeight > totalWeight ? 'limited' : 'partial');
    const minimum = 100 * earnedWeight / totalWeight;
    const maximum = 100 * (earnedWeight + missingWeight) / totalWeight;
    const sensitive = state === 'partial' && [40, 70, 85]
      .some((cutoff) => minimum < cutoff && cutoff <= maximum);
    return {
      state, score, evaluated, applicable, totalWeight, missingWeight,
      sensitive, essentialMissing, critical,
      label: state === 'complete' ? (critical.length
        ? 'Hay aspectos importantes por corregir' : labelForScore(score))
        : state === 'partial' ? 'Evaluación parcial' : 'Evaluación limitada',
    };
  };

  window.MininodePrivacyScorePresentation = Object.freeze({
    assess, labelForScore, SCORING_WEIGHTS, CONTEXT_CODES, RANGES,
  });
})();
