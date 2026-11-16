"""Derive audit counts and split-overlap evidence from committed inputs."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.experiments import load_suites


def main():
    identity = ("seed", "width", "height", "structure", "obstacle_density",
                "distribution", "num_agents")
    pools = {s.name: {tuple(spec[k] for k in identity) for spec in s.instances()}
             for s in load_suites(str(ROOT/"config/suites.json"))}
    overlap = {name: len(pool & pools["adaptive_holdout"])
               for name, pool in pools.items() if name != "adaptive_holdout"}
    union = set().union(*(p for name, p in pools.items() if name != "adaptive_holdout"))
    result = {"schema_version": 1, "adaptive_instances": len(pools["adaptive_holdout"]),
              "adaptive_overlap_by_suite": overlap,
              "adaptive_overlap_union": len(union & pools["adaptive_holdout"]),
              "identity_columns": identity,
              "holdout_spec_sha256": hashlib.sha256((ROOT/"config/async_final_holdout.json").read_bytes()).hexdigest()}
    for name in ("baseline", "repaired_baseline"):
        rows = [json.loads(l) for l in (ROOT/f"research/reports/{name}/subset.jsonl").read_text().splitlines()]
        result[name] = {"rows": len(rows), "statuses": dict(Counter(r["status"] for r in rows))}
    comparisons = json.loads((ROOT/"research/reports/repaired_baseline/comparison.json").read_text())
    result["repaired_historical_status_soc_matches"] = sum(
        r["historical_found"] and r["current_status"] == r["old_status"]
        and r["current_soc"] == r["old_soc"] for r in comparisons)
    for name in ("original_tests", "repaired_legacy_tests", "final_tests"):
        path = ROOT/f"research/reports/{name}.xml"
        if path.exists():
            suites = list(ET.parse(path).getroot().iter("testsuite"))
            result[name] = {key: sum(float(s.attrib.get(key, 0)) for s in suites)
                            for key in ("tests", "failures", "errors", "skipped", "time")}
    (ROOT/"research/reports/audit_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
