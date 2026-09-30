# PTIM Stage 0 / 0.5 — Findings Report

**Status:** Stage 0.5 complete (2026-08-27). **Decision: pivot away from the structural-interaction-model framing; do not proceed to Stage 1 as originally scoped.** See "Recommendation" below.

This document summarizes what was actually run, what broke and got fixed along the way, and what the real data says. Raw data backing every number here: `stage0_falsification/datasets/per_candidate_anthropic.json`, `stage0_falsification/results/stage0_report_anthropic.json`.

---

## 1. What was run

Two real-backend experiments against `claude-haiku-4-5` (Anthropic Batch API, thinking disabled):

| | Run 1 (Stage 0) | Run 2 (Stage 0.5) |
|---|---|---|
| Tool families | 6 | 8 (added `email`, `project_management`) |
| Candidates | 30 (5/family) | 64 (8/family) |
| Seeds | 3 | 5 |
| Real API calls | 2,700 | 9,000 |
| Errored requests | 150 (5.6%) | **0** |
| Actual cost | $2.0874 | ≈$7.14 |

Total real spend across both runs: **≈$9.23**.

## 2. Two real bugs found and fixed between runs

**Bug 1 — malformed tool names.** `mutation_engine.py`'s synonym table mapped `"search"` → `"look up"` (two words); the near-duplicate name-builder spliced this into a tool *name* unsanitized, producing literal spaces (`'look up_flights'`, `'look up_case_law'`). The Anthropic API rejects such names outright. This explained **exactly** 150/2700 errors in Run 1 (2 broken candidates × 75 calls each). Fixed by stripping spaces at the point of name construction.

**Bug 2 — every schema field marked required.** This was the bigger one. Run 1's calendar family had 2.7% baseline tool-selection accuracy. Inspecting the actual response text (not just the parsed tool_use/none distribution) showed the model wasn't confused — it was **correctly declining to call the tool and asking clarifying questions** ("what's today's date?", "what's the location?"), because every `input_schema` field, including genuinely optional ones (location, phone, notes...), was marked `required` in the generated JSON schema. Fixed with an explicit `Tool.required_fields` attribute, set per-tool for the ~30 canonical tools that are task targets, plus rewriting all task queries to ground the fields that stay genuinely required (concrete dates/IDs instead of "tomorrow" / implied IDs).

Effect of the fix: 6 of 8 families now show **100% baseline accuracy** (0% loss) across all seeds in Run 2, vs. a noisy, often-near-zero baseline in Run 1.

## 3. The headline finding: damage is concentrated almost entirely in near-duplicate additions

Of the 64 candidates in Run 2, only **11 showed any measured effect at all** — the other 53 produced *exactly* zero change in tool-selection accuracy across all 125 baseline/treatment samples each. Of those 11, **8 were `near_duplicate` mutations**, and they account for almost all of the damage:

| Candidate | Mutation type | Accuracy change |
|---|---|---|
| calendar:schedule_event | near_duplicate | −20.0 pp |
| finance:show_transactions | near_duplicate | −20.0 pp |
| calendar:show_events | near_duplicate | −18.4 pp |
| developer_tools:execute_tests | near_duplicate | −17.6 pp |
| legal:compose_clause | near_duplicate | −15.2 pp |
| legal:lookup_case_law | near_duplicate | −2.4 pp |
| travel:lookup_flights | near_duplicate | −1.6 pp |
| travel:lookup_hotels | near_duplicate | −0.8 pp |
| calendar:book_conference_room | schema_confusable | −0.8 pp |
| calendar:sync_calendar_provider | mixed_realistic | +0.8 pp |
| calendar:archive_old_events | description_confusable | +3.2 pp |

(Negative = accuracy dropped after adding the candidate. Values are `delta_loss` from `per_candidate_anthropic.json`, sign-flipped.)

**Random, schema_confusable, description_confusable, and mixed_realistic additions produced essentially zero degradation** in this grid. A semantically near-identical competitor tool is the only mutation type that reliably causes real, sometimes severe (up to 20pp) selection damage. This is mechanistically coherent — it's exactly what "the model can't tell two near-identical tools apart" would predict — and is a much cleaner, more interpretable signal than either real run before it.

## 4. Predictive model results

| Metric | Cheap (2-feature) | Full linear (5-feature) | Full GBR |
|---|---|---|---|
| R² | 0.084 | 0.006 | 0.059 |
| Spearman | 0.374 | 0.343 | 0.395 |
| MAE | 0.0285 | 0.0281 | 0.0174 |
| Recall@10 | 0.40 | 0.40 | **0.60** |
| Sign accuracy* | 12.5% | 14.1% | 14.1% |

