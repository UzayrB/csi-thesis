# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Walking-path and grid-cell definitions for ground-truth capture.

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Sequence

N_ANCHORS: int = 6

GRID_MIN: float = 0.0
GRID_MAX: float = 5.0

GRID_CELLS: int = 5

SPACING_AXIS: float = 1.0

SPACING_DIAGONAL: float = math.sqrt(2.0)

CAN_COLOURS: dict[str, str] = {
    "N": "RED",
    "E": "GREEN",
    "S": "BLUE",
    "W": "YELLOW",
}

FACINGS: tuple[str, ...] = ("N", "E", "S", "W")


# Render a facing as the instruction the operator says aloud.
def facing_cue(direction: str) -> str:
    return f"face the {CAN_COLOURS[direction]} cup"


# Assign a facing to each cell of the sweep.
def build_facing_order(seed: int, n: int = GRID_CELLS * GRID_CELLS) -> tuple[str, ...]:
    base = [FACINGS[i % len(FACINGS)] for i in range(n)]
    random.Random(seed).shuffle(base)
    return tuple(base)


# One walking path across the grid.
@dataclass(frozen=True)
class PathDef:

    name: str
    direction: str
    cue: str
    start_xy: tuple[float, float]
    end_xy: tuple[float, float]
    anchors: tuple[tuple[float, float], ...]

    # Whether this path runs diagonally, and so has sqrt(2) m spacing.
    @property
    def is_diagonal(self) -> bool:
        return self.direction in ("NE", "NW", "SE", "SW")

    # Return the distance in metres between consecutive anchors.
    def segment_lengths(self) -> tuple[float, ...]:
        return tuple(
            math.dist(self.anchors[i], self.anchors[i + 1]) for i in range(len(self.anchors) - 1)
        )


# One grid cell, used by the static sweep.
@dataclass(frozen=True)
class Cell:

    col: int
    row: int
    cell_id: str
    centre_xy: tuple[float, float]


# A shuffled walking-path order together with the seed that produced it.
@dataclass(frozen=True)
class SessionPlan:

    seed: int
    paths: tuple[PathDef, ...]

    # The number of items.
    def __len__(self) -> int:
        return len(self.paths)

    # Iterates over the items.
    def __iter__(self):
        return iter(self.paths)

    # One item.
    def __getitem__(self, i):
        return self.paths[i]


# A shuffled cell order together with the seed that produced it.
@dataclass(frozen=True)
class CellOrder:

    seed: int
    cells: tuple[Cell, ...]

    # The number of items.
    def __len__(self) -> int:
        return len(self.cells)

    # Iterates over the items.
    def __iter__(self):
        return iter(self.cells)

    # One item.
    def __getitem__(self, i):
        return self.cells[i]


# Build six evenly spaced anchors along one axis.
def _line(start: float, stop: float, fixed: float, axis: str) -> tuple[tuple[float, float], ...]:
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

SESSION_COMPOSITION: tuple[str, ...] = (
    "A_fwd", "A_fwd", "A_rev", "A_rev",
    "B_fwd", "B_fwd", "B_rev", "B_rev",
    "C_fwd", "C_fwd", "C_rev", "C_rev",
    "D_fwd", "D_fwd", "D_rev", "D_rev",
    "E_col1", "E_col5", "E_row1", "E_row5",
)


# Return all 25 grid cells in a fixed row-major order.
def all_cells() -> tuple[Cell, ...]:
    return tuple(
        Cell(col=c, row=r, cell_id=f"({c},{r})", centre_xy=(c - 0.5, r - 0.5))
        for r in range(1, GRID_CELLS + 1)
        for c in range(1, GRID_CELLS + 1)
    )


# Build one session's shuffled walking order.
def build_session(seed: int) -> SessionPlan:
    paths = [PATHS[name] for name in SESSION_COMPOSITION]
    random.Random(seed).shuffle(paths)
    return SessionPlan(seed=seed, paths=tuple(paths))


# Build one session's shuffled static-sweep cell order.
def build_cell_order(seed: int) -> CellOrder:
    cells = list(all_cells())
    random.Random(seed).shuffle(cells)
    return CellOrder(seed=seed, cells=tuple(cells))


# Check the path definitions for internal consistency.
def self_test() -> None:
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


# Return a readable summary of every path, for the operator's reference.
def describe() -> str:
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
