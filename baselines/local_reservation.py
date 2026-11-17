"""Matched local claim baselines and selective-communication research control.

All variants use identical nonexpiring grants. Selectivity changes information
broadcasts, never ownership requirements. A new algorithmic contribution is
not claimed for this standard protocol plus a communication threshold.
"""
from dataclasses import asdict
import json
from agents.belief import Belief
from agents.interfaces import AgentDecision, OutgoingMessage
from agents.local_search import optimistic_path
from agents.protocols import Claims


class LocalReservation:
    service_at_goal = True

    def __init__(self, ego_id, goal, width, height, *, communication="periodic",
                 period=2.0, freshness=4.0, incremental=True):
        if communication not in {"periodic", "always", "selective", "none"}:
            raise ValueError("unknown broadcast control")
        if period <= 0 or freshness <= 0:
            raise ValueError("period and freshness must be positive")
        self.ego_id, self.goal, self.width, self.height = ego_id, goal, width, height
        self.belief = Belief(ego_id)
        self.claims = Claims(ego_id)
        self.communication, self.period, self.freshness = communication, period, freshness
        self.incremental = incremental
        self.last_send, self.sent_walls = {}, {}
        self.path = None
        self.replans = 0

    def _information(self, obs):
        outgoing = []
        walls = frozenset(c for c, f in self.belief.cells.items() if f.state == "blocked")
        for peer in obs.visible_agents:
            p = peer.agent_id
            age = self.belief.age(p, "MAP", obs.event_time)
            elapsed = obs.event_time-self.last_send.get(p, -1e30)
            send = (self.communication == "always"
                    or self.communication == "periodic" and elapsed >= self.period
                    or self.communication == "selective" and
                    (walls != self.sent_walls.get(p) or age >= self.freshness and elapsed >= self.freshness))
            if send:
                outgoing.append(OutgoingMessage(p, "MAP", json.dumps({"cells": [
                    asdict(f) for _, f in sorted(self.belief.cells.items())]}, separators=(",", ":"))))
                self.last_send[p], self.sent_walls[p] = obs.event_time, walls
        return outgoing

    def decide(self, obs, messages):
        if obs.sensor_radius < 2:
            raise ValueError("local claims require two-hop sensing; use an explicit inapplicable outcome")
        self.belief.observe(obs)
        self.claims.completed(obs.ego_pose)
        outgoing = []
        for msg in messages:
            self.belief.receive(msg, obs.event_time)
            outgoing.extend(self.claims.receive(msg, obs.ego_pose))
        outgoing.extend(self.claims.release_retries())
        outgoing.extend(self._information(obs))
        if obs.ego_pose == self.goal:
            return AgentDecision("wait", messages=tuple(outgoing))
        held = frozenset(c for cells in self.claims.promises.values() for c in cells)
        if self.path and obs.ego_pose in self.path:
            self.path = self.path[self.path.index(obs.ego_pose):]
        valid_path = (self.path and self.path[0] == obs.ego_pose
                      and all(self.belief.state(c) != "blocked" and c not in held for c in self.path[1:]))
        if not self.incremental or not valid_path:
            self.path = optimistic_path(self.belief, self.width, self.height, obs.ego_pose, self.goal, held)
            self.replans += 1
        target = self.path[1] if self.path and len(self.path) > 1 else obs.ego_pose
        if self.claims.own and target != self.claims.own.target:
            self.claims.cancel()
            outgoing.extend(self.claims.release_retries())
        verified = {f.cell for f in obs.visible_cells if f.state == "free"}
        occupied = {c for a in obs.visible_agents for c in a.occupied_cells}
        if target == obs.ego_pose or target not in verified or target in occupied or target in held:
            return AgentDecision("wait", messages=tuple(outgoing))
        peers = {a.agent_id for a in obs.visible_agents}
        outgoing.extend(self.claims.propose(obs.ego_pose, target, peers))
        if self.claims.can_commit():
            self.claims.own.committed = True
            return AgentDecision("move", target, tuple(outgoing))
        return AgentDecision("wait", messages=tuple(outgoing))
