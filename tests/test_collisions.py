"""Unit tests for conflict detection (vertex and edge, verified separately)."""

from planning.collisions import (
    EDGE,
    VERTEX,
    Conflict,
    conflicts_per_agent,
    count_conflicts,
    detect_conflicts,
    find_first_conflict,
    has_edge_conflict,
    has_vertex_conflict,
    is_conflict_free,
    position_at,
)


def test_position_at_clamps_after_goal():
    path = [(0, 0), (1, 0), (2, 0)]
    assert position_at(path, 0) == (0, 0)
    assert position_at(path, 5) == (2, 0)


def test_vertex_conflict_detected():
    a = [(0, 0), (1, 0)]
    b = [(2, 0), (1, 0)]
    assert has_vertex_conflict(a, b, 1)
    assert not has_vertex_conflict(a, b, 0)
    conflicts = detect_conflicts([a, b])
    assert len(conflicts) == 1
    assert conflicts[0].kind == VERTEX and conflicts[0].t == 1
    assert conflicts[0].cell1 == (1, 0)


def test_edge_conflict_detected():
    a = [(0, 0), (1, 0)]
    b = [(1, 0), (0, 0)]
    assert has_vertex_conflict(a, b, 0) is False
    assert has_edge_conflict(a, b, 1)
    conflicts = detect_conflicts([a, b])
    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict.kind == EDGE
    assert conflict.t == 1
    assert (conflict.cell1, conflict.cell2) == ((0, 0), (1, 0))


def test_edge_conflict_not_reported_as_vertex():
    # Swapping agents are never in the same cell at the same timestep.
    a = [(0, 0), (1, 0)]
    b = [(1, 0), (0, 0)]
    for t in range(3):
        assert not has_vertex_conflict(a, b, t)


def test_following_is_not_a_conflict():
    # Under the standard pebble-motion assumption, entering a cell that another
    # agent has just left is legal.
    a = [(0, 0), (1, 0), (2, 0)]
    b = [(3, 0), (3, 0), (1, 0)]
    assert is_conflict_free([a, b])


def test_waiting_at_goal_blocks_the_cell_forever():
    a = [(0, 0), (1, 0)]          # parks at (1,0) from t=1 on
    b = [(2, 0), (2, 0), (1, 0)]  # arrives at (1,0) at t=2 -> conflict
    conflicts = detect_conflicts([a, b])
    assert len(conflicts) == 1 and conflicts[0].t == 2 and conflicts[0].kind == VERTEX


def test_first_conflict_is_the_earliest():
    a = [(0, 0), (1, 0), (2, 0)]
    b = [(1, 0), (0, 0), (2, 0)]  # edge conflict at t=1, vertex conflict at t=2
    conflict = find_first_conflict([a, b])
    assert conflict is not None
    assert conflict.t == 1 and conflict.kind == EDGE


def test_no_conflict_reports_none():
    a = [(0, 0), (0, 1)]
    b = [(2, 0), (2, 1)]
    assert find_first_conflict([a, b]) is None
    assert count_conflicts([a, b]) == 0
    assert is_conflict_free([a, b])


def test_conflicts_per_agent():
    a = [(0, 0), (1, 0)]
    b = [(2, 0), (1, 0)]
    c = [(5, 5), (5, 5)]
    counts = conflicts_per_agent([a, b, c], 3)
    assert counts == {0: 1, 1: 1, 2: 0}


def test_conflict_str_and_agents():
    conflict = Conflict(3, VERTEX, 0, 1, (2, 2), (2, 2))
    assert conflict.agents == (0, 1)
    assert "vertex" in str(conflict)
