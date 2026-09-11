# PRV-103 semantic routing v2.1 - final development result

## Scope

This is a consumed-data development benchmark, not an independent QA. It reuses the 104 already-consumed cases from QA6 (46), QA7 (30) and QA8 (28). It does not change production.

Frozen candidate:

- contract: `prv103-semantic-v2.1`;
- taxonomy: `prv103-intents-v2.1`;
- prompt: `prv103-intent-v2-03`;
- model: `gpt-5.6-sol`;
- reasoning: `medium`;
- architecture: Semantic Residual Router;
- deterministic fast paths never emit `concrete`.

## Execution

- GitHub Actions run: `34593077474`;
- branch head: `2f825314fbfd86e19e334d9dd168749606caf7eb`;
- workflow result: `SUCCESS`;
- focused tests: `7 passed`;
- artifact id: `10196534142`;
- artifact digest: `sha256:9341dd2eff7ce9a9cc07b5cf2ff476aa87ea408ad17ac7c5aecf2c30824fec5c`.

## Result

Formal decision: **`stop_semantic_line`**.

| Metric | Run 1 | Run 2 |
|---|---:|---:|
| Accuracy | 98.08% | 98.08% |
| Coverage | 87.50% | 89.42% |
| Emitted precision | 100.00% | 97.85% |
| Concrete precision | 100.00% | 100.00% |
| Concrete recall | 91.30% | 91.30% |
| False concrete promotions | 0 | 0 |
| False adverse `none` | 0 | 0 |
| Invalid outputs | 2 | 0 |
| LLM calls | 34 | 34 |

Class stability between runs: **98.08%**.

LLM call reduction versus sending all 104 cases: **67.31%**.

The router split stayed identical in both runs:

- `trivial_generic`: 58;
- `technical_only`: 3;
- `empty_case`: 9;
- `semantic_llm`: 34.

## Misses

The only two wrong rows in each run are the same semantic form represented in two consumed datasets:

- `QA6_CHILE-012`;
- `QA7-020`.

Visible text:

- heading: `Contrata un plan`;
- introductory text: `Ingresa tus datos y un ejecutivo se contactará contigo muy pronto.`

Reference v2.1: `concrete`.

Run 1 produced invalid structured outputs for both rows, which fail closed to `unknown`. The artifact does not retain a provider error detail, so no more specific cause is asserted.

Run 2 produced valid `subscription_generic` outputs for both rows, therefore `generic` instead of the frozen `concrete` reference.

This concentrates the remaining miss in one duplicated semantic pattern. It does not create a false `concrete` safety error.

## Frozen exit rule

The v2.1 contract was declared the final consumed-data tuning candidate before execution. Its gates require zero invalid outputs in both runs. Run 1 had two invalid outputs, so the candidate formally fails the frozen gate even though all other quality, safety, stability and call-reduction gates pass.

Therefore:

- do not create v2.2;
- do not consume QA9;
- do not create QA10;
- keep production PRV-103 on framework `0.7`;
- keep the semantic architecture as documented research / future roadmap work.

No further tuning is performed inside this benchmark.
