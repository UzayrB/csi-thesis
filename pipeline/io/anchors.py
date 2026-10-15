"""Walking-path and grid-cell definitions for ground-truth capture.

COORDINATE FRAME
----------------
Positions are ``(col, row)`` with col 1-5 left to right and row 1-5 bottom to
top, so ``(1, 1)`` is the bottom-left cell. A cell centre in metres is
``x = col - 0.5``, ``y = row - 0.5``, and the grid spans 0.0 to 5.0 m on both
axes.

ANCHORS
-------
An anchor is a point on the grid boundary, or on an internal taped line, that
a walking path crosses. Every path has exactly six: an entry anchor, four
internal ones, and an exit anchor. The operator presses a key as the
participant's torso crosses each, which is what ties wall-clock time to
position.

Paths start outside the grid and end outside it so the participant is already
walking at a steady pace when they cross the first anchor, and does not begin
decelerating before the last. The diagonal paths use offsets of 1.06 and 0.71
per axis because 1.5 m and 1.0 m along a 45-degree diagonal are 1.5/sqrt(2)
and 1.0/sqrt(2) per axis.

Nothing in this module performs I/O or depends on hardware.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Sequence

#: Number of anchors on every path: entry, four internal, exit.
N_ANCHORS: int = 6

#: Extent of the grid in metres, on both axes.
GRID_MIN: float = 0.0
GRID_MAX: float = 5.0

#: Number of cells per side, so 25 cells in total.
GRID_CELLS: int = 5

#: Expected anchor spacing on the axis-aligned paths (A, B, E), in metres.
SPACING_AXIS: float = 1.0

#: Expected anchor spacing on the diagonal paths (C, D), in metres.
SPACING_DIAGONAL: float = math.sqrt(2.0)

#: Coloured cups on the floor at the midpoint of each wall, outside the grid.
#: They are used ONLY by the static sweep, where the participant is told
#: which cup to face. Walking paths are described geometrically instead,
#: because the operator reads those aloud and grid coordinates are on the
#: tape where a colour is not.
#:
#: RED is north on the compass-needle convention and the rest run clockwise.
#: If the cups are laid out differently, change this dict rather than
#: anything else: every facing instruction is generated from it.
CAN_COLOURS: dict[str, str] = {
    "N": "RED",
    "E": "GREEN",
    "S": "BLUE",
    "W": "YELLOW",
}

#: The four facings a participant can be asked to hold during a dwell.
FACINGS: tuple[str, ...] = ("N", "E", "S", "W")


def facing_cue(direction: str) -> str:
    """Render a facing as the instruction the operator says aloud.

    Args:
        direction: One of N, E, S, W.

    Returns:
        e.g. ``"face the RED cup"``.
    """
    return f"face the {CAN_COLOURS[direction]} cup"


def build_facing_order(seed: int, n: int = GRID_CELLS * GRID_CELLS) -> tuple[str, ...]:
    """Assign a facing to each cell of the sweep.

    Args:
        seed: Seed for the shuffle, recorded in the sidecar.
        n: Number of cells.

    Returns:
        One facing per cell, in visit order.

    Constraints:
        Balanced before shuffling, so each facing appears within one of
        ``n / 4`` times. Pure random assignment over 25 cells could easily
        give one facing three times and another ten, leaving the rarer
        orientations too thin to learn from or to control for.

        Shuffled rather than cycled, because a repeating N, E, S, W pattern
        would make facing a function of visit index, and visit index is
        already correlated with time. A model could then read orientation
        off drift rather than off the body.

        Facing is randomised at all because a human is not radially
        symmetric: which way they point changes the reflection independently
        of where they stand. Left uncontrolled it is a confound; randomised
        and recorded it is a variable that can be held out or ablated.
    """
    base = [FACINGS[i % len(FACINGS)] for i in range(n)]
    random.Random(seed).shuffle(base)
    return tuple(base)


@dataclass(frozen=True)
class PathDef:
    """One walking path across the grid.

    Attributes:
        name: Path identifier, e.g. ``"A_fwd"``. Written into every record.
        direction: Compass code for the direction of travel, one of N, S, E,
            W, NE, NW, SE, SW.
        cue: Short human-readable direction cue, shown to the operator during
            a live session so the participant can be pointed the right way.
        start_xy: Where the participant begins, outside the grid, so they are
            at a steady pace before the first anchor.
        end_xy: Where the participant stops, outside the grid, so they do not
            decelerate before the last anchor.
        anchors: Exactly :data:`N_ANCHORS` ``(x, y)`` points in metres, in the
            order they are crossed.
    """

    name: str
    direction: str
    cue: str
    start_xy: tuple[float, float]
    end_xy: tuple[float, float]
    anchors: tuple[tuple[float, float], ...]

    @property
    def is_diagonal(self) -> bool:
        """Whether this path runs diagonally, and so has sqrt(2) m spacing."""
        return self.direction in ("NE", "NW", "SE", "SW")

    def segment_lengths(self) -> tuple[float, ...]:
        """Return the distance in metres between consecutive anchors."""
        return tuple(
            math.dist(self.anchors[i], self.anchors[i + 1]) for i in range(len(self.anchors) - 1)
        )


@dataclass(frozen=True)
class Cell:
    """One grid cell, used by the static sweep.

    Attributes:
        col: Column 1-5, left to right.
        row: Row 1-5, bottom to top.
        cell_id: Stable identifier in the same ``(col,row)`` form used on
            the rig diagram and spoken aloud during a session, e.g.
            ``"(3,2)"``. One notation everywhere: the operator says it, the
            screen shows it and the sidecar records it.
        centre_xy: Cell centre in metres, ``(col - 0.5, row - 0.5)``.
    """

    col: int
    row: int
    cell_id: str
    centre_xy: tuple[float, float]


@dataclass(frozen=True)
class SessionPlan:
    """A shuffled walking-path order together with the seed that produced it.

    The seed is carried alongside the order rather than being returned
    separately, because an order whose seed was not recorded cannot be
    reproduced, and the sidecar is required to record it.

    Attributes:
        seed: Seed passed to the shuffle.
        paths: The 20 passes in the order they should be walked.
    """

    seed: int
    paths: tuple[PathDef, ...]

    def __len__(self) -> int:
        return len(self.paths)

    def __iter__(self):
        return iter(self.paths)

    def __getitem__(self, i):
        return self.paths[i]


@dataclass(frozen=True)
class CellOrder:
    """A shuffled cell order together with the seed that produced it.

    Attributes:
        seed: Seed passed to the shuffle.
        cells: All 25 cells, each appearing exactly once.
    """

    seed: int
    cells: tuple[Cell, ...]

    def __len__(self) -> int:
        return len(self.cells)

    def __iter__(self):
        return iter(self.cells)

    def __getitem__(self, i):
        return self.cells[i]


def _line(start: float, stop: float, fixed: float, axis: str) -> tuple[tuple[float, float], ...]:
    """Build six evenly spaced anchors along one axis.

    Args:
        start: First coordinate along the varying axis.
        stop: Last coordinate along the varying axis.
        fixed: Coordinate held constant on the other axis.
        axis: ``"x"`` if the varying axis is x, ``"y"`` if it is y.

    Returns:
        Six ``(x, y)`` anchor points.
    """
    step = (stop - start) / (N_ANCHORS - 1)
    vals = [start + step * i for i in range(N_ANCHORS)]
    if axis == "x":
        return tuple((v, fixed) for v in vals)
    return tuple((fixed, v) for v in vals)


_A_ANCHORS = _line(0.0, 5.0, 2.5, "y")
_B_ANCHORS = _line(0.0, 5.0, 2.5, "x")
_C_ANCHORS = tuple((float(i), float(i)) for i in range(6))
_D_ANCHORS = tuple((float(i), float(5 - i)) for i in range(6))
_E_COL1_ANCHORS = _line(0.0, 5.0, 0.5, "y")
_E_COL5_ANCHORS = _line(0.0, 5.0, 4.5, "y")
_E_ROW1_ANCHORS = _line(0.0, 5.0, 0.5, "x")
_E_ROW5_ANCHORS = _line(0.0, 5.0, 4.5, "x")


#: Every defined path, keyed by name.
PATHS: dict[str, PathDef] = {
    p.name: p
    for p in (
        PathDef(
            name="A_fwd",
            direction="N",
            cue="centre column, row 1 -> row 5",
            start_xy=(2.5, -1.5),
            end_xy=(2.5, 6.0),
            anchors=_A_ANCHORS,
        ),
        PathDef(
            name="A_rev",
            direction="S",
            cue="centre column, row 5 -> row 1",
            start_xy=(2.5, 6.5),
            end_xy=(2.5, -1.0),
            anchors=tuple(reversed(_A_ANCHORS)),
        ),
        PathDef(
            name="B_fwd",
            direction="E",
            cue="centre row, col 1 -> col 5",
            start_xy=(-1.5, 2.5),
            end_xy=(6.0, 2.5),
            anchors=_B_ANCHORS,
        ),
        PathDef(
            name="B_rev",
            direction="W",
            cue="centre row, col 5 -> col 1",
            start_xy=(6.5, 2.5),
            end_xy=(-1.0, 2.5),
            anchors=tuple(reversed(_B_ANCHORS)),
        ),
        PathDef(
            name="C_fwd",
            direction="NE",
            cue="diagonal, corner (1,1) -> corner (5,5)",
            start_xy=(-1.06, -1.06),
            end_xy=(5.71, 5.71),
            anchors=_C_ANCHORS,
        ),
        PathDef(
            name="C_rev",
            direction="SW",
            cue="diagonal, corner (5,5) -> corner (1,1)",
            start_xy=(6.06, 6.06),
            end_xy=(-0.71, -0.71),
            anchors=tuple(reversed(_C_ANCHORS)),
        ),
        PathDef(
            name="D_fwd",
            direction="SE",
            cue="diagonal, corner (1,5) -> corner (5,1)",
            start_xy=(-1.06, 6.06),
            end_xy=(5.71, -0.71),
            anchors=_D_ANCHORS,
        ),
        PathDef(
            name="D_rev",
            direction="NW",
            cue="diagonal, corner (5,1) -> corner (1,5)",
            start_xy=(6.06, -1.06),
            end_xy=(-0.71, 5.71),
            anchors=tuple(reversed(_D_ANCHORS)),
        ),
        PathDef(
            name="E_col1",
            direction="N",
            cue="far-left column 1, row 1 -> row 5",
            start_xy=(0.5, -1.5),
            end_xy=(0.5, 6.0),
            anchors=_E_COL1_ANCHORS,
        ),
        PathDef(
            name="E_col5",
            direction="N",
            cue="far-right column 5, row 1 -> row 5",
            start_xy=(4.5, -1.5),
            end_xy=(4.5, 6.0),
            anchors=_E_COL5_ANCHORS,
        ),
        PathDef(
            name="E_row1",
            direction="E",
            cue="near row 1, col 1 -> col 5",
            start_xy=(-1.5, 0.5),
            end_xy=(6.0, 0.5),
            anchors=_E_ROW1_ANCHORS,
        ),
        PathDef(
            name="E_row5",
            direction="E",
            cue="far row 5, col 1 -> col 5",
            start_xy=(-1.5, 4.5),
            end_xy=(6.0, 4.5),
            anchors=_E_ROW5_ANCHORS,
        ),
    )
}

#: The 20 passes that make up one walking session, before shuffling. The
#: doubled paths give two repeats of every direction on the main axes and
#: diagonals; the E paths run once each, in one direction only, and exist to
#: cover the grid edges that the centre and diagonal paths never touch.
SESSION_COMPOSITION: tuple[str, ...] = (
    "A_fwd", "A_fwd", "A_rev", "A_rev",
    "B_fwd", "B_fwd", "B_rev", "B_rev",
    "C_fwd", "C_fwd", "C_rev", "C_rev",
    "D_fwd", "D_fwd", "D_rev", "D_rev",
    "E_col1", "E_col5", "E_row1", "E_row5",
)


def all_cells() -> tuple[Cell, ...]:
    """Return all 25 grid cells in a fixed row-major order.

    Returns:
        Every cell exactly once, ordered by row then column. This is the
        canonical order, not a walking order: see :func:`build_cell_order`.
    """
    return tuple(
        Cell(col=c, row=r, cell_id=f"({c},{r})", centre_xy=(c - 0.5, r - 0.5))
        for r in range(1, GRID_CELLS + 1)
        for c in range(1, GRID_CELLS + 1)
    )


def build_session(seed: int) -> SessionPlan:
    """Build one session's shuffled walking order.

    Args:
        seed: Seed for the shuffle. Recorded in the result and required in
            the sidecar so the order can be reproduced.

    Returns:
        A :class:`SessionPlan` holding the 20 passes and the seed used.

    Constraints:
        The same seed always yields the same order. The composition is fixed
        at 20 passes; only the order varies.
    """
    paths = [PATHS[name] for name in SESSION_COMPOSITION]
    random.Random(seed).shuffle(paths)
    return SessionPlan(seed=seed, paths=tuple(paths))


def build_cell_order(seed: int) -> CellOrder:
    """Build one session's shuffled static-sweep cell order.

    Args:
        seed: Seed for the shuffle, recorded in the result.

    Returns:
        A :class:`CellOrder` holding all 25 cells and the seed used.

    Constraints:
        The order is shuffled, never a fixed sweep. Visiting cells in a fixed
        raster makes cell position correlate with elapsed time, so any slow
        drift in the channel, thermal or otherwise, becomes a usable position
        cue and the model can score well without learning anything about the
        person. Shuffling breaks that correlation.

        The same seed always yields the same order.
    """
    cells = list(all_cells())
    random.Random(seed).shuffle(cells)
    return CellOrder(seed=seed, cells=tuple(cells))


def self_test() -> None:
    """Check the path definitions for internal consistency.

    Raises:
        AssertionError: If any path is malformed. Checks that every path has
            exactly six anchors, that anchor spacing is 1.0 m on the
            axis-aligned paths and sqrt(2) m on the diagonals, that each
            ``_rev`` path's anchors are exactly its ``_fwd`` counterpart
            reversed, and that a cell order contains all 25 cells once.
    """
    for name, p in PATHS.items():
        assert len(p.anchors) == N_ANCHORS, f"{name}: {len(p.anchors)} anchors, expected {N_ANCHORS}"
        expected = SPACING_DIAGONAL if p.is_diagonal else SPACING_AXIS
        for i, d in enumerate(p.segment_lengths()):
            assert abs(d - expected) < 1e-3, f"{name}: segment {i} is {d:.4f} m, expected {expected:.4f}"
        for x, y in p.anchors:
            assert GRID_MIN - 1e-9 <= x <= GRID_MAX + 1e-9, f"{name}: anchor x={x} outside grid"
            assert GRID_MIN - 1e-9 <= y <= GRID_MAX + 1e-9, f"{name}: anchor y={y} outside grid"

    for base in ("A", "B", "C", "D"):
        fwd = PATHS[f"{base}_fwd"].anchors
        rev = PATHS[f"{base}_rev"].anchors
        assert rev == tuple(reversed(fwd)), f"{base}_rev anchors are not {base}_fwd reversed"

    assert len(SESSION_COMPOSITION) == 20, "a session must be 20 passes"

    order = build_cell_order(0)
    assert len(order.cells) == GRID_CELLS * GRID_CELLS
    assert len({c.cell_id for c in order.cells}) == GRID_CELLS * GRID_CELLS, "cell order has duplicates"

    for c in all_cells():
        assert c.centre_xy == (c.col - 0.5, c.row - 0.5)


def describe() -> str:
    """Return a readable summary of every path, for the operator's reference."""
    lines = [f"{'path':<8} {'dir':<3} {'start':<16} {'end':<16} anchors"]
    for name in PATHS:
        p = PATHS[name]
        a = " ".join(f"({x:g},{y:g})" for x, y in p.anchors)
        lines.append(f"{p.name:<8} {p.direction:<3} {str(p.start_xy):<16} {str(p.end_xy):<16} {a}")
    return "\n".join(lines)


if __name__ == "__main__":
    self_test()
    print(describe())
    print("\nself-test passed")
