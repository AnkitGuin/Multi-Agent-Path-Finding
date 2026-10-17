"""Reproducible experiment pipeline.

Design rules that keep the study honest:

* **One row per (instance, planner) run**, written to CSV as soon as it is
  produced, so a crash never loses data and results can be regenerated.
* **Every run is re-validated** by :func:`evaluation.metrics.check_planner_result`
  using code that is independent of the planner.
* **Failures are data**: timeouts, PP failures and CBS exhaustions are recorded
  with their status, never dropped and never retried until they succeed.
* **Resumable**: re-running a suite skips (instance, algorithm) pairs that are
  already in the raw CSV, so a suite can be extended instead of restarted.
* **Deterministic**: an instance is fully determined by its configuration + seed.

The pipeline is deliberately plain (a list of dicts -> pandas DataFrame later);
all analysis lives in :mod:`evaluation.statistics`.
"""

from __future__ import annotations

import csv
import json
import os
import platform
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from environment.generators import generate_scenario, instance_features
from environment.grid import Scenario
from evaluation.metrics import check_planner_result, result_record, sum_of_individual_costs
from planning import solve
from planning.common import PlannerResult

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
RAW_DIR = os.path.join(RESULTS_DIR, "raw")


# --------------------------------------------------------------------------- #
#  Configuration
# --------------------------------------------------------------------------- #
@dataclass
class SuiteConfig:
    """A grid of experimental conditions (the cross-product is the suite)."""

    name: str
    algorithms: List[str]
    seeds: List[int] = field(default_factory=lambda: list(range(10)))
    agent_counts: List[int] = field(default_factory=lambda: [10, 20])
    densities: List[float] = field(default_factory=lambda: [0.2])
    structures: List[str] = field(default_factory=lambda: ["random"])
    distributions: List[str] = field(default_factory=lambda: ["uniform"])
    sizes: List[Tuple[int, int]] = field(default_factory=lambda: [(32, 32)])
    priority_orders: List[str] = field(default_factory=lambda: ["index"])
    time_limit: float = 10.0
    description: str = ""

    def instances(self) -> List[Dict[str, Any]]:
        """All (configuration, seed) instances of this suite."""
        out = []
        for seed in self.seeds:
            for size in self.sizes:
                for structure in self.structures:
                    for density in self.densities:
                        for distribution in self.distributions:
                            for agents in self.agent_counts:
                                out.append(
                                    {
                                        "suite": self.name,
                                        "seed": seed,
                                        "width": size[0],
                                        "height": size[1],
                                        "structure": structure,
                                        "obstacle_density": density,
                                        "distribution": distribution,
                                        "num_agents": agents,
                                        "time_limit": self.time_limit,
                                    }
                                )
        return out

    def jobs(self) -> List[Dict[str, Any]]:
        """All (instance, planner) jobs: instances x algorithms x priority orders."""
        jobs = []
        for spec in self.instances():
            for algorithm in self.algorithms:
                orders = self.priority_orders if algorithm == "Prioritized" else [None]
                for order in orders:
                    job = dict(spec)
                    job["algorithm"] = algorithm
                    job["priority_order"] = order
                    jobs.append(job)
        return jobs

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_suites(path: str) -> List[SuiteConfig]:
    """Load suite definitions from a JSON configuration file."""
    with open(path, encoding="utf-8") as handle:
        raw = json.load(handle)
    suites = []
    for entry in raw.get("suites", []):
        entry = dict(entry)
        entry["seeds"] = list(range(entry.pop("num_seeds", 10)))
        entry["sizes"] = [tuple(s) for s in entry.pop("sizes", [(32, 32)])]
        suites.append(SuiteConfig(**entry))
    return suites


# --------------------------------------------------------------------------- #
#  Running one job
# --------------------------------------------------------------------------- #
def build_instance(spec: Dict[str, Any]) -> Scenario:
    """Instantiate the scenario described by ``spec`` (deterministic in seed)."""
    return generate_scenario(
        width=spec["width"],
        height=spec["height"],
        num_agents=spec["num_agents"],
        obstacle_density=spec["obstacle_density"],
        structure=spec["structure"],
        distribution=spec["distribution"],
        seed=spec["seed"],
    )


def run_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """Run one (instance, planner) job and return one flat result row."""
    scenario = build_instance(job)
    algorithm = job["algorithm"]
    time_limit = job.get("time_limit") or 10.0

    kwargs: Dict[str, Any] = {"time_limit": time_limit}
    if algorithm.startswith("Prioritized") and job.get("priority_order"):
        kwargs["order"] = job["priority_order"]
        kwargs["rng"] = random.Random(job["seed"])

    # Sum of individual costs (SIC): computed once per instance, outside the
    # planner timing, and used as the optimality reference for every algorithm.
    sic = sum_of_individual_costs(scenario.grid, scenario.starts, scenario.goals)

    # "How much coordination does this instance need?" -- measured once with the
    # naive baseline (outside the planner timing) and attached to every row so
    # that results can be analysed as a function of instance difficulty.
    if algorithm == "Independent":
        baseline = None
    else:
        baseline = solve(scenario, "Independent", time_limit=time_limit)
    initial_conflicts = (
        baseline.conflicts_final if baseline is not None else None
    )

    result: PlannerResult = solve(scenario, algorithm, **kwargs)
    if initial_conflicts is not None:
        result.conflicts_initial = initial_conflicts
    result = check_planner_result(scenario, result)

    row = result_record(scenario, result, sic=sic)
    row.update(instance_features(scenario))
    row.update(
        {
            "suite": job.get("suite", "default"),
            "structure": job["structure"],
            "distribution": job["distribution"],
            "obstacle_density_requested": job["obstacle_density"],
            "priority_order": job.get("priority_order") or "",
            "time_limit": time_limit,
        }
    )
    return row


