# RESEARCH DEVELOPMENT INSTRUCTIONS — DECENTRALIZED, ASYNCHRONOUS MAPF UNDER PARTIAL OBSERVABILITY

**Repository:** https://github.com/AnkitGuin/Multi-Agent-Path-Finding  
**Working title (provisional, not a novelty claim):** *Information-Freshness-Aware Decentralized Multi-Agent Path Finding in Partially Known Environments*  
**Document date:** 16 November 2026  
**Audience:** A research engineer or frontier coding/research LLM working inside the repository; project investigators; eventual coauthors.  
**Ultimate objective:** Turn a sound undergraduate MAPF comparison into an independently reproducible, meaningfully novel research contribution and a defensible scientific manuscript. **Do not claim publication or novelty before the literature and experimental evidence justify it.**

> **Non-negotiable operating rule:** Perform and document the actual work. Do not invent algorithmic improvements, safety guarantees, numerical results, executed tests, citations, baselines, or empirical findings. When a dependency cannot be installed or a benchmark cannot be run, record the blockage and proceed with validated work that is possible. Do not fabricate completion.

---

## 0. How to use this file

Treat this as the project's **master execution specification**. Complete tasks in order unless there is a documented technical reason not to. At every stage produce (a) implementation, (b) tests, (c) machine-readable evidence, (d) an explanatory report, and (e) a decision whether the research hypothesis remains credible.

This document deliberately distinguishes:

- **Existing facts** about the original repository, as reported in its publicly accessible README and `REPORT.md` (verify against source and tests before changing anything).
- **Established prior research**, which limits what may be claimed as new.
- **Proposed mechanisms and hypotheses**, which are *not* established results or guaranteed contributions.
- **Mandatory engineering work**, needed regardless of whether any algorithm outperforms its baselines.
- **Publication work**, which begins in earnest only after evidence and novelty survive critical review.

### Mandatory initial actions for the executing agent

1. Inspect the **local working tree** recursively; do not assume it matches the public README.
2. Read `README.md`, `REPORT.md`, `docs/`, `config/suites.json`, `requirements.txt`, all relevant `planning/`, `environment/`, `evaluation/`, and `tests/` files before editing.
3. Run the original tests and record the exact commit, environment, commands, results, failures, and runtime. Do not silently repair unrelated old code.
4. Create a feature branch such as `research/decentralized-async-mapf`; preserve original results and algorithms.
5. Maintain a progress checklist and append dated decisions to `research/decision_log.md`.
6. Review the verified primary literature in Section 4. Refresh related-work searches immediately before submitting any paper.
7. Implement the experimental machinery **before** implementing or tuning a proposed algorithm.
8. Never use the simulator's hidden true map or hidden agent state inside a decentralized agent unless explicitly allowed by the experimental condition.
9. Before starting a manuscript, verify that evaluation demonstrates a genuine and repeatable contribution. Drafting a paper is not a substitute for research.

### Priority order

1. **Scientific validity and safety-model correctness**
2. **Strong, fair baselines and reproducibility**
3. **Clear and specific novelty**
4. **Useful quantitative results**
5. Presentation, visualization, manuscript polish

---

## 1. Background: what exists in the course project

### 1.1 Original project

The current project is titled *An Empirical Study of Coordination Strategies for Multi-Agent Pathfinding (MAPF)*. It implements:

1. **Independent A\*** — individual shortest paths, no inter-agent conflict resolution.
2. **Prioritized Planning (PP)** — sequential per-agent planning with temporal reservations; fixed priority orders can fail on solvable instances.
3. **Conflict-Based Search (CBS)** — centralized two-level conflict resolution for minimum sum of costs, with finite computation/time limits.
4. An **optional adaptive strategy selector** driven by instance features.
5. Map generators, MovingAI import/export, metrics, statistical summaries, experiment scripts, and a browser demo.

The README advertises commands including:

```bash
python -m pytest tests -q
python -m app.server --port 8000
python scripts/run_experiments.py --workers 2
python scripts/make_plots.py
python scripts/analyze.py
python scripts/run_adaptive.py
```

These commands are **instructions to validate**, not evidence that they were executed for this document. The README says 113 tests in one section and 101 in a displayed tree comment. Resolve the discrepancy by actually collecting tests. Do not rely on a marketing count.

### 1.2 Current map and movement model

The README specifies a 4-connected undirected grid, discrete time, actions `{wait, up, down, left, right}`, and unit movement duration/cost. Unique starts and goals lie on free cells of a connected component. Agents stay at goals after arrival. The existing collision convention prohibits vertex conflicts and opposite-direction edge swaps, while permitting a follow move into a cell just vacated in the same synchronized timestep.

The static A\* heuristic reportedly uses full-grid reverse BFS to compute true distances. That is valid under a known map; in an unknown-map experiment it becomes **privileged information**. Audit all similar shortcuts, including adaptive features, preprocessing, global congestion measurements, and collision-avoidance logic.

### 1.3 Existing experimental suite and limits

The public repository describes map families including random, clustered, room, and maze layouts; variations in map dimensions, density, agent count, and start/goal distribution; paired seeds; a 10-second per-run budget; and output files under `results/`. The original report describes strong PP scalability and CBS timeouts in hard cases, but these figures are **bounded by that implementation, benchmark design, and runtime budget**, not universal algorithm rankings.

The report itself acknowledges important caveats:

- PP and CBS performance depends strongly on map topology, bottlenecks, and workload.
- CBS results are success-conditioned and heavy-tailed; comparing path costs only on solved instances is biased.
- Procedural map generators do not necessarily produce equal measured obstacle density across families.
- Pure-Python runtimes cannot be treated as fair absolute-performance comparisons with optimized C++ solvers.
- Standard MovingAI benchmark support exists but should be expanded for a publication-quality evaluation.

### 1.4 Preserve these assets

Preserve `environment/grid.py`, `environment/generators.py`, `environment/benchmarks.py`, `planning/astar.py`, `planning/independent.py`, `planning/prioritized.py`, `planning/cbs.py`, `planning/collisions.py`, `planning/common.py`, `evaluation/metrics.py`, `evaluation/experiments.py`, `evaluation/statistics.py`, `evaluation/adaptive.py`, the original tests, and existing reports. Refactor through adapters and carefully tested interfaces rather than replacing working code wholesale.

**Deliverable:** `research/original_project_audit.md`, including exact file inventory, original assumptions, baseline reproduction, code health, reproducibility gaps, and an explicit list of legacy components that must never receive hidden-state leakage.

---

## 2. Interpret the professor's four critiques precisely

### 2.1 Centralized vs decentralized — planning and learning are not the same

The current three solvers are **search/planning algorithms**, not learned policies. It is therefore inaccurate to characterize their existing configurations as “centralized training” or “decentralized training.” Answer two independent questions:

**Planning/execution architecture**

- *Centralized planning:* A planner has global map and agent information and generates a joint solution (e.g., CBS).
- *Decentralized planning:* Each agent chooses actions using its own observations, internal memory, and possibly messages from neighbors.
- *Hybrid:* A central planner may produce initial guidance while local agents handle execution conflicts. State exactly which information is centralized in each phase.

**Learning architecture — only if ML is added**

- *CTCE:* Centralized training and centralized execution.
- *CTDE:* Centralized training, decentralized execution. A global critic or teacher may use full training-state information; deployed policies cannot.
- *DTDE:* Decentralized training and decentralized execution, without privileged central training input.

For agent \(i\), a general decentralized policy can be written as

\[
a_i(t) = \pi_i\!\left(o_i(t), b_i(t), m_i^{\le t}, g_i\right),
\]

where \(o_i\) is its observation, \(b_i\) its local belief, \(m_i^{\le t}\) received messages, and \(g_i\) its goal. The policy may be hand-designed. In CTDE, a training critic may use global state \(V_\phi(s)\), but the executing actor may not.

**Research issue:** individually rational shortest paths are not necessarily jointly feasible; decentralized agents must coordinate priorities, reservations, right-of-way, or local joint maneuvers. Neither “distributed” nor “learned” is novel on its own.

### 2.2 “How would it find the solution in each case?”

