"""Per-link CNN with weights shared across the three receiver links.

The deployment has one ESP32 transmitter and three receivers, giving three
TX-RX links. Each link is encoded by the SAME CNN (shared weights), so the
encoder learns a link-agnostic representation and the fusion stage learns
how the three viewpoints combine.

SIZE
----
Roughly 100k parameters, in the range of a two-conv network. Not ResNet,
not a recurrent stack. On an eight-person cohort a larger backbone mostly
gains room to memorise the training room, which is the effect this thesis
is trying to remove. If more capacity is ever needed the lever is
pretraining, fine-tuning or augmentation, not depth (Decisions Log, 24
August 2026).
"""

from __future__ import annotations

from typing import Sequence

import torch
import torch.nn as nn


class LinkCNN(nn.Module):
    """Convolutional encoder applied identically to every TX-RX link.

    One instance is shared across all three links; it is never instantiated
    per link, since per-link weights would prevent the encoder from
    generalising across receiver placements.
    """

    def __init__(
        self,
        in_channels: int = 1,
        n_sub: int = 107,
        embed_dim: int = 64,
        channels: Sequence[int] = (16, 32, 48),
        dropout: float = 0.2,
        pool_out: tuple[int, int] = (3, 3),
    ) -> None:
        """Build the shared per-link encoder.

        Args:
            in_channels: Input channels per link: 1 for one time-by-
                subcarrier map, ``n_links`` for early channel stacking.
            n_sub: Number of retained subcarriers per link.
            embed_dim: Dimension of the per-link embedding produced.
            channels: Convolutional channel widths, in depth order.
            dropout: Dropout probability applied before the embedding.
            pool_out: Adaptive pooling output (time, subcarrier), so the
                embedding size does not depend on the window length.

        Constraints:
            Holds no link-specific parameters; the same module instance is
            applied to each of the three links. About 80k parameters at the
            defaults.
        """
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

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Encode one link's window into an embedding.

        Args:
            x: Tensor of shape ``(batch, in_channels, n_samples, n_sub)``
                for a single link.

        Returns:
            Embedding tensor of shape ``(batch, embed_dim)``.

        Constraints:
            Callable repeatedly within one forward pass, once per link,
            reusing the same weights.
        """
        if x.ndim != 4 or x.shape[1] != self.in_channels:
            raise ValueError(f"expected (batch, {self.in_channels}, n_samples, n_sub), got {tuple(x.shape)}")
        h = self.features(x)
        # Crop to a multiple of the pool grid: adaptive pooling on the MPS backend
        # requires divisible sizes, and a few edge rows of a 37 x 13 map carry nothing.
        # A feature map smaller than the pool grid would crop to zero, and the MPS backend additionally
        # requires the pool input to be divisible by the pool output. That never bites for the
        # 300 x 107 windows the frozen models use (37 x 13 after three pools), but it does for the
        # small spectrogram inputs of the push batch, so pad an undersized axis up to the grid first.
        ph, pw = self.pool_out
        if h.shape[2] < ph or h.shape[3] < pw:
            h = torch.nn.functional.pad(h, (0, max(0, pw - h.shape[3]), 0, max(0, ph - h.shape[2])), mode="replicate")
        th, sw = (h.shape[2] // ph) * ph, (h.shape[3] // pw) * pw
        return self.embed(self.pool(h[:, :, :th, :sw]))

    def n_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters())


def encode_links(encoder: LinkCNN, links: torch.Tensor) -> torch.Tensor:
    """Apply the shared encoder to all links in a batch.

    Args:
        encoder: The shared :class:`LinkCNN`.
        links: Tensor of shape ``(batch, n_links, in_channels, n_samples,
            n_sub)``, with ``n_links == 3`` for this deployment.

    Returns:
        Per-link embeddings of shape ``(batch, n_links, embed_dim)``.

    Constraints:
        Exactly one encoder is used for every link; no per-link weights.
        The links are folded into the batch so the encoder sees them as
        one batch and BatchNorm statistics are pooled across links.
    """
    if links.ndim != 5:
        raise ValueError(f"expected (batch, n_links, in_channels, n_samples, n_sub), got {tuple(links.shape)}")
    b, n, c, t, s = links.shape
    z = encoder(links.reshape(b * n, c, t, s))
    return z.reshape(b, n, -1)
