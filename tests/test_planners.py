"""Tests for Independent A* and Prioritized Planning on hand-designed maps."""

import random

import pytest

from environment.generators import generate_scenario
from environment.grid import GridMap
from planning.astar import astar
from planning.collisions import count_conflicts
from planning.common import STATUS_NO_SOLUTION, STATUS_OK
from planning.independent import solve_independent
from planning.prioritized import (
    PRIORITY_ORDERS,
    solve_prioritized,
    solve_prioritized_with_restarts,
)
from evaluation.metrics import sum_of_individual_costs, validate_solution

# A corridor of three cells with a one-cell alcove in the middle:
#   (0,0) (1,0) (2,0) corridor, (1,1) alcove.
# Two agents must swap ends.  They can only pass via the alcove.
ALCOVE = GridMap.from_ascii("...\n@.@")
ALCOVE_STARTS = [(0, 0), (2, 0)]
ALCOVE_GOALS = [(2, 0), (0, 0)]


# --------------------------------------------------------------------------- #
#  Independent A*
# --------------------------------------------------------------------------- #
def test_independent_finds_paths_and_reports_conflicts():
    grid = GridMap.from_ascii(".....\n.....")
    starts = [(0, 0), (4, 0)]
    goals = [(4, 0), (0, 0)]  # they must swap -> independent paths collide
    result = solve_independent(grid, starts, goals)
    assert result.paths and len(result.paths) == 2
    assert result.success is False
    assert result.conflicts_final > 0
    assert result.soc == sum(len(p) - 1 for p in result.paths)


def test_independent_on_the_alcove_instance():
    result = solve_independent(ALCOVE, ALCOVE_STARTS, ALCOVE_GOALS)
    # Both shortest paths use (1,0) at t=1 -> at least one conflict.
    assert result.success is False
    assert result.conflicts_final >= 1
    assert result.soc == 4  # 2 + 2, the SIC lower bound


def test_independent_reports_unreachable_goal():
    grid = GridMap.from_ascii("..@..\n..@..")
    result = solve_independent(grid, [(0, 0)], [(4, 0)])
    assert result.success is False
    assert result.status == "no_solution"


# --------------------------------------------------------------------------- #
#  Prioritized Planning
# --------------------------------------------------------------------------- #
def test_prioritized_succeeds_on_a_trivial_instance():
    grid = GridMap.from_ascii(".....\n.....\n.....\n.....\n.....")
    starts, goals = [(0, 0), (0, 4)], [(4, 0), (4, 4)]
    result = solve_prioritized(grid, starts, goals)
    assert result.success and result.status == STATUS_OK
    assert validate_solution(grid, starts, goals, result.paths).valid
    assert result.soc == 8


def test_prioritized_is_conflict_free_by_construction():
    for seed in range(15):
        scenario = generate_scenario(16, 16, 6, 0.15, "random", "uniform", seed=seed)
        result = solve_prioritized(
            scenario.grid, scenario.starts, scenario.goals, rng=random.Random(seed)
        )
        if result.success:
            report = validate_solution(scenario.grid, scenario.starts, scenario.goals, result.paths)
            assert report.valid, report.problems


def test_prioritized_fails_on_the_alcove_instance_for_both_orders():
    """Documented failure case: PP is incomplete, the instance is solvable."""
    for order in ("index", "reverse"):
        result = solve_prioritized(ALCOVE, ALCOVE_STARTS, ALCOVE_GOALS, order=order)
        assert result.success is False, order
        assert result.status == STATUS_NO_SOLUTION
        assert result.details["failed_agent"] in (0, 1)


def test_second_agent_follows_the_first():
    """Both agents move right along a corridor: the follower must not overtake."""
    grid = GridMap.from_ascii("....")
    starts = [(0, 0), (1, 0)]
    goals = [(2, 0), (3, 0)]
    result = solve_prioritized(grid, starts, goals, order="index")
    assert result.success
    assert result.paths == [[(0, 0), (1, 0), (2, 0)], [(1, 0), (2, 0), (3, 0)]]
    assert result.soc == 4
    assert validate_solution(grid, starts, goals, result.paths).valid


def test_prioritized_refuses_an_impossible_corridor_swap():
    # Agent 0 must end where agent 1 starts and vice versa, in a corridor with
    # no passing place: Prioritized Planning correctly reports failure here.
    grid = GridMap.from_ascii("....")
    starts = [(0, 0), (3, 0)]
    goals = [(3, 0), (2, 0)]
    result = solve_prioritized(grid, starts, goals, order="index")
    assert result.success is False
    assert result.status == STATUS_NO_SOLUTION


def test_all_priority_orders_run_and_are_reproducible():
    scenario = generate_scenario(16, 16, 8, 0.2, "random", "uniform", seed=5)
    for order in PRIORITY_ORDERS:
        first = solve_prioritized(
            scenario.grid, scenario.starts, scenario.goals, order=order, rng=random.Random(0)
        )
        second = solve_prioritized(
            scenario.grid, scenario.starts, scenario.goals, order=order, rng=random.Random(0)
        )
        assert first.success == second.success
        assert first.soc == second.soc
        assert first.priority_order == second.priority_order
        if first.success:
            assert validate_solution(
                scenario.grid, scenario.starts, scenario.goals, first.paths
            ).valid


def test_unknown_priority_order_raises():
    grid = GridMap.from_ascii("...")
    with pytest.raises(ValueError):
        solve_prioritized(grid, [(0, 0)], [(2, 0)], order="does_not_exist")


def test_prioritized_cost_is_at_least_sic():
    scenario = generate_scenario(20, 20, 6, 0.2, "random", "uniform", seed=11)
    result = solve_prioritized(scenario.grid, scenario.starts, scenario.goals)
    if result.success:
        sic = sum_of_individual_costs(scenario.grid, scenario.starts, scenario.goals)
        assert result.soc >= sic


def test_restarts_extension_can_only_do_better_than_a_single_order():
    scenario = generate_scenario(16, 16, 8, 0.2, "random", "uniform", seed=21)
    single = solve_prioritized(scenario.grid, scenario.starts, scenario.goals, order="index")
    restarted = solve_prioritized_with_restarts(scenario.grid, scenario.starts, scenario.goals)
    assert restarted.success >= single.success
    if restarted.success:
        assert validate_solution(
            scenario.grid, scenario.starts, scenario.goals, restarted.paths
        ).valid
