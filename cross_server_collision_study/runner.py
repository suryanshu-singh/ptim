"""Batch-mode runner for the cross-server collision study.

For each (condition, task, seed, sample): one API call, catalog = that
condition's full tool list, query = that task's query. Results are
aggregated into an empirical tool-selection distribution per (condition,
task) across all seeds x samples.
"""
from __future__ import annotations

import json
import os
import time
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path

from stage0_falsification.common import Catalog
from cross_server_collision_study.tasks import CollisionTask, tasks_for_condition


@dataclass
class ConditionTaskResult:
    condition_id: str
    task_id: str
    metric_type: str
    query: str
    correct_tool: str | None
    valid_tools: list[str] | None
    n_tools_in_catalog: int
    distribution: dict[str, float]  # tool_name_or_'none' -> probability
    n_draws: int


def _build_params(model, tool_schemas, query, temperature, disable_thinking):
    params = dict(
        model=model, max_tokens=512, temperature=temperature,
        tools=tool_schemas, tool_choice={"type": "auto"},
        messages=[{"role": "user", "content": query}],
    )
    if disable_thinking:
        params["thinking"] = {"type": "disabled"}
    return params


def run_collision_study_batch(
    conditions: dict[str, Catalog],
    model: str = "claude-haiku-4-5",
    n_seeds: int = 6,
    n_samples: int = 5,
    temperature: float = 1.0,
    disable_thinking: bool = True,
    poll_interval_seconds: int = 30,
    resume_batch_id: str | None = None,
    state_file: Path | None = None,
) -> list[ConditionTaskResult]:
    try:
        import anthropic
        from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
        from anthropic.types.messages.batch_create_params import Request
    except ImportError as e:
        raise RuntimeError("pip install anthropic") from e

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")
    client = anthropic.Anthropic(api_key=api_key)

    condition_ids = list(conditions.keys())
    # condition_idx -> task list (fixed order) built once, reused for parsing.
    tasks_by_condition: dict[str, list[CollisionTask]] = {
        cid: tasks_for_condition(cid, conditions[cid]) for cid in condition_ids
    }

    if resume_batch_id:
        print(f"[batch] resuming existing batch {resume_batch_id}")
        batch = client.messages.batches.retrieve(resume_batch_id)
    else:
        requests = []
        print(f"[batch] building requests for {len(condition_ids)} conditions...")
        for c_idx, cid in enumerate(condition_ids):
            catalog = conditions[cid]
            tool_schemas = [t.to_anthropic_schema() for t in catalog.tools]
            for t_idx, task in enumerate(tasks_by_condition[cid]):
                for seed in range(n_seeds):
                    for sample_idx in range(n_samples):
                        custom_id = f"c{c_idx}-t{t_idx}-s{seed}-n{sample_idx}"
                        requests.append(Request(
                            custom_id=custom_id,
                            params=MessageCreateParamsNonStreaming(**_build_params(
                                model, tool_schemas, task.query, temperature, disable_thinking
                            )),
                        ))
        print(f"[batch] submitting {len(requests)} requests...")
        batch = client.messages.batches.create(requests=requests)
        print(f"[batch] batch id: {batch.id}")
        if state_file:
            state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump({"batch_id": batch.id, "model": model, "n_seeds": n_seeds,
                           "n_samples": n_samples, "condition_ids": condition_ids}, f, indent=2)
            print(f"[batch] saved batch id to {state_file} -- resume with --resume-batch-id {batch.id} "
                  f"if interrupted, instead of resubmitting.")

    while True:
        batch = client.messages.batches.retrieve(batch.id)
        if batch.processing_status == "ended":
            break
        c = batch.request_counts
        print(f"[batch] status={batch.processing_status} processing={c.processing} "
              f"succeeded={c.succeeded} errored={c.errored}")
        time.sleep(poll_interval_seconds)

    print("[batch] complete.", batch.request_counts)

    counts: dict[tuple[int, int], Counter] = {}
    seen: dict[tuple[int, int], int] = {}
    n_errors = 0

    for result in client.messages.batches.results(batch.id):
        parts = result.custom_id.split("-")
        c_idx = int(parts[0][1:])
        t_idx = int(parts[1][1:])
        key = (c_idx, t_idx)

        tool_name = "none"
        if result.result.type == "succeeded":
            tool_uses = [b for b in result.result.message.content if b.type == "tool_use"]
            if tool_uses:
                tool_name = tool_uses[0].name
        else:
            n_errors += 1

        counts.setdefault(key, Counter())[tool_name] += 1
        seen[key] = seen.get(key, 0) + 1

    if n_errors:
        print(f"[batch] WARNING: {n_errors} requests did not succeed (counted as 'none').")

    results: list[ConditionTaskResult] = []
    for c_idx, cid in enumerate(condition_ids):
        catalog = conditions[cid]
        for t_idx, task in enumerate(tasks_by_condition[cid]):
            key = (c_idx, t_idx)
            c = counts.get(key, Counter())
            n = seen.get(key, 1)
            dist = {name: cnt / n for name, cnt in c.items()}
            results.append(ConditionTaskResult(
                condition_id=cid, task_id=task.task_id, metric_type=task.metric_type,
                query=task.query, correct_tool=task.correct_tool, valid_tools=task.valid_tools,
                n_tools_in_catalog=len(catalog.tools), distribution=dist, n_draws=n,
            ))
    return results


def save_results(path: Path, results: list[ConditionTaskResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in results], f, indent=2)
