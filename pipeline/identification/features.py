# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: I8, a walk's gait features: band-passing each receiver's subcarriers, reducing them to a few channels, the...

from __future__ import annotations

import numpy as np
from scipy import signal



FS = 150.0
STEP_LO, STEP_HI = 1.3, 2.8
BANDS = {"b03_2": (0.3, 2.0), "b08_35": (0.8, 3.5), "dop": (4.0, 70.0), "full": (0.3, 70.0)}


# Function bandpass.
def bandpass(x: np.ndarray, band: str, fs: float = FS, axis: int = 0) -> np.ndarray:
    lo, hi = BANDS[band]
    nyq = fs / 2.0
    hi = min(hi, 0.95 * nyq)
    sos = signal.butter(4, [lo / nyq, hi / nyq], btype="bandpass", output="sos")
    return signal.sosfiltfilt(sos, np.asarray(x, float), axis=axis)


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



DROP = sorted({0, 1, 64} | set(range(27, 38)) | set(range(96, 104)))


KEEP = np.array([i for i in range(128) if i not in DROP])


# Function interp cols.
def _interp_cols(tq: np.ndarray, t: np.ndarray, a: np.ndarray) -> np.ndarray:
    j = np.clip(np.searchsorted(t, tq) - 1, 0, len(t) - 2)
    t0, t1 = t[j], t[j + 1]
    w = np.clip((tq - t0) / np.maximum(t1 - t0, 1e-9), 0.0, 1.0)
    if a.ndim == 1:
        return a[j] * (1 - w) + a[j + 1] * w
    return a[j] * (1 - w)[:, None] + a[j + 1] * w[:, None]


NULL_SC = (93, 94, 95)
SC = np.array([i for i, k in enumerate(KEEP) if k not in NULL_SC])
CADENCE_CH = [("mean", "b08_35"), ("rms", "b08_35"), ("pca", "b08_35")]


# Function columns v2.
def columns_v2(bank) -> np.ndarray:
    import pipeline.identification.classifiers as L
    cols = L.loso_columns("U_all_gait")
    names = np.array(bank["names"])
    return np.array([j for j in cols if not names[j].endswith("|dwt_6")])


# The conditioned map from an already band-limited (4 to 70 Hz) pass: per-pass PCA (PCs 2 to 4, skew sign)...
def _map_from_bmat(bm_dop: np.ndarray) -> np.ndarray:
    from scipy import signal
    P = reduce_link(bm_dop, "dop", "pca", n_pc=4, bmat=bm_dop)[1:]
    s = C.HP["stft"]
    _f, _t, Z = signal.stft(P, fs=C.HP["fs"], nperseg=s["nperseg"], noverlap=s["noverlap"], nfft=s["nfft"],
                            axis=-1, boundary=None, padded=False)
    mag = np.abs(Z).sum(axis=0)[C.KEEP_F]
    eps = 1e-6 * (float(np.median(mag)) if mag.size and np.median(mag) > 0 else 1.0)
    m = np.log(mag + eps)
    return (m - m.mean()).astype(np.float32)


# Function conditioned map v2.
def conditioned_map_v2(a_link: np.ndarray) -> np.ndarray:
    return _map_from_bmat(bandpass(np.asarray(a_link, float), "dop", axis=0))


# Subcarrier amplitude from the raw interleaved int8 payload, vectorised over packets.
def amplitude_from_frames(sub) -> np.ndarray:
    d = np.asarray(sub["data"], np.int8).astype(np.float32)
    imag, real = d[:, 0::2], d[:, 1::2]
    return np.sqrt(imag * imag + real * real)


# (f, P) with P (freq, frames): Hampel, then PCs 2 to 4 of the 4 to 70 Hz band, or every subcarrier when pca...
def conditioned_spectrogram(seg: np.ndarray, pca: bool = True):
    from scipy import signal
    a = c2_hampel(seg)
    X = reduce_link(a, "dop", "pca", n_pc=4)[1:] if pca else bandpass(a, "dop", axis=0).T
    f, _t, Z = signal.stft(X, fs=FS, nperseg=32, noverlap=24, nfft=64, axis=-1, boundary=None, padded=False)
    return f, (np.abs(Z) ** 2).sum(axis=0)



# Hampel outlier removal per subcarrier, median window k, replace beyond n_sigma MAD.
def c2_hampel(amp: np.ndarray, k: int = 7, n_sigma: float = 3.0) -> np.ndarray:
    a = np.asarray(amp, float).copy()
    if a.shape[0] < 2 * k + 1:
        return a
    from scipy.ndimage import median_filter
    med = median_filter(a, size=(2 * k + 1, 1), mode="nearest")
    mad = median_filter(np.abs(a - med), size=(2 * k + 1, 1), mode="nearest")
    thr = n_sigma * 1.4826 * mad
    bad = np.abs(a - med) > np.maximum(thr, 1e-12)
    a[bad] = med[bad]
    return a


import pipeline.identification.classifiers as C
