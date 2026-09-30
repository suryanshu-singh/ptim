"""Batch-mode intervention runner using the Anthropic Message Batches API.

This is the recommended path for a real Stage 0 run: it gets the same 50%
Batch API discount on every call, and -- like the fixed synchronous path in
runner.py -- computes each baseline distribution once per (family, task,
seed) and reuses it across all candidates in that family, instead of
re-sampling an identical baseline once per candidate.

All requests for the whole grid are submitted as a single batch, then this
module polls until it completes and reassembles the same RawRecord list
`run_interventions()` produces, so it plugs into the rest of the pipeline
(aggregate / save_records / cheap_baseline) unchanged.
"""
from __future__ import annotations

import json
import os
import time
from collections import Counter
from pathlib import Path

from stage0_falsification.common import Catalog, Task, Tool
from stage0_falsification.intervention_runner.runner import RawRecord

# Where the in-flight batch id is recorded immediately after submission, so a
# real run can be resumed (no resubmission, no double charge) if this process
# gets interrupted -- e.g. a Claude Code session limit resetting -- before the
# batch finishes. Batch results stay retrievable from Anthropic for 29 days.
BATCH_STATE_FILE = Path(__file__).resolve().parent.parent / "results" / "last_batch.json"


def _save_batch_state(batch_id: str, **params) -> None:
    BATCH_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BATCH_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"batch_id": batch_id, **params}, f, indent=2)
    print(f"[batch] saved batch id to {BATCH_STATE_FILE} -- if this process is interrupted, "
          f"resume with --resume-batch-id {batch_id} instead of resubmitting.")


def _build_params(model: str, tool_schemas: list[dict], query: str,
                   temperature: float, disable_thinking: bool, effort: str | None) -> dict:
    params: dict = dict(
        model=model,
        max_tokens=512,
        temperature=temperature,
        tools=tool_schemas,
        tool_choice={"type": "auto"},
        messages=[{"role": "user", "content": query}],
    )
    if disable_thinking:
        params["thinking"] = {"type": "disabled"}
    if effort:
        params["output_config"] = {"effort": effort}
    return params


def run_interventions_batch(
    baseline_catalogs: dict[str, Catalog],
    tasks_by_family: dict[str, list[Task]],
    candidates_by_family: dict[str, list[Tool]],
    model: str = "claude-haiku-4-5",
    n_seeds: int = 3,
    n_samples: int = 5,
    temperature: float = 1.0,
    disable_thinking: bool = True,
    effort: str | None = None,
    poll_interval_seconds: int = 30,
    resume_batch_id: str | None = None,
) -> list[RawRecord]:
    try:
        import anthropic
        from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
        from anthropic.types.messages.batch_create_params import Request
    except ImportError as e:
        raise RuntimeError(
            "The 'anthropic' package is required for batch mode. Install it with `pip install anthropic`."
        ) from e

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set in the environment.")
    client = anthropic.Anthropic(api_key=api_key)

    families = list(baseline_catalogs.keys())

    if resume_batch_id:
        print(f"[batch] resuming existing batch {resume_batch_id} -- not submitting new requests.")
        batch = client.messages.batches.retrieve(resume_batch_id)
    else:
        requests = []

        print(f"[batch] building requests for {len(families)} families...")
        for family_idx, family in enumerate(families):
            catalog = baseline_catalogs[family]
            tasks = tasks_by_family[family]
            candidates = candidates_by_family[family]
            baseline_schemas = [t.to_anthropic_schema() for t in catalog.tools]

            for task_idx, task in enumerate(tasks):
                for seed in range(n_seeds):
                    for sample_idx in range(n_samples):
                        custom_id = f"b-{family_idx}-{task_idx}-{seed}-{sample_idx}"
                        requests.append(Request(
                            custom_id=custom_id,
                            params=MessageCreateParamsNonStreaming(**_build_params(
                                model, baseline_schemas, task.query, temperature, disable_thinking, effort
                            )),
                        ))

            for candidate_idx, candidate in enumerate(candidates):
                post_schemas = [t.to_anthropic_schema() for t in [*catalog.tools, candidate]]
                for task_idx, task in enumerate(tasks):
                    for seed in range(n_seeds):
                        for sample_idx in range(n_samples):
                            custom_id = f"p-{family_idx}-{candidate_idx}-{task_idx}-{seed}-{sample_idx}"
                            requests.append(Request(
                                custom_id=custom_id,
                                params=MessageCreateParamsNonStreaming(**_build_params(
                                    model, post_schemas, task.query, temperature, disable_thinking, effort
                                )),
                            ))

        print(f"[batch] submitting {len(requests)} requests as one batch (Batch API, 50% off standard pricing)...")
        batch = client.messages.batches.create(requests=requests)
        print(f"[batch] batch id: {batch.id}")
        _save_batch_state(batch.id, model=model, n_seeds=n_seeds, n_samples=n_samples,
                           disable_thinking=disable_thinking, effort=effort)

    while True:
        batch = client.messages.batches.retrieve(batch.id)
        if batch.processing_status == "ended":
            break
        counts = batch.request_counts
        print(f"[batch] status={batch.processing_status} "
              f"processing={getattr(counts, 'processing', '?')} "
              f"succeeded={getattr(counts, 'succeeded', '?')} "
              f"errored={getattr(counts, 'errored', '?')}")
        time.sleep(poll_interval_seconds)

    print("[batch] complete. request_counts:", batch.request_counts)

    baseline_counts: dict[tuple[int, int, int], Counter] = {}
    baseline_seen: dict[tuple[int, int, int], int] = {}
    post_counts: dict[tuple[int, int, int, int], Counter] = {}
    post_seen: dict[tuple[int, int, int, int], int] = {}
    n_errors = 0

    for result in client.messages.batches.results(batch.id):
        parts = result.custom_id.split("-")
        kind = parts[0]

        tool_name = "none"
        if result.result.type == "succeeded":
            tool_uses = [b for b in result.result.message.content if b.type == "tool_use"]
            if tool_uses:
                tool_name = tool_uses[0].name
        else:
            n_errors += 1

        if kind == "b":
            family_idx, task_idx, seed, _sample = (int(x) for x in parts[1:])
            key = (family_idx, task_idx, seed)
            baseline_counts.setdefault(key, Counter())[tool_name] += 1
            baseline_seen[key] = baseline_seen.get(key, 0) + 1
        else:
            family_idx, candidate_idx, task_idx, seed, _sample = (int(x) for x in parts[1:])
            key = (family_idx, candidate_idx, task_idx, seed)
            post_counts.setdefault(key, Counter())[tool_name] += 1
            post_seen[key] = post_seen.get(key, 0) + 1

    if n_errors:
        print(f"[batch] WARNING: {n_errors} requests did not succeed (counted as 'none').")

    records: list[RawRecord] = []
    for family_idx, family in enumerate(families):
        tasks = tasks_by_family[family]
        candidates = candidates_by_family[family]

        for candidate_idx, candidate in enumerate(candidates):
            for task_idx, task in enumerate(tasks):
                for seed in range(n_seeds):
                    b_key = (family_idx, task_idx, seed)
                    p_key = (family_idx, candidate_idx, task_idx, seed)

                    b_counts = baseline_counts.get(b_key, Counter())
                    b_n = baseline_seen.get(b_key, 1)
                    baseline_dist = {name: c / b_n for name, c in b_counts.items()}

                    p_counts = post_counts.get(p_key, Counter())
                    p_n = post_seen.get(p_key, 1)
                    post_dist = {name: c / p_n for name, c in p_counts.items()}

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
