"""Reproduce native PIBT/Causal-PIBT with independent checks and model labels."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from baselines.pibt_native import run_native
from environment.generators import generate_scenario
from environment.benchmarks import load_map


def check_causal(text, grid):
    snapshots = []
    for line in text.splitlines():
        match = re.match(r"^(\d+):(\d+):(.+)", line)
        if not match:
            continue
        states = [tuple(map(int, values)) for values in re.findall(r"\((-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+)\)", match[3])]
        if not states:
            continue
        occupied = set()
        for agent, mode, head, tail, goal in states:
            cells = {tail, head} if mode == 2 else {tail}
            assert not occupied & cells, "native resource conflict"
            occupied |= cells
            for cell in cells:
                assert grid.is_free((cell % grid.width, cell // grid.width)), "native obstacle occupancy"
            if mode == 2:
                assert abs(tail % grid.width-head % grid.width)+abs(tail//grid.width-head//grid.width) == 1
        snapshots.append(states)
    assert snapshots, "native trace missing snapshots"
    solved = "solved=1" in text.splitlines()
    if solved:
        assert all(mode == 0 and tail == goal for _, mode, head, tail, goal in snapshots[-1])
    return dict(verified=True, snapshots=len(snapshots), success=solved,
                collision_count=0, variant="KNOWN_GRAPH_ATOMIC_INTERACTIONS_NATIVE",
                assumptions="authoritative atomic interactions; known graph; vacatable goals; no packet network")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT/"results/native_2026_11_17")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if (args.out/"manifest.json").exists():
        parser.error("choose a fresh output directory")
    records = []
    for family in ("random", "rooms"):
        for seed in range(10):
            scenario = generate_scenario(16, 16, 10, .2, family, "uniform", seed=seed)
            row = run_native(scenario, seed=seed, horizon=200)
            row.update(family=family, seed=seed, scenario=scenario.to_dict())
            name = f"pibt-{family}-{seed}.json"
            (args.out/name).write_text(json.dumps(row), encoding="utf-8")
            records.append(dict(method="PIBT_native", file=name, status=row["status"],
                                goal_departures=row["goal_departures"], collision_count=row["collision_count"]))
    checkout = ROOT/"external/time-independent-planning"
    for instance in ("small-crossing_2agents", "6x6_collision_8agents", "three-bridge_collision_6agents", "sample"):
        source = checkout/f"instances/{instance}.txt"
        map_name = re.search(r"^map_file=(.+)$", source.read_text(), re.M)[1].strip()
        grid = load_map(str(checkout/"map"/map_name))
        for seed in range(5):
            name = f"causal-{instance}-{seed}.txt"
            command = [str(checkout/"app.exe"), "-i", str(source), "-o", str(args.out/name),
                       "-s", "CAUSAL_PIBT", "-r", str(seed)]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
            if result.returncode != 0 or not (args.out/name).exists():
                raise RuntimeError(f"native Causal-PIBT failed: {result.stderr} {result.stdout}")
            check = check_causal((args.out/name).read_text(), grid)
            records.append(dict(method="CausalPIBT_native", file=name, command=command,
                                map_sha256=hashlib.sha256((checkout/"map"/map_name).read_bytes()).hexdigest(),
                                instance_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), **check))
    pins = dict(pypibt="a3c97f60413c6619a29a5022969896bc54877edc",
                causal_pibt="b2e9e650a1f5446b88cd7b9394504e97435e7f38",
                causal_graph="98df17f364b8e94f927e5e1317eda4f40a2238a6")
    manifest = dict(schema_version=1, command=sys.argv, revisions=pins, records=records,
                    comparison_warning="native references have different information/goal/timing models; no pooled ranking")
    (args.out/"manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(dict(native_runs=len(records), invalid=sum(r.get("status") == "invalid" for r in records))))


if __name__ == "__main__":
    main()
