# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Pd_arch: D4 of the tracking attack, the architecture options.

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn

from pipeline.constrained.heads import IDHead
from pipeline.constrained.link_cnn import LinkCNN, encode_links

EMBED, CHANNELS, DROPOUT = 64, (16, 32, 48), 0.2


# Class Shared Net.
class SharedNet(nn.Module):
    # Sets up the object.
    def __init__(self, n_links: int, out_dim: int, mode: str = "fuse", in_channels: int = 2):
        super().__init__()
        assert mode in ("fuse", "attn"), mode
        self.mode, self.n_links = mode, int(n_links)
        self.encoder = LinkCNN(in_channels=in_channels, embed_dim=EMBED, channels=CHANNELS, dropout=DROPOUT)
        self.aux = IDHead(EMBED, out_dim, dropout=DROPOUT)
        if mode == "fuse":
            self.head = IDHead(EMBED * n_links, out_dim, dropout=DROPOUT)
        else:
            self.score = nn.Sequential(nn.Linear(EMBED, 32), nn.Tanh(), nn.Linear(32, 1))
            self.link_bias = nn.Parameter(torch.zeros(n_links))
            self.head = IDHead(EMBED, out_dim, dropout=DROPOUT)

    # Function link weights.
    def link_weights(self, z):
        return torch.softmax(self.score(z).squeeze(-1) + self.link_bias[None, :], dim=1)

    # Function forward all.
    def forward_all(self, x):
        z = encode_links(self.encoder, x)
        if self.mode == "fuse":
            fused = self.head(z.reshape(z.shape[0], -1))
            a = None
        else:
            a = self.link_weights(z)
            fused = self.head((a[:, :, None] * z).sum(1))
        aux = self.aux(z.reshape(-1, z.shape[-1])).reshape(z.shape[0], z.shape[1], -1)
        return fused, aux, a

    # Function forward.
    def forward(self, x):
        fused, aux, _a = self.forward_all(x)
        return (fused, aux) if self.training else fused


# Per link AND channel: axes (0, 3, 4) of (n, links, channels, H, W).
def link_stats(X: np.ndarray):
    ax = (0, 3, 4)
    return X.mean(axis=ax, keepdims=True), X.std(axis=ax, keepdims=True) + 1e-8


# Function shared loss.
def shared_loss(out, y):
    import torch.nn.functional as F
    fused, aux = out
    L = aux.shape[1]
    return F.cross_entropy(fused, y) + sum(F.cross_entropy(aux[:, li], y) for li in range(L)) / L


# Function mixed shared loss.
def mixed_shared_loss(out, ya, yb, lam):
    import torch.nn.functional as F
    fused, aux = out
    L = aux.shape[1]

    # Function ce.
    def ce(o):
        return (lam * F.cross_entropy(o, ya, reduction="none") + (1 - lam) * F.cross_entropy(o, yb, reduction="none")).mean()
    return ce(fused) + sum(ce(aux[:, li]) for li in range(L)) / L


# (n, 3, H, W) features and (n, 3, H) RSSI to (n, 3, 2, H, W), link by link as stack_link does.
def stack_all(X_links: np.ndarray, rssi: np.ndarray) -> np.ndarray:
    from pipeline.constrained.nets import stack_link
    return np.concatenate([stack_link(X_links[:, [li]], rssi[:, [li]]) for li in range(X_links.shape[1])], axis=1)


# (prob, per_link) like nets.posterior_of: the fused head's softmax, and the auxiliary heads'.
def infer_shared(model, mu, sd, X_links, rssi, batch: int = 128):
    from pipeline.constrained.nets import device
    dev = device()
    model = model.to(dev).eval()
    P, PL = [], []
    with torch.no_grad():
        for i in range(0, len(X_links), batch):
            xb = (stack_all(X_links[i:i + batch], rssi[i:i + batch]) - mu) / sd
            fused, aux, _a = model.forward_all(torch.from_numpy(xb.astype(np.float32)).to(dev))
            P.append(torch.softmax(fused, 1).cpu().numpy().astype(np.float64))
            PL.append(torch.softmax(aux, 2).cpu().numpy().astype(np.float64))
    if dev.type == "mps":
        torch.mps.empty_cache()
    p = np.concatenate(P)
    return p / np.maximum(p.sum(1, keepdims=True), 1e-12), np.concatenate(PL).transpose(1, 0, 2)
