"""Task heads: identity, 2D position, and 25-way cell.

Every head sits on top of a fused representation. The identity head consumes
identification-branch features; the position and cell heads consume
tracking-branch features, which keep the near-DC component the ID branch
removes.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class IDHead(nn.Module):
    """Softmax classification head over enrolled subject identities."""

    def __init__(self, in_dim: int, n_classes: int = 8, dropout: float = 0.2) -> None:
        super().__init__()
        self.n_classes = int(n_classes)
        self.net = nn.Sequential(nn.Dropout(dropout), nn.Linear(in_dim, n_classes))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Identity logits ``(batch, n_classes)``; logits, not probabilities."""
        return self.net(x)


class PositionHead(nn.Module):
    """Regression head predicting a 2D floor position in metres."""

    def __init__(self, in_dim: int, hidden_dim: int = 64, dropout: float = 0.2) -> None:
        super().__init__()
        self.net = nn.Sequential(nn.Linear(in_dim, hidden_dim), nn.ReLU(inplace=True), nn.Dropout(dropout), nn.Linear(hidden_dim, 2))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """``(batch, 2)`` as ``(x, y)`` in metres in the room frame; no normalisation baked in."""
        return self.net(x)


class CellHead(nn.Module):
    """25-way cell classification head: tracking as a fingerprint lookup, which is what the data supports."""

    def __init__(self, in_dim: int, n_cells: int = 25, dropout: float = 0.2) -> None:
        super().__init__()
        self.n_cells = int(n_cells)
        self.net = nn.Sequential(nn.Dropout(dropout), nn.Linear(in_dim, n_cells))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def id_loss(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """Cross-entropy for the identity head."""
    return F.cross_entropy(logits, targets)


def cell_loss(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """Cross-entropy for the cell head."""
    return F.cross_entropy(logits, targets)


def position_loss(pred: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """Smooth L1 on the coordinates, in metres. Windows with no valid position are excluded by the caller."""
    return F.smooth_l1_loss(pred, targets)


def position_error(pred: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """Per-sample Euclidean error in metres, ``(batch,)``."""
    return torch.linalg.norm(pred - targets, dim=-1)
