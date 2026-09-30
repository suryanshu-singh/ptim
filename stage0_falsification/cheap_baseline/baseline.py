"""The Stage 0 decision experiment.

Tests whether a cheap 2-feature baseline (max semantic similarity to the
existing catalog + catalog size) predicts the observed degradation delta
about as well as a richer model with lexical- and schema-overlap features.
This is the falsification test from design-doc section 38 and the
prior-art doc's "Stage 0 — Falsify first" recommendation.

Decision rule (from the prior-art assessment):
  - If the full model's cross-validated R^2 is within ~0.05 of the cheap
    model's R^2, the cheap baseline already explains the predictable
    variance -> do not proceed to Stage 1 as a structural-model paper.
  - If the full model clearly, reproducibly beats the cheap model,
    proceed to Stage 1.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import spearmanr
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import LeaveOneGroupOut

from stage0_falsification.common import Catalog, Tool
from stage0_falsification.cheap_baseline.embeddings import fit_vectorizer, max_mean_similarity


def _token_jaccard(a: str, b: str) -> float:
    sa, sb = set(a.lower().split()), set(b.lower().split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _schema_jaccard(a: dict[str, str], b: dict[str, str]) -> float:
    sa, sb = set(a.keys()), set(b.keys())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


FEATURE_NAMES = [
    "semantic_max_sim", "semantic_mean_sim",
    "lexical_jaccard_max", "schema_jaccard_max",
    "catalog_size",
]
CHEAP_FEATURE_IDX = [0, 4]  # semantic_max_sim, catalog_size


@dataclass
class FeatureRow:
    family: str
    candidate_name: str
    mutation_type: str
    features: np.ndarray
    target: float  # observed delta_accuracy


def build_features(
    aggregated_records: list,
    candidates_by_family: dict[str, list[Tool]],
    baseline_catalogs: dict[str, Catalog],
) -> list[FeatureRow]:
    all_tools = [t for tools in candidates_by_family.values() for t in tools]
    for catalog in baseline_catalogs.values():
        all_tools.extend(catalog.tools)
    vec = fit_vectorizer(all_tools)

    candidate_lookup = {
        (family, t.name): t for family, tools in candidates_by_family.items() for t in tools
    }

    rows = []
    for rec in aggregated_records:
        catalog = baseline_catalogs[rec.family]
        candidate = candidate_lookup[(rec.family, rec.candidate_name)]

        sem_max, sem_mean = max_mean_similarity(vec, candidate, catalog.tools)
        lex_max = max(_token_jaccard(candidate.description, t.description) for t in catalog.tools)
        schema_max = max(_schema_jaccard(candidate.input_schema, t.input_schema) for t in catalog.tools)

        features = np.array([sem_max, sem_mean, lex_max, schema_max, float(rec.catalog_size)])
        rows.append(FeatureRow(
            family=rec.family, candidate_name=rec.candidate_name, mutation_type=rec.mutation_type,
            features=features, target=rec.delta_accuracy,
        ))
    return rows


def _cv_scores(X: np.ndarray, y: np.ndarray, groups: np.ndarray, model_fn) -> dict:
    logo = LeaveOneGroupOut()
    preds = np.zeros_like(y)
    for train_idx, test_idx in logo.split(X, y, groups):
        if len(train_idx) < 2:
            preds[test_idx] = y[train_idx].mean() if len(train_idx) else 0.0
            continue
        model = model_fn()
        model.fit(X[train_idx], y[train_idx])
        preds[test_idx] = model.predict(X[test_idx])

    mae = float(np.mean(np.abs(preds - y)))
    ss_res = float(np.sum((y - preds) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2)) + 1e-9
    r2 = 1 - ss_res / ss_tot
    spearman = spearmanr(preds, y).correlation if len(set(y)) > 1 else float("nan")
    sign_acc = float(np.mean(np.sign(preds) == np.sign(y)))
    return {"mae": mae, "r2": r2, "spearman": spearman, "sign_accuracy": sign_acc, "predictions": preds.tolist()}


def evaluate(rows: list[FeatureRow]) -> dict:
    X = np.stack([r.features for r in rows])
    y = np.array([r.target for r in rows])
    families = np.array([r.family for r in rows])

    X_cheap = X[:, CHEAP_FEATURE_IDX]

    results = {
        "n_examples": len(rows),
        "cheap_linear": _cv_scores(X_cheap, y, families, LinearRegression),
        "full_linear": _cv_scores(X, y, families, LinearRegression),
        "full_gbr": _cv_scores(X, y, families, lambda: GradientBoostingRegressor(
            n_estimators=50, max_depth=2, learning_rate=0.1)),
    }

    cheap_r2 = results["cheap_linear"]["r2"]
    full_r2 = max(results["full_linear"]["r2"], results["full_gbr"]["r2"])
    gap = full_r2 - cheap_r2

    if gap > 0.05:
        verdict = "PROCEED_TO_STAGE1"
        verdict_reason = (
            f"Full-feature model beats the cheap baseline by R^2 gap {gap:.3f} (> 0.05 threshold). "
            "Structural features (schema/lexical overlap) explain variance the cheap baseline misses."
        )
    else:
        verdict = "DO_NOT_PROCEED_AS_STRUCTURAL_MODEL"
        verdict_reason = (
            f"Full-feature model does not clearly beat the cheap baseline (R^2 gap {gap:.3f} <= 0.05). "
            "Per the falsification criterion, pivot to the benchmark/measurement framing instead "
            "of a structural-interaction-model paper."
        )

    results["cheap_r2"] = cheap_r2
    results["full_r2"] = full_r2
    results["r2_gap"] = gap
    results["verdict"] = verdict
    results["verdict_reason"] = verdict_reason
    return results
