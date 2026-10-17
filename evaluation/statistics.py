"""Statistical aggregation of the raw experiment rows.

All quantities reported in the report come from here, so the definitions are in
one place:

* **success rate** -- fraction of runs with ``success == 1`` (a run counts as a
  success only if it returned a plan that *we* re-validated as conflict-free).
* **runtime** -- wall-clock planning time in seconds (mean and standard
  deviation over the repetitions; timeouts contribute their full budget).
* **SOC / makespan** -- reported **only over successful runs**.  This is a
  success-conditioned quantity, which is biased when success rates differ, so
  every table shows the success rate next to it (see the report, Limitations).
* **soc_gap** -- ``SOC / SIC - 1`` where SIC is the sum of individually optimal
  costs: a scale-free measure of solution quality (0 == provably optimal).
"""

from __future__ import annotations

import math
import os
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
RAW_DIR = os.path.join(RESULTS_DIR, "raw")
TABLE_DIR = os.path.join(RESULTS_DIR, "tables")

NUMERIC = [
    "success",
    "runtime_sec",
    "soc",
    "makespan",
    "soc_gap",
    "conflicts_initial",
    "conflicts_final",
    "low_level_calls",
    "low_level_expansions",
    "high_level_expansions",
]


def load_results(names: Optional[Sequence[str]] = None, raw_dir: str = RAW_DIR) -> pd.DataFrame:
    """Load one or all raw result files (JSONL preferred, CSV as fallback)."""
    # Prefer the append-only JSONL over the CSV view of the same suite: both are
    # written, and reading both would silently duplicate every run.
    by_stem: Dict[str, List[str]] = {}
    for base in sorted(os.listdir(raw_dir)):
        stem, ext = os.path.splitext(base)
        if ext in (".jsonl", ".csv"):
            by_stem.setdefault(stem, []).append(ext)
    frames = []
    for stem, extensions in sorted(by_stem.items()):
        if names and stem not in names:
            continue
        ext = ".jsonl" if ".jsonl" in extensions else ".csv"
        path = os.path.join(raw_dir, stem + ext)
        frames.append(
            pd.read_json(path, lines=True) if ext == ".jsonl" else pd.read_csv(path)
        )
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True, sort=False)
    for column in NUMERIC:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    # pandas' JSON float parser can turn 0.3 into 0.30000000000000004, which
    # would split a factor level in two when grouping; round the factor columns.
    for column in ("num_agents", "seed", "width", "height"):
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int64")
    for column in (
        "obstacle_density_requested",
        "obstacle_density",
        "obstacle_density_measured",
        "time_limit",
    ):
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").round(4)
    return df


def ci95(values: pd.Series) -> float:
    """Half-width of a two-sided 95% Student-t confidence interval for a mean."""
    values = pd.Series(values).dropna()
    if len(values) < 2:
        return float("nan")
    # The suite cells commonly have only 8--12 seeds, where using 1.96
    # understates uncertainty. SciPy is already a declared analysis dependency.
    from scipy.stats import t

    critical_value = t.ppf(0.975, df=len(values) - 1)
    return float(critical_value * values.std(ddof=1) / math.sqrt(len(values)))


def summarise(df: pd.DataFrame, by: Sequence[str]) -> pd.DataFrame:
    """Aggregate runs grouped by ``by`` (typically algorithm x condition)."""
    rows = []
    for key, group in df.groupby(list(by), dropna=False):
        key = key if isinstance(key, tuple) else (key,)
        record = dict(zip(by, key))
        solved = group[group["success"] == 1]
        record["n"] = len(group)
        record["success_rate"] = group["success"].mean()
        record["timeout_rate"] = (group["status"] == "timeout").mean()
        record["failure_rate"] = (
            group["status"].isin(["no_solution", "invalid", "error"])
        ).mean()
        record["runtime_mean"] = group["runtime_sec"].mean()
        record["runtime_std"] = group["runtime_sec"].std(ddof=1)
        record["runtime_median"] = group["runtime_sec"].median()
        record["runtime_ci95"] = ci95(group["runtime_sec"])
        record["soc_mean"] = solved["soc"].mean() if len(solved) else np.nan
        record["soc_std"] = solved["soc"].std(ddof=1) if len(solved) > 1 else np.nan
        record["makespan_mean"] = solved["makespan"].mean() if len(solved) else np.nan
        record["soc_gap_mean"] = solved["soc_gap"].mean() if len(solved) else np.nan
        record["soc_gap_max"] = solved["soc_gap"].max() if len(solved) else np.nan
        record["conflicts_initial_mean"] = (
            group["conflicts_initial"].mean() if "conflicts_initial" in group else np.nan
        )
        record["low_level_calls_mean"] = (
            solved["low_level_calls"].mean() if len(solved) else np.nan
        )
        record["high_level_expansions_mean"] = (
            group["high_level_expansions"].mean() if len(group) else np.nan
        )
        rows.append(record)
    return pd.DataFrame(rows).sort_values(list(by)).reset_index(drop=True)


