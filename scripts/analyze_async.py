"""All-episode tables, paired cluster bootstrap and replay verification.

Intervals are exploratory. Resampling unit is the true map; one-map conditions
have no map-generalization interval. Failed runs remain in every primary table.
"""
import argparse
from collections import defaultdict
import csv
import gzip
import json
import math
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.replay_async import verify_replay
from simulation.episode import digest


def wilson(successes, n):
    z = 1.959963984540054
    p = successes/n
    center = (p+z*z/(2*n))/(1+z*z/n)
    half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return center-half, center+half


def mean(values):
    values = list(values)
    return sum(values)/len(values) if values else None


def bootstrap_clusters(records, seed=0, draws=2000):
    clusters = defaultdict(list)
    for map_id, delta in records:
        clusters[map_id].append(delta)
    observed = mean(delta for _, delta in records)
    if len(clusters) < 2:
        return observed, None, None, len(clusters)
    rng, keys, samples = random.Random(seed), sorted(clusters), []
    for _ in range(draws):
        chosen = [rng.choice(keys) for _ in keys]
        samples.append(mean(v for k in chosen for v in clusters[k]))
    samples.sort()
    return observed, samples[int(.025*draws)], samples[min(draws-1, int(.975*draws))], len(clusters)


def save_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in (args.input/"runs.jsonl").read_text().splitlines()]
    args.out.mkdir(parents=True, exist_ok=True)
    ids, groups, indexed = set(), defaultdict(list), {}
    for row in rows:
        if row["run_id"] in ids:
            raise ValueError("duplicate run")
        ids.add(row["run_id"])
        with gzip.open(args.input/row["event_log_path"], "rt", encoding="utf-8") as handle:
            replay = json.load(handle)
        verify_replay(replay)
        for key in ("collision_count", "executed_time_soc", "bytes_sent", "termination_reason", "run_id"):
            assert row[key] == replay[key], "summary does not match replay"
        grid = replay["scenario"]["grid"]
        row["map_hash"] = digest({k: grid[k] for k in ("width", "height", "obstacles")})
        groups[(row["map_family"], row["fault"], row["method"])].append(row)
        indexed[(row["pair_id"], row["method"])] = row
    table = []
    for (family, fault, method), group in sorted(groups.items()):
        n = len(group)
        successes = sum(r["termination_reason"] == "success" for r in group)
        low, high = wilson(successes, n)
        table.append(dict(family=family, fault=fault, method=method, n=n,
                          success_count=successes, success_rate=successes/n,
                          success_wilson_low=low, success_wilson_high=high,
                          mean_completion=mean(r["completion_fraction"] for r in group),
                          collision_episodes=sum(r["collision_count"] > 0 for r in group),
                          timeouts=sum(r["termination_reason"] == "timeout" for r in group),
                          agent_errors=sum(r["termination_reason"] == "agent_error" for r in group),
                          mean_censored_time_soc=mean(r["executed_time_soc"] for r in group),
                          mean_bytes_sent=mean(r["bytes_sent"] for r in group),
                          mean_wait=mean(r["total_wait_time"] for r in group),
                          mean_replans=mean(r["replan_count"] for r in group)))
    paired = []
    controls = [("claims_selective", "claims_periodic"), ("claims_selective", "claims_always"),
                ("claims_selective", "claims_no_map"), ("claims_selective", "claims_full_replan")]
    for a, b in controls:
        for metric in ("bytes_sent", "executed_time_soc", "total_wait_time", "completion_fraction"):
            records = []
            success_discordance = 0
            for (pair, method), ra in sorted(indexed.items()):
                if method != a:
                    continue
                rb = indexed[(pair, b)]
                assert ra["config_hash"] == rb["config_hash"]
                success_discordance += (ra["termination_reason"] == "success") != (rb["termination_reason"] == "success")
                records.append((ra["map_hash"], ra[metric]-rb[metric]))
            delta, lo, hi, maps = bootstrap_clusters(records)
            paired.append(dict(method_a=a, method_b=b, metric=metric, all_episode_pairs=len(records),
                               distinct_maps=maps, mean_a_minus_b=delta, map_bootstrap_low=lo,
                               map_bootstrap_high=hi, discordant_success_pairs=success_discordance))
    save_csv(args.out/"all_episode_conditions.csv", table)
    save_csv(args.out/"paired_controls.csv", paired)
    overall = []
    for method in sorted({r["method"] for r in rows}):
        group = [r for r in rows if r["method"] == method]
        overall.append(dict(method=method, n=len(group), success=sum(r["termination_reason"] == "success" for r in group),
                            collisions=sum(r["collision_count"] > 0 for r in group),
                            mean_completion=mean(r["completion_fraction"] for r in group),
                            mean_bytes=mean(r["bytes_sent"] for r in group),
                            mean_censored_time_soc=mean(r["executed_time_soc"] for r in group)))
    save_csv(args.out/"overall.csv", overall)
    output = dict(verified_replays=len(rows), conditions=len(table), paired_controls=paired, overall=overall,
                  interpretation="development only; heterogeneous families pooled descriptively; no confirmatory novelty claim",
                  uncertainty="Wilson intervals conditional on scenarios; paired 2000-draw map-cluster bootstrap; exploratory without multiplicity correction")
    (args.out/"analysis.json").write_text(json.dumps(output, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(dict(verified=len(rows), conditions=len(table), overall=overall), indent=2))


if __name__ == "__main__":
    main()
