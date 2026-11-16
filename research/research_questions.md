# Preregistered questions and falsifiers (2026-11-16)

Primary candidate question: under identical partial observations and duration
occupancy, when does stale neighbor information cause avoidable coordination
waiting at bottlenecks? A descriptive reproducibility study is the current
fallback; there is no accepted algorithmic novelty claim.

| Hypothesis | Null | Falsifier / decision |
|---|---|---|
| H1 freshness reduces waiting at equal safety | paired waits do not improve | uncertainty includes no effect, or conflicts/completion worsen |
| H2 benefit increases with delay variability | no interaction with latency | paired interaction absent or reverses outside a narrow selected slice |
| H3 known-local bottleneck coordination helps corridors | topology adds no value | matched topology ablation performs equally or better |
| H4 selective messaging reduces bytes | no byte saving | serialization/ACK/retry accounting removes saving |

One prospective primary claim: characterize the operating boundary of
freshness-triggered coordination under known loss/latency assumptions, relative
to fixed communication with **identical** commitments and observations. Two
secondary observations: topology sensitivity; communication/completion tradeoff.
Neither is asserted as a result. A threshold plus a standard lock is not enough
for a new methods contribution. G1 remains open pending full-text comparison.

Baseline shortlist in dependency order: local optimistic A* with verified entry
(weak diagnostic); fixed-period messaging with the same coordination;
faithful PIBT under its graph assumptions; Causal-PIBT/time-independent planning;
LSRP with explicit global-map/timing differences; inaccurate-map online planning
with all adaptations labeled. PP/CBS/EECBS/LNS2 are privileged references, never
matched-information primary competitors. No fabricated baseline implementation.

Development seeds 0..19; proposed final seeds 100000..100099. Development families
open/random/rooms; warehouse and selected MovingAI layouts reserved for a final
family shift. Splits will require explicit layout hashes and license checks.
The committed holdout specification is sealed planning input, not executed data.
No algorithm tuning or holdout measurements have occurred in this milestone.

Go/no-go: M0 audit required before relying on old numbers; G1 requires precise
differences and author review; G2 interval/clock validation; G3 strong authentic
baselines; G4 reproducible matched-condition effect or useful negative result;
G5 ablations/holdout/review. Manuscript and optional learning await these gates.