Explain and implement the mechanisms:

- **Centralized:** Known global graph and all starts/goals -> CBS/PP/EECBS/MAPF-LNS2 computes compatible paths; execution follows the schedule, possibly with dependency tracking.
- **Decentralized, known map:** Each agent plans locally and resolves predicted conflicts using neighbor negotiation, priority inheritance/backtracking, or agreed reservations; conflicts beyond sensing/communication cannot simply be assumed absent.
- **Decentralized, unknown map:** Each agent senses, maintains local map/belief, plans incrementally through known and unknown terrain under an explicit policy, exchanges relevant discoveries, coordinates conflict-prone moves, and replans on new observations.
- **With learning:** A policy maps local observation/history to actions. Training can be centralized, but execution privileges must be audited separately.

### 2.3 Synchronous vs asynchronous: three different axes

1. **Synchronous action execution:** all agents act at shared timestep boundaries with unit duration.
2. **Asynchronous action execution:** actions begin and finish at different real times; travel durations may vary.
3. **Asynchronous coordination/computation:** decisions and messages arrive at different times; agents do not wait for a global information barrier.

Do not conflate them. A solver can be centralized yet execute asynchronously, or decentralized yet use synchronized rounds. Existing collision checks at integer \(t\) are insufficient for realistic unequal-duration motion.

Example: Agent A is scheduled to vacate X before B arrives. If A is delayed, B's originally collision-free synchronized path can become unsafe. Robust execution requires either barriers, temporal dependencies, reservations, or online conflict resolution with explicit failure handling.

### 2.4 What if the environment is unknown?

Distinguish:

- Unknown static obstacle locations.
- New/moving obstacles (dynamic environments).
- Partial visibility of other agents and their intentions.
- Unknown or newly arriving goals (lifelong/task-allocation problems).

**Initial research scope recommendation:** static but initially partially unknown obstacles; known self-position and target coordinate; limited sensor radius; local knowledge of other agents; heterogeneous movement durations; communication delays/loss; no continuous arrival of new tasks in the primary experiments. Dynamic obstacles and lifelong MAPF are secondary extensions, not prerequisites.

For each agent, maintain

\[
B_i^t(v) \in \{\text{free},\text{blocked},\text{unknown}\}.
\]

The planner must never treat an unobserved cell as *verified free*. Different exploratory cost assumptions are allowed if stated, but movement into an unverified cell must satisfy the physical/sensing model. A “map revealed only in the visualization” while the planner still uses global BFS is **not** partial observability.

---

## 3. Research direction, hypotheses, and alternative paths

### 3.1 Overall recommendation

**Primary:** Information-freshness-aware, event-driven, decentralized coordination in partially known maps.  
**Secondary algorithmic ingredient:** Topology-aware bottleneck coordination (corridors, narrow doors, dead ends).  
**Deferred / optional:** CTDE-learned communication or conflict escalation policy, introduced only if rule-based baselines leave a clearly measured gap.

### 3.2 Candidate A — information freshness and selective coordination

**Working idea:** Agents maintain local beliefs about map occupancy, neighbor intentions, and age of updates; they communicate/coordinate more aggressively where stale information could cause collisions, while avoiding unnecessary global synchronization in open spaces.

Possible high-level definition:

\[
A_{ij}(t)=t-t_{ij}^{\text{last valid update}},
\]

where \(A_{ij}\) is the age of the latest *valid* state/intention message from agent \(j\) known to agent \(i\). Use physical time or an explicitly defined simulation clock; clock-skew assumptions and message sequence numbers must be modeled.

A tentative conflict score might use

\[
R_i(t) = f(C_i(t), U_i(t), A_i(t), D_i(t), T_i(t)),
\]

where \(C\) is predicted contention, \(U\) local map uncertainty, \(A\) information age, \(D\) estimated execution delay, and \(T\) a topology bottleneck feature. **This equation is only a design sketch; specifying a weighted sum is not a novel algorithm.**

Potential **actual** contribution: a coordination/commitment protocol that reduces avoidable waiting and communications under delayed information while preserving defined safety guarantees, or a rigorously characterized boundary where freshness awareness helps/fails.

### 3.3 Candidate B — topology-aware local coordination

Identify articulation points, bridge-like passage structures, narrow corridors, junctions, and dead ends in each agent's **known** local map. Escalate from cheap local priority negotiation to resource-oriented corridor access protocols only when needed. Do not extract these features from the hidden true topology.

Possible specific contribution: reservation allocation for unknown-length corridors with asynchronous arrivals and stale messages; compare against topology-oblivious priority and always-on reservation protocols.

### 3.4 Candidate C — CTDE exploration/communication learning

Train agents (with a privileged global critic *during training only*) to decide *whether* to share a discovered obstacle, request coordination, or explore alternative passages. Execute with local observations. Compare with simple heuristic triggers and strong learned policies where feasible. Do **not** treat a neural module as scientific novelty by itself.

### 3.5 Falsifiable research questions

- **RQ1:** How do partial map knowledge, update staleness, and asynchronous movement interact to affect completion, collisions, waiting, and communication?
- **RQ2:** Under equal information and safety assumptions, does freshness-aware local coordination improve executed cost/makespan/throughput over strong established local coordination and robust execution baselines?
- **RQ3:** Which environments benefit most: open maps, one-cell chokepoints, multi-room maps, long corridors, mazes, and dead ends?
- **RQ4:** What is the communication–efficiency–safety trade-off as delay, loss, sensing radius, and fleet size vary?
- **RQ5:** Can a protocol satisfy a precisely formulated collision-avoidance invariant; what assumptions are required for eventual progress?
- **RQ6 (optional):** Does CTDE add value beyond tuned deterministic, topology-aware, and freshness-aware rules on genuinely unseen maps and delay conditions?

### 3.6 Pre-registered hypotheses (not results)

- **H1:** Adding *correctly designed* freshness-aware coordination decreases unnecessary waits at high contention compared with an otherwise identical fixed communication scheme, at comparable safety.
- **H2:** Benefits grow as message latency and asynchronous execution variability increase, until severe loss makes coordination information unusable.
- **H3:** Bottleneck-aware local reservations improve hard corridor/room cases relative to topology-blind negotiation, but may add needless overhead on open maps.
- **H4:** Selective communication reduces message volume compared with periodic broadcasting; whether that also improves travel cost is an empirical question.

Record the null hypotheses and failure criteria before tuning on final test instances.

### 3.7 Stop/go decision gates

- **Gate G0:** Original repository tests and baselines audited.
- **G1:** Literature matrix identifies a precise gap not already solved by closest prior art.
- **G2:** Event simulator validated against hand-derived ground-truth timelines and conservation invariants.
- **G3:** At least two meaningful decentralized/uncertainty/asynchrony baselines fairly reproduced.
- **G4:** Proposed approach provides a reliable improvement or independently meaningful empirical insight; negative results recorded honestly.
- **G5:** Ablations, generalization, statistical analysis, and manuscript review satisfy Section 13.

If G1 fails, **change the research question**, not the language of the claim. If G4 fails, report what was learned, retune only on development instances, and reassess before manuscript claims.

---

## 4. Literature review: priority reading and novelty boundaries

**Instructions:** Read primary papers, not just abstracts. Record each paper's problem variant, information available to each agent, centralized components, action timing, sensing/communication assumptions, collision model, safety/liveness guarantees, metrics, datasets, release/code status, and strengths/limitations. Do not assume a method supports packet loss, partial maps, or decentralized execution unless the paper explicitly states it.

### 4.1 Classical MAPF and strong offline baselines

1. **Stern et al., 2019 — Multi-Agent Pathfinding: Definitions, Variants, and Benchmarks.** Definitions and standardized benchmark conventions. https://www.movingai.com/benchmarks/mapf.html
2. **Sharon et al., 2015 — Conflict-Based Search for Optimal Multi-Agent Pathfinding.** The classical centralized reference. https://doi.org/10.1016/j.artint.2014.11.006
3. **Li, Ruml & Koenig, 2021 — EECBS: A Bounded-Suboptimal Search for MAPF.** Stronger offline baseline than educational CBS. https://doi.org/10.1609/aaai.v35i14.17466
4. **Li et al., 2022 — MAPF-LNS2: Fast Repairing for MAPF via Large Neighborhood Search.** Large-scale path repair. https://doi.org/10.1609/aaai.v36i9.21266

