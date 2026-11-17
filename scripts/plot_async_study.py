"""Render descriptive study plots from stored, replay-verified tables only."""
import argparse
import csv
from pathlib import Path


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows = list(csv.DictReader((args.input/"overall.csv").open()))
    methods = [r["method"] for r in rows]
    figure, axes = plt.subplots(1, 3, figsize=(14, 5), sharey=True)
    values = [[int(r["success"])/int(r["n"]) for r in rows],
              [float(r["mean_completion"]) for r in rows],
              [float(r["mean_bytes"])/1024 for r in rows]]
    for ax, metric, title in zip(axes, values,
                                 ["Success by deadline", "Mean completed-agent fraction", "Mean sent KiB per episode"]):
        ax.barh(methods, metric, color=["#b65b53" if "claims" not in m else "#367fa6" for m in methods])
        ax.set_title(title, fontsize=11)
        ax.grid(axis="x", alpha=.2)
    axes[0].set_xlim(0, 1)
    axes[1].set_xlim(0, 1)
    figure.suptitle("Development study: all outcomes retained (210 episodes per controller)")
    figure.text(.5, .025, "Descriptive mixture of seven families and three fault settings; "
                "no held-out evaluation or novelty claim.", ha="center", fontsize=10)
    figure.tight_layout(rect=(0, .07, 1, .93))
    args.out.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.out/"development_tradeoffs.png", dpi=160)
    plt.close(figure)
    conditions = list(csv.DictReader((args.input/"all_episode_conditions.csv").open()))
    figure, axes = plt.subplots(1, 3, figsize=(14, 5), sharey=True)
    families = sorted({r["family"] for r in conditions})
    for ax, fault in zip(axes, ["reliable", "delayed", "lossy"]):
        for method in ["local_independent", "observed_yield", "claims_periodic", "claims_selective"]:
            values = [float(next(r for r in conditions if r["family"] == family
                                 and r["fault"] == fault and r["method"] == method)["success_rate"])
                      for family in families]
            ax.plot(families, values, marker="o", label=method)
        ax.tick_params(axis="x", rotation=45)
        ax.set_ylim(-.04, 1.04)
        ax.set_title(fault)
        ax.grid(alpha=.2)
    axes[0].set_ylabel("Success fraction (10 seeds per condition)")
    axes[-1].legend(fontsize=8)
    figure.suptitle("Failure regions by family and fault setting (development only)")
    figure.tight_layout()
    figure.savefig(args.out/"development_failure_regions.png", dpi=160)
    plt.close(figure)
    print("rendered two development figures from stored tables")


if __name__ == "__main__":
    main()
