"""Single-agent A* and the time-expanded A* used inside the MAPF planners.

Two solvers live here:

1. :func:`astar` -- classic single-agent A* on the *static* grid.  Cell states,
   no time dimension.  Used by Independent A*, by the priority-ordering
   heuristics and to compute the sum-of-individual-costs (SIC) lower bound.

2. :func:`space_time_astar` -- A* over *(cell, timestep)* states.  This is the
   low-level solver of Prioritized Planning (it must avoid a **reservation
   table**) and of CBS (it must satisfy a **constraint set**).  A verifier
   object decides which moves are legal, so the same search code serves both
   planners.

Heuristics
----------
Both solvers accept any admissible heuristic ``h(cell) -> int``.  Two are
provided:

``true_distance`` (default)
    Exact shortest-path distance to the goal obtained by a backward BFS on the
    static grid.  It is admissible *and* consistent, and it dominates Manhattan
    on maps with obstacles (identical on empty maps).  Cost: one BFS per agent
    per instance, amortised over all low-level searches.
``manhattan``
    Manhattan distance, the textbook admissible heuristic for a 4-connected
    grid.  Kept for comparison and for the unit tests.

Using a *static* heuristic inside a constrained search is safe: obstacles are
the only static cost, so the true-distance heuristic never overestimates the
remaining cost of a constrained path either.
"""

from __future__ import annotations

import heapq
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Tuple

from environment.grid import Cell, GridMap

INF = float("inf")
Heuristic = Callable[[Cell], float]


# --------------------------------------------------------------------------- #
#  Heuristics
# --------------------------------------------------------------------------- #
def true_distance_heuristic(grid: GridMap, goal: Cell) -> Heuristic:
    """Backward BFS from ``goal`` -> exact remaining cost on the static grid."""
    dist: Dict[Cell, int] = {goal: 0}
    queue = deque([goal])
    while queue:
        cell = queue.popleft()
        step = dist[cell] + 1
        for nxt in grid.neighbors(cell):
            if nxt not in dist:
                dist[nxt] = step
                queue.append(nxt)

    def h(cell: Cell) -> float:
        return dist.get(cell, INF)

    return h


def manhattan_heuristic(grid: GridMap, goal: Cell) -> Heuristic:
    """Manhattan distance (admissible, consistent, weaker than true distance)."""

    def h(cell: Cell) -> float:
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])

    return h


HEURISTICS = {"true_distance": true_distance_heuristic, "manhattan": manhattan_heuristic}


def build_heuristic(grid: GridMap, goal: Cell, kind: str = "true_distance") -> Heuristic:
    try:
        factory = HEURISTICS[kind]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(f"unknown heuristic {kind!r}") from exc
    return factory(grid, goal)


# --------------------------------------------------------------------------- #
#  Classic (static) A*
# --------------------------------------------------------------------------- #
def astar(
    grid: GridMap,
    start: Cell,
    goal: Cell,
    heuristic: Optional[Heuristic] = None,
) -> Optional[List[Cell]]:
    """Optimal single-agent A* on the static grid.

    Returns the cell path (``path[0] == start``, ``path[-1] == goal``) or
    ``None`` when the goal is unreachable.  Ties are broken in favour of the
    smaller ``h`` and then insertion order, which makes the result deterministic
    for a fixed grid.
    """
    if not grid.is_free(start) or not grid.is_free(goal):
        return None
    if heuristic is None:
        heuristic = true_distance_heuristic(grid, goal)
    if start == goal:
        return [start]
    if heuristic(start) == INF:
        return None

    counter = 0
    open_heap: List[Tuple[float, float, int, Cell]] = [(heuristic(start), 0.0, counter, start)]
    came_from: Dict[Cell, Cell] = {}
    g_score: Dict[Cell, int] = {start: 0}
    closed: Set[Cell] = set()

    while open_heap:
        _, _, _, cell = heapq.heappop(open_heap)
        if cell in closed:
            continue
        closed.add(cell)
        if cell == goal:
            return _reconstruct(came_from, cell)
        g = g_score[cell] + 1
        for nxt in grid.neighbors(cell):
            if nxt in closed:
                continue
            if g < g_score.get(nxt, INF):
                g_score[nxt] = g
                came_from[nxt] = cell
                counter += 1
                heapq.heappush(open_heap, (g + heuristic(nxt), heuristic(nxt), counter, nxt))
    return None


def _reconstruct(came_from: Dict[Cell, Cell], cell: Cell) -> List[Cell]:
    path = [cell]
    while cell in came_from:
        cell = came_from[cell]
        path.append(cell)
    path.reverse()
    return path


