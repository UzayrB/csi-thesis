# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: T7, windows to scores: each 2 s window goes through the tracker's five networks, which give a probability...

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional, Sequence

import numpy as np
import torch
import torch.nn as nn
from scipy import signal



# The frozen tracker's five shared-encoder networks, run on single windows.
class Networks:

    # The networks meta.json names under "heads", from the frozen folder; the training marginal and its weight...
    def __init__(self, folder: str, meta: dict, pieces: dict):
        self.tag, self.st, self.kind, self.alpha = meta["heads_tag"], pieces["st"], pieces["kind"], pieces["alpha"]
        self.heads = []
        for name, cells, rel in meta["heads"]:
            p = os.path.join(folder, rel)
            m, mu, sd = load_network(p)
            assert isinstance(m, SharedNet), f"{p} is not a shared-encoder network"
            self.heads.append((name, int(cells), (m, np.asarray(mu), np.asarray(sd)), p))
        self.marg = pieces["marg"]

    # The networks' input for each window: tracking_features_links on the window as stored.
    @staticmethod
    def features(windows: np.ndarray) -> np.ndarray:
        return np.stack([tracking_features_links(as_stored(w), FS) for w in windows]).astype(np.float32)

    # The window's unscaled walking-band energy; the session applies the relative gate.
    @staticmethod
    def gate_energy(window: np.ndarray) -> float:
        return float(band_energy(as_stored(window), FS))

    # Float32 RSSI minus each link's idle mean (a Python float).
    @staticmethod
    def relative(rssi: np.ndarray, means) -> np.ndarray:
        R = np.array(rssi, dtype=np.float32)
        for li in range(R.shape[1]):
            R[:, li] = R[:, li] - float(means[li])
        return R

    # {head: (n, cells) float32 fused posterior}, on the RELATIVE RSSI.
    def head_probs(self, feats: np.ndarray, rssi: np.ndarray, means) -> dict:
        R = self.relative(rssi, means)
        out = {}
        for name, _cells, (m, mu, sd), _p in self.heads:
            p, _pl = infer_shared(m, mu, sd, np.asarray(feats, np.float32), R, 128)
            out[name] = p.astype(np.float32)
        return out

    # The five heads' cell probabilities as one score per line point: each head's cells (a 10 x 10 head summed...
    def emissions_from_probs(self, probs: dict) -> np.ndarray:
        parts = []
        for name, cells, _m, _p in self.heads:
            prob = probs[name].astype(float)
            if cells == 100:
                prob = g100_to_25(prob)
                prob = prob / np.maximum(prob.sum(axis=1, keepdims=True), 1e-300)
            parts.append(cell_emission(prob, self.st.xy, 25) if self.marg is None
                         else scaled_cell_emission(prob, self.st.xy, 25, self.marg, alpha=self.alpha))
        return pool(parts)


# The window as the training windows were stored: float16, then float32.
def as_stored(window: np.ndarray) -> np.ndarray:
    return np.asarray(window).astype(np.float16).astype(np.float32)



TRACKING_LOWPASS_HZ: float = 2.0


FS: float = 150.0


# Function lowpass sos.
@lru_cache(maxsize=16)
def _lowpass_sos(fs: float, cutoff: float, order: int) -> np.ndarray:
    return signal.butter(order, cutoff / (0.5 * fs), btype="lowpass", output="sos")


