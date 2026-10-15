"""IDGP signal layer: every per-pass quantity of brief 2026-09-23f sections 2 to 4, from a ContractPass.

INPUT. `pass_features(cp)` takes a `ContractPass` and nothing else (no row, no label, no anchor). The
cadence sources read `cp.amp`, which includes the fixed margin of the cadence variant; every other
feature reads `cp.walk()`, the samples strictly between the start and end presses.

CADENCE (section 3). Per link, three sources:
  env   autocorrelation of the RMS motion envelope (0.8 to 3.5 Hz)
  dop   autocorrelation of the Doppler torso contour (the 50th-percentile energy contour of the 4 to
        70 Hz STFT of PCs 2 to 4)
  peaks step-peak counting on the envelope
Each gives a rate and a periodicity (the autocorrelation peak height, or 1 - CV of the peak
intervals). Sources below PERIODICITY_MIN are dropped, not averaged in. Every kept rate offers its
x0.5, x1 and x2 harmonics inside the step-time prior 0.35 to 0.75 s; the step rate is the candidate
with the greatest periodicity-weighted support within AGREE_HZ, and the cadence is the
periodicity-weighted median of the supporting candidates. No speed of any kind is consulted. Per-link
cadence uses only that link's sources; the fused cadence uses all links' kept sources.

GEOMETRY-CORRECTED DOPPLER (section 4). Position at each STFT frame by steady progress along the
known path between the start and end presses, F(t) = |(u_TX + u_RX) . v_hat| / 2 per link from the
rig, the contour divided by 2 F(t) / lambda (Hz to m/s of path-length rate per unit geometry), frames
with F < F_MASK masked. Every contour feature exists in RAW and COR form; shape features are
normalised by the pass's own median contour, so neither form carries an absolute speed.

FEATURE NAMES are `blk|kind|form|cadv|name`:
  blk   P (pass level) or RX1, RX2, RX3
  kind  rhy, pace, spat, dop, env, ctl (positive controls only), diag (never a feature)
  form  raw, cor or -;   cadv  lk (the link's own cadence), fu (the fused cadence) or -
"""

from __future__ import annotations

import numpy as np
from scipy import signal

from pipeline.identify import idmax_features as F
from pipeline.identify.id15_factor_map import bistatic_factor, wavelength_m
from pipeline.identify.idgp_contract import LINKS, PATHS, ContractPass, s_se

FS = 150.0
STEP_T_LO, STEP_T_HI = 0.35, 0.75
STEP_LO, STEP_HI = 1.0 / STEP_T_HI, 1.0 / STEP_T_LO          # 1.333 to 2.857 Hz
STEP_MID = float(np.sqrt(STEP_LO * STEP_HI))                    # tie-break only, 1.95 Hz
PERIODICITY_MIN = 0.2
AGREE_HZ = 0.1
F_MASK = 0.2
NPERSEG, HOP = 32, 4                                            # contour STFT, 37.5 frames per second
N_CYC = 16
LAMBDA_M = wavelength_m()                                       # channel 6; shapes do not depend on it


# ------------------------------------------------------------------ primitives

def _acf(x):
    x = np.asarray(x, float)
    x = x - np.nanmean(x)
    x = np.where(np.isfinite(x), x, 0.0)
    if not np.any(x):
        return np.zeros_like(x)
    n = len(x)
    f = np.fft.rfft(x, 2 * n)
    r = np.fft.irfft(f * np.conj(f))[:n]
    return r / max(r[0], 1e-12)


def _acf_rate(x, rate_hz: float) -> tuple:
    """(rate of the dominant autocorrelation peak between 0.3 and 2.2 s, its height) or (None, 0)."""
    r = _acf(x)
    lo, hi = int(0.3 * rate_hz), min(int(2.2 * rate_hz), len(r) - 2)
    if hi <= lo + 2:
        return None, 0.0
    pk, pr = signal.find_peaks(r[lo:hi + 1], height=0.0)
    if not len(pk):
        return None, 0.0
    k = int(pk[int(np.argmax(pr["peak_heights"]))] + lo)
    # parabolic refinement of the lag
    y0, y1, y2 = r[k - 1], r[k], r[k + 1]
    den = y0 - 2 * y1 + y2
    dk = 0.5 * (y0 - y2) / den if abs(den) > 1e-12 else 0.0
    return float(rate_hz / (k + float(np.clip(dk, -0.5, 0.5)))), float(r[k])


