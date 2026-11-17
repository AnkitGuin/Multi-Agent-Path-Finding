from dataclasses import FrozenInstanceError
import pytest
from agents.belief import Belief
from environment.grid import GridMap
from simulation.sensors import sense
from simulation.world import World


def test_hidden_obstacle_cannot_change_local_input_or_memory():
    clear = World(GridMap(5, 2), ((0, 0),))
    hidden = World(GridMap(5, 2, {(4, 0)}), ((0, 0),))
    assert sense(clear, 0, 0, 1) == sense(hidden, 0, 0, 1)
    a, b = Belief(0), Belief(0)
    a.observe(sense(clear, 0, 0, 1))
    b.observe(sense(hidden, 0, 0, 1))
    assert a.cells == b.cells
    assert a.state((4, 0)) == b.state((4, 0)) == "unknown"
    assert not hasattr(sense(hidden, 0, 0, 1), "grid")
    assert not hasattr(a, "world")


def test_wall_discovered_only_after_legitimate_observation():
    w = World(GridMap(5, 1, {(3, 0)}), ((0, 0),))
    b = Belief(0)
    b.observe(sense(w, 0, 0, 1))
    assert b.state((3, 0)) == "unknown"
    action = w.start(0, (1, 0), 0, 1, frozenset(((1, 0),)))
    w.finish(action, 1)
    action = w.start(0, (2, 0), 1, 1, frozenset(((2, 0),)))
    w.finish(action, 2)
    b.observe(sense(w, 0, 2, 1))
    assert b.state((3, 0)) == "blocked"


def test_manhattan_sensing_no_occlusion_and_immutable_snapshot():
    w = World(GridMap(5, 3, {(1, 1)}), ((0, 1),))
    obs = sense(w, 0, 0, 2)
    assert (2, 1) in {f.cell for f in obs.visible_cells}
    assert (2, 0) not in {f.cell for f in obs.visible_cells}
    with pytest.raises(FrozenInstanceError):
        obs.ego_pose = (1, 1)


def test_observed_moving_neighbor_has_no_goal_or_completion_time():
    w = World(GridMap(4, 1), ((0, 0), (2, 0)))
    w.start(1, (1, 0), 0, 10, frozenset(((1, 0),)))
    neighbor, = sense(w, 0, 1, 1).visible_agents
    assert neighbor.moving and neighbor.occupied_cells == ((1, 0), (2, 0))
    assert not hasattr(neighbor, "goal") and not hasattr(neighbor, "end_time")


def test_unsensed_entry_and_wall_entry_are_rejected():
    w = World(GridMap(3, 1, {(2, 0)}), ((0, 0),))
    with pytest.raises(ValueError, match="verified"):
        w.start(0, (1, 0), 0, 1, frozenset())
    with pytest.raises(ValueError, match="blocked"):
        w.start(0, (2, 0), 0, 1, frozenset(((2, 0),)))


def test_waiting_neighbor_is_stationary_even_during_an_active_wait_action():
    world = World(GridMap(3, 1), ((0, 0), (1, 0)))
    world.start(1, (1, 0), 0, 2, frozenset(((1, 0),)))
    neighbor, = sense(world, 0, 1, 1).visible_agents
    assert not neighbor.moving
    assert neighbor.occupied_cells == ((1, 0),)
