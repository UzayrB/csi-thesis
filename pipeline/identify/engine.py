# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The one-press identification engine.

from __future__ import annotations

import json
import os
import pickle
import time

import numpy as np


T_S = 4.0
CAP_S = 1.0
CLOCK_WIN_S = 20.0
CLOCK_MIN = 20
CLOCK_PCT = 5.0
WRAP_S = 2.0 ** 32 * 1e-6
WRAP_EDGE_S = 5.0
JUMP_S = 1.0
KEEP_S = 60.0
FS = 150.0
LAMBDA = 0.123
F_MIN = 0.3
DIR_BAND = (10.0, 35.0)
MIN_FEAT_CALIB = 10
LINKS = ("RX1", "RX2", "RX3")
CLASSES = ("P1", "P2", "P3", "P4", "P5", "P6")
LABEL = "development evaluation, all data seen"
FEATURE_WEIGHT = 1.0
ENG = os.path.join("runs", "identify", "engine")
DEV_NAMES = os.path.join("runs", "identify", "dev", "bank", "feature_names.json")






V5S_CNN_TAGS = {"cnn": ("cnn3",), "cnn_prior": ("cnn3",), "cnn_perlink_prior": ("cnn_link0", "cnn_link1", "cnn_link2")}

ENGINE_VERSION = 4
SUFFIX = "_v4"
DIR_T_S = 3.0
DET_STEP_S = 0.25
DET_REF_S, DET_MIN_S, DET_RUN = 2.5, 2.5, 10
DET_HOP_S, DET_C0_S = 8.0 / 150.0, 16.0 / 150.0
CADENCE_VOTE_MIN_ACF = 0.30


# Function bank dir.
def bank_dir(T: float = T_S) -> str:
    return os.path.join(ENG, f"bank_T{T:.1f}{SUFFIX}")


# Function model name.
def model_name(base: str) -> str:
    return base + SUFFIX


# Function replay name.
def replay_name(model: str, session: str, T: float = T_S) -> str:
    return f"{model}_{session}_T{T:.1f}"


# Idmax_features.resolve_cadence with only rhythm-bearing channels voting (acf peak >= 0.30); if none...
def resolve_cadence_v2(estimate_sets: list) -> dict:
    from pipeline.identify import idmax_features as F
    strong = [e for e in estimate_sets if e.get("acf_peak") is not None and e["acf_peak"] >= CADENCE_VOTE_MIN_ACF]
    return _RESOLVE_V1(strong if strong else estimate_sets)


# Engine v3 (fix F): as v2, but when no channel's autocorrelation peak reaches 0.30 the window has no...
def resolve_cadence_v3(estimate_sets: list) -> dict:
    strong = [e for e in estimate_sets if e.get("acf_peak") is not None and e["acf_peak"] >= CADENCE_VOTE_MIN_ACF]
    if not strong:
        return {"cadence_hz": None, "agree_frac": 0.0, "n_estimates": 0}
    return _RESOLVE_V1(strong)


# Function v1.
def _v1():
    from pipeline.identify import idmax_features as F
    return F.resolve_cadence


_RESOLVE_V1 = _v1()


# Scoped swap: the engine's gait features use the v2 resolver; every other caller keeps the frozen v1.
class _cadence_v2:

    # Enters the context.
    def __enter__(self):
        from pipeline.identify import idmax_features as F
        self._saved = F.resolve_cadence
        F.resolve_cadence = resolve_cadence_v2

    # Leaves the context.
    def __exit__(self, *exc):
        from pipeline.identify import idmax_features as F
        F.resolve_cadence = self._saved
        return False


# Scoped swap: the engine's gait features use the v3 resolver (fix F); every other caller keeps the frozen v1.
class _cadence_v3(_cadence_v2):

    # Enters the context.
    def __enter__(self):
        from pipeline.identify import idmax_features as F
        self._saved = F.resolve_cadence
        F.resolve_cadence = resolve_cadence_v3



# Function rigs.
def _rigs() -> dict:
    from pipeline.identify.idgp_contract import RIG_DC2_IDSPOT, RIG_ROOM_A
    return {"home": RIG_ROOM_A, "id_spot": RIG_DC2_IDSPOT["primary"]}


# Idw_physics.mean_F for a layout: the mean projected bistatic factor over 101 points of the path.
def mean_F(link: str, path: str, layout: str) -> float:
    from pipeline.identify.id15_factor_map import bistatic_factor
    from pipeline.identify.idgp_contract import PATHS
    rig = _rigs()[layout]
    a, b = (np.asarray(x, float) for x in PATHS[path])
    u = np.linspace(0, 1, 101)
    pts = a[None, :] + u[:, None] * (b - a)[None, :]
    return float(np.mean(bistatic_factor(pts, b - a, rig["TX"], rig[link])))


_BEST = {}


# (link index, F) of the link with the largest mean F for this path and layout.
def best_link(path: str, layout: str) -> tuple:
    key = (path, layout)
    if key not in _BEST:
        f = [mean_F(L, path, layout) for L in LINKS]
        _BEST[key] = (int(np.argmax(f)), float(np.max(f)))
    return _BEST[key]



