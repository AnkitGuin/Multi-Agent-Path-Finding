# Research extension: baselines, local claims and development evidence

This branch executes [instructions.md](../instructions.md) in dependency order.
The full legacy recertification, native references, local claim controls and
development comparisons now have reproducible evidence. The entire research
roadmap is **not complete**: novelty and a reliable waiting improvement are not
established, so final holdout/manuscript gates remain closed.

Implemented: deterministic real-time events, heterogeneous/jittered durations,
explicit duration-resource occupancy, independent conflict monitor, immutable
local sensing, timestamped beliefs, seeded local message loss/latency/duplicates,
serialized bytes, saved authoritative traces and independent metric replay.
The original goal-commitment bug is repaired with original evidence preserved.

Latest: [measured development report](reports/development_results.md),
[baseline comparison](baselines.md), [protocol](protocol_spec.md),
[reproduction commands](reproduction.md), and [internal review](protocol_safety_review.md).
Current suite: **275 passing tests**, plus eight upstream PIBT tests separately.

Read [progress](progress.md), [audit](original_project_audit.md),
[model](problem_formulation.md), [architecture](architecture.md),
[novelty gate](literature/novelty_gap.md), and [risks](risk_register.md).
The literature matrix contains 15 primary-source records with explicit review
depth; it is not a completed full-text systematic review.

## Reproduce

From the repository root, Python 3.13 was used. The engine itself is stdlib-only.
Use the pinned environment for the recorded test/analysis dependency versions:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r research/reports/requirements-lock.txt
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe scripts/validate_async.py --smoke --out results/async/local-validation
.\.venv\Scripts\python.exe scripts/summarize_research_audit.py
.\.venv\Scripts\python.exe scripts/build_literature_matrix.py
.\.venv\Scripts\python.exe scripts/generate_research_figures.py --input results/async/local-validation --out results/async/local-figures
```

Smoke output paths must be fresh, preserving previous run evidence. Original
pre-fix evidence cannot be reproduced with repaired code: use the recorded base
commit in a separate checkout. The test XML records the original failures.
To rerun the bounded original suite subset on current code:

```powershell
.\.venv\Scripts\python.exe scripts/audit_original.py --out research/reports/local-baseline
```

This selects one instance per suite. The full 1,380-job rerun and per-job
comparison are in `results/recertified_2026_11_17`, with zero invalid plans.
Existing `results/raw`, tables/figures and historical REPORT remain unchanged.

## Replay

Each `results/async/validation_final/*.json` includes observer-only true scenario,
config, observations, policy outputs, action starts/finishes, transport trace,
occupancy intervals and metrics. `evaluation.replay_async.verify_replay` checks
saved files without invoking policies. The six scripted fixtures are privileged
test guidance (`oracle_access=true`), **not** matched local algorithm results.

Development summaries, compressed full replays, manifest, all-outcome tables
and figures are in `results/async/development_2026_11_17`. Native prior-work
runs are separate in `results/native_2026_11_17` because their information,
goal and timing assumptions differ.

Limitations: abstract resource conflicts, exact sensors/localization, shared
clock, no wall occlusion, stationary decision sensing, no progress/deadlock
proof, no adversarial Python sandbox. Local claims require sensing >=2 hops.
Unmeasured metrics
are null. A frozen final evaluation remains dependent on G1/G3 and licensed
layout hashes; the holdout JSON only reserves a future split.
