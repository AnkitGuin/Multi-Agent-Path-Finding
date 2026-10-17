# Modelling assumptions (single source of truth)

Reproduced from `REPORT.md` §2 and `environment/grid.py`. Changing any of these
changes the behaviour of the planners, so they are stated once here and
referenced everywhere else.

1. **Grid / actions.** 4-connected grid, coordinates `(x, y)` with `x` the
   column and `y` the row; actions {wait, up, down, left, right} all of cost 1;
   time is discrete and starts at `t = 0` with each agent on its start cell.
2. **Vertex conflict** — two agents in the same cell at the same timestep.
3. **Edge conflict** — two agents exchanging cells during a timestep.
4. **Follow conflicts are allowed** (pebble-motion / unit-time model): agent A
   may enter a cell at `t` that agent B left at `t`. Disallowing them would be
   a different (and much harder) variant; it is not what Stern et al. call
   *classical MAPF*.
5. **Stay at target.** After reaching its goal an agent remains there forever.
   This is why Prioritized Planning must reserve goal cells permanently, and why
   a later agent can be blocked by an earlier agent's *goal*.
6. **Path cost** = `len(path) - 1` (actions until the goal is first occupied).
   Waiting before arrival costs 1; waiting after arrival costs nothing.
7. **Objectives.** SOC = Σ costs (the objective CBS optimises, and the one all
   quality comparisons use); makespan = max cost (reported, not optimised).
   SIC = Σ individually optimal costs is the lower bound used for the
   "SOC excess over SIC" quality measure.
8. **Instance validity.** Starts and goals are distinct free cells inside the
   single connected component that all generated maps are pruned to. Instances
   may still be *unsolvable* (e.g. two agents that must swap inside a
   corridor); that is a property of the instance, not a bug.
