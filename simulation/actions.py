"""Duration-conflict resource model (not geometric rigid-body physics)."""
from dataclasses import dataclass
import math
from agents.interfaces import Cell


@dataclass(frozen=True)
class ActionEvent:
    agent_id: int
    source: Cell
    target: Cell
    start_time: float
    end_time: float
    action_id: int = 0

    def __post_init__(self):
        if (not math.isfinite(self.start_time) or self.start_time < 0
                or not math.isfinite(self.end_time)
                or self.end_time <= self.start_time):
            raise ValueError("action interval must be finite, positive and nonnegative")
        if sum(abs(a-b) for a, b in zip(self.source, self.target)) > 1:
            raise ValueError("action must wait or move to a 4-neighbor")

    @property
    def moving(self):
        return self.source != self.target

    @property
    def resources(self) -> frozenset[Cell]:
        return frozenset((self.source, self.target))
