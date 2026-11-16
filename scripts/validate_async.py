"""Save and independently replay analytic simulator smoke cases.

This command validates engineering, not an algorithmic performance claim.
"""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.replay_async import verify_replay
from simulation.episode import digest, run_episode
from simulation.fixtures import ScriptedPolicy, smoke_cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.out is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        args.out = ROOT / "results/async/validation_runs" / stamp
    args.out.mkdir(parents=True, exist_ok=True)
    if (args.out / "manifest.json").exists():
        parser.error("evidence exists; choose a fresh --out directory")
    results = []
    for scenario, scripts, config, expected in smoke_cases():
        policies = tuple(ScriptedPolicy(i, script, broadcast=True) for i, script in enumerate(scripts))
        row = run_episode(scenario, policies, config, method="scripted_validation_fixture",
                          oracle_access=True)
        assert row["termination_reason"] == expected, scenario.name
        checked = verify_replay(row)
        path = args.out / f"{scenario.name}.json"
        path.write_text(json.dumps(row, indent=2), encoding="utf-8")
        results.append(dict(case=scenario.name, expected=expected, file=path.name,
                            replay=checked, sha256=digest(row)))
    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    # New modules have not necessarily been committed yet: hash every source
    # package used, together with tracked files (never scan .venv or secrets).
    source = set(tracked)
    for package in ("agents", "simulation", "evaluation", "scripts", "tests"):
        source.update(str(p.relative_to(ROOT)).replace("\\", "/")
                      for p in (ROOT/package).rglob("*.py"))
    manifest = dict(schema_version=1, purpose="analytic validation, not benchmark evidence",
                    utc_timestamp=datetime.now(timezone.utc).isoformat(),
                    git_sha=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                    source_hashes={p: digest((ROOT/p).read_text(encoding="utf-8"))
                                   for p in sorted(source) if p.endswith(".py")},
                    python=sys.version, platform=platform.platform(), command=sys.argv,
                    dependency_lock="research/reports/requirements-lock.txt", cases=results)
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"verified_cases": len(results), "out": str(args.out)}))


if __name__ == "__main__":
    main()
