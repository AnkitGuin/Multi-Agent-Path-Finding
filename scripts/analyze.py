#!/usr/bin/env python3
"""Print (and save) every number that the report quotes.

    python scripts/analyze.py            # human-readable summary + markdown tables
    python scripts/analyze.py --json     # machine-readable dump

Nothing here re-runs a planner: it only reads ``results/raw/*.jsonl``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from evaluation.statistics import (  # noqa: E402
    TABLE_DIR,
    load_results,
    mean_table,
    paired_comparison,
    save_table,
    summarise,
    success_table,
)

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 40)


def heading(text: str) -> None:
    print("\n" + "=" * 78)
    print(text)
    print("=" * 78)


def show(df: pd.DataFrame, title: str, save_as: str = "") -> pd.DataFrame:
    print(f"\n--- {title}")
    print(df.round(4).to_string())
    if save_as:
        save_table(df.round(4), save_as)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="dump a JSON summary")
    args = parser.parse_args()

    results = load_results()
    if results.empty:
        print("no results found in results/raw — run scripts/run_experiments.py first")
        return
    print(f"loaded {len(results)} raw runs from results/raw")
    print(results.groupby("suite")["algorithm"].value_counts().to_string())

    payload: dict = {}

    # ---------------------------------------------------------- overall view
    heading("1. Overall behaviour of each strategy (all main suites pooled)")
    main = results[results["suite"] != "adaptive_holdout"]
    overall = summarise(main[main["algorithm"] != "Prioritized+restarts"], ["algorithm"])
    show(overall[[
        "algorithm", "n", "success_rate", "timeout_rate", "failure_rate",
        "runtime_mean", "runtime_median", "runtime_std",
        "soc_mean", "makespan_mean", "soc_gap_mean", "soc_gap_max",
        "high_level_expansions_mean",
    ]], "per-algorithm summary", "overall_summary")
    payload["overall"] = overall.to_dict("records")

    # ------------------------------------------------------------ scalability
    heading("2. Scalability in the number of agents (32x32, 20%, uniform)")
    df = results[results["suite"] == "scalability"]
    if not df.empty:
        show(success_table(df, "num_agents"), "success rate", "scalability_success")
        show(mean_table(df, "runtime_sec", "num_agents"), "mean runtime (s)",
             "scalability_runtime")
        show(mean_table(df, "soc_gap", "num_agents", solved_only=True),
             "SOC excess over SIC (solved runs only)", "scalability_soc_gap")
        show(mean_table(df, "makespan", "num_agents", solved_only=True),
             "makespan (solved runs only)", "scalability_makespan")
        show(mean_table(df, "conflicts_initial", "num_agents"),
             "conflicts in the independent plan", "scalability_conflicts")
        payload["scalability_success"] = (
            success_table(df, "num_agents").reset_index().astype({"num_agents": int}).to_dict("records")
        )

    # --------------------------------------------------------------- density
    heading("3. Obstacle density (32x32, random)")
    df = results[results["suite"] == "density"]
    if not df.empty:
        for agents in sorted(df["num_agents"].unique()):
            sub = df[df["num_agents"] == agents]
            show(success_table(sub, "obstacle_density_requested"),
                 f"success rate — {agents} agents")
            show(mean_table(sub, "runtime_sec", "obstacle_density_requested"),
                 f"mean runtime (s) — {agents} agents")
            show(mean_table(sub, "conflicts_initial", "obstacle_density_requested"),
                 f"conflicts in the independent plan — {agents} agents")
        payload["density"] = summarise(df, ["algorithm", "obstacle_density_requested"]).to_dict("records")

    # ------------------------------------------------------------- structure
    heading("4. Map structure (32x32, 20%)")
    df = results[results["suite"] == "structure"]
    if not df.empty:
        show(success_table(df, "structure"), "success rate", "structure_success")
        show(mean_table(df, "runtime_sec", "structure"), "mean runtime (s)", "structure_runtime")
        show(mean_table(df, "conflicts_initial", "structure"), "conflicts in the independent plan",
             "structure_conflicts")
        show(mean_table(df, "soc_gap", "structure", solved_only=True),
             "SOC excess over SIC (solved)", "structure_soc_gap")

    # --------------------------------------------------------- distribution
    heading("5. Start/goal distribution = congestion (32x32, 20%, 20 agents)")
    df = results[results["suite"] == "distribution"]
    if not df.empty:
        show(success_table(df, "distribution"), "success rate", "distribution_success")
        show(mean_table(df, "runtime_sec", "distribution"), "mean runtime (s)", "distribution_runtime")
        show(mean_table(df, "conflicts_initial", "distribution"), "conflicts in the independent plan",
             "distribution_conflicts")
        show(mean_table(df, "soc_gap", "distribution", solved_only=True),
             "SOC excess over SIC (solved)", "distribution_soc_gap")

    # -------------------------------------------------------------- gridsize
    heading("6. Map size (20% obstacles)")
    df = results[results["suite"] == "gridsize"].copy()
    if not df.empty:
        df["grid_area"] = df["width"] * df["height"]
        show(success_table(df, "grid_area"), "success rate", "gridsize_success")
        show(mean_table(df, "runtime_sec", "grid_area"), "mean runtime (s)", "gridsize_runtime")

    # -------------------------------------------------------- priority orders
    heading("7. Prioritized Planning: priority-order ablation")
    df = results[results["suite"] == "priority_orders"].copy()
    if not df.empty:
        df["strategy"] = df.apply(lambda r: r["priority_order"] or r["algorithm"], axis=1)
        table = summarise(df, ["strategy", "num_agents"])
        show(table[["strategy", "num_agents", "n", "success_rate", "runtime_mean",
                    "soc_mean", "soc_gap_mean"]], "ordering rules", "priority_orders_table")

    # ------------------------------------------------------ paired comparisons
    heading("8. Paired comparisons (same instances, both algorithms successful)")
    df = results[results["suite"] == "scalability"]
    if not df.empty:
        for metric in ("runtime_sec", "soc", "makespan"):
            stats = paired_comparison(df, "Prioritized", "CBS", metric)
            print(f"  {metric:12s} " + "  ".join(
                f"{k}={v}" for k, v in stats.items() if isinstance(v, (int, float))
            ))
            payload.setdefault("paired", []).append(stats)

    # ------------------------------------------------------------ key findings
    heading("9. Headline numbers")
    solved = main[main["success"] == 1]
    lines = []
    for algorithm in ("Independent", "Prioritized", "CBS"):
        sub = main[main["algorithm"] == algorithm]
        if sub.empty:
            continue
        lines.append(
            f"{algorithm:12s} success={sub['success'].mean():.1%}  "
            f"median time={sub['runtime_sec'].median():.3f}s  "
            f"timeout={ (sub['status'] == 'timeout').mean():.1%}"
        )
    indep = main[main["algorithm"] == "Independent"]
    if not indep.empty:
        lines.append(
            f"Independent A* produces on average "
            f"{indep['conflicts_initial'].mean():.1f} conflicts per instance "
            f"(max {indep['conflicts_initial'].max():.0f})"
        )
    cbs = main[main["algorithm"] == "CBS"]
    pp = main[main["algorithm"] == "Prioritized"]
    if not cbs.empty and not pp.empty:
        lines.append(
            f"CBS plan quality: mean SOC excess over SIC "
            f"{solved[solved['algorithm'] == 'CBS']['soc_gap'].mean():.2%}; "
            f"Prioritized: "
            f"{solved[solved['algorithm'] == 'Prioritized']['soc_gap'].mean():.2%}"
        )
        correlation = np.corrcoef(
            main.dropna(subset=["conflicts_initial"])["conflicts_initial"],
            main.dropna(subset=["conflicts_initial"])["runtime_sec"],
        )[0, 1]
        lines.append(
            f"correlation(initial conflicts, runtime) over all runs = {correlation:.2f}"
        )
    for line in lines:
        print("  " + line)
    payload["headlines"] = lines

    with open(os.path.join(TABLE_DIR, "analysis_summary.md"), "w", encoding="utf-8") as handle:
        handle.write("# Analysis summary\n\n")
        for line in lines:
            handle.write(f"- {line}\n")

    if args.json:
        with open(os.path.join(TABLE_DIR, "analysis_summary.json"), "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, default=str)
        print(f"\nJSON summary -> {os.path.join(TABLE_DIR, 'analysis_summary.json')}")


if __name__ == "__main__":
    main()
