"""Run immutable local policies in the validated duration-resource world.

Scripted policies used by smoke validation are not proposed MAPF algorithms.
Unsuccessful episodes remain in all-episode metrics, censored at the deadline.
"""
from dataclasses import asdict, dataclass, is_dataclass
import hashlib
import json
import math
import random
import time
from agents.interfaces import LocalPolicy
from environment.grid import Scenario
from .communication import Network, NetworkConfig
from .events import EventQueue, Phase
from .monitor import Collision, Occupancy, detect_collisions
from .sensors import sense
from .world import World


@dataclass(frozen=True)
class EpisodeConfig:
    horizon: float = 20.0
    sensor_radius: int = 1
    durations: tuple[float, ...] = (1.0,)
    duration_seed: int = 0
    duration_jitter: float = 0.0
    wait_duration: float = 1.0
    max_events: int = 100000
    network: NetworkConfig = NetworkConfig()

    def __post_init__(self):
        if (not math.isfinite(self.horizon) or self.horizon <= 0
                or not math.isfinite(self.wait_duration) or self.wait_duration <= 0
                or not self.durations
                or any(not math.isfinite(v) or v <= 0 for v in self.durations)
                or not math.isfinite(self.duration_jitter) or self.duration_jitter < 0
                or isinstance(self.sensor_radius, bool)
                or not isinstance(self.sensor_radius, int) or self.sensor_radius < 0
                or not isinstance(self.max_events, int) or self.max_events < 1):
            raise ValueError("invalid episode configuration")


def jsonable(value):
    if is_dataclass(value):
        return jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return [jsonable(v) for v in sorted(value)]
    return value