# --------------------------------------------------------------------------- #
#  Constraints (CBS) and reservations (Prioritized Planning)
# --------------------------------------------------------------------------- #
@dataclass
class Constraints:
    """Constraints imposed on a *single* agent in CBS.

    ``vertex[(x, y)] = {t, ...}``     -- the agent must not occupy the cell at t.
    ``edge[(u, v)] = {t, ...}``       -- the agent must not be at ``v`` at time
    ``t`` having been at ``u`` at ``t - 1``.
    """

    vertex: Dict[Cell, Set[int]] = field(default_factory=dict)
    edge: Dict[Tuple[Cell, Cell], Set[int]] = field(default_factory=dict)
    latest_vertex: Dict[Cell, int] = field(default_factory=dict)
    latest_self_edge: Dict[Cell, int] = field(default_factory=dict)
    max_time: int = -1

    @classmethod
    def empty(cls) -> "Constraints":
        return cls()

    def copy(self) -> "Constraints":
        return Constraints(
            vertex={c: set(ts) for c, ts in self.vertex.items()},
            edge={e: set(ts) for e, ts in self.edge.items()},
            latest_vertex=dict(self.latest_vertex),
            latest_self_edge=dict(self.latest_self_edge),
            max_time=self.max_time,
        )

    def add_vertex(self, cell: Cell, t: int) -> None:
        self.vertex.setdefault(cell, set()).add(t)
        self.latest_vertex[cell] = max(self.latest_vertex.get(cell, -1), t)
        self.max_time = max(self.max_time, t)

    def add_edge(self, u: Cell, v: Cell, t: int) -> None:
        self.edge.setdefault((u, v), set()).add(t)
        if u == v:
            self.latest_self_edge[v] = max(self.latest_self_edge.get(v, -1), t)
        self.max_time = max(self.max_time, t)

    def has_vertex(self, cell: Cell, t: int) -> bool:
        return t in self.vertex.get(cell, ())

    def has_edge(self, u: Cell, v: Cell, t: int) -> bool:
        return t in self.edge.get((u, v), ())

    def __len__(self) -> int:
        return sum(len(ts) for ts in self.vertex.values()) + sum(
            len(ts) for ts in self.edge.values()
        )


class Verifier:
    """Interface for "is this space-time move legal?" (default: always legal)."""

    max_time: int = -1

    def can_start(self, cell: Cell) -> bool:  # noqa: D102 - see class docstring
        return True

    def can_enter(self, cell: Cell, t: int) -> bool:
        return True

    def can_move(self, u: Cell, v: Cell, t: int) -> bool:
        return True

    def can_terminate(self, cell: Cell, t: int) -> bool:
        return True


class ConstraintVerifier(Verifier):
    """CBS low-level legality test: only the agent's own constraints matter.

    ``can_terminate`` is the subtle part.  Under the "stay at target" assumption
    an agent that reaches its goal at time ``t`` occupies that cell for every
    ``t' >= t``.  Therefore terminating is only allowed once no future
    constraint can be violated by sitting still: no vertex constraint on the
    goal cell at any ``t' > t`` and no self-edge (stay) constraint on it either.
    """

    def __init__(self, constraints: Constraints) -> None:
        self.c = constraints
        self.max_time = constraints.max_time

    def can_start(self, cell: Cell) -> bool:
        return not self.c.has_vertex(cell, 0)

    def can_enter(self, cell: Cell, t: int) -> bool:
        return not self.c.has_vertex(cell, t)

    def can_move(self, u: Cell, v: Cell, t: int) -> bool:
        return not self.c.has_edge(u, v, t)

    def can_terminate(self, cell: Cell, t: int) -> bool:
        return t >= self.c.latest_vertex.get(cell, -1) and t >= self.c.latest_self_edge.get(
            cell, -1
        )


class ReservationTable:
    """Space-time reservations produced by the paths of already-planned agents.

    Two kinds of occupancy are stored:

    * *transient* -- the agent is at ``cell`` at time ``t`` for ``t`` along its
      path (``t <= len(path) - 1``, the arrival time at its goal).
    * *permanent* -- from its arrival time onwards the agent stays at its goal
      forever ("stay at target"), so that cell is blocked for all later times.

    Edge reservations record traversals ``u -> v`` arriving at time ``t``; a
    later agent may not traverse the same edge in the opposite direction at the
    same timestep (edge / swap conflict).
    """

    def __init__(self) -> None:
        self.vertex: Dict[Cell, Set[int]] = {}
        self.edges: Dict[frozenset, Set[int]] = {}
        self.permanent: Dict[Cell, int] = {}
        self.last_transient: Dict[Cell, int] = {}
        self.horizon = 0

    def add_path(self, path: List[Cell]) -> None:
        if not path:
            return
        for t, cell in enumerate(path):
            self.vertex.setdefault(cell, set()).add(t)
            self.last_transient[cell] = max(self.last_transient.get(cell, -1), t)
        for t in range(1, len(path)):
            u, v = path[t - 1], path[t]
            if u != v:
                self.edges.setdefault(frozenset((u, v)), set()).add(t)
        goal = path[-1]
        arrival = len(path) - 1
        self.permanent[goal] = min(self.permanent.get(goal, INF), arrival)
        self.horizon = max(self.horizon, arrival)

    def is_vertex_reserved(self, cell: Cell, t: int) -> bool:
        if t in self.vertex.get(cell, ()):
            return True
        start = self.permanent.get(cell)
        return start is not None and t >= start

    def is_edge_reserved(self, u: Cell, v: Cell, t: int) -> bool:
        if u == v:
            return False
        return t in self.edges.get(frozenset((u, v)), ())


