# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: DC2 identification v2: the building blocks.

from __future__ import annotations

import copy

import numpy as np

HP = {
    "fs": 150.0, "stft": {"nperseg": 32, "noverlap": 24, "nfft": 64}, "band_hz": (4.0, 70.0), "n_freq": 28,
    "win_frames": 34, "hop_frames": 4,
    "channels": (16, 32, 32), "dropout": 0.3,
    "lr": 1e-3, "weight_decay": 1e-4, "batch": 64, "steps": 3000, "seeds": (0, 1, 2, 3, 4),
    "aug": {"time_mask_max": 4, "freq_mask_max": 2, "log_gain_sd": 0.2, "link_drop_p": 0.15, "noise_sd": 0.02},
    "prob_floor": 1e-9, "temperature_grid": (-1.0, 1.5, 61),
}
FREQS = np.fft.rfftfreq(HP["stft"]["nfft"], 1.0 / HP["fs"])
KEEP_F = (FREQS >= HP["band_hz"][0]) & (FREQS <= HP["band_hz"][1])
F_BINS = FREQS[KEEP_F]
assert KEEP_F.sum() == HP["n_freq"]
DIRS = ("A_fwd", "A_rev")



# (n, 103) amplitude of one link on the 150 Hz grid of one pass -> (28, n_frames): 4 to 70 Hz zero-phase...
def conditioned_map(a_link: np.ndarray) -> np.ndarray:
    from scipy import signal
    from pipeline.identify import idmax_features as F
    P = F.reduce_link(np.asarray(a_link, float), "dop", "pca", n_pc=4)[1:]
    s = HP["stft"]
    _f, _t, Z = signal.stft(P, fs=HP["fs"], nperseg=s["nperseg"], noverlap=s["noverlap"], nfft=s["nfft"],
                            axis=-1, boundary=None, padded=False)
    m = np.log(np.abs(Z).sum(axis=0)[KEEP_F] + 1e-6)
    return (m - m.mean()).astype(np.float32)


# (C, 28, n_frames) -> (n_windows, C, 28, win), from inside the pass only.
def windows(M: np.ndarray, win: int = HP["win_frames"], hop: int = HP["hop_frames"]) -> np.ndarray:
    n = M.shape[-1]
    if n < win:
        return np.empty((0,) + M.shape[:-1] + (win,), np.float32)
    return np.stack([M[..., s:s + win] for s in range(0, n - win + 1, hop)]).astype(np.float32)


# N1-f: the frequency axis rescaled so the pass's torso frequency f_t lands on f_ref: new(f) = old(f * f_t /...
def rescale_freq(M: np.ndarray, f_t: float, f_ref: float) -> np.ndarray:
    if not np.isfinite(f_t) or f_t <= 0:
        return M
    src = F_BINS * (f_t / f_ref)
    out = np.zeros_like(M)
    for c in range(M.shape[0]):
        for j in range(M.shape[-1]):
            out[c, :, j] = np.interp(src, F_BINS, M[c, :, j], left=0.0, right=0.0)
    return out



# Function torch.
def _torch():
    import torch
    return torch


# Function make net.
def make_net(c_in: int, n_cls: int):
    torch = _torch()
    nn = torch.nn
    c1, c2, c3 = HP["channels"]

    # Class CNNv2.
    class CNNv2(nn.Module):
        # Sets up the object.
        def __init__(self):
            super().__init__()
            self.f = nn.Sequential(
                nn.Conv2d(c_in, c1, 3, padding=1), nn.BatchNorm2d(c1), nn.ReLU(), nn.MaxPool2d((1, 2)),
                nn.Conv2d(c1, c2, 3, padding=1), nn.BatchNorm2d(c2), nn.ReLU(), nn.MaxPool2d((1, 2)),
                nn.Conv2d(c2, c3, 3, padding=1), nn.BatchNorm2d(c3), nn.ReLU())
            self.drop = nn.Dropout(HP["dropout"])
            self.head = nn.Linear(c3 * HP["n_freq"] + 2, n_cls)

        # Function forward.
        def forward(self, x, d):
            h = self.f(x).mean(-1).flatten(1)
            return self.head(self.drop(torch.cat([h, d], 1)))
    return CNNv2()


