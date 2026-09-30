"""Cross-server collision study entry point.

    python cross_server_collision_study/run_study.py --backend mock
    python cross_server_collision_study/run_study.py --backend anthropic

Tests whether composing multiple independently-authored real MCP servers
with organically overlapping tools (e.g. Brave/Tavily/Exa's "search the web")
degrades tool-selection determinism/accuracy, and whether that interacts
with overall catalog size (small=15-tool vs large=45-tool backbone).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from cross_server_collision_study.conditions import build_conditions
from cross_server_collision_study.runner import run_collision_study_batch, save_results
from cross_server_collision_study.analysis import build_rows, print_report

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"
RESULTS_DIR = Path(__file__).resolve().parent / "results"
STATE_FILE = RESULTS_DIR / "last_batch.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["mock", "anthropic"], default="mock")
    parser.add_argument("--model", default="claude-haiku-4-5")
    parser.add_argument("--n-seeds", type=int, default=6)
    parser.add_argument("--n-samples", type=int, default=5)
    parser.add_argument("--poll-interval", type=int, default=30)
    parser.add_argument("--resume-batch-id", default=None)
    args = parser.parse_args()

    conditions = build_conditions()
    print(f"[study] {len(conditions)} conditions built: {list(conditions.keys())}")
    for cid, cat in conditions.items():
        print(f"    {cid}: {len(cat.tools)} tools")

    if args.backend == "mock":
        from cross_server_collision_study.mock_runner import run_collision_study_mock
        results = run_collision_study_mock(conditions, n_seeds=args.n_seeds, n_samples=args.n_samples)
    else:
        results = run_collision_study_batch(
            conditions, model=args.model, n_seeds=args.n_seeds, n_samples=args.n_samples,
            poll_interval_seconds=args.poll_interval, resume_batch_id=args.resume_batch_id,
            state_file=STATE_FILE,
        )

    save_results(DATASETS_DIR / f"results_{args.backend}.json", results)
    print(f"[study] saved {len(results)} (condition, task) results")

    rows = build_rows(results)
    print_report(rows)

    if args.backend == "mock":
        print("\nNOTE: mock backend -- pipeline validation only, not a real result.")


if __name__ == "__main__":
    main()
