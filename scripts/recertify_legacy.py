"""Rerun every configured legacy job into a new results directory.

Historical raw results, manifests and figures are never replaced. The repaired
goal semantics are checked independently by the existing experiment harness.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.experiments import load_suites, run_suite, write_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if (args.out/"manifest.json").exists():
        parser.error("choose a fresh output directory")
    suites = load_suites(str(ROOT/"config/suites.json"))
    write_manifest(str(args.out/"manifest.json"), suites, dict(
        git_sha=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        purpose="full recertification after goal-entry correction", command=sys.argv))
    for suite in suites:
        run_suite(suite, str(args.out/f"{suite.name}.csv"), workers=args.workers,
                  resume=False, progress_every=50)
    rows = [json.loads(line) for p in args.out.glob("*.jsonl") for line in p.read_text().splitlines()]
    summary = dict(rows=len(rows), expected=sum(len(s.jobs()) for s in suites),
                   statuses={s: sum(r["status"] == s for r in rows) for s in sorted({r["status"] for r in rows})})
    (args.out/"summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
