"""Stage 0.5 additions on top of the existing Stage 0 cheap-vs-full-model fit:
per-seed repeatability (signal vs. noise), full per-candidate ground truth +
predictions, effect-size distribution, and a Recall@K ranking diagnostic.

Per PTIM_Stage_0_5_Refined_Experiment.md section 16: do not let a single R^2
gap threshold decide the outcome. This module produces the extra diagnostics
needed to make that judgment call for real, without changing the underlying
feature set, models, or CV methodology from baseline.py.
"""
from __future__ import annotations

import random
import statistics
from collections import Counter

import numpy as np

from stage0_falsification.cheap_baseline.baseline import FEATURE_NAMES
from stage0_falsification.intervention_runner.runner import AggregatedRecord, RawRecord


def select_repeatability_candidates(aggregated: list[AggregatedRecord], n: int = 10, seed: int = 42) -> list[str]:
    """Random, not cherry-picked -- per doc section 7 ('Do not select only
    interesting or extreme candidates'). Returns candidate_ids ('family:name')."""
    all_ids = [f"{r.family}:{r.candidate_name}" for r in aggregated]
    rng = random.Random(seed)
    return sorted(rng.sample(all_ids, min(n, len(all_ids))))


def seed_level_losses(raw_records: list[RawRecord], n_seeds: int) -> dict[tuple[str, str], dict]:
    """For each (family, candidate), one loss value per seed (averaged over that
    seed's tasks) -- the 'n_repeats' observations the repeatability check needs.
    This reuses the already-collected per-seed data from the main run; no extra
    backend calls."""
    groups: dict[tuple[str, str], list[RawRecord]] = {}
    for r in raw_records:
        groups.setdefault((r.family, r.candidate_name), []).append(r)

    result = {}
    for key, group in groups.items():
        baseline_losses = []
        treatment_losses = []
        for seed in range(n_seeds):
            seed_group = [r for r in group if r.seed == seed]
            if not seed_group:
                continue
            baseline_losses.append(1 - sum(r.baseline_p_correct for r in seed_group) / len(seed_group))
            treatment_losses.append(1 - sum(r.post_p_correct for r in seed_group) / len(seed_group))
        result[key] = {"baseline_losses": baseline_losses, "treatment_losses": treatment_losses}
    return result


def effect_size_distribution(aggregated: list[AggregatedRecord]) -> dict:
    """delta_loss = -delta_accuracy (positive delta_loss = the addition made things worse)."""
    deltas = np.array([-r.delta_accuracy for r in aggregated])
    return {
        "mean": float(deltas.mean()),
        "median": float(np.median(deltas)),
        "std": float(deltas.std()),
        "min": float(deltas.min()),
        "max": float(deltas.max()),
        "p25": float(np.percentile(deltas, 25)),
        "p75": float(np.percentile(deltas, 75)),
        "count_delta_gt_0": int((deltas > 0).sum()),
        "count_delta_lt_0": int((deltas < 0).sum()),
        "count_delta_eq_0": int((deltas == 0).sum()),
    }


def recall_at_k(aggregated: list[AggregatedRecord], predictions: list[float], k: int = 10) -> float:
    """predictions are delta_accuracy predictions (same sign convention as the
    CV report) -- most-damaging-first ranking uses ascending delta_accuracy
    (most negative = most damaging), which is descending delta_loss."""
    n = len(aggregated)
    k = min(k, n)
    true_order = sorted(range(n), key=lambda i: aggregated[i].delta_accuracy)[:k]
    pred_order = sorted(range(n), key=lambda i: predictions[i])[:k]
    return len(set(true_order) & set(pred_order)) / k


def build_per_candidate_report(
    aggregated: list[AggregatedRecord],
    rows: list,
    cv_report: dict,
    raw_records: list[RawRecord],
    n_seeds: int,
    repeatability_ids: list[str],
) -> list[dict]:
    seed_losses = seed_level_losses(raw_records, n_seeds)
    repeatability_set = set(repeatability_ids)

    entries = []
    for i, (rec, row) in enumerate(zip(aggregated, rows)):
        candidate_id = f"{rec.family}:{rec.candidate_name}"
        baseline_loss = 1 - rec.baseline_accuracy
        treatment_loss = 1 - rec.post_addition_accuracy
        entry = {
            "candidate_id": candidate_id,
            "candidate_family": rec.family,
            "mutation_type": rec.mutation_type,
            "catalog_size": rec.catalog_size,
            "baseline_loss": baseline_loss,
            "treatment_loss": treatment_loss,
            "delta_loss": treatment_loss - baseline_loss,
            "features": {name: float(v) for name, v in zip(FEATURE_NAMES, row.features)},
            "predictions": {
                # cv_report predictions are for delta_accuracy; negate for delta_loss.
                "cheap_linear": -cv_report["cheap_linear"]["predictions"][i],
                "full_linear": -cv_report["full_linear"]["predictions"][i],
                "full_gbr": -cv_report["full_gbr"]["predictions"][i],
            },
        }
        if candidate_id in repeatability_set:
            sl = seed_losses[(rec.family, rec.candidate_name)]
            deltas = [t - b for t, b in zip(sl["treatment_losses"], sl["baseline_losses"])]
            entry["repeatability"] = {
                "n_repeats": len(sl["baseline_losses"]),
                "baseline_losses": sl["baseline_losses"],
                "treatment_losses": sl["treatment_losses"],
                "baseline_mean": statistics.mean(sl["baseline_losses"]),
                "baseline_std": statistics.pstdev(sl["baseline_losses"]),
                "treatment_mean": statistics.mean(sl["treatment_losses"]),
                "treatment_std": statistics.pstdev(sl["treatment_losses"]),
                "delta_mean": statistics.mean(deltas),
                "delta_std": statistics.pstdev(deltas),
            }
        entries.append(entry)
    return entries


def build_stage0_5_aggregate(
    aggregated: list[AggregatedRecord],
    cv_report: dict,
    n_seeds: int,
    repeatability_ids: list[str],
) -> dict:
    family_counts = dict(Counter(r.family for r in aggregated))
    return {
        **cv_report,
        "n_candidates": len(aggregated),
        "n_seeds": n_seeds,
        "family_distribution": family_counts,
        "effect_size_distribution": effect_size_distribution(aggregated),
        "recall_at_10": {
            "cheap_linear": recall_at_k(aggregated, cv_report["cheap_linear"]["predictions"], k=10),
            "full_linear": recall_at_k(aggregated, cv_report["full_linear"]["predictions"], k=10),
            "full_gbr": recall_at_k(aggregated, cv_report["full_gbr"]["predictions"], k=10),
        },
        "repeatability_candidate_ids": repeatability_ids,
        "repeatability_selection_method": "random.Random(seed=42).sample() over all candidate_ids, "
                                           f"n={len(repeatability_ids)}",
    }
