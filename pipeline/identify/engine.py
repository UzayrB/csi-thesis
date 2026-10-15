"""engine. The one-press identification engine (`reports/identification/briefs/2026-09-30_engine.md`; every parameter is
fixed in `runs/identify/engine/PLAN.md`, section 2). It is the live app's identification and the thesis
model: the bank builder, the evaluation harness and `pipeline.live` all call this code.

From one press to one answer:
1. `push` each receiver's frames as they arrive (capture frames, in arrival order);
2. `press(t0)` opens a window [t0, t0 + T];
3. `poll(now)` decides every open window whose decision time has come: the earliest frame arrival at which
   every receiver has delivered a frame past t0 + T on the causal clock (section 2.2), or t0 + T + 1 s;
4. the window's frames are resampled onto the 150 Hz grid; the gait features and Doppler maps are computed
   by the bank's own functions; the direction and the Wi-Fi speed are measured from the signal;
5. the eight components score it, calibrated on every earlier window of the session with the same antenna
   layout (causal; engine v3), and their log-probabilities are summed.

Decisions depend only on the frames' arrival times, never on how frames were batched when pushed, so a
replay and the rig give the same decision for the same frames.

Development evaluation, all data seen.
"""

from __future__ import annotations

import json
import os
import pickle
import time

import numpy as np

# ------------------------------------------------------------------ fixed parameters (PLAN section 2)

T_S = 4.0                    # the window after the press (engine v4; v1 to v3 used 3.0)
CAP_S = 1.0                  # decide at t0 + T + CAP_S at the latest
CLOCK_WIN_S = 20.0           # the causal clock's trailing window (arrival time)
CLOCK_MIN = 20               # frames needed for an offset; otherwise t_mono
CLOCK_PCT = 5.0
WRAP_S = 2.0 ** 32 * 1e-6    # the receiver clock's modulus, seconds
WRAP_EDGE_S = 5.0            # a wrap goes from within 5 s of the top to under 5 s
JUMP_S = 1.0                 # a backwards jump larger than this is a wrap or a reboot
KEEP_S = 60.0                # the rolling buffer (arrival time)
FS = 150.0
LAMBDA = 0.123
F_MIN = 0.3
DIR_BAND = (10.0, 35.0)
MIN_FEAT_CALIB = 10          # `idw_core.Prior.apply`'s threshold
LINKS = ("RX1", "RX2", "RX3")
CLASSES = ("P1", "P2", "P3", "P4", "P5", "P6")
LABEL = "development evaluation, all data seen"
ENG = os.path.join("runs", "identify", "engine")
DEV_NAMES = os.path.join("runs", "identify", "dev", "bank", "feature_names.json")

# ------------------------------------------------------------------ engine v2: the cadence bug fix (PLAN note 2026-10-01)

# ------------------------------------------------------------------ engine v3: two bug fixes (PLAN note 2026-10-01 18:12)
#   fix F: a window with no rhythm-bearing channel has no step rate (`resolve_cadence_v3`);
#   fix L: a window calibrates only on earlier windows of its own antenna layout (`Session`).

# ------------------------------------------------------------------ engine v4: the 4.0 s window (PLAN note 2026-10-02 00:23)
#   the window is [t0, t0 + 4 s]; the direction is still detected on its first 3 s; the Wi-Fi speed uses only the walking
#   span, ended by RX2's torso-band energy (alpha, a model parameter in the manifest); a window stops at a pending press.

# ------------------------------------------------------------------ engine v5: shipped 10 Oct 2026 (PLAN note; runs/identify/v5/)
#   chosen per model: a model whose manifest says engine_version 5 runs as v5, any other model exactly as v4. v5 = six
#   feature components (v4's five and hgb_pace_prior, which shares rf_pace_prior's state); three windows per press (0, 0.15
#   and 0.30 s after it; an offset window is never cut by the next press), each classified against the same CAL-causal
#   pool, only the 0 s window joining it; per window s_k = a x the feature components' sum + the CNN components' sum,
#   normalised, the three averaged and normalised; a from the installation's room (the manifest's room weights).