**Implication:** Do not claim superiority over contemporary centralized MAPF on the basis of basic pure-Python CBS alone. Global-map offline solvers are useful *oracle* or *reference* conditions, not fair decentralized same-information competitors.

### 4.2 Decentralized coordination and local learning

5. **Okumura et al., 2019 — Priority Inheritance with Backtracking (PIBT).** Locally coordinated, implementable in decentralized form. Its finite-time reachability guarantee depends on a graph-cycle condition and is not universal over arbitrary corridors/dead ends. https://doi.org/10.24963/ijcai.2019/76
6. **Damani et al., 2020 — PRIMAL2.** Distributed reinforcement/imitation learning for lifelong and partially observable MAPF. https://arxiv.org/abs/2010.08184
7. **Wang et al., 2023 — SCRIMP.** Communication-enabled learned local policies, including very small fields of view. https://arxiv.org/abs/2303.00605
8. **Skrynnik et al., 2024 — Decentralized MCTS for Partially Observable MAPF.** Model-based decentralized learning/planning under limited observations/communication. https://doi.org/10.1609/aaai.v38i16.29703
9. **Skrynnik et al., 2024 — When to Switch: Planning and Learning for Partially Observable MAPF.** Hybrid heuristic/RL switching is already studied. https://doi.org/10.1109/TNNLS.2023.3303502
10. **Wang et al., 2025 — LNS2+RL.** Hybrid learning/search is not novel by itself. https://doi.org/10.1609/aaai.v39i22.34501

**Implication:** Decentralization, learned communication, tiny sensor windows, switching, and MARL/hybrid planning are established concepts.

### 4.3 Asynchrony, robust execution, and timing

11. **Okumura, Tamura & Défago, 2021 — Time-Independent Planning for Multiple Moving Agents.** Online distributed planning that avoids synchronized action schedules. https://doi.org/10.1609/aaai.v35i13.17347
12. **Levy, Shani & Stern, 2022 — An Online Approach for MAPF Under Movement Uncertainty (extended abstract).** Local joint policies for stochastic actions. https://doi.org/10.1609/socs.v15i1.21792
13. **Berndt et al., 2024 — Receding Horizon Re-Ordering of Multi-Agent Execution Schedules.** Switchable action dependency graphs and robust scheduling. https://doi.org/10.1109/TRO.2023.3344051
14. **Zhou, Zhao & Ren, 2025 — Loosely Synchronized Rule-Based Planning (LSRP) for MAPF with Asynchronous Actions.** Scalable asynchronous solver. https://doi.org/10.1609/aaai.v39i14.33618
15. **Zhou, Zhao & Ren, 2025 — LSRP*: Scalable and Anytime Planning for MAPF with Asynchronous Actions (SoCS extended abstract).** Better-quality anytime asynchronous planning. https://doi.org/10.1609/socs.v18i1.36016

**Implication:** Modeling asynchronous action duration is not enough for novelty. Also investigate the difference between asynchronous planning, asynchronous execution of a static plan, and asynchronous communication.

### 4.4 Unknown maps, partial observability, online repairs

16. **Shofer, Shani & Stern, 2023 — MAPF under Obstacle Uncertainty.** Contingent centralized plans for hidden obstacles, with centralized/decentralized *execution* modes. https://doi.org/10.1609/icaps.v33i1.27219
17. **Malka, Shani & Stern, 2024 — Online Planning for MAPF in Inaccurate Maps.** Interleaves observation, planning and execution and selectively replans for affected agents. https://doi.org/10.1109/IROS58592.2024.10801975
18. **Parimi et al., 2026 — Belief-Aware MAPF under Map Uncertainty (preprint, not automatically peer reviewed).** Spatial belief inference and uncertainty-aware map costs; check publication status before citing as a journal/conference article. https://arxiv.org/abs/2609.40269
19. **MovingAI MAPF benchmark page.** Standard map and scenario sources and attribution. https://www.movingai.com/benchmarks/mapf.html
20. **MovingAI file format specification.** Avoid format mistakes and inadvertent changes in movement conventions. https://movingai.com/benchmarks/formats.html

**Implication:** “unknown obstacles + online replanning” is already an investigated problem. A new combination of known components is not automatically a new contribution.

### 4.5 Mandatory literature-review outputs

Create:

- `research/literature/literature_matrix.csv` with columns `id,authors,year,title,venue,status,doi_or_url,public_code,problem_variant,training,planning_architecture,execution_architecture,full_map_available,sensing,communication,async_actions,async_messages,collision_model,formal_guarantee,benchmarks,metrics,closest_overlap,verified_notes`.
- `research/literature/annotated_bibliography.md`: 150–300 words per core paper, actual limitation and evidence, not generic summaries.
- `research/literature/novelty_gap.md`: precise differences between the proposed mechanism and the 5–8 *closest* papers; quote page/section numbers when possible.
- `research/literature/claim_to_evidence.csv`: every prospective contribution claim paired with evidence and competing prior work.
- `research/literature/related_work_queries.md`: dated search strings used on Google Scholar, Semantic Scholar, DBLP, arXiv, IEEE, ACM, AAAI/IJCAI, and citations backward/forward. Include 2025–2026 work and refresh before submission.

**No novelty gate without this matrix.** If a paper's details could not be verified, mark `unverified`, never infer its guarantees from a title.

---

## 5. Formalize the new problem before coding

### 5.1 World and agents

Let the hidden physical environment be \(G^*=(V^*,E^*)\), with blocked cells/edges and known geometric bounds. Agents have start states \(s_i\), known destination coordinates \(g_i\), and local clocks/event schedules. Static hidden obstacles are generated before the episode and remain fixed in the primary experiment.

The executing agent cannot read \(G^*\). It may maintain a belief/partial map \(B_i(t)\), including observation provenance and timestamps. Other agents' future intentions are not globally known by default.

### 5.2 Observations and sensing

Specify and test all of:

- Manhattan or Euclidean sensor radius (choose one explicitly).
- Whether walls occlude line of sight or sensor visibility passes through them.
- Whether sensing happens continuously, at movement completion, or at scheduled sensor events.
- Whether current positions of nearby agents are directly observable, including while they traverse an edge.
- Positioning assumptions: perfect localization in the main study; noise as a clearly labeled extension.
- Whether observation events, observations, and communicated reports have independent delays.

Do not silently give agents all starts/goals of other agents unless that information is part of the named scenario variant.

### 5.3 Physical time and collision semantics

Use real-valued simulation time where appropriate; action durations can be constant, stochastic, or heterogeneous. Define each movement as a time interval and reserve both appropriate vertex occupancy and edge traversal resources. Handle opposite-direction traversal conflict; same-vertex overlap; departure/arrival at equal timestamps; and goal occupancy. Decide whether robots are points or have a nonzero body/safety radius, and state the limitation.

**Critical:** The old synchronous “follow move” convention does not automatically carry over to continuous-time occupancy. For example, one robot may enter a cell at exactly the instant another completely leaves if the movement and clearance model permits it. Define the boundary convention, and test it.

All collisions are detected by the **simulator's authoritative physical state**, not by the agents' predicted state. Hidden ground truth is permitted in the simulator and external evaluator, never for policy decisions.

### 5.4 Communication

Represent each directed message as

\[
m=(\text{sender},\text{receiver},\text{type},\text{payload},\text{seq},t_\text{send},t_\text{delivery}).
\]

Model configurable radius/connectivity, byte size, latency distributions, loss, duplication and reordering (at minimum loss + latency; others as stress tests). Decide which parts are known to an agent, and whether clocks are synchronized. Distinguish freshness of *position observations*, *map discoveries*, and *commitment/reservation state*: these have different consequences.

### 5.5 Solution quality and objectives

For each episode report:

