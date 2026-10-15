"""Draw the rig layout for DC2 (Room B): every cell labelled, the four nodes, RX2's two places, the seat.

The one sheet that answers both "where does everything physically go" and
"which square is (3,2)". Generated from the same coordinates the session
records in its sidecar (``--rx-positions``, and ``capture_idpath``'s seat and
RX2 spot), so the diagram and the recordings cannot drift apart.

Updated 2026-09-24 for DC2: the operator seat is (-1.0, 0.5), fixed for all of
DC2; RX2 is drawn at home (-0.5, 2.5) facing east, where it is for tracking, and
at its identification spot (2.0, -0.5) facing north, where it moves for the
identification walks (the primary spot, confirmed in the room by Uzayr). There is
no grid sweep at DC2, so the facing cups are gone. The Room A sheet is in git.

THE FRAME
---------
``(0, 0)`` is the BOTTOM-LEFT CORNER OF THE TAPED GRID, not a wall. ``x``
runs right along the columns, ``y`` runs up the rows, both spanning 0-5 m,
and the tape lines fall on whole metres. Cell ``(col, row)`` has its centre
at ``(col - 0.5, row - 0.5)``: cell labels and metre positions are two
different numberings of the same floor.

Regenerate with::

    python -m tools.make_layout_image

Output: Layout.png at the repo root.
"""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrow, Rectangle

from pipeline.identify.capture_idpath import SEAT, SPOTS

#: TRUE node positions in grid metres, exactly as passed to ``--rx-positions``
#: and ``--tx-position``. Each sits at a wall midpoint, on the centre line of
#: its side, 0.5 m outside the tape. RX2 here is its HOME, for tracking.
#: (tools/make_paths_image.py reads this table too.)
NODE_XY = {"RX1": (2.5, 5.5), "RX2": (-0.5, 2.5), "RX3": (5.5, 2.5), "TX": (2.5, -0.5)}

#: RX2's identification spot: the primary spot, confirmed in the room.
RX2_ID_XY = SPOTS["primary"]

#: Where each label sits, its text, and which way its leader runs.
LABELS = {
    "RX1": ((4.35, 5.95), "RX1\n(2.5, 5.5)"),
    "RX3": ((6.3, 3.65), "RX3\n(5.5, 2.5)"),
    "TX": ((4.05, -1.15), "TX\n(2.5, -0.5)"),
    "RX2": ((-2.15, 3.55), "RX2 · TRACKING\n(-0.5, 2.5), faces east"),
    "RX2_ID": ((0.35, -1.55), "RX2 · IDENTIFICATION\n(2.0, -0.5), faces north"),
}

#: The operator seat: fixed for all of DC2, identification and tracking. The
#: researcher and the laptop are part of the static multipath, so this is a
#: fixed, recorded position, in every baseline too.
SEAT_XY = SEAT


