# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The encoder and the two heads, built from pipeline.models alone.

from __future__ import annotations

from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from pipeline.constrained.heads import IDHead, PositionHead
from pipeline.constrained.link_cnn import LinkCNN, encode_links

LR = 1e-3
WEIGHT_DECAY = 1e-4
BATCH = 64
DROPOUT = 0.2
EMBED = 64
CHANNELS = (16, 32, 48)


# Function device.
def device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


# One link's encoder plus a task head.
class LinkNet(nn.Module):

    # Sets up the object.
    def __init__(self, n_links: int, out_dim: int, head: str = "posterior", in_channels: int = 2):
        super().__init__()
        self.encoder = LinkCNN(in_channels=in_channels, embed_dim=EMBED, channels=CHANNELS,
                               dropout=DROPOUT)
        d = EMBED * n_links
        self.head = (PositionHead(d, 64, DROPOUT) if head == "position"
                     else IDHead(d, out_dim, dropout=DROPOUT))
        self.head_kind = head

    # Function forward.
    def forward(self, x):
        z = encode_links(self.encoder, x)
        return self.head(z.reshape(z.shape[0], -1))

    # The pooled per-link embedding, before the head.
    def embed(self, x):
        z = encode_links(self.encoder, x)
        return z.reshape(z.shape[0], -1)


# Mean and standard deviation per CHANNEL, over the training side only.
def per_channel_stats(X: np.ndarray):
    ax = (0, 1, 3, 4)
    return X.mean(axis=ax, keepdims=True), X.std(axis=ax, keepdims=True) + 1e-8


# (n, 1, H, W) plus an optional (n, 1, H) series to (n, 1, channels, H, W).
def stack_link(X_link: np.ndarray, second: Optional[np.ndarray]) -> np.ndarray:
    base = X_link[:, :, None]
    if second is None:
        return base
    rep = np.repeat(second[:, :, None, :, None], base.shape[-1], axis=-1)
    return np.concatenate([base, rep.astype(np.float32)], axis=2)


# Function run epochs.
def run_epochs(model, Xt, yt, loss_fn, epochs: int, seed: int, lr: float = LR):
    dev = device()
    model = model.to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=WEIGHT_DECAY)
    rng = np.random.default_rng(seed)
    for _ in range(epochs):
        model.train()
        order = rng.permutation(len(Xt))
        for i in range(0, len(order), BATCH):
            idx = order[i:i + BATCH]
            opt.zero_grad()
            loss_fn(model(Xt[idx].to(dev)), yt[idx].to(dev)).backward()
            opt.step()
        if dev.type == "mps":
            torch.mps.empty_cache()
    model.eval()
    return model


# Function infer logits.
def infer_logits(model, Xe: torch.Tensor, batch: int = 128) -> np.ndarray:
    dev = device()
    model = model.to(dev)
    out = []
    with torch.no_grad():
        for i in range(0, len(Xe), batch):
            out.append(model(Xe[i:i + batch].to(dev)).cpu().numpy())
    if dev.type == "mps":
        torch.mps.empty_cache()
    return np.concatenate(out) if out else np.zeros((0, 1), dtype=np.float32)


# Function infer embeddings.
def infer_embeddings(model, Xe: torch.Tensor, batch: int = 128) -> np.ndarray:
    dev = device()
    model = model.to(dev)
    out = []
    with torch.no_grad():
        for i in range(0, len(Xe), batch):
            out.append(model.embed(Xe[i:i + batch].to(dev)).cpu().numpy())
    if dev.type == "mps":
        torch.mps.empty_cache()
    return np.concatenate(out) if out else np.zeros((0, EMBED), dtype=np.float32)


# Train one link's posterior head.
def fit_posterior(X: np.ndarray, cells: np.ndarray, n_cells: int, epochs: int, seed: int):
    from pipeline.constrained.common import seed_all
    mu, sd = per_channel_stats(X)
    seed_all(seed)
    model = LinkNet(X.shape[1], n_cells, "posterior", X.shape[2])
    model = run_epochs(model, torch.from_numpy(((X - mu) / sd).astype(np.float32)),
                       torch.from_numpy(np.asarray(cells, dtype=np.int64)),
                       F.cross_entropy, epochs, seed)
    return model, mu, sd


# Train one link's position head.
def fit_position(X: np.ndarray, xy: np.ndarray, epochs: int, seed: int):
    from pipeline.constrained.common import seed_all
    mu, sd = per_channel_stats(X)
    seed_all(seed)
    model = LinkNet(X.shape[1], 2, "position", X.shape[2])
    model = run_epochs(model, torch.from_numpy(((X - mu) / sd).astype(np.float32)),
                       torch.from_numpy(np.asarray(xy, dtype=np.float32)),
                       F.smooth_l1_loss, epochs, seed)
    return model, mu, sd


# Fused posterior over a block of windows, and the per-link posteriors behind it.
def posterior_of(models, X: np.ndarray, rssi: np.ndarray, batch: int = 128) -> tuple:
    per_link = []
    for li, (model, mu, sd) in enumerate(models):
        Xb = stack_link(X[:, [li]], None if rssi is None else rssi[:, [li]])
        Xb = torch.from_numpy(((Xb - mu) / sd).astype(np.float32))
        lg = infer_logits(model, Xb, batch)
        per_link.append(torch.softmax(torch.from_numpy(lg), dim=1).numpy().astype(np.float64))
        del Xb
    p = np.mean(np.stack(per_link), axis=0)
    return p / np.maximum(p.sum(1, keepdims=True), 1e-12), np.stack(per_link)


# Fused (x, y) over a block of windows, and the per-link predictions behind it.
def position_of(models, X: np.ndarray, rssi: np.ndarray, batch: int = 128) -> tuple:
    per_link = []
    for li, (model, mu, sd) in enumerate(models):
        Xb = stack_link(X[:, [li]], None if rssi is None else rssi[:, [li]])
        Xb = torch.from_numpy(((Xb - mu) / sd).astype(np.float32))
        per_link.append(infer_logits(model, Xb, batch).astype(np.float64))
        del Xb
    stack = np.stack(per_link)
    return stack.mean(axis=0), stack