def digest(value) -> str:
    return hashlib.sha256(json.dumps(jsonable(value), sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def run_episode(scenario: Scenario, policies: tuple[LocalPolicy, ...],
                config: EpisodeConfig, *, method: str = "unspecified_local_policy",
                oracle_access: bool = False) -> dict:
    n = scenario.num_agents
    if (len(policies) != n or len(scenario.goals) != n
            or len(set(scenario.goals)) != n
            or not all(scenario.grid.is_free(g) for g in scenario.goals)):
        raise ValueError("one policy and unique free goal per agent required")
    if len(config.durations) not in (1, n):
        raise ValueError("durations must be scalar or one per agent")
    world = World(scenario.grid, tuple(scenario.starts))
    queue = EventQueue()
    network = Network(queue, config.network)
    inbox = {i: [] for i in range(n)}
    contacts = {i: set() for i in range(n)}
    arrivals = {i: 0.0 for i in range(n) if scenario.starts[i] == scenario.goals[i]}
    log, intervals = [], []
    last_end = dict.fromkeys(range(n), 0.0)
    move_index = dict.fromkeys(range(n), 0)
    distance = dict.fromkeys(range(n), 0.0)
    moving_time = dict.fromkeys(range(n), 0.0)
    unsafe = decisions = 0
    cpu = 0.0
    error = None
    wall_start = time.perf_counter()
    for i in range(n):
        if i not in arrivals or getattr(policies[i], "service_at_goal", False):
            queue.schedule(0, Phase.SENSE, "SENSE", i)
    queue.schedule(config.horizon, Phase.TIMEOUT, "EPISODE_TIMEOUT")
    count = 0
    ended = 0.0
    while queue and len(arrivals) < n:
        event = queue.pop()
        if event.time > config.horizon:
            ended = config.horizon
            break
        ended = event.time
        count += 1
        if count > config.max_events:
            error = "event budget exhausted"
            break
        log.append(dict(time=event.time, cycle=event.cycle, phase=event.phase,
                        sequence=event.sequence, kind=event.kind,
                        payload=jsonable(event.payload)))
        if event.kind == "EPISODE_TIMEOUT":
            break
        if event.kind == "MESSAGE_DELIVER":
            network.delivered(event.payload)
            inbox[event.payload.recipient].append(event.payload)
            contacts[event.payload.recipient].add(event.payload.sender)
        elif event.kind == "ACTION_FINISH":
            action = event.payload
            if world.finish(action, queue.now):
                i = action.agent_id
                if action.moving:
                    distance[i] += 1
                    moving_time[i] += action.end_time - action.start_time
                if action.target == scenario.goals[i]:
                    arrivals.setdefault(i, queue.now)
                if i not in arrivals or getattr(policies[i], "service_at_goal", False):
                    queue.schedule(queue.now, Phase.SENSE, "SENSE", i)
        elif event.kind == "SENSE":
            obs = sense(world, event.payload, queue.now, config.sensor_radius)
            queue.schedule(queue.now, Phase.DECIDE, "DECIDE", obs)
        elif event.kind == "DECIDE":
            obs = event.payload
            i = obs.ego_id
            contacts[i].update(a.agent_id for a in obs.visible_agents)
            started = time.process_time()
            try:
                decision = policies[i].decide(obs, tuple(inbox[i]))
            except Exception as exc:
                error = f"agent {i}: {type(exc).__name__}: {exc}"
                break
            finally:
                cpu += time.process_time() - started
            inbox[i].clear()
            decisions += 1
            log.append(dict(time=queue.now, kind="DECISION", agent=i,
                            decision=jsonable(decision)))
            try:
                for outgoing in decision.messages:
                    # v0.2 permits release/ACK retries to legitimately remembered
                    # peers. Transport still tests actual send-time range.
                    if outgoing.recipient not in contacts[i]:
                        raise ValueError("message recipient was never locally learned")
                    network.send(i, outgoing.recipient, outgoing.kind,
                                 json.loads(outgoing.payload_json), obs.ego_pose,
                                 world.positions[outgoing.recipient])
                if decision.action_kind not in ("move", "wait"):
                    raise ValueError("unknown action kind")
                if i in arrivals and decision.action_kind != "wait":
                    raise ValueError("permanent goal cannot be vacated")
                target = decision.next_vertex if decision.action_kind == "move" else obs.ego_pose
                if target is None or (decision.action_kind == "move" and target == obs.ego_pose):
                    raise ValueError("move requires a distinct target")
                if decision.action_kind == "wait":
                    duration = config.wait_duration
                else:
                    key = f"{config.duration_seed}:{i}:{move_index[i]}".encode()
                    rng = random.Random(int.from_bytes(hashlib.sha256(key).digest(), "big"))
                    base = config.durations[0 if len(config.durations) == 1 else i]
                    duration = base + rng.uniform(0, config.duration_jitter)
                    move_index[i] += 1
                verified = frozenset(f.cell for f in obs.visible_cells if f.state == "free")
                action = world.start(i, target, queue.now, duration, verified)
            except (ValueError, TypeError, AttributeError) as exc:
                unsafe += 1
                log.append(dict(time=queue.now, kind="ACTION_FAILED", agent=i,
                                reason=str(exc)))
                action = world.start(i, obs.ego_pose, queue.now, config.wait_duration,
                                     frozenset((obs.ego_pose,)))
            if last_end[i] < action.start_time:
                intervals.append(Occupancy(i, frozenset((action.source,)),
                                           last_end[i], action.start_time))
            intervals.append(Occupancy(i, action.resources, action.start_time,
                                       min(action.end_time, config.horizon),
                                       (action.source, action.target) if action.moving else None))
            last_end[i] = action.end_time
            log.append(dict(time=queue.now, kind="ACTION_START", action=jsonable(action)))
            queue.schedule(action.end_time, Phase.FINISH, "ACTION_FINISH", action)

    # Truncate intervals if every agent finishes early or a controller errors.
    intervals = [Occupancy(v.agent_id, v.resources, v.start, min(v.end, ended), v.edge)
                 for v in intervals if v.start < ended]
    for i in range(n):
        action = world.active.get(i)
        if action and action.moving:
            elapsed = max(0.0, ended-action.start_time)
            distance[i] += elapsed / (action.end_time-action.start_time)
            moving_time[i] += elapsed
        if last_end[i] < ended:
            intervals.append(Occupancy(i, frozenset((world.positions[i],)),
                                       last_end[i], ended))
    collisions = detect_collisions(intervals)
    # Right-limit state at the deadline catches contact exactly at truncation.
    for i in range(n):
        for j in range(i+1, n):
            shared = world.occupied(i) & world.occupied(j)
            if shared and not any(c.agents == (i, j) and c.end == ended for c in collisions):
                collisions.append(Collision((i, j), ended, ended,
                                            "terminal_vertex_resource", tuple(sorted(shared))))
    all_done = len(arrivals) == n
    status = "collision" if collisions else "agent_error" if error else "success" if all_done else "timeout"
    elapsed = [arrivals.get(i, ended) for i in range(n)]
    waits = [max(0.0, elapsed[i] - moving_time[i]) for i in range(n)]
    result = dict(schema_version=1, model="duration_resources_v0.2.1",
                  scenario_hash=digest(scenario.to_dict()), config_hash=digest(config),
                  termination_reason=status, error=error, completed_agents=len(arrivals),
                  completion_fraction=len(arrivals)/n, agent_count=n, elapsed_time=ended,
                  makespan=max(arrivals.values(), default=0) if all_done else None,
                  executed_distance_soc=sum(distance.values()), executed_time_soc=sum(elapsed),
                  censored=not all_done, total_wait_time=sum(waits), per_agent_wait=waits,
                  per_agent_arrival=[arrivals.get(i) for i in range(n)],
                  per_agent_distance=list(distance.values()), decisions=decisions,
                  unsafe_move_attempts=unsafe, collision_count=len(collisions),
                  collisions=jsonable(collisions), deadlock_flag=None,
                  planning_cpu_seconds=cpu, sim_wall_seconds=time.perf_counter()-wall_start,
                  messages_sent=network.messages_sent, messages_delivered=network.messages_delivered,
                  bytes_sent=network.bytes_sent, bytes_delivered=network.bytes_delivered,
                  method=method, oracle_access=oracle_access,
                  replan_count=sum(getattr(p, "replans", 0) for p in policies), peak_memory=None,
                  events=log, network_trace=jsonable(network.trace),
                  occupancy=jsonable(intervals), scenario=scenario.to_dict(), config=jsonable(config))
    return result
