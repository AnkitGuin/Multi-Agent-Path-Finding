# Local resource claim protocol v0.1 — implemented, not a novelty claim

A move has a monotonically increasing agent-local epoch and two endpoint
resources. The stationary owner sends REQUEST(epoch,source,target) to every
currently sensed peer, adding newly seen peers while negotiating. It commits
locally only after GRANT from all required peers and a fresh target-clearance
observation. A move with no nearby peers needs no messages.

A grant creates a nonexpiring promise excluding conflicting own moves and other
grants. It cannot include the granting agent's current cell. A conflicting
uncommitted request yields to a lower agent ID by cancellation. A committed move
cannot cancel. This is fixed priority, not PIBT or priority inheritance.

After actual completion, or cancellation before movement, the owner retries
RELEASE to every requested peer until ACK. RELEASE fences older epochs. An old
REQUEST cannot recreate a released promise. Duplicates resend responses. Late
GRANT applies only to a matching current epoch; reordered REJECT cannot retract
a prior nonexpiring grant. COMMIT is local, not a redundant wire message.

```text
idle -> requesting --all grants + clearance--> committed/moving
requesting --cancel--> idle + release retries
committed --actual completion--> idle + release retries
release retries --ACK--> acknowledged
```

Assumptions: cooperative policies, static map, exact localization, Manhattan
sensing radius >=2, directly verified adjacent entry, persistent peer IDs/epochs,
remembered legitimate contacts, no state corruption/restarts, and duration
resources. Every participant must use the protocol. Agents cannot read hidden
occupancy/maps or a global roster.

Conditional intuition: intersecting one-edge moves start at most two hops apart,
so relevant stationary peers are visible. A promise excludes the peer's
conflicting movement until explicit release. This motivates an invariant, but
is **not** a machine-checked theorem over all asynchronous executions. Tests
and independent monitoring validate implemented traces, not unconditional safety.

No liveness guarantee: loss, peers leaving range, stopped owners, fixed priority
and permanently occupied goal passages can block progress. No expiry frees a
resource. Failed completion is a timeout, not proof of deadlock/infeasibility.
Backtracking/starvation recovery is still missing.

The v0.2 engine permits message service at goals while preserving first arrival
cost and forbidding departure. Remembered contacts may receive release retries;
transport still checks actual range. With sensing two and transport three hops,
a one-edge completion can reply to a peer formerly two hops away. Loss can still
prevent progress, which is retained in the experimental data.