ENGINE_VERSION = 4            # the extraction's version (v5 extracts exactly as v4); a model's own version is in its manifest
SUFFIX = "_v4"                # engine v4's banks and models; v1's, v2's (`_x`) and v3's (`_v3`) are kept beside them
DIR_T_S = 3.0                 # the direction's window (v1 to v3's whole window)
DET_STEP_S = 0.25             # end-detector checkpoints from DIR_T_S to T
DET_REF_S, DET_MIN_S, DET_RUN = 2.5, 2.5, 10          # reference frames up to 2.5 s; a run starts at or after 2.5 s; 10 frames
DET_HOP_S, DET_C0_S = 8.0 / 150.0, 16.0 / 150.0       # the conditioned spectrogram's frame grid
CADENCE_VOTE_MIN_ACF = 0.30   # only channels with a clear rhythm vote on the step rate


def bank_dir(T: float = T_S) -> str:
    return os.path.join(ENG, f"bank_T{T:.1f}{SUFFIX}")


def model_name(base: str) -> str:
    return base + SUFFIX


def replay_name(model: str, session: str, T: float = T_S) -> str:
    return f"{model}_{session}_T{T:.1f}"


def resolve_cadence_v2(estimate_sets: list) -> dict:
    """`idmax_features.resolve_cadence` with only rhythm-bearing channels voting (acf peak >= 0.30); if none
    qualifies, every channel votes as in v1. Without it, rhythm-less channels' estimates at the 0.8 Hz band-pass edge,
    doubled into the step band, outvoted the true rate (fast away walks read 0.73 to 0.91 on simulated truth)."""
    from pipeline.identify import idmax_features as F
    strong = [e for e in estimate_sets if e.get("acf_peak") is not None and e["acf_peak"] >= CADENCE_VOTE_MIN_ACF]
    return _RESOLVE_V1(strong if strong else estimate_sets)


def resolve_cadence_v3(estimate_sets: list) -> dict:
    """Engine v3 (fix F): as v2, but when no channel's autocorrelation peak reaches 0.30 the window has no measurable
    rhythm, so there is no step rate (None) instead of every channel voting. The cadence-scaled features are then
    missing (NaN), and imputed from the training medians as any missing feature."""
    strong = [e for e in estimate_sets if e.get("acf_peak") is not None and e["acf_peak"] >= CADENCE_VOTE_MIN_ACF]
    if not strong:
        return {"cadence_hz": None, "agree_frac": 0.0, "n_estimates": 0}
    return _RESOLVE_V1(strong)


def _v1():
    from pipeline.identify import idmax_features as F
    return F.resolve_cadence


_RESOLVE_V1 = _v1()


class _cadence_v2:
    """Scoped swap: the engine's gait features use the v2 resolver; every other caller keeps the frozen v1."""

    def __enter__(self):
        from pipeline.identify import idmax_features as F
        self._saved = F.resolve_cadence
        F.resolve_cadence = resolve_cadence_v2

    def __exit__(self, *exc):
        from pipeline.identify import idmax_features as F
        F.resolve_cadence = self._saved
        return False


class _cadence_v3(_cadence_v2):
    """Scoped swap: the engine's gait features use the v3 resolver (fix F); every other caller keeps the frozen v1."""

    def __enter__(self):
        from pipeline.identify import idmax_features as F
        self._saved = F.resolve_cadence
        F.resolve_cadence = resolve_cadence_v3


# ------------------------------------------------------------------ geometry: the bistatic factor per layout

def _rigs() -> dict:
    from pipeline.identify.idgp_contract import RIG_DC2_IDSPOT, RIG_ROOM_A
    return {"home": RIG_ROOM_A, "id_spot": RIG_DC2_IDSPOT["primary"]}


def mean_F(link: str, path: str, layout: str) -> float:
    """`idw_physics.mean_F` for a layout: the mean projected bistatic factor over 101 points of the path."""
    from pipeline.identify.id15_factor_map import bistatic_factor
    from pipeline.identify.idgp_contract import PATHS
    rig = _rigs()[layout]
    a, b = (np.asarray(x, float) for x in PATHS[path])
    u = np.linspace(0, 1, 101)
    pts = a[None, :] + u[:, None] * (b - a)[None, :]
    return float(np.mean(bistatic_factor(pts, b - a, rig["TX"], rig[link])))


_BEST = {}