def _peak_rate(env) -> tuple:
    env = np.asarray(env, float)
    sd = np.std(env)
    if sd <= 0:
        return None, 0.0
    pk, _ = signal.find_peaks(env, distance=max(int(FS / STEP_HI), 2), prominence=0.3 * sd)
    if len(pk) < 3:
        return None, 0.0
    iv = np.diff(pk) / FS
    return float(1.0 / np.median(iv)), float(max(0.0, 1.0 - np.std(iv) / max(np.mean(iv), 1e-9)))


def _candidates(rate):
    if rate is None or not np.isfinite(rate) or rate <= 0:
        return []
    return [c for c in (0.5 * rate, rate, 2.0 * rate) if STEP_LO <= c <= STEP_HI]


def resolve(sources: list) -> dict:
    """Periodicity-weighted harmonic resolution. `sources` is a list of (name, rate, periodicity)."""
    kept = [(n, r, w) for n, r, w in sources if w >= PERIODICITY_MIN and _candidates(r)]
    out = {"cadence_hz": np.nan, "n_kept": len(kept), "n_sources": len(sources),
           "support_frac": 0.0}
    if not kept:
        return out
    cands = [(w, _candidates(r)) for _n, r, w in kept]
    pool = sorted({c for _w, cs in cands for c in cs})
    wsum = sum(w for w, _ in cands)
    best = None
    for c0 in pool:
        near = np.array([min(cs, key=lambda c: abs(c - c0)) for _w, cs in cands])
        ws = np.array([w for w, _ in cands])
        ok = np.abs(near - c0) <= AGREE_HZ
        sup = float(ws[ok].sum())
        dev = float(np.sum(ws * np.abs(near - c0)) / ws.sum())
        key = (-sup, dev, abs(np.log(c0 / STEP_MID)))
        if best is None or key < best[0]:
            best = (key, c0, near, ws, ok, sup)
    _k, c0, near, ws, ok, sup = best
    v, w = near[ok], ws[ok]
    o = np.argsort(v)
    cw = np.cumsum(w[o])
    out["cadence_hz"] = float(v[o][np.searchsorted(cw, 0.5 * cw[-1])])
    out["support_frac"] = sup / wsum
    return out


def envelope(a: np.ndarray) -> np.ndarray:
    """RMS across subcarriers of the 0.8 to 3.5 Hz amplitude, band-limited again: the motion envelope."""
    b = F.bandpass(a, "b08_35", axis=0)
    return F.bandpass(np.sqrt(np.mean(b * b, axis=1)), "b08_35")


def contours(a: np.ndarray) -> dict:
    """Per-frame percentile contours of the 4 to 70 Hz spectrogram of PCs 2 to 4 of one link."""
    P = F.reduce_link(a, "dop", "pca", n_pc=4)[1:]
    f, t, Z = signal.stft(P, fs=FS, nperseg=NPERSEG, noverlap=NPERSEG - HOP, nfft=64, axis=-1,
                          boundary=None, padded=False)
    mag = np.abs(Z).sum(axis=0).T                                  # (frames, freq)
    keep = (f >= 4.0) & (f <= 70.0)
    f, E = f[keep], mag[:, keep] ** 2
    c = np.cumsum(E, axis=1)
    tot = c[:, -1]
    ok = tot > 0
    cn = np.where(ok[:, None], c / np.maximum(tot[:, None], 1e-30), 0.0)
    out = {q: np.where(ok, f[np.clip(np.argmax(cn >= q / 100.0, axis=1), 0, len(f) - 1)], np.nan)
           for q in (25, 50, 75, 95)}
    out["t"] = t                                                   # frame centres, s from sample 0
    out["f"] = f
    out["E"] = E
    return out


