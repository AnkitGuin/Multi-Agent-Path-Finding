#!/usr/bin/env python3
"""Regenerate every report figure and summary table from the raw results."""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from visualization.plots import FIGURE_DIR, make_all_plots  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=FIGURE_DIR)
    args = parser.parse_args()
    make_all_plots(args.out)


if __name__ == "__main__":
    main()
