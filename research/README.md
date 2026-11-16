# Research extension: audit and simulator foundation

This branch executes the initial dependency stages of [instructions.md](../instructions.md).
It does **not** complete the entire research/publication roadmap. There is no
proposed freshness algorithm, reproduced strong decentralized baseline,
comparative improvement, safety theorem or manuscript yet.

Implemented: deterministic real-time events, heterogeneous/jittered durations,
explicit duration-resource occupancy, independent conflict monitor, immutable
local sensing, timestamped beliefs, seeded local message loss/latency/duplicates,
serialized bytes, saved authoritative traces and independent metric replay.
The original goal-commitment bug is repaired with original evidence preserved.

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

This selects one instance per suite, not a full experiment. The existing
`results/raw` and historical report are retained. Full report recertification
requires a new complete run, outside this bounded audit.

## Replay

Each `results/async/validation_final/*.json` includes observer-only true scenario,
config, observations, policy outputs, action starts/finishes, transport trace,
occupancy intervals and metrics. `evaluation.replay_async.verify_replay` checks
saved files without invoking policies. The six scripted fixtures are privileged
test guidance (`oracle_access=true`), **not** matched local algorithm results.

Limitations: abstract resource conflicts, exact sensors/localization, shared
clock, no wall occlusion, only stationary sensing, no distributed ownership
protocol, no deadlock proof, no adversarial Python sandbox. Unmeasured metrics
are null. A frozen final evaluation remains dependent on G1/G3 and licensed
layout hashes; the holdout JSON only reserves a future split.
