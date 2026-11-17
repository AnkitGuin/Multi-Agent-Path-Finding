"""Reproduce a bounded subset of every original suite without replacing results.

The first configured instance per suite, all configured algorithms and priority
orders, retains the original 10-second budget. Historical comparisons exclude
runtime equality and disclose invalid-plan downgrades.
"""
import hashlib
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.experiments import load_suites, run_job


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="research/reports/baseline")
    args = parser.parse_args()
    out = ROOT / args.out
    if (out / "manifest.json").exists():
        parser.error("evidence already exists; choose a new --out directory")
    out.mkdir(parents=True, exist_ok=True)
    rows, comparisons = [], []
    started = time.perf_counter()
    for suite in load_suites(str(ROOT / "config/suites.json")):
        spec = suite.instances()[0]
        jobs = [j for j in suite.jobs() if all(j[k] == v for k, v in spec.items())]
        previous = [json.loads(line) for line in
                    (ROOT / f"results/raw/{suite.name}.jsonl").read_text().splitlines()]
        for job in jobs:
            row = run_job(job)
            rows.append(row)
            old = next((r for r in previous if r["instance"] == row["instance"]
                        and r["algorithm"] == row["algorithm"]
                        and (r.get("priority_order") or "") == row["priority_order"]), None)
            comparisons.append({"suite": suite.name, "instance": row["instance"],
                                "algorithm": row["algorithm"],
                                "priority_order": row["priority_order"],
                                "historical_found": old is not None,
                                "current_status": row["status"],
                                "old_status": old.get("status") if old else None,
                                "current_soc": row["soc"],
                                "old_soc": old.get("soc") if old else None})
    (out / "subset.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    (out / "comparison.json").write_text(json.dumps(comparisons, indent=2), encoding="utf-8")
    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    inventory = [{"path": p, "bytes": (ROOT/p).stat().st_size,
                  "sha256": hashlib.sha256((ROOT/p).read_bytes()).hexdigest()}
                 for p in tracked]
    manifest = dict(schema_version=1, git_sha=subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        python=sys.version, executable=sys.executable, platform=platform.platform(),
        processor=platform.processor(), cpu_count=os.cpu_count(),
        command="python scripts/audit_original.py " + " ".join(sys.argv[1:]),
        wall_seconds=time.perf_counter()-started,
        dependencies=subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True).splitlines(),
        inventory=inventory, rows=len(rows),
        selection="first configured instance in each original suite; all algorithms/orders",
        initial_dirty_paths=["app/static/index.html", "presentation_screenshots/"],
        initial_test_attempt="system Python: No module named pytest",
        original_tests="114 collected; 111 passed, 3 failed; original_tests.xml",
        config_sha256=hashlib.sha256((ROOT/"config/suites.json").read_bytes()).hexdigest())
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"rows": len(rows), "wall_seconds": manifest["wall_seconds"],
                      "statuses": {s: sum(r["status"] == s for r in rows)
                                   for s in sorted({r["status"] for r in rows})}}))


if __name__ == "__main__":
    main()
