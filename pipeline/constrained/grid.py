"""The cell grids the posterior head is trained over, and the mapping from a position to a cell.

TWO RESOLUTIONS, for one reason. The frozen head is 25 cells of 1 m, which quantises position along
a 5 m path to a five-step staircase: the radio cannot express anything finer than a metre along the
line however good the sensing is. A 100-cell head of 0.5 m halves that. Whether the finer head
actually resolves position better, or just spreads the same evidence over four times the classes, is
the question stage 2 answers, and it is asked because the first requirement of this batch is that
along-path position comes from the CSI rather than from a walking-pace prior.

The 25-cell mapping is the project's own and is reproduced exactly: cell index
``(row - 1) * 5 + (col - 1)`` with centres at half-metre offsets, so anything built here stays
comparable with every number on record.
"""

from __future__ import annotations

import numpy as np

ROOM_M = 5.0


def grid_n(n_cells: int) -> int:
    n = int(round(np.sqrt(n_cells)))
    if n * n != n_cells:
        raise ValueError(f"n_cells must be a perfect square, got {n_cells}")
    return n


def centres(n_cells: int) -> np.ndarray:
    """Cell centres, ``(n_cells, 2)``, ordered so that index = row * n + col."""
    n = grid_n(n_cells)
    step = ROOM_M / n
    xs = (np.arange(n) + 0.5) * step
    gx, gy = np.meshgrid(xs, xs, indexing="xy")
    return np.stack([gx.ravel(), gy.ravel()], axis=1)


def cell_index(xy: np.ndarray, n_cells: int) -> np.ndarray:
    """The cell each position falls in. Clipped to the room, so an edge coordinate never escapes."""
    n = grid_n(n_cells)
    step = ROOM_M / n
    ij = np.clip(np.floor(np.asarray(xy, dtype=float) / step).astype(int), 0, n - 1)
    return ij[:, 1] * n + ij[:, 0]


def quantisation_floor(n_cells: int, n: int = 200000, seed: int = 0) -> float:
    """Mean distance from a uniform point in the room to the nearest cell centre.

    The floor a cell-state emission cannot go below however good the sensing is: 0.38 m at 25 cells,
    0.19 m at 100. Quoted beside any along-path number so resolution is never mistaken for accuracy.
    """
    rng = np.random.default_rng(seed)
    pts = rng.uniform(0, ROOM_M, size=(n, 2))
    c = centres(n_cells)
    d = np.linalg.norm(pts[:, None, :] - c[None, :, :], axis=2).min(1)
    return float(d.mean())