# One receiver's frames in arrival order, with epochs (reboots) and unwrapped local time.
class Receiver:

    # Sets up the object.
    def __init__(self):
        self._chunks = []
        self.tm = np.empty(0)
        self.lt = np.empty(0)
        self.ep = np.empty(0, int)
        self.amp = np.empty((0, 103), np.float32)
        self.rssi = np.empty(0, np.float32)
        self.prev_raw = None
        self.epoch = 0
        self.wraps = 0
        self.n_wraps = 0
        self.n_reboots = 0

    # A structured capture-frame array (FRAME_DTYPE fields t_mono, local_timestamp, rssi, data), in arrival order.
    def push(self, fr) -> None:
        if not len(fr):
            return
        from pipeline.identify.id19_bank import KEEP
        from pipeline.identify.id19_featbank import SC
        from pipeline.identify.raw_access import amplitude_from_frames
        raw = np.asarray(fr["local_timestamp"], np.float64) * 1e-6
        tm = np.asarray(fr["t_mono"], np.float64)
        ep = np.empty(len(raw), int)
        lt = np.empty(len(raw))
        prev = self.prev_raw
        start = 0
        prevs = np.r_[prev if prev is not None else raw[0], raw[:-1]]
        jumps = np.flatnonzero(raw - prevs < -JUMP_S)
        for j in list(jumps) + [len(raw)]:
            ep[start:j] = self.epoch
            lt[start:j] = raw[start:j] + self.wraps * WRAP_S
            if j == len(raw):
                break
            p = prevs[j]
            if p > WRAP_S - WRAP_EDGE_S and raw[j] < WRAP_EDGE_S:
                self.wraps += 1
                self.n_wraps += 1
            else:
                self.epoch += 1
                self.wraps = 0
                self.n_reboots += 1
            start = j
        self.prev_raw = float(raw[-1])
        a = amplitude_from_frames(fr)[:, KEEP][:, SC].astype(np.float32)
        self._chunks.append((tm, lt, ep, a, np.asarray(fr["rssi"], np.float32)))

    # Drop whole blocks that arrived entirely before before (idle housekeeping; no copying).
    def drop_old(self, before: float) -> None:
        if len(self.tm) and self.tm[-1] < before:
            self.tm, self.lt, self.ep, self.amp, self.rssi = (x[:0] for x in (self.tm, self.lt, self.ep, self.amp, self.rssi))
        while self._chunks and self._chunks[0][0][-1] < before and not len(self.tm):
            self._chunks.pop(0)

    # Function consolidate.
    def consolidate(self, trim_before: float = None) -> None:
        if self._chunks:
            parts = [(self.tm, self.lt, self.ep, self.amp, self.rssi)] + self._chunks
            self.tm, self.lt, self.ep, self.amp, self.rssi = (np.concatenate([p[k] for p in parts]) for k in range(5))
            self._chunks = []
        if trim_before is not None and len(self.tm) and self.tm[0] < trim_before:
            k = int(np.searchsorted(self.tm, trim_before, side="left"))
            self.tm, self.lt, self.ep, self.amp, self.rssi = (x[k:] for x in (self.tm, self.lt, self.ep, self.amp, self.rssi))

    # Indices of the frames of the current epoch (at tau) that arrived by tau.
    def arrived(self, tau: float) -> np.ndarray:
        n = int(np.searchsorted(self.tm, tau, side="right"))
        if n == 0:
            return np.empty(0, int)
        k0 = int(np.searchsorted(self.ep[:n], self.ep[n - 1], side="left"))
        return np.arange(k0, n)

    # The causal offset at tau, or None (fewer than 20 frames: use t_mono).
    def offset(self, tau: float, idx: np.ndarray):
        if not len(idx):
            return None
        w = idx[self.tm[idx] > tau - CLOCK_WIN_S]
        if len(w) < CLOCK_MIN:
            return None
        return float(np.percentile(self.tm[w] - self.lt[w], CLOCK_PCT))

    # Function last time.
    def last_time(self, tau: float) -> float:
        idx = self.arrived(tau)
        if not len(idx):
            return -np.inf
        off = self.offset(tau, idx)
        return float(self.lt[idx].max() + off) if off is not None else float(self.tm[idx].max())

    # (t_hat, amplitude (n, 103), rssi) of the frames arrived by tau, timed by the clock at tau, sorted.
    def timed(self, tau: float) -> tuple:
        idx = self.arrived(tau)
        off = self.offset(tau, idx)
        t = self.lt[idx] + off if off is not None else self.tm[idx]
        o = np.argsort(t, kind="stable")
        return t[o], self.amp[idx][o], self.rssi[idx][o]



# Direction and Wi-Fi speed from the window's raw amplitude (3, n, 103), identity-blind.
def signal_measures(A_raw: np.ndarray, path: str, layout: str) -> dict:
    from pipeline.identify import id29_dc2_score as D
    from pipeline.identify import rehearsal_doppler_check as RD
    f, P = RD.conditioned_spectrogram(A_raw[1])
    out = {"dir_slope": float("nan"), "dir_detected": None}
    if P.shape[1] >= 2:
        m = (f >= DIR_BAND[0]) & (f < DIR_BAND[1])
        e = np.log10(P[m].sum(axis=0) + 1e-12)
        k = np.arange(len(e), dtype=float)
        slope = float(np.polyfit(k, e, 1)[0])
        out["dir_slope"] = slope
        out["dir_detected"] = "A_fwd" if slope < 0 else "A_rev"
    use = path if path is not None else (out["dir_detected"] or "A_fwd")
    li, F = best_link(use, layout)
    out.update({"path": use, "speed_link": LINKS[li], "speed_F": F})
    if F < F_MIN:
        out.update({"f_torso": float("nan"), "wifi_speed": float("nan")})
    else:
        ft = D.torso_hz(A_raw[li])
        out.update({"f_torso": ft, "wifi_speed": float(ft * LAMBDA / (2.0 * F)) if np.isfinite(ft) else float("nan")})
    return out


# The window's features (in names order), maps, direction and speed, from each receiver's (t_hat, amplitude...
def extract_window(timed: list, t0: float, T: float, amp_norm: bool, path, layout: str, names: list) -> dict:
    from pipeline.identify import id19_featbank as FB
    from pipeline.identify import idz_bank as ZB
    from pipeline.identify.id19_bank import _interp_cols
    c0 = time.perf_counter()
    grid = np.arange(t0, t0 + T, 1.0 / FS)
    A_raw = np.asarray([_interp_cols(grid, t, a.astype(np.float64)) for t, a, _r in timed], np.float64)
    R = np.asarray([_interp_cols(grid, t, r.astype(np.float64)) for t, _a, r in timed], np.float64)
    if amp_norm:
        A = np.asarray([_interp_cols(grid, t, a.astype(np.float64) / np.maximum(a.astype(np.float64).mean(axis=1, keepdims=True), 1e-9))
                        for t, a, _r in timed], np.float64)
    else:
        A = A_raw
    with (_cadence_v3() if ENGINE_VERSION >= 3 else _cadence_v2()):
        feats = FB.pass_features(A, R)
    fv = np.array([feats.get(n, np.nan) if feats.get(n) is not None else np.nan for n in names], np.float64)
    fv[~np.isfinite(fv)] = np.nan
    maps = np.stack([ZB.conditioned_map_v2(A[li]) for li in range(3)]).astype(np.float32)
    sm = signal_measures(A_raw, path, layout)
    return {"features": fv.astype(np.float32), "maps": maps, **sm, "layout": layout, "n_frames": [int(len(t)) for t, _a, _r in timed],
            "extract_s": time.perf_counter() - c0}


