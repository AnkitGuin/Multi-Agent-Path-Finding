"""Unmodified author's PIBT, full known map, synchronous native goal semantics.

This reference can vacate goals and allows classical follows. It is NOT a
partial-map asynchronous same-information competitor or a decentralized runtime.
"""
import time
import numpy as np
from third_party.pypibt import PIBT
from planning.collisions import detect_conflicts

UPSTREAM = "a3c97f60413c6619a29a5022969896bc54877edc"


def run_native(scenario, *, seed=0, horizon=200):
    grid = np.array(scenario.grid.to_rows()) == 0
    starts = [(y, x) for x, y in scenario.starts]
    goals = [(y, x) for x, y in scenario.goals]
    started = time.perf_counter()
    configs = PIBT(grid, starts, goals, seed=seed).run(max_timestep=horizon)
    runtime = time.perf_counter() - started
    configs = [[(int(x), int(y)) for y, x in config] for config in configs]
    paths = [[q[i] for q in configs] for i in range(scenario.num_agents)]
    conflicts = detect_conflicts(paths)
    legal = all(scenario.grid.is_free(c) for path in paths for c in path)
    legal &= all(abs(a[0]-b[0])+abs(a[1]-b[1]) <= 1
                 for path in paths for a, b in zip(path, path[1:]))
    first, final, departures = [], [], 0
    for path, goal in zip(paths, scenario.goals):
        visits = [t for t, cell in enumerate(path) if cell == goal]
        first.append(visits[0] if visits else None)
        departures += sum(a == goal and b != goal for a, b in zip(path, path[1:]))
        final.append(next((t for t in range(len(path)) if all(c == goal for c in path[t:])), None))
    success = configs[-1] == scenario.goals
    return dict(schema_version=1, method="PIBT_native_author_code", oracle_access=True,
                variant="KNOWN_SYNC_GLOBAL_VACATABLE_GOALS", upstream_revision=UPSTREAM,
                status="invalid" if conflicts or not legal else "success" if success else "timeout",
                collision_count=len(conflicts), goal_departures=departures,
                first_arrivals=first, final_arrivals=final,
                final_arrival_soc=sum(final) if all(v is not None for v in final) else None,
                makespan=len(configs)-1 if success else None, runtime_seconds=runtime,
                configs=configs)
