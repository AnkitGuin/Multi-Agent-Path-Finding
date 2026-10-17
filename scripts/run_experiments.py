#!/usr/bin/env python3
"""Run the experiment suites defined in ``config/suites.json``.

    python scripts/run_experiments.py                 # everything, resuming
    python scripts/run_experiments.py --suites scalability density
    python scripts/run_experiments.py --workers 2 --fresh

Raw per-run rows are written to ``results/raw/<suite>.csv``.
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from evaluation.experiments import RAW_DIR, load_suites, run_suite, write_manifest  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=os.path.join(ROOT, "config", "suites.json"))
    parser.add_argument("--suites", nargs="*", default=None, help="subset of suite names")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--fresh", action="store_true", help="ignore existing raw results")
    parser.add_argument("--progress-every", type=int, default=25)
    args = parser.parse_args()

    suites = load_suites(args.config)
    if args.suites:
        wanted = set(args.suites)
        suites = [s for s in suites if s.name in wanted]
        missing = wanted - {s.name for s in suites}
        if missing:
            parser.error(f"unknown suite(s): {sorted(missing)}")

    os.makedirs(RAW_DIR, exist_ok=True)
    write_manifest(os.path.join(RAW_DIR, "manifest.json"), suites)
    for suite in suites:
        run_suite(
            suite,
            workers=args.workers,
            resume=not args.fresh,
            progress_every=args.progress_every,
        )


if __name__ == "__main__":
    main()
