"""Orchestrates baseline-vs-post-addition intervention runs.

For each (family, candidate, task, seed): measure P(correct_tool) under the
baseline catalog and under catalog+candidate, using the given backend. This
produces the counterfactual training data described in design-doc section 9.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

from stage0_falsification.common import Catalog, Task, Tool
from stage0_falsification.intervention_runner.backends import ModelBackend


@dataclass
class RawRecord:
    family: str
    candidate_name: str
    mutation_type: str
    task_query: str
    correct_tool: str
    seed: int
    baseline_p_correct: float
    post_p_correct: float
    baseline_dist: dict[str, float]
    post_dist: dict[str, float]


@dataclass
class AggregatedRecord:
    model: str
    family: str
    candidate_name: str
    mutation_type: str
    catalog_size: int
    baseline_accuracy: float
    post_addition_accuracy: float
    delta_accuracy: float


def run_interventions(
    backend: ModelBackend,
    baseline_catalogs: dict[str, Catalog],
    tasks_by_family: dict[str, list[Task]],
    candidates_by_family: dict[str, list[Tool]],
    n_seeds: int = 3,
    n_samples: int = 5,
) -> list[RawRecord]:
    records: list[RawRecord] = []

    for family, catalog in baseline_catalogs.items():
        tasks = tasks_by_family[family]
        candidates = candidates_by_family[family]

        # Baseline distribution depends only on (family, task, seed), not on the
        # candidate being evaluated -- compute it once per (task, seed) and reuse
        # it across all candidates for this family, instead of re-sampling it
        # once per candidate. This cuts real backend calls by roughly 1/(1 + 1/len(candidates)).
        baseline_by_task_seed: dict[tuple[str, int], dict[str, float]] = {}
        for task in tasks:
            for seed in range(n_seeds):
                baseline_by_task_seed[(task.query, seed)] = backend.select_tool(
                    task.query, catalog.tools, n_samples, seed
                )

        for candidate in candidates:
            post_catalog = catalog.with_addition(candidate)

            for task in tasks:
                for seed in range(n_seeds):
                    baseline_dist = baseline_by_task_seed[(task.query, seed)]
                    post_dist = backend.select_tool(task.query, post_catalog.tools, n_samples, seed)

                    records.append(RawRecord(
                        family=family,
                        candidate_name=candidate.name,
                        mutation_type=candidate.mutation_type or "unknown",
                        task_query=task.query,
                        correct_tool=task.correct_tool,
                        seed=seed,
                        baseline_p_correct=baseline_dist.get(task.correct_tool, 0.0),
                        post_p_correct=post_dist.get(task.correct_tool, 0.0),
                        baseline_dist=baseline_dist,
                        post_dist=post_dist,
                    ))

    return records


def aggregate(records: list[RawRecord], model_name: str, catalog_sizes: dict[str, int]) -> list[AggregatedRecord]:
    groups: dict[tuple[str, str], list[RawRecord]] = {}
    for r in records:
        groups.setdefault((r.family, r.candidate_name), []).append(r)

    aggregated = []
    for (family, candidate_name), group in groups.items():
        baseline_acc = sum(r.baseline_p_correct for r in group) / len(group)
        post_acc = sum(r.post_p_correct for r in group) / len(group)
        aggregated.append(AggregatedRecord(
            model=model_name,
            family=family,
            candidate_name=candidate_name,
            mutation_type=group[0].mutation_type,
            catalog_size=catalog_sizes[family],
            baseline_accuracy=baseline_acc,
            post_addition_accuracy=post_acc,
            delta_accuracy=post_acc - baseline_acc,
        ))
    return aggregated


def save_records(path: Path, records: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in records], f, indent=2)


def load_records(path: Path, cls):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [cls(**d) for d in data]
