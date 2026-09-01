# W2.S.3 — LLM semantic adjudicator result

**Status: completed — no production integration**

## Frozen execution

- GitHub Actions run: `33461629873` (`success`)
- Artifact: `privacy-semantic-llm-w2s3` (artifact ID `9783407539`)
- Corpus: `w2s2a-2026-02` (36 cases; frozen)
- Model: `gpt-5.6-sol`
- Prompt version: `w2s3-01`
- Reasoning effort: `medium`
- Primary quality result: run 1
- Stability-only result: run 2; it was not considered as an alternative quality run
- Routing: frozen before inference in `semantic_llm_runner.py`
- Cost reference: USD 4.00 / million input tokens and USD 20.00 / million
  output tokens, snapshot dated 2026-08-31; prices may change.

No prompt, routing, model, reasoning effort, class, corpus, or golden label was
changed after run 1. W2.S.3 must not be rerun to seek a better result.

## Quality results — official run 1

| Metric | Rules | LLM only | Hybrid selective |
| --- | ---: | ---: | ---: |
| Total cases | 36 | 36 | 36 |
| Exact matches | 28 | 31 | 31 |
| Accuracy | 0.7778 | 0.8611 | 0.8611 |
| False-positive promotions | 1 | 3 | 3 |
| False-negative omissions | 6 | 2 | 2 |
| Semantic polarity errors | 0 | 0 | 0 |
| Invalid outputs | 0 | 0 | 0 |

Hybrid selective improved accuracy by `0.0833`, approximately 8.3 percentage
points over rules. This does not reach the approximate experimental target of 10
percentage points, and false-positive promotions increased from 1 to 3.

### Accuracy per control

| Control | Rules | LLM only | Hybrid selective |
| --- | ---: | ---: | ---: |
| PRV-008 | 0.6667 | 0.7500 | 0.7500 |
| PRV-010 | 0.7500 | 1.0000 | 1.0000 |
| PRV-012 | 0.9167 | 0.8333 | 0.8333 |

PRV-010 is the strongest positive signal (`0.75` to `1.00`), and overall
omissions fell from 6 to 2. Conversely, PRV-012 degraded from `0.9167` to
`0.8333`.

## Hybrid corrections and regressions

Rules incorrect → hybrid correct:

| Policy / control | Gold | Rules | Hybrid |
| --- | --- | --- | --- |
| `emol` / PRV-010 | `explicit` | `generic` | `explicit` |
| `commerce_01` / PRV-008 | `concrete` | `generic` | `concrete` |
| `saas_01` / PRV-010 | `explicit_none` | `none` | `explicit_none` |
| `travel_01` / PRV-008 | `concrete` | `none` | `concrete` |
| `services_01` / PRV-010 | `explicit` | `generic` | `explicit` |

Rules correct → hybrid incorrect:

| Policy / control | Gold | Rules | Hybrid |
| --- | --- | --- | --- |
| `media_01` / PRV-008 | `none` | `none` | `generic` |
| `media_01` / PRV-012 | `generic` | `generic` | `none` |

## False-positive promotions

Hybrid run 1 promoted these cases beyond the observed gold class:

| Policy / control | Gold | Hybrid |
| --- | --- | --- |
| `edusmart` / PRV-012 | `none` | `generic` |
| `telecom_01` / PRV-008 | `generic` | `concrete` |
| `media_01` / PRV-008 | `none` | `generic` |

This is especially important because Mininode Privacy should behave
conservatively rather than declare evidence stronger than what was observed.

## Evidence observation

Evidence provenance worked technically: the returned fixture IDs existed in the
input documents and no invented IDs were accepted. However, valid evidence could
belong semantically to a neighboring concept:

- `telecom_01` / PRV-008 predicted `concrete` using
  `telecom_01-prv-010-e01`; disclosure to authorities was interpreted as a
  processing purpose.
- `edusmart` / PRV-012 predicted `generic` using
  `edusmart-prv-008-e01`; purpose evidence was used for retention.

Thus traceability alone does not prevent cross-control semantic contamination.
This observation is documented for future research and is not corrected or tuned
in this PR.

## Stability — run 1 versus run 2

- Total cases: 36
- Stable classes: 34 (94.4%)
- Class differences: 2
- Evidence differences: 2
- Uncertain differences: 0

| Policy / control | Run 1 | Run 2 |
| --- | --- | --- |
| `edusmart` / PRV-012 | `generic` | `none` |
| `media_01` / PRV-012 | `none` | `generic` |

Run 2 is used only for stability. Its predictions were not selected over run 1.

## Operational usage, latency, and cost

| Metric | Actual LLM run 1 | Projected hybrid selective run 1 |
| --- | ---: | ---: |
| LLM calls | 33 | 22 |
| Routing | all applicable | 22 / 36 (61.1%) |
| Input tokens | 10,116 | 6,688 |
| Output tokens | 2,388 | 1,744 |
| Reasoning tokens | 488 | 488 |
| Total latency | ~74.08 s | ~48.17 s |
| Average latency/call | ~2.24 s | ~2.19 s |
| Estimated cost | USD 0.088224 | USD 0.061632 |

The hybrid value is a **projected** cost for an architecture that would call the
LLM only for routed cases. It was not additional spend: hybrid classes reused run
1 inferences. The estimated actual total for both stability runs was USD 0.171448.
Cost remains separate from quality and is not production logic.

## Conclusion and decision

The result is substantially stronger than the Direct NLI experiment and shows
that an LLM can contribute useful semantic capacity within the conceptual hybrid
architecture. In particular, PRV-010 reached perfect accuracy and omissions were
materially reduced.

Nevertheless, the evaluated variant improved accuracy by only 8.3 percentage
points, increased false-positive promotions from 1 to 3, degraded PRV-012, showed
two class differences between runs, and exhibited cross-control semantic
contamination.

**Final classification: D — risky due to false promotions.**

D does not discard future LLM research. It means this variant is not sufficiently
conservative for Privacy Web and is not ready for integration. Future research may
be especially valuable per control, notably PRV-010, but must be validated using
data not used to adjust the solution.

The conceptual architecture remains hybrid. The current production architecture
remains deterministic rules. W2.S.3 adds no production LLM runtime or production
dependency and makes no production change.
