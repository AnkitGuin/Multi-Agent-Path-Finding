# Protocol review and counterexamples — 2026-11-17

This is an internal engineering audit by the implementing assistant, not three
independent scientific reviews or a proof of publication readiness.

| Severity | Objection | Resolution / remaining limitation |
|---|---|---|
| critical | Grant expiry could let an agent enter an occupied resource | No expiry exists. Only matching/fencing RELEASE removes promises. |
| critical | A canceled request could be revived by a reordered grant | Current epoch must match; releases retain per-sender epoch tombstones. |
| critical | A requester could commit after a relevant new peer appears | Current sensor peer set is added before every commitment; radius >=2 is required. |
| major | An arrived agent could stop servicing release/ACK and block others | v0.2 allows message service at goals, preserving first-arrival cost and permanent goal occupancy. |
| major | A peer could move out of reply range | Remembered legitimate contacts are addressable; radius is still enforced. Lost/out-of-range release remains fail-closed, with possible noncompletion. |
| major | Two agents face each other in a corridor or block each other's goals | No backtracking/priority inheritance. Record timeout; no liveness claim. |
| major | Fixed priority may starve an agent | No starvation-free claim. Per-agent arrivals/waits and failed episodes remain raw evidence. |
| major | Native prior work uses stronger information/atomic interactions | Native data are separate labeled references, not primary local rankings. |
| major | A simulator might mask unsafe controllers | Only invalid/unsensed moves are rejected. Resource-conflicting moves execute and are detected independently. |
| minor | Replanning/cache changes might affect comparisons | Explicit full-replan control, shared observation/search semantics, stored source/config hashes. |

Executed checks include delayed/duplicate/reordered requests, release before
request, lost grant, lost release and ACK retries, cancellation/late grant,
non-cancelable committed movement, sensed-secret-wall counterfactuals, native
coordinate conversion, goal-service behavior, stochastic duration/loss fuzz,
and independent interval-sweep comparison to a pairwise sampling oracle.

Not resolved: participant restarts/epoch persistence across crashes, Byzantine
messages, clock skew, realistic robot geometry, unknown/dynamic peer membership
without two-hop sensing, stopped-owner recovery, or formal liveness. These are
outside the validated model; do not extrapolate the measured conflict count.
