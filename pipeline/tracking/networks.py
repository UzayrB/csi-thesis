# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: T7, windows to scores: each 2 s window goes through the tracker's five networks, which give a probability...

from __future__ import annotations

import os
from functools import lru_cache

import numpy as np
import torch
import torch.nn as nn
from scipy import signal

FS = 150.0
LOWPASS_HZ = 2.0
MOTION_BAND_HZ = (0.3, 2.0)
ROOM_M = 5.0
LOG_FLOOR = -30.0
EMBED, CHANNELS, DROPOUT = 64, (16, 32, 48), 0.2
USE_CPU = False



# Function use cpu.
def use_cpu() -> None:
    global USE_CPU
    USE_CPU = True


# Function device.
def device() -> torch.device:
    if not USE_CPU and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")



# The frozen tracker's five shared-encoder networks, run on single windows.
class Networks:

    # The networks meta.json names under "heads", from the frozen folder; the training marginal and its weight...
    def __init__(self, folder: str, meta: dict, pieces: dict):
        if pieces.get("marg") is None:
            raise SystemExit("REFUSED: the frozen tracker has no training marginal; the app scores cells against it only")
        self.st, self.alpha, self.marg = pieces["st"], pieces["alpha"], pieces["marg"]
        self.heads = []
        for name, cells, rel in meta["heads"]:
            p = os.path.join(folder, rel)
            m, mu, sd = load_network(p)
            assert isinstance(m, SharedNet), f"{p} is not a shared-encoder network"
            self.heads.append((name, int(cells), (m, np.asarray(mu), np.asarray(sd))))

    # The networks' input for each window: every receiver's shape lowpassed below LOWPASS_HZ, the window as stored.
    @staticmethod
    def features(windows: np.ndarray) -> np.ndarray:
        return np.stack([np.stack([lowpass(link) for link in as_stored(w)]) for w in windows]).astype(np.float32)

    # The window's unscaled walking-band energy; the session applies the relative gate.
    @staticmethod
    def gate_energy(window: np.ndarray) -> float:
        return band_energy(as_stored(window))

    # {head: (n, cells) float32 fused posterior}, on the RSSI relative to each receiver's idle mean.
    def head_probs(self, feats: np.ndarray, rssi: np.ndarray, means) -> dict:
        R = np.array(rssi, dtype=np.float32)
        for li in range(R.shape[1]):
            R[:, li] = R[:, li] - float(means[li])
        return {name: infer_shared(m, mu, sd, np.asarray(feats, np.float32), R).astype(np.float32)
                for name, _cells, (m, mu, sd) in self.heads}

    # The five heads' cell probabilities as one score per line point: each head's cells (a 10 x 10 head summed...
    def emissions_from_probs(self, probs: dict) -> np.ndarray:
        parts = []
        for name, cells, _m in self.heads:
            prob = probs[name].astype(float)
            if cells == 100:
                prob = g100_to_25(prob)
                prob = prob / np.maximum(prob.sum(axis=1, keepdims=True), 1e-300)
            parts.append(scaled_cell_emission(prob, self.st.xy, self.marg, self.alpha))
        return pool(parts)



# The window as the training windows were stored: float16, then float32.
def as_stored(window: np.ndarray) -> np.ndarray:
    return np.asarray(window).astype(np.float16).astype(np.float32)


# Function lowpass sos.
@lru_cache(maxsize=16)
def _lowpass_sos(fs: float, cutoff: float, order: int) -> np.ndarray:
    return signal.butter(order, cutoff / (0.5 * fs), btype="lowpass", output="sos")


# Zero-phase lowpass of one receiver's window (samples, subcarriers), the steady part passed intact.
def lowpass(amplitude: np.ndarray, order: int = 4) -> np.ndarray:
    a = np.asarray(amplitude, dtype=np.float64)
    pad = min(3 * (2 * order + 1) * 4, a.shape[0] - 1)
    return signal.sosfiltfilt(_lowpass_sos(FS, LOWPASS_HZ, int(order)), a, axis=0, padlen=pad).astype(np.float32)



# The window's power in the walking band, the mean over subcarriers and receivers.
def band_energy(window: np.ndarray, band: tuple = MOTION_BAND_HZ) -> float:
    x = np.asarray(window, dtype=np.float64)
    x = x - x.mean(axis=1, keepdims=True)
    f = np.fft.rfftfreq(x.shape[1], 1 / FS)
    P = (np.abs(np.fft.rfft(x, axis=1)) ** 2) / x.shape[1]
    sel = (f >= band[0]) & (f <= band[1])
    return float(P[:, sel, :].sum(axis=1).mean())



