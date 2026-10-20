# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Task heads: identity, 2D position, and 25-way cell.

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


# Softmax classification head over enrolled subject identities.
class IDHead(nn.Module):

    # Sets up the object.
    def __init__(self, in_dim: int, n_classes: int = 8, dropout: float = 0.2) -> None:
        super().__init__()
        self.n_classes = int(n_classes)
        self.net = nn.Sequential(nn.Dropout(dropout), nn.Linear(in_dim, n_classes))

    # Identity logits (batch, n_classes); logits, not probabilities.
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# Regression head predicting a 2D floor position in metres.
class PositionHead(nn.Module):

    # Sets up the object.
    def __init__(self, in_dim: int, hidden_dim: int = 64, dropout: float = 0.2) -> None:
        super().__init__()
        self.net = nn.Sequential(nn.Linear(in_dim, hidden_dim), nn.ReLU(inplace=True), nn.Dropout(dropout), nn.Linear(hidden_dim, 2))

    # (batch, 2) as (x, y) in metres in the room frame; no normalisation baked in.
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# 25-way cell classification head: tracking as a fingerprint lookup, which is what the data supports.
class CellHead(nn.Module):

    # Sets up the object.
    def __init__(self, in_dim: int, n_cells: int = 25, dropout: float = 0.2) -> None:
        super().__init__()
        self.n_cells = int(n_cells)
        self.net = nn.Sequential(nn.Dropout(dropout), nn.Linear(in_dim, n_cells))

    # Function forward.
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# Cross-entropy for the identity head.
def id_loss(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    return F.cross_entropy(logits, targets)


# Cross-entropy for the cell head.
def cell_loss(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    return F.cross_entropy(logits, targets)


# Smooth L1 on the coordinates, in metres.
def position_loss(pred: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    return F.smooth_l1_loss(pred, targets)


# Per-sample Euclidean error in metres, (batch,).
def position_error(pred: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    return torch.linalg.norm(pred - targets, dim=-1)
