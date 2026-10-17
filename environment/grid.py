"""Static 2-D grid environment for MAPF.

Conventions (documented once, used everywhere)
---------------------------------------------
* A cell is a tuple ``(x, y)`` with ``0 <= x < width`` (column) and
  ``0 <= y < height`` (row).  Rendered row ``y`` first, so ``(0, 0)`` is the
  top-left corner.
* Time is discrete and starts at ``t = 0``.  At ``t = 0`` every agent occupies
  its start cell.
* Actions are the 5-element set {wait, up, down, left, right} (4-connected grid
  plus waiting); every action costs 1.
* A *path* is a list of cells, ``path[0] == start`` and ``path[-1] == goal``.
  ``cost(path) = len(path) - 1`` -- the number of actions (including waits)
  executed until the goal is *first* occupied.
* "Stay at target": after reaching its goal an agent remains there forever and
  never blocks other agents from traversing the cell at earlier timesteps
  (standard assumption in Stern et al., 2019).
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, List, Sequence, Set, Tuple

Cell = Tuple[int, int]

# (dx, dy) for wait, up, down, left, right.  The order is deterministic so that
# neighbour enumeration (and therefore tie-breaking inside A*) is reproducible.
MOVES: Tuple[Tuple[int, int], ...] = ((0, 0), (0, -1), (0, 1), (-1, 0), (1, 0))
MOVE_NAMES: Dict[Tuple[int, int], str] = {
    (0, 0): "wait",
    (0, -1): "up",
    (0, 1): "down",
    (-1, 0): "left",
    (1, 0): "right",
}


@dataclass
class GridMap:
    """A static grid: free cells plus a set of blocked (obstacle) cells.

    The grid is *static*: obstacles never move and never appear/disappear.  All
    dynamic information (agents, reservations, constraints) lives in the
    planning layer, which keeps the environment layer trivially testable.
    """

    width: int
    height: int
    obstacles: Set[Cell] = field(default_factory=set)
    name: str = "grid"

    # ------------------------------------------------------------------ setup
    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("grid dimensions must be positive")
        # Drop obstacles that fall outside the grid (defensive; keeps invariants).
        self.obstacles = {
            (x, y)
            for (x, y) in self.obstacles
            if 0 <= x < self.width and 0 <= y < self.height
        }

    # ---------------------------------------------------------------- basics
    def in_bounds(self, cell: Cell) -> bool:
        x, y = cell
        return 0 <= x < self.width and 0 <= y < self.height

    def is_blocked(self, cell: Cell) -> bool:
        return cell in self.obstacles

    def is_free(self, cell: Cell) -> bool:
        return self.in_bounds(cell) and cell not in self.obstacles

    def cells(self) -> Iterator[Cell]:
        for y in range(self.height):
            for x in range(self.width):
                yield (x, y)

    @property
    def free_cells(self) -> List[Cell]:
        return [c for c in self.cells() if c not in self.obstacles]

    @property
    def size(self) -> int:
        """Number of cells (free or blocked)."""
        return self.width * self.height

    @property
    def obstacle_density(self) -> float:
        """Measured obstacle density (#obstacles / #cells)."""
        return len(self.obstacles) / self.size

    def neighbors(self, cell: Cell) -> Iterator[Cell]:
        """Yield all cells reachable from ``cell`` in one action (incl. waiting)."""
        x, y = cell
        for dx, dy in MOVES:
            nxt = (x + dx, y + dy)
            if self.is_free(nxt):
                yield nxt

    # ------------------------------------------------------------ connectivity
    def reachable_from(self, start: Cell) -> Set[Cell]:
        """BFS over free cells; used for connectivity checks and heuristics."""
        if not self.is_free(start):
            return set()
        seen: Set[Cell] = {start}
        queue = deque([start])
        while queue:
            cell = queue.popleft()
            for nxt in self.neighbors(cell):
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return seen

    def largest_connected_component(self) -> Set[Cell]:
        """Return the biggest set of mutually reachable free cells."""
        unvisited = set(self.free_cells)
        best: Set[Cell] = set()
        while unvisited:
            start = next(iter(unvisited))
            comp = self.reachable_from(start)
            unvisited -= comp
            if len(comp) > len(best):
                best = comp
        return best

    def connected(self) -> bool:
        free = set(self.free_cells)
        return bool(free) and len(self.largest_connected_component()) == len(free)

    # ------------------------------------------------------------ construction
    @classmethod
    def from_rows(cls, rows: Sequence[Sequence[int]], name: str = "grid") -> "GridMap":
        """Build from a 0/1 matrix (1 == obstacle), rows indexed by ``y``."""
        height = len(rows)
        width = len(rows[0]) if height else 0
        obstacles = {
            (x, y)
            for y, row in enumerate(rows)
            for x, value in enumerate(row)
            if value
        }
        return cls(width=width, height=height, obstacles=obstacles, name=name)

    def to_rows(self) -> List[List[int]]:
        return [
            [1 if (x, y) in self.obstacles else 0 for x in range(self.width)]
            for y in range(self.height)
        ]

    @classmethod
    def from_ascii(cls, text: str, name: str = "grid") -> "GridMap":
        """Build from an ASCII art map.

        ``'.'``/``' '`` free, ``'@'``/``'#'``/``'T'`` obstacle.  Handy for
        hand-designed unit tests.
        """
        # Indented triple-quoted strings are convenient in tests: de-indent
        # before parsing so that leading whitespace is not read as map content.
        import textwrap

        lines = [
            line for line in textwrap.dedent(text).strip("\n").splitlines() if line.strip() != ""
        ]
        rows = []
        for line in lines:
            rows.append([0 if ch in ". " else 1 for ch in line])
        return cls.from_rows(rows, name=name)

    def to_ascii(self) -> str:
        return "\n".join(
            "".join("@" if (x, y) in self.obstacles else "." for x in range(self.width))
            for y in range(self.height)
        )

    # ------------------------------------------------------------- serialise
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "obstacles": sorted(self.obstacles),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GridMap":
        return cls(
            width=data["width"],
            height=data["height"],
            obstacles={(x, y) for x, y in data["obstacles"]},
            name=data.get("name", "grid"),
        )

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle)

    @classmethod
    def load(cls, path: str) -> "GridMap":
        with open(path, encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))

    def __str__(self) -> str:
        return f"<GridMap {self.name} {self.width}x{self.height} obs={len(self.obstacles)}>"


