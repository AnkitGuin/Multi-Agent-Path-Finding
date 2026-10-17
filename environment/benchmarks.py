"""Interoperability with the standard MovingAI MAPF benchmark format.

The generators in :mod:`environment.generators` give us *control* (we can vary
one factor at a time), but a study is more credible when it can also run on the
community's benchmark set.  This module reads and writes that format:

``.map``  (MovingAI grid map)::

    type octile
    height 32
    width 32
    map
    .@@....
    ...

``.scen``  (MovingAI scenario)::

    version 1
    0   mapname.map  32  32  12  4  20  15  14.0

Coordinates in ``.scen`` files are ``(column, row)`` == our ``(x, y)``, and the
last column is the optimal *individual* path length, which we use as a
cross-check for our A* implementation.

No benchmark files are bundled (they are large and separately licensed).  Drop
``*.map`` / ``*.scen`` pairs into ``data/benchmarks`` and they will be picked up
by :func:`discover_benchmarks`.  :func:`export_instance` writes our generated
instances in the same format so that anybody can re-run them with another
solver.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

from .grid import Cell, GridMap, Scenario

PASSABLE = {".", "G", "S", " "}
BLOCKED_HINT = {"@", "O", "T", "W", "#"}


def load_map(path: str) -> GridMap:
    """Parse a MovingAI ``.map`` file into a :class:`GridMap`."""
    with open(path, encoding="utf-8") as handle:
        lines = [line.rstrip("\n") for line in handle]
    width = height = 0
    rows: List[str] = []
    in_map = False
    for line in lines:
        if not in_map:
            key, _, value = line.partition(" ")
            key = key.strip().lower()
            if key == "width":
                width = int(value)
            elif key == "height":
                height = int(value)
            elif key == "map":
                in_map = True
            continue
        rows.append(line)
    if not width or not height:
        raise ValueError(f"{path}: missing width/height header")
    obstacles = {
        (x, y)
        for y, row in enumerate(rows[:height])
        for x, ch in enumerate(row[:width])
        if ch not in PASSABLE
    }
    return GridMap(
        width=width, height=height, obstacles=obstacles, name=os.path.basename(path)
    )


@dataclass
class ScenarioFile:
    """One parsed ``.scen`` file: a list of start/goal pairs for one map."""

    map_file: str
    entries: List[Tuple[Cell, Cell, Optional[float]]]


def load_scen(path: str) -> ScenarioFile:
    """Parse a MovingAI ``.scen`` file (start/goal pairs plus optimal length)."""
    entries: List[Tuple[Cell, Cell, Optional[float]]] = []
    map_file = ""
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t") if "\t" in line else line.split()
            if parts[0].lower() == "version":
                continue
            if len(parts) < 8:
                continue
            map_file = parts[1]
            start = (int(parts[4]), int(parts[5]))
            goal = (int(parts[6]), int(parts[7]))
            optimal = float(parts[8]) if len(parts) > 8 else None
            entries.append((start, goal, optimal))
    return ScenarioFile(map_file=map_file, entries=entries)


def load_scenario(
    map_path: str, scen_path: str, num_agents: Optional[int] = None, offset: int = 0
) -> Scenario:
    """Build a :class:`Scenario` from a ``.map``/``.scen`` pair.

    ``num_agents`` takes the *first* n entries of the scenario file after
    ``offset`` (the conventional way to vary the number of agents with the
    standard benchmark files).
    """
    grid = load_map(map_path)
    scen = load_scen(scen_path)
    entries = scen.entries[offset:]
    if num_agents is not None:
        entries = entries[:num_agents]
    starts = [start for start, _, _ in entries]
    goals = [goal for _, goal, _ in entries]
    name = f"{os.path.basename(map_path).rsplit('.', 1)[0]}-{len(starts)}"
    return Scenario(grid=grid, starts=starts, goals=goals, name=name)


def iter_benchmark_scenarios(
    directory: str, agent_counts: Iterable[int]
) -> Iterator[Scenario]:
    """Yield scenarios for every ``.map``/matching ``.scen`` pair found."""
    directory = os.path.abspath(directory)
    if not os.path.isdir(directory):
        return
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".scen"):
            continue
        scen_path = os.path.join(directory, filename)
        try:
            scen = load_scen(scen_path)
        except OSError:
            continue
        map_path = os.path.join(directory, os.path.basename(scen.map_file))
        if not os.path.exists(map_path):
            continue
        grid = load_map(map_path)
        for count in agent_counts:
            if count > len(scen.entries):
                continue
            yield Scenario(
                grid=grid,
                starts=[s for s, _, _ in scen.entries[:count]],
                goals=[g for _, g, _ in scen.entries[:count]],
                name=f"{os.path.basename(map_path).rsplit('.', 1)[0]}-a{count}",
                meta={"source": "movingai", "map": os.path.basename(map_path)},
            )


def discover_benchmarks(directory: str = "data/benchmarks") -> List[str]:
    """List ``.scen`` files available locally (empty list == none downloaded)."""
    directory = os.path.abspath(directory)
    if not os.path.isdir(directory):
        return []
    return sorted(
        os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".scen")
    )


# --------------------------------------------------------------------------- #
#  Export
# --------------------------------------------------------------------------- #
def write_map(grid: GridMap, path: str) -> None:
    """Write a grid in MovingAI ``.map`` format."""
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("type octile\n")
        handle.write(f"height {grid.height}\n")
        handle.write(f"width {grid.width}\n")
        handle.write("map\n")
        for y in range(grid.height):
            handle.write(
                "".join("@" if (x, y) in grid.obstacles else "." for x in range(grid.width))
            )
            handle.write("\n")


def write_scen(scenario: Scenario, path: str, map_filename: str) -> None:
    """Write start/goal pairs (with individual optimal costs) as ``.scen``."""
    from planning.astar import astar

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("version 1\n")
        for i, (start, goal) in enumerate(zip(scenario.starts, scenario.goals)):
            path_len = astar(scenario.grid, start, goal)
            optimal = len(path_len) - 1 if path_len else 0
            handle.write(
                f"{i}\t{map_filename}\t{scenario.grid.width}\t{scenario.grid.height}\t"
                f"{start[0]}\t{start[1]}\t{goal[0]}\t{goal[1]}\t{optimal}\n"
            )


def export_instance(scenario: Scenario, directory: str, stem: Optional[str] = None) -> Tuple[str, str]:
    """Export one instance as a ``.map``/``.scen`` pair; returns both paths."""
    os.makedirs(directory, exist_ok=True)
    stem = stem or scenario.name.replace(" ", "_")
    map_path = os.path.join(directory, f"{stem}.map")
    scen_path = os.path.join(directory, f"{stem}.scen")
    write_map(scenario.grid, map_path)
    write_scen(scenario, scen_path, os.path.basename(map_path))
    return map_path, scen_path


def cross_check_against_benchmark(scenario: Scenario, scen_path: str) -> Dict[str, int]:
    """Compare our A* costs with the optimal lengths recorded in a ``.scen``.

    Returns ``{"checked": n, "mismatches": k}``.  A mismatch means our grid or
    A* disagrees with the benchmark's own numbers -- a useful sanity check
    before trusting any result on those maps.
    """
    from planning.astar import astar

    scen = load_scen(scen_path)
    mismatches = 0
    checked = 0
    for start, goal, optimal in scen.entries[: len(scenario.starts)]:
        path = astar(scenario.grid, start, goal)
        if path is None or optimal is None:
            continue
        checked += 1
        if abs((len(path) - 1) - optimal) > 1e-6:
            mismatches += 1
    return {"checked": checked, "mismatches": mismatches}
