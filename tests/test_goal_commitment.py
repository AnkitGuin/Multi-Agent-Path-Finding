"""Regression for the three pre-existing PP failures captured in the audit."""
from environment.grid import GridMap
from planning.astar import ReservationTable, ReservationVerifier, space_time_astar
from planning.astar import Constraints, ConstraintVerifier
from evaluation.metrics import validate_solution


def test_first_goal_entry_must_allow_permanent_occupancy():
    grid = GridMap.from_ascii("...\n...")
    table = ReservationTable()
    # Our goal (1,0) is free early, but a higher-priority agent will pass it.
    higher = [(2, 0), (2, 0), (2, 0), (1, 0), (0, 0), (0, 1)]
    table.add_path(higher)
    result = space_time_astar(grid, (1, 1), (1, 0), ReservationVerifier(table))
    assert result.path is not None
    assert result.path.index((1, 0)) == len(result.path) - 1
    assert validate_solution(grid, [(2, 0), (1, 1)], [(0, 1), (1, 0)],
                             [higher, result.path]).valid


def test_initial_goal_cannot_be_vacated_to_evade_future_constraint():
    constraints = Constraints.empty()
    constraints.add_vertex((0, 0), 2)
    result = space_time_astar(GridMap(2, 1), (0, 0), (0, 0),
                             ConstraintVerifier(constraints))
    assert result.path is None