# Function n params.
def n_params(net) -> int:
    return int(sum(p.numel() for p in net.parameters()))


# Per link, per direction: mean and SD over the training windows (windows, frequency, time).
def norm_stats(Xw: np.ndarray, dirw: np.ndarray) -> dict:
    st = {}
    for k in (0, 1):
        sel = dirw == k
        if sel.any():
            st[k] = (Xw[sel].mean(axis=(0, 2, 3)), Xw[sel].std(axis=(0, 2, 3)) + 1e-6)
    for k in (0, 1):
        if k not in st:
            st[k] = st[1 - k]
    return st


# Function apply norm.
def apply_norm(Xw: np.ndarray, dirw: np.ndarray, st: dict) -> np.ndarray:
    out = np.empty_like(Xw)
    for k in (0, 1):
        sel = dirw == k
        mu, sd = st[k]
        out[sel] = (Xw[sel] - mu[None, :, None, None]) / sd[None, :, None, None]
    return out


# PER SAMPLE: a time mask of 0 to 4 frames, a frequency mask of 0 to 2 bins, a per-link log-gain offset ~...
def augment(x, g):
    torch = _torch()
    a = HP["aug"]
    B, C, Fq, T = x.shape
    dev = x.device
    wt = torch.randint(0, a["time_mask_max"] + 1, (B,), generator=g)
    st = (torch.rand(B, generator=g) * (T - wt + 1).float()).long()
    tt = torch.arange(T)
    mt = (tt[None, :] >= st[:, None]) & (tt[None, :] < (st + wt)[:, None])
    wf = torch.randint(0, a["freq_mask_max"] + 1, (B,), generator=g)
    sf = (torch.rand(B, generator=g) * (Fq - wf + 1).float()).long()
    ff = torch.arange(Fq)
    mf = (ff[None, :] >= sf[:, None]) & (ff[None, :] < (sf + wf)[:, None])
    keep = (~mt[:, None, None, :] & ~mf[:, None, :, None]).float().to(dev)
    x = x * keep
    x = x + a["log_gain_sd"] * torch.randn(B, C, 1, 1, generator=g).to(dev)
    if C > 1:
        drop = (torch.rand(B, C, generator=g) < a["link_drop_p"]).to(dev)
        x = x * (~drop).float()[:, :, None, None]
    return x + a["noise_sd"] * torch.randn(x.shape, generator=g).to(dev)


# (lr 1e-3, wd 1e-4), batch 64 windows, steps steps, cosine decay to 0, class-balanced sampling (a class...
def train_cnn(Xw: np.ndarray, yw: np.ndarray, dirw: np.ndarray, n_cls: int, seed: int, device: str = "cpu",
              steps: int = HP["steps"]):
    torch = _torch()
    torch.manual_seed(seed)
    g = torch.Generator().manual_seed(seed)
    net = make_net(Xw.shape[1], n_cls).to(device)
    opt = torch.optim.Adam(net.parameters(), lr=HP["lr"], weight_decay=HP["weight_decay"])
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=steps, eta_min=0.0)
    X = torch.tensor(Xw, dtype=torch.float32, device=device)
    D = torch.nn.functional.one_hot(torch.tensor(dirw, dtype=torch.long), 2).float().to(device)
    Y = torch.tensor(yw, dtype=torch.long, device=device)
    by = [torch.tensor(np.flatnonzero(yw == c)) for c in range(n_cls)]
    present = [c for c in range(n_cls) if len(by[c])]
    net.train()
    for _ in range(steps):
        cls = torch.tensor(present)[torch.randint(0, len(present), (HP["batch"],), generator=g)]
        r = torch.rand(HP["batch"], generator=g)
        idx = torch.stack([by[int(c)][int(r[i] * len(by[int(c)]))] for i, c in enumerate(cls)]).to(device)
        loss = torch.nn.functional.cross_entropy(net(augment(X[idx], g), D[idx]), Y[idx])
        opt.zero_grad()
        loss.backward()
        opt.step()
        sched.step()
    net.eval()
    return net


