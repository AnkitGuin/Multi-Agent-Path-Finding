"""Plot observer/local maps and action/network timelines from verified replay.

These figures describe scripted simulator validation, not method performance.
No planner is run and no measurements are manually transcribed.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.replay_async import verify_replay


def render(row, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    verify_replay(row)
    grid = row["scenario"]["grid"]
    width, height = grid["width"], grid["height"]
    truth = [[1] * width for _ in range(height)]
    local = [[0] * width for _ in range(height)]
    for x, y in grid["obstacles"]:
        truth[y][x] = 2
    for event in row["events"]:
        if event["kind"] == "DECIDE" and event["payload"]["ego_id"] == 0:
            for fact in event["payload"]["visible_cells"]:
                x, y = fact["cell"]
                local[y][x] = 1 if fact["state"] == "free" else 2
    figure, axes = plt.subplots(2, 2, figsize=(11, 6),
                                gridspec_kw={"height_ratios": [1, 1.2]})
    cmap = ListedColormap(["#b8c3d1", "#f5f7fb", "#26384a"])
    for ax, values, title in [(axes[0, 0], truth, "Observer truth (privileged)"),
                               (axes[0, 1], local, "Agent 0: direct sensor memory")]:
        ax.imshow(values, cmap=cmap, vmin=0, vmax=2, interpolation="nearest")
        for i, (start, goal) in enumerate(zip(row["scenario"]["starts"], row["scenario"]["goals"])):
            if title.startswith("Agent") and i != 0:
                continue
            ax.text(*start, str(i), ha="center", va="center", color="#1b66ae", weight="bold")
            ax.plot(*goal, marker="x", color="#b24b20", markersize=10)
        ax.set_title(title, fontsize=11)
        ax.set_xticks(range(width))
        ax.set_yticks(range(height))
        ax.set_aspect("equal")
    action_ax, net_ax = axes[1]
    for event in row["events"]:
        if event["kind"] != "ACTION_START":
            continue
        a = event["action"]
        start, end = a["start_time"], min(a["end_time"], row["elapsed_time"])
        if start >= end:
            continue
        move = a["source"] != a["target"]
        action_ax.barh(a["agent_id"], end-start, left=start, height=.5,
                       color="#3686b6" if move else "#c5ced6", edgecolor="white")
    for c in row["collisions"]:
        action_ax.axvspan(c["start"], c["end"], color="#d04444", alpha=.2)
    action_ax.set_title("Actual actions: blue move, gray wait, red conflict", fontsize=10)
    action_ax.set_yticks(range(row["agent_count"]))
    action_ax.set_ylabel("Agent")
    action_ax.set_xlim(0, max(1, row["elapsed_time"]))
    action_ax.set_xlabel("Simulation seconds")
    for entry in row["network_trace"]:
        if entry["event"] not in ("sent", "lost", "delivered"):
            continue
        m = entry["message"]
        t = m["deliver_time"] if entry["event"] == "delivered" else m["send_time"]
        marker, color = {"sent": ("o", "#3686b6"), "lost": ("x", "#d04444"),
                         "delivered": ("+", "#268768")}[entry["event"]]
        net_ax.scatter(t, m["sender"], marker=marker, color=color, s=40)
    net_ax.set_yticks(range(row["agent_count"]))
    net_ax.set_xlim(0, max(1, row["elapsed_time"]))
    net_ax.set_xlabel("Simulation seconds")
    net_ax.set_ylabel("Sender")
    net_ax.set_title("Packets: blue sent, red lost, green delivered", fontsize=10)
    figure.suptitle(f"{row['scenario']['name']} | {row['termination_reason']} | "
                   f"completion {row['completed_agents']}/{row['agent_count']} | "
                   f"conflicts {row['collision_count']} | bytes sent {row['bytes_sent']}", fontsize=12)
    figure.text(.5, .01, "Scripted validation fixture; not an algorithm comparison. "
                "Unknown=gray, free=white, blocked=dark; X=goal.", ha="center", fontsize=9)
    figure.tight_layout(rect=(0, .04, 1, .94))
    figure.savefig(path, dpi=150)
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT/"results/async/validation_final")
    parser.add_argument("--out", type=Path, default=ROOT/"results/async/figures")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((args.input/"manifest.json").read_text())
    for case in manifest["cases"]:
        row = json.loads((args.input/case["file"]).read_text())
        render(row, args.out/f"{case['case']}.png")
    print(f"rendered {len(manifest['cases'])} verified validation figures")


if __name__ == "__main__":
    main()