# The stream side: three receivers, open windows, and extraction.
class Extractor:

    # Sets up the object.
    def __init__(self, T: float = T_S, amp_norm: bool = False, layout: str = "id_spot", names: list = None,
                 alpha: float = None, rx: dict = None, cut: bool = True):
        self.T, self.amp_norm, self.layout = float(T), bool(amp_norm), layout
        self.alpha = alpha
        self.names = names if names is not None else json.load(open(DEV_NAMES))
        self.rx = rx if rx is not None else {L: Receiver() for L in LINKS}
        self.cut = cut
        self.pending = []
        self.newest = -np.inf

    # Function push.
    def push(self, link: str, frames) -> None:
        self.rx[link].push(frames)
        if len(frames):
            self.newest = max(self.newest, float(np.max(frames["t_mono"])))

    # Function press.
    def press(self, t0: float, path=None, layout=None, info=None) -> None:
        if ENGINE_VERSION >= 4 and self.cut and self.pending and self.pending[-1]["t0"] + self.T > float(t0) > self.pending[-1]["t0"]:
            self.pending[-1]["end"] = float(t0)
            self.pending[-1].pop("checked", None)
        self.pending.append({"t0": float(t0), "path": path, "layout": layout or self.layout, "info": info or {}})

    # Function end.
    def _end(self, w: dict) -> float:
        return w.get("end", w["t0"] + self.T)

    # The engine's decision rule for any window end, on every frame that has arrived (engine v4's checkpoints).
    def t_dec_end(self, t0: float, end: float) -> float:
        cap = end + CAP_S
        cand = np.unique(np.concatenate([r.tm[(r.tm > t0) & (r.tm <= cap)] for r in self.rx.values()]))
        for tau in cand:
            if all(r.last_time(tau) > end for r in self.rx.values()):
                return float(tau)
        return float(cap)

    # Function raw.
    def _raw(self, t0: float, end: float, td: float) -> np.ndarray:
        from pipeline.identify.id19_bank import _interp_cols
        grid = np.arange(t0, end, 1.0 / FS)
        return np.asarray([_interp_cols(grid, t, a.astype(np.float64)) for t, a, _r in [self.rx[L].timed(td) for L in LINKS]],
                          np.float64)

    # The decision time if it has come by now, else None.
    def _t_dec(self, w: dict, now: float):
        t0, end = w["t0"], self._end(w)
        cap = end + CAP_S
        lo = w.get("checked", t0)
        hi = min(now, cap)
        if hi > lo:
            cand = np.unique(np.concatenate([r.tm[(r.tm > lo) & (r.tm <= hi)] for r in self.rx.values()]))
            for tau in cand:
                if all(r.last_time(tau) > end for r in self.rx.values()):
                    return float(tau)
            w["checked"] = hi
        return cap if now >= cap else None

    # Windows decided by now, in press order: [(window, t_dec, extraction)].
    def poll(self, now: float, closing: bool = False) -> list:
        if not self.pending:
            for r in self.rx.values():
                r.drop_old(self.newest - KEEP_S)
            return []
        for r in self.rx.values():
            r.consolidate(trim_before=self.newest - KEEP_S)
        out = []
        while self.pending:
            w = self.pending[0]
            td = self._t_dec(w, np.inf if closing else now)
            if td is None:
                break
            timed = [self.rx[L].timed(td) for L in LINKS]
            if self.T > DIR_T_S:
                ex = self.extract_v4(w, td, timed)
            else:
                ex = extract_window(timed, w["t0"], self._end(w) - w["t0"] if "end" in w else self.T, self.amp_norm,
                                    w["path"], w["layout"], self.names)
            self.pending.pop(0)
            out.append((w, td, ex))
        return out

    # Engine v4's window: the direction from its first 3 s; the walking span from RX2's torso-band energy at...
    def extract_v4(self, w: dict, td: float, timed: list) -> dict:
        from pipeline.identify import id29_dc2_score as D
        t0, end = w["t0"], self._end(w)
        layout = w["layout"]
        e3 = min(t0 + DIR_T_S, end)
        sm3 = signal_measures(self._raw(t0, e3, self.t_dec_end(t0, e3)), w["path"], layout)
        path = sm3["path"]
        walk_end = end
        if self.alpha is not None:
            series = []
            for c in np.round(np.arange(DIR_T_S, self.T + 1e-9, DET_STEP_S), 2):
                ec = min(t0 + c, end)
                series.append((float(ec - t0), band_energy_rx2(self._raw(t0, ec, self.t_dec_end(t0, ec))[1])))
                if ec < t0 + c:
                    break
            d = detect_end(series, self.alpha, upto=self.T)
            if d is not None:
                walk_end = min(t0 + d[0], end)
        T_win = self.T if end == t0 + self.T else end - t0
        x = extract_window(timed, t0, T_win, self.amp_norm, path, layout, self.names)
        A = self._raw(t0, end, td)
        li, F = best_link(path, layout)
        nw = int(np.searchsorted(np.arange(t0, end, 1.0 / FS), walk_end, side="left"))
        ft = D.torso_hz(A[li][:nw]) if nw >= 64 else float("nan")
        v = float(ft * LAMBDA / (2.0 * F)) if (F >= F_MIN and np.isfinite(ft)) else float("nan")
        x.update({"path": path, "dir_detected": sm3["dir_detected"], "dir_slope": sm3["dir_slope"], "speed_link": LINKS[li],
                  "speed_F": F, "f_torso": ft, "wifi_speed": v, "walk_end_s": walk_end - t0, "alpha": self.alpha,
                  "window_s": end - t0})
        return x


# Per frame, RX2's conditioned spectrogram summed over the direction band (10 <= f < 35 Hz).
def band_energy_rx2(a_rx2: np.ndarray) -> np.ndarray:
    from pipeline.identify import rehearsal_doppler_check as RD
    f, P = RD.conditioned_spectrogram(a_rx2)
    m = (f >= DIR_BAND[0]) & (f < DIR_BAND[1])
    return P[m].sum(axis=0)


# Engine v4's end detector (iwg_bank.detect): per checkpoint c, the frame energies of [t0, t0 + c]; the...
def detect_end(series: list, alpha: float, upto: float):
    for c, e in series:
        if c > upto + 1e-9:
            break
        tc = DET_C0_S + DET_HOP_S * np.arange(len(e))
        ref = np.median(e[tc <= DET_REF_S]) if np.any(tc <= DET_REF_S) else np.nan
        if not np.isfinite(ref) or ref <= 0:
            continue
        low = e < alpha * ref
        for i in np.flatnonzero(low & (tc >= DET_MIN_S) & (tc <= 6.0)):
            if i + DET_RUN <= len(e) and low[i:i + DET_RUN].all():
                return float(tc[i]), float(c)
    return None



