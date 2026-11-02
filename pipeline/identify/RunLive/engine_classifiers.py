# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The engine's models: training and applying the five components and their priors, and the calibration that...

from __future__ import annotations

import os

import numpy as np


CLASSES = ("P1", "P2", "P3", "P4", "P5", "P6")
COMPONENTS = ("rf", "rf_prior", "rf_pace_prior", "et_pace_prior", "lda_pace_prior", "cnn", "cnn_prior",
              "cnn_perlink_prior")
PACE_COMPONENTS = ("rf_pace_prior", "et_pace_prior", "lda_pace_prior")
FEAT = {"rf": ("rf", "perpath", False), "rf_prior": ("rf", "prior", False), "rf_pace_prior": ("rf", "prior", True),
        "et_pace_prior": ("et", "prior", True), "lda_pace_prior": ("lda", "prior", True)}



# Idx_dev.prior_standardise, split into fit (training side) and apply (per calibration group).
class Prior:

    # Function fit.
    def fit(self, Xtr, ptr, str_):
        Xtr = np.array(Xtr, float)
        med = np.nanmedian(Xtr, axis=0)
        self.ok = np.isfinite(med)
        self.med = med[self.ok]
        Z = self._impute(Xtr)
        self.keep = Z.std(axis=0) > 1e-12
        Z = Z[:, self.keep]
        self.g_mu, self.g_sd = Z.mean(0), Z.std(0) + 1e-9
        A = np.empty_like(Z)
        for s in np.unique(str_):
            m = str_ == s
            A[m] = self.zs(Z[m], ptr[m], Z[m], ptr[m])
        return A

    # Function impute.
    def _impute(self, Xr):
        Z = np.array(Xr, float)[:, self.ok]
        r, c = np.nonzero(~np.isfinite(Z))
        Z[r, c] = self.med[c]
        return Z

    # Function Z.
    def Z(self, Xr):
        return self._impute(Xr)[:, self.keep]

    # Function zs.
    def zs(self, Zrows, prows, Zref, pref):
        out = np.empty_like(Zrows)
        for p in np.unique(prows):
            m = prows == p
            rr = pref == p
            if rr.sum() < 3:
                rr = np.ones(len(pref), bool)
            mu, sd = Zref[rr].mean(0), Zref[rr].std(0)
            out[m] = (Zrows[m] - mu) / np.where(sd > 1e-9, sd, self.g_sd)
        return out

    # Function apply.
    def apply(self, Xall, paths, rows, calib):
        Zr = self.Z(Xall[rows])
        if calib is not None and len(calib) >= 10:
            return self.zs(Zr, paths[rows], self.Z(Xall[calib]), paths[calib])
        return (Zr - self.g_mu) / self.g_sd



# Function load net.
def _load_net(path, c_in):
    import torch
    net = make_net(c_in, 6)
    net.load_state_dict(torch.load(path, map_location="cpu"))
    return net.eval()


from dataclasses import dataclass

_FEAT_CACHE: dict = {}


# Function load variant.
def load_variant(variant: str) -> dict:
    if variant == "S0_ORACLE_SPEED" and variant not in _FEAT_CACHE:
        inv = IC.pass_inventory()
        X = np.array([[r["speed_m_s"]] for r in inv], float)
        _FEAT_CACHE[variant] = {"X": X, "names": ["S0|-|-|-|speed"], "fam": np.array(["S0"]),
                                "rb": np.array(["-"]), "link": np.array(["-"]),
                                "chan": np.array(["-"]), "nm": np.array(["speed"]),
                                "keys": [IC.pass_key(r) for r in inv]}
    if variant not in _FEAT_CACHE:
        d = np.load(os.path.join(IC.FEAT, f"{variant}.npz"), allow_pickle=False)
        names = [str(x) for x in d["names"]]
        parts = [n.split("|") for n in names]
        _FEAT_CACHE[variant] = {"X": d["X"].astype(np.float64), "names": names,
                                "fam": np.array([p[0] for p in parts]),
                                "rb": np.array([p[1] for p in parts]),
                                "link": np.array([p[2] for p in parts]),
                                "chan": np.array([p[3] for p in parts]),
                                "nm": np.array([p[4] for p in parts]),
                                "keys": [str(k) for k in d["keys"]]}
    return _FEAT_CACHE[variant]


FEATURE_SETS = {
    "B1_rhythm": lambda ch: [("cad", None), ("rhy", ch, "scalar")],
    "B2_acfshape": lambda ch: [("rhy", ch, "acfshape")],
    "B3_templates": lambda ch: [("tplacf", ch, None)],
    "B3p_templates_peaks": lambda ch: [("tplpeaks", ch, None)],
    "B4_spectral": lambda ch: [("spec", ch, None)],
    "B5_doppler": lambda ch: [("dop", "pca-pc1@w0.1", None), ("dop", "pca-pc1@w0.2", None),
                              ("dop", "pca-pc1@w0.43", None)],
    "B5k_doppler_keep_pc1": lambda ch: [("dop", "pca+pc1@w0.1", None),
                                        ("dop", "pca+pc1@w0.2", None),
                                        ("dop", "pca+pc1@w0.43", None)],
    "B6_wavelet": lambda ch: [("wav", None, None)],
    "B7_handcrafted": lambda ch: [("cad", None), ("rhy", ch, "scalar"),
                                  ("dop", "pca-pc1@w0.2", "scalar"), ("mod", None, None),
                                  ("tplacf", ch, "scalar")],
    "B8_linkmod": lambda ch: [("tplacf", ch, None), ("mod", None, None), ("prof", None, None)],
    "U_rhythm_shape": lambda ch: [("cad", None), ("rhy", ch, None), ("tplacf", ch, None)],
    "U_env_spec": lambda ch: [("cad", None), ("rhy", ch, "scalar"), ("spec", ch, None),
                              ("dop", "pca-pc1@w0.2", None)],
    "U_all_gait": lambda ch: [("cad", None), ("rhy", ch, None), ("tplacf", ch, None),
                              ("spec", ch, None), ("dop", "pca-pc1@w0.2", None),
                              ("wav", None, None), ("mod", None, None)],
    "RECSIG": lambda ch: [("RECSIG", None, None)],
    "S0": lambda ch: [("S0", None, None)],
}


