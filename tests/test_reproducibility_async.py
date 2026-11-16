from dataclasses import replace
from copy import deepcopy
import json
import pytest
from agents.interfaces import AgentDecision
from environment.grid import GridMap, Scenario
from evaluation.replay_async import verify_replay
from simulation.episode import EpisodeConfig, run_episode
from simulation.fixtures import ScriptedPolicy, smoke_cases


def execute(scenario, scripts, config):
    return run_episode(scenario, tuple(ScriptedPolicy(i, s, True) for i, s in enumerate(scripts)),
                       config, method="scripted_validation_fixture", oracle_access=True)


@pytest.mark.parametrize("case", list(smoke_cases()), ids=lambda c: c[0].name)
def test_analytic_cases_replay_and_repeat(case):
    scenario, scripts, config, expected = case
    a, b = execute(scenario, scripts, config), execute(scenario, scripts, config)
    assert a["termination_reason"] == expected
    assert verify_replay(json.loads(json.dumps(a)))["verified"]
    for row in (a, b):
        row.pop("planning_cpu_seconds")
        row.pop("sim_wall_seconds")
    assert a == b


def test_heterogeneous_analytic_time_and_distance():
    scenario, scripts, config, _ = next(smoke_cases())
    row = execute(scenario, scripts, config)
    assert row["executed_distance_soc"] == 6
    assert row["executed_time_soc"] == 9
    assert row["makespan"] == 6 and row["total_wait_time"] == 0


def test_deadline_censors_in_progress_move_and_does_not_prove_infeasibility():
    scenario, scripts, config, _ = list(smoke_cases())[-1]
    row = execute(scenario, scripts, config)
    assert row["executed_distance_soc"] == pytest.approx(0.4)
    assert row["executed_time_soc"] == 2 and row["censored"]
    assert row["makespan"] is None and row["deadlock_flag"] is None


def test_goal_at_exact_deadline_succeeds_and_start_at_goal_stays():
    s = Scenario(GridMap(3, 1), [(0, 0), (2, 0)], [(1, 0), (2, 0)])
    row = execute(s, [[(1, 0)], [(1, 0)]], EpisodeConfig(horizon=1))
    assert row["termination_reason"] == "success"
    assert row["per_agent_arrival"] == [1, 0]


def test_collision_exactly_at_deadline_is_not_missed():
    s = Scenario(GridMap(3, 1), [(0, 0), (2, 0)], [(2, 0), (1, 0)])
    row = execute(s, [[(1, 0)], [(2, 0), (1, 0)]],
                  EpisodeConfig(horizon=1, durations=(1, 1)))
    # First agent occupies cell 1 while second begins a move exactly at t=1.
    assert row["termination_reason"] == "collision"
    assert verify_replay(row)["verified"]


def test_unverified_attempt_is_counted_without_hidden_map_disclosure():
    s = Scenario(GridMap(3, 1), [(0, 0)], [(2, 0)])
    row = execute(s, [[(1, 0)]], EpisodeConfig(horizon=1, sensor_radius=0))
    assert row["unsafe_move_attempts"] == 1 and row["collision_count"] == 0
    assert row["termination_reason"] == "timeout"


def test_policy_exception_is_failure_data():
    class Broken:
        def decide(self, observation, messages):
            raise RuntimeError("deliberate validation fault")
    s = Scenario(GridMap(3, 1), [(0, 0)], [(2, 0)])
    row = run_episode(s, (Broken(),), EpisodeConfig())
    assert row["termination_reason"] == "agent_error" and row["error"]
    assert verify_replay(row)["verified"]


@pytest.mark.parametrize("key,value", [("executed_time_soc", 999),
                                      ("collision_count", 999),
                                      ("termination_reason", "infeasible"),
                                      ("makespan", 999),
                                      ("config_hash", "altered")])
def test_independent_replay_rejects_corrupted_results(key, value):
    scenario, scripts, config, _ = next(smoke_cases())
    row = deepcopy(execute(scenario, scripts, config))
    row[key] = value
    with pytest.raises(AssertionError):
        verify_replay(row)


@pytest.mark.parametrize("seed", range(20))
def test_seeded_duration_and_message_fuzz_preserves_accounting(seed):
    scenario, scripts, config, _ = next(smoke_cases())
    config = replace(config, duration_seed=seed, duration_jitter=3,
                     network=replace(config.network, seed=seed, loss=seed/20,
                                     max_latency=5, duplication=0.5))
    row = execute(scenario, scripts, config)
    assert verify_replay(row)["verified"]
    assert row["collision_count"] == 0
    assert row["completed_agents"] == 2
