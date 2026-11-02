# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The grids of cells the networks were trained on, and how a position becomes a cell.

from __future__ import annotations

import numpy as np

ROOM_M = 5.0


# Function grid n.
def grid_n(n_cells: int) -> int:
    n = int(round(np.sqrt(n_cells)))
    if n * n != n_cells:
        raise ValueError(f"n_cells must be a perfect square, got {n_cells}")
    return n


# The cell each position falls in.
def cell_index(xy: np.ndarray, n_cells: int) -> np.ndarray:
    n = grid_n(n_cells)
    step = ROOM_M / n
    ij = np.clip(np.floor(np.asarray(xy, dtype=float) / step).astype(int), 0, n - 1)
    return ij[:, 1] * n + ij[:, 0]