- Episode completion fraction and **success by deadline**.
- Collision count and severity under a clearly specified physical model.
- Realized executed sum of costs (distance or elapsed travel/wait time; give both when possible).
- Real-time makespan, completed tasks/throughput if episodic goals are completed, and per-agent delay.
- Waiting fractions, local/global deadlocks, fairness/starvation, and number of replans.
- Total and per-agent communications (messages and serialized bytes).
- Planning/computation CPU time and decision latency; simulator wall time separately.
- Memory, scalability, and robustness to heterogeneous delays, message drop, and sensor radius.

Define metric denominators and how unsuccessful/timeout episodes are handled before experiments. Never report only successful-episode mean SOC when success differs across methods.

### 5.6 Safety versus liveness and impossibility boundaries

**Safety:** No two physically conflicting movements or occupancies occur.  
**Liveness:** Agents eventually progress and, under appropriate assumptions, reach feasible goals.  
**Efficiency:** How much movement, waiting, communication, and computation are consumed.

With unbounded communication loss, completely hidden approaching agents, no shared safety resource, and arbitrary delays, an unconditional safety/liveness guarantee is not credible. Identify necessary assumptions and perhaps prove a **restricted conditional invariant**, not an impossible global promise.

For any reservation scheme, **expiry alone must not imply that a resource is empty**. An agent can still occupy a cell or corridor after a lease expires if it is delayed or fails. Safe recovery requires an acknowledged release, trustworthy sensing, or another explicitly justified mechanism. Fail-closed behavior can preserve safety but may prevent liveness; quantify it.

### 5.7 Variants and fairness

Maintain named, versioned conditions, e.g.:

- `KNOWN_SYNC_GLOBAL`: original offline reference, privileged global input.
- `KNOWN_SYNC_LOCAL`: known map, local coordination, synchronized moves.
- `KNOWN_ASYNC_LOCAL`: known map, local coordination, asynchronous moves.
- `UNKNOWN_SYNC_LOCAL`: partial map, synchronized moves.
- `UNKNOWN_ASYNC_RELIABLE`: partial map, asynchronous moves, reliable communication.
- `UNKNOWN_ASYNC_DELAYED`: plus latency and staleness.
- `UNKNOWN_ASYNC_LOSSY`: plus packet loss.

Do not compare a global-map optimal planner against a local-knowledge policy as if their information access were equal. Show global-map planners as upper-bound/oracle context and use matched-information baselines for primary claims.

**Deliverable:** `research/problem_formulation.md`, with all assumptions numbered and fixed before the final evaluation.

---
## 6. Implementation specification and directory architecture

### 6.1 Suggested organization

Add new modules without breaking the old interface. Adapt actual names after the audit; do not create redundant duplicate folders if equivalent infrastructure already exists.

```text
research/
  decision_log.md
  original_project_audit.md
  problem_formulation.md
  research_questions.md
  literature/
    literature_matrix.csv
    annotated_bibliography.md
    novelty_gap.md
    related_work_queries.md
    claim_to_evidence.csv
  protocol_spec.md
  experiment_protocol.md
  risk_register.md
  reports/
  manuscript/
    paper.tex
    references.bib
    figures/
    tables/
    supplementary.tex
    reviewer_checklist.md

simulation/
  events.py             # deterministic event queue and event clock
  world.py              # authoritative true map, physical locations
  actions.py            # move/start/finish/wait and occupancy intervals
  sensors.py            # local observations, radius and occlusion
  communication.py      # latency, loss, sequence, bytes, optional duplication
  monitor.py            # independent collisions, invariants, deadlocks
  scenarios.py          # scenario seeds and hidden-map derivation

agents/
  interfaces.py         # observation/message/action/belief contracts
  belief.py             # local map and neighbor-intention memory
  local_search.py       # local A*, bounded/online replanning
  negotiation.py        # local reservations / commitments
  protocols.py          # release/ack safety states, idempotence, recovery

baselines/
  legacy_adapter.py     # original PP/CBS on known-map reference scenarios
  local_independent.py
  pibt.py
  fixed_broadcast.py
  local_reservation.py
  online_replanning.py
  async_dependency.py   # compatible with the chosen assumptions

methods/
  freshness_aware.py    # hypothesis-driven proposed method
  topology_aware.py     # optional second component
  learned_trigger.py    # strictly optional; gated

evaluation/
  # retain existing files; add only needed modules:
  async_metrics.py
  scenario_registry.py
  runners_async.py
  ablations.py
  statistical_analysis_async.py

config/
  async_experiments.yaml
  async_development.yaml
  async_final_holdout.yaml

scripts/
  run_async.py
  validate_async.py
  analyze_async.py
  generate_research_figures.py

results/async/
  raw/
  manifests/
  tables/
  figures/
  failure_cases/

tests/
  test_event_ordering.py
  test_physical_collisions.py
  test_sensing_and_privilege.py
  test_message_delivery.py
  test_belief_updates.py
  test_negotiation_invariants.py
  test_agent_deadlocks.py
  test_async_baseline_regression.py
  test_reproducibility_async.py
```

### 6.2 Interface contracts

Define typed, documented structures (dataclasses are adequate):

```python
Observation(ego_id, event_time, ego_pose, visible_cells,
            visible_agents, sensor_metadata)
Message(sender, recipient, kind, sequence_id, send_time,
        deliver_time, payload, byte_count)
AgentDecision(action_kind, next_vertex=None, negotiation=None,
              predicted_duration=None)
ActionEvent(agent_id, resource, start_time, end_time, status)
EpisodeResult(status, safety_violations, completion_fraction,
              executed_soc, makespan, waits, messages, bytes, ...)
```

The exact API can change. Its **invariants** cannot: agent decisions receive only allowed information; event timestamps are ordered deterministically; simulated physics independently enforces the world model; output schemas are versioned and machine readable.

### 6.3 Deterministic event queue

Use events such as `SENSE`, `MESSAGE_SEND`, `MESSAGE_DELIVER`, `REQUEST_RESOURCE`, `RESOURCE_GRANTED`, `ACTION_START`, `ACTION_FINISH`, `ACTION_FAILED`, `REPLAN`, and `EPISODE_TIMEOUT`.

For equal timestamps specify an explicit deterministic order, e.g. `(time, safety_phase, sequence_no)`; never allow arbitrary Python dictionary iteration to affect physical outcomes. Test alternative tie-handling conventions if they alter collision semantics. In particular, the event queue must not allow an agent to start an action based on a completion event that has not actually happened.

### 6.4 Strict separation of responsibilities

- **World/simulator:** may see the true map and all positions. Generates observations, moves robots, and detects collisions.
- **Agent:** sees only its own observations/messages, local state, and allowed fixed prior information.
- **Baseline oracle adapter:** may see global state *only* when explicitly run in an oracle condition.
- **Metric collector:** may see ground truth after execution for evaluation, but must not send it to the agent.
- **Plotter/paper scripts:** read stored result rows rather than rerunning/tuning experiments silently.

Add privilege-audit tests by injecting a “secret obstacle” inaccessible to the agent and asserting that its planned decision cannot depend on the hidden obstacle before a legitimate observation or message.

---

## 7. Full task backlog with acceptance criteria

### Phase 0 — Baseline reproduction and audit

- [ ] Record Git commit SHA, directory tree, Python version, dependencies, OS, hardware, and test count.
- [ ] Execute and capture original tests; explain every failure, warning, and discrepancy.
- [ ] Regenerate at least a small subset of each original benchmark suite and compare output definitions with `REPORT.md`.
- [ ] Verify all baseline planners return start/goal-valid, collision-checked plans under *original* semantics.
- [ ] Check CBS optimality claims against small exhaustive joint-state searches and verify termination/timeout behavior.
- [ ] Inspect the adaptive selector for leakage from full-map features, train/test overlap, or post-hoc feature computation.
- [ ] Audit randomness and pairwise scenario seeds; distinguish nominal from observed obstacle density.
- [ ] Record issues as `critical`, `major`, `minor` with file and line numbers where possible.

**Done when:** Original functionality is reproducible and its assumptions are captured in an immutable baseline manifest. Do not improve the original experiments while pretending they are unchanged.

### Phase 1 — Formalization and literature gap

