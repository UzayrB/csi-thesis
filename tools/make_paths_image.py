"""Draw the walking-path sheet the operator reads during the walking blocks.

One panel per path, generated from :data:`pipeline.io.anchors.PATHS` and the
node positions in :mod:`tools.make_layout_image`, so the sheet cannot drift
out of step with the coordinates the session actually prompts.

Each panel shows:

* a GREEN dot where the participant is stood before the pass: 1.5 m outside
  the tape, so they are at steady walking pace before the first press. A
  RED dot where they walk out to, 1.0 m beyond the last line, so they do not
  slow down before the sixth press. Starting or stopping closer than that is
  the most common way to ruin a pass.
* the six black anchors, which are the six SPACE presses, on the torso.
* the four nodes as grey pots. On paths A and B the walk runs straight
  through a pot at each end; start BESIDE it, one pot-width off the line,
  and walk straight at the first tape line. Never start in front of it.

Regenerate with::

    python tools/make_paths_image.py

Output: Paths.png at the repo root, opened by
:mod:`pipeline.io.ground_truth` at the start of a session.
"""

from __future__ import annotations

import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle

from pipeline.io.anchors import PATHS
from tools.make_layout_image import NODE_XY

START_HEX = "#1a9e4b"
END_HEX = "#cc2b2b"
POT_HEX = "#c8c8c8"

#: Panel grid. Twelve paths, four across.
N_COLS = 4

#: A node closer than this to the run-in or run-out is "on" the walk.
ON_LINE_M = 0.35


