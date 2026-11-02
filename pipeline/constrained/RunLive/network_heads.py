# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The heads that sit on the encoder: identity, position and cell.

from __future__ import annotations

import torch
import torch.nn as nn


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
