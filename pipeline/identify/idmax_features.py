# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: IDMAX feature layer: every gait feature of section 8 B, computed from the id19 signal bank.

from __future__ import annotations

import numpy as np
from scipy import signal
from scipy.fft import dct

FS = 150.0
STEP_LO, STEP_HI = 1.3, 2.8
PHASE = 32
BANDS = {"b03_2": (0.3, 2.0), "b08_35": (0.8, 3.5), "dop": (4.0, 70.0), "full": (0.3, 70.0)}
STFT_WINDOWS_S = (0.1, 0.2, 0.43)
NOTCH_HZ = 50.5



# Function bandpass.
def bandpass(x: np.ndarray, band: str, fs: float = FS, axis: int = 0) -> np.ndarray:
    lo, hi = BANDS[band]
    nyq = fs / 2.0
    hi = min(hi, 0.95 * nyq)
    sos = signal.butter(4, [lo / nyq, hi / nyq], btype="bandpass", output="sos")
    return signal.sosfiltfilt(sos, np.asarray(x, float), axis=axis)


# Function notch.
def notch(x: np.ndarray, fs: float = FS, axis: int = 0) -> np.ndarray:
    b, a = signal.iirnotch(NOTCH_HZ, 30.0, fs=fs)
    return signal.filtfilt(b, a, np.asarray(x, float), axis=axis)


# Function static removal.
def static_removal(a: np.ndarray, mode: str, fs: float = FS) -> np.ndarray:
    if mode == "none":
        return a
    if mode == "runmean":
        from scipy.ndimage import uniform_filter1d
        return a - uniform_filter1d(a, size=int(fs), axis=0, mode="nearest")
    raise ValueError(mode)


# (n, n_sub) amplitude of ONE link -> (n_channels, n) band-limited channels.
def reduce_link(a: np.ndarray, band: str, reduction: str, n_pc: int = 6,
                bmat: np.ndarray = None) -> np.ndarray:
    a = np.asarray(a, float)
    if reduction == "mean":
        return bandpass(a.mean(axis=1), band)[None, :]
    b = bandpass(a, band, axis=0) if bmat is None else bmat
    if reduction == "rms":
        e = np.sqrt(np.mean(b * b, axis=1))
        return bandpass(e, "b03_2" if band == "b03_2" else "b08_35")[None, :]
    if reduction == "pca":
        b = b - b.mean(axis=0, keepdims=True)
        w, V = np.linalg.eigh(b.T @ b)
        V = V[:, np.argsort(w)[::-1][:n_pc]]
        comp = (b @ V).T
        for i in range(comp.shape[0]):
            if np.mean(comp[i] ** 3) < 0:
                comp[i] = -comp[i]
        return comp
    raise ValueError(reduction)



# Function acf.
def _acf(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, float) - np.mean(x)
    if not np.any(x):
        return np.zeros_like(x)
    n = len(x)
    f = np.fft.rfft(x, 2 * n)
    r = np.fft.irfft(f * np.conj(f))[:n]
    return r / max(r[0], 1e-12)


# The three raw estimates, before harmonic resolution.
def cadence_estimates(x: np.ndarray, fs: float = FS) -> dict:
    x = np.asarray(x, float)
    out = {"welch": None, "acf_cycle": None, "peaks": None, "acf_peak": None}
    if len(x) < int(1.5 * fs):
        return out
    f, p = signal.welch(x, fs=fs, nperseg=min(len(x), 512), nfft=4096)
    m = (f >= 0.5) & (f <= STEP_HI)
    if m.any():
        out["welch"] = float(f[m][np.argmax(p[m])])
    r = _acf(x)
    lo, hi = int(0.3 * fs), min(int(2.2 * fs), len(r) - 1)
    if hi > lo + 3:
        pk, pr = signal.find_peaks(r[lo:hi], height=0.0)
        if len(pk):
            k = pk[int(np.argmax(pr["peak_heights"]))] + lo
            out["acf_cycle"] = float(fs / k)
            out["acf_peak"] = float(r[k])
    pk, _ = signal.find_peaks(x, distance=max(int(fs / STEP_HI), 2),
                              prominence=0.3 * np.std(x) if np.std(x) > 0 else None)
    if len(pk) >= 3:
        out["peaks"] = float(fs / np.median(np.diff(pk)))
    return out


# Function candidates.
def _candidates(v):
    if v is None or not np.isfinite(v) or v <= 0:
        return []
    return [c for c in (0.5 * v, v, 2.0 * v) if STEP_LO <= c <= STEP_HI]