# A trained ensemble (idz_core.train's saved files), applied one window at a time.
class Model:

    # Sets up the object.
    def __init__(self, model_dir: str, device: str = "cpu", names: list = None):
        from pipeline.identify import idw_core as W
        from pipeline.identify import idz_core as Z
        man_p = os.path.join(model_dir, "manifest.json")
        man = json.load(open(man_p)) if os.path.exists(man_p) else {}
        if man.get("v5s"):
            self._init_v5s(model_dir, device, names, man)
            return
        self.v5s = None
        self.states = {}
        self.dir, self.device = model_dir, device
        meta_p = os.path.join(model_dir, "meta_feat_cnn.json")
        self.meta = json.load(open(meta_p))
        self.cfg = self.meta["cfg"]
        assert not self.cfg.get("layout") and not self.cfg.get("fn") and self.cfg.get("cols", "v2") == "v2", self.cfg
        self.names = names if names is not None else json.load(open(DEV_NAMES))
        self.cols = v2_columns(self.names)
        self.feat = {c: pickle.load(open(os.path.join(model_dir, f"feat_{c}.pkl"), "rb")) for c in W.FEAT}
        man_p = os.path.join(model_dir, "manifest.json")
        self.manifest = json.load(open(man_p)) if os.path.exists(man_p) else {}
        self.version = int(self.manifest.get("engine_version", ENGINE_VERSION))
        self.extra_feat = ()
        if self.version >= 5:
            v5 = self.manifest["v5"]
            refuse_room_weights(model_dir, v5)
            self.extra_feat = tuple(v5["extra_feature_components"])
            for c in self.extra_feat:
                self.feat[c] = pickle.load(open(os.path.join(model_dir, f"feat_{c}.pkl"), "rb"))
            self.offsets = tuple(float(o) for o in v5["offsets"])
        self.nets, self.norm = {}, {}
        for chan in (None, 0, 1, 2):
            tag = "cnn3" if chan is None else f"cnn_link{chan}"
            self.norm[tag] = pickle.load(open(os.path.join(model_dir, f"{tag}_norm.pkl"), "rb"))
            for s in self.meta["seeds"]:
                self.nets[(tag, s)] = W._load_net(os.path.join(model_dir, f"{tag}_seed{s}.pt"), 3 if chan is None else 1).to(device)
        self.components = Z.COMPONENTS
        self.pace = Z.PACE_COMPONENTS
        if self.version >= 5:
            self.feat_components = tuple(W.FEAT) + self.extra_feat
            self.cnn_components = tuple(c for c in Z.COMPONENTS if c not in W.FEAT)
            self.components = self.feat_components + self.cnn_components
            self.pace = tuple(Z.PACE_COMPONENTS) + tuple(c for c in self.extra_feat
                                                         if W.FEAT[self.feat[c]["state_of"]][2])

    # Engine v5s: the model with only the members its manifest names; no other component's file is opened.
    def _init_v5s(self, model_dir: str, device: str, names: list, man: dict) -> None:
        from pipeline.identify import idw_core as W
        from pipeline.identify import idz_core as Z
        self.dir, self.device = model_dir, device
        self.meta = json.load(open(os.path.join(model_dir, "meta_feat_cnn.json")))
        self.cfg = self.meta["cfg"]
        assert not self.cfg.get("layout") and not self.cfg.get("fn") and self.cfg.get("cols", "v2") == "v2", self.cfg
        self.names = names if names is not None else json.load(open(DEV_NAMES))
        self.cols = v2_columns(self.names)
        self.manifest = man
        self.version = int(man.get("engine_version", ENGINE_VERSION))
        assert self.version >= 5, "engine v5s needs an engine v5 model"
        v5, spec = man["v5"], man["v5s"]
        refuse_room_weights(model_dir, v5)
        mem = tuple(spec["members"])
        all_feat = tuple(W.FEAT) + tuple(v5["extra_feature_components"])
        all_cnn = tuple(c for c in Z.COMPONENTS if c not in W.FEAT)
        assert set(mem) <= set(all_feat + all_cnn) and len(set(mem)) == len(mem), mem
        self.v5s = spec
        self.feat = {c: pickle.load(open(os.path.join(model_dir, f"feat_{c}.pkl"), "rb")) for c in all_feat if c in mem}
        self.extra_feat = tuple(c for c in v5["extra_feature_components"] if c in mem)
        self.states = {}
        for c in self.extra_feat:
            base = self.feat[c]["state_of"]
            if base not in self.feat:
                self.states[base] = pickle.load(open(os.path.join(model_dir, spec["state_files"][base]), "rb"))["state"]
        self.offsets = tuple(float(o) for o in v5["offsets"])
        self.cnn_tags = tuple(t for t in ("cnn3", "cnn_link0", "cnn_link1", "cnn_link2")
                              if any(t in V5S_CNN_TAGS[c] for c in mem if c in V5S_CNN_TAGS))
        self.nets, self.norm = {}, {}
        for tag in self.cnn_tags:
            self.norm[tag] = pickle.load(open(os.path.join(model_dir, f"{tag}_norm.pkl"), "rb"))
            for s in self.meta["seeds"]:
                self.nets[(tag, s)] = W._load_net(os.path.join(model_dir, f"{tag}_seed{s}.pt"),
                                                  3 if tag == "cnn3" else 1).to(device)
        self.feat_components = tuple(c for c in all_feat if c in mem)
        self.cnn_components = tuple(c for c in all_cnn if c in mem)
        self.components = self.feat_components + self.cnn_components
        self.pace = tuple(c for c in Z.PACE_COMPONENTS if c in mem) + tuple(
            c for c in self.extra_feat if W.FEAT[self.feat[c]["state_of"]][2])

    # A feature component's standardiser: its own, or the shared one read from its state file (engine v5s).
    def state(self, base: str):
        return self.feat[base]["state"] if base in self.feat else self.states[base]



_V2 = {}


# The 630 v2 gait columns (idz_bank.columns_v2) as indices into names.
def v2_columns(names: list) -> np.ndarray:
    key = tuple(names)
    if key not in _V2:
        from pipeline.identify import idmax_eval as E
        from pipeline.identify import idx_loso as L
        from pipeline.identify import idz_bank as ZB
        saved = E._FEAT_CACHE.get("dev")
        L.register_variant("dev", np.zeros((1, len(names))), names)
        _V2[key] = ZB.columns_v2({"names": names})
        if saved is not None:
            E._FEAT_CACHE["dev"] = saved
            E._MASK_CACHE.clear()
        assert len(_V2[key]) == 630, len(_V2[key])
    return _V2[key]




from pipeline.identify import id19_bank as _IB
from pipeline.identify import id19_featbank as _FB
from pipeline.identify import idmax_features as _F
from pipeline.identify import idz_bank as _ZB

LAM11 = 299792458.0 / 2.462e9
KEEP103 = np.asarray(_IB.KEEP)
SC103 = np.asarray(_FB.SC)
RAW103 = KEEP103[SC103]
KEEP107 = np.array(sorted(set(KEEP103.tolist()) | {100, 101, 102, 103}))
SC107 = np.array([i for i, k in enumerate(KEEP107) if k not in _FB.NULL_SC])
RAW107 = KEEP107[SC107]
IDX103 = np.array([int(np.flatnonzero(RAW107 == r)[0]) for r in RAW103])
V5N_NAMES = json.load(open(DEV_NAMES))
V5N_COLS = v2_columns(V5N_NAMES)
V5N_V2 = [V5N_NAMES[k] for k in V5N_COLS]
V5N_V2_INDEX = {n: i for i, n in enumerate(V5N_V2)}
V5N_LIVE_FAMILIES = ("cad", "dop", "mod")



# Conditioning.energy_percentile_contour with the crossing interpolated linearly inside its bin (bin j spans...
def contour_interp(f: np.ndarray, mag: np.ndarray, pct: float) -> np.ndarray:
    f = np.asarray(f, float)
    df = float(f[1] - f[0])
    assert np.allclose(np.diff(f), df), "contour_interp needs uniform bins"
    m = np.asarray(mag, float) ** 2
    tot = m.sum(axis=1)
    c = np.cumsum(m, axis=1)
    out = np.full(m.shape[0], np.nan)
    ok = tot > 0
    if ok.any():
        thr = (pct / 100.0) * tot[ok]
        cc, mm = c[ok], m[ok]
        j = (cc >= thr[:, None]).argmax(axis=1)
        r = np.arange(len(j))
        prev = np.where(j > 0, cc[r, np.maximum(j - 1, 0)], 0.0)
        frac = (thr - prev) / np.maximum(mm[r, j], 1e-300)
        out[ok] = f[j] + (frac - 0.5) * df
    return out


# Id29_dc2_score.torso_hz with H2 and H3 (boundary None, padded False; the crossing interpolated).
def torso_hz_h(a_link: np.ndarray, bmat: np.ndarray = None) -> float:
    from scipy import signal
    P = _F.reduce_link(np.asarray(a_link, float), "dop", "pca", n_pc=4, bmat=bmat)[1:]
    f, _t, Z = signal.stft(P, fs=FS, nperseg=32, noverlap=24, nfft=64, axis=-1, boundary=None, padded=False)
    mag = np.abs(Z).sum(axis=0).T
    keep = (f >= 4.0) & (f <= 70.0)
    c = contour_interp(f[keep], mag[:, keep], 50.0)
    c = c[np.isfinite(c)]
    return float(np.median(c)) if len(c) else float("nan")


