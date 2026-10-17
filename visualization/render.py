"""Static rendering of grids, paths and conflicts (matplotlib).

The interactive demo (``app/``) animates plans in the browser; this module
produces the *figures for the report*: publication-style snapshots that show,
for the same instance, what each coordination strategy actually does.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Sequence

import matplotlib

matplotlib.use("Agg")  # headless: figures are written to files, never displayed

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import colors  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from environment.grid import Cell, GridMap, Scenario  # noqa: E402

OBSTACLE_COLOR = "#2b2b3c"
FREE_COLOR = "#fbfbfd"
GRID_COLOR = "#d7d9e0"
START_COLOR = "#2a9d8f"
GOAL_COLOR = "#e76f51"

FIGURE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "figures"
)


def _grid_image(grid: GridMap) -> np.ndarray:
    image = np.zeros((grid.height, grid.width), dtype=float)
    for x, y in grid.obstacles:
        image[y, x] = 1.0
    return image


def render_scenario(
    ax: plt.Axes,
    grid: GridMap,
    starts: Sequence[Cell] = (),
    goals: Sequence[Cell] = (),
    paths: Optional[Sequence[Sequence[Cell]]] = None,
    conflicts: Optional[Sequence[Cell]] = None,
    title: str = "",
    show_labels: bool = False,
) -> None:
    """Draw one grid situation on ``ax``."""
    ax.imshow(
        _grid_image(grid),
        cmap=colors.ListedColormap([FREE_COLOR, OBSTACLE_COLOR]),
        vmin=0,
        vmax=1,
        interpolation="nearest",
        origin="upper",
    )
    ax.set_xticks(np.arange(-0.5, grid.width, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, grid.height, 1), minor=True)
    ax.grid(which="minor", color=GRID_COLOR, linewidth=0.3)
    ax.tick_params(
        which="both", bottom=False, left=False, labelbottom=False, labelleft=False
    )

    if paths:
        cmap = plt.get_cmap("tab10")
        for i, path in enumerate(paths):
            xs = [c[0] for c in path]
            ys = [c[1] for c in path]
            color = cmap(i % 10)
            ax.plot(xs, ys, "-", color=color, linewidth=1.6, alpha=0.85, zorder=2)
            ax.scatter(xs[0], ys[0], s=34, facecolor="white", edgecolor=color, zorder=3)
            ax.scatter(xs[-1], ys[-1], s=34, marker="s", color=color, zorder=3)
            if show_labels:
                ax.text(xs[0], ys[0], str(i), ha="center", va="center", fontsize=6)
    else:
        for cell in starts:
            ax.add_patch(
                Rectangle(
                    (cell[0] - 0.5, cell[1] - 0.5), 1, 1, fill=False,
                    edgecolor=START_COLOR, linewidth=1.4,
                )
            )
        for cell in goals:
            ax.scatter(
                cell[0], cell[1], marker="x", s=40, color=GOAL_COLOR, linewidths=1.6
            )

    for cell in conflicts or []:
        ax.scatter(cell[0], cell[1], marker="*", s=180, color="#e63946", zorder=5)

    if title:
        ax.set_title(title, fontsize=10)


def render_plan(
    scenario: Scenario,
    paths: Optional[Sequence[Sequence[Cell]]] = None,
    conflicts: Optional[Sequence[Cell]] = None,
    title: str = "",
    out: Optional[str] = None,
) -> plt.Figure:
    """Single-panel figure of one instance (optionally with its solution)."""
    fig, ax = plt.subplots(figsize=(6, 6))
    render_scenario(
        ax,
        scenario.grid,
        scenario.starts,
        scenario.goals,
        paths=paths,
        conflicts=conflicts,
        title=title,
    )
    fig.tight_layout()
    if out:
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        fig.savefig(out, dpi=150)
        plt.close(fig)
    return fig


def render_algorithm_comparison(
    scenario: Scenario,
    results: Dict[str, List[List[Cell]]],
    stats: Optional[Dict[str, str]] = None,
    out: Optional[str] = None,
) -> plt.Figure:
    """One panel per algorithm, same instance -> the visual 'money figure'."""
    names = list(results)
    fig, axes = plt.subplots(1, len(names), figsize=(5 * len(names), 5.2))
    axes = np.atleast_1d(axes)
    for ax, name in zip(axes, names):
        caption = stats.get(name, "") if stats else ""
        render_scenario(
            ax,
            scenario.grid,
            scenario.starts,
            scenario.goals,
            paths=results[name],
            title=f"{name}\n{caption}",
        )
    fig.suptitle(scenario.summary(), fontsize=11)
    fig.tight_layout()
    if out:
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        fig.savefig(out, dpi=150)
        plt.close(fig)
    return fig


def conflict_cells(paths: Sequence[Sequence[Cell]]) -> List[Cell]:
    """Cells where a vertex conflict occurs (for highlighting)."""
    from planning.collisions import detect_conflicts

    return [c.cell1 for c in detect_conflicts(paths) if c.kind == "vertex"]
