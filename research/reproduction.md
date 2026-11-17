# Reproducing the second-stage work

Run from the repository root using the pinned environment described in README.
Choose fresh output directories. Existing run evidence is never overwritten.

```powershell
python -m pytest tests -q
python scripts/recertify_legacy.py --out results/local-legacy --workers 2
python scripts/run_async.py --config config/async_development.json --out results/async/local-study
python scripts/analyze_async.py --input results/async/local-study --out results/async/local-study/tables
python scripts/plot_async_study.py --input results/async/local-study/tables --out results/async/local-study/figures
```

The development runner writes every outcome immediately and keeps all replay
files (gzip JSON). Analysis independently validates replays and their summary
rows, checks duplicate IDs and paired configs, and resamples maps rather than
individual agents/events. Native oracle references are not pooled with local
controls. CPU timing and compression bytes may vary by environment; physical
outcomes, message wire bytes and scenario/config hashes are deterministic.

The old first-session tests/XML and validation fixtures are historical evidence
for their recorded source state. The new v0.2.1 model fixes a wait-action sensor
flag and adds goal message service/remembered contacts; see the decision log.
Run IDs include model and baseline version. Source raw-byte and LF-normalized
hashes support matching Windows/Linux text checkouts. The updated test suite
also checks the pinned author's PIBT code integrity after newline normalization.

## Native references

The Python PIBT baseline is vendored with its MIT license and exact revision.
It requires NumPy, already in requirements. Native Causal-PIBT needs the author's
downloaded source and graph submodule. The following example reproduces the
recorded revision without unnecessary visualizer submodules:

```powershell
git clone https://github.com/Kei18/time-independent-planning.git external/time-independent-planning
git -C external/time-independent-planning checkout b2e9e650a1f5446b88cd7b9394504e97435e7f38
git -C external/time-independent-planning submodule update --init --depth 1 third_party/grid-pathfinding
git clone https://github.com/rap-lab-org/public_LSRP.git external/lsrp
git -C external/lsrp checkout 8d39da609a8c5601f05492ebbb089a32a0db4dd2
python scripts/build_native_baselines.py --out research/reports/local-native-build
python scripts/reproduce_native_baselines.py --out results/local-native
```

The build script records each compiler outcome, including LSRP failure under
GCC 6.3; native reproduction requires a successfully built Causal-PIBT app.
It force-includes a generated directory-macro header and does not alter the
author's algorithm. On another platform adjust executable suffix/compiler
discovery as needed; only the recorded Windows setup has been tested. The
native source uses atomic authoritative interactions and allows vacating goals;
this is not an implementation of our packet-loss/unknown-map condition.

No third-party MovingAI maps are added to this repository. Native logs use
bundled author examples, with original input/map hashes for verification after
fetching. LSRP license wording is ambiguous; its downloaded source stays ignored.

## Research gates

The final holdout config remains a reserved, unresolved specification. The
runner rejects it. Do not tune on it or pretend the development results are a
held-out test. The current evidence does not justify a new methods manuscript.
Final experiments/optional learning/manuscript depend on a distinct contribution,
strong matched baselines and satisfactory progress behavior.
