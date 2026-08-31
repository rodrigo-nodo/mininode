# W2.S.2b — direct NLI experiment result

**Date:** 2026-08-31

**GitHub Actions run:** `33438255762` (`SUCCESS`)

**Corpus:** `w2s2a-2026-02` (unchanged)

**Status:** experiment completed; Direct NLI is not selected for integration

## Frozen configuration

- Model: `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli`.
- Model revision: `8adb042d524ecd5c26d3e3ba0e3fbcf7e2d0864c`.
- Architecture: multilingual DeBERTa-v3-base sequence classifier trained for NLI
  with MNLI/XNLI; approximately 278 million parameters.
- License: MIT, as declared by the selected model repository.
- Entailment threshold: `0.65`.
- Class margin: `0.10`.
- Execution: direct scoring of every document fixture against the hypotheses, with
  no embeddings, retrieval, top-k filtering, LLM, fine-tuning, or post-result tuning.

The two executions used the same model revision, corpus, hypotheses, thresholds,
code, and GitHub Actions runner.

## Results

| metric | baseline rules | direct NLI |
|---|---:|---:|
| total cases | 36 | 36 |
| exact matches | 28 | 21 |
| accuracy | 0.7778 | 0.5833 |
| PRV-008 accuracy | 0.6667 | 0.7500 |
| PRV-010 accuracy | 0.7500 | 0.5000 |
| PRV-012 accuracy | 0.9167 | 0.5000 |
| false positive promotions | 1 | 0 |
| false negative omissions | 6 | 15 |
| semantic polarity errors | 0 | 0 |

First Direct NLI execution:

- elapsed seconds: approximately `298.6`;
- average seconds per case: approximately `8.3`;
- total inferences: `312`.

The latency is an experimental GitHub Actions CPU measurement, not a production
service benchmark.

## Stability

Direct NLI ran twice sequentially with the same inputs and resolved model snapshot.
The artifact comparison ignored elapsed-time fields and compared semantic classes,
evidence fixture IDs, and technical scores with only insignificant numeric variation
permitted.

- `stable_predictions: true`
- `prediction_differences: 0`

## Representative cases

Direct NLI provided useful localized signals:

- `commerce_01 / PRV-008`: gold `concrete`; rules `generic`; NLI `concrete`;
- `travel_01 / PRV-008`: gold `concrete`; rules `none`; NLI `concrete`;
- `saas_01 / PRV-010`: NLI correctly recognized `explicit_none`;
- `edusmart / PRV-012`: NLI returned `none`, avoiding an incorrect generic
  interpretation.

It also omitted clear evidence in important cases:

- `emol / PRV-010`: gold `explicit`; NLI `none`;
- `banking_01 / PRV-012`: gold `explicit`; NLI `none`;
- `telecom_01 / PRV-010`: gold `explicit`; NLI `none`.

These examples are observations from the frozen run, not changes to the gold labels.
The dominant weakness was excessive omission: false-negative omissions increased
from 6 to 15. Direct NLI removed the baseline's one false-positive promotion and
introduced no semantic polarity errors, but overall accuracy fell from 0.7778 to
0.5833. PRV-008 improved from 0.6667 to 0.7500, while both PRV-010 and PRV-012 fell
to 0.5000. The isolated PRV-008 gain and individual successes do not compensate for
the loss on recipient and retention evidence or the approximately five-minute CPU
latency.

## Decision

**Classification: C — Direct NLI does not provide sufficient advantage.**

This is not a choice of “rules instead of AI.” Mininode Privacy's current production
architecture remains deterministic rules, while its target/conceptual architecture
remains hybrid. W2.S.2b tested whether this particular direct NLI classifier supplied
enough semantic value to become a layer in that hybrid architecture. It did not.

Direct NLI must not be integrated into production from this result. Production code,
controls, scoring, APIs, dependencies, and the frozen golden set remain unchanged.
A later phase may evaluate a semantic alternative with greater contextual capacity
before any production modification, but its design or implementation is outside this
experiment.