class ReservationVerifier(Verifier):
    """Prioritized Planning legality test against a :class:`ReservationTable`."""

    def __init__(self, table: ReservationTable) -> None:
        self.table = table
        self.max_time = table.horizon

    def can_start(self, cell: Cell) -> bool:
        return not self.table.is_vertex_reserved(cell, 0)

    def can_enter(self, cell: Cell, t: int) -> bool:
        return not self.table.is_vertex_reserved(cell, t)

    def can_move(self, u: Cell, v: Cell, t: int) -> bool:
        return not self.table.is_edge_reserved(u, v, t)

    def can_terminate(self, cell: Cell, t: int) -> bool:
        # Reaching `cell` at `t` implies occupying it at every t' > t, so:
        #  - nobody may sit on it permanently (they would stay forever),
        #  - no *transient* reservation may exist at any t' > t.
        if cell in self.table.permanent:
            return False
        return self.table.last_transient.get(cell, -1) <= t


# --------------------------------------------------------------------------- #
#  Time-expanded A*
# --------------------------------------------------------------------------- #
@dataclass
class SearchResult:
    path: Optional[List[Cell]]
    expansions: int = 0
    generated: int = 0
    timed_out: bool = False


def space_time_astar(
    grid: GridMap,
    start: Cell,
    goal: Cell,
    verifier: Optional[Verifier] = None,
    heuristic: Optional[Heuristic] = None,
    deadline: Optional[float] = None,
    max_expansions: Optional[int] = None,
) -> SearchResult:
    """A* over ``(cell, t)`` states with unit action costs.

    ``verifier`` restricts which space-time moves are legal (constraints in CBS,
    reservations in Prioritized Planning).  Returns a :class:`SearchResult`;
    ``path is None`` means "no feasible path under these restrictions", which is
    a *meaningful* answer (it prunes a CBS branch / reports a PP failure) and is
    never silently turned into a success.
    """
    if not grid.is_free(start) or not grid.is_free(goal):
        return SearchResult(None)
    if heuristic is None:
        heuristic = true_distance_heuristic(grid, goal)
    verifier = verifier or Verifier()
    if heuristic(start) == INF:
        return SearchResult(None)
    if not verifier.can_start(start):
        return SearchResult(None)

    # Time horizon: constraints/reservations are finite, so any useful waiting
    # happens near them.  The slack keeps the search complete for all practical
    # instances while bounding the (otherwise infinite) time dimension.
    max_t = None
    if verifier.max_time >= 0:
        max_t = verifier.max_time + 2 * grid.size + 8
    if max_expansions is None:
        max_expansions = 50 * grid.size + 200000

    h0 = heuristic(start)
    open_heap: List[Tuple[float, float, int, int, Cell]] = [(h0, h0, 0, 0, start)]
    came_from: Dict[Tuple[Cell, int], Tuple[Cell, int]] = {}
    g_score: Dict[Tuple[Cell, int], int] = {(start, 0): 0}
    closed: Set[Tuple[Cell, int]] = set()
    counter = 1
    expansions = 0
    generated = 1

    while open_heap:
        f, h, _, t, cell = heapq.heappop(open_heap)
        state = (cell, t)
        if state in closed:
            continue
        closed.add(state)
        expansions += 1

        if cell == goal and verifier.can_terminate(cell, t):
            path = [cell]
            cur = state
            while cur in came_from:
                cur = came_from[cur]
                path.append(cur[0])
            path.reverse()
            return SearchResult(path, expansions, generated)

        if max_t is not None and t >= max_t:
            continue
        if deadline is not None and expansions % 512 == 0 and time.monotonic() > deadline:
            return SearchResult(None, expansions, generated, timed_out=True)
        if expansions > max_expansions:
            return SearchResult(None, expansions, generated, timed_out=True)

        nt = t + 1
        g = t + 1
        for nxt in grid.neighbors(cell):
            if not verifier.can_enter(nxt, nt):
                continue
            if not verifier.can_move(cell, nxt, nt):
                continue
            nstate = (nxt, nt)
            if nstate in closed:
                continue
            if g < g_score.get(nstate, math.inf):
                g_score[nstate] = g
                came_from[nstate] = state
                counter += 1
                generated += 1
                hn = heuristic(nxt)
                heapq.heappush(open_heap, (g + hn, hn, counter, nt, nxt))

    return SearchResult(None, expansions, generated)