# (n_pass, n_cls): the mean log-softmax over each pass's windows.
def pass_logp(net, Xw: np.ndarray, dirw: np.ndarray, pass_of: np.ndarray, n_pass: int, n_cls: int,
              device: str = "cpu", chunk: int = 1024) -> np.ndarray:
    torch = _torch()
    net.eval()
    out = np.zeros((n_pass, n_cls))
    cnt = np.zeros(n_pass)
    with torch.no_grad():
        for s in range(0, len(Xw), chunk):
            x = torch.tensor(Xw[s:s + chunk], dtype=torch.float32, device=device)
            d = torch.nn.functional.one_hot(torch.tensor(dirw[s:s + chunk], dtype=torch.long), 2).float().to(device)
            lp = torch.log_softmax(net(x, d), 1).cpu().numpy()
            np.add.at(out, pass_of[s:s + chunk], lp)
            np.add.at(cnt, pass_of[s:s + chunk], 1)
    return out / np.maximum(cnt, 1)[:, None]


# A copy of net whose BatchNorm running statistics are recomputed, in ONE forward pass with no labels and no...
def adabn(net, Xw_other: np.ndarray, dirw_other: np.ndarray, device: str = "cpu"):
    torch = _torch()
    net2 = copy.deepcopy(net)
    bns = [m for m in net2.modules() if isinstance(m, torch.nn.BatchNorm2d)]
    for m in bns:
        m.reset_running_stats()
        m.momentum = None
    net2.eval()
    for m in bns:
        m.train()
    with torch.no_grad():
        x = torch.tensor(Xw_other, dtype=torch.float32, device=device)
        d = torch.nn.functional.one_hot(torch.tensor(dirw_other, dtype=torch.long), 2).float().to(device)
        net2(x, d)
    net2.eval()
    return net2


# Function normalise logp.
def normalise_logp(L: np.ndarray) -> np.ndarray:
    L = np.asarray(L, float)
    m = L.max(1, keepdims=True)
    return L - (m + np.log(np.exp(L - m).sum(1, keepdims=True)))


# Function logp from proba.
def logp_from_proba(P) -> np.ndarray:
    return normalise_logp(np.log(np.clip(np.asarray(P, float), HP["prob_floor"], 1.0)))



# N2-D's preparation.
def prep_day(Xtr, Xte, Xoth, ltr, lte, loth):
    from pipeline.identify import idmax_eval as E
    A, _B = E.prep(Xtr, Xte, ltr, lte, "perline_z")
    Xtr = np.array(Xtr, float)
    med = np.nanmedian(Xtr, axis=0)
    ok = np.isfinite(med)
    Xtr, Xte, Xoth, med = Xtr[:, ok], np.array(Xte, float)[:, ok], np.array(Xoth, float)[:, ok], med[ok]
    for X in (Xtr, Xte, Xoth):
        r, c = np.nonzero(~np.isfinite(X))
        X[r, c] = med[c]
    ok2 = Xtr.std(axis=0) > 1e-12
    Xte, Xoth = Xte[:, ok2], Xoth[:, ok2]
    mu_g, sd_g = Xoth.mean(0), Xoth.std(0)
    sd_g = np.where(sd_g > 1e-9, sd_g, 1.0)
    B = np.empty_like(Xte)
    for L in np.unique(lte):
        io = loth == L
        mu, s = (Xoth[io].mean(0), Xoth[io].std(0)) if io.sum() >= 3 else (mu_g, sd_g)
        s = np.where(s > 1e-9, s, sd_g)
        B[lte == L] = (Xte[lte == L] - mu) / s
    return A, B


# Function rf proba.
def rf_proba(A, B, y_tr):
    from pipeline.identify import idmax_eval as E
    clf = E.make_model("rf").fit(A, y_tr)
    return clf.predict_proba(B), [str(c) for c in clf.classes_]


# N3's Wi-Fi-sensed speed: v = f_t * lambda / (2 F), lambda from the channel ((2407 + 5 ch) MHz).
def v_hat(f_t: np.ndarray, channel: np.ndarray, F_rx2: float) -> np.ndarray:
    lam = 299_792_458.0 / ((2407.0 + 5.0 * np.asarray(channel, float)) * 1e6)
    return np.asarray(f_t, float) * lam / (2.0 * F_rx2)


