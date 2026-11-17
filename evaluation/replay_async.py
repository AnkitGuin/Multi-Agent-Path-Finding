"""Recompute validation metrics from saved authoritative logs, no policies."""
import math
from agents.interfaces import Message
from simulation.monitor import Collision, Occupancy, detect_collisions
from simulation.episode import digest, jsonable


def verify_replay(row: dict) -> dict:
    assert row["schema_version"] == 1
    assert row["scenario_hash"] == digest(row["scenario"]), "scenario hash differs"
    assert row["config_hash"] == digest(row["config"]), "config hash differs"
    end = row["elapsed_time"]
    starts = {i: tuple(c) for i, c in enumerate(row["scenario"]["starts"])}
    goals = {i: tuple(c) for i, c in enumerate(row["scenario"]["goals"])}
    n = len(starts)
    arrivals = {i: 0.0 for i in starts if starts[i] == goals[i]}
    distance = moving = 0.0
    active = {}
    positions = dict(starts)
    for event in row["events"]:
        if event["kind"] == "ACTION_START":
            a = event["action"]
            i = a["agent_id"]
            assert i not in active, "overlapping own actions"
            assert tuple(a["source"]) == positions[i], "discontinuous action trace"
            active[i] = a
            if a["source"] != a["target"]:
                elapsed = min(a["end_time"], end) - a["start_time"]
                assert elapsed >= 0
                distance += elapsed / (a["end_time"]-a["start_time"])
                moving += elapsed
        elif event["kind"] == "ACTION_FINISH":
            a = event["payload"]
            i = a["agent_id"]
            assert active[i] == a, "finish lacks matching action start"
            del active[i]
            positions[i] = tuple(a["target"])
            if positions[i] == goals[i]:
                arrivals.setdefault(i, a["end_time"])
    intervals = [Occupancy(v["agent_id"], frozenset(tuple(c) for c in v["resources"]),
                           v["start"], v["end"],
                           tuple(tuple(c) for c in v["edge"]) if v["edge"] else None)
                 for v in row["occupancy"]]
    collisions = detect_collisions(intervals)
    occupied = {i: frozenset((tuple(active[i]["source"]), tuple(active[i]["target"])))
                if i in active else frozenset((positions[i],)) for i in starts}
    for i in range(n):
        for j in range(i+1, n):
            shared = occupied[i] & occupied[j]
            if shared and not any(c.agents == (i, j) and c.end == end for c in collisions):
                collisions.append(Collision((i, j), end, end,
                                            "terminal_vertex_resource", tuple(sorted(shared))))
    assert len(collisions) == row["collision_count"], "collision count differs"
    assert jsonable(collisions) == row["collisions"], "collision intervals differ"
    assert len(arrivals) == row["completed_agents"], "arrival count differs"
    assert row["completion_fraction"] == len(arrivals)/n
    assert row["per_agent_arrival"] == [arrivals.get(i) for i in range(n)]
    all_done = len(arrivals) == n
    assert row["censored"] == (not all_done)
    assert row["makespan"] == (max(arrivals.values(), default=0) if all_done else None)
    expected = ("collision" if collisions else "agent_error" if row["error"]
                else "success" if all_done else "timeout")
    assert row["termination_reason"] == expected, "outcome differs"
    assert math.isclose(distance, row["executed_distance_soc"]), "distance differs"
    time_soc = sum(arrivals.get(i, end) for i in starts)
    assert math.isclose(time_soc, row["executed_time_soc"]), "time SOC differs"
    assert math.isclose(time_soc-moving, row["total_wait_time"], abs_tol=1e-9), "wait differs"
    for key, kinds in [("sent", {"sent", "lost"}), ("delivered", {"delivered"})]:
        messages = [Message(**e["message"]) for e in row["network_trace"] if e["event"] in kinds]
        assert len(messages) == row[f"messages_{key}"]
        assert sum(m.byte_count for m in messages) == row[f"bytes_{key}"]
    return dict(verified=True, collision_count=len(collisions), completed_agents=len(arrivals),
                executed_time_soc=time_soc, executed_distance_soc=distance)