# --------------------------------------------------------------------------- #
#  Running a suite
# --------------------------------------------------------------------------- #
def _job_key(row: Dict[str, Any]) -> Tuple:
    return (
        row.get("suite"),
        row.get("instance"),
        row.get("algorithm"),
        row.get("priority_order"),
    )


def raw_jsonl_path(csv_path: str) -> str:
    return os.path.splitext(csv_path)[0] + ".jsonl"


def append_row(jsonl_path: str, row: Dict[str, Any]) -> None:
    """Append one result row immediately (crash- and interrupt-safe)."""
    with open(jsonl_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, default=str) + "\n")


def load_existing(path: str) -> List[Dict[str, Any]]:
    """Read results: prefer the append-only JSONL, fall back to an older CSV."""
    jsonl = raw_jsonl_path(path)
    if os.path.exists(jsonl):
        rows = []
        with open(jsonl, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def run_suite(
    suite: SuiteConfig,
    output: Optional[str] = None,
    workers: int = 1,
    resume: bool = True,
    progress_every: int = 25,
) -> List[Dict[str, Any]]:
    """Run every job of ``suite``, appending rows to ``output`` as they finish."""
    os.makedirs(RAW_DIR, exist_ok=True)
    output = output or os.path.join(RAW_DIR, f"{suite.name}.csv")
    existing = load_existing(output) if resume else []
    done = {_job_key(row) for row in existing}
    jobs = [job for job in suite.jobs() if _job_key(_preview_row(job)) not in done]

    rows: List[Dict[str, Any]] = list(existing)
    new_rows: List[Dict[str, Any]] = []
    jsonl_path = raw_jsonl_path(output)
    if not jobs:
        print(f"[{suite.name}] {len(existing)} rows already present, nothing to do")
        _write_csv(output, existing)
        return rows

    print(
        f"[{suite.name}] {len(jobs)} new jobs "
        f"({len(suite.instances())} instances x {len(suite.algorithms)} algorithms), "
        f"workers={workers}, time_limit={suite.time_limit}s"
    )
    started = time.time()
    completed = 0
    try:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(run_job, job): job for job in jobs}
            for future in as_completed(futures):
                try:
                    row = future.result()
                except Exception as exc:  # record, never swallow silently
                    job = futures[future]
                    row = {
                        "suite": job.get("suite"),
                        "instance": f"seed{job['seed']}-a{job['num_agents']}",
                        "algorithm": job["algorithm"],
                        "success": 0,
                        "status": "error",
                        "details": repr(exc),
                    }
                    row.update(job)
                new_rows.append(row)
                append_row(jsonl_path, row)
                completed += 1
                if completed % progress_every == 0:
                    elapsed = time.time() - started
                    print(
                        f"    {completed}/{len(jobs)} ({elapsed:.0f}s elapsed, "
                        f"~{elapsed / completed * (len(jobs) - completed):.0f}s left)",
                        flush=True,
                    )
    except KeyboardInterrupt:
        print(f"[{suite.name}] interrupted; {completed} rows already on disk", flush=True)

    _write_csv(output, new_rows + existing)
    print(
        f"[{suite.name}] wrote {len(new_rows)} new rows -> {output} "
        f"in {time.time() - started:.0f}s"
    )
    return new_rows + existing


def _write_csv(path: str, rows: Sequence[Dict[str, Any]]) -> None:
    """Materialise a CSV view of the raw rows (JSONL stays the source of truth)."""
    if not rows:
        return
    fieldnames = sorted({key for row in rows for key in row})
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _preview_row(job: Dict[str, Any]) -> Dict[str, Any]:
    """The identity of a job as it will appear in a result row."""
    name = (
        f"{job['structure']}-{job['width']}x{job['height']}"
        f"-d{int(round(job['obstacle_density'] * 100)):02d}"
        f"-a{job['num_agents']}-{job['distribution']}-s{job['seed']}"
    )
    return {
        "suite": job.get("suite"),
        "instance": name,
        "algorithm": job["algorithm"],
        "priority_order": job.get("priority_order") if job["algorithm"].startswith("Prioritized") else "",
    }


def environment_info() -> Dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def write_manifest(path: str, suites: Sequence[SuiteConfig], extra: Optional[Dict] = None) -> None:
    """Record exactly what was run, for reproducibility."""
    payload = {
        "environment": environment_info(),
        "suites": [s.to_dict() for s in suites],
    }
    if extra:
        payload.update(extra)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
