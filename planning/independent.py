"""Independent A* --- the deliberately naive baseline.

Every agent is routed by a plain single-agent A* that completely ignores all
other agents.  The resulting joint plan is usually *not* conflict-free; that is
the point.  Independent A* serves two purposes in this study:

1. It quantifies how much coordination an instance actually needs (the number of
   conflicts it produces is the "initial conflict count" feature used later).
2. Its sum of costs is the **sum of individual costs (SIC)**, a valid lower
   bound on the optimal SOC and hence the yardstick for solution quality.

It never "fails" because of other agents; it only fails if a goal is genuinely
unreachable in the static map.
"""

from __future__ import annotations

import time
from typing import List, Optional

from environment.grid import Cell, GridMap

from .astar import astar, build_heuristic
from .collisions import count_conflicts
from .common import (
    STATUS_CONFLICT,
    STATUS_NO_SOLUTION,
    STATUS_OK,
    STATUS_TIMEOUT,
    PlannerResult,
)

ALGORITHM_NAME = "Independent"


def solve_independent(
    grid: GridMap,
    starts: List[Cell],
    goals: List[Cell],
    heuristic_kind: str = "true_distance",
    time_limit: Optional[float] = None,
    initial_conflicts: Optional[int] = None,
) -> PlannerResult:
    """Plan each agent independently and report the resulting joint plan.

    ``time_limit`` is accepted for interface uniformity: a plain A* per agent is
    far too fast to hit any realistic budget, but the harness calls every
    planner the same way.
    """
    start_time = time.perf_counter()
    deadline = start_time + time_limit if time_limit is not None else None
    paths: List[List[Cell]] = []
    expansions = 0
    for start, goal in zip(starts, goals):
        path = astar(grid, start, goal, build_heuristic(grid, goal, heuristic_kind))
        if path is None:
            runtime = time.perf_counter() - start_time
            return PlannerResult(
                algorithm=ALGORITHM_NAME,
                success=False,
                status=STATUS_NO_SOLUTION,
                paths=[],
                runtime_sec=runtime,
                conflicts_final=-1,
                details={"reason": "goal unreachable in the static map"},
            )
        if deadline is not None and time.monotonic() > deadline:
            return PlannerResult(
                algorithm=ALGORITHM_NAME,
                success=False,
                status=STATUS_TIMEOUT,
                runtime_sec=time.perf_counter() - start_time,
                details={"reason": "time limit reached"},
            )
        paths.append(path)

    conflicts = count_conflicts(paths)
    runtime = time.perf_counter() - start_time
    return PlannerResult(
        algorithm=ALGORITHM_NAME,
        success=(conflicts == 0),
        status=STATUS_OK if conflicts == 0 else STATUS_CONFLICT,
        paths=paths,
        runtime_sec=runtime,
        soc=sum(len(p) - 1 for p in paths),
        makespan=max(len(p) for p in paths) - 1,
        low_level_calls=len(paths),
        low_level_expansions=expansions,
        high_level_expansions=0,
        conflicts_initial=conflicts,
        conflicts_final=conflicts,
        details={"sic": sum(len(p) - 1 for p in paths)},
    )
