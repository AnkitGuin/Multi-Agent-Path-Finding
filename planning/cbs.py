"""Conflict-Based Search (CBS) --- Sharon et al. (2015), standard two-level CBS.

High level
----------
A best-first search over a **constraint tree**.  Each node holds one constraint
set per agent plus a shortest path per agent that satisfies it.  The node's cost
is the sum of costs (SOC).  If the joint plan of the cheapest node is
conflict-free, it is optimal and CBS stops.  Otherwise one conflict is picked
and *resolved by branching*: two children are generated, each adding a single
constraint for one of the two conflicting agents (a vertex constraint for a
vertex conflict, an edge constraint for a swap).  Because a feasible solution
must violate at least one of the two constraints, no solution is lost.

Low level
---------
:func:`~planning.astar.space_time_astar` with a
:class:`~planning.astar.ConstraintVerifier`: a time-expanded A* that respects
the agent's own constraints and uses the (admissible, consistent) true-distance
heuristic.  Only the re-planned agent's search is repeated, which is what makes
CBS dramatically cheaper than joint-state A*.

Guarantees
----------
CBS is **optimal** for SOC and **complete** (Sharon et al., 2015, Theorems 1-2)
provided the low level is complete.  Our low level bounds the time dimension
(``verifier.max_time + 2 * area + 8``), which is generous enough that it never
binds in practice, and the wall-clock budget can cut a run short -- both are
reported honestly as ``timeout`` rather than "unsolvable".

Deliberately *not* implemented (the brief asks for standard CBS first):
prioritising/merge & restart (ICBS), disjoint splitting, symmetry breaking,
CBSH, EECBS, or any other improvement.  The only deviation from the textbook
algorithm is the optional tie-break on the number of remaining conflicts among
nodes of equal SOC; it changes only the *order* in which equal-cost nodes are
expanded, never the optimal cost that CBS returns.
"""

from __future__ import annotations

import heapq
import itertools
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from environment.grid import Cell, GridMap

from .astar import (
    ConstraintVerifier,
    Constraints,
    SearchResult,
    astar,
    build_heuristic,
    space_time_astar,
)
from .collisions import EDGE, VERTEX, Conflict, count_conflicts, find_first_conflict
from .common import STATUS_NO_SOLUTION, STATUS_OK, STATUS_TIMEOUT, PlannerResult

ALGORITHM_NAME = "CBS"


@dataclass
class CBSNode:
    """A high-level (constraint-tree) node."""

    constraints: Dict[int, Constraints]
    paths: List[List[Cell]]
    cost: int
    conflicts: int = 0

    @property
    def soc(self) -> int:
        return self.cost

    @property
    def makespan(self) -> int:
        return max(len(p) for p in self.paths) - 1 if self.paths else 0


