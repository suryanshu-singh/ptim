# Stage 0 / 0.5 — Falsification

Goal: before building any structural tool-interference model, check whether a
**cheap** baseline — max embedding-similarity between a candidate tool and the
existing catalog, plus catalog size — already predicts most of the observed
degradation delta when that candidate is added. This is the single highest-priority
experiment per the prior-art assessment ([docs/PTIM_Prior_Art_and_Novelty_Assessment.md](../docs/PTIM_Prior_Art_and_Novelty_Assessment.md)).

The first real-backend run (30 candidates, 3 seeds) came back inconclusive — R² was
negative and unstable for both the cheap and full models, and 2 of 30 data points
turned out to be corrupted by a tool-naming bug (fixed). Per
[docs/PTIM_Stage_0_5_Refined_Experiment.md](../docs/PTIM_Stage_0_5_Refined_Experiment.md),
Stage 0.5 scales candidates and seeds and adds a repeatability check to tell whether
that inconclusive result was genuine-but-underpowered signal, pure noise, or absent —
**without** changing the feature set, models, or CV methodology (that would confound
"is there signal" with "did we just change the measurement").

## Pipeline

```
catalog_generator/   8 tool families (calendar, crm, finance, email = train; travel, legal,
                      developer_tools, project_management = held-out test), 6 canonical tools +
                      5 tasks each. Train/test split (design-doc section 18) prevents
                      near-duplicate leakage; email + project_management were added on top of
                      the original 6 specifically to grow the leave-one-family-out CV fold count
                      (see "Scale notes" below -- more folds is the real lever for the R²
                      instability seen in the first run, not more candidates).
                      Task queries are grounded (concrete dates/IDs) and each tool declares
                      which fields are actually required -- both fixed after the first real
                      run showed the model correctly declining ambiguous calls and asking
                      clarifying questions instead of guessing.

mutation_engine/     8 candidate additions per family (64 total, Stage 0.5), spanning all five
                      mutation types from design-doc section 17: random, near_duplicate,
                      schema_confusable, description_confusable, mixed_realistic.

intervention_runner/ For each (family, candidate, task, seed): measure P(correct_tool) with the
                      baseline catalog and with catalog+candidate, via a pluggable backend
                      (mock or anthropic). Produces the counterfactual dataset from design-doc
                      section 9 (baseline_accuracy, post_addition_accuracy, delta_accuracy).

cheap_baseline/      baseline.py fits the unchanged 2-feature "cheap" model and 5-feature "full"
                      model (leave-one-family-out CV, same as Stage 0). stage0_5_report.py adds:
                      per-candidate ground truth + predictions, effect-size distribution, a
                      10-candidate repeatability subset (per-seed loss values, not just the
                      mean, so |delta| can be compared against run-to-run noise), and Recall@10.
```

## Run it

```bash
# Free, instant, pipeline smoke test only (see warning below):
python run_stage0.py --backend mock

# Real Stage 0.5 run (requires ANTHROPIC_API_KEY):
python run_stage0.py --backend anthropic
```

Outputs land in `datasets/` (raw + aggregated + **per-candidate** intervention records,
the latter including repeatability data for the selected subset) and `results/`
(the aggregate report: cheap-vs-full model comparison, effect-size distribution,
Recall@10, repeatability summary).

### Cost controls (on by default for `--backend anthropic`)

- **Batch mode** (`intervention_runner/batch_runner.py`) is the default execution path
  for the anthropic backend: it submits every request for the whole grid as one Message
  Batch (50% off standard token pricing) instead of firing requests one at a time. Pass
  `--no-batch` to fall back to the synchronous per-call path (e.g. for debugging).
- **Baseline de-duplication**: a candidate's baseline distribution depends only on
  (family, task, seed), not on the candidate itself. Both the batch and synchronous
  paths compute it once per (family, task, seed) and reuse it across all candidates
  in that family, instead of re-sampling an identical baseline once per candidate.