# Idmax_features.doppler_features with H2 and H3: the STFT unpadded and the four contours interpolated.
def doppler_features_h(x: np.ndarray, fs: float = FS, win_s: float = 0.2, cadence_hz=None) -> dict:
    from scipy import signal
    x = np.atleast_2d(np.asarray(x, float))
    n = int(round(win_s * fs))
    if x.shape[1] < 4 * n:
        return {}
    f, t, Z = signal.stft(x, fs=fs, nperseg=n, noverlap=int(0.75 * n), axis=-1, nfft=max(n, 64), boundary=None, padded=False)
    mag = np.abs(Z).sum(axis=0).T
    keep = (f >= 4.0) & (f <= 0.95 * fs / 2)
    f, mag = f[keep], mag[:, keep]
    P = mag ** 2
    tot = P.sum(axis=1)
    ok = tot > 0
    if ok.sum() < 8:
        return {}
    cont = {q: contour_interp(f, mag[ok], float(q)) for q in (25, 50, 75, 95)}
    med50 = max(float(np.median(cont[50])), 1e-6)
    out = {"leg_torso": float(np.median(cont[95]) / med50), "q25_torso": float(np.median(cont[25]) / med50),
           "q75_torso": float(np.median(cont[75]) / med50)}
    fr = 1.0 / max(np.median(np.diff(t)), 1e-9)
    for q in (50, 95):
        cq = cont[q] / med50
        out[f"c{q}_cv"] = float(np.std(cq) / max(np.mean(cq), 1e-9))
        r = _F._acf(cq)
        lo, hi = int(0.3 * fr), min(int(2.2 * fr), len(r) - 1)
        out[f"c{q}_periodicity"] = float(r[lo:hi].max()) if hi > lo else np.nan
        if cadence_hz:
            L = int(round(2.0 * fr / cadence_hz))
            segs = [cq[s:s + L] for s in range(0, len(cq) - L + 1, L)] if L >= 4 else []
            if len(segs) >= 2:
                Pc = np.vstack([np.interp(np.linspace(0, 1, 16, endpoint=False), np.linspace(0, 1, len(s), endpoint=False), s)
                                for s in segs]).mean(axis=0)
                Pc = np.roll(Pc, -int(np.argmax(Pc)))
                Pc = (Pc - Pc.mean()) / max(Pc.std(), 1e-9)
                for i, v in enumerate(Pc):
                    out[f"c{q}_cyc{i:02d}"] = float(v)
    fr_u = f / med50
    Pk = P[ok]
    prof = np.asarray([Pk[:, (fr_u >= a) & (fr_u < a + 0.5)].mean() if ((fr_u >= a) & (fr_u < a + 0.5)).any() else 0.0
                       for a in np.arange(0, 4.0, 0.5)])
    prof = prof / max(prof.sum(), 1e-20)
    for i, v in enumerate(prof):
        out[f"uprof_{i}"] = float(v)
    return out



# Function normalise.
def normalise(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, np.float64)
    return a / np.maximum(a.mean(axis=1, keepdims=True), 1e-9)


# One receiver's 107-bin amplitude on grid: the bracketing frames, then N ('N') or not ('raw'), then linear...
def resample(timed_link: tuple, grid: np.ndarray, mode: str) -> np.ndarray:
    t, a, _r = timed_link
    j0 = max(int(np.searchsorted(t, grid[0])) - 1, 0)
    j1 = min(int(np.searchsorted(t, grid[-1])) + 1, len(t))
    ts, a_ = t[j0:j1], np.asarray(a[j0:j1], np.float64)
    if mode == "N":
        a_ = normalise(a_)
    return _IB._interp_cols(grid, ts, a_)


# Function resample rssi.
def resample_rssi(timed_link: tuple, grid: np.ndarray) -> np.ndarray:
    t, _a, r = timed_link
    j0 = max(int(np.searchsorted(t, grid[0])) - 1, 0)
    j1 = min(int(np.searchsorted(t, grid[-1])) + 1, len(t))
    return _IB._interp_cols(grid, t[j0:j1], np.asarray(r[j0:j1], np.float64))



# The 630 v2 columns with only the live ones computed (the rest NaN), Queue 41's features_v statements for...
def live_features(AN: np.ndarray, RL: np.ndarray) -> np.ndarray:
    out, chans, bm = {}, {}, {}
    with _cadence_v3():
        for li, link in enumerate(LINKS):
            bg_long = _F.bandpass(AN[li], "b08_35", axis=0)
            bm[(li, "b08_35")] = bg_long
            a_cut = AN[li]
            chans[(link, "rms", "b08_35")] = _F.bandpass(np.sqrt(np.mean(bg_long ** 2, axis=1)), "b08_35")[None, :]
            chans[(link, "pca", "b08_35")] = _F.reduce_link(a_cut, "b08_35", "pca", n_pc=6, bmat=bg_long)
            bd_long = _F.bandpass(AN[li], "dop", axis=0)
            bm[(li, "dop_long")] = bd_long
            chans[(link, "pca", "dop")] = _F.reduce_link(a_cut, "dop", "pca", n_pc=6, bmat=bd_long)
        live_ch = [(r, b) for r, b in _FB.CADENCE_CH if r != "mean"]
        est = [_F.cadence_estimates(chans[(link, red, band)][0]) for link in LINKS for red, band in live_ch]
        cad = _F.resolve_cadence(est)
        c = cad["cadence_hz"]
        out["cad|all|-|-|cadence_hz"] = c
        out["cad|all|-|-|agree_frac"] = cad["agree_frac"]
        per_link = []
        for link in LINKS:
            rl_ = _F.resolve_cadence([_F.cadence_estimates(chans[(link, red, band)][0]) for red, band in live_ch])
            per_link.append(rl_["cadence_hz"])
            out[f"cad|link|{link}|-|cadence_hz"] = rl_["cadence_hz"]
        pl = [x for x in per_link if x]
        out["cad|all|-|-|link_spread"] = float(np.ptp(pl)) if len(pl) > 1 else np.nan
        for li, link in enumerate(LINKS):
            for k, v in doppler_features_h(chans[(link, "pca", "dop")][1:], win_s=0.2, cadence_hz=c).items():
                out[f"dop|pca-pc1@w0.2|{link}|-|{k}"] = v
            lvl_r = max(float(np.asarray(AN[li], float).mean()), 1e-6)
            d = _F.bandpass(np.sqrt(np.mean(bm[(li, "dop_long")] ** 2, axis=1)), "b08_35")
            r = np.asarray(RL[li], float)
            out[f"mod|-|{link}|-|moddepth_dop"] = float(np.std(d) / lvl_r)
            out[f"mod|-|{link}|-|sub_dispersion"] = float(np.median(np.std(bm[(li, "b08_35")], axis=0)) / 1e-9)
            out[f"mod|-|{link}|-|rssi_std"] = float(np.std(r - np.median(r)))
    v = np.full(len(V5N_V2), np.nan)
    for k, val in out.items():
        i = V5N_V2_INDEX.get(k)
        if i is not None:
            v[i] = np.nan if val is None else val
    v[~np.isfinite(v)] = np.nan
    return v.astype(np.float32).astype(np.float64)


# The live columns by family (the families the v5n path computes; moddepth_gait is dead).
def live_columns() -> dict:
    out = {}
    for n in V5N_V2:
        fam = n.split("|")[0]
        if fam in V5N_LIVE_FAMILIES and not n.endswith("moddepth_gait"):
            out.setdefault(fam, []).append(n)
    return out



