"""Weak local-information diagnostics; neither guarantees coordination."""
from dataclasses import asdict
import json
from agents.belief import Belief
from agents.interfaces import AgentDecision, OutgoingMessage
from agents.local_search import optimistic_path


class IndependentLocal:
    def __init__(self, ego_id, goal, width, height, *, observed_yield=False,
                 broadcast_period=None):
        self.ego_id, self.goal = ego_id, goal
        self.width, self.height = width, height
        self.belief = Belief(ego_id)
        self.observed_yield = observed_yield
        self.broadcast_period = broadcast_period
        self.last_send = {}
        self.replans = 0

    def decide(self, obs, messages):
        self.belief.observe(obs)
        for msg in messages:
            self.belief.receive(msg, obs.event_time)
        self.replans += 1
        path = optimistic_path(self.belief, self.width, self.height, obs.ego_pose, self.goal)
        target = path[1] if path and len(path) > 1 else obs.ego_pose
        outgoing = []
        for peer in obs.visible_agents:
            if self.broadcast_period is not None and obs.event_time - self.last_send.get(peer.agent_id, -1e30) >= self.broadcast_period:
                outgoing.append(OutgoingMessage(peer.agent_id, "MAP", json.dumps(
                    {"cells": [asdict(f) for f in obs.visible_cells]})))
                self.last_send[peer.agent_id] = obs.event_time
        verified = {f.cell for f in obs.visible_cells if f.state == "free"}
        occupied = {c for peer in obs.visible_agents for c in peer.occupied_cells}
        if target not in verified or self.observed_yield and target in occupied:
            target = obs.ego_pose
        return AgentDecision("wait" if target == obs.ego_pose else "move", target, tuple(outgoing))
