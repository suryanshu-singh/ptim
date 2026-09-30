"""Free, synchronous mock runner for pipeline validation only -- same caveat
as stage0_falsification's MockBackend: it simulates selection via TF-IDF
cosine similarity, so it cannot validate the actual hypothesis, only that
data flows correctly end to end.
"""
from __future__ import annotations

from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from stage0_falsification.common import Catalog
from cross_server_collision_study.runner import ConditionTaskResult
from cross_server_collision_study.tasks import tasks_for_condition


def run_collision_study_mock(
    conditions: dict[str, Catalog],
    n_seeds: int = 6,
    n_samples: int = 5,
    temperature: float = 0.6,
) -> list[ConditionTaskResult]:
    results = []
    for cid, catalog in conditions.items():
        for task in tasks_for_condition(cid, catalog):
            corpus = [task.query] + [f"{t.name.replace('_', ' ')} {t.description}" for t in catalog.tools]
            vec = TfidfVectorizer(stop_words="english")
            mat = vec.fit_transform(corpus).toarray()
            q_vec, tool_vecs = mat[0], mat[1:]
            sims = np.array([
                float(np.dot(q_vec, tv) / (np.linalg.norm(q_vec) * np.linalg.norm(tv) + 1e-9))
                for tv in tool_vecs
            ])
            logits = sims / temperature
            probs = np.exp(logits - logits.max())
            probs = probs / probs.sum()

            counts = Counter()
            n_draws = n_seeds * n_samples
            for seed in range(n_seeds):
                rng = np.random.default_rng(seed)
                draws = rng.choice(len(catalog.tools), size=n_samples, p=probs)
                for i in draws:
                    counts[catalog.tools[i].name] += 1

            dist = {name: c / n_draws for name, c in counts.items()}
            results.append(ConditionTaskResult(
                condition_id=cid, task_id=task.task_id, metric_type=task.metric_type,
                query=task.query, correct_tool=task.correct_tool, valid_tools=task.valid_tools,
                n_tools_in_catalog=len(catalog.tools), distribution=dist, n_draws=n_draws,
            ))
    return results