# Engine.Receiver with the 107 bins stored (the shipped 103 are amp[:, IDX103]).
class V5NReceiver(Receiver):

    # Sets up the object.
    def __init__(self):
        super().__init__()
        self.amp = np.empty((0, 107), np.float32)

    # Function push.
    def push(self, fr) -> None:
        n0 = len(self._chunks)
        super().push(fr)
        if len(self._chunks) > n0:
            from pipeline.identify.raw_access import amplitude_from_frames
            tm, lt, ep, _a, rs = self._chunks[-1]
            self._chunks[-1] = (tm, lt, ep, amplitude_from_frames(fr)[:, KEEP107][:, SC107].astype(np.float32), rs)


# Engine.Extractor for v5n: the shipped direction and end detection, maps and decision clock (on the 103...
class V5NExtractor(Extractor):

    # Sets up the object.
    def __init__(self, T: float = T_S, amp_norm: bool = False, layout: str = "id_spot", names: list = None,
                 alpha: float = None, rx: dict = None, cut: bool = True):
        super().__init__(T, amp_norm, layout, names, alpha, rx if rx is not None else {L: V5NReceiver() for L in LINKS}, cut)

    # Function raw.
    def _raw(self, t0: float, end: float, td: float) -> np.ndarray:
        grid = np.arange(t0, end, 1.0 / FS)
        return np.asarray([_IB._interp_cols(grid, t, a[:, IDX103].astype(np.float64)) for t, a, _r in [self.rx[L].timed(td) for L in LINKS]],
                          np.float64)

    # Function extract v4.
    def extract_v4(self, w: dict, td: float, timed: list) -> dict:
        t0, end = w["t0"], self._end(w)
        layout = w["layout"]
        e3 = min(t0 + DIR_T_S, end)
        sm3 = signal_measures(self._raw(t0, e3, self.t_dec_end(t0, e3)), w["path"], layout)
        path = sm3["path"]
        walk_end = end
        if self.alpha is not None:
            series = []
            for c in np.round(np.arange(DIR_T_S, self.T + 1e-9, DET_STEP_S), 2):
                ec = min(t0 + c, end)
                series.append((float(ec - t0), band_energy_rx2(self._raw(t0, ec, self.t_dec_end(t0, ec))[1])))
                if ec < t0 + c:
                    break
            d = detect_end(series, self.alpha, upto=self.T)
            if d is not None:
                walk_end = min(t0 + d[0], end)
        return self.window(w, timed, path, sm3, walk_end)

    # The window once its path and walking span are known: the maps (v5s's), the live features and the H speed.
    def window(self, w: dict, timed: list, path: str, sm3: dict, walk_end: float) -> dict:
        t0, end = w["t0"], self._end(w)
        layout = w["layout"]
        T_win = self.T if end == t0 + self.T else end - t0
        c0 = time.perf_counter()
        grid = np.arange(t0, t0 + T_win, 1.0 / FS)
        A_raw = np.asarray([_IB._interp_cols(grid, t, a[:, IDX103].astype(np.float64)) for t, a, _r in timed], np.float64)
        maps = np.stack([_ZB.conditioned_map_v2(A_raw[li]) for li in range(3)]).astype(np.float32)
        AN = np.asarray([resample(timed[k], grid, "N") for k in range(3)])
        RL = np.asarray([resample_rssi(timed[k], grid) for k in range(3)])
        fv = np.full(len(self.names), np.nan, np.float32)
        fv[V5N_COLS] = live_features(AN, RL).astype(np.float32)
        span = np.arange(t0, end, 1.0 / FS)
        li, Fb = best_link(path, layout)
        nw = int(np.searchsorted(span, walk_end, side="left"))
        AH = np.asarray([resample(timed[k], span, "raw") for k in range(3)])
        ft = torso_hz_h(AH[li][:nw]) if nw >= 64 else float("nan")
        v = float(ft * LAM11 / (2.0 * Fb)) if (Fb >= F_MIN and np.isfinite(ft)) else float("nan")
        return {"features": fv, "maps": maps, "layout": layout, "n_frames": [int(len(t)) for t, _a, _r in timed],
                "extract_s": time.perf_counter() - c0, "path": path, "dir_detected": sm3["dir_detected"], "dir_slope": sm3["dir_slope"],
                "speed_link": LINKS[li], "speed_F": Fb, "f_torso": ft, "wifi_speed": v, "walk_end_s": walk_end - t0,
                "alpha": self.alpha, "window_s": end - t0, "engine": "v5n"}




# A model folder whose manifest carries "v5n" (engine v5n).
def is_v5n(model_dir) -> bool:
    p = os.path.join(model_dir, "manifest.json") if model_dir else None
    return bool(p and os.path.exists(p) and json.load(open(p)).get("v5n"))