def paired_comparison(
    df: pd.DataFrame,
    algorithm_a: str,
    algorithm_b: str,
    metric: str,
    instance_keys: Sequence[str] = ("instance",),
    both_successful: bool = True,
) -> Dict[str, object]:
    """Paired comparison of two algorithms on the *same* instances.

    Pairing removes instance difficulty from the comparison, which is essential
    here: instances are shared across algorithms by construction.  Returns the
    mean paired difference, its standard deviation, the fraction of instances
    where A is better, and (when SciPy is available) a Wilcoxon signed-rank
    p-value.
    """
    a = df[df["algorithm"] == algorithm_a].set_index(list(instance_keys))
    b = df[df["algorithm"] == algorithm_b].set_index(list(instance_keys))
    common = a.index.intersection(b.index)
    a, b = a.loc[common], b.loc[common]
    if both_successful:
        keep = (a["success"] == 1) & (b["success"] == 1)
        a, b = a[keep], b[keep]
    diff = (a[metric] - b[metric]).dropna()
    result: Dict[str, object] = {
        "metric": metric,
        "algorithm_a": algorithm_a,
        "algorithm_b": algorithm_b,
        "n_pairs": int(len(diff)),
        "mean_difference": float(diff.mean()) if len(diff) else float("nan"),
        "std_difference": float(diff.std(ddof=1)) if len(diff) > 1 else float("nan"),
        "a_better_fraction": float((diff < 0).mean()) if len(diff) else float("nan"),
    }
    if len(diff) > 5:
        try:
            from scipy import stats

            stat, pvalue = stats.wilcoxon(diff, zero_method="wilcox", alternative="two-sided")
            result["wilcoxon_stat"] = float(stat)
            result["wilcoxon_p"] = float(pvalue)
        except Exception:  # pragma: no cover - scipy optional
            result["wilcoxon_p"] = float("nan")
    return result


def success_table(df: pd.DataFrame, index: str, columns: str = "algorithm") -> pd.DataFrame:
    return df.pivot_table(index=index, columns=columns, values="success", aggfunc="mean")


def mean_table(
    df: pd.DataFrame, value: str, index: str, columns: str = "algorithm", solved_only: bool = False
) -> pd.DataFrame:
    data = df[df["success"] == 1] if solved_only else df
    return data.pivot_table(index=index, columns=columns, values=value, aggfunc="mean")


def to_markdown(df: pd.DataFrame, float_fmt: str = "{:.3f}") -> str:
    """Render a DataFrame as a Markdown table (small local implementation).

    ``DataFrame.to_markdown`` needs the optional ``tabulate`` package; the
    report tables are simple enough to format here, which keeps the dependency
    list short.
    """
    frame = df.copy()
    if not isinstance(frame.index, pd.RangeIndex):
        frame = frame.reset_index()
    header = [str(c) for c in frame.columns]
    rows: List[List[str]] = []
    for _, record in frame.iterrows():
        row = []
        for value in record:
            if isinstance(value, float) and not pd.isna(value):
                row.append(float_fmt.format(value))
            else:
                row.append("" if pd.isna(value) else str(value))
        rows.append(row)
    widths = [
        max(len(header[i]), *(len(r[i]) for r in rows)) if rows else len(header[i])
        for i in range(len(header))
    ]
    def line(cells: Sequence[str]) -> str:
        return "| " + " | ".join(c.ljust(w) for c, w in zip(cells, widths)) + " |"

    out = [line(header), "| " + " | ".join("-" * w for w in widths) + " |"]
    out.extend(line(r) for r in rows)
    return "\n".join(out)


def save_table(df: pd.DataFrame, name: str, directory: str = TABLE_DIR) -> str:
    os.makedirs(directory, exist_ok=True)
    csv_path = os.path.join(directory, f"{name}.csv")
    md_path = os.path.join(directory, f"{name}.md")
    df.to_csv(csv_path)
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(to_markdown(df) + "\n")
    return csv_path