def best_link(path: str, layout: str) -> tuple:
    """(link index, F) of the link with the largest mean F for this path and layout."""
    key = (path, layout)
    if key not in _BEST:
        f = [mean_F(L, path, layout) for L in LINKS]
        _BEST[key] = (int(np.argmax(f)), float(np.max(f)))
    return _BEST[key]


# ------------------------------------------------------------------ one receiver: buffer and causal clock

class Receiver:
    """One receiver's frames in arrival order, with epochs (reboots) and unwrapped local time."""

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

    def push(self, fr) -> None:
        """A structured capture-frame array (`FRAME_DTYPE` fields `t_mono`, `local_timestamp`, `rssi`,
        `data`), in arrival order."""
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
            else:                                   # a reboot: the estimate restarts
                self.epoch += 1
                self.wraps = 0
                self.n_reboots += 1
            start = j
        self.prev_raw = float(raw[-1])
        a = amplitude_from_frames(fr)[:, KEEP][:, SC].astype(np.float32)
        self._chunks.append((tm, lt, ep, a, np.asarray(fr["rssi"], np.float32)))

    def drop_old(self, before: float) -> None:
        """Drop whole blocks that arrived entirely before `before` (idle housekeeping; no copying)."""
        if len(self.tm) and self.tm[-1] < before:
            self.tm, self.lt, self.ep, self.amp, self.rssi = (x[:0] for x in (self.tm, self.lt, self.ep, self.amp, self.rssi))
        while self._chunks and self._chunks[0][0][-1] < before and not len(self.tm):
            self._chunks.pop(0)

    def consolidate(self, trim_before: float = None) -> None:
        if self._chunks:
            parts = [(self.tm, self.lt, self.ep, self.amp, self.rssi)] + self._chunks
            self.tm, self.lt, self.ep, self.amp, self.rssi = (np.concatenate([p[k] for p in parts]) for k in range(5))
            self._chunks = []
        if trim_before is not None and len(self.tm) and self.tm[0] < trim_before:
            k = int(np.searchsorted(self.tm, trim_before, side="left"))
            self.tm, self.lt, self.ep, self.amp, self.rssi = (x[k:] for x in (self.tm, self.lt, self.ep, self.amp, self.rssi))

    def arrived(self, tau: float) -> np.ndarray:
        """Indices of the frames of the current epoch (at tau) that arrived by tau."""
        n = int(np.searchsorted(self.tm, tau, side="right"))
        if n == 0:
            return np.empty(0, int)
        k0 = int(np.searchsorted(self.ep[:n], self.ep[n - 1], side="left"))   # epochs only increase
        return np.arange(k0, n)

    def offset(self, tau: float, idx: np.ndarray):
        """The causal offset at tau (PLAN 2.2), or None (fewer than 20 frames: use t_mono)."""
        if not len(idx):
            return None
        w = idx[self.tm[idx] > tau - CLOCK_WIN_S]
        if len(w) < CLOCK_MIN:
            return None
        return float(np.percentile(self.tm[w] - self.lt[w], CLOCK_PCT))

    def last_time(self, tau: float) -> float:
        idx = self.arrived(tau)
        if not len(idx):
            return -np.inf
        off = self.offset(tau, idx)
        return float(self.lt[idx].max() + off) if off is not None else float(self.tm[idx].max())

    def timed(self, tau: float) -> tuple:
        """(t_hat, amplitude (n, 103), rssi) of the frames arrived by tau, timed by the clock at tau, sorted."""
        idx = self.arrived(tau)
        off = self.offset(tau, idx)
        t = self.lt[idx] + off if off is not None else self.tm[idx]
        o = np.argsort(t, kind="stable")
        return t[o], self.amp[idx][o], self.rssi[idx][o]


# ------------------------------------------------------------------ extraction: one window

def signal_measures(A_raw: np.ndarray, path: str, layout: str) -> dict:
    """Direction and Wi-Fi speed from the window's raw amplitude (3, n, 103), identity-blind (PLAN 2.4, 2.5).
    `path` is the known path, or None to use the detected direction (line A)."""
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


