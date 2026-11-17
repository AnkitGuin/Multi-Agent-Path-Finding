"""Compare the scalable interval sweep with a simple independent pair oracle."""
import itertools
import random
import pytest
from simulation.monitor import Occupancy, detect_collisions


@pytest.mark.parametrize("seed", range(20))
def test_sweep_has_exact_pair_coverage_at_every_atomic_interval(seed):
    rng = random.Random(seed)
    intervals = []
    for agent in range(5):
        for k in range(8):
            start = k*2 + rng.random()
            intervals.append(Occupancy(agent, frozenset(((rng.randrange(4), 0),)), start, start+1))
    rng.shuffle(intervals)
    collisions = detect_collisions(intervals)
    endpoints = sorted({v for item in intervals for v in (item.start, item.end)})
    for a, b in zip(endpoints, endpoints[1:]):
        t = (a+b)/2
        occupied = [v for v in intervals if v.start <= t < v.end]
        expected = {tuple(sorted((u.agent_id, v.agent_id)))
                    for u, v in itertools.combinations(occupied, 2)
                    if u.agent_id != v.agent_id and u.resources & v.resources}
        actual = {c.agents for c in collisions if c.start <= t < c.end}
        assert actual == expected
