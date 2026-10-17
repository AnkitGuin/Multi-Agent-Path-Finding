"""Unit tests for single-agent A* and the time-expanded A*.

These tests are the foundation of everything else: if the low level is wrong,
every MAPF metric is wrong.
"""

import pytest

from planning.astar import (
    ConstraintVerifier,
    Constraints,
    ReservationTable,
    ReservationVerifier,
    astar,
    build_heuristic,
    manhattan_heuristic,
    space_time_astar,
    true_distance_heuristic,
)

EMPTY = None  # placeholder, built in fixtures below


def grid_from(text):
    from environment.grid import GridMap

    return GridMap.from_ascii(text)


# --------------------------------------------------------------------------- #
#  Static A*
# --------------------------------------------------------------------------- #
def test_astar_on_empty_grid():
    grid = grid_from(".....\n.....\n.....")
    path = astar(grid, (0, 0), (4, 2))
    assert path[0] == (0, 0) and path[-1] == (4, 2)
    assert len(path) - 1 == 6  # 4 right + 2 down


def test_astar_returns_none_when_unreachable():
    grid = grid_from("..@..\n..@..\n..@..")
    assert astar(grid, (0, 0), (4, 0)) is None


def test_astar_start_equals_goal():
    grid = grid_from("...")
    assert astar(grid, (1, 0), (1, 0)) == [(1, 0)]


def test_astar_avoids_obstacles():
    # A wall with a single gap on the left: the optimal route must use the gap.
    grid = grid_from(
        """
        .@...
        .@...
        .....
        """
    )
    path = astar(grid, (0, 0), (4, 0))
    assert path is not None
    # the wall at column 1 blocks the direct route: down, right, up
    assert len(path) - 1 == 8
    assert all(grid.is_free(c) for c in path)


def test_astar_is_optimal_against_bfs():
    import random
    from collections import deque

    from environment.generators import generate_grid

    for seed in range(8):
        grid = generate_grid(20, 20, 0.25, "random", rng=random.Random(seed))
        free = grid.free_cells
        rng = random.Random(seed + 100)
        start, goal = rng.sample(free, 2)
        # reference: BFS from start
        dist = {start: 0}
        queue = deque([start])
        while queue:
            cell = queue.popleft()
            for nxt in grid.neighbors(cell):
                if nxt not in dist:
                    dist[nxt] = dist[cell] + 1
                    queue.append(nxt)
        path = astar(grid, start, goal)
        assert path is not None
        assert len(path) - 1 == dist[goal]


def test_manhattan_and_true_distance_agree_on_empty_grid():
    grid = grid_from(".....\n.....\n.....")
    goal = (4, 2)
    td = true_distance_heuristic(grid, goal)
    mh = manhattan_heuristic(grid, goal)
    for cell in grid.free_cells:
        assert td(cell) == mh(cell)


def test_true_distance_dominates_manhattan_with_obstacles():
    # A wall across row 1 with a single gap at the right-hand side: reaching the
    # bottom-left corner costs far more than the Manhattan distance suggests.
    grid = grid_from(
        """
        .....
        @@@@.
        .....
        """
    )
    goal = (0, 2)
    td = true_distance_heuristic(grid, goal)
    mh = manhattan_heuristic(grid, goal)
    assert td((0, 0)) == 10
    assert mh((0, 0)) == 2
    assert td((0, 0)) > mh((0, 0))


def test_heuristic_kind_switch():
    grid = grid_from(".....")
    h = build_heuristic(grid, (4, 0), "manhattan")
    assert h((0, 0)) == 4


# --------------------------------------------------------------------------- #
#  Time-expanded A*
# --------------------------------------------------------------------------- #
def test_space_time_astar_without_restrictions_matches_static_astar():
    grid = grid_from(".....\n..@..\n.....")
    path_s = astar(grid, (0, 0), (4, 0))
    result = space_time_astar(grid, (0, 0), (4, 0))
    assert result.path is not None
    assert len(result.path) - 1 == len(path_s) - 1


def test_vertex_constraint_forces_a_longer_path():
    # Corridor: (0,0) (1,0) (2,0); a constraint on (1,0) at t=1 forces a wait.
    grid = grid_from("...")
    constraints = Constraints.empty()
    constraints.add_vertex((1, 0), 1)
    result = space_time_astar(grid, (0, 0), (2, 0), verifier=ConstraintVerifier(constraints))
    assert result.path == [(0, 0), (0, 0), (1, 0), (2, 0)]


def test_edge_constraint_forces_alternative_move():
    # 2x2 block: going (0,0)->(1,0) at t=1 is forbidden, go down first.
    grid = grid_from("..\n..")
    constraints = Constraints.empty()
    constraints.add_edge((0, 0), (1, 0), 1)
    result = space_time_astar(grid, (0, 0), (1, 0), verifier=ConstraintVerifier(constraints))
    assert result.path is not None
    assert result.path[1] != (1, 0)


def test_stay_at_target_is_respected_by_constraints():
    """Arriving early is illegal when a later constraint forbids staying there.

    The agent may not occupy (2,0) at t=3, and reaching the goal means staying
    there forever, so the earliest legal arrival is t=4 (cost 4 instead of 2).
    """
    grid = grid_from("...")
    constraints = Constraints.empty()
    constraints.add_vertex((2, 0), 3)
    result = space_time_astar(grid, (0, 0), (2, 0), verifier=ConstraintVerifier(constraints))
    assert result.path == [(0, 0), (0, 0), (0, 0), (0, 0), (2, 0)] or (
        len(result.path) - 1 == 4 and result.path[3] != (2, 0)
    )


def test_constraint_on_start_makes_problem_infeasible():
    grid = grid_from("...")
    constraints = Constraints.empty()
    constraints.add_vertex((0, 0), 0)
    result = space_time_astar(grid, (0, 0), (2, 0), verifier=ConstraintVerifier(constraints))
    assert result.path is None


def test_reservation_table_blocks_future_goal_occupancy():
    grid = grid_from(".....")
    table = ReservationTable()
    table.add_path([(4, 0), (4, 0)])  # an agent is parked at (4,0) from t=0
    result = space_time_astar(grid, (0, 0), (4, 0), verifier=ReservationVerifier(table))
    assert result.path is None, "the goal cell is permanently occupied"


def test_reservation_table_forces_a_wait_but_allows_later_passage():
    # 3x2 open grid.  Another agent briefly steps into (1,0) at t=1 and then
    # parks in the alcove (1,1); our agent must wait one step and may then pass.
    grid = grid_from("...\n...")
    table = ReservationTable()
    table.add_path([(1, 1), (1, 0), (1, 1)])
    result = space_time_astar(grid, (0, 0), (2, 0), verifier=ReservationVerifier(table))
    assert result.path == [(0, 0), (0, 0), (1, 0), (2, 0)]


def test_edge_reservation_prevents_swapping():
    grid = grid_from("..")
    table = ReservationTable()
    table.add_path([(1, 0), (0, 0)])  # other agent moves right -> left at t=1
    result = space_time_astar(grid, (0, 0), (1, 0), verifier=ReservationVerifier(table))
    # The swap is forbidden; waiting is also forbidden (goal occupied at t>=1?).
    # (1,0) is permanently occupied from t=1, so no valid path exists.
    assert result.path is None
