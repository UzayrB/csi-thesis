"""id25_learned. Item 8: the learned models of section 8 group D, nested, five seeds each.

ARCHITECTURES, each at most 50k parameters, a fixed epoch budget, Adam, weight decay 1e-4:
  D1_protoMLP    MLP on the U_all_gait features -> 16-d embedding; prototypes are training class
                 means; prediction is the nearest prototype (prototypical loss, episodic)
  D2_cnn1d       1D CNN on stride-normalised cycles: 21 channels (7 channel types x 3 links) of 32
                 phase points, circular padding, since a cycle has no start
  D3_cnn2d       2D CNN on Doppler spectrograms: 3 links x 28 frequency bins (4 to 70 Hz) x 56
                 frames, a 3.0 s CROP of the steady span. Cropped, never resampled: resampling the
                 time axis would change cadence, which is what the model must read
  D4_triplet     MLP embedding trained with batch-hard triplet loss; nearest-ENROLMENT inference
AUGMENTATION (training only): time shift, crop position, time and frequency masking, gain jitter,
additive noise, link dropout. NEVER time stretch, resampling or frequency shift.

NESTED. Inside each fold the architecture is chosen by inner accuracy (two seeds per inner fit);
the winner is then trained on the whole training side with five seeds. Reported: the mean and
spread over seeds, and the five-seed probability ensemble. AdaBN (batch-norm statistics
re-estimated on the unlabelled test day) is a separate TRANSDUCTIVE row for the CNNs.

DEVICE. `IDMAX_DEVICE` (mps | cpu), set by the launcher from the governor's two-sample GPU gate.
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np

import torch  # noqa: E402  (imported before job_start so its thread count is set there)
from torch import nn

from pipeline.identify import idmax_common as IC
from pipeline.identify import idmax_eval as E

STAGE = "id25_learned"
OUT = os.path.join(IC.ROOT, STAGE)
SEEDS = (0, 1, 2, 3, 4)
ARCHS = ("D1_protoMLP", "D2_cnn1d", "D3_cnn2d", "D4_triplet")
EPOCHS = {"D1_protoMLP": 120, "D2_cnn1d": 80, "D3_cnn2d": 60, "D4_triplet": 120}
LOSO_TAGS = ("s0102_to_s03", "s0103_to_s02", "s0203_to_s01")
TPL_TYPES = ("mean@b03_2|{L}|0", "mean@b08_35|{L}|0", "rms@b08_35|{L}|0", "rms@dop|{L}|0",
             "pca@b08_35|{L}|0", "pca@b08_35|{L}|1", "pca@b08_35|{L}|2")


def device() -> torch.device:
    d = os.environ.get("IDMAX_DEVICE", "cpu")
    if d == "mps" and torch.backends.mps.is_available() and not IC.force_cpu():
        return torch.device("mps")
    return torch.device("cpu")


# ------------------------------------------------------------------ inputs

def feature_matrix() -> np.ndarray:
    fc = E.FConf("steady_raw", "U_all_gait", "mean@b08_35")
    V = E.load_variant("steady_raw")
    return V["X"][:, E.columns(fc)]


def template_tensor() -> np.ndarray:
    V = E.load_variant("steady_raw")
    col = {n: j for j, n in enumerate(V["names"])}
    T = np.zeros((V["X"].shape[0], 21, 32), np.float32)
    c = 0
    for L in ("RX1", "RX2", "RX3"):
        for t in TPL_TYPES:
            pre = "tplacf|" + t.format(L=L)
            for i in range(32):
                j = col.get(f"{pre}|tpl_{i:02d}")
                if j is not None:
                    T[:, c, i] = np.nan_to_num(V["X"][:, j])
            c += 1
    return T


def spectrogram_tensor() -> np.ndarray:
    p = os.path.join(OUT, "spec.npz")
    if os.path.exists(p):
        return np.load(p)["S"]
    from scipy import signal
    from pipeline.identify import idmax_features as F
    from pipeline.identify.id19_featbank import load_segment
    inv = IC.pass_inventory()
    n_fr = 56
    S = np.zeros((len(inv), 3, 28, n_fr), np.float32)
    for i, r in enumerate(inv):
        a, _rs = load_segment(r, "steady", "raw")
        n = a.shape[1]
        L3 = int(3.0 * IC.FS)
        lo = max((n - L3) // 2, 0)
        for li in range(3):
            P = F.reduce_link(a[li], "dop", "pca", n_pc=4)[1:]            # PC1 dropped
            f, t, Z = signal.stft(P[:, lo:lo + L3], fs=IC.FS, nperseg=32, noverlap=24, nfft=64,
                                  axis=-1, boundary=None, padded=False)
            mag = np.abs(Z).sum(axis=0)
            keep = (f >= 4.0) & (f <= 70.0)
            m = np.log(mag[keep][:28] + 1e-6)
            m = m - m.mean()
            k = min(m.shape[1], n_fr)
            S[i, li, : m.shape[0], :k] = m[:, :k]
    os.makedirs(OUT, exist_ok=True)
    np.savez_compressed(p, S=S)
    return S


# ------------------------------------------------------------------ models

class MLP(nn.Module):
    def __init__(self, d_in, n_cls, emb=16):
        super().__init__()
        h = max(8, min(32, 48000 // max(d_in, 1)))
        self.f = nn.Sequential(nn.Linear(d_in, h), nn.BatchNorm1d(h), nn.ReLU(), nn.Dropout(0.3),
                               nn.Linear(h, emb))
        self.n_cls = n_cls

    def forward(self, x):
        return self.f(x)


class CNN1D(nn.Module):
    def __init__(self, c_in, n_cls):
        super().__init__()
        self.f = nn.Sequential(
            nn.Conv1d(c_in, 24, 5, padding=2, padding_mode="circular"), nn.BatchNorm1d(24), nn.ReLU(),
            nn.Conv1d(24, 24, 5, padding=2, padding_mode="circular"), nn.BatchNorm1d(24), nn.ReLU(),
            nn.Conv1d(24, 24, 3, padding=1, padding_mode="circular"), nn.BatchNorm1d(24), nn.ReLU())
        self.head = nn.Linear(48, n_cls)

    def forward(self, x):
        h = self.f(x)
        return self.head(torch.cat([h.mean(-1), h.amax(-1)], 1))


class CNN2D(nn.Module):
    def __init__(self, c_in, n_cls):
        super().__init__()
        self.f = nn.Sequential(
            nn.Conv2d(c_in, 12, 3, padding=1), nn.BatchNorm2d(12), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(12, 24, 3, padding=1), nn.BatchNorm2d(24), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(24, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU())
        self.head = nn.Linear(64, n_cls)

    def forward(self, x):
        h = self.f(x)
        return self.head(torch.cat([h.mean((-1, -2)), h.amax((-1, -2))], 1))


def n_params(m) -> int:
    return int(sum(p.numel() for p in m.parameters()))


def augment(x: torch.Tensor, kind: str, g: torch.Generator) -> torch.Tensor:
    """Shift, mask, gain jitter, noise, link dropout. Never stretch, resample or shift frequency."""
    x = x.clone()
    B = x.shape[0]
    dev = x.device
    if kind == "cnn1d":                                   # circular phase shift, link dropout
        s = int(torch.randint(0, 32, (1,), generator=g))
        x = torch.roll(x, s, dims=-1)
        x = x * (1 + 0.1 * torch.randn(B, x.shape[1], 1, generator=g).to(dev))
        drop = torch.rand(B, 3, generator=g) < 0.15
        mask = drop.repeat_interleave(7, 1).to(dev)
        x[mask] = 0.0
    elif kind == "cnn2d":                                 # time shift, masks, gain, link dropout
        s = int(torch.randint(-6, 7, (1,), generator=g))
        x = torch.roll(x, s, dims=-1)
        t0 = int(torch.randint(0, x.shape[-1] - 8, (1,), generator=g))
        x[..., t0:t0 + 6] = 0.0
        f0 = int(torch.randint(0, x.shape[-2] - 4, (1,), generator=g))
        x[..., f0:f0 + 3, :] = 0.0
        x = x + 0.2 * torch.randn(B, x.shape[1], 1, 1, generator=g).to(dev)
        drop = (torch.rand(B, 3, generator=g) < 0.15).to(dev)
        x[drop] = 0.0
    else:                                                  # features: noise and feature masking
        x = x + 0.1 * torch.randn(x.shape, generator=g).to(dev)
        x = x * (torch.rand(x.shape, generator=g) > 0.05).float().to(dev)
    return x + 0.02 * torch.randn(x.shape, generator=g).to(dev)


def _batches(n, bs, g):
    p = torch.randperm(n, generator=g)
    return [p[i:i + bs] for i in range(0, n, bs)]


def train_eval(arch: str, Xtr: np.ndarray, ytr: np.ndarray, Xte: np.ndarray, classes: list,
               seed: int, adabn: bool = False, return_net: bool = False):
    """Fit on the training side only; return (n_te, n_cls) probabilities, and with `return_net`
    also the trained network and the normalised train and test tensors (for id26b's diagnostics)."""
    dev = device()
    torch.manual_seed(seed)
    g = torch.Generator().manual_seed(seed)
    yi = torch.tensor([classes.index(v) for v in ytr])
    if arch in ("D1_protoMLP", "D4_triplet"):
        mu, sd = np.nanmean(Xtr, 0), np.nanstd(Xtr, 0)
        sd = np.where(sd > 1e-9, sd, 1.0)
        med = np.where(np.isfinite(mu), mu, 0.0)
        A = np.where(np.isfinite(Xtr), Xtr, med)
        B = np.where(np.isfinite(Xte), Xte, med)
        A, B = (A - med) / sd, (B - med) / sd
        kind = "feat"
    else:
        mu = Xtr.mean(axis=(0, -1) if Xtr.ndim == 3 else (0, -1, -2), keepdims=True)
        sd = Xtr.std(axis=(0, -1) if Xtr.ndim == 3 else (0, -1, -2), keepdims=True) + 1e-6
        A, B = (Xtr - mu[0:1]) / sd[0:1], (Xte - mu[0:1]) / sd[0:1]
        kind = "cnn1d" if arch == "D2_cnn1d" else "cnn2d"
    A = torch.tensor(A, dtype=torch.float32, device=dev)
    Bt = torch.tensor(B, dtype=torch.float32, device=dev)
    yi = yi.to(dev)
    C = len(classes)
    if arch == "D1_protoMLP" or arch == "D4_triplet":
        net = MLP(A.shape[1], C).to(dev)
    elif arch == "D2_cnn1d":
        net = CNN1D(A.shape[1], C).to(dev)
    else:
        net = CNN2D(A.shape[1], C).to(dev)
    assert n_params(net) <= 50_000, (arch, n_params(net))
    opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-4)
    for _ep in range(EPOCHS[arch]):
        net.train()
        for idx in _batches(len(A), 48, g):
            idx = idx.to(dev)
            xb = augment(A[idx], kind, g)
            yb = yi[idx]
            if arch == "D1_protoMLP":
                z = net(xb)
                present = torch.unique(yb)
                if len(present) < 2:
                    continue
                protos = torch.stack([z[yb == c].mean(0) for c in present])
                d = torch.cdist(z, protos) ** 2
                tgt = torch.stack([(present == c).nonzero()[0, 0] for c in yb])
                loss = nn.functional.cross_entropy(-d, tgt)
            elif arch == "D4_triplet":
                z = nn.functional.normalize(net(xb), dim=1)
                D = torch.cdist(z, z)
                same = yb[:, None] == yb[None, :]
                pos = (D * same.float()).amax(1)
                neg = (D + 1e3 * same.float()).amin(1)
                loss = torch.relu(pos - neg + 0.3).mean()
            else:
                loss = nn.functional.cross_entropy(net(xb), yb)
            opt.zero_grad()
            loss.backward()
            opt.step()
    if adabn:
        # TRANSDUCTIVE: re-estimate batch-norm statistics on the unlabelled test day
        for m in net.modules():
            if isinstance(m, (nn.BatchNorm1d, nn.BatchNorm2d)):
                m.reset_running_stats()
                m.momentum = None
        net.train()
        with torch.no_grad():
            net(Bt)
    net.eval()
    with torch.no_grad():
        if arch in ("D1_protoMLP", "D4_triplet"):
            za, zb = net(A), net(Bt)
            if arch == "D4_triplet":
                za, zb = nn.functional.normalize(za, dim=1), nn.functional.normalize(zb, dim=1)
                D = torch.cdist(zb, za)                               # nearest ENROLMENT pass
                P = torch.stack([-(D[:, yi == c].amin(1)) for c in range(C)], 1) * 10
            else:
                protos = torch.stack([za[yi == c].mean(0) for c in range(C)])
                P = -torch.cdist(zb, protos) ** 2
        else:
            P = net(Bt)
        P = torch.softmax(P, 1).cpu().numpy()
    if return_net:
        return P, net, A, Bt
    return P


