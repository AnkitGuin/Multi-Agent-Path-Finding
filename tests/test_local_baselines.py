import json
import pytest
from agents.belief import Belief
from agents.interfaces import CellFact, Message
from agents.local_search import optimistic_path
from agents.protocols import Claims
from baselines.local_independent import IndependentLocal
from baselines.local_reservation import LocalReservation
from baselines.pibt_native import run_native
from environment.grid import GridMap, Scenario
from simulation.episode import EpisodeConfig, run_episode
from simulation.communication import NetworkConfig
from simulation.sensors import sense
from simulation.world import World
from evaluation.replay_async import verify_replay


def packet(sender, recipient, kind, epoch, **body):
    return Message(sender, recipient, kind, 0, 0, 0, json.dumps(dict(epoch=epoch, **body)))


def test_local_search_uses_only_observed_walls_and_exploration_is_speculative():
    belief = Belief(0)
    assert optimistic_path(belief, 4, 2, (0, 0), (3, 0))[1] == (1, 0)
    assert belief.state((1, 0)) == "unknown"
    belief.update(CellFact((1, 0), "blocked", 0, 0))
    assert optimistic_path(belief, 4, 2, (0, 0), (3, 0))[1] == (0, 1)


def test_duplicate_request_resends_lost_grant_and_release_fences_old_request():
    c = Claims(1)
    request = packet(0, 1, "REQUEST", 1, source=[0, 0], target=[1, 0])
    assert c.receive(request, (2, 0))[0].kind == "GRANT"
    assert c.receive(request, (2, 0))[0].kind == "GRANT"
    assert len(c.promises) == 1
    assert c.receive(packet(0, 1, "RELEASE", 1), (2, 0))[0].kind == "ACK"
    assert not c.promises
    assert c.receive(request, (2, 0))[0].kind == "REJECT"


def test_grants_never_expire_and_conflicting_requests_cannot_both_win():
    c = Claims(2)
    first = packet(0, 2, "REQUEST", 1, source=[0, 0], target=[1, 0])
    second = packet(1, 2, "REQUEST", 1, source=[2, 0], target=[1, 0])
    assert c.receive(first, (1, 1))[0].kind == "GRANT"
    assert c.receive(second, (1, 1))[0].kind == "REJECT"
    assert (0, 1) in c.promises  # no simulated passage of time can release this


def test_release_before_request_and_duplicate_ack_are_idempotent():
    c = Claims(1)
    c.receive(packet(0, 1, "RELEASE", 5), (2, 0))
    assert c.receive(packet(0, 1, "REQUEST", 4, source=[0, 0], target=[1, 0]), (2, 0))[0].kind == "REJECT"
    c.receive(packet(0, 1, "ACK", 5), (2, 0))
    assert not c.promises


def test_late_grant_cannot_authorize_canceled_epoch():
    c = Claims(1)
    c.propose((0, 0), (1, 0), {0})
    c.cancel()
    c.propose((0, 0), (0, 1), {0})
    c.receive(packet(0, 1, "GRANT", 1), (0, 0))
    assert not c.can_commit()


def test_own_committed_move_cannot_be_canceled_by_timeout():
    c = Claims(0)
    c.propose((0, 0), (1, 0), set())
    c.own.committed = True
    with pytest.raises(ValueError):
        c.cancel()
    with pytest.raises(ValueError):
        c.completed((0, 0))
    c.completed((1, 0))
    assert c.own is None


@pytest.mark.parametrize("loss", [0, .1, .5, 1])
@pytest.mark.parametrize("seed", range(10))
def test_local_claims_adversarial_corridor_safety_and_replay(loss, seed):
    s = Scenario(GridMap(5, 2), [(0, 0), (4, 0), (2, 1)], [(4, 0), (0, 0), (2, 0)])
    policies = tuple(LocalReservation(i, g, 5, 2) for i, g in enumerate(s.goals))
    c = EpisodeConfig(horizon=25, sensor_radius=2, duration_jitter=2,
                      duration_seed=seed, wait_duration=.5,
                      network=NetworkConfig(seed=seed, radius=3, max_latency=2, loss=loss, duplication=.5))
    row = run_episode(s, policies, c)
    assert row["collision_count"] == row["unsafe_move_attempts"] == 0
    assert row["termination_reason"] in {"success", "timeout"}
    assert verify_replay(row)["verified"]


def test_independent_local_collision_is_not_silently_shielded():
    s = Scenario(GridMap(3, 1), [(0, 0), (2, 0)], [(2, 0), (0, 0)])
    row = run_episode(s, tuple(IndependentLocal(i, g, 3, 1) for i, g in enumerate(s.goals)), EpisodeConfig())
    assert row["termination_reason"] == "collision"


def test_official_pibt_non_square_coordinate_conversion_and_validation():
    s = Scenario(GridMap(6, 3), [(0, 0), (5, 0)], [(5, 2), (0, 2)])
    row = run_native(s, horizon=50)
    assert row["status"] == "success" and row["collision_count"] == 0
    assert row["configs"][0] == s.starts and row["configs"][-1] == s.goals


def test_agents_at_goals_still_service_grants_without_changing_arrival_cost():
    s = Scenario(GridMap(5, 1), [(0, 0), (2, 0), (4, 0)], [(1, 0), (3, 0), (4, 0)])
    policies = tuple(LocalReservation(i, g, 5, 1) for i, g in enumerate(s.goals))
    row = run_episode(s, policies, EpisodeConfig(horizon=10, sensor_radius=2, wait_duration=.5))
    assert row["termination_reason"] == "success"
    assert row["per_agent_arrival"][2] == 0
    assert verify_replay(row)["verified"]


@pytest.mark.parametrize("policy_type", [IndependentLocal, LocalReservation])
def test_hidden_wall_counterfactual_cannot_change_actual_policy_decision(policy_type):
    a = World(GridMap(7, 2), ((0, 0),))
    b = World(GridMap(7, 2, {(6, 0)}), ((0, 0),))
    one, two = policy_type(0, (5, 0), 7, 2), policy_type(0, (5, 0), 7, 2)
    obs_a, obs_b = sense(a, 0, 0, 2), sense(b, 0, 0, 2)
    assert obs_a == obs_b
    assert one.decide(obs_a, ()) == two.decide(obs_b, ())
    assert one.belief.state((6, 0)) == two.belief.state((6, 0)) == "unknown"


def test_lost_release_and_ack_require_explicit_retries_without_silent_clearance():
    a, b = Claims(0), Claims(1)
    a.propose((0, 0), (1, 0), {1})
    request = packet(0, 1, "REQUEST", 1, source=[0, 0], target=[1, 0])
    b.receive(request, (2, 0))
    a.receive(packet(1, 0, "GRANT", 1), (0, 0))
    a.own.committed = True
    a.completed((1, 0))
    release, = a.release_retries()
    assert b.promises  # first release lost: occupancy promise remains held
    assert a.release_retries() == [release]
    b.receive(packet(0, 1, "RELEASE", 1), (2, 0))
    assert not b.promises and a.awaiting_ack  # ACK lost: requester retries
    b.receive(packet(0, 1, "RELEASE", 1), (2, 0))
    a.receive(packet(1, 0, "ACK", 1), (1, 0))
    assert not a.awaiting_ack