def solve_cbs(
    grid: GridMap,
    starts: List[Cell],
    goals: List[Cell],
    heuristic_kind: str = "true_distance",
    time_limit: Optional[float] = None,
    tie_break: bool = True,
    initial_conflicts: Optional[int] = None,
    max_high_level_expansions: Optional[int] = None,
) -> PlannerResult:
    """Standard CBS.  Returns an SOC-optimal, conflict-free joint plan."""
    started = time.perf_counter()
    deadline = started + time_limit if time_limit is not None else None
    n = len(starts)
    heuristics = [build_heuristic(grid, goal, heuristic_kind) for goal in goals]

    low_level_calls = 0
    low_level_expansions = 0

    # ---------------------------------------------------------------- root node
    root_paths: List[List[Cell]] = []
    for i in range(n):
        path = astar(grid, starts[i], goals[i], heuristics[i])
        if path is None:
            return PlannerResult(
                algorithm=ALGORITHM_NAME,
                success=False,
                status=STATUS_NO_SOLUTION,
                runtime_sec=time.perf_counter() - started,
                conflicts_initial=initial_conflicts,
                details={"reason": "goal unreachable in the static map", "agent": i},
            )
        root_paths.append(path)

    root = CBSNode(
        constraints={i: Constraints.empty() for i in range(n)},
        paths=root_paths,
        cost=sum(len(p) - 1 for p in root_paths),
        conflicts=count_conflicts(root_paths),
    )

    counter = itertools.count()
    open_heap: List[Tuple[int, int, int, CBSNode]] = [
        (root.cost, root.conflicts if tie_break else 0, next(counter), root)
    ]
    high_level_expansions = 0
    nodes_generated = 1

    while open_heap:
        if deadline is not None and time.monotonic() > deadline:
            return _timeout(started, low_level_calls, low_level_expansions, high_level_expansions, initial_conflicts)
        if max_high_level_expansions is not None and high_level_expansions >= max_high_level_expansions:
            return _timeout(started, low_level_calls, low_level_expansions, high_level_expansions, initial_conflicts)

        _, _, _, node = heapq.heappop(open_heap)
        high_level_expansions += 1

        conflict = find_first_conflict(node.paths)
        if conflict is None:
            runtime = time.perf_counter() - started
            return PlannerResult(
                algorithm=ALGORITHM_NAME,
                success=True,
                status=STATUS_OK,
                paths=node.paths,
                runtime_sec=runtime,
                soc=node.cost,
                makespan=node.makespan,
                low_level_calls=low_level_calls,
                low_level_expansions=low_level_expansions,
                high_level_expansions=high_level_expansions,
                conflicts_initial=initial_conflicts,
                conflicts_final=0,
                details={"nodes_generated": nodes_generated, "optimal_soc": True},
            )

        for agent, constraint in _split(conflict):
            child_constraints = dict(node.constraints)  # shallow: share unmodified sets
            own = node.constraints[agent].copy()
            if constraint[0] == VERTEX:
                _, cell, t = constraint
                if own.has_vertex(cell, t):
                    continue  # duplicate child, already represented by this node
                own.add_vertex(cell, t)
            else:
                _, u, v, t = constraint
                if own.has_edge(u, v, t):
                    continue
                own.add_edge(u, v, t)
            child_constraints[agent] = own

            result: SearchResult = space_time_astar(
                grid,
                starts[agent],
                goals[agent],
                verifier=ConstraintVerifier(own),
                heuristic=heuristics[agent],
                deadline=deadline,
            )
            low_level_calls += 1
            low_level_expansions += result.expansions
            if result.timed_out:
                return _timeout(
                    started, low_level_calls, low_level_expansions, high_level_expansions, initial_conflicts
                )
            if result.path is None:
                continue  # this branch is infeasible

            child_paths = list(node.paths)
            child_paths[agent] = result.path
            child = CBSNode(
                constraints=child_constraints,
                paths=child_paths,
                cost=sum(len(p) - 1 for p in child_paths),
                conflicts=count_conflicts(child_paths) if tie_break else 0,
            )
            nodes_generated += 1
            heapq.heappush(
                open_heap,
                (child.cost, child.conflicts if tie_break else 0, next(counter), child),
            )

    # Open list exhausted => no solution exists (CBS is complete).
    return PlannerResult(
        algorithm=ALGORITHM_NAME,
        success=False,
        status=STATUS_NO_SOLUTION,
        runtime_sec=time.perf_counter() - started,
        low_level_calls=low_level_calls,
        low_level_expansions=low_level_expansions,
        high_level_expansions=high_level_expansions,
        conflicts_initial=initial_conflicts,
        details={"reason": "high-level search space exhausted: instance is unsolvable"},
    )


def _split(conflict: Conflict) -> List[Tuple[int, tuple]]:
    """The two constraints that resolve ``conflict``, one per involved agent."""
    if conflict.kind == VERTEX:
        cell, t = conflict.cell1, conflict.t
        return [(conflict.a1, (VERTEX, cell, t)), (conflict.a2, (VERTEX, cell, t))]
    # Edge conflict: a1 goes cell1 -> cell2, a2 goes cell2 -> cell1 during (t-1, t].
    return [
        (conflict.a1, (EDGE, conflict.cell1, conflict.cell2, conflict.t)),
        (conflict.a2, (EDGE, conflict.cell2, conflict.cell1, conflict.t)),
    ]


def _timeout(started, low_level_calls, low_level_expansions, high_level_expansions, initial_conflicts):
    return PlannerResult(
        algorithm=ALGORITHM_NAME,
        success=False,
        status=STATUS_TIMEOUT,
        runtime_sec=time.perf_counter() - started,
        low_level_calls=low_level_calls,
        low_level_expansions=low_level_expansions,
        high_level_expansions=high_level_expansions,
        conflicts_initial=initial_conflicts,
        details={"reason": "time limit reached"},
    )