# ------------------------------------------------------------------ nested

def inputs() -> dict:
    return {"D1_protoMLP": feature_matrix(), "D4_triplet": feature_matrix(),
            "D2_cnn1d": template_tensor(), "D3_cnn2d": spectrogram_tensor()}


def run_fold(f: E.Fold, y: np.ndarray, X: dict, ck: IC.Checkpoint) -> dict:
    classes = sorted(set(y[f.tr]))
    inner = {}
    for arch in ARCHS:
        key = f"{f.tag}|inner|{arch}"
        if ck.has(key):
            inner[arch] = ck.done[key]["acc"]
            continue
        accs = []
        for a, b in f.inner:
            P = np.mean([train_eval(arch, X[arch][a], y[a], X[arch][b], classes, s)
                         for s in SEEDS[:2]], axis=0)
            accs.append(float(np.mean(np.asarray(classes)[P.argmax(1)] == y[b])))
        inner[arch] = float(np.mean(accs))
        ck.put(key, {"acc": inner[arch]})
        if IC.should_stop():
            raise SystemExit("SIGTERM; checkpoint holds the progress")
    best = max(ARCHS, key=lambda k: (inner[k], -ARCHS.index(k)))
    Ps, accs = [], []
    for s in SEEDS:
        P = train_eval(best, X[best][f.tr], y[f.tr], X[best][f.te], classes, s)
        Ps.append(P)
    P = np.mean(Ps, 0)
    pred = np.asarray(classes)[P.argmax(1)]
    truth = f.y_te.reveal(pred)
    seed_acc = [float(np.mean(np.asarray(classes)[Q.argmax(1)] == truth)) for Q in Ps]
    r = {"tag": f.tag, "scope": f.scope, "config": best, "model": best, "inner": inner,
         "te": f.te.tolist(), "pred": pred.tolist(), "truth": truth.tolist(),
         "proba": np.round(P, 5).tolist(), "classes": classes,
         "acc": float(np.mean(pred == truth)), "seed_acc": seed_acc}
    if best in ("D2_cnn1d", "D3_cnn2d"):
        Pa = np.mean([train_eval(best, X[best][f.tr], y[f.tr], X[best][f.te], classes, s, adabn=True)
                      for s in SEEDS], 0)
        r["adabn_TRANSDUCTIVE_acc"] = float(np.mean(np.asarray(classes)[Pa.argmax(1)] == truth))
    return r


