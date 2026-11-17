"""Centralized dependency execution reference with explicit oracle access.

Preserve per-vertex visit order from a classical valid plan, release resources
at actual completion, and wait for predecessor departures. This is ADG-like
execution machinery, not a claimed reproduction of a particular ADG/SADG paper.
It uses full map, all paths and authoritative completions; no packet model.
"""
from collections import defaultdict
import hashlib
import heapq
import random
from evaluation.metrics import validate_solution
from simulation.monitor import Occupancy, detect_collisions
from simulation.world import World


def execute_dependencies(scenario, paths, config):
    assert validate_solution(scenario.grid, scenario.starts, scenario.goals, paths).valid
    compact = [[c for k, c in enumerate(path) if k == 0 or c != path[k-1]] for path in paths]
    visits = defaultdict(list)
    for t in range(max(map(len, paths))):
        for i, path in enumerate(paths):
            if t < len(path) and (t == 0 or path[t] != path[t-1]):
                visits[path[t]].append(i)
    world = World(scenario.grid, tuple(scenario.starts))
    cursor, released = [0]*len(paths), defaultdict(int)
    arrivals = {i: 0.0 for i, (s, g) in enumerate(zip(scenario.starts, scenario.goals)) if s == g}
    ready, move_index = [0.0]*len(paths), [0]*len(paths)
    queue, intervals, actions = [], [], []
    now = 0.0
    while len(arrivals) < len(paths):
        for i in range(len(paths)):
            if i in arrivals or i in world.active:
                continue
            target = compact[i][cursor[i]+1]
            if visits[target][released[target]] != i:
                continue
            if any(target in world.occupied(j) for j in range(len(paths)) if j != i):
                continue
            base = config.durations[0 if len(config.durations) == 1 else i]
            seed = hashlib.sha256(f"{config.duration_seed}:{i}:{move_index[i]}".encode()).digest()
            duration = base + random.Random(int.from_bytes(seed, "big")).uniform(0, config.duration_jitter)
            move_index[i] += 1
            action = world.start(i, target, now, duration, frozenset((target,)))
            if ready[i] < now:
                intervals.append(Occupancy(i, frozenset((action.source,)), ready[i], now))
            intervals.append(Occupancy(i, action.resources, now, min(action.end_time, config.horizon),
                                       (action.source, action.target)))
            actions.append(action)
            heapq.heappush(queue, (action.end_time, i, action))
        if not queue:
            now = config.horizon  # dependency cycle/stall; no global impossibility claim
            break
        time, _, action = heapq.heappop(queue)
        if time > config.horizon:
            now = config.horizon
            break
        now = time
        finished = [action]
        while queue and queue[0][0] == now:
            finished.append(heapq.heappop(queue)[2])
        for action in finished:
            i = action.agent_id
            world.finish(action, now)
            released[action.source] += 1
            cursor[i] += 1
            ready[i] = now
            if action.target == scenario.goals[i]:
                arrivals[i] = now
    for i in range(len(paths)):
        if i not in world.active and ready[i] < now:
            intervals.append(Occupancy(i, frozenset((world.positions[i],)), ready[i], now))
    collisions = detect_collisions(intervals)
    return dict(method="central_dependency_reference", oracle_access=True,
                variant="KNOWN_ASYNC_GLOBAL_DEPENDENCIES", model="duration_resources_v0.2.1",
                information="full map, all paths, authoritative actual completions; no packet network",
                status="collision" if collisions else "success" if len(arrivals) == len(paths) else "timeout",
                collision_count=len(collisions), completion_fraction=len(arrivals)/len(paths),
                elapsed_time=now, time_soc=sum(arrivals.get(i, now) for i in range(len(paths))),
                actions=[dict(agent=a.agent_id, source=a.source, target=a.target,
                              start=a.start_time, end=a.end_time) for a in actions],
                paths=paths)