LINK_SETS = {"all": ("RX1", "RX2", "RX3"), "noRX1": ("RX2", "RX3"), "noRX2": ("RX1", "RX3"),
             "noRX3": ("RX1", "RX2"), "RX1": ("RX1",), "RX2": ("RX2",), "RX3": ("RX3",)}


PC_OPTS = {"pc1-3": (0, 1, 2), "pc2-4": (1, 2, 3), "pc1-6": (0, 1, 2, 3, 4, 5), "pc2-6": (1, 2, 3, 4, 5),
           "pc1": (0,)}


# Class FConf.
@dataclass(frozen=True)
class FConf:
    variant: str
    fset: str
    ch: str = "mean@b08_35"
    links: str = "all"
    pc: str = "pc1-3"
    norm: str = "none"

    # Function tag.
    def tag(self) -> str:
        return f"{self.variant}/{self.fset}/{self.ch}/{self.links}/{self.pc}/{self.norm}"


_MASK_CACHE: dict = {}


# Function eval columns.
def eval_columns(fc: FConf) -> np.ndarray:
    k = (fc.variant, fc.fset, fc.ch, fc.links, fc.pc)
    if k in _MASK_CACHE:
        return _MASK_CACHE[k]
    V = load_variant(fc.variant)
    links = set(LINK_SETS[fc.links]) | {"-"}
    m = np.zeros(len(V["names"]), bool)
    for spec in FEATURE_SETS[fc.fset](fc.ch):
        fam = spec[0]
        rb = spec[1] if len(spec) > 1 else None
        sub = spec[2] if len(spec) > 2 else None
        mm = V["fam"] == fam
        if rb is not None:
            mm &= V["rb"] == rb
        if sub == "scalar":
            mm &= ~np.char.startswith(V["nm"], "acfshape") & ~np.char.startswith(V["nm"], "tpl_") \
                  & ~np.char.startswith(V["nm"], "tplharm") & ~np.char.startswith(V["nm"], "uprof") \
                  & ~np.char.find(V["nm"], "_cyc").__ge__(0)
        elif sub == "acfshape":
            mm &= np.char.startswith(V["nm"], "acfshape")
        m |= mm
    m &= np.isin(V["link"], list(links))
    ispca = np.char.startswith(V["rb"], "pca@")
    if ispca.any():
        allowed = {str(i) for i in PC_OPTS[fc.pc]}
        m &= ~ispca | np.isin(V["chan"], list(allowed))
    idx = np.flatnonzero(m)
    _MASK_CACHE[k] = idx
    return idx


import copy

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


# (C, 28, n_frames) -> (n_windows, C, 28, win), from inside the pass only.
def windows(M: np.ndarray, win: int = HP["win_frames"], hop: int = HP["hop_frames"]) -> np.ndarray:
    n = M.shape[-1]
    if n < win:
        return np.empty((0,) + M.shape[:-1] + (win,), np.float32)
    return np.stack([M[..., s:s + win] for s in range(0, n - win + 1, hop)]).astype(np.float32)


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


# Make the bank a feature variant of the frozen idmax_eval, so its column sets select by name.
def register_variant(variant: str, X: np.ndarray, names: list) -> None:
    parts = [n.split("|") for n in names]
    _FEAT_CACHE[variant] = {"X": X, "names": names, "fam": np.array([p[0] for p in parts]),
                              "rb": np.array([p[1] for p in parts]), "link": np.array([p[2] for p in parts]),
                              "chan": np.array([p[3] for p in parts]), "nm": np.array([p[4] for p in parts]),
                              "keys": [str(i) for i in range(len(X))]}
    _MASK_CACHE.clear()


# Function loso columns.
def loso_columns(fset: str, variant: str = "dev", links: str = "all") -> np.ndarray:
    return eval_columns(FConf(variant, fset, "mean@b08_35", links, "pc1-3", "perline_z"))


# Function order.
def _order(L, cl):
    out = np.full((L.shape[0], 6), np.log(HP["prob_floor"]))
    for j, c in enumerate(cl):
        out[:, CLASSES.index(str(c))] = L[:, j]
    return normalise_logp(out)


# Function apply norm keyed.
def apply_norm_keyed(Xw, dw, lw, st) -> np.ndarray:
    out = np.empty_like(Xw)
    for k in (0, 1):
        for lay in (np.unique(lw) if lw is not None else ["*"]):
            sel = (dw == k) & ((lw == lay) if lw is not None else True)
            if not np.any(sel):
                continue
            mu, sd = st.get((lay, k), st[("*", k)])
            out[sel] = (Xw[sel] - mu[None, :, None, None]) / sd[None, :, None, None]
    return out


import pipeline.identify.RunLive.engine_session_replay as IC
