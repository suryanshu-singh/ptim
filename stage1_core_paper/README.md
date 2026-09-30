# Stage 1 — Core Paper (gated)

**Gate not met as of 2026-08-27.** Stage 0.5's real-backend run found the gate criterion
false: a cheap semantic-similarity feature explains nearly all the measurable degradation
signal (concentrated almost entirely in `near_duplicate` additions), and richer structural
features don't beat it. Full findings: [docs/PTIM_Stage_0_5_Findings.md](../docs/PTIM_Stage_0_5_Findings.md).
Do not start this stage on the current data — see that doc's "What would change this
recommendation" section for the specific narrower condition that would revive it.

If and when that gate is met, this stage scales to the full grid (~50 tools ×
~20 task families × ~5 models × ~100 candidate additions × ~10 seeds, per
design-doc section 38) and builds the structural interaction predictor:

- `predictor/` — the feature-based regressor (`ĝ(t, x) + Σh(t, x_i, x_j) + r(C,x)` per
  design-doc section 14), trained on the Stage 0-style counterfactual dataset at scale.
- `interaction_models/` — pairwise + higher-order interaction terms (design-doc
  sections 12-13): graph/hypergraph neural net or factorization-machine style models.
- `uncertainty/` — calibrated prediction intervals (design-doc section 15.6).
- `evaluation/` — zero-shot generalization tests: unseen tool families, unseen
  providers, unseen catalogs, unseen models (design-doc section 18-20), plus the
  ranking (`Recall@K`) and distribution-shift (`JS(P̂, P)`) experiments from
  sections 21-22.

Position explicitly against: datamodels (Ilyas et al., ICML 2022) — "we transfer
the datamodel idea from training data to tool catalogs"; LLMCert-T — "prediction
without execution vs. their sampling-based certification"; HYSET — "degradation-
of-addition target vs. their set-retrieval target." Report the cheap baseline
from Stage 0 as a first-class competitor throughout, not a strawman.

Empty until the gate is met.