# A session's calibration pools and the model adapted to each.
class Session:

    # Sets up the object.
    def __init__(self, model: Model):
        self.m = model
        self.pools = {}
        self.update_s = []
        self._use("-")

    # Point the working pool at key's: X (630 gait columns per earlier window), speed, paths, W (each earlier...
    def _use(self, key: str) -> None:
        p = self.pools.setdefault(key, {"X": [], "speed": [], "paths": [], "W": [], "adapted": {}})
        self.X, self.speed, self.paths, self.W, self.adapted = p["X"], p["speed"], p["paths"], p["W"], p["adapted"]

    # Function route.
    def _route(self, ex: dict) -> None:
        self._use(ex.get("layout") or "-")

    # The number of items.
    def __len__(self):
        return sum(len(p["X"]) for p in self.pools.values())

    # Function dir.
    @staticmethod
    def _dir(path: str) -> int:
        return 1 if path.endswith("_rev") else 0

    # Function cnn input.
    def _cnn_input(self, tag, Wl, paths):
        from pipeline.identify import idz_core as Z
        chan = None if tag == "cnn3" else int(tag[-1])
        nd = self.m.norm[tag]
        Xs, ds, ps = [], [], []
        for k, (w, p) in enumerate(zip(Wl, paths)):
            Xs.append(w if chan is None else w[:, chan:chan + 1])
            ds.append(np.full(len(w), nd["dir_map"][self._dir(p)]))
            ps.append(np.full(len(w), k))
        Xw, dw, pw = np.concatenate(Xs), np.concatenate(ds).astype(int), np.concatenate(ps).astype(int)
        return Z.apply_norm_keyed(Xw, dw, None, nd["st"]), dw, pw

    # The components' normalised log-probabilities for one window, and the ensemble.
    def classify(self, ex: dict) -> dict:
        if getattr(self.m, "v5s", None):
            return self._classify_v5s(ex)
        from pipeline.identify import idv2_core as C
        from pipeline.identify import idw_core as W
        from pipeline.identify import idx_loso as L
        c0 = time.perf_counter()
        self._route(ex)
        m = self.m
        g = ex["features"].astype(np.float64)[m.cols]
        path = ex["path"]
        out = {}
        n = len(self.X)
        for comp, (_head, norm, pace) in W.FEAT.items():
            d = m.feat[comp]
            row = np.r_[g, ex["wifi_speed"]] if pace else g
            if norm == "perpath":
                Bm = d["state"].transform(row[None, :], np.array([path]))
            else:
                if n:
                    pool = np.c_[np.asarray(self.X), np.asarray(self.speed)] if pace else np.asarray(self.X)
                    Xall = np.vstack([pool, row[None, :]])
                    paths = np.array(self.paths + [path])
                    calib = np.arange(n)
                else:
                    Xall, paths, calib = row[None, :], np.array([path]), None
                Bm = d["state"].apply(Xall, paths, np.array([len(Xall) - 1]), calib)
            out[comp] = L._order(C.logp_from_proba(d["clf"].predict_proba(Bm)), d["classes"])[0]
        for comp in m.extra_feat:
            d = m.feat[comp]
            base = d["state_of"]
            _head, norm, pace = W.FEAT[base]
            row = np.r_[g, ex["wifi_speed"]] if pace else g
            if norm == "perpath":
                Bm = m.feat[base]["state"].transform(row[None, :], np.array([path]))
            else:
                if n:
                    pool = np.c_[np.asarray(self.X), np.asarray(self.speed)] if pace else np.asarray(self.X)
                    Xall = np.vstack([pool, row[None, :]])
                    paths = np.array(self.paths + [path])
                    calib = np.arange(n)
                else:
                    Xall, paths, calib = row[None, :], np.array([path]), None
                Bm = m.feat[base]["state"].apply(Xall, paths, np.array([len(Xall) - 1]), calib)
            out[comp] = L._order(C.logp_from_proba(d["clf"].predict_proba(Bm)), d["classes"])[0]
        Wn = C.windows(ex["maps"])
        seeds = m.meta["seeds"]
        for tag in ("cnn3", "cnn_link0", "cnn_link1", "cnn_link2"):
            Xw, dw, pw = self._cnn_input(tag, [Wn], [path])
            plain, adapted = [], []
            for s in seeds:
                if tag == "cnn3":
                    plain.append(C.normalise_logp(C.pass_logp(m.nets[(tag, s)], Xw, dw, pw, 1, 6, m.device)))
                net = self.adapted.get((tag, s), m.nets[(tag, s)])
                adapted.append(C.normalise_logp(C.pass_logp(net, Xw, dw, pw, 1, 6, m.device)))
            if tag == "cnn3":
                out["cnn"] = C.normalise_logp(np.mean(plain, axis=0))[0]
                out["cnn_prior"] = C.normalise_logp(np.mean(adapted, axis=0))[0]
            else:
                out[f"_{tag}"] = C.normalise_logp(np.mean(adapted, axis=0))[0]
        out["cnn_perlink_prior"] = C.normalise_logp(sum(out.pop(f"_cnn_link{c}") for c in range(3))[None, :])[0]
        comps = {c: out[c] for c in m.components}
        s = sum(comps.values())
        ens = C.normalise_logp(s[None, :])[0]
        conf = np.exp(s / len(comps) - (s / len(comps)).max())
        return {"components": comps, "ensemble": ens, "confidence": conf / conf.sum(),
                "ensemble_nopace": C.normalise_logp(sum(comps[c] for c in comps if c not in m.pace)[None, :])[0],
                "calib_n": n, "model_s": time.perf_counter() - c0}

    # Engine v5s: classify over the model's members only, the same statements for each member.
    def _classify_v5s(self, ex: dict) -> dict:
        from pipeline.identify import idv2_core as C
        from pipeline.identify import idw_core as W
        from pipeline.identify import idx_loso as L
        m = self.m
        c0 = time.perf_counter()
        self._route(ex)
        g = ex["features"].astype(np.float64)[m.cols]
        path = ex["path"]
        out = {}
        n = len(self.X)
        for comp in m.feat_components:
            d = m.feat[comp]
            base = d.get("state_of", comp)
            _head, norm, pace = W.FEAT[base]
            st = m.state(base)
            row = np.r_[g, ex["wifi_speed"]] if pace else g
            if norm == "perpath":
                Bm = st.transform(row[None, :], np.array([path]))
            else:
                if n:
                    pool = np.c_[np.asarray(self.X), np.asarray(self.speed)] if pace else np.asarray(self.X)
                    Xall = np.vstack([pool, row[None, :]])
                    paths = np.array(self.paths + [path])
                    calib = np.arange(n)
                else:
                    Xall, paths, calib = row[None, :], np.array([path]), None
                Bm = st.apply(Xall, paths, np.array([len(Xall) - 1]), calib)
            out[comp] = L._order(C.logp_from_proba(d["clf"].predict_proba(Bm)), d["classes"])[0]
        Wn = C.windows(ex["maps"])
        seeds = m.meta["seeds"]
        for tag in m.cnn_tags:
            Xw, dw, pw = self._cnn_input(tag, [Wn], [path])
            plain, adapted = [], []
            for s in seeds:
                if tag == "cnn3" and "cnn" in m.cnn_components:
                    plain.append(C.normalise_logp(C.pass_logp(m.nets[(tag, s)], Xw, dw, pw, 1, 6, m.device)))
                if tag != "cnn3" or "cnn_prior" in m.cnn_components:
                    net = self.adapted.get((tag, s), m.nets[(tag, s)])
                    adapted.append(C.normalise_logp(C.pass_logp(net, Xw, dw, pw, 1, 6, m.device)))
            if tag == "cnn3":
                if plain:
                    out["cnn"] = C.normalise_logp(np.mean(plain, axis=0))[0]
                if adapted:
                    out["cnn_prior"] = C.normalise_logp(np.mean(adapted, axis=0))[0]
            else:
                out[f"_{tag}"] = C.normalise_logp(np.mean(adapted, axis=0))[0]
        if "cnn_perlink_prior" in m.cnn_components:
            out["cnn_perlink_prior"] = C.normalise_logp(sum(out.pop(f"_cnn_link{c}") for c in range(3))[None, :])[0]
        comps = {c: out[c] for c in m.components}
        s = sum(comps.values())
        ens = C.normalise_logp(s[None, :])[0]
        conf = np.exp(s / len(comps) - (s / len(comps)).max())
        return {"components": comps, "ensemble": ens, "confidence": conf / conf.sum(),
                "ensemble_nopace": C.normalise_logp(sum(comps[c] for c in comps if c not in m.pace)[None, :])[0],
                "calib_n": n, "model_s": time.perf_counter() - c0}

    # Engine v5: per window k, s_k = a x the feature components' sum + the CNN components' sum (summed in the...
    def combine(self, results: list, a: float) -> dict:
        from pipeline.identify import idv2_core as C
        m = self.m
        ens, nop, raw = [], [], []
        for r in results:
            comps = r["components"]
            s, snp = 0, 0
            for c in m.feat_components:
                s = s + a * comps[c]
                if c not in m.pace:
                    snp = snp + a * comps[c]
            for c in m.cnn_components:
                s = s + 1.0 * comps[c]
                snp = snp + 1.0 * comps[c]
            raw.append(s)
            ens.append(C.normalise_logp(s[None, :])[0])
            nop.append(C.normalise_logp(snp[None, :])[0])
        E = C.normalise_logp(np.mean(ens, axis=0)[None, :])[0] if len(ens) > 1 else ens[0]
        Enp = C.normalise_logp(np.mean(nop, axis=0)[None, :])[0] if len(nop) > 1 else nop[0]
        A = a * len(m.feat_components) + len(m.cnn_components)
        z = np.mean(raw, axis=0) / A
        conf = np.exp(z - z.max())
        return {"ensemble": E, "ensemble_nopace": Enp, "confidence": conf / conf.sum(), "weight_a": float(a)}

    # Add a decided window to the pool and recompute the AdaBN copies for the next window.
    def add(self, ex: dict) -> None:
        c0 = time.perf_counter()
        self._route(ex)
        self._append(ex)
        self._adapt()
        self.update_s.append(time.perf_counter() - c0)

    # A whole calibration pool at once (information-only settings such as CAL-others); one adaptation.
    def set_pool(self, exs: list) -> None:
        by = {}
        for ex in exs:
            by.setdefault(ex.get("layout") or "-", []).append(ex)
        for key, group in by.items():
            self._use(key)
            for ex in group:
                self._append(ex)
            self._adapt()

    # Function append.
    def _append(self, ex: dict) -> None:
        from pipeline.identify import idv2_core as C
        self.X.append(ex["features"].astype(np.float64)[self.m.cols])
        self.speed.append(ex["wifi_speed"])
        self.paths.append(ex["path"])
        self.W.append(C.windows(ex["maps"]))

    # Function adapt.
    def _adapt(self) -> None:
        if getattr(self.m, "v5s", None):
            self._adapt_v5s()
            return
        from pipeline.identify import idv2_core as C
        for tag in ("cnn3", "cnn_link0", "cnn_link1", "cnn_link2"):
            Xo, do, _p = self._cnn_input(tag, self.W, self.paths)
            for s in self.m.meta["seeds"]:
                self.adapted[(tag, s)] = C.adabn(self.m.nets[(tag, s)], Xo, do, self.m.device)

    # Engine v5s: _adapt over the members' networks only (cnn3's adapted copies only when cnn_prior is a member).
    def _adapt_v5s(self) -> None:
        from pipeline.identify import idv2_core as C
        for tag in self.m.cnn_tags:
            if tag == "cnn3" and "cnn_prior" not in self.m.cnn_components:
                continue
            Xo, do, _p = self._cnn_input(tag, self.W, self.paths)
            for s in self.m.meta["seeds"]:
                self.adapted[(tag, s)] = C.adabn(self.m.nets[(tag, s)], Xo, do, self.m.device)



