# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Per-link CNN with weights shared across the three receiver links.

from __future__ import annotations

from typing import Sequence

import torch
import torch.nn as nn


# Convolutional encoder applied identically to every TX-RX link.
class LinkCNN(nn.Module):

    # Build the shared per-link encoder.
    def __init__(
        self,
        in_channels: int = 1,
        n_sub: int = 107,
        embed_dim: int = 64,
        channels: Sequence[int] = (16, 32, 48),
        dropout: float = 0.2,
        pool_out: tuple[int, int] = (3, 3),
    ) -> None:
        super().__init__()
        self.in_channels = int(in_channels)
        self.n_sub = int(n_sub)
        self.embed_dim = int(embed_dim)
        layers: list[nn.Module] = []
        c_in = self.in_channels
        for c_out in channels:
            layers += [nn.Conv2d(c_in, c_out, kernel_size=5, padding=2), nn.BatchNorm2d(c_out), nn.ReLU(inplace=True),
                       nn.MaxPool2d(kernel_size=2)]
            c_in = c_out
        self.features = nn.Sequential(*layers)
        self.pool_out = tuple(int(v) for v in pool_out)
        self.pool = nn.AdaptiveAvgPool2d(self.pool_out)
        self.embed = nn.Sequential(nn.Flatten(), nn.Dropout(dropout), nn.Linear(c_in * pool_out[0] * pool_out[1], embed_dim))

    # Encode one link's window into an embedding.
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 4 or x.shape[1] != self.in_channels:
            raise ValueError(f"expected (batch, {self.in_channels}, n_samples, n_sub), got {tuple(x.shape)}")
        h = self.features(x)
        ph, pw = self.pool_out
        if h.shape[2] < ph or h.shape[3] < pw:
            h = torch.nn.functional.pad(h, (0, max(0, pw - h.shape[3]), 0, max(0, ph - h.shape[2])), mode="replicate")
        th, sw = (h.shape[2] // ph) * ph, (h.shape[3] // pw) * pw
        return self.embed(self.pool(h[:, :, :th, :sw]))

    # Function n parameters.
    def n_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters())


# Apply the shared encoder to all links in a batch.
def encode_links(encoder: LinkCNN, links: torch.Tensor) -> torch.Tensor:
    if links.ndim != 5:
        raise ValueError(f"expected (batch, n_links, in_channels, n_samples, n_sub), got {tuple(links.shape)}")
    b, n, c, t, s = links.shape
    z = encoder(links.reshape(b * n, c, t, s))
    return z.reshape(b, n, -1)