def extract_window(timed: list, t0: float, T: float, amp_norm: bool, path, layout: str, names: list) -> dict:
    """The window's features (in `names` order), maps, direction and speed, from each receiver's
    (t_hat, amplitude, rssi). The same statements as the bank (`idx_bank.pass_items`, `idz_bank`)."""
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
    with (_cadence_v3() if ENGINE_VERSION >= 3 else _cadence_v2()):     # v2: the cadence bug fix; v3: fix F
        feats = FB.pass_features(A, R)
    fv = np.array([feats.get(n, np.nan) if feats.get(n) is not None else np.nan for n in names], np.float64)
    fv[~np.isfinite(fv)] = np.nan
    maps = np.stack([ZB.conditioned_map_v2(A[li]) for li in range(3)]).astype(np.float32)
    sm = signal_measures(A_raw, path, layout)
    return {"features": fv.astype(np.float32), "maps": maps, **sm, "layout": layout, "n_frames": [int(len(t)) for t, _a, _r in timed],
            "extract_s": time.perf_counter() - c0}


class Extractor:
    """The stream side: three receivers, open windows, and extraction. No model."""

    def __init__(self, T: float = T_S, amp_norm: bool = False, layout: str = "id_spot", names: list = None,
                 alpha: float = None, rx: dict = None, cut: bool = True):
        self.T, self.amp_norm, self.layout = float(T), bool(amp_norm), layout
        self.alpha = alpha          # engine v4's end-detector threshold (None: the walking span is the whole window)
        self.names = names if names is not None else json.load(open(DEV_NAMES))
        self.rx = rx if rx is not None else {L: Receiver() for L in LINKS}    # engine v5: offset windows share the receivers
        self.cut = cut              # engine v5's offset windows are never cut by the next press (v4 windows always are)
        self.pending = []           # [{"t0", "path", "checked"}]
        self.newest = -np.inf

    def push(self, link: str, frames) -> None:
        self.rx[link].push(frames)
        if len(frames):
            self.newest = max(self.newest, float(np.max(frames["t_mono"])))

    def press(self, t0: float, path=None, layout=None, info=None) -> None:
        if ENGINE_VERSION >= 4 and self.cut and self.pending and self.pending[-1]["t0"] + self.T > float(t0) > self.pending[-1]["t0"]:
            self.pending[-1]["end"] = float(t0)          # engine v4: a window stops at the next start press
            self.pending[-1].pop("checked", None)
        self.pending.append({"t0": float(t0), "path": path, "layout": layout or self.layout, "info": info or {}})

    def _end(self, w: dict) -> float:
        return w.get("end", w["t0"] + self.T)

    def t_dec_end(self, t0: float, end: float) -> float:
        """The engine's decision rule for any window end, on every frame that has arrived (engine v4's checkpoints)."""
        cap = end + CAP_S
        cand = np.unique(np.concatenate([r.tm[(r.tm > t0) & (r.tm <= cap)] for r in self.rx.values()]))
        for tau in cand:
            if all(r.last_time(tau) > end for r in self.rx.values()):
                return float(tau)
        return float(cap)

    def _raw(self, t0: float, end: float, td: float) -> np.ndarray:
        from pipeline.identify.id19_bank import _interp_cols
        grid = np.arange(t0, end, 1.0 / FS)
        return np.asarray([_interp_cols(grid, t, a.astype(np.float64)) for t, a, _r in [self.rx[L].timed(td) for L in LINKS]],
                          np.float64)

    def _t_dec(self, w: dict, now: float):
        """The decision time if it has come by `now`, else None (PLAN 2.1)."""
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

    def poll(self, now: float, closing: bool = False) -> list:
        """Windows decided by `now`, in press order: [(window, t_dec, extraction)]. `closing`: the stream has
        ended, so every open window is decided with what arrived."""
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

    def extract_v4(self, w: dict, td: float, timed: list) -> dict:
        """Engine v4's window (the lean-in brief's 4.0 s arm, `iwg_bank.window`): the direction from its first 3 s; the
        walking span from RX2's torso-band energy at causal checkpoints; the Wi-Fi speed on that span; features and maps
        on the whole window."""
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


def band_energy_rx2(a_rx2: np.ndarray) -> np.ndarray:
    """Per frame, RX2's conditioned spectrogram summed over the direction band (10 <= f < 35 Hz)."""
    from pipeline.identify import rehearsal_doppler_check as RD
    f, P = RD.conditioned_spectrogram(a_rx2)
    m = (f >= DIR_BAND[0]) & (f < DIR_BAND[1])
    return P[m].sum(axis=0)