# Engine v5 since 25 Oct 2026: the feature weight is 1 on every walk and the engine takes no room.
def refuse_room_weights(model_dir: str, v5: dict) -> None:
    if "room_weights" in v5:
        raise ValueError(f"{model_dir}: the manifest carries room_weights, retired on 25 Oct 2026 (the feature weight is now 1 "
                         "on every walk); this model's figures hold only at its room weights")


# One press in, one decision out.
class Engine:

    # Sets up the object.
    def __init__(self, model_dir=None, T: float = T_S, amp_norm: bool = False, layout: str = "id_spot",
                 device: str = "cpu", names: list = None, alpha: float = None):
        self.names = names if names is not None else json.load(open(DEV_NAMES))
        if alpha is None and model_dir and os.path.exists(os.path.join(model_dir, "manifest.json")):
            alpha = json.load(open(os.path.join(model_dir, "manifest.json"))).get("alpha")
        self.alpha = alpha
        self._xcls = V5NExtractor if is_v5n(model_dir) else Extractor
        self.ex = self._xcls(T, amp_norm, layout, self.names, alpha)
        self.model = Model(model_dir, device, self.names) if model_dir else None
        self.session = Session(self.model) if self.model else None
        self.decisions = []
        self.v5 = bool(self.model is not None and self.model.version >= 5)
        if self.v5:
            self._offsets()
            self._walks, self._order, self._wid = {}, [], 0

    # Engine v5: the offset windows' extractors, sharing the main extractor's receivers, never cut by a press.
    def _offsets(self) -> None:
        self.ex_off = {o: self._xcls(self.ex.T, self.ex.amp_norm, self.ex.layout, self.names, self.alpha, rx=self.ex.rx, cut=False)
                       for o in self.model.offsets}

    # A new stream (new capture files): the receivers restart; the session's calibration pool stays.
    def new_recording(self, layout: str = None) -> None:
        self.ex = self._xcls(self.ex.T, self.ex.amp_norm, layout or self.ex.layout, self.names, self.alpha)
        if self.v5:
            self._offsets()

    # Function push.
    def push(self, link: str, frames) -> None:
        self.ex.push(link, frames)
        if self.v5:
            for e in self.ex_off.values():
                e.newest = self.ex.newest

    # Function press.
    def press(self, t0: float, path=None, layout=None, info=None) -> None:
        if not self.v5:
            self.ex.press(t0, path, layout, info)
            return
        wid = self._wid
        self._wid += 1
        tagged = dict(info or {}, _walk=wid)
        self.ex.press(t0, path, layout, tagged)
        for o, e in self.ex_off.items():
            e.press(t0 + o, path, layout, tagged)
        self._walks[wid] = {"t0": float(t0), "info": info or {}, "layout": layout or self.ex.layout, "wins": {}}
        self._order.append(wid)

    # Function open windows.
    @property
    def open_windows(self) -> int:
        return len(self.ex.pending) + (sum(len(e.pending) for e in self.ex_off.values()) if self.v5 else 0)

    # Engine v5: every window decided by now; each walk whose three windows are decided, in press order: the...
    def _poll_v5(self, now: float, closing: bool) -> list:
        for o, e in [(0.0, self.ex)] + list(self.ex_off.items()):
            for w, td, ex in e.poll(now, closing):
                self._walks[w["info"]["_walk"]]["wins"][o] = (td, ex)
        keys = (0.0,) + self.model.offsets
        out = []
        while self._order and all(k in self._walks[self._order[0]]["wins"] for k in keys):
            W = self._walks.pop(self._order.pop(0))
            c0 = time.perf_counter()
            res = [self.session.classify(W["wins"][k][1]) for k in keys]
            comb = self.session.combine(res, FEATURE_WEIGHT)
            model_s = time.perf_counter() - c0
            td = W["wins"][keys[-1]][0]
            ex0 = W["wins"][0.0][1]
            d = {"t0": W["t0"], "t_dec": td, "T": self.ex.T, "info": W["info"], "extraction": ex0,
                 "wait_s": td - (W["t0"] + self.ex.T), "engine_version": 5,
                 "windows": {k: {"t_dec": W["wins"][k][0], "extraction": W["wins"][k][1], "components": r["components"]}
                             for k, r in zip(keys, res)},
                 "components": res[0]["components"], "calib_n": res[0]["calib_n"], "model_s": model_s, **comb}
            order = np.argsort(-d["ensemble"])
            d["top"], d["runner_up"] = CLASSES[int(order[0])], CLASSES[int(order[1])]
            d["latency_s"] = d["wait_s"] + W["wins"][keys[-1]][1]["extract_s"] + model_s
            self.session.add(ex0)
            self.decisions.append(d)
            out.append(d)
        return out

    # Function poll.
    def poll(self, now: float, closing: bool = False) -> list:
        if self.v5:
            return self._poll_v5(now, closing)
        out = []
        for w, td, ex in self.ex.poll(now, closing):
            d = {"t0": w["t0"], "t_dec": td, "T": self.ex.T, "info": w["info"], "extraction": ex,
                 "wait_s": td - (w["t0"] + self.ex.T)}
            if self.session is not None:
                r = self.session.classify(ex)
                d.update(r)
                k = int(np.argmax(r["ensemble"]))
                order = np.argsort(-r["ensemble"])
                d["top"], d["runner_up"] = CLASSES[k], CLASSES[int(order[1])]
                d["latency_s"] = d["wait_s"] + ex["extract_s"] + r["model_s"]
                self.session.add(ex)
            else:
                d["latency_s"] = d["wait_s"] + ex["extract_s"]
            self.decisions.append(d)
            out.append(d)
        return out