- [ ] Produce the formal model, information-access table, collision/time/communication semantics, and named variants.
- [ ] Complete the literature matrix and identify the **three closest algorithms**, not merely famous ones.
- [ ] Extract an actionable limitation from each: exact assumptions, the scenario where it fails, and evidence from original papers.
- [ ] Verify which baselines provide public code and what can be reproduced fairly.
- [ ] Select a *single primary claim* and two secondary observations, rather than a vague claim of a universally superior MAPF solution.
- [ ] Establish development/final holdout split before algorithm tuning.

**Done when:** A skeptical reviewer can distinguish the new proposed mechanism from PIBT, online inaccurate-map replanning, time-independent planning, LSRP, and communication-aware learned coordination.

### Phase 2 — Event-driven physical simulator

- [ ] Implement authoritative asynchronous state and event scheduling.
- [ ] Support heterogeneous per-agent movement durations and seeded stochastic delays.
- [ ] Implement waiting/blocked moves and travel time cost accounting.
- [ ] Implement vertex-occupancy interval conflicts and edge conflicts, with stated simultaneous arrival/departure rules.
- [ ] Add independent collision monitor and invariant assertions.
- [ ] Verify event ordering, duplicate events, resource lock states, and termination conditions.
- [ ] Verify limiting case: identical unit durations plus synchronous starts recovers classical grid semantics where applicable.

**Done when:** Hand-crafted traces and property tests establish consistency of simulated execution and collision detection independently of planners.

### Phase 3 — Observation and communication model

- [ ] Per-agent local maps with `known_free`, `known_blocked`, `unknown`, timestamp, provenance.
- [ ] Limited sensing; correctly handle occlusion and discovery timing.
- [ ] Support updates from own sensors versus other-agent messages with provenance.
- [ ] Add delayed, lost, reordered, and duplicate message tests; use unique message IDs.
- [ ] Count actual serialized bytes and message frequency, not merely calls to a `send` method.
- [ ] Add controls for range/reachability; compare all-to-all reliable links versus local lossy links in separate scenarios.
- [ ] Add unit tests forbidding privileged full-map access from policies, including heuristics.

**Done when:** Two agents can legitimately hold different map beliefs, receive the same discovery at different times, and act without unintended central information.

### Phase 4 — Fair decentralized baselines

Implement in increasing order of difficulty:

- [ ] **Independent local A\* with online replanning:** a deliberately weak lower baseline; unsafe behavior must be recorded, not hidden.
- [ ] **Fixed periodic communication:** broadcast observation/intent every chosen interval, with a defined coordination policy.
- [ ] **PIBT:** faithful implementation or wrapped public implementation, with explicitly documented applicability on maps with/without PIBT's graph assumptions.
- [ ] **Local reservation/negotiation:** fixed priority and safe commitments, using only local information.
- [ ] **Online inaccurate-map replanning:** a version matching the published setting as closely as feasible; differentiate adaptations from authentic reproduction.
- [ ] **Asynchronous execution comparison:** ADG-like dependency schedule, a time-independent planning baseline, or LSRP depending on code availability and exact experimental compatibility; document any oracle/global input.
- [ ] **Global-map references:** PP/CBS/EECBS/MAPF-LNS2 when relevant; label these as offline/oracle or privileged-information benchmarks.
- [ ] Shared input scenarios, physical simulator, observation settings, runtime budget, and metrics for all matched-information baselines.

**Done when:** Proposed improvements cannot be explained merely by comparing against Independent A\* or by giving one method more information or faster hardware.

### Phase 5 — Proposed method v1: simple, understandable, testable

Do not start with a large neural architecture. Develop a protocol that could be independently tested and explained.

- [ ] For each agent, maintain freshest known neighbor position/intention with an age and sequence number.
- [ ] Build a short-horizon local conflict predictor; do not look beyond legitimately observed/communicated state.
- [ ] Classify local movement proposals: unconstrained free movement; possible shared-resource conflict; uncertain/corridor movement; stale-information case.
- [ ] Define explicit, deterministic negotiation messages such as `REQUEST`, `GRANT`, `REJECT`, `COMMIT`, `RELEASE`, `ACK` (or a smaller rigorously chosen protocol).
- [ ] Specify a safe transition state machine; idempotence for retries; rules for out-of-order requests; recovery from interrupted negotiations.
- [ ] Design a starvation/deadlock strategy (bounded local priority or backtracking), with honest assumptions and fallback behavior.
- [ ] Define a baseline freshness threshold or conservative predictive criterion on development data; do not tune on test results.
- [ ] Add adaptive communication triggering when new information would affect a pending path/reservation. Compare with fixed periodic and always-broadcast baselines.
- [ ] If topology-aware escalation is introduced, calculate corridor membership only from known/local map structure.
- [ ] Use minimally sufficient communication payloads and log byte costs.

**Done when:** A clear pseudocode procedure exists, all message transitions are test-covered, and failure cases are documented. If the mechanism is essentially a standard well-known reservation protocol plus a threshold, re-evaluate novelty before writing a methods paper.

### Phase 6 — Safety analysis and adversarial testing

Required scenarios:

- [ ] Two agents face each other in a 1-cell corridor.
- [ ] Two agents enter a room through a shared 1-cell doorway.
- [ ] An agent finishes a move later than predicted and blocks an intended follower.
- [ ] Simultaneous requests for one cell or edge.
- [ ] Message delayed until after it would have been useful.
- [ ] Lost `GRANT`, lost `COMMIT`, lost `RELEASE`, and lost `ACK`.
- [ ] Duplicate and reordered message delivery; sequence wrap/old updates if applicable.
- [ ] One agent stops indefinitely in a reserved resource (test safety versus liveness separately).
- [ ] Previously unknown corridor is discovered blocked.
- [ ] Agents disagree about a wall or current reservation due to delayed observations.
- [ ] One agent occupies its goal indefinitely in a choke point.
- [ ] A known-map route is feasible but partially observed local navigation explores a dead end.
- [ ] An infeasible hidden map disconnects start from goal (correct infeasibility labeling vs timeouts).
- [ ] Sparse and dense traffic extremes.

For each, save a replayable event log. Add property-based/fuzz tests over seeds and adversarial event sequences. Check collision freedom independently from protocol code.

**Safety proof (optional but valuable):** Formalize a protocol invariant such as “at any physical time, at most one compatible owner may commit to an exclusive resource,” then prove induction over authorized resource-acquisition and release events under explicit trustworthy-sensing and message assumptions. Do **not** claim reachability/completeness unless also proven; safe waiting can deadlock.

### Phase 7 — Ablation and parameter research

- [ ] `full_method`.
- [ ] `minus_freshness` — stale neighbor information treated uniformly or a fixed policy.
- [ ] `minus_topology` — no passage-aware escalation.
- [ ] `minus_selective_comm` — fixed-period/always-broadcast communication.
- [ ] `minus_local_repair` — replans full local route after every relevant discovery.
- [ ] `minus_delay_awareness` — constant-duration assumptions, evaluated on asynchronous movement.
- [ ] If learned: `minus_learning`, heuristic-only matched-feature controller, and a same-budget simple model.
- [ ] Sweep hyperparameters only on development data; publish chosen values and search budget.

**Done when:** The advertised component provides a measurable, interpretable benefit beyond other components, and results are not the product of over-tuned arbitrary weights.

### Phase 8 — Scalability and robustness

- [ ] Agent counts: start small (e.g. 5, 10, 20, 40, 80) and scale upward only where meaningful.
- [ ] Grid sizes: start at 16/32/64 and expand if planning/visualization permits.
- [ ] Map families: random, rooms, maze, warehouse-style corridors, and MovingAI maps.
- [ ] Obstacle densities: independently measure realized blocked-cell fraction.
- [ ] Initial unseen fraction: fully known, moderate, and high uncertainty.
- [ ] Sensor radii: e.g. 1/2/3/5/7, under a stated metric and occlusion model.
- [ ] Message latency: none, low, moderate, heavy-tailed, plus reordering where supported.
- [ ] Message loss: 0%, small, moderate, severe; loss distributions must be documented.
- [ ] Movement durations: deterministic, homogeneous stochastic, heterogeneous, and heavy-tail stress conditions.
- [ ] Bottleneck severity: topology/flow-based structural metrics.
- [ ] Evaluate both easy and deliberately adversarial pathological scenarios.

