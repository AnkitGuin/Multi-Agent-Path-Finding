"""Independent interval sweep: never consults policies or their reservations."""
from dataclasses import dataclass
import heapq
from agents.interfaces import Cell


@dataclass(frozen=True)
class Occupancy:
    agent_id: int
    resources: frozenset[Cell]
    start: float
    end: float
    edge: tuple[Cell, Cell] | None = None


@dataclass(frozen=True)
class Collision:
    agents: tuple[int, int]
    start: float
    end: float
    kind: str
    cells: tuple[Cell, ...]


def detect_collisions(intervals: list[Occupancy]) -> list[Collision]:
    """Return overlap segments, merging adjacent segments of the same pair/kind.

Intervals are half-open; a handoff at an actual completion is permissible.
These are abstract resource conflicts, not measured robot body penetration.
"""
    found = []
    active, ends = {}, []
    for identifier, b in sorted(enumerate(intervals), key=lambda item: (item[1].start, item[0])):
        while ends and ends[0][0] <= b.start:
            _, old = heapq.heappop(ends)
            active.pop(old, None)
        if b.end <= b.start:
            continue
        for a in active.values():
            if a.agent_id == b.agent_id:
                continue
            start, end = b.start, min(a.end, b.end)
            shared = a.resources & b.resources
            if not shared:
                continue
            edge = a.edge is not None and b.edge == a.edge[::-1]
            found.append(Collision(tuple(sorted((a.agent_id, b.agent_id))), start, end,
                                   "opposite_edge" if edge else "vertex_resource",
                                   tuple(sorted(shared))))
        active[identifier] = b
        heapq.heappush(ends, (b.end, identifier))
    merged: list[Collision] = []
    for item in sorted(found, key=lambda c: (c.agents, c.kind, c.cells, c.start, c.end)):
        if (merged and (merged[-1].agents, merged[-1].kind, merged[-1].cells)
                == (item.agents, item.kind, item.cells)
                and item.start <= merged[-1].end):
            old = merged.pop()
            item = Collision(old.agents, old.start, max(old.end, item.end),
                             old.kind, old.cells)
        merged.append(item)
    return sorted(merged, key=lambda c: (c.start, c.agents, c.kind))
