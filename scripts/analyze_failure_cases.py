"""Save a representative success and a failed local run with an oracle witness.

Qualitative case selection is explicit and not a success-rate benchmark. The
oracle sees the full map/paths/completions and is not information-matched.
"""
from dataclasses import asdict
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from baselines.async_dependency import execute_dependencies
from environment.grid import Scenario
from planning.cbs import solve_cbs
from simulation.episode import EpisodeConfig
from simulation.communication import NetworkConfig
from scripts.generate_research_figures import render


def load(directory, row):
    with gzip.open(directory/row["event_log_path"], "rt", encoding="utf-8") as f:
        return json.load(f)


def main():
    directory = ROOT/"results/async/development_2026_11_17"
    rows = [json.loads(line) for line in (directory/"runs.jsonl").read_text().splitlines()]
    out = directory/"failure_cases"
    out.mkdir(exist_ok=True)
    success = next(r for r in rows if r["method"] == "claims_selective" and r["termination_reason"] == "success")
    render(load(directory, success), out/"representative_success.png")
    checked, failure = [], None
    for row in rows:
        if (row["method"] != "claims_selective" or row["termination_reason"] != "timeout"
                or row["fault"] != "reliable" or row["map_family"] not in {"open", "random", "rooms"}):
            continue
        replay = load(directory, row)
        scenario = Scenario.from_dict(replay["scenario"])
        plan = solve_cbs(scenario.grid, scenario.starts, scenario.goals, time_limit=1)
        attempt = dict(run_id=row["run_id"], cbs_status=plan.status)
        checked.append(attempt)
        if not plan.success:
            continue
        physical = dict(replay["config"])
        physical["network"] = NetworkConfig(**physical["network"])
        reference = execute_dependencies(scenario, plan.paths, EpisodeConfig(**physical))
        attempt["dependency_status"] = reference["status"]
        if reference["status"] != "success":
            continue
        reference.update(local_run_id=row["run_id"], local_replay=row["event_log_path"],
                         local_completion=row["completion_fraction"], cbs_runtime=plan.runtime_sec)
        (out/"oracle_feasible_witness.json").write_text(json.dumps(reference, indent=2), encoding="utf-8")
        render(replay, out/"representative_failure.png")
        failure = reference
        break
    report = dict(success_run_id=success["run_id"], success_replay=success["event_log_path"],
                  selection="first selective success; first reliable open/random/rooms timeout with a successful centralized dependency witness",
                  checked_candidates=checked, oracle_witness_found=failure is not None,
                  interpretation="qualitative feasible-failure witness only; full-information oracle is not matched to local controls")
    (out/"selection.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
