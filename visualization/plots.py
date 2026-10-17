"""Generate every figure of the study from the raw result files.

Run with::

    python scripts/make_plots.py

All figures are written to ``results/figures``; the raw data they are derived
from stays in ``results/raw`` so the figures can always be regenerated.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

from evaluation.statistics import load_results, save_table, summarise  # noqa: E402

FIGURE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "figures"
)

sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams.update({"figure.dpi": 130, "savefig.bbox": "tight", "font.size": 9})

ALGO_STYLE: Dict[str, Dict[str, object]] = {
    "Independent": {"color": "#8d99ae", "marker": "o", "linestyle": ":"},
    "Prioritized": {"color": "#2a9d8f", "marker": "s", "linestyle": "--"},
    "CBS": {"color": "#e76f51", "marker": "^", "linestyle": "-"},
}
ORDER = ["Independent", "Prioritized", "CBS"]


def _ordered(algorithms: Sequence[str]) -> List[str]:
    return [a for a in ORDER if a in algorithms] + [
        a for a in algorithms if a not in ORDER
    ]


def _save(fig: plt.Figure, name: str, directory: str) -> str:
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"{name}.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  -> {path}")
    return path


def _algo_plot(summary: pd.DataFrame, x: str, y: str, ax: plt.Axes, log_y: bool = False):
    for algorithm in _ordered(summary["algorithm"].unique()):
        data = summary[summary["algorithm"] == algorithm].sort_values(x)
        style = ALGO_STYLE.get(algorithm, {})
        ax.errorbar(
            data[x],
            data[y],
            yerr=data.get(f"{y}_ci95"),
            label=algorithm,
            color=style.get("color"),
            marker=style.get("marker"),
            linestyle=style.get("linestyle"),
            capsize=3,
            markersize=5,
        )
    if log_y:
        ax.set_yscale("log")
    ax.set_xlabel(x.replace("_", " "))
    ax.set_ylabel(y.replace("_", " "))
    ax.legend()


def plot_scalability(df: pd.DataFrame, directory: str) -> None:
    summary = summarise(df, ["algorithm", "num_agents"])
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
    _algo_plot(summary, "num_agents", "runtime_mean", axes[0], log_y=True)
    axes[0].set_title("Planning time vs. number of agents")
    _algo_plot(summary, "num_agents", "success_rate", axes[1])
    axes[1].set_ylim(-0.02, 1.05)
    axes[1].set_title("Success rate vs. number of agents")
    _algo_plot(summary, "num_agents", "soc_gap_mean", axes[2])
    axes[2].set_title("SOC excess over SIC (solved runs)")
    fig.suptitle("Scalability (32x32 random maps, 20% obstacles, 12 seeds per point)")
    _save(fig, "scalability", directory)
    save_table(summary, "scalability_summary")


def plot_density(df: pd.DataFrame, directory: str) -> None:
    summary = summarise(df, ["algorithm", "obstacle_density_requested", "num_agents"])
    for agents, group in summary.groupby("num_agents"):
        fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
        _algo_plot(group, "obstacle_density_requested", "runtime_mean", axes[0], log_y=True)
        axes[0].set_title("Planning time")
        _algo_plot(group, "obstacle_density_requested", "success_rate", axes[1])
        axes[1].set_ylim(-0.02, 1.05)
        axes[1].set_title("Success rate")
        _algo_plot(group, "obstacle_density_requested", "soc_gap_mean", axes[2])
        axes[2].set_title("SOC excess over SIC")
        fig.suptitle(f"Effect of obstacle density ({agents} agents, 32x32, 8 seeds)")
        _save(fig, f"density_a{agents}", directory)
    save_table(summary, "density_summary")


def plot_structure(df: pd.DataFrame, directory: str) -> None:
    summary = summarise(df, ["algorithm", "structure", "num_agents"])
    for agents, group in summary.groupby("num_agents"):
        fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
        for ax, (metric, title, logy) in zip(
            axes,
            [
                ("runtime_mean", "Planning time", True),
                ("success_rate", "Success rate", False),
                ("soc_gap_mean", "SOC excess over SIC", False),
            ],
        ):
            pivot = group.pivot(index="structure", columns="algorithm", values=metric)
            pivot = pivot[_ordered(pivot.columns)]
            pivot.plot(
                kind="bar",
                ax=ax,
                logy=logy,
                color=[ALGO_STYLE.get(c, {}).get("color") for c in pivot.columns],
            )
            ax.set_title(title)
            ax.set_xlabel("map structure")
            ax.tick_params(axis="x", rotation=0)
            if metric == "success_rate":
                ax.set_ylim(0, 1.05)
            ax.legend_.remove() if ax.legend_ else None
        axes[-1].legend(title="algorithm")
        fig.suptitle(f"Effect of map structure ({agents} agents, 32x32, 8 seeds)")
        _save(fig, f"structure_a{agents}", directory)
    save_table(summary, "structure_summary")


def plot_distribution(df: pd.DataFrame, directory: str) -> None:
    summary = summarise(df, ["algorithm", "distribution"])
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
    for ax, (metric, title, logy) in zip(
        axes,
        [
            ("conflicts_initial_mean", "Conflicts in the independent plan", False),
            ("runtime_mean", "Planning time (s, log)", True),
            ("success_rate", "Success rate", False),
        ],
    ):
        pivot = summary.pivot(index="distribution", columns="algorithm", values=metric)
        pivot = pivot[_ordered(pivot.columns)]
        pivot.plot(
            kind="bar",
            ax=ax,
            logy=logy,
            color=[ALGO_STYLE.get(c, {}).get("color") for c in pivot.columns],
        )
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=0)
        if ax.legend_:
            ax.legend_.remove()
    axes[-1].legend(title="algorithm")
    fig.suptitle("Effect of start/goal distribution (20 agents, 32x32, 20%, 10 seeds)")
    _save(fig, "distribution", directory)
    save_table(summary, "distribution_summary")


def plot_gridsize(df: pd.DataFrame, directory: str) -> None:
    df = df.copy()
    df["grid_area"] = df["width"] * df["height"]
    summary = summarise(df, ["algorithm", "grid_area", "num_agents"])
    for agents, group in summary.groupby("num_agents"):
        fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
        _algo_plot(group, "grid_area", "runtime_mean", axes[0], log_y=True)
        axes[0].set_title("Planning time vs. map size")
        _algo_plot(group, "grid_area", "success_rate", axes[1])
        axes[1].set_ylim(-0.02, 1.05)
        axes[1].set_title("Success rate vs. map size")
        fig.suptitle(f"Effect of map size ({agents} agents, 20% obstacles, 8 seeds)")
        _save(fig, f"gridsize_a{agents}", directory)
    save_table(summary, "gridsize_summary")


def plot_priority_orders(df: pd.DataFrame, directory: str) -> None:
    data = df.copy()
    data["strategy"] = data.apply(
        lambda r: r["priority_order"] or r["algorithm"], axis=1
    )
    summary = summarise(data, ["strategy", "num_agents"])
    strategies = list(dict.fromkeys(summary.sort_values("success_rate", ascending=False)["strategy"]))
    groups = list(summary.groupby("num_agents"))
    metrics = ["success_rate", "soc_mean", "runtime_mean"]
    labels = ["success rate", "SOC (solved runs)", "runtime (s)"]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
    for ax, metric, label in zip(axes, metrics, labels):
        positions = np.arange(len(strategies))
        height = 0.8 / max(1, len(groups))
        for i, (agents, group) in enumerate(groups):
            lookup = group.set_index("strategy")[metric]
            values = [lookup.get(s, np.nan) for s in strategies]
            ax.barh(
                positions + i * height - 0.4 + height / 2,
                values,
                height=height,
                label=f"{agents} agents",
            )
        ax.set_yticks(positions)
        ax.set_yticklabels(strategies)
        ax.set_xlabel(label)
        ax.invert_yaxis()
    axes[-1].legend(title="agents", fontsize=8)
    fig.suptitle("Prioritized Planning: priority ordering ablation (32x32, 20%, 8 seeds)")
    fig.tight_layout()
    _save(fig, "priority_orders", directory)
    save_table(summary, "priority_orders_summary")


def plot_tradeoff(df: pd.DataFrame, directory: str) -> None:
    """Per-instance PP vs CBS trade-off (the central question of the study)."""
    wide = df.pivot_table(
        index="instance",
        columns="algorithm",
        values=["runtime_sec", "soc", "success"],
    )
    needed = {("runtime_sec", "Prioritized"), ("runtime_sec", "CBS")}
    if not needed.issubset(wide.columns):
        return
    sub = wide.dropna(subset=list(needed))
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    axes[0].scatter(
        sub[("runtime_sec", "Prioritized")],
        sub[("runtime_sec", "CBS")],
        s=22,
        alpha=0.7,
    )
    limit = max(
        sub[("runtime_sec", "Prioritized")].max(), sub[("runtime_sec", "CBS")].max()
    )
    axes[0].plot([1e-3, limit * 1.2], [1e-3, limit * 1.2], "k--", linewidth=0.8)
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("Prioritized Planning runtime (s)")
    axes[0].set_ylabel("CBS runtime (s)")
    axes[0].set_title("Runtime per instance (below the line CBS is faster)")

    if ("soc", "Prioritized") in sub and ("soc", "CBS") in sub:
        both = sub.dropna(subset=[("soc", "Prioritized"), ("soc", "CBS")])
        axes[1].scatter(
            both[("soc", "CBS")],
            both[("soc", "Prioritized")],
            s=22,
            alpha=0.7,
            color="#2a9d8f",
        )
        low = min(both[("soc", "CBS")].min(), both[("soc", "Prioritized")].min())
        high = max(both[("soc", "CBS")].max(), both[("soc", "Prioritized")].max())
        axes[1].plot([low, high], [low, high], "k--", linewidth=0.8)
        axes[1].set_xlabel("CBS sum of costs")
        axes[1].set_ylabel("Prioritized sum of costs")
        axes[1].set_title("Solution quality (above the line PP costs more)")
    fig.suptitle("Per-instance runtime/quality trade-off")
    _save(fig, "tradeoff", directory)


def plot_conflict_analysis(df: pd.DataFrame, directory: str) -> None:
    """How initial conflict count predicts planning difficulty."""
    data = df.dropna(subset=["conflicts_initial"])
    if data.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    sns.scatterplot(
        data=data,
        x="conflicts_initial",
        y="runtime_sec",
        hue="algorithm",
        ax=axes[0],
        alpha=0.7,
    )
    axes[0].set_yscale("log")
    axes[0].set_title("Planning time vs. conflicts in the independent plan")
    sns.boxplot(
        data=data,
        x="distribution" if "distribution" in data else "algorithm",
        y="conflicts_initial",
        hue="algorithm" if "distribution" in data else None,
        ax=axes[1],
    )
    axes[1].set_title("Conflicts generated by the naive baseline")
    fig.tight_layout()
    _save(fig, "conflict_analysis", directory)


def make_all_plots(directory: str = FIGURE_DIR) -> List[str]:
    os.makedirs(directory, exist_ok=True)
    results = load_results()
    produced: List[str] = []
    plotters = {
        "scalability": plot_scalability,
        "density": plot_density,
        "structure": plot_structure,
        "distribution": plot_distribution,
        "gridsize": plot_gridsize,
        "priority_orders": plot_priority_orders,
    }
    for suite, plotter in plotters.items():
        df = results[results["suite"] == suite] if "suite" in results else pd.DataFrame()
        if df.empty:
            print(f"[plots] skipping {suite}: no data")
            continue
        print(f"[plots] {suite}")
        try:
            plotter(df, directory)
        except Exception as exc:  # a broken figure must not abort the run
            print(f"[plots]   FAILED {suite}: {type(exc).__name__}: {exc}")
    if not results.empty:
        for name, plotter, suite in (
            ("tradeoff", plot_tradeoff, "scalability"),
            ("conflict_analysis", plot_conflict_analysis, "distribution"),
        ):
            try:
                plotter(results[results["suite"] == suite], directory)
            except Exception as exc:
                print(f"[plots]   FAILED {name}: {type(exc).__name__}: {exc}")
    return produced
