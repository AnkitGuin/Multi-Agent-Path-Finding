"""Deterministic event clock with explicit zero-delay causal microsteps."""
from dataclasses import dataclass, field
from enum import IntEnum
import heapq
import math
from typing import Any


class Phase(IntEnum):
    FINISH = 0
    DELIVER = 1
    SENSE = 2
    DECIDE = 3
    TIMEOUT = 4


@dataclass(order=True, frozen=True)
class Event:
    time: float
    cycle: int
    phase: int
    sequence: int
    kind: str = field(compare=False)
    payload: Any = field(default=None, compare=False)


class EventQueue:
    """Order by (time, causal cycle, phase, insertion sequence).

An event causing an earlier phase at its own timestamp schedules the event in
the next causal cycle. Thus no delivery predates its send, including delay=0.
"""
    def __init__(self):
        self.now = 0.0
        self._heap: list[Event] = []
        self._sequence = 0
        self._current: Event | None = None

    def schedule(self, time: float, phase: Phase, kind: str, payload=None) -> Event:
        if not math.isfinite(time) or time < self.now:
            raise ValueError("event time must be finite and cannot precede clock")
        cycle = 0
        if self._current is not None and time == self.now:
            cycle = self._current.cycle + (int(phase) < self._current.phase)
        event = Event(time, cycle, int(phase), self._sequence, kind, payload)
        self._sequence += 1
        heapq.heappush(self._heap, event)
        return event

    def pop(self) -> Event:
        event = heapq.heappop(self._heap)
        self.now = event.time
        self._current = event
        return event

    def __bool__(self):
        return bool(self._heap)