- **Thinking disabled by default** (`--enable-thinking` to opt back in): current-generation
  Claude models run adaptive thinking by default, which bills reasoning as output tokens
  even though the summary display is omitted. These are short synthetic classification
  queries with no expected benefit from extended reasoning, so thinking is off unless
  requested. `--effort {low,medium,high,xhigh,max}` is also available if you re-enable it.
- **Default model is `claude-haiku-4-5`** ($1/$5 per MTok) rather than a Sonnet/Opus-tier
  model -- plenty capable for this classification-shaped task, and matches the prior-art
  doc's own Stage 0 recommendation to use small/cheap models first. Override with `--model`.

**Real measured cost** (from the completed first run: 2,700 calls, $2.0874 actual spend
→ **$0.000773/call**, not an estimate). Stage 0.5 defaults (`--n-seeds 5`, 8 families,
8 candidates/family):

```
baseline: 8 families × 5 tasks × 5 seeds × 5 samples                      = 1,000
post:     8 families × 8 candidates/family × 5 tasks × 5 seeds × 5 samples = 8,000
total: 9,000 calls → ≈ $6.90-7.20
```

Batches typically complete within an hour (max 24h); the script polls `--poll-interval`
seconds (default 30) until done, so a full run is one blocking command.

### If the process gets interrupted mid-run

The moment the batch is submitted, its id is printed and saved to
`results/last_batch.json` -- before polling even starts. If the process dies
while waiting (session timeout, closed terminal, etc.), the batch itself keeps
running on Anthropic's side regardless (results stay retrievable for 29 days).
**Do not just re-run the same command** -- that submits a second batch and pays
twice. Instead, resume the same one:

```bash
python run_stage0.py --backend anthropic --resume-batch-id <id from last_batch.json>
```

This only polls and parses the existing batch's results -- it never resubmits.

## ⚠️ The mock backend does not test the hypothesis

`MockBackend` simulates tool selection as a softmax over the *same* TF-IDF
cosine-similarity signal the cheap baseline uses as a feature. Running Stage 0
against it will always show the cheap baseline winning — that only proves the
data flows correctly through catalog generation → mutation → intervention →
feature extraction → evaluation → report. It is not evidence for or against
the PTIM hypothesis. The real test requires a real model backend (`anthropic`,
or another one added to `intervention_runner/backends.py`) so the observed
deltas come from actual model behavior, independent of the features being
evaluated against it.

## Decision criterion — read this before trusting a single number

Per [docs/PTIM_Stage_0_5_Refined_Experiment.md](../docs/PTIM_Stage_0_5_Refined_Experiment.md)
section 15-16: **do not** use a single mechanical rule like "full R² beats cheap R² by
> 0.05 → proceed" as the actual decision. `run_stage0.py` still computes and prints that
rule's verdict (labeled explicitly as mechanical, not final), but the real call should
weigh it alongside:

- the **effect-size distribution** (is `|delta_loss|` even large enough to be worth predicting?),
- the **repeatability subset** (is `|delta_loss|` bigger than run-to-run noise, per candidate?),
- **Recall@10** (can the models rank the most-damaging candidates better than chance?),
- **Spearman / sign accuracy**, not just R² (R² is unstable at this sample size).

Kill/continue/strong-signal criteria are spelled out in the doc's section 15.

## Scale notes

Stage 0.5's grid (48 tools / 8 families / 64 candidates / 5 seeds) is still below the
prior-art doc's full recommendation (~50 tools / ~5-20 task families / ~50-100 candidates),
but the family count was deliberately bumped from 6 to 8 (adding `email` and
`project_management`) specifically to grow leave-one-family-out CV from 6 to 8 folds --
scaling candidates/seeds alone narrows noise *within* each fold but doesn't add independent
folds, which was the diagnosed cause of the first run's unstable R². 8 folds is still a
small number by ML-CV standards; if R² is still unstable after this run, more families
remains the next lever, not a bigger version of this same grid.
