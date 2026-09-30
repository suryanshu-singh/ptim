# PTIM Stage 0.5 — Refined Validation Run

## Purpose

This is a controlled refinement of Stage 0, not a new experiment.

The goal is to determine whether the weak predictive signal observed in the first 30-candidate run is:
1. genuine but underpowered,
2. dominated by stochastic measurement noise,
3. poorly captured by the current features, or
4. effectively absent.

Do **not** introduce a sophisticated structural model yet.

## 1. Experimental Setup

| Component | Previous | Stage 0.5 |
|---|---:|---:|
| Base tools | 36 | **36** |
| Tool families | 6 | **6** |
| Candidate additions | 30 | **~50** |
| Seeds | 3 | **5** |
| Models | Same | **Same** |
| Tasks | Same | **Same** |
| Feature definitions | Same | **Same** |
| Train/test methodology | Same | **Same** |
| Cheap linear baseline | Yes | **Yes** |
| Full linear model | Yes | **Yes** |
| Gradient boosting | Yes | **Yes** |

**Critical rule:** do not change the feature set, model architecture, data-generation process, or evaluation methodology merely to improve the result. This run tests whether the original Stage-0 observation survives a larger sample and more seeds.

## 2. Candidate Count

Increase:

`30 → approximately 50`

Keep the existing 36-tool / 6-family base catalog.

If the generator naturally produces 48–52 candidates, that is acceptable.

## 3. Seeds

Increase:

`3 → 5`

Use five independent seeds and record the seed for every run.

## 4. Preserve the Existing Baselines

Run exactly the same:
- cheap linear model;
- full linear model;
- gradient boosting model.

Do not add GNNs, hypergraphs, transformers, or other sophisticated interaction models yet.

## 5. Required Per-Candidate Data

For **every candidate**, return:

```json
{
  "candidate_id": "...",
  "candidate_family": "...",
  "baseline_loss": 0.0,
  "treatment_loss": 0.0,
  "delta_loss": 0.0,
  "cheap_features": {},
  "full_features": {},
  "predictions": {
    "cheap_linear": 0.0,
    "full_linear": 0.0,
    "full_gbr": 0.0
  }
}
```

Use the actual feature names from the existing Stage-0 implementation.

The crucial ground truth is:

`delta_loss = treatment_loss - baseline_loss`

using the same loss definition as Stage 0.

## 6. Required Aggregate Results

Return the same aggregate metrics:
- MAE;
- RMSE if already available;
- R²;
- Spearman correlation;
- sign accuracy;
- predictions.

Also report:
- number of candidates;
- number of seeds;
- train/test sizes;
- candidate-family distribution if available.

## 7. New Requirement: Repeatability / Noise Subset

Select approximately **10 candidates at random**.

For these candidates, run **five independent baseline runs** and **five independent treatment runs**.

Do not select only interesting or extreme candidates. Record the selection method and candidate IDs.

### Baseline

```text
C, seed 1
C, seed 2
C, seed 3
C, seed 4
C, seed 5
```

### Treatment

```text
C + candidate, seed 1
C + candidate, seed 2
C + candidate, seed 3
C + candidate, seed 4
C + candidate, seed 5
```

## 8. Repeatability JSON

For each repeatability candidate:

```json
{
  "candidate_id": "...",
  "repeatability": {
    "n_repeats": 5,
    "baseline_losses": [0, 0, 0, 0, 0],
    "treatment_losses": [0, 0, 0, 0, 0],
    "baseline_mean": 0,
    "baseline_std": 0,
    "treatment_mean": 0,
    "treatment_std": 0,
    "delta_mean": 0,
    "delta_std": 0
  }
}
```

Preserve the individual observations; do not return only averages.

## 9. Why Repeatability Matters

The first run had only 30 examples and produced weak predictive performance. We cannot yet distinguish:
- genuinely absent signal;
- weak signal with insufficient sample size;
- high stochastic noise;
- inadequate features.

Estimate:
- baseline variability;
- treatment variability;
- delta variability.

Compare the intervention magnitude `|delta|` with normal run-to-run variation.

If `|delta|` is generally much smaller than noise, exact prediction may be intrinsically difficult.

If `|delta|` is substantially larger than noise, there is a stable signal worth modeling.