# Harmonic resolution BY AGREEMENT across estimators and links.
def resolve_cadence(estimate_sets: list) -> dict:
    cands = []
    for es in estimate_sets:
        for k in ("welch", "acf_cycle", "peaks"):
            cands.append((k, _candidates(es.get(k))))
    pool = sorted({c for _k, cs in cands for c in cs})
    if not pool:
        return {"cadence_hz": None, "agree_frac": 0.0, "n_estimates": 0}
    best = None
    for c0 in pool:
        near = [min(cs, key=lambda c: abs(c - c0)) for _k, cs in cands if cs]
        near = np.asarray(near)
        support = int(np.sum(np.abs(near - c0) <= 0.1))
        score = (-support, float(np.median(np.abs(near - c0))))
        if best is None or score < best[0]:
            best = (score, c0, near)
    _s, c0, near = best
    agree = np.abs(near - c0) <= 0.1
    return {"cadence_hz": float(np.median(near[agree])) if agree.any() else float(c0),
            "agree_frac": float(agree.mean()), "n_estimates": int(len(near))}



# Step and stride structure given the RESOLVED cadence.
def rhythm_features(x: np.ndarray, cadence_hz, fs: float = FS) -> dict:
    out = {}
    x = np.asarray(x, float)
    r = _acf(x)
    if not cadence_hz:
        return out
    step = fs / cadence_hz
    stride = 2.0 * step
    i_step, i_stride = int(round(step)), int(round(stride))
    if i_stride < len(r) - 1:
        out["acf_step"] = float(r[i_step])
        out["acf_stride"] = float(r[i_stride])
        out["step_symmetry"] = float(r[i_step] / max(abs(r[i_stride]), 1e-6))
        lag = np.linspace(0, min(2.0 * stride, len(r) - 1), 2 * PHASE)
        acf_shape = np.interp(lag, np.arange(len(r)), r)
        for i, v in enumerate(acf_shape[1:]):
            out[f"acfshape_{i:02d}"] = float(v)
    pk, _ = signal.find_peaks(x, distance=max(int(0.6 * step), 2))
    if len(pk) >= 4:
        iv = np.diff(pk) / fs
        out["step_cv"] = float(np.std(iv) / max(np.mean(iv), 1e-9))
        out["step_alt"] = float(np.mean(np.abs(np.diff(iv))) / max(np.mean(iv), 1e-9))
    f, p = signal.welch(x, fs=fs, nperseg=min(len(x), 512), nfft=4096)

    # Function pw.
    def pw(h, w=0.15):
        m = (f >= h - w) & (f <= h + w)
        return float(p[m].sum()) if m.any() else 0.0
    tot = max(float(p[(f >= 0.3) & (f <= 8.0)].sum()), 1e-20)
    out["rel_pow_stride"] = pw(cadence_hz / 2) / tot
    out["rel_pow_step"] = pw(cadence_hz) / tot
    out["rel_pow_3h"] = pw(1.5 * cadence_hz) / tot
    out["rel_pow_2step"] = pw(2 * cadence_hz) / tot
    out["cadence_sharpness"] = pw(cadence_hz, 0.05) / max(pw(cadence_hz, 0.3), 1e-20)
    return out


# Stride-normalised gait cycles.
def cycle_templates(x: np.ndarray, cadence_hz, fs: float = FS, method: str = "acf") -> dict:
    out = {}
    if not cadence_hz:
        return out
    x = np.asarray(x, float)
    stride = int(round(2.0 * fs / cadence_hz))
    if method == "acf":
        starts = list(range(0, len(x) - stride + 1, stride))
        segs = [x[s:s + stride] for s in starts]
    else:
        pk, _ = signal.find_peaks(x, distance=max(int(0.6 * stride / 2), 2))
        segs = [x[pk[i]:pk[i + 2]] for i in range(0, len(pk) - 2, 2)
                if 0.6 * stride <= pk[i + 2] - pk[i] <= 1.4 * stride]
    if len(segs) < 2:
        return out
    P = np.vstack([np.interp(np.linspace(0, 1, PHASE, endpoint=False),
                             np.linspace(0, 1, len(s), endpoint=False), s) for s in segs])
    ref = P[0] - P[0].mean()
    A = []
    for c in P:
        c0 = c - c.mean()
        xc = np.real(np.fft.ifft(np.fft.fft(c0) * np.conj(np.fft.fft(ref))))
        A.append(np.roll(c, -int(np.argmax(xc))))
    A = np.asarray(A)
    m = A.mean(axis=0)
    m = np.roll(m, -int(np.argmax(m)))
    sd = np.std(m)
    tpl = (m - m.mean()) / sd if sd > 0 else m * 0
    for i, v in enumerate(tpl):
        out[f"tpl_{i:02d}"] = float(v)
    H = np.abs(np.fft.rfft(tpl))[1:9]
    H = H / max(H.sum(), 1e-12)
    for i, v in enumerate(H):
        out[f"tplharm_{i + 1}"] = float(v)
    Az = (A - A.mean(axis=1, keepdims=True)) / np.maximum(A.std(axis=1, keepdims=True), 1e-12)
    out["cycle_var"] = float(np.mean(np.std(Az, axis=0)))
    cc = [np.corrcoef(Az[i], Az[i + 1])[0, 1] for i in range(len(Az) - 1)]
    out["cycle_corr"] = float(np.nanmean(cc))
    h = PHASE // 2
    out["half_cycle_sym"] = float(np.corrcoef(tpl[:h], tpl[h:])[0, 1])
    return out


