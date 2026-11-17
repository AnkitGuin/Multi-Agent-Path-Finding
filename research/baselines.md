# Baseline reproduction and information matching — 2026-11-17

The author's minimal Python PIBT is copied unchanged under `third_party/pypibt`
at revision `a3c97f60413c6619a29a5022969896bc54877edc`, with MIT license,
file hashes and attribution. All eight upstream tests passed. Twenty native
16x16/10-agent random/room runs (seeds 0..9 per family) succeeded and passed
independent movement/vertex/swap checks. They include **41 goal departures**,
confirming that permanent-first-goal semantics require an explicit adaptation.
Native outputs and scenarios are in `results/native_2026_11_17`.

Causal-PIBT was built from unmodified author revision
`b2e9e650a1f5446b88cd7b9394504e97435e7f38`, graph dependency
`98df17f364b8e94f927e5e1317eda4f40a2238a6`. A force-include header sets only
directory macros. MinGW GCC 6.3 compiled it with `-std=c++1z -O1`. Twenty runs
across four bundled instances/five activation seeds succeeded. Every native
snapshot was independently checked for free-cell occupancy, adjacent extended
head/tail resources and disjoint resources. These are activation-state checks,
not robot-body physics. Commands, compiler/warnings and failures are retained in
`research/reports/native_build`. External checkouts are ignored, not redistributed.

The LSRP source at `8d39da609a8c5601f05492ebbb089a32a0db4dd2` was inspected.
Builds failed with the installed toolchain, including missing `<optional>`
support; no LSRP run is claimed. Its README contains both academic/noncommercial
and MIT statements, without a license file in the inspected checkout. Resolve
the ambiguity before redistribution. A newer compiler is a separate build task.

| Local controller | Coordination | Role |
|---|---|---|
| local_independent | none | deliberately unsafe diagnostic |
| observed_yield | wait for visibly occupied target; periodic map reports | weak sensing control; simultaneous arrivals can conflict |
| claims_periodic | fixed priority and nonexpiring promises; periodic map reports | protocol baseline |
| claims_always | identical claims; reports every decision | communication control |
| claims_selective | identical claims; reports new wall knowledge/stale peer map information | experimental control; no novelty claim |
| claims_no_map | identical claims; no MAP reports | map-sharing ablation, still sends control messages |
| claims_full_replan | identical selective claims; full local search every decision | local-repair ablation |

All local controls receive own goal/bounds and permitted observations/messages,
use the same v0.2 engine, and share movement/network draws where message IDs
correspond. A* uses known walls plus speculative unknown terrain; entry requires
directly sensed free terrain. Native references have different map, timing and
goal semantics and are reported separately, never pooled in a ranking. No local
adaptation is misidentified as an authentic Shofer/Malka reproduction.

The claim controls isolate a communication trigger beyond independent A*, but
lack priority inheritance/backtracking and can deadlock. They do not replace a
strong modern same-information competitor. G3 is partially satisfied and a
publication-scale superiority claim remains unsupported.

A central dependency-execution reference preserves per-vertex visit order from
a valid classical plan, waiting for actual predecessor departures under
heterogeneous durations. It sees the true map, full plans and actual completions,
and is labeled `KNOWN_ASYNC_GLOBAL_DEPENDENCIES` with oracle access. This is
ADG-like machinery, not a claimed faithful ADG/SADG paper reproduction. Classical
rotation cycles can stall; the adapter reports timeout, not a false solution.
