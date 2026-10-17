"""Prioritized Planning (PP).

Agents are planned **sequentially** in a fixed priority order.  Agent ``i``
receives the full space-time reservation table of agents ``1..i-1`` and must
avoid every reserved cell (at the reserved time) and every reserved edge; it may
not end up on a cell that an earlier agent occupies permanently (its goal).

Properties (Erdmann & Lozano-Pérez, 1987; Silver, 2005; van den Berg &
Overmars, 2005):

* **Complete only in a weak sense.**  If a *priority order* that admits a
  solution exists, PP can find it, but for a *fixed* order PP may fail even
  though the instance is solvable.  This is exactly the failure mode we measure
  (``status == no_solution`` while CBS succeeds).
* **Not optimal.**  A high-priority agent never yields, so the joint cost can be
  arbitrarily far from optimal.
* **Polynomial per agent** -- one time-expanded A* each, so it is fast; the
  price is solution quality and completeness.

Priority orders implemented here
--------------------------------
``index``      the given agent order (the generator produces agents in random
               order, so this is effectively a random order -- and it is the
               default because it is the honest "no tuning" choice).
``random``     explicitly shuffled with the instance RNG.
``reverse``    reverse of ``index``.
``longest_first``  descending individual optimal cost (longest routes first).
``shortest_first`` ascending individual optimal cost.
``most_conflicting_first``  descending conflict count in the independent plan.
``least_conflicting_first`` ascending conflict count in the independent plan.
"""

from __future__ import annotations

import random
import time
from typing import Dict, List, Optional, Sequence

from environment.grid import Cell, GridMap

from .astar import (
    ReservationTable,
    ReservationVerifier,
    SearchResult,
    astar,
    build_heuristic,
)
from .collisions import conflicts_per_agent, count_conflicts, detect_conflicts
from .common import STATUS_CONFLICT, STATUS_NO_SOLUTION, STATUS_OK, STATUS_TIMEOUT, PlannerResult

ALGORITHM_NAME = "Prioritized"

PRIORITY_ORDERS = (
    "index",
    "random",
    "reverse",
    "longest_first",
    "shortest_first",
    "most_conflicting_first",
    "least_conflicting_first",
)


def _priority_order(
    order: str,
    grid: GridMap,
    starts: Sequence[Cell],
    goals: Sequence[Cell],
    rng: Optional[random.Random],
) -> List[int]:
    n = len(starts)
    if order == "index":
        return list(range(n))
    if order == "reverse":
        return list(reversed(range(n)))
    if order == "random":
        idx = list(range(n))
        (rng or random.Random(0)).shuffle(idx)
        return idx
    if order in ("longest_first", "shortest_first"):
        costs = []
        for i, (start, goal) in enumerate(zip(starts, goals)):
            path = astar(grid, start, goal)
            costs.append((len(path) - 1) if path else 10 ** 6)
        idx = sorted(range(n), key=lambda i: costs[i])
        return list(reversed(idx)) if order == "longest_first" else idx
    if order in ("most_conflicting_first", "least_conflicting_first"):
        paths = [astar(grid, s, g) or [s] for s, g in zip(starts, goals)]
        counts = conflicts_per_agent(paths, n)
        idx = sorted(range(n), key=lambda i: counts[i])
        return list(reversed(idx)) if order == "most_conflicting_first" else idx
    raise ValueError(f"unknown priority order {order!r}")