*\*Sign accuracy is a misleading number here, not a real failure signal — see caveat below.*

- **R² is positive for the first time** across all three real-backend attempts (both prior runs were negative). There is real, learnable signal.
- **The cheap 2-feature model (max semantic similarity + catalog size) is competitive with, and by raw R² slightly ahead of, the full 5-feature model.** This is the exact outcome the prior-art assessment flagged as the main threat to novelty: near-duplicates are semantically near-identical to their base tool *by construction*, so `semantic_max_sim` catches almost all the signal on its own. The added schema/lexical-overlap features in the "full" model don't meaningfully improve on it (R² gap = −0.025, favoring cheap).
- **Recall@10 (0.4-0.6) is meaningfully above the ~0.16 chance baseline** (10/64 candidates) — the models can rank likely-damaging candidates better than random, with gradient boosting doing best.
- **Sign-accuracy caveat**: 53 of 64 true deltas are *exactly* zero. A continuous-valued prediction can essentially never land exactly on 0.0, so those 53 cases are guaranteed "misses" regardless of model quality. Read correctly, sign accuracy here means "correctly signed most of the 11 cases that actually had a nonzero effect," not "wrong 87% of the time." A future version of this analysis should score sign accuracy only on nonzero-true-delta candidates, or use a three-way (better/worse/no-change) classification instead of continuous-vs-sign.

## 5. Decision, per the Stage 0.5 decision rules

Per `docs/PTIM_Stage_0_5_Refined_Experiment.md` section 15 (explicitly: do not use a single R² threshold as the decision):

- **Cheap baseline remains competitive** — met (cheap R² ≥ full R²).
- **Richer features provide no reproducible improvement** — met (gap is small and negative).
- **Spearman is *not* near zero** — not met for "kill" (0.34-0.40 is real correlation); this is the one criterion pointing toward "continue."
- **Risk ranking is *not* no-better-than-random** — not met for "kill" (Recall@10 well above chance); another point toward "continue."
- **Intervention effects mostly within the noise floor** — partially met: 53/64 candidates are genuinely, deterministically zero-effect (not noise-masked — the repeatability subset shows std=0 for most of these, meaning the model's behavior is fully consistent across seeds). The real effects that exist (the 9 near-duplicate cases) are large relative to that near-zero noise floor.

This doesn't cleanly match either the doc's "kill" or "continue" bucket — it's closer to a **third outcome the doc didn't explicitly name**: there is real, mechanistically-clear signal, but it is fully explained by the mutation-type/semantic-similarity feature the cheap baseline already has, concentrated in one narrow category (near-duplicates) rather than spread broadly across catalog structure. This is exactly the pattern the prior-art assessment predicted as the likely fate of this research direction, now confirmed with real data instead of speculation.

## 6. Recommendation

**Do not proceed to Stage 1 as scoped** (the structural interaction model / GNN / hypergraph approach) — the data doesn't support that the extra machinery would earn its cost, since a single cheap similarity feature already captures nearly all the predictable variance.

**Do** consider this a legitimate, decisive Stage 0 outcome worth keeping, in either of two forms:

1. **Benchmark/measurement framing** (the prior-art doc's own fallback recommendation): publish the dataset and this finding — "single-tool-addition degradation in a safe-zone catalog is rare and concentrated almost entirely in near-duplicate redundancy; a cheap embedding-similarity check catches nearly all of it." Honest, useful, modest.
2. **Screening/triage framing**: the Recall@10 result (especially GBR's 0.6) suggests a cheap near-duplicate detector could work as a lightweight pre-deployment gate for tool registries ("flag candidates with high similarity to an existing tool for manual review") — decision-useful even without a sophisticated model, and doesn't require Stage 1's investment.

Either framing is a smaller, cheaper deliverable than the original PTIM structural-model ambition, but both are backed by real, reproducible, mechanistically-sensible data — which is a better foundation than a paper built on an untested hypothesis.

## 7. What would change this recommendation

Per the falsification spirit of this whole project: if a future run at larger scale (more families, more near-duplicate variety, testing whether near-duplicate damage is genuinely unpredictable from schema features alone or whether some near-duplicates are more damaging than others in a way structural features *do* explain) showed the full model pulling ahead of the cheap one specifically *within* the near-duplicate subset, that would revive the case for structural modeling — narrowed to "predicting near-duplicate severity," not the original broad claim.