def main() -> int:
    IC.job_start(STAGE, device=os.environ.get("IDMAX_DEVICE", "cpu"))
    t0 = time.time()
    M = E.meta()
    y = M["y"].copy()
    X = inputs()
    IC.status(STAGE, f"device {device()}; inputs {[(k, v.shape) for k, v in X.items()]}")
    for arch, x in X.items():
        net = {"D1_protoMLP": MLP(feature_matrix().shape[1], 6),
               "D4_triplet": MLP(feature_matrix().shape[1], 6),
               "D2_cnn1d": CNN1D(21, 6), "D3_cnn2d": CNN2D(3, 6)}[arch]
        IC.status(STAGE, f"{arch}: {n_params(net)} parameters")
    ck = IC.Checkpoint(os.path.join(OUT, "checkpoint.jsonl"))
    out = {"stage": STAGE, "device": str(device()), "scopes": {}}
    for scope in ("pairings9", "WD_temporal"):
        res = []
        for f in E.scope_folds(M, y, scope):
            key = f"LEARNED|{f.tag}|final"
            if ck.has(key):
                res.append(ck.done[key]["r"])
                continue
            r = run_fold(f, y, X, ck)
            ck.put(key, {"r": r})
            res.append(r)
            IC.status(STAGE, f"{f.tag}: {r['config']} {100 * r['acc']:.1f} seeds "
                             f"{np.round(100 * np.asarray(r['seed_acc']), 1).tolist()} "
                             f"adabn {r.get('adabn_TRANSDUCTIVE_acc')}")
        if scope == "pairings9":
            loso = [r for r in res if r["tag"] in LOSO_TAGS]
            out["scopes"]["LOSO"] = E.summarise(loso, M, 100 / 6)
            out["scopes"]["LOSO"]["seed_mean_pct"] = round(100 * float(np.mean(
                [np.mean(r["seed_acc"]) for r in loso])), 2)
            out["scopes"]["LOSO"]["seed_sd_pct"] = round(100 * float(np.std(
                [np.mean([r["seed_acc"][s] for r in loso]) for s in range(5)])), 2)
            ad = [r for r in loso if "adabn_TRANSDUCTIVE_acc" in r]
            out["scopes"]["LOSO"]["adabn_TRANSDUCTIVE"] = (
                {r["tag"]: round(100 * r["adabn_TRANSDUCTIVE_acc"], 2) for r in ad} or None)
        s = E.summarise(res, M, 100 / 6)
        if scope.startswith("WD"):
            s["LABEL"] = E.WITHIN_DAY_LABEL
        out["scopes"][scope] = s
        IC.save_json(os.path.join(OUT, "results.json"), out)
    out["minutes"] = round((time.time() - t0) / 60, 2)
    IC.save_json(os.path.join(OUT, "results.json"), out)
    IC.status(STAGE, "done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