**Done when:** Results identify a stable operating region, failure region, and sensitivity to key assumptions; not only an averaged “win rate.”

### Phase 9 — Optional learned component (start only if Gates G1–G4 support it)

- [ ] Specify the exact learnable decision (e.g. message trigger, escalation, or neighbor-selection), not “use MARL for path planning” vaguely.
- [ ] Define CTDE versus DTDE input boundaries and inference interface.
- [ ] Use curriculum/map diversity and fixed train/val/test generation seeds.
- [ ] Restrict actor input to available local observations and memory.
- [ ] Audit test leakage and privileged teacher information.
- [ ] Compare equal computational budgets, behavior-cloned/rule baselines, and training-free heuristics.
- [ ] Test transfer to unseen map families, agent counts, sensor radii, and delay distributions.
- [ ] Report training compute, GPU/CPU, wall time, seeds, and variance.
- [ ] If learned controller adds no robust benefit, exclude it from the primary proposed method and discuss as a negative exploratory result.

### Phase 10 — Manuscript and release

- [ ] Complete novelty and evidence review one final time.
- [ ] Freeze code and evaluation protocol; rerun final benchmarks from a clean environment.
- [ ] Prepare results tables/figures from code-generated raw data, including failures and uncertainty.
- [ ] Write reproducible methods and limitations before abstract and conclusion.
- [ ] Draft paper following Section 13; create supplementary material.
- [ ] Run an adversarial internal review, fix reproducibility and validity defects, repeat analyses when warranted.
- [ ] Prepare anonymous artifact if a venue requests double-blind review.
- [ ] Check publication venue scope, templates, open-access and preprint requirements, dates, and citation formatting **at submission time**.

---

## 8. Baseline comparability and experiment matrix

### 8.1 Comparison groups

| Group | Map available at decision time | Agents' information | Movement | Communication | What it answers |
|---|---|---|---|---|---|
| Classical oracle | Full global map | Global starts/goals | Sync | Central planner | Offline reference and gap |
| Decentralized-known | Full known geometry | Local intentions | Sync | Local/fixed | Cost of decentralization |
| Decentralized-async | Known geometry | Local intentions | Async | Reliable/local | Cost of physical asynchrony |
| Partial-observation | Local map belief | Local intentions | Sync | Reliable/local | Cost of hidden obstacles |
| Partial + async | Local map belief | Local intentions | Async | Reliable/local | Combined challenge |
| Partial + async + delay | Local map belief | Stale local intentions | Async | Delayed | Value of freshness-aware design |
| Partial + async + loss | Local map belief | Missing/stale intentions | Async | Lossy | Robustness and failure boundaries |

### 8.2 Fairness checklist

- Same generated true maps, start/goal instances, sensing model, physical movement duration draws, and communication draws **where logically applicable**. Use paired scenario IDs.
- Same permitted information, and clearly mark any oracle baseline that violates it.
- Same success horizon and failure categories.
- Same Python interpreter/hardware when comparing runtime; disclose external optimized baselines and focus interpretation on solution efficiency/robustness rather than raw speed unless controlled.
- Methods should have comparable tuning effort; state every training/tuning budget.
- For communication budget comparisons, use bytes, cadence, and delivery assumptions consistently.
- Separate collision avoidance provided by the simulator from collision avoidance performed by the policy: a simulator that refuses every unsafe action can mask bad planners. Record attempted invalid actions and blocked attempts as separate metrics, in addition to real collisions.
- Do not conceal baselines that fail due to assumptions outside their intended scope; instead categorize them as inapplicable, adapted, unsafe, timed out, or unsuccessful and explain the reason.

### 8.3 Test-set design and statistical discipline

Use two datasets:

1. **Development:** enough varied scenarios to debug, tune, and choose design choices.
2. **Final holdout:** unseen map seeds and, where possible, unseen map *layouts/families*, agent-count ranges, and delay distributions.

Freeze `config/async_final_holdout.yaml` and its hashes *before final model selection*. Do not keep inspecting the final test data and tuning repeatedly. If the final design changes, establish a new honest independent holdout.

Report, at a minimum:

- Every individual run as a row with a unique scenario hash.
- Per-condition success with a binomial confidence interval.
- Paired differences of realized cost/makespan/communications on matched instances; additionally report all-episode outcomes and timeouts.
- Appropriate bootstrap confidence intervals, preferably resampling by scenario/map (not individual frames or time steps, which are correlated).
- Effect sizes and an explanation of practical importance, not just p-values.
- Adjustment or transparent limitations for multiple exploratory tests.
- Exact seed counts and failure/timeout denominators.
- Sensitivity to choices such as horizon, replanning trigger, and message rate.

**Potential metric trap:** “zero collisions” may simply mean the robots waited indefinitely or the simulator rejected moves. Always pair collisions with successful completion, waiting, safety interventions, and failure rates.

---

## 9. Research-ready dataset, logging, and reproducibility

### 9.1 Raw schema

Store one record per `(method, scenario, replicate, config_hash)` in JSONL or Parquet; maintain CSV summaries for human review. Suggested fields:

```text
run_id, git_sha, utc_timestamp, config_hash, scenario_hash, map_family,
map_width, map_height, observed_obstacle_density, initial_unknown_fraction,
agent_count, agent_seed, obstacle_seed, duration_seed, message_seed,
method, variant, baseline_version, oracle_access,
sensor_radius, occlusion_model, delay_model, packet_loss,
termination_reason, completed_agents, completion_fraction, collision_count,
unsafe_move_attempts, deadlock_flag, starvation_count,
executed_distance_soc, executed_time_soc, makespan,
total_wait_time, per_agent_wait_summary, replan_count,
messages_sent, messages_delivered, bytes_sent, bytes_delivered,
planning_cpu_seconds, sim_wall_seconds, peak_memory,
source_manifest_path, event_log_path
```

Define `success`, `timeout`, `infeasible`, `deadlock`, `collision`, `agent_error`, `external_failure`, and `not_applicable` as disjoint reporting outcomes where possible; specify precedence when multiple flags apply.

### 9.2 Replay and provenance

- Write event logs sufficient to replay every collision, deadlock, and representative success without rerunning the planner.
- Seed map generation, action duration sampling, message delivery and loss independently.
- Store exact config, code revision, dependency lock/checksums, hardware, and command line in a manifest.
- Provide script to confirm raw-data consistency and regenerate all primary tables/plots.
- Verify summaries against raw logs with automated assertion tests.
- Keep data/benchmark licenses and attribution clear, particularly MovingAI redistribution obligations.
- Avoid storing enormous repeated raw logs for routine successful episodes when summaries plus seed-based replay are sufficient; always preserve full failure cases.

### 9.3 Reproduction commands (illustrative; implement and test them)

```bash
python -m pytest -q
python scripts/validate_async.py --smoke
python scripts/run_async.py --config config/async_development.yaml
python scripts/run_async.py --config config/async_final_holdout.yaml
python scripts/analyze_async.py --input results/async/raw --out results/async
python scripts/generate_research_figures.py --input results/async/raw
```

These new commands are **desired final deliverables** and do not currently exist simply because they are listed here.

---

## 10. Suggested implementation milestones and deliverables

These are dependency milestones, **not promised completion times**.

| Milestone | Primary artifact | Verification gate |
|---|---|---|
| M0 | `original_project_audit.md` | Original tests and metrics reproduced |
| M1 | `problem_formulation.md`, literature matrix, precise gap | Novelty G1 approved by authors |
| M2 | Event-driven simulator, independently validated collision monitor | Hand traces + property tests pass |
| M3 | Partial-observation and communication machinery | No hidden-state leakage; delivery tests pass |
| M4 | Strong, matched-information baselines | Baseline behavior faithful and documented |
| M5 | Proposed deterministic freshness-aware protocol | Protocol state machine + adversarial tests pass |
| M6 | Development comparison and ablations | Identify if a reproducible improvement exists |
| M7 | Frozen holdout runs, confidence intervals, figures | No unresolved validity blockers |
| M8 | Paper, supplement, code/data artifact | Adversarial review + reproducibility checklist pass |

