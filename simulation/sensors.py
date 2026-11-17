"""Manhattan-radius sensing, no wall occlusion, sampled when stationary.

Moving neighbors expose both occupied endpoints if either is in range. Their
goals, future actions and movement completion times are not exposed.
"""
from agents.interfaces import CellFact, Observation, VisibleAgent
from .world import World


def sense(world: World, agent_id: int, now: float, radius: int) -> Observation:
    if isinstance(radius, bool) or not isinstance(radius, int) or radius < 0:
        raise ValueError("radius must be a nonnegative integer")
    if agent_id in world.active:
        raise ValueError("ego sensing is defined only while stationary")
    x, y = world.positions[agent_id]
    cells = tuple((cx, cy)
                  for cy in range(max(0, y-radius), min(world.grid.height, y+radius+1))
                  for cx in range(max(0, x-radius), min(world.grid.width, x+radius+1))
                  if abs(cx-x) + abs(cy-y) <= radius)
    visible = frozenset(cells)
    facts = tuple(CellFact(c, "blocked" if world.grid.is_blocked(c) else "free",
                           now, agent_id) for c in cells)
    neighbors = tuple(VisibleAgent(i, tuple(sorted(world.occupied(i))),
                                   i in world.active and world.active[i].moving)
                      for i in sorted(world.positions) if i != agent_id
                      and world.occupied(i) & visible)
    return Observation(agent_id, now, (x, y), facts, neighbors, radius)
