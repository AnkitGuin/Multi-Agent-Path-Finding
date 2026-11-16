"""Hand-authored validation timelines, NOT experimental MAPF competitors.

Paths are deliberately supplied by the test author (privileged guidance). The
fixture receives only local observations at runtime, and can emit sensed facts.
"""
from dataclasses import asdict
import json
from agents.belief import Belief
from agents.interfaces import AgentDecision, OutgoingMessage
from environment.grid import GridMap, Scenario
from .communication import NetworkConfig
from .episode import EpisodeConfig


class ScriptedPolicy:
    def __init__(self, agent_id, targets, broadcast=False):
        self.belief = Belief(agent_id)
        self.targets = iter(targets)
        self.broadcast = broadcast

    def decide(self, observation, messages):
        self.belief.observe(observation)
        for msg in messages:
            self.belief.receive(msg, observation.event_time)
        messages_out = ()
        if self.broadcast:
            payload = json.dumps({"cells": [asdict(f) for f in observation.visible_cells]})
            messages_out = tuple(OutgoingMessage(a.agent_id, "MAP", payload)
                                 for a in observation.visible_agents)
        target = next(self.targets, observation.ego_pose)
        return AgentDecision("wait" if target == observation.ego_pose else "move",
                             target, messages_out)


def smoke_cases():
    """Analytic traces: (scenario, scripts, config, expected status)."""
    yield (Scenario(GridMap(4, 2), [(0, 0), (0, 1)], [(3, 0), (3, 1)], name="disjoint_heterogeneous"),
           [[(1, 0), (2, 0), (3, 0)], [(1, 1), (2, 1), (3, 1)]],
           EpisodeConfig(durations=(1, 2)), "success")
    yield (Scenario(GridMap(3, 1), [(0, 0), (2, 0)], [(2, 0), (0, 0)], name="head_on_corridor"),
           [[(1, 0), (2, 0)], [(1, 0), (0, 0)]], EpisodeConfig(), "collision")
    yield (Scenario(GridMap(3, 1, {(1, 0)}), [(0, 0)], [(2, 0)], name="hidden_disconnection"),
           [[(1, 0)]], EpisodeConfig(horizon=5), "timeout")
    yield (Scenario(GridMap(3, 1), [(0, 0), (1, 0)], [(2, 0), (1, 0)], name="goal_blocks_chokepoint"),
           [[(1, 0), (2, 0)], []], EpisodeConfig(), "collision")
    yield (Scenario(GridMap(3, 2), [(0, 0), (2, 0)], [(0, 1), (2, 1)], name="delayed_lossy_map_reports"),
           [[(0, 0), (0, 0), (0, 1)], [(2, 0), (2, 0), (2, 1)]],
           EpisodeConfig(sensor_radius=3, network=NetworkConfig(seed=7, max_latency=3,
                                                               loss=0.25, duplication=0.5)),
           "success")
    yield (Scenario(GridMap(3, 1), [(0, 0)], [(2, 0)], name="duration_exceeds_deadline"),
           [[(1, 0), (2, 0)]], EpisodeConfig(horizon=2, durations=(5,)), "timeout")
