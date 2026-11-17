"""Optimistic A* using only an agent's timestamped map facts and known bounds."""
import heapq
import itertools
from .belief import Belief
from .interfaces import Cell


def neighbors(cell: Cell, width: int, height: int):
    x, y = cell
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        nxt = (x+dx, y+dy)
        if 0 <= nxt[0] < width and 0 <= nxt[1] < height:
            yield nxt


def optimistic_path(belief: Belief, width: int, height: int, start: Cell,
                    goal: Cell, avoid: frozenset[Cell] = frozenset()):
    """Unknown terrain has unit speculative cost, never verified-free status.

Only the next step can execute, and only if locally sensed free. No full-grid
distance table, global congestion feature or simulator reference is available.
"""
    heuristic = lambda c: abs(c[0]-goal[0]) + abs(c[1]-goal[1])
    counter = itertools.count()
    heap = [(heuristic(start), heuristic(start), next(counter), start)]
    costs, parents = {start: 0}, {}
    closed = set()
    while heap:
        _, _, _, cell = heapq.heappop(heap)
        if cell in closed:
            continue
        if cell == goal:
            path = [cell]
            while cell in parents:
                cell = parents[cell]
                path.append(cell)
            return list(reversed(path))
        closed.add(cell)
        for nxt in neighbors(cell, width, height):
            if belief.state(nxt) == "blocked" or nxt in avoid:
                continue
            cost = costs[cell] + 1
            if cost < costs.get(nxt, float("inf")):
                costs[nxt], parents[nxt] = cost, cell
                heapq.heappush(heap, (cost+heuristic(nxt), heuristic(nxt), next(counter), nxt))
    return None
