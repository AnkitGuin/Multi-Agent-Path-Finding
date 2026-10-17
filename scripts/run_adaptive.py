#!/usr/bin/env python3
"""Fit and evaluate the (optional) adaptive strategy-selector extension.

    python scripts/run_adaptive.py

Reads ``results/raw/adaptive_holdout.jsonl`` (produced by the experiment
pipeline), writes ``results/tables/adaptive_*.csv|.md`` and a figure.
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import seaborn as sns  # noqa: E402

from evaluation.adaptive import (  # noqa: E402
    build_feature_table,
    cross_validate,
    feature_importance,
    oracle_labels,
)
from evaluation.statistics import TABLE_DIR, load_results, save_table  # noqa: E402

sns.set_theme(style="whitegrid")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--budget", type=float, default=10.0, help="per-run time budget (s)")
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args()

    df = load_results(["adaptive_holdout"])
    if df.empty:
        print("no adaptive_holdout results yet; run the experiment pipeline first")
        return
    table = build_feature_table(df)
    print(f"{len(table)} instances in the hold-out pool\n")

    importance = feature_importance(table, args.budget)
    print(importance.to_string(index=False), "\n")
    save_table(importance, "adaptive_feature_importance")

    comparison, descriptions = cross_validate(table, budget=args.budget, folds=args.folds)
    for name, description in descriptions.items():
        print(f"{name}: {description}")
    print()
    print(comparison.to_string(index=False))
    save_table(comparison, "adaptive_comparison")

    os.makedirs(os.path.join(ROOT, "results", "figures"), exist_ok=True)
    metrics = [c for c in comparison.columns if c.startswith("utility_a")] or ["mean_runtime"]
    fig, axes = plt.subplots(1, 4, figsize=(15, 3.6))
    for ax, metric in zip(axes, ["success_rate", "mean_runtime", "mean_soc_gap"] + metrics[:1]):
        sns.barplot(data=comparison, x="strategy", y=metric, ax=ax)
        ax.tick_params(axis="x", rotation=35)
        ax.set_xlabel("")
    fig.suptitle(
        f"Adaptive strategy selection ({args.folds}-fold CV, {len(table)} instances, "
        f"budget {args.budget}s)"
    )
    fig.tight_layout()
    out = os.path.join(ROOT, "results", "figures", "adaptive_selection.png")
    fig.savefig(out)
    print(f"\nfigure -> {out}")
    # Fair quality comparison: mean SOC gaps are success-conditioned, and CBS
    # only succeeds on the easier instances.  Compare both algorithms on the
    # *same* instances (the subset CBS managed to solve) before drawing a
    # conclusion about solution quality.
    cbs_ok = table.index[table["cbs_success"] > 0]
    if len(cbs_ok):
        print(
            f"\nMatched-subset quality ({len(cbs_ok)} instances CBS solved):\n"
            f"  CBS        mean SOC excess over SIC = {table.loc[cbs_ok, 'cbs_soc_gap'].mean():.2%}\n"
            f"  Prioritized mean SOC excess over SIC = {table.loc[cbs_ok, 'prioritized_soc_gap'].mean():.2%}"
        )
    print("\nCBS preference rate of the oracle: "
          f"{oracle_labels(table, args.budget).mean():.1%}")


if __name__ == "__main__":
    main()
