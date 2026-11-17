"""Authoritative state. Policies must never receive this object.

Moves occupy both endpoint resources on [start,end). The source is released
only at actual completion. This conservative abstraction forbids overlapping
following moves; it intentionally differs from classical pebble motion.
"""
from environment.grid import GridMap
from agents.interfaces import Cell
from .actions import ActionEvent


class World:
    def __init__(self, grid: GridMap, starts: tuple[Cell, ...]):
        if not starts or len(set(starts)) != len(starts):
            raise ValueError("starts must be nonempty and unique")
        if not all(grid.is_free(c) for c in starts):
            raise ValueError("starts must be free")
        # Copy: later mutations to the caller's grid cannot change the world.
        self.grid = GridMap(grid.width, grid.height, set(grid.obstacles), grid.name)
        self.positions = dict(enumerate(starts))
        self.active: dict[int, ActionEvent] = {}
        self.completed: list[ActionEvent] = []
        self._next_action = 0
        self._ready = dict.fromkeys(self.positions, 0.0)

    def occupied(self, agent_id: int) -> frozenset[Cell]:
        action = self.active.get(agent_id)
        return action.resources if action else frozenset((self.positions[agent_id],))

    def start(self, agent_id: int, target: Cell, now: float,
              duration: float, verified_free: frozenset[Cell]) -> ActionEvent:
        if agent_id in self.active:
            raise ValueError("agent already executing an action")
        if now < self._ready[agent_id]:
            raise ValueError("action cannot precede prior physical completion")
        source = self.positions[agent_id]
        if target not in verified_free:
            raise ValueError("target has not been verified free by local sensing")
        if not self.grid.is_free(target):
            raise ValueError("target is blocked or outside bounds")
        action = ActionEvent(agent_id, source, target, now, now + duration,
                             self._next_action)
        self._next_action += 1
        # No inter-agent safety shield: unsafe plans remain visible to monitor.
        self.active[agent_id] = action
        return action

    def finish(self, action: ActionEvent, now: float) -> bool:
        if self.active.get(action.agent_id) != action:
            return False  # duplicate/stale completion is idempotent
        if now != action.end_time:
            raise ValueError("completion must use actual action end time")
        self.positions[action.agent_id] = action.target
        self.completed.append(action)
        self._ready[action.agent_id] = now
        del self.active[action.agent_id]
        return True
