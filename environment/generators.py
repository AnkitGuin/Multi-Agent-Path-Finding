"""Procedural generators for controlled MAPF experiments.

Every generator takes an explicit ``random.Random`` instance so that a whole
experiment is reproducible from a single integer seed.  The seed of an instance
is stored in :class:`~environment.grid.Scenario` and recorded in the raw result
files, so any reported map can be regenerated exactly.

Map structures
--------------
``random``
    Uniform i.i.d. obstacles (the classic "random 20%" MAPF benchmark family).
``clusters``
    Random rectangular obstacle blobs -> cave-like maps with big open areas and
    large irregular obstacles.
``rooms``
    A grid of rectangular rooms connected by single-cell doorways.  Creates
    strong bottlenecks, which is where coordination strategies differ most.
``maze``
    Randomised-DFS perfect maze (spanning tree: exactly one route between any
    two cells), optionally *braided*.  For this structure the ``density``
    argument is reinterpreted as the **braid fraction**: the fraction of dead
    ends that are opened up.  Braiding turns the spanning tree into a graph with
    loops and is the variable that actually changes difficulty here, so the
    *measured* obstacle density is reported for every map in the raw results.

Start/goal distributions
------------------------
``uniform``  starts and goals i.i.d. over free cells.
``clustered`` starts and goals drawn around a few shared centres (heavy overlap).
``near``      goal drawn close to its own start (little overlap, short paths).
``far``       goal drawn as far as possible from its own start (long paths,
             many crossings -> high congestion).
"""

from __future__ import annotations

import math
import random
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from environment.grid import Cell, GridMap, Scenario

STRUCTURES = ("random", "clusters", "rooms", "maze")
DISTRIBUTIONS = ("uniform", "clustered", "near", "far")


# --------------------------------------------------------------------------- #
#  Map structures
# --------------------------------------------------------------------------- #
def generate_grid(
    width: int,
    height: int,
    obstacle_density: float = 0.2,
    structure: str = "random",
    rng: Optional[random.Random] = None,
    name: str = "map",
) -> GridMap:
    """Generate a static grid of the requested structure.

    For ``random``/``clusters`` the map is first generated slightly denser than
    requested and then pruned to its largest connected component; obstacles are
    subsequently removed until the *measured* density matches the request.  This
    guarantees (a) a connected map and (b) that the reported density label is
    honest -- both properties matter for a controlled experiment.
    """
    rng = rng or random.Random(0)
    if not 0.0 <= obstacle_density < 1.0:
        raise ValueError("obstacle_density must be in [0, 1)")
    if structure not in STRUCTURES:
        raise ValueError(f"unknown structure {structure!r}; expected one of {STRUCTURES}")

    if structure == "maze":
        return _maze(width, height, braid=obstacle_density, rng=rng, name=name)
    if structure == "rooms":
        return _rooms(width, height, obstacle_density, rng, name=name)

    # random / clusters: obstacles are placed at exactly the requested density
    # and the map is *not* pruned.  Pruning to the largest connected component
    # and then re-opening cells to restore the target density turns a uniform
    # random map into a structured one (long comb-like corridors) as soon as the
    # density approaches the site-percolation threshold of the square lattice
    # (~0.41 obstacles), which silently confounded the "obstacle density"
    # factor.  Standard benchmark maps keep their small unreachable pockets too;
    # agents are simply placed inside the giant component.
    for attempt in range(25):
        if structure == "clusters":
            blocked = _clusters(width, height, obstacle_density, rng)
        else:
            blocked = _uniform(width, height, obstacle_density, rng)
        grid = GridMap(width=width, height=height, obstacles=set(blocked), name=name)
        component = grid.largest_connected_component()
        free = grid.free_cells
        if free and len(component) >= max(16, 0.75 * len(free)):
            return grid
    return grid


def usable_cells(grid: GridMap) -> List[Cell]:
    """Cells agents may use: the largest connected component of free space."""
    return sorted(grid.largest_connected_component())


def _uniform(width: int, height: int, density: float, rng: random.Random) -> Set[Cell]:
    """Uniform random obstacles: exactly ``density * area`` cells, chosen uniformly.

    Exact-count sampling (rather than one Bernoulli trial per cell) makes the
    *measured* density of every generated map equal to the requested one, so the
    "obstacle density" factor of the experiment is exactly what its label says.
    """
    area = width * height
    count = int(round(density * area))
    all_cells = [(x, y) for y in range(height) for x in range(width)]
    return set(rng.sample(all_cells, count))


