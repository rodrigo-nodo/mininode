# W2.S.3 — LLM semantic adjudicator result

**Status: pending real API execution**

- Model: `gpt-5.6-sol`
- Prompt version: `w2s3-01`
- Reasoning effort: `medium`
- Corpus: `w2s2a-2026-02` (frozen)
- Primary quality run: run 1; run 2 is used only for stability.
- Routing: frozen before inference in `semantic_llm_runner.py`.
- Cost reference: USD 4.00 / million input tokens and USD 20.00 / million
  output tokens, snapshot dated 2026-08-31. This experimental estimate is
  separate from quality metrics and pricing may change.

Real execution requires the `OPENAI_API_KEY` GitHub Actions secret. No result,
mismatch analysis, correction/degradation list, or final classification is claimed
until both API runs and the generated artifacts have been reviewed. At that point
this document must record rules, LLM-only and hybrid metrics; stability; token use;
estimated cost; latency; representative mismatches; hybrid corrections and
degradations; and exactly one final classification (A–E). No tuning may occur after
run 1, and the temporary workflow must be removed before merge.
