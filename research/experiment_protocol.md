# Experimental protocol draft — not a final evaluation

Current executable data are six analytic simulator fixtures, not a baseline
comparison. Scripts supplied by the evaluator are explicitly `oracle_access=true`
because their paths may encode prior map information. Their purpose is checking
physics/observations/network/replay. No local algorithm improvement is measured.

Final design requirements:

- Match scenario hashes, observation radius, horizon, duration-resource semantics
  and computation budgets. Pair movement draws by agent/move index, message draws
  by directed logical-message ID; different traffic has no claim of identical
  packet-level counterfactual randomness.
- Keep failed runs. Precedence: collision, agent_error, success, timeout. Do not
  infer infeasibility/deadlock from a horizon. Include attempted invalid actions,
  censored time SOC, completion, and waits beside conflict rate. Real robot
  contact/severity is outside this abstract occupancy model.
- Before final selection, freeze resolved development/holdout JSON and hashes,
  selected licensed map files, method versions, seeds, duration distributions,
  baseline adaptations, and tuning budgets. JSON is used instead of YAML to
  keep runtime dependency-free. The current holdout reservation has unresolved
  layout/distribution choices and cannot be executed as a final study.
- Analyze completion with binomial intervals and paired differences with
  scenario/map bootstrap. Restrict solved-pair costs to a labeled secondary
  analysis; primary all-episode outcome tables retain failures. No statistics
  are warranted from a hand-selected analytic smoke set.
- Reserve minus_freshness / fixed-period communication with identical commitment
  semantics. Add topology, local-repair and delay-awareness ablations only when
  their components exist. No claims based on subtracting imaginary components.
- Record source hashes, git SHA, exact command/config, interpreter/dependency
  lock, hardware, CPU/wall timing, raw events and failure traces. Timing fields
  are excluded from deterministic equivalence. Validate saved logs before plots.

Publication remains gated on strong authentic baselines and G1/G4, not merely
tests passing. The new run_async/analyze_async benchmark commands and manuscript
are intentionally not advertised as existing deliverables.
