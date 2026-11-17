import pytest
from environment.grid import GridMap
from simulation.actions import ActionEvent
from simulation.monitor import Occupancy, detect_collisions
from simulation.world import World


def occupancy(agent, cells, start, end, edge=None):
    return Occupancy(agent, frozenset(cells), start, end, edge)


def test_hand_derived_vertex_overlap():
    a = occupancy(0, [(0, 0), (1, 0)], 0, 2)
    b = occupancy(1, [(1, 0)], 1, 3)
    collision, = detect_collisions([a, b])
    assert (collision.start, collision.end, collision.cells) == (1, 2, ((1, 0),))


def test_edge_swap_and_exact_handoff():
    a = occupancy(0, [(0, 0), (1, 0)], 0, 2, ((0, 0), (1, 0)))
    b = occupancy(1, [(0, 0), (1, 0)], 1, 3, ((1, 0), (0, 0)))
    assert detect_collisions([a, b])[0].kind == "opposite_edge"
    b = occupancy(1, [(0, 0), (1, 0)], 2, 3)
    assert not detect_collisions([a, b])


def test_delayed_departure_blocks_follower_until_actual_completion():
    leader = occupancy(0, [(1, 0), (2, 0)], 0, 5)
    follower = occupancy(1, [(0, 0), (1, 0)], 1, 2)
    assert detect_collisions([leader, follower])[0].start == 1
    assert not detect_collisions([leader, occupancy(1, [(0, 0), (1, 0)], 5, 6)])


def test_contiguous_goal_conflict_is_merged_and_self_not_counted():
    parked = occupancy(0, [(1, 0)], 0, 10)
    other = [occupancy(1, [(1, 0)], 1, 2), occupancy(1, [(1, 0)], 2, 3)]
    collision, = detect_collisions([parked, *other])
    assert (collision.start, collision.end) == (1, 3)


def test_duration_model_intentionally_disallows_classical_train():
    assert detect_collisions([occupancy(0, [(0, 0), (1, 0)], 0, 1),
                              occupancy(1, [(1, 0), (2, 0)], 0, 1)])


def test_world_keeps_resources_until_actual_finish_and_duplicate_is_safe():
    world = World(GridMap(3, 1), ((0, 0),))
    action = world.start(0, (1, 0), 0, 2, frozenset(((1, 0),)))
    assert world.occupied(0) == frozenset(((0, 0), (1, 0)))
    with pytest.raises(ValueError):
        world.finish(action, 1)
    assert world.finish(action, 2)
    assert world.occupied(0) == frozenset(((1, 0),))
    assert not world.finish(action, 2)


@pytest.mark.parametrize("duration", [0, -1, float("nan"), float("inf")])
def test_movement_duration_must_be_positive_finite(duration):
    with pytest.raises(ValueError):
        ActionEvent(0, (0, 0), (1, 0), 0, duration)


def test_world_does_not_silently_shield_colliding_moves():
    w = World(GridMap(3, 1), ((0, 0), (2, 0)))
    for i in range(2):
        w.start(i, (1, 0), 0, 1, frozenset(((1, 0),)))
    assert w.occupied(0) & w.occupied(1) == frozenset(((1, 0),))