def detect_end(series: list, alpha: float, upto: float):
    """Engine v4's end detector (`iwg_bank.detect`): per checkpoint c, the frame energies of [t0, t0 + c]; the first
    complete run of DET_RUN frames below alpha x the median over frames centred up to DET_REF_S, starting at or after
    DET_MIN_S, using checkpoints <= upto. Returns (end s, checkpoint s) or None."""
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


# ------------------------------------------------------------------ the model: eight components, causal calibration

class Model:
    """A trained ensemble (`idz_core.train`'s saved files), applied one window at a time."""

    def __init__(self, model_dir: str, device: str = "cpu", names: list = None):
        from pipeline.identify import idw_core as W
        from pipeline.identify import idz_core as Z
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
        if self.version >= 5:                           # engine v5: the extra feature components (M3), offsets, room weights
            v5 = self.manifest["v5"]
            self.extra_feat = tuple(v5["extra_feature_components"])
            for c in self.extra_feat:
                self.feat[c] = pickle.load(open(os.path.join(model_dir, f"feat_{c}.pkl"), "rb"))
            self.offsets = tuple(float(o) for o in v5["offsets"])
            self.room_weights = v5["room_weights"]
            self.rooms = sorted({str(x)[0] for x in self.manifest["training_sessions"]})
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

    def weight(self, room: str, layout: str) -> float:
        """Engine v5's feature weight a for a window: the trained-room weight on a tracking walk (layout home) in a room
        the model trained in, the unseen weight on a tracking walk in any other room, the identification weight on an
        identification walk."""
        rw = self.room_weights
        if layout != "home":
            return float(rw["identification"])
        return float(rw["trained"][room]) if room in self.rooms else float(rw["unseen"])


_V2 = {}


def v2_columns(names: list) -> np.ndarray:
    """The 630 v2 gait columns (`idz_bank.columns_v2`) as indices into `names`. The frozen column selector
    reads a registered feature variant; any variant already registered is restored afterwards."""
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


class Session:
    """A session's calibration pools and the model adapted to each. Engine v3 (fix L): one pool per antenna layout,
    so a window calibrates (feature standardisation and AdaBN) only on earlier windows of its own layout (a home has
    one). A window without a layout (an `ex` built by hand) uses the pool "-"."""

    def __init__(self, model: Model):
        self.m = model
        self.pools = {}              # layout -> {"X", "speed", "paths", "W", "adapted"}
        self.update_s = []
        self._use("-")

    def _use(self, key: str) -> None:
        """Point the working pool at `key`'s: X (630 gait columns per earlier window), speed, paths, W (each earlier
        window's CNN windows) and adapted ((tag, seed) -> AdaBN copy; empty until the pool has a window)."""
        p = self.pools.setdefault(key, {"X": [], "speed": [], "paths": [], "W": [], "adapted": {}})
        self.X, self.speed, self.paths, self.W, self.adapted = p["X"], p["speed"], p["paths"], p["W"], p["adapted"]

    def _route(self, ex: dict) -> None:
        self._use(ex.get("layout") or "-")

    def __len__(self):
        return sum(len(p["X"]) for p in self.pools.values())

    @staticmethod
    def _dir(path: str) -> int:
        return 1 if path.endswith("_rev") else 0

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

    def classify(self, ex: dict) -> dict:
        """The eight components' normalised log-probabilities for one window, and the ensemble."""
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
        for comp in m.extra_feat:                       # engine v5: a component sharing another component's state
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

    def combine(self, results: list, a: float) -> dict:
        """Engine v5: per window k, s_k = a x the feature components' sum + the CNN components' sum (summed in the
        components' order), normalised; the windows averaged and normalised again; the confidence softmax(mean_k(s_k) / A)
        with A = a x (feature components) + (CNN components); without pace likewise without the pace components."""
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

    def add(self, ex: dict) -> None:
        """Add a decided window to the pool and recompute the AdaBN copies for the next window."""
        c0 = time.perf_counter()
        self._route(ex)
        self._append(ex)
        self._adapt()
        self.update_s.append(time.perf_counter() - c0)

    def set_pool(self, exs: list) -> None:
        """A whole calibration pool at once (information-only settings such as CAL-others); one adaptation."""
        by = {}
        for ex in exs:
            by.setdefault(ex.get("layout") or "-", []).append(ex)
        for key, group in by.items():
            self._use(key)
            for ex in group:
                self._append(ex)
            self._adapt()

    def _append(self, ex: dict) -> None:
        from pipeline.identify import idv2_core as C
        self.X.append(ex["features"].astype(np.float64)[self.m.cols])
        self.speed.append(ex["wifi_speed"])
        self.paths.append(ex["path"])
        self.W.append(C.windows(ex["maps"]))

    def _adapt(self) -> None:
        from pipeline.identify import idv2_core as C
        for tag in ("cnn3", "cnn_link0", "cnn_link1", "cnn_link2"):
            Xo, do, _p = self._cnn_input(tag, self.W, self.paths)
            for s in self.m.meta["seeds"]:
                self.adapted[(tag, s)] = C.adabn(self.m.nets[(tag, s)], Xo, do, self.m.device)