# Function template vector.
def template_vector(feats: dict) -> np.ndarray:
    return np.asarray([feats.get(f"tpl_{i:02d}", np.nan) for i in range(PHASE)], float)



# Relative band powers, centroid and spread IN UNITS OF THE BAND (0 to 1), and cepstral coefficients of the...
def spectral_shape(x: np.ndarray, band: str, fs: float = FS, n_rel: int = 8,
                   n_cep: int = 12) -> dict:
    lo, hi = BANDS[band]
    hi = min(hi, 0.95 * fs / 2)
    f, p = signal.welch(np.asarray(x, float), fs=fs, nperseg=min(len(x), 512), nfft=4096)
    m = (f >= lo) & (f <= hi)
    if m.sum() < n_rel:
        return {}
    fb, pb = f[m], p[m]
    tot = max(pb.sum(), 1e-20)
    out = {}
    edges = np.linspace(lo, hi, n_rel + 1)
    E = []
    for i in range(n_rel):
        k = (fb >= edges[i]) & (fb < edges[i + 1])
        E.append(pb[k].sum() / tot)
        out[f"relpow_{i}"] = float(E[-1])
    u = (fb - lo) / (hi - lo)
    c = float(np.sum(u * pb) / tot)
    out["centroid_u"] = c
    out["spread_u"] = float(np.sqrt(np.sum((u - c) ** 2 * pb) / tot))
    out["flatness"] = float(np.exp(np.mean(np.log(pb + 1e-20))) / (np.mean(pb) + 1e-20))
    edges2 = np.linspace(lo, hi, 2 * n_cep + 1)
    fbank = np.asarray([pb[(fb >= edges2[i]) & (fb < edges2[i + 1])].sum() + 1e-20
                        for i in range(2 * n_cep)])
    cep = dct(np.log(fbank / tot), norm="ortho")[1:n_cep + 1]
    for i, v in enumerate(cep):
        out[f"cep_{i + 1:02d}"] = float(v)
    return out



# Percentile contours of the path-rate spectrogram, as SHAPES normalised by the pass's own median torso contour.
def doppler_features(x: np.ndarray, fs: float = FS, win_s: float = 0.2,
                     cadence_hz=None) -> dict:
    x = np.atleast_2d(np.asarray(x, float))
    n = int(round(win_s * fs))
    if x.shape[1] < 4 * n:
        return {}
    f, t, Z = signal.stft(x, fs=fs, nperseg=n, noverlap=int(0.75 * n), axis=-1, nfft=max(n, 64))
    mag = np.abs(Z).sum(axis=0).T
    keep = (f >= 4.0) & (f <= 0.95 * fs / 2)
    f, mag = f[keep], mag[:, keep]
    P = mag ** 2
    c = np.cumsum(P, axis=1)
    tot = c[:, -1:]
    ok = tot[:, 0] > 0
    if ok.sum() < 8:
        return {}
    cn = c[ok] / tot[ok]
    cont = {q: f[np.clip(np.argmax(cn >= q / 100.0, axis=1), 0, len(f) - 1)]
            for q in (25, 50, 75, 95)}
    med50 = max(float(np.median(cont[50])), 1e-6)
    out = {"leg_torso": float(np.median(cont[95]) / med50),
           "q25_torso": float(np.median(cont[25]) / med50),
           "q75_torso": float(np.median(cont[75]) / med50)}
    fr = 1.0 / max(np.median(np.diff(t)), 1e-9)
    for q in (50, 95):
        cq = cont[q] / med50
        out[f"c{q}_cv"] = float(np.std(cq) / max(np.mean(cq), 1e-9))
        r = _acf(cq)
        lo, hi = int(0.3 * fr), min(int(2.2 * fr), len(r) - 1)
        out[f"c{q}_periodicity"] = float(r[lo:hi].max()) if hi > lo else np.nan
        if cadence_hz:
            L = int(round(2.0 * fr / cadence_hz))
            segs = [cq[s:s + L] for s in range(0, len(cq) - L + 1, L)] if L >= 4 else []
            if len(segs) >= 2:
                Pc = np.vstack([np.interp(np.linspace(0, 1, 16, endpoint=False),
                                          np.linspace(0, 1, len(s), endpoint=False), s)
                                for s in segs]).mean(axis=0)
                Pc = np.roll(Pc, -int(np.argmax(Pc)))
                Pc = (Pc - Pc.mean()) / max(Pc.std(), 1e-9)
                for i, v in enumerate(Pc):
                    out[f"c{q}_cyc{i:02d}"] = float(v)
    fr_u = f / med50
    prof = np.asarray([P[:, (fr_u >= a) & (fr_u < a + 0.5)].mean() if ((fr_u >= a) & (fr_u < a + 0.5)).any()
                       else 0.0 for a in np.arange(0, 4.0, 0.5)])
    prof = prof / max(prof.sum(), 1e-20)
    for i, v in enumerate(prof):
        out[f"uprof_{i}"] = float(v)
    return out