def draw(out_path: str) -> str:
    """Render the layout and write it to ``out_path``."""
    fig, ax = plt.subplots(figsize=(16.0, 15.0))

    # Every cell, labelled with its id and its centre in metres.
    for col in range(1, 6):
        for row in range(1, 6):
            ax.add_patch(Rectangle((col - 1, row - 1), 1, 1, facecolor="white", edgecolor="#999", lw=1.1))
            cx, cy = col - 0.5, row - 0.5
            ax.text(cx, cy + 0.14, f"({col},{row})", ha="center", va="center", fontsize=24, fontweight="bold")
            ax.text(cx, cy - 0.24, f"{cx:g}, {cy:g} m", ha="center", va="center", fontsize=12, color="#666")
    ax.add_patch(Rectangle((0, 0), 5, 5, fill=False, edgecolor="black", lw=3.2, zorder=2))

    # Metre ticks: x along the TOP edge (the bottom edge holds TX and RX2's identification spot), y on the left.
    for m in range(6):
        ax.text(m, 5.18, f"{m}", ha="center", va="bottom", fontsize=13, color="#555")
        ax.text(-0.18, m, f"{m}", ha="right", va="center", fontsize=13, color="#555")
    ax.text(1.0, 5.72, "x  →  metres", ha="center", va="bottom", fontsize=14, fontweight="bold", color="#333")
    ax.text(-0.72, 4.35, "y  ↑  metres", ha="center", va="center", fontsize=14, fontweight="bold",
            color="#333", rotation=90)
    ax.plot([0], [0], marker="o", ms=13, color="#c0392b", zorder=6)
    ax.text(0.12, -0.12, "(0,0)", ha="left", va="top", fontsize=15, fontweight="bold", color="#c0392b")

    # Nodes, drawn where they actually are, names led outward.
    nodes = {**NODE_XY, "RX2_ID": RX2_ID_XY}
    for name, (x, y) in nodes.items():
        (lx, ly), text = LABELS[name]
        ax.plot([x, lx], [y, ly], color="#555", lw=1.4, ls=(0, (3, 2)), zorder=4)
        rx2 = name.startswith("RX2")
        ax.add_patch(Circle((x, y), 0.19, facecolor="black" if name == "TX" else ("#f6d9a8" if rx2 else "white"),
                            edgecolor="black", lw=2.6, zorder=6))
        ax.text(lx, ly, text, ha="center", va="center", fontsize=15, fontweight="bold", zorder=7,
                bbox=dict(boxstyle="round,pad=0.35", facecolor="#fdf0db" if rx2 else "white",
                          edgecolor="black", lw=1.8))
    # Which way RX2 faces in each place.
    hx, hy = NODE_XY["RX2"]
    ax.add_patch(FancyArrow(hx + 0.2, hy, 0.26, 0.0, width=0.05, head_width=0.2, head_length=0.14,
                            length_includes_head=True, color="#b9770e", zorder=7))
    ix, iy = RX2_ID_XY
    ax.add_patch(FancyArrow(ix, iy + 0.2, 0.0, 0.26, width=0.05, head_width=0.2, head_length=0.14,
                            length_includes_head=True, color="#b9770e", zorder=7))
    # The seat.
    sx, sy = SEAT_XY
    ax.add_patch(Rectangle((sx - 0.42, sy - 0.3), 0.84, 0.6, facecolor="white",
                           edgecolor="black", lw=1.5, ls=(0, (4, 3)), zorder=5))
    ax.text(sx, sy, "me", ha="center", va="center", fontsize=15, fontweight="bold", zorder=6)
    ax.text(sx - 0.55, sy, "operator seat\n(-1.0, 0.5)\nlaptop + hub", ha="right", va="center",
            fontsize=12, color="#333")

    ax.set_title(
        "Rig layout — Room B, DC2 (26 and 27 September)\n"
        "1 TX + 3 RX · 5.0 × 5.0 m taped grid · 25 cells of 1 m · RX2 in two places",
        fontsize=20, fontweight="bold", pad=22,
    )
    ax.text(
        2.5, -2.75,
        "(0,0) is the BOTTOM-LEFT CORNER OF THE TAPE, not a wall.  x runs right, y runs up, both 0–5 m.  "
        "Cell (col,row) centre = (col − 0.5, row − 0.5).\n"
        "Nodes sit at the wall midpoints, 0.5 m outside the tape, at the same height as Room A.  "
        "Tape RX2's outline and arrow in both places.\n"
        "RX2 is at home for tracking, moves to its identification spot for the identification walks, "
        "and goes home again.  You and the laptop stay at the seat, in every baseline.",
        ha="center", va="center", fontsize=13, color="#333",
    )

    ax.set_xlim(-3.55, 8.55)
    ax.set_ylim(-3.35, 6.55)
    ax.set_aspect("equal")
    ax.axis("off")
    # Explicit margins: tight_layout under-allocates for a title above an
    # axes whose spines are hidden, and clips it.
    fig.subplots_adjust(left=0.01, right=0.99, top=0.915, bottom=0.01)
    fig.savefig(out_path, dpi=200, facecolor="white")
    plt.close(fig)
    return out_path


#: The report figure's printed height, shared with tools/make_paths_image.py so
#: the two sit side by side at one height across the 6.27 in A4 text width.
REPORT_HEIGHT_IN = 3.1


