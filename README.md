# An Empirical Study of Coordination Strategies for Multi-Agent Pathfinding (MAPF)

An undergraduate AI research project: a working MAPF simulator, three
coordination strategies of increasing sophistication (Independent A* →
Prioritized Planning → Conflict-Based Search), a reproducible experiment
pipeline, a statistical comparison, and an interactive browser demo.

> **Research question.** *How does the choice of coordination strategy affect
> the efficiency, solution quality and scalability of multi-agent pathfinding
> under different environment conditions?*
>
> **Optional extension (implemented, clearly separated).** *Can the
> characteristics of a MAPF instance be used to select a coordination strategy
> automatically?*

---

## 1. Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. verify the implementation (113 tests, ~2 s)
python -m pytest tests -q

# 2. interactive demo in the browser  ->  http://localhost:8000
python -m app.server --port 8000

# 3. reproduce every experiment (see config/suites.json)
python scripts/run_experiments.py --workers 2

# 4. rebuild every figure and summary table from the raw results
python scripts/make_plots.py
python scripts/analyze.py          # prints the numbers used in the report
python scripts/run_adaptive.py     # optional extension
```

Everything except `pandas`, `numpy`, `matplotlib`, `seaborn` and `scipy` (used
only for analysis/plotting) is standard library: the planners and the demo
server have **no third-party dependencies**.

---

## 2. Repository structure

```
mapf/
├── environment/            # the world
│   ├── grid.py             #   GridMap, Scenario, coordinate & cost conventions
│   ├── generators.py       #   procedural maps (random / clusters / rooms / maze)
│   │                       #   and start-goal distributions (uniform/clustered/near/far)
│   └── benchmarks.py       #   MovingAI .map / .scen import & export
│
├── planning/               # the algorithms (UI- and evaluation-independent)
│   ├── astar.py            #   static A*, time-expanded A*, constraints, reservations
│   ├── collisions.py       #   vertex & edge conflict detection
│   ├── independent.py      #   A. Independent A* (baseline)
│   ├── prioritized.py      #   B. Prioritized Planning (+ priority orders)
│   ├── cbs.py              #   C. Conflict-Based Search (two-level, optimal)
│   └── common.py           #   PlannerResult — one status vocabulary for all
│
├── evaluation/             # the experiment
│   ├── metrics.py          #   SOC / makespan / SIC / validation of any plan
│   ├── experiments.py      #   suite runner (parallel, resumable, crash-safe)
│   ├── statistics.py       #   aggregation + paired significance tests
│   └── adaptive.py         #   EXTENSION: automatic strategy selection
│
├── visualization/          # report figures
│   ├── render.py           #   static grid / plan rendering
│   └── plots.py            #   every figure of the study
│
├── app/                    # interactive demo (stdlib HTTP server + canvas UI)
│   ├── server.py           #   /api/generate, /api/solve
│   └── static/index.html   #   single-page app (no build step, no CDN)
│
├── tests/                  # 101 unit/integration tests
├── scripts/                # run_experiments, make_plots, analyze, run_adaptive
├── config/suites.json      # the experimental design, checked into git
├── results/                # raw rows (.jsonl/.csv), tables (.csv/.md), figures (.png)
├── REPORT.md               # the research report
└── docs/                   # notes on the two core papers
```

---

## 3. Problem definition and assumptions (stated explicitly)

Classical MAPF (Stern et al., 2019).  Input: an undirected 4-connected grid
graph, `k` agents, a start and a goal cell per agent.  Time is discrete and
starts at `t = 0`, when every agent occupies its start cell.

| Assumption | Value used here |
|---|---|
| Actions | {wait, up, down, left, right}, each of cost 1 |
| Vertex conflict | two agents in the same cell at the same timestep — forbidden |
| Edge conflict | two agents swapping cells during a timestep — forbidden |
| Follow conflict | entering a cell another agent has just left — **allowed** (pebble-motion model) |
| Stay at target | an agent occupies its goal from arrival onwards and never moves again |
| Path cost | `len(path) - 1` (number of actions until the goal is first occupied) |
| Objectives | **SOC** = Σ costs (primary, the one CBS optimises); **makespan** = max cost (secondary) |
| Goals/starts | unique per agent, all on free cells of one connected component |

Any change to these would change the algorithms' behaviour, so they are also
restated in `docs/assumptions.md` and in `REPORT.md`.

---

## 4. The three strategies

| | Independent A* | Prioritized Planning | CBS |
|---|---|---|---|
| Coordination | none | sequential reservation table | constraint tree + re-planning |
| Complete | yes (if goals reachable) | **no** — fails for a fixed order | yes (with a time budget) |
| Optimal | no | no | **yes** (SOC) |
| Typical cost | *k* × A* | *k* × time-expanded A* | exponential in the conflicts |

Implementation notes that matter for reproducibility:

* the low-level heuristic is the **true distance** (backward BFS on the static
  grid), which dominates Manhattan and is still admissible/consistent;
* CBS branches on the **earliest** conflict and (optionally) breaks SOC ties by
  the number of remaining conflicts — a tie-break only, it cannot change the
  optimal cost;
* Prioritized Planning stores *permanent* reservations for goal cells
  ("stay at target"), which is exactly why it fails on some solvable instances.

---

## 5. Experimental design

`config/suites.json` defines six controlled suites plus the pool for the
adaptive extension.  Each cell of a suite is repeated over several random
seeds, and **the same instance (same seed) is given to every algorithm**, so
algorithm comparisons are paired by construction.

For the structure suite, 20% is the generator's nominal setting, not a matched
measured obstacle density: the maze generator treats it as a braid fraction,
and the rooms generator retains its walls and doorways. Check measured density
in each raw result when interpreting structure comparisons.

| Suite | Varies | Fixed |
|---|---|---|
| `scalability` | agents ∈ {5…40} | 32×32, random, 20 %, uniform |
| `density` | obstacles ∈ {0,10,20,30,40 %} | 32×32, random, 10 & 20 agents |
| `structure` | random / clusters / rooms / maze | 32×32, 20 %, 10 & 20 agents |
| `distribution` | uniform / clustered / near / far | 32×32, 20 %, 20 agents |
| `gridsize` | 16², 32², 48², 64² | 20 %, 10 & 20 agents |
| `priority_orders` | 6 ordering rules + restarts | 32×32, 20 %, 10/20/30 agents |
| `adaptive_holdout` | mixed conditions | used only for the extension |

Per-run wall-clock budget: **10 s** (a timeout is recorded as a timeout, never
as a success).  Reported metrics: success rate, runtime (mean ± sd, 95 % CI),
SOC, makespan, SOC excess over SIC, and search effort (low-level A* calls,
CBS high-level expansions).

Reproducibility: every instance is a pure function of
`(size, structure, density, distribution, agents, seed)`; `results/raw/*.jsonl`
stores one row per run; `results/raw/manifest.json` stores the suite
configuration and the Python/platform version.

---

## 6. Results at a glance

See **`REPORT.md`** for the full analysis.  Headline findings:

1. Independent A* is essentially free to compute but almost never usable: even
   at 20 agents on a 32×32 map it produces a colliding plan on the vast
   majority of instances — the instance *does* require coordination.
2. Prioritized Planning solves nearly every instance in milliseconds, but pays
   in solution quality and fails outright on a small, structure-dependent
   fraction of instances (bottlenecks, corridor swaps).
3. CBS is optimal but its runtime is heavy-tailed: it is competitive up to
   ~20 agents and then increasingly hits the time budget.
4. Map *structure* and start/goal *distribution* change the picture as much as
   the number of agents — corridors/rooms and "far" goals are where the
   strategies differ most.
5. No single strategy dominates, which is what motivates the adaptive
   selector in `evaluation/adaptive.py`.

---

## 7. Known limitations

* Pure-Python implementation: absolute runtimes are ~1–2 orders of magnitude
  above optimised C++ baselines, so the *crossover points* reported here are
  conservative.
* Success-conditioned SOC is biased when success rates differ (CBS looks better
  on the instances it manages to solve); every table therefore reports the
  success rate alongside it.
* CBS cannot *prove* unsolvability within a budget: on an unsolvable instance
  its constraint tree is infinite, so such runs are reported as timeouts.
* Benchmarks are procedurally generated.  `environment/benchmarks.py` reads
  MovingAI `.map`/`.scen` files if you drop them into `data/benchmarks/`, so
  the same pipeline can be pointed at the standard benchmark set.

---

## 8. References

* Stern, R., Sturtevant, N., Felner, A., Koenig, S., Ma, H., Walker, T., Li, J.,
  Atzmon, D., Cohen, L., Kumar, T., Boyarski, E. & Barták, R. (2019).
  *Multi-Agent Pathfinding: Definitions, Variants, and Benchmarks.* SoCS.
* Sharon, G., Stern, R., Felner, A. & Sturtevant, N. (2015).
  *Conflict-Based Search for Optimal Multi-Agent Pathfinding.* Artificial
  Intelligence, 219, 40–66.
* Silver, D. (2005). *Cooperative Pathfinding.* AIIDE.
* Erdmann, M. & Lozano-Pérez, T. (1987). *On Multiple Moving Objects.* ICRA.
* Kornhauser, D., Miller, G. & Spirakis, P. (1984). *Coordinating Pebble Motion
  on Graphs.* FOCS.
* Standley, T. (2010). *Finding Optimal Solutions to Cooperative Pathfinding
  Problems.* AAAI.
