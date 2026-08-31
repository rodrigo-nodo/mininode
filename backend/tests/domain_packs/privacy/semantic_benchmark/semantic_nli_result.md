# W2.S.2b — direct NLI execution note

**Date:** 2026-08-31

**Corpus:** `w2s2a-2026-02` (unchanged)

**Status:** real inference blocked before model download

## Selected experiment

- Model: `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli`.
- Architecture: multilingual DeBERTa-v3-base sequence classifier trained for NLI
  with MNLI/XNLI; approximately 278 million parameters.
- License: MIT, as declared by the selected model repository.
- Reason: a single base-size, multilingual entailment model with Spanish in XNLI,
  suitable for direct premise/hypothesis scoring on CPU.
- Revision: unavailable in this environment. The Hub metadata request was blocked
  before a commit hash could be resolved; a successful run must record that hash.

No second model, fallback LLM, embeddings, or retrieval path was attempted.

## Frozen baseline

| metric | baseline rules |
|---|---:|
| total cases | 36 |
| exact matches | 28 |
| accuracy | 0.7778 |
| PRV-008 accuracy | 0.6667 |
| PRV-010 accuracy | 0.7500 |
| PRV-012 accuracy | 0.9167 |
| false positive promotions | 1 |
| false negative omissions | 6 |
| semantic polarity errors | 0 |

## Direct NLI result

The temporary Python 3.11 environment successfully installed CPU experiment
dependencies outside the repository. Both the Transformers runner and its unit
tests were prepared, but the first real invocation could not download
`config.json`: the configured HTTPS proxy rejected the tunnel to
`huggingface.co` with **403 Forbidden**. The failure occurred before weights loaded
or any benchmark pair was inferred.

Consequently there are no honest direct-NLI accuracy, per-control accuracy, error,
latency, mismatch, or stability measurements to report. `total_inferences` completed
is 0; the planned runner count is emitted only after a complete run. A second run
would exercise the same missing checkpoint and was not represented as a stability
check. The required conclusion is therefore **todavía no concluyente**: this
environment cannot establish whether direct NLI adds value.

To finish the measurement in an environment allowed to access the selected model,
run the JSON command twice against the same cached checkpoint, record the resolved
Hub commit, compare predictions (excluding timing), and report the first five
mismatches. Do not alter the golden set or thresholds between those executions.
