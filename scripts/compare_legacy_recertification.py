"""Compare the full repaired rerun with preserved historical rows."""
from collections import Counter
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def key(row):
    return row["instance"], row["algorithm"], row.get("priority_order") or ""


def main():
    directory = ROOT/"results/recertified_2026_11_17"
    comparisons, statuses = [], Counter()
    for path in sorted(directory.glob("*.jsonl")):
        old = {key(r): r for r in (json.loads(line) for line in (ROOT/"results/raw"/path.name).read_text().splitlines())}
        current = [json.loads(line) for line in path.read_text().splitlines()]
        assert len(old) == len(current), "historical/rerun denominators differ"
        for r in current:
            previous = old[key(r)]
            statuses[(previous["status"], r["status"])] += 1
            comparisons.append(dict(suite=path.stem, instance=r["instance"], algorithm=r["algorithm"],
                                    priority_order=r.get("priority_order") or "", old_status=previous["status"],
                                    new_status=r["status"], old_soc=previous["soc"], new_soc=r["soc"],
                                    same_status_soc=(previous["status"], previous["soc"]) == (r["status"], r["soc"])))
    with (directory/"historical_comparison.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, list(comparisons[0]))
        writer.writeheader()
        writer.writerows(comparisons)
    result = dict(rows=len(comparisons), exact_status_soc_matches=sum(r["same_status_soc"] for r in comparisons),
                  status_transitions={f"{a}->{b}": count for (a, b), count in sorted(statuses.items())},
                  invalid_runs=sum(r["new_status"] == "invalid" for r in comparisons),
                  caution="10-second timeouts depend on host load; asynchronous study overlapped the final legacy suite. Cost differences are success-conditioned; no universal ranking.")
    (directory/"comparison_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
