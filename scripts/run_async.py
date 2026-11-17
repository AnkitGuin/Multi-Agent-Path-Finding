"""Run a preregistered paired development study, retaining every failed run."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.runners_async import run_case
from evaluation.replay_async import verify_replay
from simulation.episode import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT/"config/async_development.json")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.config.read_text())
    if "settings" not in data or "faults" not in data:
        parser.error("unresolved/holdout reservation config cannot be executed")
    args.out.mkdir(parents=True, exist_ok=True)
    if (args.out/"manifest.json").exists():
        parser.error("choose a fresh output directory")
    (args.out/"replays").mkdir()
    source_hashes = {str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
                     for package in ("agents", "baselines", "simulation", "evaluation")
                     for p in (ROOT/package).rglob("*.py")}
    manifest = dict(schema_version=1, utc_timestamp=datetime.now(timezone.utc).isoformat(),
                    git_sha=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                    command=sys.argv, config=data, config_hash=digest(data),
                    source_hashes=source_hashes, python=sys.version, platform=platform.platform(),
                    source_lf_hashes={p: hashlib.sha256((ROOT/p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                                      for p in source_hashes},
                    final_holdout_executed=False, source_state="working tree; exact package hashes recorded")
    (args.out/"manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    jobs = list(itertools.product(data["families"], data["seeds"], data["agent_counts"], data["faults"], data["methods"]))
    start, statuses, ids = time.perf_counter(), Counter(), set()
    with (args.out/"runs.jsonl").open("w", encoding="utf-8") as output:
        for k, (family, seed, n, fault, method) in enumerate(jobs, 1):
            row = run_case(method, family, seed, n, data["size"], fault, data["settings"])
            verify_replay(row)
            if row["run_id"] in ids:
                raise ValueError("duplicate experimental run")
            ids.add(row["run_id"])
            replay = args.out/"replays"/f"{row['run_id']}.json.gz"
            with gzip.open(replay, "wt", encoding="utf-8") as handle:
                json.dump(row, handle, separators=(",", ":"))
            summary = {key: value for key, value in row.items()
                       if key not in {"events", "network_trace", "occupancy", "scenario", "config"}}
            summary.update(event_log_path=f"replays/{replay.name}", source_manifest_path="manifest.json")
            output.write(json.dumps(summary, allow_nan=False)+"\n")
            output.flush()
            statuses[row["termination_reason"]] += 1
            if k % 50 == 0 or k == len(jobs):
                print(json.dumps(dict(done=k, total=len(jobs), seconds=round(time.perf_counter()-start, 1),
                                      statuses=statuses)), flush=True)
    (args.out/"summary.json").write_text(json.dumps(dict(runs=len(ids), statuses=statuses,
                                                       wall_seconds=time.perf_counter()-start), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