# Shrinkage LDA on a feature matrix after the frozen prep (training-side imputation and z).
def lda_proba(xtr, xte, y_tr):
    from pipeline.identify import idmax_eval as E
    A, B = E.prep(np.asarray(xtr, float), np.asarray(xte, float), norm="none")
    clf = E.make_model("lda").fit(A, y_tr)
    return clf.predict_proba(B), [str(c) for c in clf.classes_]



# Function fit temperature.
def fit_temperature(L: np.ndarray, truth_idx: np.ndarray) -> float:
    lo, hi, n = HP["temperature_grid"]
    grid = np.logspace(lo, hi, int(n))
    best, bT = np.inf, 1.0
    for T in grid:
        z = normalise_logp(L / T)
        nll = -z[np.arange(len(truth_idx)), truth_idx].sum()
        if nll < best:
            best, bT = nll, float(T)
    return bT


# One decision per group of passes (index arrays): the argmax of the summed log-probabilities.
def group_decisions(L: np.ndarray, groups: list, classes: list) -> list:
    return [classes[int(L[np.asarray(g)].sum(0).argmax())] for g in groups]


# Function pass bootstrap.
def pass_bootstrap(correct: np.ndarray, n: int = 1000, seed: int = 0) -> list:
    rng = np.random.default_rng(seed)
    c = np.asarray(correct, float)
    b = [c[rng.integers(0, len(c), len(c))].mean() for _ in range(n)]
    return [round(100 * float(np.percentile(b, 2.5)), 2), round(100 * float(np.percentile(b, 97.5)), 2)]


# Spearman of pair accuracy against the pair's time gap, with a ONE-SIDED permutation p for a positive...
def spearman_gap_test(acc: np.ndarray, gap: np.ndarray, day: np.ndarray, n_perm: int = 10000, seed: int = 0) -> dict:
    from scipy.stats import spearmanr
    acc, gap, day = np.asarray(acc, float), np.asarray(gap, float), np.asarray(day)
    rho = float(spearmanr(acc, gap).correlation)
    rng = np.random.default_rng(seed)
    null = []
    for _ in range(n_perm):
        g = gap.copy()
        for d in np.unique(day):
            ix = np.flatnonzero(day == d)
            g[ix] = g[rng.permutation(ix)]
        null.append(spearmanr(acc, g).correlation)
    null = np.nan_to_num(np.asarray(null, float), nan=0.0)
    rho0 = 0.0 if not np.isfinite(rho) else rho
    return {"spearman": round(rho0, 3), "p_one_sided_positive": round(float((1 + np.sum(null >= rho0)) / (1 + n_perm)), 4),
            "n_points": int(len(acc))}


# Which slot's empty room a window came from: z-score from the training windows, shrinkage LDA.
def empty_room_recognition(Xtr, ytr, Xte, yte, n_perm: int = 1000, seed: int = 0) -> dict:
    from pipeline.identify import idmax_eval as E
    Xtr, Xte = np.asarray(Xtr, float), np.asarray(Xte, float)
    mu, sd = Xtr.mean(0), Xtr.std(0)
    k = sd > 1e-9
    clf = E.make_model("lda").fit(((Xtr - mu) / np.where(k, sd, 1))[:, k], ytr)
    pred = clf.predict(((Xte - mu) / np.where(k, sd, 1))[:, k])
    yte = np.asarray(yte)
    obs = float(np.mean(pred == yte))
    rng = np.random.default_rng(seed)
    labs = np.unique(yte)
    null = []
    for _ in range(n_perm):
        m = dict(zip(labs, rng.permutation(labs)))
        null.append(np.mean(pred == np.array([m[v] for v in yte])))
    null = np.asarray(null)
    return {"acc_pct": round(100 * obs, 2), "n_windows": int(len(yte)), "chance_pct": round(100 / len(labs), 2),
            "null_p95_pct": round(100 * float(np.percentile(null, 95)), 2),
            "perm_p": round(float((1 + np.sum(null >= obs)) / (1 + n_perm)), 4),
            "EXCEEDS_NULL_P95": bool(obs > np.percentile(null, 95))}
