# Milestone checklist — 2026-11-16

The attached file is a multi-stage research specification, not proof of a
completed contribution. This is the explicit first-session handoff it requests.

| Milestone | State | Actual evidence / next dependency |
|---|---|---|
| M0 original audit | bounded audit done; full report recertification open | 114 original tests, 3 failures; 24 original/repaired benchmark jobs each; inventory/hashes |
| M1 formulation/literature | initial artifacts done; G1 OPEN | 15 checked primary-source identities, annotated notes, review-depth gaps; no author-approved novelty claim |
| M2 event simulator | foundation implemented and analytically validated | ordering, durations, conflicts, actual completion, censoring, six replays |
| M3 observations/network | foundation implemented and validated | hidden-cell isolation, sensor timing, belief provenance, message age/loss/reorder/duplicates/bytes |
| M4 strong baselines | not implemented | public code locations checked, native assumptions/build/reproduction pending |
| M5 candidate method | gated / not implemented | requires G1 and fair baselines; protocol requirements documented |
| M6 comparison/ablations | not run | no method/baseline comparison data |
| M7 final evaluation | not run | holdout seed/family reservation only; no resolved final experiment |
| M8 manuscript/release | not started | no justified contribution, venue or coauthor review yet |

Minimum initial-session artifacts requested by section 15 are present: audit,
problem formulation, literature matrix with at least ten verified publication
identities (15 total records including newer preprints), research questions,
architecture and independent simulator tests. Verification does not mean every
paper's full text/proof/code was audited; each row states its depth.

Measured validation at this point: 197 tests passed, no skipped/error cases;
six saved analytic smoke cases independently replay-verified. These figures
are engineering coverage, not evidence that a MAPF method outperforms prior art.

Next session: read instructions and decision log; resolve the closest-paper
full-text/code gaps; obtain the spec's G1 author review; reproduce PIBT and
Causal-PIBT in native known-map settings and state every local adaptation.
Do not tune a freshness method against the sealed future holdout. Full legacy
table recertification should use a new results directory.

Novelty hypothesis: still an open question. The additional 2026 communication
papers narrow it. A descriptive boundary/failure study is the evidence-based
fallback if an independent algorithmic mechanism cannot be distinguished.
