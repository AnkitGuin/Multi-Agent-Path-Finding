"""Unit tests for the environment layer: grid semantics and generators."""

import random

import pytest

from environment.generators import (
    DISTRIBUTIONS,
    STRUCTURES,
    generate_agents,
    usable_cells,
    generate_grid,
    generate_scenario,
    instance_features,
)
from environment.grid import GridMap, Scenario, path_to_actions


def test_grid_basics():
    grid = GridMap.from_ascii(
        """
        .....
        ..@..
        .....
        """
    )
    assert grid.width == 5 and grid.height == 3
    assert grid.is_blocked((2, 1))
    assert not grid.is_free((2, 1))
    assert not grid.in_bounds((5, 0))
    assert grid.obstacle_density == pytest.approx(1 / 15)
    assert len(grid.free_cells) == 14


def test_neighbors_include_wait_and_exclude_obstacles():
    grid = GridMap.from_ascii(
        """
        .@.
        ...
        """
    )
    assert set(grid.neighbors((0, 0))) == {(0, 0), (0, 1)}  # (1,0) is blocked
    assert set(grid.neighbors((1, 1))) == {(1, 1), (0, 1), (2, 1)}


def test_connectivity_and_components():
    connected = GridMap.from_ascii("...\n...")
    assert connected.connected()

    split = GridMap.from_ascii(
        """
        .@.
        .@.
        """
    )
    assert not split.connected()
    assert len(split.largest_connected_component()) == 2


def test_serialisation_roundtrip(tmp_path):
    grid = GridMap.from_ascii("..@\n...", name="tiny")
    path = tmp_path / "grid.json"
    grid.save(str(path))
    other = GridMap.load(str(path))
    assert other.obstacles == grid.obstacles and other.name == "tiny"


def test_path_to_actions():
    path = [(0, 0), (0, 0), (1, 0), (1, 1)]
    assert path_to_actions(path) == ["wait", "right", "down"]


# --------------------------------------------------------------------------- #
#  Generators
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("structure", STRUCTURES)
@pytest.mark.parametrize("density", [0.0, 0.2, 0.4])
def test_generated_maps_have_one_big_component(structure, density):
    """Every map must contain a giant component in which agents can be placed.

    ``random``/``clusters`` maps keep their small unreachable pockets (exactly
    like the standard benchmark maps); ``rooms``/``maze`` are built connected.
    """
    grid = generate_grid(32, 32, density, structure, rng=random.Random(7))
    free = grid.free_cells
    component = grid.largest_connected_component()
    assert len(free) > 100
    if structure in ("rooms", "maze"):
        assert grid.connected(), f"{structure}/{density} produced a disconnected map"
    else:
        assert len(component) >= 0.75 * len(free), (
            f"{structure}/{density}: largest component is only "
            f"{len(component)}/{len(free)} free cells"
        )


def test_agents_are_placed_in_one_component():
    """Starts and goals must be mutually reachable, whatever the map."""
    for structure in STRUCTURES:
        for density in (0.2, 0.4):
            grid = generate_grid(32, 32, density, structure, rng=random.Random(5))
            starts, goals = generate_agents(
                grid, 12, random.Random(9), "uniform", cells=usable_cells(grid)
            )
            component = set(usable_cells(grid))
            assert all(c in component for c in starts + goals)


@pytest.mark.parametrize("density", [0.0, 0.1, 0.2, 0.3, 0.4])
def test_random_structure_matches_requested_density(density):
    grid = generate_grid(32, 32, density, "random", rng=random.Random(3))
    assert grid.obstacle_density == pytest.approx(density, abs=0.005)


def test_zero_density_has_no_obstacles():
    grid = generate_grid(16, 16, 0.0, "random", rng=random.Random(1))
    assert grid.obstacles == set()


@pytest.mark.parametrize("structure", ["rooms", "maze"])
def test_structured_maps_are_connected(structure):
    grid = generate_grid(31, 31, 0.2, structure, rng=random.Random(11))
    assert grid.connected()


def test_maze_braiding_creates_loops():
    # A perfect maze is a spanning tree: #edges == #cells - 1.  Braiding adds
    # edges, so the "edges per cell" ratio must increase with the braid factor.
    def edge_ratio(braid):
        grid = generate_grid(31, 31, braid, "maze", rng=random.Random(5))
        free = set(grid.free_cells)
        edges = 0
        for x, y in free:
            for nx, ny in ((x + 1, y), (x, y + 1)):
                if (nx, ny) in free:
                    edges += 1
        return edges / len(free)

    assert edge_ratio(0.0) < edge_ratio(0.4) < edge_ratio(0.8)


@pytest.mark.parametrize("distribution", DISTRIBUTIONS)
def test_agent_placement_is_valid(distribution):
    grid = generate_grid(32, 32, 0.2, "random", rng=random.Random(2))
    starts, goals = generate_agents(grid, 10, random.Random(4), distribution)
    assert len(starts) == len(goals) == 10
    assert len(set(starts)) == 10 and len(set(goals)) == 10
    assert all(grid.is_free(c) for c in starts + goals)
    assert all(s != g for s, g in zip(starts, goals))


def test_too_many_agents_raises():
    grid = generate_grid(8, 8, 0.0, "random", rng=random.Random(0))
    with pytest.raises(ValueError):
        generate_agents(grid, 100, random.Random(0), "uniform")


def test_far_distribution_has_longer_goals_than_near():
    grid = generate_grid(32, 32, 0.2, "random", rng=random.Random(9))
    near = generate_agents(grid, 10, random.Random(1), "near")
    far = generate_agents(grid, 10, random.Random(1), "far")
    d_near = sum(abs(s[0] - g[0]) + abs(s[1] - g[1]) for s, g in zip(*near)) / 10
    d_far = sum(abs(s[0] - g[0]) + abs(s[1] - g[1]) for s, g in zip(*far)) / 10
    assert d_near < d_far


def test_scenario_is_fully_reproducible():
    a = generate_scenario(32, 32, 10, 0.2, "rooms", "uniform", seed=42)
    b = generate_scenario(32, 32, 10, 0.2, "rooms", "uniform", seed=42)
    c = generate_scenario(32, 32, 10, 0.2, "rooms", "uniform", seed=43)
    assert a.starts == b.starts and a.goals == b.goals
    assert a.grid.obstacles == b.grid.obstacles
    assert (a.starts, a.goals) != (c.starts, c.goals)


def test_scenario_roundtrip_and_features(tmp_path):
    scenario = generate_scenario(16, 16, 5, 0.1, "random", "uniform", seed=3)
    path = tmp_path / "scen.json"
    scenario.save(str(path))
    loaded = Scenario.load(str(path))
    assert loaded.starts == scenario.starts and loaded.goals == scenario.goals
    features = instance_features(loaded)
    assert features["num_agents"] == 5.0
    assert 0.0 <= features["obstacle_density"] <= 1.0