# --------------------------------------------------------------------------- #
#  Scenario (a MAPF instance = grid + starts + goals)
# --------------------------------------------------------------------------- #
@dataclass
class Scenario:
    """A MAPF instance: a static grid plus one start/goal pair per agent.

    Starts and goals are required to be distinct free cells; that invariant is
    enforced by the generators and checked by :func:`validate_scenario`.
    """

    grid: GridMap
    starts: List[Cell]
    goals: List[Cell]
    name: str = "scenario"
    seed: int | None = None
    meta: Dict[str, object] = field(default_factory=dict)

    @property
    def num_agents(self) -> int:
        return len(self.starts)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "seed": self.seed,
            "meta": dict(self.meta),
            "grid": self.grid.to_dict(),
            "starts": [list(c) for c in self.starts],
            "goals": [list(c) for c in self.goals],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Scenario":
        return cls(
            grid=GridMap.from_dict(data["grid"]),
            starts=[tuple(c) for c in data["starts"]],
            goals=[tuple(c) for c in data["goals"]],
            name=data.get("name", "scenario"),
            seed=data.get("seed"),
            meta=data.get("meta", {}),
        )

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle)

    @classmethod
    def load(cls, path: str) -> "Scenario":
        with open(path, encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))

    def summary(self) -> str:
        return (
            f"{self.name}: {self.grid.width}x{self.grid.height}, "
            f"density={self.grid.obstacle_density:.2f}, agents={self.num_agents}"
        )


def validate_scenario(scenario: Scenario) -> List[str]:
    """Return a list of problems (empty list == structurally valid instance)."""
    problems: List[str] = []
    grid = scenario.grid
    if len(scenario.starts) != len(scenario.goals):
        problems.append("starts/goals length mismatch")
    for i, (start, goal) in enumerate(zip(scenario.starts, scenario.goals)):
        if not grid.is_free(start):
            problems.append(f"agent {i}: start {start} is not a free cell")
        if not grid.is_free(goal):
            problems.append(f"agent {i}: goal {goal} is not a free cell")
    if len(set(scenario.starts)) != len(scenario.starts):
        problems.append("duplicate start cells")
    if len(set(scenario.goals)) != len(scenario.goals):
        problems.append("duplicate goal cells")
    return problems


def path_to_actions(path: Sequence[Cell]) -> List[str]:
    """Convert a cell path into the action sequence that produced it."""
    actions = []
    for (x1, y1), (x2, y2) in zip(path, path[1:]):
        actions.append(MOVE_NAMES.get((x2 - x1, y2 - y1), "?"))
    return actions