def _dist_to_segment(p, a, b) -> float:
    """Distance from point ``p`` to the segment ``a``-``b``."""
    ax_, ay_ = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax_, by - ay_
    if dx == 0 and dy == 0:
        return math.hypot(px - ax_, py - ay_)
    t = max(0.0, min(1.0, ((px - ax_) * dx + (py - ay_) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax_ + t * dx), py - (ay_ + t * dy))


def _panel(ax, path) -> None:
    """Draw one path onto one axes."""
    for i in range(6):
        ax.plot([i, i], [0, 5], color="#d8d8d8", lw=0.8, zorder=0)
        ax.plot([0, 5], [i, i], color="#d8d8d8", lw=0.8, zorder=0)
    ax.plot([0, 5, 5, 0, 0], [0, 0, 5, 5, 0], color="black", lw=1.8, zorder=1)

    sx, sy = path.start_xy
    ex, ey = path.end_xy
    a0x, a0y = path.anchors[0]
    a5x, a5y = path.anchors[-1]

    # The pots, faded, so the walker can see which ones the line runs through.
    run_in, run_out = ((sx, sy), (a0x, a0y)), ((a5x, a5y), (ex, ey))
    for name, (nx, ny) in NODE_XY.items():
        on_walk = min(_dist_to_segment((nx, ny), *run_in), _dist_to_segment((nx, ny), *run_out)) < ON_LINE_M
        ax.add_patch(Circle((nx, ny), 0.26, facecolor=POT_HEX, edgecolor="#333" if on_walk else "#999",
                            lw=1.6 if on_walk else 0.9, zorder=2 if on_walk else 1))
        ax.text(nx, ny, name, ha="center", va="center", fontsize=6.6, fontweight="bold", color="#222", zorder=3)

    # Unrecorded run-in and run-out.
    ax.plot([sx, a0x], [sy, a0y], color="#555", lw=1.4, ls=(0, (4, 3)), zorder=2)
    ax.plot([a5x, ex], [a5y, ey], color="#555", lw=1.4, ls=(0, (4, 3)), zorder=2)

    # The 1.5 m run-in, dimensioned, so it is read as a distance, not a suggestion.
    mx, my = (sx + a0x) / 2, (sy + a0y) / 2
    dx, dy = a0x - sx, a0y - sy
    n = math.hypot(dx, dy) or 1.0
    px, py = -dy / n, dx / n
    # Read along the run-in, never upside down; beside a vertical run-in
    # the text lies flat so it does not fight the dashed line.
    rot = math.degrees(math.atan2(dy, dx))
    if rot > 90:
        rot -= 180
    elif rot <= -90:
        rot += 180
    if abs(rot) > 80:
        rot = 0.0
    ax.text(mx + 0.7 * px, my + 0.7 * py, "1.5 m", ha="center", va="center", fontsize=8.5,
            fontweight="bold", color="#1a9e4b", rotation=rot, zorder=5)

    # The recorded span, and the six presses.
    xs = [p[0] for p in path.anchors]
    ys = [p[1] for p in path.anchors]
    ax.plot(xs, ys, color="black", lw=2.4, zorder=3)
    ax.plot(xs, ys, "o", color="black", ms=6.5, zorder=4)

    # Direction, drawn mid-path so it never sits under a dot.
    mid = len(path.anchors) // 2
    ax.annotate(
        "",
        xy=(xs[mid], ys[mid]),
        xytext=(xs[mid - 1], ys[mid - 1]),
        arrowprops=dict(arrowstyle="-|>", color="black", lw=2.4, mutation_scale=22),
        zorder=5,
    )

    ax.plot([sx], [sy], "o", color=START_HEX, ms=15, markeredgecolor="black", markeredgewidth=1.4, zorder=6)
    ax.plot([ex], [ey], "o", color=END_HEX, ms=15, markeredgecolor="black", markeredgewidth=1.4, zorder=6)

    ax.set_title(path.name, fontsize=14, fontweight="bold", pad=4)
    ax.text(
        0.5, -0.045,
        f"{path.cue}\nstart ({sx:g}, {sy:g})   end ({ex:g}, {ey:g})",
        transform=ax.transAxes, ha="center", va="top", fontsize=8.8, color="#333",
    )
    ax.set_xlim(-2.1, 7.1)
    ax.set_ylim(-2.1, 7.1)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ax.spines.values():
        side.set_visible(False)


def draw(out_path: str) -> str:
    """Render every path and write the sheet to ``out_path``."""
    names = list(PATHS)
    rows = (len(names) + N_COLS - 1) // N_COLS
    fig, axes = plt.subplots(rows, N_COLS, figsize=(4.0 * N_COLS, 5.15 * rows))
    flat = axes.ravel()

    for ax, name in zip(flat, names):
        _panel(ax, PATHS[name])
    for ax in flat[len(names) :]:
        ax.axis("off")

    fig.suptitle(
        "Walking paths — START 1.5 m OUTSIDE the tape, walk straight through, out the far side",
        fontsize=18,
        fontweight="bold",
        y=0.983,
    )

    handles = [
        Line2D([], [], marker="o", ls="", color=START_HEX, markeredgecolor="black", ms=13,
               label="START — 1.5 m outside the tape, at steady pace by line 1"),
        Line2D([], [], marker="o", ls="", color=END_HEX, markeredgecolor="black", ms=13,
               label="END — 1.0 m beyond the last line, then stop"),
        Line2D([], [], marker="o", ls="-", color="black", ms=7, lw=2.4,
               label="the 6 anchors — SPACE as the TORSO crosses each"),
        Line2D([], [], marker="o", ls="", color=POT_HEX, markeredgecolor="#333", ms=11,
               label="a pot on the line — start BESIDE it, never in front of it"),
    ]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.962),
               ncol=2, frameon=False, fontsize=11.5)

    fig.text(
        0.5, 0.028,
        "There is NO start press: you call \"go\", they walk it on their own. Starting or stopping ON the grid, or closer than 1.5 m "
        "to it, is the most common way to ruin a pass.\n"
        "Paths A and B run through a pot at each end. Stand them 1.5 m back and one pot-width to the side, walking straight at "
        "the first tape line — no step, no slowing.\n"
        "A session is 20 passes: A/B/C/D forward and reverse twice each, then E_col1, E_col5, E_row1, E_row5 "
        "once each. Order is shuffled per session with a logged seed.",
        ha="center", fontsize=10.5, color="#333",
    )

    # Explicit spacing rather than tight_layout: the captions are drawn in
    # axes coordinates below each panel, which tight_layout does not account
    # for, so it packs the rows until they overlap.
    fig.subplots_adjust(left=0.015, right=0.985, top=0.905, bottom=0.105, hspace=0.34, wspace=0.02)
    fig.savefig(out_path, dpi=115, facecolor="white")
    plt.close(fig)
    return out_path


#: The report figure's printed size: the 6.27 in A4 text width minus the layout figure beside it
#: (tools/make_layout_image.draw_report, about 3.04 in) and a small gap, at the same height.
REPORT_SIZE_IN = (3.12, 3.0)