def draw_report(out_path: str) -> str:
    """The layout for the thesis, drawn at its printed size: no title, no caption, real axis arrows.

    Narrower than the operator sheet (labels stacked above and below rather than out to the sides),
    so that the walking-path panels beside it can be wider. The operator sheet (:func:`draw`) is
    unchanged, because the capture opens it.
    """
    fig, ax = plt.subplots(figsize=(3.0, REPORT_HEIGHT_IN))

    for col in range(1, 6):
        for row in range(1, 6):
            ax.add_patch(Rectangle((col - 1, row - 1), 1, 1, facecolor="white", edgecolor="#999", lw=0.5))
            cx, cy = col - 0.5, row - 0.5
            ax.text(cx, cy + 0.13, f"({col},{row})", ha="center", va="center", fontsize=6.8, fontweight="bold")
            ax.text(cx, cy - 0.22, f"{cx:g}, {cy:g}", ha="center", va="center", fontsize=4.6, color="#666")
    ax.add_patch(Rectangle((0, 0), 5, 5, fill=False, edgecolor="black", lw=1.3, zorder=2))

    # Metre ticks on the bottom and left edges, and both axes as real arrows from the origin. The two
    # zero ticks mark the origin, so it carries a red dot and no separate label.
    for m in range(6):
        ax.text(m, -0.07, f"{m}", ha="center", va="top", fontsize=5.5, color="#555")
        ax.text(-0.09, m, f"{m}", ha="right", va="center", fontsize=5.5, color="#555")
    arrow = dict(arrowstyle="-|>", color="#333", lw=0.9, mutation_scale=7)
    ax.annotate("", xy=(0.9, -0.45), xytext=(0.0, -0.45), arrowprops=arrow)
    ax.text(0.45, -0.58, "x (m)", ha="center", va="top", fontsize=6, fontweight="bold", color="#333")
    ax.annotate("", xy=(-0.48, 1.25), xytext=(-0.48, 0.0), arrowprops=arrow)
    ax.text(-0.48, 1.33, "y (m)", ha="center", va="bottom", fontsize=6, fontweight="bold", color="#333")
    ax.plot([0], [0], marker="o", ms=4, color="#c0392b", zorder=6)

    # Nodes where they are; labels stacked compactly so nothing reaches far out to the sides.
    labels = {
        "RX1": ((4.05, 5.95), "RX1 (2.5, 5.5)"),
        "RX3": ((5.62, 3.55), "RX3\n(5.5, 2.5)"),
        "TX": ((3.95, -1.05), "TX\n(2.5, -0.5)"),
        "RX2": ((-1.12, 3.85), "RX2, tracking\n(-0.5, 2.5)\nfaces east"),
        "RX2_ID": ((1.05, -1.25), "RX2, identification\n(2.0, -0.5), faces north"),
    }
    nodes = {**NODE_XY, "RX2_ID": RX2_ID_XY}
    for name, (x, y) in nodes.items():
        (lx, ly), text = labels[name]
        ax.plot([x, lx], [y, ly], color="#555", lw=0.6, ls=(0, (3, 2)), zorder=4)
        rx2 = name.startswith("RX2")
        ax.add_patch(Circle((x, y), 0.17, facecolor="black" if name == "TX" else ("#f6d9a8" if rx2 else "white"),
                            edgecolor="black", lw=1.0, zorder=6))
        ax.text(lx, ly, text, ha="center", va="center", fontsize=5.5, fontweight="bold", zorder=7,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="#fdf0db" if rx2 else "white",
                          edgecolor="black", lw=0.7))
    hx, hy = NODE_XY["RX2"]
    ax.add_patch(FancyArrow(hx + 0.17, hy, 0.25, 0.0, width=0.04, head_width=0.16, head_length=0.11,
                            length_includes_head=True, color="#b9770e", zorder=7))
    # Beside the identification spot rather than above it, where the x = 2 tick now sits.
    ix, iy = RX2_ID_XY
    ax.add_patch(FancyArrow(ix - 0.3, iy - 0.13, 0.0, 0.26, width=0.04, head_width=0.16, head_length=0.11,
                            length_includes_head=True, color="#b9770e", zorder=7))

    # The operator's seat, drawn small so it stays clear of the y arrow.
    sx, sy = SEAT_XY
    ax.add_patch(Rectangle((sx - 0.3, sy - 0.25), 0.6, 0.5, facecolor="white",
                           edgecolor="black", lw=0.7, ls=(0, (3, 2)), zorder=5))
    ax.text(sx, sy, "seat", ha="center", va="center", fontsize=5.5, fontweight="bold", zorder=6)
    ax.text(sx, sy - 0.33, "operator\n(-1.0, 0.5)", ha="center", va="top", fontsize=4.8, color="#333")

    ax.set_xlim(-1.95, 6.25)
    ax.set_ylim(-1.75, 6.25)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    fig.savefig(out_path, dpi=400, facecolor="white", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return out_path


if __name__ == "__main__":
    import sys

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if "--report" in sys.argv:
        print(draw_report(os.path.join(root, "reports", "project", "figures", "2026-10-05_layout-report.png")))
    else:
        print(draw(os.path.join(root, "Layout.png")))
