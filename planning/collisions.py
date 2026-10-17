"""Conflict (collision) detection for MAPF.

Following Stern et al. (2019) we handle the two standard collision types of
classical MAPF on a 4-connected grid:

* **Vertex conflict** -- agents *i* and *j* occupy the same cell at the same
  timestep *t*.
* **Edge conflict** ("swap") -- agents *i* and *j* exchange their positions
  during the same timestep, i.e. *i* moves ``u -> v`` while *j* moves ``v -> u``
  between ``t-1`` and ``t``.

Follow conflicts (agent *i* occupies a cell at ``t+1`` that agent *j* occupied
at ``t``) are *not* treated as conflicts: with unit-time moves and no planning
delays this is the standard "pebble motion" assumption.  This is a modelling
decision and is stated explicitly in the report.

An agent that has reached its goal stays there, therefore
``position(path, t) = path[min(t, len(path) - 1)]``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from environment.grid import Cell

VERTEX = "vertex"
EDGE = "edge"


@dataclass(frozen=True, order=True)
class Conflict:
    """A pairwise collision between two agents.

    For a vertex conflict ``cell1 == cell2`` is the contested cell and ``t`` is
    the timestep.  For an edge conflict agent ``a1`` moves ``cell1 -> cell2``
    and agent ``a2`` moves ``cell2 -> cell1`` during ``(t-1, t]``.
    """

    t: int
    kind: str
    a1: int
    a2: int
    cell1: Cell
    cell2: Cell

    @property
    def agents(self) -> Tuple[int, int]:
        return (self.a1, self.a2)

    def __str__(self) -> str:
        if self.kind == VERTEX:
            return f"vertex({self.a1},{self.a2})@{self.cell1},t={self.t}"
        return f"edge({self.a1},{self.a2}) {self.cell1}<->{self.cell2},t={self.t}"


def position_at(path: Sequence[Cell], t: int) -> Cell:
    """Location of an agent at timestep ``t`` (it waits at its goal afterwards)."""
    if t < len(path):
        return path[t]
    return path[-1]


def has_vertex_conflict(path_i: Sequence[Cell], path_j: Sequence[Cell], t: int) -> bool:
    return position_at(path_i, t) == position_at(path_j, t)


def has_edge_conflict(path_i: Sequence[Cell], path_j: Sequence[Cell], t: int) -> bool:
    """True if the two agents swap positions between ``t-1`` and ``t``."""
    if t < 1:
        return False
    return (
        position_at(path_i, t - 1) == position_at(path_j, t)
        and position_at(path_i, t) == position_at(path_j, t - 1)
        and position_at(path_i, t) != position_at(path_i, t - 1)
    )


def detect_conflicts(
    paths: Sequence[Sequence[Cell]], max_conflicts: Optional[int] = None
) -> List[Conflict]:
    """All pairwise conflicts of a joint plan (each conflicting pair/time once)."""
    conflicts: List[Conflict] = []
    if not paths:
        return conflicts
    horizon = max(len(p) for p in paths) - 1
    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            for t in range(horizon + 1):
                if has_vertex_conflict(paths[i], paths[j], t):
                    conflicts.append(
                        Conflict(t, VERTEX, i, j, position_at(paths[i], t), position_at(paths[i], t))
                    )
                elif has_edge_conflict(paths[i], paths[j], t):
                    conflicts.append(
                        Conflict(
                            t,
                            EDGE,
                            i,
                            j,
                            position_at(paths[i], t - 1),
                            position_at(paths[i], t),
                        )
                    )
                if max_conflicts is not None and len(conflicts) >= max_conflicts:
                    return conflicts
    return conflicts


def find_first_conflict(paths: Sequence[Sequence[Cell]]) -> Optional[Conflict]:
    """Earliest conflict in the joint plan, or ``None`` if it is conflict-free.

    "First" orders by timestep and then by agent index, so the choice is
    deterministic.  CBS is optimal regardless of *which* conflict is chosen, but
    a deterministic choice keeps experiments reproducible.
    """
    if not paths:
        return None
    horizon = max(len(p) for p in paths) - 1
    for t in range(horizon + 1):
        for i in range(len(paths)):
            for j in range(i + 1, len(paths)):
                if has_vertex_conflict(paths[i], paths[j], t):
                    return Conflict(t, VERTEX, i, j, position_at(paths[i], t), position_at(paths[i], t))
        for i in range(len(paths)):
            for j in range(i + 1, len(paths)):
                if has_edge_conflict(paths[i], paths[j], t):
                    return Conflict(
                        t, EDGE, i, j, position_at(paths[i], t - 1), position_at(paths[i], t)
                    )
    return None


def count_conflicts(paths: Sequence[Sequence[Cell]]) -> int:
    return len(detect_conflicts(paths))


def conflicts_per_agent(
    paths: Sequence[Sequence[Cell]], num_agents: int
) -> Dict[int, int]:
    """How many conflicts each agent participates in (used for priority orders)."""
    counts = {i: 0 for i in range(num_agents)}
    for conflict in detect_conflicts(paths):
        counts[conflict.a1] += 1
        counts[conflict.a2] += 1
    return counts


def is_conflict_free(paths: Sequence[Sequence[Cell]]) -> bool:
    return find_first_conflict(paths) is None
