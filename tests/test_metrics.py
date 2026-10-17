"""Tests for the evaluation layer: metrics, validation and aggregation."""

import random

import pytest

from environment.generators import generate_scenario
from environment.grid import GridMap
from evaluation.metrics import (
    check_planner_result,
    conflict_counts,
    makespan,
    path_cost,
    soc_optimality_gap,
    sum_of_costs,
    sum_of_individual_costs,
    validate_solution,
)
from planning.common import STATUS_CONFLICT, STATUS_OK, PlannerResult
from planning.independent import solve_independent
from planning.prioritized import solve_prioritized


def test_path_cost_and_aggregates():
    paths = [[(0, 0), (1, 0), (2, 0)], [(0, 1)]]
    assert path_cost(paths[0]) == 2
    assert path_cost(paths[1]) == 0
    assert sum_of_costs(paths) == 2
    assert makespan(paths) == 2


def test_sic_and_gap():
    grid = GridMap.from_ascii(".....\n.....")
    starts, goals = [(0, 0), (1, 0)], [(4, 0), (3, 0)]
    sic = sum_of_individual_costs(grid, starts, goals)
    assert sic == 4 + 2
    assert soc_optimality_gap(6, 6) == 0.0
    assert soc_optimality_gap(9, 6) == pytest.approx(0.5)
    assert soc_optimality_gap(None, 6) is None


def test_validation_accepts_a_correct_plan():
    grid = GridMap.from_ascii(".....\n.....")
    starts, goals = [(0, 0), (0, 1)], [(1, 0), (1, 1)]
    paths = [[(0, 0), (1, 0)], [(0, 1), (1, 1)]]
    report = validate_solution(grid, starts, goals, paths)
    assert report.valid and not report.problems


def test_validation_rejects_leaving_a_goal_after_arrival():
    grid = GridMap.from_ascii("...")
    report = validate_solution(
        grid, [(0, 0)], [(1, 0)], [[(0, 0), (1, 0), (2, 0), (1, 0)]]
    )
    assert not report.valid
    assert any("leaves goal" in problem for problem in report.problems)


def test_validation_rejects_wrong_start_goal_and_obstacles():
    grid = GridMap.from_ascii("..@..\n.....")
    starts, goals = [(0, 0), (0, 1)], [(1, 0), (4, 1)]
    paths = [[(1, 0), (1, 0)], [(0, 1), (1, 1), (2, 1), (3, 1), (4, 1)]]
    report = validate_solution(grid, starts, goals, paths)
    assert not report.valid
    assert any("starts at" in p for p in report.problems)

    bad = [[(0, 0), (1, 0), (2, 0)], [(0, 1), (1, 1)]]
    report = validate_solution(grid, starts, goals, bad)
    assert not report.valid
    assert any("blocked" in p for p in report.problems)


def test_validation_rejects_illegal_moves():
    grid = GridMap.from_ascii(".....")
    report = validate_solution(grid, [(0, 0)], [(2, 0)], [[(0, 0), (2, 0)]])
    assert not report.valid
    assert any("illegal move" in p for p in report.problems)


def test_validation_counts_remaining_conflicts():
    grid = GridMap.from_ascii(".....")
    paths = [[(0, 0), (1, 0)], [(2, 0), (1, 0)]]
    report = validate_solution(grid, [(0, 0), (2, 0)], [(1, 0), (1, 0)], paths)
    assert not report.valid
    assert report.num_vertex_conflicts == 1
    assert report.num_edge_conflicts == 0


def test_conflict_counts_split_by_type():
    paths = [[(0, 0), (1, 0)], [(1, 0), (0, 0)]]
    counts = conflict_counts(paths)
    assert counts == {"total": 1, "vertex": 0, "edge": 1}


def test_check_planner_result_downgrades_a_bad_claim():
    scenario = generate_scenario(8, 8, 2, 0.0, "random", "uniform", seed=1)
    # Pretend a planner claimed success with a conflicting plan.
    bogus = PlannerResult(
        algorithm="Fake",
        success=True,
        status=STATUS_OK,
        paths=[scenario.starts, scenario.starts],
        soc=0,
        makespan=0,
    )
    checked = check_planner_result(scenario, bogus)
    assert checked.success is False
    assert checked.status == "invalid"
    assert "validation_problems" in checked.details


def test_check_planner_result_keeps_a_good_claim():
    scenario = generate_scenario(16, 16, 5, 0.2, "random", "uniform", seed=2)
    result = solve_prioritized(scenario.grid, scenario.starts, scenario.goals)
    if result.success:
        checked = check_planner_result(scenario, result)
        assert checked.success and checked.status == STATUS_OK


def test_end_to_end_record_contains_the_expected_keys():
    from evaluation.metrics import result_record

    scenario = generate_scenario(16, 16, 5, 0.2, "random", "uniform", seed=3)
    result = solve_independent(scenario.grid, scenario.starts, scenario.goals)
    row = result_record(scenario, result, sic=42)
    for key in ("instance", "algorithm", "success", "status", "runtime_sec", "soc", "num_agents"):
        assert key in row
    assert row["num_agents"] == 5