def solve_prioritized(
    grid: GridMap,
    starts: List[Cell],
    goals: List[Cell],
    order: str = "index",
    rng: Optional[random.Random] = None,
    heuristic_kind: str = "true_distance",
    time_limit: Optional[float] = None,
    initial_conflicts: Optional[int] = None,
) -> PlannerResult:
    """Run Prioritized Planning for one priority order.

    ``time_limit`` is a wall-clock budget in seconds; when it expires the run is
    reported as ``timeout`` (a *budget* outcome, never rewritten as success).
    """
    started = time.perf_counter()
    deadline = started + time_limit if time_limit is not None else None

    priorities = _priority_order(order, grid, starts, goals, rng)
    heuristics = [build_heuristic(grid, goal, heuristic_kind) for goal in goals]
    table = ReservationTable()
    paths: List[Optional[List[Cell]]] = [None] * len(starts)
    low_level_calls = 0
    low_level_expansions = 0

    for agent in priorities:
        verifier = ReservationVerifier(table)
        result: SearchResult = _space_time_search(
            grid, starts[agent], goals[agent], verifier, heuristics[agent], deadline
        )
        low_level_calls += 1
        low_level_expansions += result.expansions
        if result.timed_out:
            return PlannerResult(
                algorithm=ALGORITHM_NAME,
                success=False,
                status=STATUS_TIMEOUT,
                runtime_sec=time.perf_counter() - started,
                low_level_calls=low_level_calls,
                low_level_expansions=low_level_expansions,
                conflicts_initial=initial_conflicts,
                priority_order=priorities,
                details={"failed_agent": agent, "planned_agents": len(paths)},
            )
        if result.path is None:
            return PlannerResult(
                algorithm=ALGORITHM_NAME,
                success=False,
                status=STATUS_NO_SOLUTION,
                runtime_sec=time.perf_counter() - started,
                low_level_calls=low_level_calls,
                low_level_expansions=low_level_expansions,
                conflicts_initial=initial_conflicts,
                priority_order=priorities,
                details={
                    "failed_agent": agent,
                    "reason": "no path avoiding higher-priority agents",
                },
            )
        paths[agent] = result.path
        table.add_path(result.path)

    final_paths = [p for p in paths if p is not None]
    conflicts = count_conflicts(final_paths)
    runtime = time.perf_counter() - started
    return PlannerResult(
        algorithm=ALGORITHM_NAME,
        success=(conflicts == 0),
        status=STATUS_OK if conflicts == 0 else STATUS_CONFLICT,
        paths=final_paths,
        runtime_sec=runtime,
        soc=sum(len(p) - 1 for p in final_paths),
        makespan=max(len(p) for p in final_paths) - 1,
        low_level_calls=low_level_calls,
        low_level_expansions=low_level_expansions,
        high_level_expansions=0,
        conflicts_initial=initial_conflicts,
        conflicts_final=conflicts,
        priority_order=priorities,
        details={"order": order},
    )


def _space_time_search(grid, start, goal, verifier, heuristic, deadline):
    from .astar import space_time_astar  # local import keeps module import cheap

    return space_time_astar(
        grid, start, goal, verifier=verifier, heuristic=heuristic, deadline=deadline
    )


def solve_prioritized_with_restarts(
    grid: GridMap,
    starts: List[Cell],
    goals: List[Cell],
    orders: Sequence[str] = ("index", "longest_first", "shortest_first"),
    heuristic_kind: str = "true_distance",
    time_limit: Optional[float] = None,
) -> PlannerResult:
    """Try several priority orders in sequence and keep the first success.

    This is a *documented extension* of plain PP (it is **not** the baseline):
    it trades extra runtime for a higher success rate, and it is the simplest
    possible answer to "PP failed but a solution exists".  It remains
    non-optimal and still incomplete.
    """
    started = time.perf_counter()
    best: Optional[PlannerResult] = None
    for k, order in enumerate(orders):
        remaining = None if time_limit is None else time_limit - (time.perf_counter() - started)
        if remaining is not None and remaining <= 0:
            break
        result = solve_prioritized(
            grid,
            starts,
            goals,
            order=order,
            heuristic_kind=heuristic_kind,
            time_limit=remaining,
            initial_conflicts=None,
        )
        result.details["restart_index"] = k
        if result.success:
            result.runtime_sec = time.perf_counter() - started
            result.algorithm = "Prioritized+restarts"
            return result
        if best is None or (not best.success and result.status == STATUS_TIMEOUT):
            best = result
    assert best is not None
    best.runtime_sec = time.perf_counter() - started
    best.algorithm = "Prioritized+restarts"
    best.details["attempts"] = list(orders)
    return best
