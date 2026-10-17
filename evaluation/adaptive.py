"""OPTIONAL EXTENSION -- adaptive selection between Prioritized Planning and CBS.

This is *not* part of the reproduced literature: Independent A*, Prioritized
Planning and CBS are standard algorithms; this module is the project's own
small investigation of the extension question posed in the brief:

    "Can the characteristics of a MAPF instance be used to select an
     appropriate coordination strategy automatically?"

Formulation
-----------
The two candidates have complementary failure modes, which is what makes
selection potentially useful:

* Prioritized Planning is fast but incomplete and suboptimal.
* CBS is optimal but its runtime is highly variable and it hits the time budget
  on crowded instances.

We define the utility of a run as a lexicographic score -- **first succeed,
then be optimal, then be fast**:

    score = (solved, -soc_gap if solved else 0, -runtime if solved else 0)

The *oracle* picks the better algorithm per instance under this utility.  The
selector only sees cheap features of the instance (never the outcome) and is
trained to imitate the oracle.  Because the oracle label depends on measured
outcomes, all evaluation is done with k-fold cross-validation on a pool of
instances that is disjoint from the suites used for the main analysis.

Two selectors are implemented, both deliberately lightweight and inspectable:

:class:`ThresholdSelector`
    A one- or two-feature rule ("use CBS iff agents <= t1 and conflicts <= t2")
    fitted by exhaustive search.  Easy to state in a viva and easy to falsify.
:class:`LogisticSelector`
    Logistic regression (standardised features, gradient descent in NumPy) on
    the same features -- a smooth, probabilistic version of the same idea.

They are compared against the two fixed strategies (always PP, always CBS) and
against the oracle (an upper bound that is not achievable in practice).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

FEATURES: List[str] = [
    "num_agents",
    "obstacle_density",
    "agent_density",
    "mean_start_goal_manhattan",
    "conflicts_initial",
]

#: Features that can be computed *before* any coordinated planning (the whole
#: point: the selector must be cheap and must not require running CBS).
CHEAP_FEATURES: List[str] = [
    "num_agents",
    "obstacle_density",
    "agent_density",
    "mean_start_goal_manhattan",
    "conflicts_initial",
]


# --------------------------------------------------------------------------- #
#  Feature table
# --------------------------------------------------------------------------- #
def build_feature_table(
    df: pd.DataFrame, algorithms: Sequence[str] = ("Prioritized", "CBS")
) -> pd.DataFrame:
    """Collapse per-run rows into one row per instance with both outcomes.

    ``conflicts_initial`` is obtained from the Independent A* plan, which costs
    one single-agent A* per agent -- negligible next to either planner.
    """
    if df.empty:
        return pd.DataFrame()
    base = df.drop_duplicates(subset=["instance"]).set_index("instance")
    table = pd.DataFrame(index=base.index)
    for feature in CHEAP_FEATURES:
        if feature in base.columns:
            table[feature] = pd.to_numeric(base[feature], errors="coerce")
    for algorithm in algorithms:
        sub = df[df["algorithm"] == algorithm].set_index("instance")
        prefix = algorithm.lower().replace("+", "_").replace(" ", "_")
        table[f"{prefix}_success"] = sub["success"].astype(float)
        table[f"{prefix}_runtime"] = pd.to_numeric(sub["runtime_sec"], errors="coerce")
        table[f"{prefix}_soc"] = pd.to_numeric(sub["soc"], errors="coerce")
        table[f"{prefix}_soc_gap"] = pd.to_numeric(sub["soc_gap"], errors="coerce")
        table[f"{prefix}_timeout"] = (sub["status"] == "timeout").astype(float)
    return table.dropna(subset=[c for c in table.columns if c.startswith("prioritized")])


#: A plan that costs more than this fraction above the SIC lower bound is
#: treated as "no quality left" when normalising the quality term.
GAP_CAP = 0.15


def utility(row: pd.Series, algorithm: str, budget: float, quality_weight: float = 0.5) -> float:
    """Weighted utility of using ``algorithm`` on one instance.

    The utility is deliberately a *parameterised* trade-off rather than one
    hand-picked objective, because which strategy "wins" depends on how the
    application values optimality relative to speed:

        U = solved * [ alpha * quality + (1 - alpha) * speed ]

    with ``quality = 1 - min(gap, GAP_CAP) / GAP_CAP`` and
    ``speed = 1 - min(runtime, budget) / budget``.  Failure dominates everything
    (a missing plan has utility 0), which is the right model for a warehouse:
    an unsolved instance is a fleet that does not move.

    ``alpha`` is swept in the evaluation: reporting a single number would hide
    the fact that the ranking of the strategies flips with the weighting.
    """
    prefix = algorithm.lower().replace("+", "_").replace(" ", "_")
    solved = row.get(f"{prefix}_success", 0.0) > 0
    if not solved:
        return 0.0
    gap = row.get(f"{prefix}_soc_gap", np.nan)
    gap = 0.0 if pd.isna(gap) else float(gap)
    runtime = row.get(f"{prefix}_runtime", budget)
    runtime = budget if pd.isna(runtime) else min(float(runtime), budget)
    quality = 1.0 - min(gap, GAP_CAP) / GAP_CAP
    speed = 1.0 - runtime / budget
    return quality_weight * quality + (1.0 - quality_weight) * speed


def oracle_labels(table: pd.DataFrame, budget: float) -> pd.Series:
    """Which algorithm *should* have been used, knowing both outcomes."""
    score_pp = table.apply(lambda r: utility(r, "Prioritized", budget), axis=1)
    score_cbs = table.apply(lambda r: utility(r, "CBS", budget), axis=1)
    return (score_cbs > score_pp).astype(int)  # 1 == prefer CBS


# --------------------------------------------------------------------------- #
#  Selector 1: interpretable threshold rule
# --------------------------------------------------------------------------- #
@dataclass
class ThresholdSelector:
    """Use CBS iff ``feature <= threshold`` (optionally ANDed with a second rule).

    Fitted by exhaustive search over features, directions and quantile
    thresholds, maximising agreement with the oracle.
    """

    feature: Optional[str] = None
    threshold: float = 0.0
    direction: str = "below"  # "below": use CBS when feature <= threshold
    feature2: Optional[str] = None
    threshold2: float = 0.0
    direction2: str = "below"
    train_accuracy: float = 0.0

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "ThresholdSelector":
        best = (0.0, None)
        candidates = [f for f in FEATURES if f in X.columns]
        for feature in candidates:
            values = X[feature].dropna()
            for threshold in np.unique(np.quantile(values, np.linspace(0.05, 0.95, 19))):
                for direction, mask in (
                    ("below", (X[feature] <= threshold).astype(int)),
                    ("above", (X[feature] >= threshold).astype(int)),
                ):
                    accuracy = float((mask == y).mean())
                    if accuracy > best[0]:
                        best = (accuracy, (feature, threshold, direction, None, 0.0, ""))
        # Optional second conjunct that only fires where the first rule says CBS.
        if best[1] is not None:
            feature, threshold, direction, _, _, _ = best[1]
            base = (X[feature] <= threshold) if direction == "below" else (X[feature] >= threshold)
            for feature2 in candidates:
                if feature2 == feature:
                    continue
                values = X.loc[base, feature2].dropna()
                if len(values) < 5:
                    continue
                for threshold2 in np.unique(np.quantile(values, np.linspace(0.1, 0.9, 9))):
                    for direction2, mask2 in (
                        ("below", (X[feature2] <= threshold2).astype(int)),
                        ("above", (X[feature2] >= threshold2).astype(int)),
                    ):
                        combined = (base & mask2.astype(bool)).astype(int)
                        accuracy = float((combined == y).mean())
                        if accuracy > best[0] + 1e-9:
                            best = (
                                accuracy,
                                (feature, threshold, direction, feature2, threshold2, direction2),
                            )
        self.train_accuracy = best[0]
        if best[1] is not None:
            (
                self.feature,
                self.threshold,
                self.direction,
                self.feature2,
                self.threshold2,
                self.direction2,
            ) = best[1]
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.feature is None:
            return np.zeros(len(X), dtype=int)
        op = (lambda a, b: a <= b) if self.direction == "below" else (lambda a, b: a >= b)
        mask = op(X[self.feature].fillna(np.inf), self.threshold)
        if self.feature2 is not None:
            op2 = (lambda a, b: a <= b) if self.direction2 == "below" else (lambda a, b: a >= b)
            mask = mask & op2(X[self.feature2].fillna(np.inf), self.threshold2)
        return mask.astype(int).to_numpy()

    def describe(self) -> str:
        if self.feature is None:
            return "always Prioritized"
        symbol1 = "<=" if self.direction == "below" else ">="
        rule = f"use CBS iff {self.feature} {symbol1} {self.threshold:.3g}"
        if self.feature2 is not None:
            symbol2 = "<=" if self.direction2 == "below" else ">="
            rule += f" AND {self.feature2} {symbol2} {self.threshold2:.3g}"
        return rule + f"  (train agreement {self.train_accuracy:.1%})"


# --------------------------------------------------------------------------- #
#  Selector 2: logistic regression (NumPy)
# --------------------------------------------------------------------------- #
@dataclass
class LogisticSelector:
    """Logistic regression trained with plain gradient descent (no sklearn)."""

    learning_rate: float = 0.1
    epochs: int = 800
    l2: float = 1e-3
    weights: Optional[np.ndarray] = None
    mean: Optional[np.ndarray] = None
    std: Optional[np.ndarray] = None
    feature_names: List[str] = field(default_factory=list)

    def _design(self, X: pd.DataFrame, fit: bool = False) -> np.ndarray:
        values = X[self.feature_names].astype(float).to_numpy()
        values = np.nan_to_num(values, nan=0.0)
        if fit:
            self.mean = values.mean(axis=0)
            self.std = values.std(axis=0) + 1e-8
        values = (values - self.mean) / self.std
        return np.hstack([np.ones((len(values), 1)), values])

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "LogisticSelector":
        self.feature_names = [f for f in FEATURES if f in X.columns]
        design = self._design(X, fit=True)
        target = y.to_numpy(dtype=float)
        self.weights = np.zeros(design.shape[1])
        for _ in range(self.epochs):
            logits = design @ self.weights
            probabilities = 1.0 / (1.0 + np.exp(-np.clip(logits, -30, 30)))
            gradient = design.T @ (probabilities - target) / len(target)
            gradient[1:] += self.l2 * self.weights[1:]
            self.weights -= self.learning_rate * gradient
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        design = self._design(X)
        logits = design @ self.weights
        return 1.0 / (1.0 + np.exp(-np.clip(logits, -30, 30)))

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return (self.predict_proba(X) >= 0.5).astype(int)

    def describe(self) -> str:
        if self.weights is None:
            return "unfitted"
        terms = ", ".join(
            f"{w:+.2f}·{name}" for name, w in zip(self.feature_names, self.weights[1:])
        )
        return f"logistic: P(CBS) = sigmoid({self.weights[0]:+.2f} {terms})"


# --------------------------------------------------------------------------- #
#  Evaluation
# --------------------------------------------------------------------------- #
def evaluate_strategy(
    table: pd.DataFrame,
    choices: pd.Series,
    budget: float,
    name: str,
    quality_weights: Sequence[float] = (0.25, 0.5, 0.75),
) -> Dict[str, float]:
    """Score a strategy: pick one algorithm per instance, then measure."""
    runtimes, solved, gaps = [], [], []
    utilities: Dict[float, List[float]] = {w: [] for w in quality_weights}
    for instance, choice in choices.items():
        row = table.loc[instance]
        algorithm = "CBS" if choice == 1 else "Prioritized"
        prefix = "cbs" if choice == 1 else "prioritized"
        runtimes.append(min(row.get(f"{prefix}_runtime", budget) or budget, budget))
        solved.append(row.get(f"{prefix}_success", 0.0))
        gap = row.get(f"{prefix}_soc_gap", np.nan)
        gaps.append(gap if not pd.isna(gap) and row.get(f"{prefix}_success", 0) > 0 else np.nan)
        for weight in quality_weights:
            utilities[weight].append(utility(row, algorithm, budget, weight))
    record: Dict[str, float] = {
        "strategy": name,
        "success_rate": float(np.mean(solved)),
        "mean_runtime": float(np.mean(runtimes)),
        "mean_soc_gap": float(np.nanmean(gaps)) if any(not np.isnan(g) for g in gaps) else np.nan,
    }
    for weight in quality_weights:
        record[f"utility_a{weight:.2f}"] = float(np.mean(utilities[weight]))
    return record


def cross_validate(
    table: pd.DataFrame,
    budget: float = 10.0,
    folds: int = 5,
    seed: int = 0,
) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """K-fold comparison of fixed strategies, both selectors and the oracle."""
    y = oracle_labels(table, budget)
    X = table[[f for f in FEATURES if f in table.columns]]
    rng = np.random.default_rng(seed)
    indices = rng.permutation(len(table))
    assignments = np.zeros(len(table), dtype=int)
    descriptions: Dict[str, str] = {}
    fold_rules: List[str] = []

    for k in range(folds):
        test_idx = indices[k::folds]
        train_idx = np.setdiff1d(indices, test_idx)
        train_X, train_y = X.iloc[train_idx], y.iloc[train_idx]
        selector = ThresholdSelector().fit(train_X, train_y)
        fold_rules.append(selector.describe())
        assignments[test_idx] = selector.predict(X.iloc[test_idx])

    choices_threshold = pd.Series(assignments, index=table.index)
    agreement_threshold = float((choices_threshold == y).mean())
    descriptions["Adaptive (threshold rule)"] = (
        f"{folds}-fold CV; cross-validated oracle agreement {agreement_threshold:.1%} "
        f"(always-PP baseline {1 - float(y.mean()):.1%}); example rule: {fold_rules[0]}"
    )

    assignments = np.zeros(len(table), dtype=int)
    for k in range(folds):
        test_idx = indices[k::folds]
        train_idx = np.setdiff1d(indices, test_idx)
        model = LogisticSelector().fit(X.iloc[train_idx], y.iloc[train_idx])
        assignments[test_idx] = model.predict(X.iloc[test_idx])
    choices_logistic = pd.Series(assignments, index=table.index)
    agreement_logistic = float((choices_logistic == y).mean())
    full_logistic = LogisticSelector().fit(X, y)
    descriptions["Adaptive (logistic)"] = (
        full_logistic.describe()
        + f"  [cross-validated oracle agreement {agreement_logistic:.1%}]"
    )

    rows = [
        evaluate_strategy(table, pd.Series(0, index=table.index), budget, "Always Prioritized"),
        evaluate_strategy(table, pd.Series(1, index=table.index), budget, "Always CBS"),
        evaluate_strategy(table, choices_threshold, budget, "Adaptive (threshold rule)"),
        evaluate_strategy(table, choices_logistic, budget, "Adaptive (logistic)"),
        evaluate_strategy(table, y, budget, "Oracle (unattainable)"),
    ]
    return pd.DataFrame(rows), descriptions


def feature_importance(table: pd.DataFrame, budget: float) -> pd.DataFrame:
    """Correlation of each feature with the oracle's preference (descriptive)."""
    y = oracle_labels(table, budget)
    rows = []
    for feature in FEATURES:
        if feature not in table.columns:
            continue
        values = pd.to_numeric(table[feature], errors="coerce")
        mask = values.notna() & y.notna()
        if mask.sum() < 5:
            continue
        correlation = float(np.corrcoef(values[mask], y[mask])[0, 1])
        rows.append(
            {
                "feature": feature,
                "correlation_with_oracle": correlation,
                "mean_when_CBS_preferred": float(values[mask & (y == 1)].mean()),
                "mean_when_PP_preferred": float(values[mask & (y == 0)].mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("correlation_with_oracle", key=abs, ascending=False)