def frame_F(cp: ContractPass, link: str, t_abs: np.ndarray) -> np.ndarray:
    """F at each frame time, steady progress along the path between the start and end presses."""
    a, b = (np.asarray(x, float) for x in PATHS[cp.path_id])
    u = np.clip((t_abs - cp.t_start) / cp.duration_s, 0.0, 1.0)
    pts = a[None, :] + u[:, None] * (b - a)[None, :]
    rig = cp.rig_dict()
    return bistatic_factor(pts, b - a, rig["TX"], rig[link])


# ------------------------------------------------------------------ contour features

def contour_features(C: dict, scale: np.ndarray, cadence_hz, fr: float) -> dict:
    """Shape features of one link's contours. `scale` converts each frame's Hz to the target unit
    (1 for RAW; lambda / (2 F) for COR, NaN where masked). Everything is normalised by the pass's own
    median torso contour, so no absolute rate enters."""
    out = {}
    cq = {q: C[q] * scale for q in (25, 50, 75, 95)}
    valid = np.isfinite(cq[50])
    if valid.sum() < 8:
        return out
    med = float(np.nanmedian(cq[50]))
    if not np.isfinite(med) or med <= 0:
        return out
    out["leg_torso"] = float(np.nanmedian(cq[95]) / med)
    out["q25_torso"] = float(np.nanmedian(cq[25]) / med)
    out["q75_torso"] = float(np.nanmedian(cq[75]) / med)
    for q in (50, 95):
        x = cq[q] / med
        out[f"c{q}_cv"] = float(np.nanstd(x) / max(np.nanmean(x), 1e-9))
        _r, h = _acf_rate(x, fr)
        out[f"c{q}_periodicity"] = h
        if cadence_hz and np.isfinite(cadence_hz):
            L = 2.0 * fr / cadence_hz                                 # frames per stride
            n_cyc = int(len(x) // L)
            if n_cyc >= 2:
                segs = []
                for k in range(n_cyc):
                    s = x[int(round(k * L)):int(round((k + 1) * L))]
                    if np.isfinite(s).sum() >= 0.6 * len(s):
                        idx = np.arange(len(s))
                        s = np.interp(idx, idx[np.isfinite(s)], s[np.isfinite(s)])
                        segs.append(np.interp(np.linspace(0, 1, N_CYC, endpoint=False),
                                              np.linspace(0, 1, len(s), endpoint=False), s))
                if len(segs) >= 2:
                    m = np.mean(segs, axis=0)
                    m = np.roll(m, -int(np.argmax(m)))
                    m = (m - m.mean()) / max(m.std(), 1e-9)
                    for i, v in enumerate(m):
                        out[f"c{q}_cyc{i:02d}"] = float(v)
    # the energy profile over frequency in units of the torso median
    E, f = C["E"], C["f"]
    prof = np.zeros(8)
    nfr = 0
    for j in np.flatnonzero(valid):
        u = f * scale[j] / med
        e = E[j]
        tot = e.sum()
        if tot <= 0:
            continue
        idx = np.floor(u / 0.5).astype(int)
        m = (idx >= 0) & (idx < 8)
        prof += np.bincount(idx[m], weights=e[m] / tot, minlength=8)[:8]
        nfr += 1
    if nfr:
        prof = prof / max(prof.sum(), 1e-20)
        for i, v in enumerate(prof):
            out[f"uprof_{i}"] = float(v)
    return out


def trend(cq50: np.ndarray, u: np.ndarray) -> float:
    """Slope of the normalised torso contour against walk progress (0 to 1): the geometry trend."""
    m = np.isfinite(cq50) & (u >= 0) & (u <= 1)
    if m.sum() < 8:
        return np.nan
    y = cq50[m] / np.nanmean(cq50[m])
    return float(np.polyfit(u[m], y, 1)[0])


# ------------------------------------------------------------------ rhythm

def rhythm(env: np.ndarray, cadence_hz) -> dict:
    out = {}
    if not cadence_hz or not np.isfinite(cadence_hz):
        return out
    out["cadence_hz"] = float(cadence_hz)
    out["stride_time_s"] = float(2.0 / cadence_hz)
    r = _acf(env)
    i1, i2 = int(round(FS / cadence_hz)), int(round(2 * FS / cadence_hz))
    if i2 < len(r):
        out["acf_step"] = float(r[i1])
        out["acf_stride"] = float(r[i2])
        out["sym_ratio"] = float(r[i1] / max(abs(r[i2]), 1e-3))
    pk, _ = signal.find_peaks(env, distance=max(int(0.6 * FS / cadence_hz), 2))
    if len(pk) >= 4:
        iv = np.diff(pk) / FS
        out["cad_var"] = float(np.std(iv) / max(np.mean(iv), 1e-9))
    return out


# ------------------------------------------------------------------ the pass

def link_signals(cp: ContractPass) -> dict:
    """Per link: the envelope and contours on the full amp (cadence) and on the walk (features)."""
    i0, i1 = cp.index_of(cp.t_start), cp.index_of(cp.t_end)
    full = cp.amp.astype(np.float64)
    walk = full[:, i0:i1, :]
    out = {}
    for li, link in enumerate(LINKS):
        d = {"env_walk": envelope(walk[li]), "C_walk": contours(walk[li])}
        if cp.margin_s > 0:
            d["env_cad"], d["C_cad"] = envelope(full[li]), contours(full[li])
        else:
            d["env_cad"], d["C_cad"] = d["env_walk"], d["C_walk"]
        out[link] = d
    return out


def cadence_sources(sig: dict) -> list:
    fr = FS / HOP
    env, C = sig["env_cad"], sig["C_cad"]
    r1, w1 = _acf_rate(env, FS)
    c50 = C[50]
    r2, w2 = _acf_rate(np.where(np.isfinite(c50), c50, np.nanmean(c50)), fr) \
        if np.isfinite(c50).sum() > 8 else (None, 0.0)
    r3, w3 = _peak_rate(env)
    return [("env", r1, w1), ("dop", r2, w2), ("peaks", r3, w3)]


def pass_features(cp: ContractPass) -> dict:
    """Every IDGP quantity of one pass. Receives the ContractPass only."""
    out = {}
    sig = link_signals(cp)
    fr = FS / HOP
    srcs = {L: cadence_sources(sig[L]) for L in LINKS}
    link_cad = {L: resolve(srcs[L]) for L in LINKS}
    fused = resolve([s for L in LINKS for s in srcs[L]])
    cf = fused["cadence_hz"]
    for L in LINKS:
        for n, r, w in srcs[L]:
            out[f"{L}|diag|-|-|src_{n}_hz"] = np.nan if r is None else r
            out[f"{L}|diag|-|-|src_{n}_per"] = w
        out[f"{L}|diag|-|-|cad_link_hz"] = link_cad[L]["cadence_hz"]
        out[f"{L}|diag|-|-|n_kept"] = link_cad[L]["n_kept"]
    out["P|diag|-|-|n_kept"] = fused["n_kept"]
    out["P|diag|-|-|support_frac"] = fused["support_frac"]
    out["P|diag|-|-|duration_s"] = cp.duration_s                  # diagnostic, never a feature
    out["P|diag|-|-|n_strides"] = cp.duration_s * cf / 2.0 if np.isfinite(cf) else np.nan

    # ---- pass level: fused rhythm, pace and spatial parameters
    rh = {}
    envs_ok = [L for L in LINKS if srcs[L][0][2] >= PERIODICITY_MIN] or list(LINKS)
    per_link_fu = {L: rhythm(sig[L]["env_walk"], cf) for L in LINKS}
    if np.isfinite(cf):
        rh = {"cadence_hz": cf, "stride_time_s": 2.0 / cf}
        for k in ("cad_var", "sym_ratio", "acf_step", "acf_stride"):
            v = [per_link_fu[L].get(k, np.nan) for L in envs_ok]
            rh[k] = float(np.nanmedian(v)) if np.isfinite(v).any() else np.nan
    for k, v in rh.items():
        out[f"P|rhy|-|fu|{k}"] = v
    sp = s_se(cp)
    out["P|pace|-|-|S_se"] = sp
    if np.isfinite(cf):
        out["P|spat|-|fu|step_length_m"] = sp / cf
        out["P|spat|-|fu|walk_ratio"] = sp / cf ** 2

    # ---- per link
    t_abs0 = cp.t_start                                            # walk contours start at t_start
    for L in LINKS:
        S = sig[L]
        C = S["C_walk"]
        t_abs = t_abs0 + C["t"]
        Fv = frame_F(cp, L, t_abs)
        u = np.clip((t_abs - cp.t_start) / cp.duration_s, 0.0, 1.0)
        cor = np.where(Fv >= F_MASK, LAMBDA_M / (2.0 * np.maximum(Fv, 1e-9)), np.nan)
        raw = np.ones_like(Fv)
        cl = link_cad[L]["cadence_hz"]
        for form, sc in (("raw", raw), ("cor", cor)):
            for cadv, c in (("lk", cl), ("fu", cf)):
                for k, v in contour_features(C, sc, c, fr).items():
                    if cadv == "fu" and "_cyc" not in k:
                        continue                                   # identical to the lk value
                    out[f"{L}|dop|{form}|{cadv}|{k}"] = v
            out[f"{L}|diag|{form}|-|trend"] = trend(C[50] * sc, u)
            out[f"{L}|diag|{form}|-|torso_median"] = float(np.nanmedian(C[50] * sc)) \
                if np.isfinite(C[50] * sc).any() else np.nan
        out[f"{L}|diag|-|-|frac_masked"] = float(np.mean(~np.isfinite(cor)))
        out[f"{L}|diag|-|-|mean_F"] = float(np.mean(Fv))
        for k, v in rhythm(S["env_walk"], cl).items():
            out[f"{L}|rhy|-|lk|{k}"] = v
        for k, v in per_link_fu[L].items():
            if k not in ("cadence_hz", "stride_time_s"):
                out[f"{L}|rhy|-|fu|{k}"] = v
        for k, v in F.spectral_shape(S["env_walk"], "b08_35").items():
            out[f"{L}|env|-|-|{k}"] = v
        li = LINKS.index(L)
        for k, v in F.profile_features(cp.walk()[li].astype(np.float64)).items():
            out[f"{L}|ctl|-|-|{k}"] = v
    return {k: (float(v) if v is not None else np.nan) for k, v in out.items()}


# ------------------------------------------------------------------ S_csi, the unbounded variant

def csi_walk_bounds(amp_full: np.ndarray, fs: float = FS) -> tuple:
    """Onset and offset sample of the walk from motion energy alone. No press, anchor or window
    offset is used: the threshold, smoothing and gap rule are fixed constants."""
    e = []
    for li in range(amp_full.shape[0]):
        b = F.bandpass(np.asarray(amp_full[li], float), "full", axis=0)
        e.append(np.sqrt(np.mean(b * b, axis=1)))
    e = np.mean(e, axis=0)
    k = int(0.5 * fs)
    e = np.convolve(e, np.ones(k) / k, mode="same")
    lo, hi = np.percentile(e, 20), np.percentile(e, 95)
    on = e > lo + 0.3 * (hi - lo)
    # merge gaps shorter than 0.3 s
    idx = np.flatnonzero(np.diff(np.r_[0, on.astype(int), 0]))
    runs = list(zip(idx[::2], idx[1::2]))
    merged = []
    for a, b in runs:
        if merged and a - merged[-1][1] < int(0.3 * fs):
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    if not merged:
        return None, None
    a, b = max(merged, key=lambda r: r[1] - r[0])
    return int(a), int(b)