# Relative DWT energy per level (db4, 7 levels) and relative CWT (Morlet) energy over 12 log-spaced scales...
def wavelet_features(x: np.ndarray, fs: float = FS) -> dict:
    import pywt
    x = np.asarray(x, float)
    out = {}
    lev = min(7, pywt.dwt_max_level(len(x), pywt.Wavelet("db4").dec_len))
    if lev >= 3:
        co = pywt.wavedec(x, "db4", level=lev)
        e = np.asarray([np.sum(c ** 2) for c in co[1:]])
        e = e / max(e.sum(), 1e-20)
        for i, v in enumerate(e):
            out[f"dwt_{i}"] = float(v)
    freqs = np.geomspace(0.5, 20.0, 12)
    xd = signal.decimate(x, 3, zero_phase=True)
    scales = pywt.central_frequency("morl") * (fs / 3.0) / freqs
    try:
        coef, _ = pywt.cwt(xd, scales, "morl", sampling_period=3.0 / fs)
        e = np.mean(np.abs(coef) ** 2, axis=1)
        e = e / max(e.sum(), 1e-20)
        for i, v in enumerate(e):
            out[f"cwt_{i:02d}"] = float(v)
    except Exception:
        pass
    return out



# How strongly the walk modulates the link, RELATIVE to the link's own level in this pass.
def modulation_features(a_link: np.ndarray, rssi: np.ndarray, b_gait: np.ndarray = None,
                        b_dop: np.ndarray = None) -> dict:
    a = np.asarray(a_link, float)
    lvl = max(float(a.mean()), 1e-6)
    g = bandpass(a.mean(axis=1), "b08_35")
    bd = bandpass(a, "dop", axis=0) if b_dop is None else b_dop
    bg = bandpass(a, "b08_35", axis=0) if b_gait is None else b_gait
    d = bandpass(np.sqrt(np.mean(bd ** 2, axis=1)), "b08_35")
    r = np.asarray(rssi, float)
    return {"moddepth_gait": float(np.std(g) / lvl),
            "moddepth_dop": float(np.std(d) / lvl),
            "sub_dispersion": float(np.median(np.std(bg, axis=0)) / max(np.std(g), 1e-9)),
            "rssi_std": float(np.std(r - np.median(r)))}


# The motion-energy time course over the segment, resampled to n_pts and normalised to unit sum: WHERE in...
def profile_features(a_link: np.ndarray, n_pts: int = 16, b_full: np.ndarray = None) -> dict:
    b = bandpass(np.asarray(a_link, float), "full", axis=0) if b_full is None else b_full
    e = np.sqrt(np.mean(b * b, axis=1))
    idx = np.linspace(0, len(e), n_pts + 1).astype(int)
    v = np.asarray([e[idx[i]:max(idx[i + 1], idx[i] + 1)].mean() for i in range(n_pts)])
    v = v / max(v.sum(), 1e-20)
    return {f"prof_{i:02d}": float(x) for i, x in enumerate(v)}


# RECORDING-SIGNATURE REFERENCE ONLY.
def recsig_features(a_link: np.ndarray, rssi: np.ndarray) -> dict:
    m = np.asarray(a_link, float).mean(axis=0)
    out = {f"lvl_{i:03d}": float(v) for i, v in enumerate(m)}
    out["rssi_mean"] = float(np.mean(rssi))
    return out