# Zero-phase lowpass of one link's window, DC and near-DC passed through intact.
def lowpass(amplitude: np.ndarray, fs: float = FS, cutoff: float = TRACKING_LOWPASS_HZ,
            order: int = 4) -> np.ndarray:
    a = np.asarray(amplitude, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError(f"expected (n_samples, n_sub), got {a.shape}")
    pad = min(3 * (2 * order + 1) * 4, a.shape[0] - 1)
    return signal.sosfiltfilt(_lowpass_sos(float(fs), float(cutoff), int(order)), a, axis=0,
                              padlen=pad).astype(np.float32)


# The lowpass applied to every link of a fusion window (n_links, n_samples, n_sub).
def tracking_features_links(window: np.ndarray, fs: float = FS,
                            cutoff: float = TRACKING_LOWPASS_HZ) -> np.ndarray:
    w = np.asarray(window)
    if w.ndim != 3:
        raise ValueError(f"expected (n_links, n_samples, n_sub), got {w.shape}")
    return np.stack([lowpass(w[i], fs, cutoff) for i in range(w.shape[0])])



DROPOUT = 0.2


EMBED = 64
CHANNELS = (16, 32, 48)


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


# Apply the shared encoder to all links in a batch.
def encode_links(encoder: LinkCNN, links: torch.Tensor) -> torch.Tensor:
    if links.ndim != 5:
        raise ValueError(f"expected (batch, n_links, in_channels, n_samples, n_sub), got {tuple(links.shape)}")
    b, n, c, t, s = links.shape
    z = encoder(links.reshape(b * n, c, t, s))
    return z.reshape(b, n, -1)


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


# (n, 3, H, W) features and (n, 3, H) RSSI to (n, 3, 2, H, W), link by link as stack_link does.
def stack_all(X_links: np.ndarray, rssi: np.ndarray) -> np.ndarray:
    return np.concatenate([stack_link(X_links[:, [li]], rssi[:, [li]]) for li in range(X_links.shape[1])], axis=1)


# (prob, per_link) like nets.posterior_of: the fused head's softmax, and the auxiliary heads'.
def infer_shared(model, mu, sd, X_links, rssi, batch: int = 128):
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


# (n, 1, H, W) plus an optional (n, 1, H) series to (n, 1, channels, H, W).
def stack_link(X_link: np.ndarray, second: Optional[np.ndarray]) -> np.ndarray:
    base = X_link[:, :, None]
    if second is None:
        return base
    rep = np.repeat(second[:, :, None, :, None], base.shape[-1], axis=-1)
    return np.concatenate([base, rep.astype(np.float32)], axis=2)


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


# A saved network, its input mean and its input sd: a SharedNet when the file says so (its "arch"), else a...
def load_network(path: str):
    d = torch.load(path, map_location="cpu", weights_only=False)
    if d.get("arch"):
        m = SharedNet(d["n_links"], d["out_dim"], d["arch"], d["in_channels"])
    else:
        head = {"pos": "position", "g": "posterior"}.get(d["kind"], d["kind"])
        m = LinkNet(d["n_links"], d["out_dim"], head, d["in_channels"])
    m.load_state_dict(d["state_dict"])
    m.eval()
    return m, d["mu"], d["sd"]



MOTION_BAND_HZ: tuple[float, float] = (0.3, 2.0)


# 0.3 to 2 Hz band power of one window, mean over subcarriers and links.
def band_energy(window: np.ndarray, fs: float, band: tuple[float, float] = MOTION_BAND_HZ) -> float:
    x = np.asarray(window, dtype=np.float64)
    if x.ndim == 2:
        x = x[None]
    if x.ndim != 3:
        raise ValueError(f"expected (links, samples, sub) or (samples, sub), got {x.shape}")
    x = x - x.mean(axis=1, keepdims=True)
    f = np.fft.rfftfreq(x.shape[1], 1 / fs)
    P = (np.abs(np.fft.rfft(x, axis=1)) ** 2) / x.shape[1]
    sel = (f >= band[0]) & (f <= band[1])
    return float(P[:, sel, :].sum(axis=1).mean())



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


LOG_FLOOR = -30.0


# Function log.
def _log(p: np.ndarray) -> np.ndarray:
    return np.log(np.clip(p, np.exp(LOG_FLOOR), None))


# (T, n_cells) posterior to (T, n_states) log emission, by the cell each state sits in.
def cell_emission(prob: np.ndarray, state_xy: np.ndarray, n_cells: int) -> np.ndarray:
    idx = cell_index(state_xy, n_cells)
    return _log(np.asarray(prob, dtype=float))[:, idx]


# Brief stage 1.5: decode on p(cell | x) / p(cell) rather than the posterior itself.
def scaled_cell_emission(prob: np.ndarray, state_xy: np.ndarray, n_cells: int,
                         marginal: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    idx = cell_index(state_xy, n_cells)
    e = _log(np.asarray(prob, dtype=float))[:, idx]
    if alpha == 0.0:
        return e
    return e - float(alpha) * np.log(np.asarray(marginal, float))[idx][None, :]


# Equal-weight log-opinion pool of N emissions, renormalised per window.
def pool(emissions):
    n = min(len(e) for e in emissions)
    m = np.mean([np.asarray(e[:n], float) for e in emissions], axis=0)
    return m - m.max(axis=1, keepdims=True)


# A 10 by 10 grid summed into 5 by 5: each 25-cell is exactly four g100 cells.
def g100_to_25(prob100):
    p = np.asarray(prob100, float)
    n = p.shape[0]
    g = p.reshape(n, 10, 10)
    return g.reshape(n, 5, 2, 5, 2).sum(axis=(2, 4)).reshape(n, 25)