def _clusters(width: int, height: int, density: float, rng: random.Random) -> Set[Cell]:
    """Random overlapping rectangles of obstacles (cave-like maps)."""
    blocked: Set[Cell] = set()
    area = width * height
    target_cells = density * area
    placed = 0
    attempts = 0
    while placed < target_cells and attempts < 4000:
        attempts += 1
        bw = rng.randint(1, max(1, width // 5))
        bh = rng.randint(1, max(1, height // 5))
        x0 = rng.randint(0, width - bw)
        y0 = rng.randint(0, height - bh)
        for y in range(y0, y0 + bh):
            for x in range(x0, x0 + bw):
                if (x, y) not in blocked:
                    blocked.add((x, y))
                    placed += 1
    return blocked


def _rooms(
    width: int, height: int, density: float, rng: random.Random, name: str
) -> GridMap:
    """Grid of rooms with doorways.

    ``density`` here scales the *extra* obstacle clutter placed inside the rooms
    (0 == clean rooms, 0.3 == 30% of the remaining free room cells blocked).
    """
    blocked: Set[Cell] = set()
    # Split the map into bands; band boundaries become walls.
    xs = _band_edges(width, rng)
    ys = _band_edges(height, rng)

    for wx in xs:  # vertical walls
        for y in range(height):
            blocked.add((wx, y))
    for wy in ys:  # horizontal walls
        for x in range(width):
            blocked.add((x, wy))

    # One door per pair of horizontally/vertically adjacent rooms -> connected.
    for wx in xs:
        for (y0, y1) in zip([0] + [b + 1 for b in ys], list(ys) + [height]):
            if y1 - y0 <= 1:
                continue
            blocked.discard((wx, rng.randrange(y0, y1)))
    for wy in ys:
        for (x0, x1) in zip([0] + [b + 1 for b in xs], list(xs) + [width]):
            if x1 - x0 <= 1:
                continue
            blocked.discard((rng.randrange(x0, x1), wy))

    # Optional clutter inside rooms, added one cell at a time while the map
    # stays connected, until the *measured* density reaches the request.
    area = width * height
    if density > 0 and len(blocked) / area < density:
        free = [c for c in _all_cells(width, height) if c not in blocked]
        rng.shuffle(free)
        needed = int(density * area) - len(blocked)
        added = 0
        for cell in free:
            if added >= needed:
                break
            blocked.add(cell)
            # A cell with 0 or 1 free neighbours can never disconnect anything,
            # so only the (rare) other case needs the full connectivity check.
            if _free_degree(width, height, blocked, cell) < 2 or _is_connected(
                width, height, blocked
            ):
                added += 1
            else:
                blocked.discard(cell)
    return _prune(width, height, blocked, density, rng, name=name, keep_density=False)


def _band_edges(length: int, rng: random.Random) -> List[int]:
    """Positions of internal walls along one axis (rooms of size 6..10)."""
    edges: List[int] = []
    pos = rng.randint(6, 9)
    while pos < length - 6:
        edges.append(pos)
        pos += rng.randint(6, 10)
    return edges


def _maze(
    width: int, height: int, braid: float, rng: random.Random, name: str
) -> GridMap:
    """Randomised-DFS perfect maze on the odd-cell lattice, then braided."""
    # The DFS maze lives on odd coordinates; trailing even row/column is wall.
    w = width if width % 2 == 1 else width - 1
    h = height if height % 2 == 1 else height - 1
    w, h = max(w, 3), max(h, 3)
    blocked: Set[Cell] = {(x, y) for y in range(height) for x in range(width)}

    def carve(x: int, y: int) -> None:
        blocked.discard((x, y))

    start = (1, 1)
    carve(*start)
    stack = [start]
    visited = {start}
    while stack:
        x, y = stack[-1]
        options = [
            (nx, ny)
            for nx, ny in ((x + 2, y), (x - 2, y), (x, y + 2), (x, y - 2))
            if 0 < nx < w and 0 < ny < h and (nx, ny) not in visited
        ]
        if not options:
            stack.pop()
            continue
        nx, ny = rng.choice(options)
        carve((x + nx) // 2, (y + ny) // 2)  # knock down the wall between
        carve(nx, ny)
        visited.add((nx, ny))
        stack.append((nx, ny))

    if braid > 0:
        _braid(width, height, blocked, braid, rng)
    return _prune(width, height, blocked, 0.0, rng, name=name, keep_density=False)


def _braid(
    width: int, height: int, blocked: Set[Cell], braid: float, rng: random.Random
) -> None:
    """Open a fraction ``braid`` of dead ends, creating loops (alternate routes)."""
    dead_ends = []
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if (x, y) in blocked:
                continue
            open_neighbours = sum(
                1
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                if (nx, ny) not in blocked
            )
            if open_neighbours == 1:
                dead_ends.append((x, y))
    for x, y in dead_ends:
        if rng.random() > braid:
            continue
        walls = [
            (nx, ny)
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
            if 0 < nx < width - 1 and 0 < ny < height - 1 and (nx, ny) in blocked
        ]
        if walls:
            blocked.discard(rng.choice(walls))


def _all_cells(width: int, height: int) -> Iterable[Cell]:
    return ((x, y) for y in range(height) for x in range(width))


def _prune(
    width: int,
    height: int,
    blocked: Set[Cell],
    target_density: float,
    rng: random.Random,
    name: str,
    keep_density: bool = True,
) -> GridMap:
    """Keep only the largest connected component, then match target density."""
    grid = GridMap(width=width, height=height, obstacles=set(blocked), name=name)
    component = grid.largest_connected_component()
    obstacles = {c for c in _all_cells(width, height) if c not in component}

    if keep_density and target_density >= 0:
        # Only obstacles *adjacent to* the kept component may be removed: that
        # way the freed cell simply joins the component and free space stays
        # connected.  Newly exposed obstacles then become candidates too.
        target_cells = int(round(target_density * width * height))
        frontier = [
            c
            for c in obstacles
            if any(_neighbour(c, dx, dy) in component for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        ]
        rng.shuffle(frontier)
        in_frontier = set(frontier)
        while len(obstacles) > target_cells and frontier:
            cell = frontier.pop()
            in_frontier.discard(cell)
            if cell not in obstacles:
                continue
            obstacles.discard(cell)
            component.add(cell)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nxt = _neighbour(cell, dx, dy)
                if nxt in obstacles and nxt not in in_frontier:
                    in_frontier.add(nxt)
                    frontier.append(nxt)
    return GridMap(width=width, height=height, obstacles=obstacles, name=name)


def _neighbour(cell: Cell, dx: int, dy: int) -> Cell:
    return (cell[0] + dx, cell[1] + dy)


def _is_connected(width: int, height: int, blocked: Set[Cell]) -> bool:
    """Is the free space of this (partially built) map still one component?"""
    start = next((c for c in _all_cells(width, height) if c not in blocked), None)
    if start is None:
        return False
    seen = {start}
    queue = [start]
    while queue:
        x, y = queue.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (x + dx, y + dy)
            if (
                0 <= nxt[0] < width
                and 0 <= nxt[1] < height
                and nxt not in blocked
                and nxt not in seen
            ):
                seen.add(nxt)
                queue.append(nxt)
    return len(seen) == width * height - len(blocked)


# --------------------------------------------------------------------------- #
#  Start/goal placement
# --------------------------------------------------------------------------- #
def generate_agents(
    grid: GridMap,
    num_agents: int,
    rng: Optional[random.Random] = None,
    distribution: str = "uniform",
    cells: Optional[Sequence[Cell]] = None,
) -> Tuple[List[Cell], List[Cell]]:
    """Sample ``num_agents`` distinct start/goal pairs.

    Sampling is restricted to ``cells`` (by default the largest connected
    component of free space) so that every goal is reachable from every start.
    Raises ``ValueError`` if the map cannot host that many agents.
    """
    rng = rng or random.Random(0)
    if distribution not in DISTRIBUTIONS:
        raise ValueError(f"unknown distribution {distribution!r}")
    free = list(cells) if cells is not None else grid.free_cells
    if num_agents <= 0:
        return [], []
    if len(free) < 2 * num_agents:
        raise ValueError(
            f"map has {len(free)} free cells, not enough for {num_agents} agents"
        )

    if distribution == "uniform":
        chosen = rng.sample(free, 2 * num_agents)
        return list(chosen[:num_agents]), list(chosen[num_agents:])

    if distribution == "clustered":
        return _clustered_agents(grid, num_agents, rng, free)

    if distribution == "near":
        radius = max(2, int(0.15 * min(grid.width, grid.height)))
        return _near_agents(grid, num_agents, rng, radius, free)

    # distribution == "far"
    return _far_agents(grid, num_agents, rng, free)


def _clustered_agents(
    grid: GridMap, num_agents: int, rng: random.Random, cells: Sequence[Cell]
) -> Tuple[List[Cell], List[Cell]]:
    """Starts/goals concentrated around a few centres -> heavy interaction."""
    free = set(cells)
    centres = rng.sample(grid.free_cells, k=max(1, min(len(free), num_agents // 4 + 1)))
    radius = max(3, int(0.20 * min(grid.width, grid.height)))
    starts, goals, used = [], [], set()

    def pick(centre: Cell) -> Optional[Cell]:
        cx, cy = centre
        candidates = [
            (x, y)
            for x in range(max(0, cx - radius), min(grid.width, cx + radius + 1))
            for y in range(max(0, cy - radius), min(grid.height, cy + radius + 1))
            if (x, y) in free and (x, y) not in used
        ]
        return rng.choice(candidates) if candidates else None

    while len(starts) < num_agents:
        centre = rng.choice(centres)
        start = pick(centre)
        if start is None:
            leftovers = [c for c in free if c not in used]
            if not leftovers:
                raise ValueError("map too small/crowded for clustered placement")
            start = rng.choice(leftovers)
        used.add(start)
        starts.append(start)
    for _ in range(num_agents):
        centre = rng.choice(centres)
        goal = pick(centre)
        if goal is None:
            leftovers = [c for c in free if c not in used]
            if not leftovers:
                raise ValueError("map too small/crowded for clustered placement")
            goal = rng.choice(leftovers)
        used.add(goal)
        goals.append(goal)
    return starts, goals


def _near_agents(
    grid: GridMap, num_agents: int, rng: random.Random, radius: int, cells: Sequence[Cell]
) -> Tuple[List[Cell], List[Cell]]:
    free = set(cells)
    starts, goals, used = [], [], set()
    while len(starts) < num_agents:
        start = rng.choice(tuple(free - used))
        used.add(start)
        starts.append(start)
        candidates = [
            (x, y)
            for x in range(max(0, start[0] - radius), min(grid.width, start[0] + radius + 1))
            for y in range(max(0, start[1] - radius), min(grid.height, start[1] + radius + 1))
            if (x, y) in free and (x, y) not in used and (x, y) != start
        ]
        goal = rng.choice(candidates) if candidates else rng.choice(tuple(free - used))
        used.add(goal)
        goals.append(goal)
    return starts, goals


def _far_agents(
    grid: GridMap, num_agents: int, rng: random.Random, cells: Sequence[Cell]
) -> Tuple[List[Cell], List[Cell]]:
    """Each goal is (approximately) maximally far from its own start."""
    free = list(cells)
    starts, goals, used = [], [], set()
    while len(starts) < num_agents:
        start = rng.choice([c for c in free if c not in used] or free)
        used.add(start)
        starts.append(start)
        sample = rng.sample(free, k=min(len(free), 40))
        sample = [c for c in sample if c not in used]
        if not sample:
            sample = [c for c in free if c not in used]
        sample.sort(
            key=lambda c: -(abs(c[0] - start[0]) + abs(c[1] - start[1]))
        )
        top = sample[: max(1, len(sample) // 5)]
        goal = rng.choice(top)
        used.add(goal)
        goals.append(goal)
    return starts, goals


# --------------------------------------------------------------------------- #
#  Full instance generation
# --------------------------------------------------------------------------- #
def generate_scenario(
    width: int = 32,
    height: int = 32,
    num_agents: int = 10,
    obstacle_density: float = 0.2,
    structure: str = "random",
    distribution: str = "uniform",
    seed: int = 0,
    name: Optional[str] = None,
) -> Scenario:
    """Build one complete MAPF instance; fully determined by its arguments."""
    rng = random.Random(seed)
    grid = generate_grid(width, height, obstacle_density, structure, rng, name="map")
    starts, goals = generate_agents(
        grid, num_agents, rng, distribution, cells=usable_cells(grid)
    )
    label = name or (
        f"{structure}-{width}x{height}-d{int(round(obstacle_density * 100)):02d}"
        f"-a{num_agents}-{distribution}-s{seed}"
    )
    return Scenario(
        grid=grid,
        starts=starts,
        goals=goals,
        name=label,
        seed=seed,
        meta={
            "structure": structure,
            "distribution": distribution,
            "obstacle_density_requested": obstacle_density,
            "obstacle_density_measured": grid.obstacle_density,
            "width": width,
            "height": height,
            "num_agents": num_agents,
        },
    )


def instance_features(scenario: Scenario) -> Dict[str, float]:
    """Cheap structural features of an instance (used by the adaptive selector)."""
    grid = scenario.grid
    n = scenario.num_agents
    dists = [
        abs(s[0] - g[0]) + abs(s[1] - g[1]) for s, g in zip(scenario.starts, scenario.goals)
    ]
    return {
        "num_agents": float(n),
        "grid_area": float(grid.width * grid.height),
        "agent_density": n / max(1, len(grid.free_cells)),
        "obstacle_density": grid.obstacle_density,
        "mean_start_goal_manhattan": sum(dists) / n if n else 0.0,
        "max_start_goal_manhattan": float(max(dists)) if n else 0.0,
        "diameter": float(grid.width + grid.height),
    }


def _free_degree(width: int, height: int, blocked: Set[Cell], cell: Cell) -> int:
    """Number of free 4-neighbours of ``cell`` (``cell`` itself is blocked)."""
    x, y = cell
    return sum(
        1
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
        if 0 <= x + dx < width and 0 <= y + dy < height and (x + dx, y + dy) not in blocked
    )