### Deliverables to return to the project owner at the end of every milestone

1. Changed files and concise explanation.
2. Commands actually executed and outcomes (including failures).
3. New tests and coverage of critical invariants.
4. Quantitative results **only when actually measured**.
5. Known limitations and next action.
6. Decision whether the current novelty hypothesis remains worth pursuing.

Do not return merely “implemented” without tests and traces.

---

## 11. Proving or testing genuine scientific novelty

### 11.1 Novelty claims that are *not sufficient*

- “We solve MAPF in an unknown environment.”
- “We use decentralized agents.”
- “We use CTDE and GNNs.”
- “We add communication.”
- “We account for asynchronous movements.”
- “We combine A\* and reinforcement learning.”
- “We adaptively select between existing algorithms.”
- “We reduce communications by not broadcasting every step.”

Each is preempted or materially narrowed by prior literature. If the final manuscript contains any of these as its central novelty sentence, rewrite the contribution or obtain substantially stronger evidence.

### 11.2 What might be defensible

Possible results, *if demonstrated*:

1. **Protocol contribution:** A precisely new, safe coordination mechanism for conflicting commitments under stale/partially observed map information.
2. **Theory:** A proof of collision avoidance or absence of a specific deadlock class under nontrivial and explicit timing/network assumptions.
3. **Empirical contribution:** Systematic, reproducible identification of a failure regime or phase transition in existing MAPF coordination strategies under map uncertainty + asynchronous execution + stale communications.
4. **Algorithm/efficiency:** Meaningful reduction in communications or waiting while preserving safety and success against directly relevant algorithms under matched information.
5. **Benchmark:** A well-designed, reusable evaluator integrating hidden-map sensing, events, network delivery, safety monitoring, and standard benchmark imports, with evidence the benchmark tests an underexplored interaction.

A collection of old components **without an isolatable mechanism or new evidence** remains an engineering project, even if the resulting demo looks sophisticated.

### 11.3 Adversarial novelty audit

Before finalizing title and abstract, ask:

- Which published work is closest to our claimed algorithm?
- Is our method merely the same algorithm with renamed states/thresholds?
- Does the proposed benefit remain when comparing against a tuned, resource-aware baseline rather than a deliberately weak method?
- What scenario breaks the proposed method but not the best baseline?
- Does the theoretical statement assume reliable global communication, contradicting the decentralized/packet-loss motivation?
- Could a simple deterministic priority/age rule achieve the same effect?
- Does the improvement disappear if communication cost is counted in bytes or collisions are evaluated continuously?
- Is the dataset or experiment itself new and useful enough to publish even if the algorithm is not?
- Has a relevant late-2025/2026 paper already answered this exact question?

Record answers in `research/literature/novelty_gap.md` with citations. If no claim survives, conduct the study honestly as a strong reproducibility/benchmark project and refine the research direction.

---

## 12. Visualization and demonstration deliverables

A convincing research project should be understandable without reading source code. Build:

- Local belief map viewer: known free, known obstacle, unknown, discovery time, origin of knowledge.
- Ground-truth map view **available only to the observer/evaluator**, not algorithmically accessible to agents.
- Per-agent message timeline: sent, delayed, lost, duplicated, acknowledged.
- Execution timeline: current movement, occupancy interval, reservation state, waiting, and actual arrival time.
- Conflict visualizer: potential predicted conflicts versus physical collisions/invalid attempted actions.
- Reproducible side-by-side algorithm replay on the same scenario seeds.
- Benchmark dashboard: trade-offs between completion, makespan, waiting, communication, and safety across scenario types.

A browser demo is supplementary. If time or complexity is constrained, prioritize static reproducible figures and replay logs over UI polish.

---

## 13. Manuscript development, scientific writing, and submission

### 13.1 When to write the manuscript

Start detailed scientific writing when the full method is defined and the experimental protocol is frozen. A provisional outline and related-work notes may exist earlier, but **do not write results, abstract conclusions, significance claims, or claimed improvements before experiments**.

### 13.2 Recommended paper structure

**Title:** Narrowly convey verified mechanism and setting; avoid words such as “optimal,” “guaranteed,” “first,” or “state of the art” unless proven.

**Abstract (draft last):** Problem and assumption gap -> precise method -> evaluation protocol -> measured main result with uncertainty -> limitations/implications. No unmeasured numbers.

**1. Introduction**

- The difference between known-map synchronous planning and decentralized robot execution.
- Why stale information and hidden obstacles are important.
- Explain the **specific** failure mode studied (e.g., asynchronous occupation of a narrow passage under delayed information).
- State three or fewer concrete, non-overlapping contributions supported by citations and evidence.

**2. Related work**

- Classical/global MAPF (CBS, EECBS, MAPF-LNS2).
- Decentralized/local coordination (PIBT, learned approaches).
- Partial observation and hidden-map planning (Shofer; Malka; later work).
- Asynchronous execution (time-independent planning, ADG/SADG, LSRP).
- Communication under delay and selective disclosure; include all closest newer work.
- Explicitly articulate how the proposed work differs in problem assumptions, mechanism, and tested outcomes.

**3. Problem formulation**

- True world, observation process, asynchronous action time, network model, safety/liveness, goals and objective.
- Table of information available centrally and to each agent.
- List failure assumptions and the exact scope of any proof.

**4. Proposed method**

- Agent memory/beliefs, message protocol, local planning, risk estimates, conflict negotiation, deadlock handling.
- Algorithm pseudocode (agent-local and simulator-agnostic).
- Computational/communication complexity or practical runtime analysis.
- Safety theorem if actually proven; otherwise explain mechanism and empirical validation without false guarantee.

**5. Experimental design**

- Benchmark sources and licenses; map splits; scenario parameters.
- Fairness conditions and baseline configurations.
- Metric definitions, hardware, compute budgets, tuning methodology, seeds, statistical tests.
- Validity and stress tests, including failures.

**6. Results**

- Main matched-condition table with success, safety, realized path cost/makespan, communications.
- Scalability and communication/delay sensitivity.
- Unknown-map challenge and bottleneck breakdown.
- Ablations and trade-off curves.
- Qualitative trace of at least one representative success and one failure.

**7. Discussion / limitations**

- Safety assumptions, network/sensor model, map discretization, incomplete observation, global oracle caveats, deadlocks, generalization, sim-to-real gap, and computational scalability.
- Why result does or does not transfer to real robots.
- Any negative and inconclusive findings.

**8. Conclusion**

- Restrained claims based on actual measured evidence; direct future research directions.

**Supplementary material**

- Full proof, additional pseudocode, hyperparameters, test protocols, extended results, additional seeds, repository revision, and artifact reproduction instructions.

### 13.3 Tables and figures required

1. Assumptions/comparison table (our setting vs closest prior methods).
2. Architecture diagram and agent-local information boundary.
3. Agent-message timing sequence with a collision/stale-message failure example.
4. Algorithm pseudocode and protocol state machine.
5. Main success/realized cost/makespan/bytes/safety table.
6. Performance vs agent count and/or map topology.
7. Performance vs delay and packet loss.
8. Communication-efficiency Pareto trade-off.
9. Ablation table or plot.
10. Representative replay of a failure or deadlock, with explanation.

Every data figure must be generated by a documented script; no manual rewriting of inconvenient results.

### 13.4 Reporting and ethical research requirements

- Cite original work rather than attributing old mechanisms to this project.
- No fabricated experiments, artificial “expected” values presented as results, synthetic confidence intervals, or invented reviewer feedback.
- No generated numerical claims unless traceable to raw run files.
- Distinguish peer-reviewed publication, preprint, and extended abstract.
- Disclose LLM/software assistance according to venue policy; authors remain responsible for methods and correctness.
- State limitations prominently rather than burying them.
- Confirm coauthor eligibility and contributions with actual contributors; do not automatically list all course-project members on the research paper.
- Decide authorship and public-release permissions with the project team and supervisor.
- Observe third-party benchmark/code licenses and citation requirements.
- Do not publish a manuscript as “accepted” or “under review” unless that status is true.

