"""Versioned procedural study cases; no third-party maps redistributed."""
from environment.generators import generate_scenario
from environment.grid import GridMap, Scenario


def build_scenario(family, seed, agents=5, size=16):
    if family in {"random", "rooms", "maze"}:
        return generate_scenario(size, size, agents, .2, family, "uniform", seed=seed)
    if family == "open":
        return generate_scenario(size, size, agents, 0, "random", "uniform", seed=seed)
    if family == "corridor":
        return Scenario(GridMap(7, 1), [(0, 0), (6, 0)], [(6, 0), (0, 0)],
                        name=f"corridor-{seed}", seed=seed, meta={"family": family})
    if family == "doorway":
        grid = GridMap(7, 5, {(3, y) for y in range(5) if y != 2})
        return Scenario(grid, [(1, 2), (5, 2)], [(5, 2), (1, 2)],
                        name=f"doorway-{seed}", seed=seed, meta={"family": family})
    if family == "hidden_wall":
        return Scenario(GridMap(7, 3, {(3, 0), (3, 1)}), [(0, 1), (6, 1)], [(6, 1), (0, 1)],
                        name=f"hidden-wall-{seed}", seed=seed, meta={"family": family})
    raise ValueError(f"unknown family {family!r}")
