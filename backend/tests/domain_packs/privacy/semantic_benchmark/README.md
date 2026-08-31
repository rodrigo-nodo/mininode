# W2.S.2a — semantic evidence benchmark

This directory is the offline golden set for the semantic-evidence work proposed in
[`semantic-evidence-w2-s1.md`](../../../../../docs/decisions/privacy/semantic-evidence-w2-s1.md).
It freezes human-expected classes for the evaluation unit `(policy_id, control)` and
runs the **unchanged production rules** as baseline A.

It is not a model, training set, production feature, legal assessment, or scoring
change. It performs no NLI, embeddings, LLM inference, network access, persistence,
or model download. The 12 profiles and 36 cases cover only PRV-008, PRV-010 and
PRV-012.

## Data and minimization

`manifest.yaml` holds labels, rationales, dependency state, and fixture references.
`fixtures.yaml` holds short Spanish synthetic paraphrases. The `sip`, `emol`, and
`edusmart` profiles reproduce calibration phenomena without preserving real policies;
all other profiles are fictional sector-diverse equivalents. There is no HTML or full
policy text. A golden label is the reviewed expected semantic class, not the current
rules' output.

## Run

From the repository root (with backend requirements installed):

```bash
python -m backend.tests.domain_packs.privacy.semantic_benchmark.runner
python -m backend.tests.domain_packs.privacy.semantic_benchmark.runner --format json
pytest -q backend/tests/domain_packs/privacy/semantic_benchmark/test_semantic_benchmark.py
```

The report includes exact accuracy, per-control accuracy, confusion counts, macro
precision/recall, omissions, and false-positive promotions. Promotion uses these
strict orders: `none < generic < concrete` for PRV-008 and
`none < generic < explicit` for PRV-010/012. `explicit_none` and `not_applicable` are
incomparable and are never counted as ordinal promotions or omissions.

## Add a case

1. Add short, original synthetic fragments to `fixtures.yaml`, each with a globally
   unique ID, role, and reason.
2. Add one manifest entry with a unique `(policy_id, control)`, a valid class for that
   control, and references to the fixtures.
3. Keep fixture text below 1,000 characters and never paste HTML or complete policies.
4. Increment `corpus_version` consistently when freezing a revised corpus, then run
   the focused tests and both report formats.

The benchmark adapts fixtures to `EvidenceContract`/`PageEvidence`; production's
adapter and evaluator must not be changed to accommodate benchmark data. SIP-style
cases deliberately model PRV-003 as `not_detected`, so the evaluator—not benchmark
post-processing—produces `not_applicable`.
