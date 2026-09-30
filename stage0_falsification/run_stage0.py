"""Stage 0 / 0.5 falsification pipeline entry point.

    python stage0_falsification/run_stage0.py --backend mock
    python stage0_falsification/run_stage0.py --backend anthropic

Generates the eight baseline catalogs, generates 64 candidate additions across
five mutation types per family, runs baseline-vs-post-addition interventions
via the chosen backend (defaults: 5 seeds x 5 samples), fits the cheap-vs-full
model comparison, and reports the Stage 0.5 diagnostics (effect-size
distribution, repeatability subset, Recall@10) needed to judge signal vs.
noise rather than relying on a single R^2 number.

See README.md in this directory for the decision criterion.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

# Loads ANTHROPIC_API_KEY (and anything else) from a .env file in the repo root,
# if one exists, into the process environment -- see .env.example. Falls back
# silently to whatever is already in the environment if there's no .env file.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from stage0_falsification.catalog_generator.catalog_generator import build_baseline_catalogs
from stage0_falsification.catalog_generator.tool_families import ALL_FAMILIES, FAMILY_TASKS
from stage0_falsification.mutation_engine.candidates import candidates_for_family
from stage0_falsification.intervention_runner.backends import build_backend
from stage0_falsification.intervention_runner.runner import run_interventions, aggregate, save_records
from stage0_falsification.intervention_runner.batch_runner import run_interventions_batch
from stage0_falsification.cheap_baseline.baseline import build_features, evaluate
from stage0_falsification.cheap_baseline.stage0_5_report import (
    select_repeatability_candidates, build_per_candidate_report, build_stage0_5_aggregate,
)

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Stage 0 falsification pipeline.")
    parser.add_argument("--backend", choices=["mock", "anthropic"], default="mock")
    parser.add_argument("--model", default="claude-haiku-4-5", help="Model name (anthropic backend only).")
    parser.add_argument("--n-seeds", type=int, default=5)
    parser.add_argument("--n-samples", type=int, default=5, help="Samples per (task, seed) draw.")
    parser.add_argument("--enable-thinking", action="store_true",
                         help="Allow adaptive thinking on the anthropic backend (default: disabled). "
                              "These are short synthetic tool-selection queries -- thinking adds "
                              "billed output tokens with no expected benefit, so it's off by default.")
    parser.add_argument("--effort", default=None, choices=["low", "medium", "high", "xhigh", "max"],
                         help="output_config.effort for the anthropic backend (default: unset -> high).")
    parser.add_argument("--no-batch", action="store_true",
                         help="Use the synchronous per-call path instead of the Batch API. "
                              "The anthropic backend defaults to batch mode (50%% cheaper, and "
                              "reuses each baseline sample across all 5 candidates in a family).")
    parser.add_argument("--poll-interval", type=int, default=30,
                         help="Seconds between batch status checks (batch mode only).")
    parser.add_argument("--resume-batch-id", default=None,
                         help="Resume polling an already-submitted batch instead of submitting a new "
                              "one (batch mode only). The id was printed and saved to "
                              "results/last_batch.json when the batch was first submitted -- use this "
                              "if that run was interrupted, to avoid paying for the requests twice.")
    args = parser.parse_args()

    use_batch = args.backend == "anthropic" and not args.no_batch
    disable_thinking = not args.enable_thinking

    print(f"[stage0] backend={args.backend} n_seeds={args.n_seeds} n_samples={args.n_samples} "
          f"batch={use_batch} disable_thinking={disable_thinking} effort={args.effort}")

    baseline_catalogs = build_baseline_catalogs()
    candidates_by_family = {family: candidates_for_family(family, random_seed=i)
                             for i, family in enumerate(ALL_FAMILIES)}

    print("[stage0] running interventions...")
    if use_batch:
        raw_records = run_interventions_batch(
            baseline_catalogs=baseline_catalogs,
            tasks_by_family=FAMILY_TASKS,
            candidates_by_family=candidates_by_family,
            model=args.model,
            n_seeds=args.n_seeds,
            n_samples=args.n_samples,
            disable_thinking=disable_thinking,
            effort=args.effort,
            poll_interval_seconds=args.poll_interval,
            resume_batch_id=args.resume_batch_id,
        )
    else:
        backend_kwargs = {}
        if args.backend == "anthropic":
            backend_kwargs = {"model": args.model, "disable_thinking": disable_thinking, "effort": args.effort}
        backend = build_backend(args.backend, **backend_kwargs)
        raw_records = run_interventions(
            backend=backend,
            baseline_catalogs=baseline_catalogs,
            tasks_by_family=FAMILY_TASKS,
            candidates_by_family=candidates_by_family,
            n_seeds=args.n_seeds,
            n_samples=args.n_samples,
        )
    print(f"[stage0] {len(raw_records)} raw (task, seed) records collected")

    catalog_sizes = {f: len(c.tools) for f, c in baseline_catalogs.items()}
    aggregated = aggregate(raw_records, model_name=f"{args.backend}:{args.model}", catalog_sizes=catalog_sizes)

    save_records(DATASETS_DIR / f"raw_{args.backend}.json", raw_records)
    save_records(DATASETS_DIR / f"aggregated_{args.backend}.json", aggregated)
    print(f"[stage0] saved {len(aggregated)} aggregated (family, candidate) records to datasets/")

    print("[stage0] fitting cheap-baseline vs full-feature models (leave-one-family-out CV)...")
    rows = build_features(aggregated, candidates_by_family, baseline_catalogs)
    report = evaluate(rows)

    repeatability_ids = select_repeatability_candidates(aggregated, n=10, seed=42)
    stage0_5_aggregate = build_stage0_5_aggregate(aggregated, report, args.n_seeds, repeatability_ids)
    per_candidate = build_per_candidate_report(
        aggregated, rows, report, raw_records, args.n_seeds, repeatability_ids
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = RESULTS_DIR / f"stage0_report_{args.backend}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(stage0_5_aggregate, f, indent=2, default=str)
    per_candidate_path = DATASETS_DIR / f"per_candidate_{args.backend}.json"
    per_candidate_path.parent.mkdir(parents=True, exist_ok=True)
    with open(per_candidate_path, "w", encoding="utf-8") as f:
        json.dump(per_candidate, f, indent=2, default=str)

    eff = stage0_5_aggregate["effect_size_distribution"]
    print()
    print("=" * 70)
    print(f"n candidates:      {stage0_5_aggregate['n_candidates']}   n seeds: {stage0_5_aggregate['n_seeds']}")
    print(f"cheap baseline R2: {report['cheap_r2']:.3f}   full model R2: {report['full_r2']:.3f}   "
          f"gap: {report['r2_gap']:.3f}")
    print(f"mechanical verdict (do not treat as final -- see decision rules in "
          f"PTIM_Stage_0_5_Refined_Experiment.md section 15-16): {report['verdict']}")
    print()
    print("effect-size distribution (delta_loss; positive = addition made things worse):")
    print(f"  mean={eff['mean']:.4f} median={eff['median']:.4f} std={eff['std']:.4f} "
          f"min={eff['min']:.4f} max={eff['max']:.4f}")
    print(f"  p25={eff['p25']:.4f} p75={eff['p75']:.4f}  "
          f"n(delta>0)={eff['count_delta_gt_0']} n(delta<0)={eff['count_delta_lt_0']} "
          f"n(delta=0)={eff['count_delta_eq_0']}")
    print()
    print(f"Recall@10 (predicted-most-damaging vs actually-most-damaging):")
    for model_name, val in stage0_5_aggregate["recall_at_10"].items():
        print(f"  {model_name}: {val:.2f}")
    print()
    print(f"repeatability subset ({len(repeatability_ids)} candidates, "
          f"{stage0_5_aggregate['repeatability_selection_method']}):")
    rep_entries = [e for e in per_candidate if "repeatability" in e]
    for e in rep_entries:
        r = e["repeatability"]
        print(f"  {e['candidate_id']:45s} delta_mean={r['delta_mean']:+.4f} delta_std={r['delta_std']:.4f} "
              f"{'[delta within 1 std of 0 -> looks like noise]' if abs(r['delta_mean']) < r['delta_std'] else '[delta exceeds 1 std -> looks like signal]'}")
    print("=" * 70)
    print(f"aggregate report saved to {report_path}")
    print(f"per-candidate report (with repeatability) saved to {DATASETS_DIR / f'per_candidate_{args.backend}.json'}")

    if args.backend == "mock":
        print()
        print("NOTE: this ran against the mock backend, which simulates tool selection")
        print("from the same similarity signal the cheap baseline uses. This verdict")
        print("only confirms the pipeline runs end-to-end -- it is NOT a real Stage 0")
        print("result. Re-run with --backend anthropic (requires ANTHROPIC_API_KEY) for")
        print("the actual falsification test.")


if __name__ == "__main__":
    main()