def _panel_report(ax, path) -> None:
    """One path for the thesis figure: the same drawing as :func:`_panel`, scaled to print, no caption."""
    for i in range(6):
        ax.plot([i, i], [0, 5], color="#d8d8d8", lw=0.3, zorder=0)
        ax.plot([0, 5], [i, i], color="#d8d8d8", lw=0.3, zorder=0)
    ax.plot([0, 5, 5, 0, 0], [0, 0, 5, 5, 0], color="black", lw=0.7, zorder=1)

    sx, sy = path.start_xy
    ex, ey = path.end_xy
    a0x, a0y = path.anchors[0]
    a5x, a5y = path.anchors[-1]

    # The receivers as grey pots and the transmitter in black, as on the layout figure; unlabelled at
    # this size (the layout figure beside this one names them).
    run_in, run_out = ((sx, sy), (a0x, a0y)), ((a5x, a5y), (ex, ey))
    for name, (nx, ny) in NODE_XY.items():
        on_walk = min(_dist_to_segment((nx, ny), *run_in), _dist_to_segment((nx, ny), *run_out)) < ON_LINE_M
        tx = name == "TX"
        ax.add_patch(Circle((nx, ny), 0.3, facecolor="black" if tx else POT_HEX,
                            edgecolor="black" if tx else ("#333" if on_walk else "#999"),
                            lw=0.6 if on_walk else 0.35, zorder=2 if on_walk else 1))

    ax.plot([sx, a0x], [sy, a0y], color="#555", lw=0.55, ls=(0, (3, 2)), zorder=2)
    ax.plot([a5x, ex], [a5y, ey], color="#555", lw=0.55, ls=(0, (3, 2)), zorder=2)

    # No "1.5 m" label here: at print size it is wider than the run-in it names; the caption states it.

    xs = [p[0] for p in path.anchors]
    ys = [p[1] for p in path.anchors]
    ax.plot(xs, ys, color="black", lw=0.9, zorder=3)
    ax.plot(xs, ys, "o", color="black", ms=2.2, zorder=4)
    # The direction, with its head between two presses so it never sits on a dot.
    mid = len(path.anchors) // 2
    (x0, y0), (x1, y1) = (xs[mid - 1], ys[mid - 1]), (xs[mid], ys[mid])
    ax.annotate("", xy=(x0 + 0.82 * (x1 - x0), y0 + 0.82 * (y1 - y0)), xytext=(x0 + 0.18 * (x1 - x0), y0 + 0.18 * (y1 - y0)),
                arrowprops=dict(arrowstyle="-|>,head_length=0.75,head_width=0.6", color="black", lw=0.9, mutation_scale=4.2,
                                shrinkA=0, shrinkB=0), zorder=5)

    ax.plot([sx], [sy], "o", color=START_HEX, ms=4.6, markeredgecolor="black", markeredgewidth=0.5, zorder=6)
    ax.plot([ex], [ey], "o", color=END_HEX, ms=4.6, markeredgecolor="black", markeredgewidth=0.5, zorder=6)

    ax.set_title(path.name, fontsize=6.5, fontweight="bold", pad=1.5)
    ax.set_xlim(-1.85, 6.85)
    ax.set_ylim(-1.85, 6.85)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ax.spines.values():
        side.set_visible(False)


def draw_report(out_path: str) -> str:
    """The twelve paths for the thesis, at their printed size: a legend, no title and no captions.

    The operator sheet (:func:`draw`) is unchanged, because the capture opens it at every session.
    """
    names = list(PATHS)
    rows = (len(names) + N_COLS - 1) // N_COLS
    fig, axes = plt.subplots(rows, N_COLS, figsize=REPORT_SIZE_IN)
    for ax, name in zip(axes.ravel(), names):
        _panel_report(ax, PATHS[name])
    handles = [
        Line2D([], [], marker="o", ls="", color=START_HEX, markeredgecolor="black", markeredgewidth=0.5, ms=4.6,
               label="start, 1.5 m before the tape"),
        Line2D([], [], marker="o", ls="", color=END_HEX, markeredgecolor="black", markeredgewidth=0.5, ms=4.6,
               label="end, 1.0 m past the tape"),
        Line2D([], [], marker="o", ls="-", color="black", ms=2.2, lw=0.9, label="key presses (six)"),
        Line2D([], [], marker=">", ls="", color="black", ms=3.4, label="walking direction"),
        Line2D([], [], marker="o", ls="", color=POT_HEX, markeredgecolor="#999", markeredgewidth=0.35, ms=4.2,
               label="receiver"),
        Line2D([], [], marker="o", ls="", color="black", ms=4.2, label="transmitter"),
    ]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=3, frameon=False,
               fontsize=5.4, handlelength=1.6, handletextpad=0.4, columnspacing=0.9, labelspacing=0.3)
    fig.subplots_adjust(left=0.0, right=1.0, top=0.885, bottom=0.0, hspace=0.12, wspace=0.0)
    fig.savefig(out_path, dpi=400, facecolor="white", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return out_path


if __name__ == "__main__":
    import sys

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if "--report" in sys.argv:
        print(draw_report(os.path.join(root, "reports", "project", "figures", "2026-10-05_paths-report.png")))
    else:
        print(draw(os.path.join(root, "Paths.png")))