Do not make a definitive statistical claim from the 10-candidate subset alone.

## 10. Keep the Target Unchanged

Continue predicting exactly the same target used in Stage 0.

Do **not** switch the primary target to:
- selection entropy;
- JS divergence;
- probability redistribution;
- risk ranking.

Those can be investigated later.

If selection distributions are already available, preserve them as raw data for later analysis, but do not change the Stage-0 target.

## 11. Train/Test Discipline

Prevent leakage.

Preserve the existing Stage-0 train/test methodology.

Report:
- train candidate count;
- test candidate count;
- stable candidate identifiers;
- family distribution.

Where possible, evaluate on candidate tools never seen during training.

## 12. Effect-Size Distribution

Return statistics for observed `delta_loss`:
- mean;
- median;
- standard deviation;
- minimum;
- maximum;
- 25th percentile;
- 75th percentile;
- count with delta < 0;
- count with delta > 0.

This tells us whether there is enough variation for a predictor to learn.

## 13. Optional Diagnostic: Risk Ranking

If predictions are available, calculate whether the candidates predicted to have the largest negative effects are actually among the largest negative effects.

Report `Recall@K` (for example Recall@10 when appropriate).

This is diagnostic only and does not replace the primary regression task.

## 14. Do Not Overinterpret R²

R² may be unstable at small sample sizes.

Interpret it alongside:
- MAE;
- Spearman;
- sign accuracy;
- ranking performance;
- effect-size distribution;
- repeatability/noise;
- per-candidate predictions.

A negative R² alone does not prove that interference is unpredictable.

## 15. Decision Rules

### Kill the predictive hypothesis if

After the larger run:
- cheap baseline remains competitive;
- richer features provide no reproducible improvement;
- Spearman remains near zero;
- risk ranking is no better than trivial baselines;
- intervention effects are mostly within the noise floor.

### Continue investigation if

- cheap semantic features remain weak;
- richer features show consistent improvement;
- intervention effects exceed measurement noise;
- ranking candidates is meaningfully better than random;
- catalog context appears to change the effect.

### Strong signal if

- unseen candidates can be predicted;
- richer features substantially outperform cheap baselines;
- results hold across seeds;
- risk ranking is useful;
- effect sizes exceed measurement noise;
- results generalize across tool families.

Only then investigate structural interaction models.

## 16. Do Not Automatically Pivot to a Benchmark Paper

Do not use an arbitrary rule such as:

`full R² <= cheap R² → benchmark paper`

as the scientific decision.

Inspect:
- signal;
- noise;
- generalization;
- ranking;
- effect-size distribution.

Then decide whether to continue, pivot, or kill the hypothesis.

## 17. Required Final Output

Return **two JSON objects/files**.

### A. Aggregate JSON

Keep the previous structure, including:
- n_examples;
- cheap_linear;
- full_linear;
- full_gbr;
- metrics;
- predictions;
- verdict.

Add:
- n_candidates;
- n_seeds.

### B. Per-candidate JSON

For every candidate:
- candidate_id;
- candidate_family;
- baseline_loss;
- treatment_loss;
- delta_loss;
- features;
- predictions.

Also include repeatability records for the approximately 10 selected candidates.

Do not summarize away the raw values.

## 18. What We Will Analyze Afterwards

The next analysis will determine:
1. Is the intervention effect real relative to noise?
2. Is it predictable?
3. Does semantic similarity explain it?
4. Do schema/catalog features add information?
5. Does prediction generalize to unseen candidates?
6. Is ranking easier than exact regression?
7. Does surrounding catalog context condition the effect?
8. Should PTIM continue, pivot, or be killed?

## 19. Core Principle

The purpose of Stage 0.5 is **not to make PTIM succeed**.

The purpose is:

> Find out whether there is a stable, measurable, generalizable signal worth building a predictive system around.

If the answer is no, kill the idea.

If the answer is yes, then—and only then—invest in the structural model.

## 20. One-Line Instruction for the Experiment Runner

> Repeat the original Stage-0 experiment with 36 base tools, 6 families, approximately 50 candidate additions, and 5 seeds, preserving all existing methodology, while additionally returning complete per-candidate ground truth/predictions and a 10-candidate × 5-repeat baseline/treatment repeatability subset so that signal can be separated from stochastic noise.
