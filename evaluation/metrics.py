"""Metrics and *independent* solution validation.

Every number reported in the study is produced here.  Crucially, validation is
done by code that does **not** belong to the planner that produced the plan: a
planner's own claim "I succeeded" is re-checked from the definition of classical
MAPF.  If the check fails the run is recorded as ``invalid`` and loudly counted
as a failure (never silently fixed or dropped).

Definitions (Stern et al., 2019)
--------------------------------
``cost(path) = len(path) - 1``
    number of actions (moves/wait) until the goal is first occupied.
``SOC = sum_i cost(path_i)``
    sum of costs -- the objective CBS optimises.
``makespan = max_i cost(path_i)``
    completion time of the whole fleet.
``SIC = sum_i cost(shortest_path_i)``
    sum of individual optimal costs -- a lower bound on the optimal SOC and the
    reference for the *optimality gap* ``SOC / SIC - 1``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from environment.grid import Cell, GridMap, Scenario

from planning.astar import astar
from planning.collisions import (
    EDGE,
    VERTEX,
    Conflict,
    count_conflicts,
    detect_conflicts,
)
from planning.common import STATUS_INVALID, STATUS_OK, PlannerResult


# --------------------------------------------------------------------------- #
#  Basic cost metrics
# --------------------------------------------------------------------------- #
def path_cost(path: Sequence[Cell]) -> int:
    """Number of actions until the goal is reached (waiting counts as 1)."""
    return max(0, len(path) - 1)


def sum_of_costs(paths: Sequence[Sequence[Cell]]) -> int:
    return sum(path_cost(p) for p in paths)


def makespan(paths: Sequence[Sequence[Cell]]) -> int:
    return max((path_cost(p) for p in paths), default=0)


def sum_of_individual_costs(grid: GridMap, starts: Sequence[Cell], goals: Sequence[Cell]) -> Optional[int]:
    """SIC: sum of *individually optimal* path costs (admissible SOC bound)."""
    total = 0
    for start, goal in zip(starts, goals):
        path = astar(grid, start, goal)
        if path is None:
            return None
        total += path_cost(path)
    return total


def soc_optimality_gap(soc: Optional[int], sic: Optional[int]) -> Optional[float]:
    """Relative excess of SOC over the SIC lower bound (0.0 == provably optimal)."""
    if soc is None or not sic:
        return None
    return soc / sic - 1.0


# --------------------------------------------------------------------------- #
#  Validation
# --------------------------------------------------------------------------- #
@dataclass
class ValidationReport:
    valid: bool
    problems: List[str] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)

    @property
    def num_vertex_conflicts(self) -> int:
        return sum(1 for c in self.conflicts if c.kind == VERTEX)

    @property
    def num_edge_conflicts(self) -> int:
        return sum(1 for c in self.conflicts if c.kind == EDGE)

    def __bool__(self) -> bool:
        return self.valid


def validate_solution(
    grid: GridMap,
    starts: Sequence[Cell],
    goals: Sequence[Cell],
    paths: Sequence[Sequence[Cell]],
    max_conflicts: Optional[int] = None,
) -> ValidationReport:
    """Check a joint plan against the definition of classical MAPF.

    Verifies, per agent: starts at its start, every step is a legal action
    (wait or a 4-connected move), never enters an obstacle, ends at its goal.
    Then verifies pairwise: no vertex and no edge conflicts at any timestep.
    """
    problems: List[str] = []
    if len(paths) != len(starts):
        problems.append(f"expected {len(starts)} paths, got {len(paths)}")
        return ValidationReport(False, problems)

    for i, (path, start, goal) in enumerate(zip(paths, starts, goals)):
        if not path:
            problems.append(f"agent {i}: empty path")
            continue
        if path[0] != start:
            problems.append(f"agent {i}: path starts at {path[0]}, expected {start}")
        if path[-1] != goal:
            problems.append(f"agent {i}: path ends at {path[-1]}, expected {goal}")
        # Under stay-at-target semantics, arrival is the first occurrence of
        # the goal and the agent may not leave it afterwards. Paths need not
        # contain the implicit post-arrival waits, but may not encode departure.
        try:
            arrival = path.index(goal)
        except ValueError:
            arrival = None
        if arrival is not None and any(cell != goal for cell in path[arrival:]):
            problems.append(f"agent {i}: leaves goal {goal} after first arrival")
        for t, cell in enumerate(path):
            if not grid.is_free(cell):
                problems.append(f"agent {i}: occupies blocked cell {cell} at t={t}")
                break
        for t in range(1, len(path)):
            dx = abs(path[t][0] - path[t - 1][0])
            dy = abs(path[t][1] - path[t - 1][1])
            if dx + dy > 1:
                problems.append(f"agent {i}: illegal move {path[t - 1]} -> {path[t]} at t={t}")
                break

    conflicts = detect_conflicts(paths, max_conflicts=max_conflicts) if not problems else []
    valid = not problems and not conflicts
    if conflicts:
        problems.append(
            f"{len(conflicts)} conflict(s) remain "
            f"(vertex={sum(1 for c in conflicts if c.kind == VERTEX)}, "
            f"edge={sum(1 for c in conflicts if c.kind == EDGE)})"
        )
    return ValidationReport(valid, problems, conflicts)


def check_planner_result(scenario: Scenario, result: PlannerResult) -> PlannerResult:
    """Re-validate a planner's claim and downgrade it if the plan is wrong.

    Returns the same object, mutated: ``success``/``status`` are overwritten
    with ``invalid`` when the plan does not stand up to scrutiny.  Nothing is
    dropped and nothing is hidden -- the experiment tables count these runs.
    """
    if not result.success or not result.paths:
        return result
    report = validate_solution(scenario.grid, scenario.starts, scenario.goals, result.paths)
    if report.valid:
        result.conflicts_final = 0
        return result
    result.success = False
    result.status = STATUS_INVALID
    result.conflicts_final = len(report.conflicts)
    result.details["validation_problems"] = report.problems[:5]
    return result


# --------------------------------------------------------------------------- #
#  Aggregation of one run into a flat record
# --------------------------------------------------------------------------- #
def result_record(
    scenario: Scenario,
    result: PlannerResult,
    sic: Optional[int] = None,
    extra: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    """Flatten one (instance, planner) run into a CSV-friendly row."""
    row: Dict[str, object] = {
        "instance": scenario.name,
        "seed": scenario.seed,
        "algorithm": result.algorithm,
        "success": int(result.success),
        "status": result.status,
        "runtime_sec": round(result.runtime_sec, 6),
        "soc": result.soc,
        "makespan": result.makespan,
        "low_level_calls": result.low_level_calls,
        "low_level_expansions": result.low_level_expansions,
        "high_level_expansions": result.high_level_expansions,
        "conflicts_initial": result.conflicts_initial,
        "conflicts_final": result.conflicts_final,
    }
    if sic is not None and result.soc is not None:
        row["sic"] = sic
        row["soc_gap"] = round(soc_optimality_gap(result.soc, sic) or 0.0, 6)
        row["makespan_gap"] = (
            round(result.makespan / max(1, _sic_makespan(scenario, sic)) - 1.0, 6)
            if result.makespan is not None
            else None
        )
    else:
        row["sic"] = sic
        row["soc_gap"] = None
        row["makespan_gap"] = None
    row.update(scenario.meta or {})
    row["num_agents"] = scenario.num_agents
    if extra:
        row.update(extra)
    return row


def _sic_makespan(scenario: Scenario, sic: int) -> int:
    """Crude reference makespan (max individual optimal cost); a lower bound."""
    best = 0
    for start, goal in zip(scenario.starts, scenario.goals):
        path = astar(scenario.grid, start, goal)
        if path:
            best = max(best, path_cost(path))
    return best


def conflict_counts(paths: Sequence[Sequence[Cell]]) -> Dict[str, int]:
    conflicts = detect_conflicts(paths)
    return {
        "total": len(conflicts),
        "vertex": sum(1 for c in conflicts if c.kind == VERTEX),
        "edge": sum(1 for c in conflicts if c.kind == EDGE),
    }