### 13.5 Publication venues (illustrative; check current calls and requirements)

Potential matches based on eventual emphasis:

- **SoCS** — search, heuristic algorithms, rigorous evaluations, MAPF variants.
- **ICAPS** — planning under uncertainty, algorithmic planning contribution.
- **AAMAS** — decentralized coordination, multiagent learning, communication.
- **IROS / ICRA / RA-L** — robot execution systems, robust coordination, ideally with convincing physical/realistic validation.
- **Specialized workshops** at the above venues — a focused empirical finding or early reproducible benchmark, provided submissions meet requirements.

Venue choice must follow actual contribution and maturity, not journal quartile alone. Confirm the current CFP, deadlines, formatting, page limits, anonymization, supplementary policy, dual-submission/preprint restrictions, data availability statements, and APCs directly from official websites shortly before submission.

### 13.6 Internal pre-submission review

Conduct three independent critical reviews (a human reviewer where possible; separate LLM reviewers are supplementary, not a substitute):

1. **Theory and correctness reviewer:** Any unsupported guarantee, ambiguous timing, improper treatment of deadlock, hidden privileged information, invalid metric?
2. **Prior-art/novelty reviewer:** Is the algorithm genuinely distinguishable from PIBT, LSRP, online replanning, ADG, or communication-aware RL? What important papers are missing?
3. **Experimental reviewer:** Baseline strength, paired instances, held-out data, confidence intervals, runtime fairness, effect sizes, known failure distributions, reproducibility.

Compile a blocking-issues table (`critical`, `major`, `minor`), fix each critical/major issue or explicitly narrow claims, and perform a clean rerun if code or protocol changed.

### 13.7 Mandatory submission artifacts

- `paper.tex` and versioned `references.bib` (using an official venue template when selected).
- All figures and scripts used to create them.
- Raw experiment tables, manifests, and reproducible configs.
- Tested source repository and installation instructions.
- Experiment reproduction instructions from a clean checkout.
- Supplement describing protocol proofs/edge cases/extra results.
- Limitations and reproducibility statement.
- Anonymized repository/data release if required by the venue.

---

## 14. Definition of success: ready for a paper versus merely finished code

### 14.1 Engineering completion

The project has an event simulator, local observation model, communication model, tested safety monitor, compatible baselines, proposed method, deterministic replays, visualizations, and reproducible result pipeline. All important tests pass or blocked cases are explicitly documented.

### 14.2 Research completion

In addition to engineering completion:

- There is a **precise, non-obvious** claim compared with the closest literature.
- Method changes can be isolated by ablations.
- Evaluations use relevant and strong baselines under matched conditions.
- Main results generalize beyond a few development maps or hand-picked seeds.
- Failures and confidence intervals are disclosed.
- Any guarantee is correctly conditional and proven, rather than assumed.
- Results support the claim **without** granting the method unfair map/communication privileges.

### 14.3 Submission readiness

In addition to research completion:

- Related work includes relevant work published before submission.
- Paper is internally reviewed and all critical objections resolved.
- Tables are reproducible by a clean experiment process.
- Code/data release is permitted and appropriately anonymized/licensed.
- Venue instructions and coauthor approvals are satisfied.

A paper **cannot** be declared publishable on the basis of this instructions file, a polished manuscript, or a positive-looking demo alone.

---

## 15. Exact instructions to an autonomous research/implementation agent

Use the following operational prompt after adding this `instructions.md` to the project root:

> You are acting as a research scientist, multi-agent planning specialist, distributed-systems engineer, and scientific software auditor. Read `instructions.md` fully, inspect the entire repository, and implement its roadmap **in dependency order**. First audit and preserve the original baselines. Then verify the closest literature and formulate an explicit, testable novelty claim. Build and validate the event-driven simulator and partial-observation/communication models before adding the new algorithm. Implement strong fair baselines and adversarial tests. Perform reproducible experiments, ablations, uncertainty reporting, and failure analyses. Start a manuscript only when the data justify a concrete contribution. Make changes directly to the repository, not just a plan. Never fabricate tests, numerical results, code execution, guarantees, citations, or publication status. Use only verified sources and mark inaccessible material as unverified. Keep a milestone-specific progress report, exact run commands and outcomes, a decision log, and a prioritized list of unresolved blockers. Do not quietly alter the experimental problem to make your method look better. If the core novelty hypothesis fails, record the negative result and recommend an evidence-based alternate research direction.

### Recommended work protocol for limited context or token budgets

At the start of each execution session:

1. Read `instructions.md` and the latest `research/decision_log.md`.
2. Identify the first uncompleted milestone and relevant files.
3. Perform a meaningful bounded chunk of implementation/testing.
4. Update test results, artifact paths, and blocker list.
5. Reassess whether the primary research question is still justified.
6. Leave the repository in a reproducible state and save an explicit handoff summary.

### Minimum first-session scope

Before writing any new MAPF algorithm, produce:

- `research/original_project_audit.md`.
- `research/problem_formulation.md` (draft assumptions, noting uncertainties).
- `research/literature/literature_matrix.csv` (at least the most relevant 10 verified publications, with gaps).
- `research/research_questions.md` with the proposed hypotheses, their falsifiers, and a baseline shortlist.
- An architecture plan and first independent tests for the event simulator.

This protects the project from investing heavily in a method that turns out to duplicate existing research or to depend on invalid simulator assumptions.

---

## 16. Final research advice

The professor's criticisms expose a real gap between textbook offline MAPF and distributed navigation, but each broad problem has already been studied. The purpose of this project is **not** to assemble the maximum possible number of features. It is to identify one important mechanism, study it rigorously, demonstrate a real advantage or new insight, and describe its limits.

The ideal final outcome is a modest, carefully defended result on **how agents should handle stale/partial information at coordination bottlenecks during asynchronous execution**—not an unjustified declaration that all of decentralized, asynchronous, unknown-map MAPF has been solved.

If the work reveals that a simpler existing algorithm is equally effective, record that clearly; the research task then becomes understanding why, identifying the boundary conditions, or designing a better, narrower problem. That is better science than adding unvalidated complexity.

---

## Appendix A — Quick verification checklist

- [ ] Existing planner inputs are not confused with training data.
- [ ] Decentralized agent code cannot inspect global ground truth.
- [ ] “Unknown map” really means hidden obstacles at decision time.
- [ ] Asynchronous time is modeled with action events, not only shuffled timestep order.
- [ ] Movement/occupancy semantics are stated and verified.
- [ ] Sensor/communication data includes generation and arrival times.
- [ ] Message loss does not silently imply resource release.
- [ ] Collisions and invalid attempted moves are independently logged.
- [ ] Safety and eventual completion are not conflated.
- [ ] Graph assumptions of PIBT and other baselines are respected.
- [ ] Full-map oracle references are clearly labeled.
- [ ] Strongest relevant baselines, not merely legacy CBS, are considered.
- [ ] Metrics report failed, timed-out, and deadlocked runs.
- [ ] A held-out map/test family is untouched during tuning.
- [ ] Ablations isolate the actual proposed mechanism.
- [ ] Communication bytes, not only counts, are measured.
- [ ] Every figure and statistic is generated from stored raw results.
- [ ] Novelty claims are supported by an updated related-work search.
- [ ] Proposed method is actually different from the closest baseline.
- [ ] Manuscript discusses limitations and negative findings.
- [ ] Code, tests, and research artifacts can be reproduced cleanly.

## Appendix B — Sources and verification status

The repository structure and original assumptions in Sections 1–2 are based on publicly visible repository documentation:

- https://github.com/AnkitGuin/Multi-Agent-Path-Finding
- https://github.com/AnkitGuin/Multi-Agent-Path-Finding/blob/main/REPORT.md

Primary literature URLs were checked against publisher/institutional records or the corresponding available preprint as of this document date. **A complete full-text systematic review and source-code audit were not performed while drafting this instructions file.** The executing research agent must inspect the source papers and implementations, validate all method details, search for additional 2025–2026 work, and update the bibliography before fixing the novelty claim.

**Document status:** Research and implementation specification. **Not evidence that the proposed novel method, experiments, or manuscript have been completed.**
