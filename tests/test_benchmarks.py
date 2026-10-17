"""Tests for the MovingAI benchmark import/export layer."""

import os

import pytest

from environment.benchmarks import (
    cross_check_against_benchmark,
    export_instance,
    load_map,
    load_scenario,
    load_scen,
    write_map,
)
from environment.generators import generate_scenario
from environment.grid import GridMap

MAP_TEXT = """type octile
height 4
width 5
map
.....
.@@@.
.....
..@..
"""

SCEN_TEXT = """version 1
0\ttest.map\t5\t4\t0\t0\t4\t0\t8
1\ttest.map\t5\t4\t0\t2\t4\t2\t4
"""


def test_load_map(tmp_path):
    path = tmp_path / "test.map"
    path.write_text(MAP_TEXT)
    grid = load_map(str(path))
    assert grid.width == 5 and grid.height == 4
    assert grid.obstacles == {(1, 1), (2, 1), (3, 1), (2, 3)}
    assert grid.name == "test.map"


def test_load_scen(tmp_path):
    path = tmp_path / "test.scen"
    path.write_text(SCEN_TEXT)
    scen = load_scen(str(path))
    assert scen.map_file == "test.map"
    assert scen.entries[0][0] == (0, 0) and scen.entries[0][1] == (4, 0)
    assert scen.entries[0][2] == 8.0


def test_load_scenario_combines_map_and_scen(tmp_path):
    (tmp_path / "test.map").write_text(MAP_TEXT)
    (tmp_path / "test.scen").write_text(SCEN_TEXT)
    scenario = load_scenario(str(tmp_path / "test.map"), str(tmp_path / "test.scen"))
    assert scenario.num_agents == 2
    assert scenario.starts == [(0, 0), (0, 2)]
    assert scenario.goals == [(4, 0), (4, 2)]
    assert scenario.grid.obstacles == {(1, 1), (2, 1), (3, 1), (2, 3)}

    one = load_scenario(str(tmp_path / "test.map"), str(tmp_path / "test.scen"), num_agents=1)
    assert one.num_agents == 1


def test_export_then_reload_round_trip(tmp_path):
    scenario = generate_scenario(16, 16, 5, 0.2, "random", "uniform", seed=4)
    map_path, scen_path = export_instance(scenario, str(tmp_path), stem="rt")
    reloaded = load_scenario(map_path, scen_path)
    assert reloaded.grid.obstacles == scenario.grid.obstacles
    assert reloaded.starts == scenario.starts
    assert reloaded.goals == scenario.goals


def test_cross_check_agrees_with_our_astar(tmp_path):
    """The .scen 'optimal length' column must match our A* costs exactly."""
    scenario = generate_scenario(24, 24, 6, 0.15, "random", "uniform", seed=8)
    map_path, scen_path = export_instance(scenario, str(tmp_path), stem="cc")
    report = cross_check_against_benchmark(load_scenario(map_path, scen_path), scen_path)
    assert report["checked"] == 6
    assert report["mismatches"] == 0


def test_bundled_example_instance_loads():
    """The example instance shipped in data/benchmarks must be loadable."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    map_path = os.path.join(root, "data", "benchmarks", "example_rooms_a12.map")
    scen_path = os.path.join(root, "data", "benchmarks", "example_rooms_a12.scen")
    if not (os.path.exists(map_path) and os.path.exists(scen_path)):
        pytest.skip("example instance not exported yet (run scripts/make_example_figure.py)")
    scenario = load_scenario(map_path, scen_path)
    assert scenario.num_agents == 12
    assert all(scenario.grid.is_free(c) for c in scenario.starts + scenario.goals)


def test_write_map_round_trip(tmp_path):
    grid = GridMap.from_ascii("..@\n...", name="tiny")
    path = tmp_path / "tiny.map"
    write_map(grid, str(path))
    assert load_map(str(path)).obstacles == grid.obstacles