# ------------------------------------------------------------------ the engine: stream + model + session

class Engine:
    """One press in, one decision out. `model_dir` None: extraction only (the bank builder)."""

    def __init__(self, model_dir=None, T: float = T_S, amp_norm: bool = False, layout: str = "id_spot",
                 device: str = "cpu", names: list = None, alpha: float = None, room: str = None):
        self.names = names if names is not None else json.load(open(DEV_NAMES))
        if alpha is None and model_dir and os.path.exists(os.path.join(model_dir, "manifest.json")):
            alpha = json.load(open(os.path.join(model_dir, "manifest.json"))).get("alpha")   # engine v4's threshold
        self.alpha = alpha
        self.ex = Extractor(T, amp_norm, layout, self.names, alpha)
        self.model = Model(model_dir, device, self.names) if model_dir else None
        self.session = Session(self.model) if self.model else None
        self.decisions = []
        self.v5 = bool(self.model is not None and self.model.version >= 5)
        if self.v5:
            if room not in ("A", "B", "new"):
                raise ValueError("an engine v5 model needs the installation's room, set once before any press: A, B or new")
            self.room = room
            self._offsets()
            self._walks, self._order, self._wid = {}, [], 0

    def _offsets(self) -> None:
        """Engine v5: the offset windows' extractors, sharing the main extractor's receivers, never cut by a press."""
        self.ex_off = {o: Extractor(self.ex.T, self.ex.amp_norm, self.ex.layout, self.names, self.alpha, rx=self.ex.rx, cut=False)
                       for o in self.model.offsets}

    def new_recording(self, layout: str = None) -> None:
        """A new stream (new capture files): the receivers restart; the session's calibration pool stays."""
        self.ex = Extractor(self.ex.T, self.ex.amp_norm, layout or self.ex.layout, self.names, self.alpha)
        if self.v5:
            self._offsets()

    def push(self, link: str, frames) -> None:
        self.ex.push(link, frames)
        if self.v5:
            for e in self.ex_off.values():
                e.newest = self.ex.newest

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

    @property
    def open_windows(self) -> int:
        return len(self.ex.pending) + (sum(len(e.pending) for e in self.ex_off.values()) if self.v5 else 0)

    def _poll_v5(self, now: float, closing: bool) -> list:
        """Engine v5: every window decided by `now`; each walk whose three windows are decided, in press order: the three
        classified against the same pool, combined with the room's weight, and only the 0 s window added to the pool."""
        for o, e in [(0.0, self.ex)] + list(self.ex_off.items()):
            for w, td, ex in e.poll(now, closing):
                self._walks[w["info"]["_walk"]]["wins"][o] = (td, ex)
        keys = (0.0,) + self.model.offsets
        out = []
        while self._order and all(k in self._walks[self._order[0]]["wins"] for k in keys):
            W = self._walks.pop(self._order.pop(0))
            c0 = time.perf_counter()
            a = self.model.weight(self.room, W["layout"])
            res = [self.session.classify(W["wins"][k][1]) for k in keys]
            comb = self.session.combine(res, a)
            model_s = time.perf_counter() - c0
            td = W["wins"][keys[-1]][0]
            ex0 = W["wins"][0.0][1]
            d = {"t0": W["t0"], "t_dec": td, "T": self.ex.T, "info": W["info"], "extraction": ex0,
                 "wait_s": td - (W["t0"] + self.ex.T), "engine_version": 5, "room": self.room,
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
