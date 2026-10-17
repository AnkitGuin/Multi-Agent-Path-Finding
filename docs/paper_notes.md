# Notes on the two core papers

Study notes written while implementing this project (kept in the repository so
that the reasoning behind each design decision is traceable).

## 1. Stern et al. (2019) — *Multi-Agent Pathfinding: Definitions, Variants, and Benchmarks*

**Why read it first.** It fixes the vocabulary and, more importantly, the
*modelling choices* that every MAPF paper has to make explicitly. Half of the
"surprising" differences between published results come from authors silently
using different variants.

Key take-aways that shaped the code:

| Concept | Definition used in this project |
|---|---|
| Classical MAPF | discrete timesteps, one action per agent per timestep, unit costs |
| Vertex conflict | agents *i, j* in the same vertex at the same timestep |
| Edge conflict | agents *i, j* traverse the same edge in opposite directions at the same timestep |
| Follow conflict | *i* enters a vertex that *j* left in the previous timestep — **not** a conflict in the classical (pebble-motion) variant |
| Stay at target | an agent remains at its goal (we implement exactly this; it is what makes a "goal cell" a permanent reservation in Prioritized Planning) |
| SOC | Σ over agents of the number of timesteps until the goal is reached = Σ (len(path) − 1) |
| Makespan | max over agents of the same quantity |
| Optimal variants | sum-of-costs optimal (what CBS gives) ≠ makespan optimal ≠ time-optimal |
| Benchmarks | procedurally generated maps (empty / random / rooms / mazes) plus a standard `.scen` scenario format |

The paper also documents *why* the problem is hard: deciding whether a solution
exists is NP-hard in general for makespan-optimisation variants, and the joint
state space grows as |V|^k, which kills joint-state A* beyond a handful of
agents. That is the motivation for the two-level (CBS) idea.

**Consequences for our experiments.** Because the variant changes the answer,
our assumptions are stated in `docs/assumptions.md` and restated in the report;
and because instance *generation* changes the answer too, the map generator
(`environment/generators.py`) documents exactly what each parameter means.

## 2. Sharon et al. (2015) — *Conflict-Based Search for Optimal Multi-Agent Pathfinding*

**The core idea.** Do not search the joint state space. Search instead over
*sets of constraints*. A high-level node holds

* a constraint set per agent, and
* one (shortest) path per agent consistent with those constraints.

If the joint plan of the cheapest node is conflict-free, it is optimal and we
stop. Otherwise pick one conflict ⟨aᵢ, aⱼ, v, t⟩ and branch into two children:
one forbids aᵢ from occupying *v* at *t*, the other forbids aⱼ. Any solution
must violate at least one of the two constraints, so no solution is lost
(→ completeness); and because the children strictly refine the parent's
constraint sets while branching on the cheapest node first, the first
conflict-free node found is optimal (→ optimality).

**Why it is efficient.** Only the re-planned agent's low-level A* is re-run;
all other paths are reused. The number of high-level expansions is driven by
the number of *conflicts that actually matter*, not by the joint state space.

**Implementation checklist we followed.**

1. Low level = time-expanded A* with the agent's own constraints only.
   The heuristic must not count other agents (otherwise it is inadmissible):
   we use the exact static-grid distance (backward BFS), which is admissible
   *and* consistent and dominates Manhattan.
2. "Stay at target" has to be handled inside the low level: terminating at the
   goal at time *t* implies occupying it at every *t′ > t*, so a later vertex
   constraint on the goal cell must forbid early arrival. (`ConstraintVerifier.can_terminate`.)
3. Duplicate constraints produce duplicate nodes; we skip a child whose
   constraint is already present in the parent.
4. Equal-cost nodes are expanded in a deterministic order (we break ties by the
   number of remaining conflicts — an *ordering* heuristic only; it cannot
   change the cost CBS returns).

**Deliberately not implemented** (the brief asks for standard CBS first):
prioritising conflicts / ICBS, disjoint splitting, symmetry breaking, CBSH,
EECBS. Each of those is an *improvement* on top of the reproduced algorithm and
would blur the comparison with the baselines.

**Known property we confirmed empirically.** On an *unsolvable* instance the
constraint tree is infinite (every repaired plan runs into a new conflict
later in time), so CBS cannot prove unsolvability — it just keeps expanding.
With a time budget such runs are reported as `timeout`, never as "unsolvable".

## Supporting literature (for the Related Work section)

* Silver (2005), *Cooperative Pathfinding* — Windowed Hierarchical Cooperative
  A*; the origin of the "plan in priority order against reservations" idea used
  by our Prioritized Planning baseline.
* Erdmann & Lozano-Pérez (1987), *On Multiple Moving Objects* — priority-based
  (decoupled) planning and its incompleteness.
* Kornhauser, Miller & Spirakis (1984), *Coordinating Pebble Motion on Graphs*
  — polynomial-time feasibility results for pebble motion on graphs, the
  theoretical backbone of the follow-conflict assumption.
* Standley (2010), *Finding Optimal Solutions to Cooperative Pathfinding
  Problems* — operator decomposition and independence detection, the immediate
  precursor of CBS.
* Wagner & Choset (2011), *MAPP: a Scalable Multi-Agent Path Planning Algorithm
  with Tractability and Completeness Guarantees* — sub-optimal but complete
  alternative; useful contrast for the "is optimality worth it?" discussion.
