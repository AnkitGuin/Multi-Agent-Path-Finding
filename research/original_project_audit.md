# Original project audit — 2026-11-16

Base: `c4d073d32ec428411d26ca51459915ebca2645b2`, original `main`.
Research branch: `research/decentralized-async-mapf`. No AGENTS.md was found in
the workspace ancestry or recursive project inventory. The attached roadmap is
preserved as `instructions.md`; the user expressly authorized its execution.

## Inventory and environment

The recursive tracked-file inventory, byte sizes and SHA-256 values are in
`reports/baseline/manifest.json`. It covers the original environment/planning/
evaluation/tests/scripts/docs/config, demo, bundled example, raw archives,
tables and figures. The starting dirty tree contained `app/static/index.html`
and untracked `presentation_screenshots/`; those were preserved and excluded
from research staging. The baseline manifest hashes the working HTML as found.

Read before changes: README, REPORT, both docs, suites.json, requirements, all
environment/planning/evaluation modules and original tests. There is no existing
asynchronous engine or agent-local memory abstraction to reuse.

Windows 11 build 26300; Python 3.13.3 (64-bit AMD64); Intel64 Family 6 Model 154
Stepping 3; 12 logical CPUs. Exact executable/platform/processor/dependency
versions are stored in the manifest. RAM and peak memory were not measured.
The local `.venv` was created because system Python lacked pytest. Dependencies
were installed from requirements.txt; pinned resolved versions are in
`reports/requirements-lock.txt`. Initial sandbox networking failed (WinError
10013); network-enabled installation succeeded. Git emitted an inaccessible
global ignore-file warning and Windows line-ending notices; no source warning
was suppressed. Source SHA and per-file hashes distinguish uncommitted states.

## Original assumptions and privilege boundary

Original solvers receive the full static grid and all starts/goals, use discrete
unit-time actions, permit follows, prohibit vertex/swaps, and promise permanent
goal occupancy. They are search algorithms, not learned policies or CTDE.
`GridMap` retains disconnected free pockets on random/clustered maps; agents
are sampled from the largest component. The roadmap's description of pruning
all maps is outdated. Rooms and maze parameters do not match realized density;
the old report already qualifies this.

Never supply these to a decentralized partial-map policy:

- `planning/astar.py:52` full-grid reverse BFS or default `astar(GridMap,...)`.
- `planning/prioritized.py` global cost/conflict priority order and reservation
  table, `planning/cbs.py` joint constraints/paths, original Independent inputs.
- `environment/generators.py:509` global density/agent-density features.
- `evaluation/experiments.py` global SIC and independent initial conflicts.
- `evaluation/adaptive.py` full-map features and offline solver outcomes.
- `planning/collisions.py` all-agent ground-truth trajectory checker.

These remain appropriate oracle/evaluation components under labeled conditions.
New agent modules have no imports of these objects or world references.

## Executed baseline evidence

| Command (using .venv Python unless stated) | Actual outcome |
|---|---|
| system `python -m pytest tests -q` | failed: No module named pytest |
| `python -m pytest tests -q --junitxml=research/reports/original_tests.xml` | 114 collected, 111 passed, 3 failed; pytest 1.49 s |
| `python scripts/audit_original.py` before correction | 24 jobs, 8.915 s; 17 ok, 4 conflict, 3 invalid |
| `python -m pytest tests -q --junitxml=research/reports/repaired_legacy_tests.xml` | 115 passed, 1.12 s (one added regression at that point) |
| `python scripts/audit_original.py --out research/reports/repaired_baseline` | 24 jobs, 8.129 s; 20 ok, 4 conflict; all 24 stored status/SOC pairs matched |

The 24 jobs select the **first configured instance** from each of all seven
suites, with every configured algorithm/order and unchanged 10-second budget.
They are a bounded reproduction, not replication of whole reported curves.
Raw subsets, comparisons and source hashes are separate for original/repaired
states. Historical `results/raw`, superseded archives, tables and REPORT were
not rewritten. Original tests already exhaustively cross-check CBS against
joint-state Dijkstra on 2/3-agent tiny grids and include timeout/unsolvable cases;
those tests passed. This is empirical bounded coverage, not a completeness proof.

## Findings and decisions

| Severity | Finding | Disposition |
|---|---|---|
| critical | space-time A* allowed early entry to a goal, later departure around a future reservation/constraint, then return | fixed only the goal-entry condition; also disallow departing an initially occupied goal; separate regression tests |
| major | original reproduction downgrades PP to invalid in distribution/index and priority_orders/longest_first and most_conflicting_first | preserve original evidence; repaired selected rows match stored status/SOC; full published tables have not been recertified |
| major | claimed disjoint adaptive pool overlaps main suites | 48 of 108 adaptive specifications also occur in main suites; machine-derived counts in audit_summary.json |
| major | global heuristics/features would leak hidden state | preserve as labeled oracle components; immutable local interfaces for new engine |
| major | CBS wall/expansion/time-horizon limits weaken unrestricted guarantees | no unconditional completeness claim; finite low-level horizon exhaustion is an unresolved legacy theoretical limitation |
| minor | README has 113 and 101 counts; actual collection is 114 | count discrepancy recorded here and README research note; old report retained as history |
| minor | dependency lower bounds are not a lock; manifest lacks source checksums/hardware completeness | pin this environment and hash sources; do not present it as a cross-platform clean-room replication |

Adaptive inspection: labels derive from measured outcomes offline, features are
available before coordinated solving in the **known-global-map** condition,
logistic standardization is fitted on each training fold, and CV indices are
disjoint within that pool. The 48 overlapping configurations contradict the
claim of independence from the main suites; this alone is not proof of
train/test leakage *within* its CV. No threshold/model was retrained here.
The future study uses distinct seeds/layout reservations before tuning.

Randomness is explicit and jobs share procedural parameters/seeds. Placement
uses sorted component cells. Set-order component tie selection remains a minor
potential portability gap for equal-size disconnected components. Nominal and
measured density are recorded separately. Runtime depends on hardware and is
not expected to equal historical measurements.

G0: bounded reproduction and bug diagnosis achieved; complete historical table
recertification and finite-search theoretical audit remain open. New research
claims must not inherit the legacy report's claims without that qualification.
