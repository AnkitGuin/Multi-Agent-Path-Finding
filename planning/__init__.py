"""Planning layer: the four MAPF algorithms plus conflict detection.

Importing this package gives access to the planner registry:

    from planning import PLANNERS, solve
    result = solve(scenario, "CBS", time_limit=30)

Adding an algorithm means adding one entry to :data:`PLANNERS`; nothing in the
evaluation or UI layer needs to change.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from environment.grid import Scenario

from .cbs import solve_cbs
from .common import PlannerResult
from .independent import solve_independent
from .prioritized import PRIORITY_ORDERS, solve_prioritized, solve_prioritized_with_restarts


def _solve_independent(scenario: Scenario, **kwargs) -> PlannerResult:
    return solve_independent(scenario.grid, scenario.starts, scenario.goals, **kwargs)


def _solve_prioritized(scenario: Scenario, **kwargs) -> PlannerResult:
    return solve_prioritized(scenario.grid, scenario.starts, scenario.goals, **kwargs)


def _solve_cbs(scenario: Scenario, **kwargs) -> PlannerResult:
    return solve_cbs(scenario.grid, scenario.starts, scenario.goals, **kwargs)


def _solve_pp_restarts(scenario: Scenario, **kwargs) -> PlannerResult:
    return solve_prioritized_with_restarts(scenario.grid, scenario.starts, scenario.goals, **kwargs)


#: name -> callable(scenario, **kwargs) -> PlannerResult
PLANNERS: Dict[str, Callable[..., PlannerResult]] = {
    "Independent": _solve_independent,
    "Prioritized": _solve_prioritized,
    "CBS": _solve_cbs,
    "Prioritized+restarts": _solve_pp_restarts,
}

#: Algorithms that guarantee a conflict-free plan when they succeed.
COMPLETE_PLANNERS = ("CBS",)
#: Algorithms that must appear in the core comparison.
CORE_ALGORITHMS = ("Independent", "Prioritized", "CBS")


def solve(scenario: Scenario, algorithm: str, **kwargs) -> PlannerResult:
    """Run ``algorithm`` on ``scenario`` (unknown names raise ``ValueError``)."""
    try:
        planner = PLANNERS[algorithm]
    except KeyError as exc:
        raise ValueError(
            f"unknown algorithm {algorithm!r}; available: {sorted(PLANNERS)}"
        ) from exc
    return planner(scenario, **kwargs)


__all__ = [
    "PLANNERS",
    "CORE_ALGORITHMS",
    "COMPLETE_PLANNERS",
    "PRIORITY_ORDERS",
    "PlannerResult",
    "solve",
    "solve_cbs",
    "solve_independent",
    "solve_prioritized",
    "solve_prioritized_with_restarts",
]