# The fused head's probabilities for a block of windows (each receiver's features with its RSSI as a second...
def infer_shared(model, mu, sd, X_links, rssi, batch: int = 128) -> np.ndarray:
    dev = device()
    model = model.to(dev).eval()
    P = []
    with torch.no_grad():
        for i in range(0, len(X_links), batch):
            xb = (stack_all(X_links[i:i + batch], rssi[i:i + batch]) - mu) / sd
            P.append(torch.softmax(model(torch.from_numpy(xb.astype(np.float32)).to(dev)), 1).cpu().numpy().astype(np.float64))
    if dev.type == "mps":
        torch.mps.empty_cache()
    p = np.concatenate(P)
    return p / np.maximum(p.sum(1, keepdims=True), 1e-12)


# (n, 3, H, W) features and (n, 3, H) RSSI to (n, 3, 2, H, W), receiver by receiver.
def stack_all(X_links: np.ndarray, rssi: np.ndarray) -> np.ndarray:
    return np.concatenate([stack_link(X_links[:, [li]], rssi[:, [li]]) for li in range(X_links.shape[1])], axis=1)


# (n, 1, H, W) features plus their (n, 1, H) RSSI to (n, 1, 2, H, W).
def stack_link(X_link: np.ndarray, second: np.ndarray) -> np.ndarray:
    base = X_link[:, :, None]
    rep = np.repeat(second[:, :, None, :, None], base.shape[-1], axis=-1)
    return np.concatenate([base, rep.astype(np.float32)], axis=2)


# Fused (x, y) over a block of windows, and the per-link predictions behind it.
def position_of(models, X: np.ndarray, rssi: np.ndarray, batch: int = 128) -> tuple:
    per_link = []
    for li, (model, mu, sd) in enumerate(models):
        Xb = stack_link(X[:, [li]], rssi[:, [li]])
        Xb = torch.from_numpy(((Xb - mu) / sd).astype(np.float32))
        per_link.append(infer_logits(model, Xb, batch).astype(np.float64))
    stack = np.stack(per_link)
    return stack.mean(axis=0), stack


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



# A 10 by 10 grid summed into 5 by 5: each 25-cell is exactly four g100 cells.
def g100_to_25(prob100) -> np.ndarray:
    p = np.asarray(prob100, float)
    n = p.shape[0]
    return p.reshape(n, 10, 10).reshape(n, 5, 2, 5, 2).sum(axis=(2, 4)).reshape(n, 25)


# (T, 25) cell probabilities to (T, line points) log scores: each point takes its cell's log probability...
def scaled_cell_emission(prob: np.ndarray, state_xy: np.ndarray, marginal: np.ndarray, alpha: float) -> np.ndarray:
    idx = cell_index(state_xy, 25)
    e = np.log(np.clip(np.asarray(prob, dtype=float), np.exp(LOG_FLOOR), None))[:, idx]
    return e - float(alpha) * np.log(np.asarray(marginal, float))[idx][None, :]


# The cell each position falls in, on the room's n x n grid.
def cell_index(xy: np.ndarray, n_cells: int) -> np.ndarray:
    n = int(round(np.sqrt(n_cells)))
    step = ROOM_M / n
    ij = np.clip(np.floor(np.asarray(xy, dtype=float) / step).astype(int), 0, n - 1)
    return ij[:, 1] * n + ij[:, 0]


# The equal-weight log-opinion pool of the five heads' scores, renormalised per window.
def pool(emissions) -> np.ndarray:
    n = min(len(e) for e in emissions)
    m = np.mean([np.asarray(e[:n], float) for e in emissions], axis=0)
    return m - m.max(axis=1, keepdims=True)



# A saved network, its input mean and its input sd: a SharedNet when the file says so (its "arch"), else a...
def load_network(path: str):
    d = torch.load(path, map_location="cpu", weights_only=False)
    if d.get("arch"):
        if d["arch"] != "fuse":
            raise SystemExit(f"REFUSED: {path} is a {d['arch']!r} network; the app runs the 'fuse' networks only")
        m = SharedNet(d["n_links"], d["out_dim"], d["in_channels"])
    else:
        m = LinkNet(d["n_links"], d["out_dim"], {"pos": "position", "g": "posterior"}.get(d["kind"], d["kind"]),
                    d["in_channels"])
    m.load_state_dict(d["state_dict"])
    m.eval()
    return m, d["mu"], d["sd"]


