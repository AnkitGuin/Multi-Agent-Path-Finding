#!/usr/bin/env python3
"""Render the report's "money figure": one instance, all three strategies.

    python scripts/make_example_figure.py --agents 12 --seed 7

Writes ``results/figures/example_comparison.png`` (three panels, same instance)
and ``results/figures/example_independent_conflicts.png`` (the naive plan with
its collisions highlighted).
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from environment.benchmarks import export_instance  # noqa: E402
from environment.generators import generate_scenario  # noqa: E402
from evaluation.metrics import sum_of_individual_costs  # noqa: E402
from planning import solve  # noqa: E402
from visualization.plots import FIGURE_DIR as _  # noqa: E402  (kept for import order)
from visualization.render import (  # noqa: E402
    FIGURE_DIR,
    conflict_cells,
    render_algorithm_comparison,
    render_plan,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, default=32)
    parser.add_argument("--height", type=int, default=32)
    parser.add_argument("--agents", type=int, default=12)
    parser.add_argument("--density", type=float, default=0.2)
    parser.add_argument("--structure", default="rooms")
    parser.add_argument("--distribution", default="uniform")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--time-limit", type=float, default=30.0)
    args = parser.parse_args()

    scenario = generate_scenario(
        width=args.width,
        height=args.height,
        num_agents=args.agents,
        obstacle_density=args.density,
        structure=args.structure,
        distribution=args.distribution,
        seed=args.seed,
    )
    sic = sum_of_individual_costs(scenario.grid, scenario.starts, scenario.goals)

    paths, stats = {}, {}
    for algorithm in ("Independent", "Prioritized", "CBS"):
        result = solve(scenario, algorithm, time_limit=args.time_limit)
        paths[algorithm] = result.paths
        stats[algorithm] = (
            f"{result.status}, {result.runtime_sec * 1000:.0f} ms, "
            f"SOC={result.soc}, gap={0.0 if not result.soc else result.soc / sic - 1:.1%}"
        )
        print(f"{algorithm:12s} {stats[algorithm]}")

    os.makedirs(FIGURE_DIR, exist_ok=True)
    render_algorithm_comparison(
        scenario,
        paths,
        stats,
        out=os.path.join(FIGURE_DIR, "example_comparison.png"),
    )
    independent_conflicts = conflict_cells(paths["Independent"])
    render_plan(
        scenario,
        paths=paths["Independent"],
        conflicts=independent_conflicts,
        title=(
            f"Independent A*: {len(independent_conflicts)} collisions "
            f"(red) — the coordination burden of this instance"
        ),
        out=os.path.join(FIGURE_DIR, "example_independent_conflicts.png"),
    )
    exported = export_instance(
        scenario, os.path.join(ROOT, "data", "benchmarks"), stem="example_rooms_a12"
    )
    print(f"figures -> {FIGURE_DIR}")
    print(f"instance exported in MovingAI format -> {exported}")


if __name__ == "__main__":
    main()
