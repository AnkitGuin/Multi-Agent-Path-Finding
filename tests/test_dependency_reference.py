from baselines.async_dependency import execute_dependencies
from environment.grid import GridMap, Scenario
from simulation.episode import EpisodeConfig


def test_delayed_leader_releases_source_only_after_completion():
    scenario = Scenario(GridMap(4, 1), [(0, 0), (1, 0)], [(2, 0), (3, 0)])
    paths = [[(0, 0), (1, 0), (2, 0)], [(1, 0), (2, 0), (3, 0)]]
    row = execute_dependencies(scenario, paths, EpisodeConfig(durations=(1, 3)))
    assert row["status"] == "success" and row["collision_count"] == 0
    follower = next(a for a in row["actions"] if a["agent"] == 0)
    assert follower["start"] >= 3


def test_full_rotation_is_not_misreported_as_executable_duration_plan():
    starts = [(0, 0), (1, 0), (1, 1), (0, 1)]
    goals = starts[1:]+starts[:1]
    scenario = Scenario(GridMap(2, 2), starts, goals)
    row = execute_dependencies(scenario, [[s, g] for s, g in zip(starts, goals)], EpisodeConfig())
    assert row["status"] == "timeout" and row["collision_count"] == 0
    assert row["completion_fraction"] == 0