# The shipped network: one encoder shared by the three receivers, their embeddings joined into one head.
class SharedNet(nn.Module):

    # Sets up the object.
    def __init__(self, n_links: int, out_dim: int, in_channels: int = 2):
        super().__init__()
        self.n_links = int(n_links)
        self.encoder = LinkCNN(in_channels=in_channels, embed_dim=EMBED, channels=CHANNELS, dropout=DROPOUT)
        self.aux = IDHead(EMBED, out_dim, dropout=DROPOUT)
        self.head = IDHead(EMBED * n_links, out_dim, dropout=DROPOUT)

    # Function forward.
    def forward(self, x):
        z = encode_links(self.encoder, x)
        return self.head(z.reshape(z.shape[0], -1))


# One receiver's encoder plus a task head (the start-of-walk readers' networks).
class LinkNet(nn.Module):

    # Sets up the object.
    def __init__(self, n_links: int, out_dim: int, head: str = "posterior", in_channels: int = 2):
        super().__init__()
        self.encoder = LinkCNN(in_channels=in_channels, embed_dim=EMBED, channels=CHANNELS, dropout=DROPOUT)
        d = EMBED * n_links
        self.head = PositionHead(d, 64, DROPOUT) if head == "position" else IDHead(d, out_dim, dropout=DROPOUT)

    # Function forward.
    def forward(self, x):
        return self.head(self.embed(x))

    # The pooled per-receiver embedding, before the head.
    def embed(self, x):
        z = encode_links(self.encoder, x)
        return z.reshape(z.shape[0], -1)


# The convolutional encoder, applied identically to every receiver's window.
class LinkCNN(nn.Module):

    # Sets up the object.
    def __init__(self, in_channels: int = 1, embed_dim: int = 64, channels=(16, 32, 48), dropout: float = 0.2,
                 pool_out: tuple = (3, 3)) -> None:
        super().__init__()
        self.in_channels = int(in_channels)
        layers: list = []
        c_in = self.in_channels
        for c_out in channels:
            layers += [nn.Conv2d(c_in, c_out, kernel_size=5, padding=2), nn.BatchNorm2d(c_out), nn.ReLU(inplace=True),
                       nn.MaxPool2d(kernel_size=2)]
            c_in = c_out
        self.features = nn.Sequential(*layers)
        self.pool_out = tuple(int(v) for v in pool_out)
        self.pool = nn.AdaptiveAvgPool2d(self.pool_out)
        self.embed = nn.Sequential(nn.Flatten(), nn.Dropout(dropout), nn.Linear(c_in * pool_out[0] * pool_out[1], embed_dim))

    # Function forward.
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 4 or x.shape[1] != self.in_channels:
            raise ValueError(f"expected (batch, {self.in_channels}, n_samples, n_sub), got {tuple(x.shape)}")
        h = self.features(x)
        ph, pw = self.pool_out
        if h.shape[2] < ph or h.shape[3] < pw:
            h = torch.nn.functional.pad(h, (0, max(0, pw - h.shape[3]), 0, max(0, ph - h.shape[2])), mode="replicate")
        th, sw = (h.shape[2] // ph) * ph, (h.shape[3] // pw) * pw
        return self.embed(self.pool(h[:, :, :th, :sw]))


# The shared encoder on every receiver of a batch: (B, L, C, H, W) to (B, L, embed).
def encode_links(encoder: LinkCNN, links: torch.Tensor) -> torch.Tensor:
    b, n, c, t, s = links.shape
    return encoder(links.reshape(b * n, c, t, s)).reshape(b, n, -1)


# A linear head over the cells (or the classes), as logits.
class IDHead(nn.Module):

    # Sets up the object.
    def __init__(self, in_dim: int, n_classes: int = 8, dropout: float = 0.2) -> None:
        super().__init__()
        self.net = nn.Sequential(nn.Dropout(dropout), nn.Linear(in_dim, n_classes))

    # Function forward.
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# A head that regresses (x, y) in metres.
class PositionHead(nn.Module):

    # Sets up the object.
    def __init__(self, in_dim: int, hidden_dim: int = 64, dropout: float = 0.2) -> None:
        super().__init__()
        self.net = nn.Sequential(nn.Linear(in_dim, hidden_dim), nn.ReLU(inplace=True), nn.Dropout(dropout),
                                 nn.Linear(hidden_dim, 2))

    # Function forward.
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)
