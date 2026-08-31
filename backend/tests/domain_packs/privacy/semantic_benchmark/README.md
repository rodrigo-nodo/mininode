# W2.S.2a — semantic evidence benchmark

This directory is the offline golden set for the semantic-evidence work proposed in
[`semantic-evidence-w2-s1.md`](../../../../../docs/decisions/privacy/semantic-evidence-w2-s1.md).
It freezes human-expected classes for the evaluation unit `(policy_id, control)` and
runs the **unchanged production rules** as baseline A. Each `policy_id` represents one
frozen synthetic document, and all three controls evaluate that same complete input.

It is not a model, training set, production feature, legal assessment, or scoring
change. It performs no NLI, embeddings, LLM inference, network access, persistence,
or model download. The 12 profiles and 36 cases cover only PRV-008, PRV-010 and
PRV-012.

## W2.S.2b direct NLI experiment

`semantic_nli_runner.py` is a separate, experiment-only direct classifier. It sends
every synthetic document fixture (one fixture is one fragment) to
`MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` with explicit Spanish hypotheses; it does
not use embeddings, retrieval, or top-k filtering. The model is an approximately
278M-parameter multilingual DeBERTa-v3-base NLI checkpoint, distributed under MIT,
and was selected as one CPU-capable base-size model trained with multilingual XNLI
data including Spanish. The model ID identifies the selected repository; record the
resolved Hub commit in any frozen result because the runner intentionally does not
add or pin a product dependency.

The only calibration constants are `ENTAILMENT_THRESHOLD = 0.65` and
`CLASS_MARGIN = 0.10`. The strongest fragment/hypothesis pair for each semantic
class is retained; the leading class must clear both constants or the runner returns
`none`. PRV-003 remains a deterministic gate and returns `not_applicable` without
model inference. Evidence is emitted only from the input document, together with raw
NLI scores and the model ID.

Install CPU-only `torch` and `transformers` in a temporary environment, not in the
product requirements, then run:

```bash
python -m backend.tests.domain_packs.privacy.semantic_benchmark.semantic_nli_runner
python -m backend.tests.domain_packs.privacy.semantic_benchmark.semantic_nli_runner --format json
```

The JSON output contains all 36 predictions, reusable baseline metrics, direct-NLI
metrics, latency, and inference count. Run it twice with the same cached checkpoint
to check basic stability. Unit tests inject a scorer and never import Transformers or
download model weights.

## Data and minimization

`manifest.yaml` holds labels, rationales, dependency state, and gold fixture
references. A case's `evidence` and `hard_negatives` identify the gold annotations for
that control; they are not the complete input. `fixtures.yaml` holds short Spanish
synthetic paraphrases and the single ordered document fixture list for every policy.
The runner builds `PageEvidence` from that full list, so evidence for one control can
act as a realistic distractor for another. The `sip`, `emol`, and
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
`semantic_polarity_errors` separately counts PRV-010 contradictions between an
explicit no-disclosure statement (`explicit_none`) and a positive disclosure
assertion (`generic` or `explicit`). `none` versus `explicit_none` is not automatically
a polarity error because absence of evidence is not the opposite assertion.

## Add a case

1. Add short, original synthetic fragments to `fixtures.yaml`, each with a globally
   unique ID, role, and reason, and reference them from the policy's one document.
2. Add one manifest entry with a unique `(policy_id, control)`, a valid class for that
   control, and references to the fixtures.
3. Keep fixture text below 1,000 characters and never paste HTML or complete policies.
4. Increment `corpus_version` consistently when freezing a revised corpus, then run
   the focused tests and both report formats.

The benchmark adapts fixtures to `EvidenceContract`/`PageEvidence`; production's
adapter and evaluator must not be changed to accommodate benchmark data. SIP-style
cases deliberately model PRV-003 as `not_detected`, so the evaluator—not benchmark
post-processing—produces `not_applicable`.
