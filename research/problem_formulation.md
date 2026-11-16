# Partial-map asynchronous model v0.1

Status: engineering model for validation, not a frozen final study. No learning
or training is implemented. The legacy planners remain centralized references.

1. The world is a bounded 4-connected integer grid with static hidden obstacles.
   Starts are unique free cells; goals are unique free coordinates. A start may
   already equal its goal. Disconnected goals are permitted in adversarial tests.
2. Each policy knows geometric bounds, its ID, own coordinate and own goal only.
   Neither all starts/goals nor the true grid enter the policy interface.
   Agents are trusted cooperating software, not Byzantine processes.
3. Sensors reveal a Manhattan ball at stationary decision events, including at
   initialization and actual action completion. Walls do not occlude visibility.
   Localization and sensing are exact and instantaneous. Radius zero is valid.
   Moving neighbors expose occupied endpoints when either is in view, without
   exposing their goal, duration or future route.
4. Unknown cells remain unknown. Exploration may be optimistic in a future local
   search, but physical entry requires a free cell in the current local sensor
   snapshot. This conservative entry rule must be identical across competitors.
5. Time is nonnegative real simulation time. Movement durations are positive;
   per-agent heterogeneity and independently seeded jitter are environmental,
   not policy predictions. No agent is permitted to advance the simulator clock.
6. A move u->v occupies both endpoint resources on [start, actual_finish).
   A stationary/waiting agent occupies its cell. At actual_finish the source is
   released and the destination remains occupied. Opposite edge traversal is a
   separately labeled conflict. These are abstract duration conflicts, not a
   calibrated robot footprint/contact simulation. Same-direction overlapping
   endpoint occupation is conservatively forbidden too.
7. Half-open boundaries permit an instantaneous handoff once the other action
   actually finishes. FINISH precedes DELIVERY, SENSE, DECISION at equal time.
   Zero-delay causal phase reversals use a new microstep, never retroactive
   knowledge. Equal-time decisions have deterministic insertion order.
8. This model does **not** recover the legacy follow-move convention: classical
   trains/cycles can conflict under duration occupancy. Only disjoint-resource
   synchronous paths have the same outcomes. Never pool the two models' costs.
9. No inter-agent safety shield is enabled. The world rejects malformed,
   obstacle, concurrent-self or unsensed entry attempts and records them. It
   accepts resource-conflicting valid moves; the independent monitor evaluates
   authoritative occupancy intervals. Zero conflicts therefore cannot be caused
   by silent collision rejection. Policies are responsible for coordination.
10. Directed messages have per-(sender,recipient,kind) sequence IDs, generation
    and delivery times, immutable JSON payloads and actual UTF-8 wire lengths.
    Uniform bounded latency, independent Bernoulli packet loss and optional
    duplication are configurable; variable delays allow reordering. Range is
    tested at send time using authoritative transport locations. No omniscient
    peer roster is supplied to the policy. Links need not persist until delivery.
11. Clocks share simulation time with no skew in v0.1. Message age is now minus
    generation time, not now minus receipt time. Cell facts retain their own
    observation times and origins. Sequence IDs never wrap in this Python model.
    Unreliable communication cannot release an occupied resource by expiry.
12. Agents remain at goals permanently. Success requires all goals reached by
    deadline **and** no detected resource conflicts. Deadline failures are
    timeouts; inactivity is a diagnostic, not proof of deadlock or infeasibility.
    A simulator/agent exception is an agent_error, never an unsolvable instance.
13. No safety or liveness theorem is claimed. Tests validate implementation
    consistency under these assumptions, not all executions. Unknown agents,
    unbounded loss and failures prevent an unconditional progress claim.

| Information | World/observer | Local policy | Legacy oracle |
|---|---|---|---|
| True obstacles | yes | sensed facts/messages only | yes |
| All starts/goals | yes | own only | yes |
| Actual active actions | yes | visible endpoints only | schedule reference only |
| Future delivery/loss draws | transport only | no | no |
| Global BFS/features | evaluator only | prohibited | permitted |

Named target conditions from the master spec are reserved, not all implemented:
KNOWN_SYNC_GLOBAL is the legacy experiment; UNKNOWN_ASYNC_RELIABLE/DELAYED/LOSSY
describe local observation plus the named network setting. Synchronous local and
known-map local controllers await baseline adapters. No comparison may silently
change sensing, resource semantics, durations, horizon or information access.

Metrics: completion fraction uses all agents; executed distance counts completed
edges plus fractional progress on a move cut by the horizon; time SOC sums
min(arrival, episode_end) for every agent, explicitly censored on failure.
Waiting is elapsed non-moving time before arrival/censoring. Successful makespan
is latest arrival; unsuccessful makespan is null and elapsed horizon is retained.
Communication denominators count attempted in-range directed transmissions,
including lost packets, and all delivered copies. CPU/wall times are nondeterministic
metadata. Conflict counts describe merged pair/resource overlap segments.
