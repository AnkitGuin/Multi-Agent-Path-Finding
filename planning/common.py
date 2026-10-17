"""Shared result type and planner registry.

Keeping the result container here (rather than inside each planner) means the
evaluation layer never branches on *how* a planner failed: every planner returns
the same object with an explicit ``status``.  Failures are recorded, never
masked -- a core requirement of this project.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from environment.grid import Cell

# Planner outcomes.  Distinguishing them matters for the analysis:
#   ok           - conflict-free solution returned
#   no_solution  - planner proved/observed that it cannot return a solution
#                  (CBS: search space exhausted; PP: an agent could not be
#                  routed around earlier agents; Independent: unreachable goal)
#   timeout      - stopped because the time budget ran out (not a proof)
#   invalid      - never produced by a planner; set by the validator in the
#                  evaluation layer if a returned plan fails the checks
STATUS_OK = "ok"
STATUS_NO_SOLUTION = "no_solution"
STATUS_TIMEOUT = "timeout"
STATUS_INVALID = "invalid"
# A plan was returned but it is not conflict-free.  Expected for Independent A*
# (a deliberately naive baseline); for PP/CBS it would indicate a bug, which the
# experiment harness reports instead of hiding.
STATUS_CONFLICT = "conflict"


@dataclass
class PlannerResult:
    """Uniform outcome of a planner run."""

    algorithm: str
    success: bool
    status: str
    paths: List[List[Cell]] = field(default_factory=list)
    runtime_sec: float = 0.0
    soc: Optional[int] = None
    makespan: Optional[int] = None
    # Search effort (comparable across algorithms only with care -- see report).
    low_level_calls: int = 0
    low_level_expansions: int = 0
    high_level_expansions: int = 0
    conflicts_initial: Optional[int] = None  # conflicts of the independent solution
    conflicts_final: int = 0                 # conflicts left in the returned plan
    priority_order: Optional[List[int]] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "success": self.success,
            "status": self.status,
            "runtime_sec": self.runtime_sec,
            "soc": self.soc,
            "makespan": self.makespan,
            "low_level_calls": self.low_level_calls,
            "low_level_expansions": self.low_level_expansions,
            "high_level_expansions": self.high_level_expansions,
            "conflicts_initial": self.conflicts_initial,
            "conflicts_final": self.conflicts_final,
            "priority_order": self.priority_order,
            "details": self.details,
        }
