"""Turns raw ConditionTaskResult records into the actual answers:
  - does an ambiguous task's tool-selection entropy rise as more organically-
    overlapping real servers are connected (collision degree 1/2/3)?
  - does overall catalog size (small/large backbone) change that?
  - is there collateral damage to unrelated (time/git) task accuracy?
  - does the model wrongly reach for a look-alike it can't actually use
    (capability-specific tasks)?
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

from cross_server_collision_study.runner import ConditionTaskResult


def _parse_condition_id(cid: str) -> tuple[str, int, str]:
    # e.g. "search_d2_large" -> ("search", 2, "large")
    m = re.match(r"(search|messaging)_d(\d+)_(small|large)", cid)
    family, degree, backbone = m.group(1), int(m.group(2)), m.group(3)
    return family, degree, backbone


def entropy_bits(dist: dict[str, float], support: list[str]) -> tuple[float, float]:
    """Returns (normalized_entropy in [0,1], on_target_rate) restricted to `support`."""
    on_target_mass = sum(dist.get(t, 0.0) for t in support)
    if on_target_mass <= 1e-9 or len(support) <= 1:
        return 0.0, on_target_mass
    probs = [dist.get(t, 0.0) / on_target_mass for t in support]
    h = -sum(p * math.log2(p) for p in probs if p > 1e-12)
    h_max = math.log2(len(support))
    return (h / h_max if h_max > 0 else 0.0), on_target_mass


@dataclass
class Row:
    family: str
    degree: int
    backbone: str
    task_id: str
    metric_type: str
    n_tools: int
    value: float          # accuracy [0,1] or normalized entropy [0,1]
    on_target_rate: float | None  # only meaningful for entropy tasks
    top_tool: str | None
    top_tool_share: float | None


def build_rows(results: list[ConditionTaskResult]) -> list[Row]:
    rows = []
    for r in results:
        family, degree, backbone = _parse_condition_id(r.condition_id)
        top_tool, top_share = (max(r.distribution.items(), key=lambda kv: kv[1])
                                if r.distribution else (None, None))
        if r.metric_type == "accuracy":
            value = r.distribution.get(r.correct_tool, 0.0)
            on_target = None
        else:
            value, on_target = entropy_bits(r.distribution, r.valid_tools or [])
        rows.append(Row(family=family, degree=degree, backbone=backbone, task_id=r.task_id,
                         metric_type=r.metric_type, n_tools=r.n_tools_in_catalog, value=value,
                         on_target_rate=on_target, top_tool=top_tool, top_tool_share=top_share))
    return rows


def print_report(rows: list[Row]) -> None:
    print("=" * 78)
    print("AMBIGUOUS-TASK ENTROPY vs. COLLISION DEGREE (0 = always same tool, 1 = fully confused)")
    print("=" * 78)
    for family in ("search", "messaging"):
        for backbone in ("small", "large"):
            matches = [r for r in rows if r.family == family and r.backbone == backbone
                       and r.task_id.endswith("_ambiguous")]
            matches.sort(key=lambda r: r.degree)
            if not matches:
                continue
            print(f"\n  {family} / {backbone} backbone:")
            for r in matches:
                print(f"    degree={r.degree}  n_tools={r.n_tools:3d}  "
                      f"entropy={r.value:.3f}  on_target_rate={r.on_target_rate:.3f}")

    print()
    print("=" * 78)
    print("COLLATERAL DAMAGE: accuracy on UNRELATED tasks (time/git) as collision degree grows")
    print("=" * 78)
    for task_id in ("time_task", "git_task"):
        for family in ("search", "messaging"):
            for backbone in ("small", "large"):
                matches = [r for r in rows if r.family == family and r.backbone == backbone
                           and r.task_id == task_id]
                matches.sort(key=lambda r: r.degree)
                if not matches:
                    continue
                vals = "  ".join(f"d{r.degree}(n={r.n_tools})={r.value:.3f}" for r in matches)
                print(f"  [{task_id}] {family}/{backbone}: {vals}")

    print()
    print("=" * 78)
    print("CAPABILITY-SPECIFIC: does the model wrongly reach for a look-alike that can't do the job?")
    print("=" * 78)
    for task_id in ("brave_local_task", "tavily_map_task"):
        matches = [r for r in rows if r.task_id == task_id]
        matches.sort(key=lambda r: (r.backbone, r.degree))
        for r in matches:
            print(f"  [{task_id}] {r.backbone}/degree{r.degree} (n_tools={r.n_tools}): "
                  f"accuracy={r.value:.3f}  top_tool={r.top_tool} ({r.top_tool_share:.2f})")
