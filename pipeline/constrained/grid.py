# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The cell grids the posterior head is trained over, and the mapping from a position to a cell.

from __future__ import annotations

import numpy as np

ROOM_M = 5.0


# Function grid n.
def grid_n(n_cells: int) -> int:
    n = int(round(np.sqrt(n_cells)))
    if n * n != n_cells:
        raise ValueError(f"n_cells must be a perfect square, got {n_cells}")
    return n


# Cell centres, (n_cells, 2), ordered so that index = row * n + col.
def centres(n_cells: int) -> np.ndarray:
    n = grid_n(n_cells)
    step = ROOM_M / n
    xs = (np.arange(n) + 0.5) * step
    gx, gy = np.meshgrid(xs, xs, indexing="xy")
    return np.stack([gx.ravel(), gy.ravel()], axis=1)


# The cell each position falls in.
def cell_index(xy: np.ndarray, n_cells: int) -> np.ndarray:
    n = grid_n(n_cells)
    step = ROOM_M / n
    ij = np.clip(np.floor(np.asarray(xy, dtype=float) / step).astype(int), 0, n - 1)
    return ij[:, 1] * n + ij[:, 0]


# Mean distance from a uniform point in the room to the nearest cell centre.
def quantisation_floor(n_cells: int, n: int = 200000, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    pts = rng.uniform(0, ROOM_M, size=(n, 2))
    c = centres(n_cells)
    d = np.linalg.norm(pts[:, None, :] - c[None, :, :], axis=2).min(1)
    return float(d.mean())
