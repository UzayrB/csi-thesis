"""C0 to C7: the identification conditioning chain. Switchable per stage, for R1 and R2.

SCOPE. This chain belongs to the IDENTIFICATION branch and to nothing else. It never touches the
common cleaner, `pipeline/io/clean.py`, or the tracking transform. The tracking chain applies a
2 Hz lowpass that removes the step rhythm entirely, which is exactly the content this chain exists
to keep, and the two must never be confused. Figure F2 shows one pass through both.

PORTED, NOT IMPORTED. `bandpass`, `notch` and `doppler_spectrogram` are ported from
`testing/pipeline/branches/id_branch.py`, which is the archived pre-pivot identification branch.
`testing/` is never imported by the shipping model, so the code is copied here with attribution
rather than called across that boundary, and the archived tests are ported alongside it. The
archived constants are carried over unchanged:

  NOTCH_HZ 50.5   the room's line, measured 10 September 2026 at 0.25 Hz resolution
  NOTCH_Q  30     bandwidth about 1.7 Hz, the line's one-to-two-bin width and little else
  8.13 Hz per m/s per unit geometric factor, at channel 11, lambda 0.123 m

WHY THE LINE MATTERS HERE. The 50.5 Hz line appeared mid-morning on day 2 and sits INSIDE the
path-rate band. The archived branch's working explanation is a mechanical component near twice
mains, 99.5 Hz, folded by the 150 Hz sampling to 150 - 99.5 = 50.5 Hz. If it is not removed,
session 02 carries a day-specific artefact, and that is the pre-registered falsifiable prediction
this chain exists to test.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Optional, Sequence

import numpy as np
from scipy import signal

#: ported from testing/pipeline/branches/id_branch.py, unchanged
NOTCH_HZ = 50.5
NOTCH_Q = 30.0
DOPPLER_HZ_PER_MPS_PER_UNIT_FACTOR = 8.13

#: C7. Band (a) is the current envelope band; band (b) is the path-rate band this run adds.
BAND_A = (0.8, 3.5)
BAND_B_LO = 4.0

STAGES = ("C1", "C2", "C3", "C4", "C5", "C6")


@dataclass(frozen=True)
class Chain:
    """Which stages are on. Leave-one-stage-out is `Chain.full().without('C4')`."""
    on: tuple = STAGES
    c3_mode: str = "auto"          # auto | exact | normalise | null
    c5_mode: str = "running_mean"  # running_mean | svd
    c6_drop_pc1: bool = True
    c6_keep: int = 4
    notch_hz: tuple = (NOTCH_HZ,)

    @staticmethod
    def full() -> "Chain":
        return Chain()

    def without(self, stage: str) -> "Chain":
        return Chain(tuple(s for s in self.on if s != stage), self.c3_mode, self.c5_mode,
                     self.c6_drop_pc1, self.c6_keep, self.notch_hz)

    def upto(self, stage: str) -> "Chain":
        i = STAGES.index(stage)
        return Chain(tuple(STAGES[:i + 1]), self.c3_mode, self.c5_mode,
                     self.c6_drop_pc1, self.c6_keep, self.notch_hz)

    def has(self, stage: str) -> bool:
        return stage in self.on


# ----------------------------------------------------------------- C1

def c1_resample(amp: np.ndarray, t: np.ndarray, fs: float,
                gap_rule_s: float = 0.05) -> tuple:
    """Timestamp-based resampling onto a uniform grid. Gaps are MARKED, never interpolated across.

    A gap longer than `gap_rule_s` is a stretch of time where nothing was received. Interpolating
    through it invents motion that was never observed, and in a spectrogram that invention lands as
    broadband energy at exactly the moment the person was least observable. The samples are marked
    invalid instead and every downstream statistic skips them.
    """
    a = np.asarray(amp, float)
    t = np.asarray(t, float)
    if a.ndim != 2 or len(t) != a.shape[0]:
        raise ValueError(f"expected (n_samples, n_sub) with matching t, got {a.shape}, {t.shape}")
    order = np.argsort(t)
    t, a = t[order], a[order]
    grid = np.arange(t[0], t[-1], 1.0 / fs)
    out = np.empty((len(grid), a.shape[1]), float)
    for j in range(a.shape[1]):
        out[:, j] = np.interp(grid, t, a[:, j])
    dt = np.diff(t)
    bad = np.zeros(len(grid), bool)
    for i in np.flatnonzero(dt > gap_rule_s):
        bad |= (grid >= t[i]) & (grid <= t[i + 1])
    return out, grid, bad


# ----------------------------------------------------------------- C2

def c2_hampel(amp: np.ndarray, k: int = 7, n_sigma: float = 3.0) -> np.ndarray:
    """Hampel outlier removal per subcarrier, median window `k`, replace beyond `n_sigma` MAD."""
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


# ----------------------------------------------------------------- C3

def c3_gain(amp: np.ndarray, gain: Optional[np.ndarray] = None, mode: str = "auto") -> tuple:
    """AGC handling. Addendum B fixes which of three forms this takes, by MEASUREMENT.

    exact      divide by the logged per-packet gain. Exact, and it KEEPS body shadowing.
    normalise  divide each packet by its mean across subcarriers. Gain-invariant, but it also
               removes genuine broadband amplitude change, which is what shadow depth measures.
    null       do nothing, and record that nothing was needed.
    """
    a = np.asarray(amp, float)
    if mode == "auto":
        varies = gain is not None and len(np.unique(np.asarray(gain))) > 1
        mode = "exact" if varies else "null"
    if mode == "exact":
        g = np.asarray(gain, float).reshape(-1, 1)
        return a / np.maximum(g, 1e-9), mode
    if mode == "normalise":
        m = a.mean(axis=1, keepdims=True)
        return a / np.maximum(m, 1e-9), mode
    return a, "null"


def shared_step_discontinuities(amp: np.ndarray, z: float = 6.0) -> dict:
    """Detect gain changes: a step shared by ALL subcarriers at ONE instant.

    A body moving through the room changes subcarriers differently, because it changes some paths
    and not others. A gain change scales every subcarrier at once. That difference is the signature,
    and it is what decides between the null and normalise branches of C3.
    """
    a = np.asarray(amp, float)
    if a.shape[0] < 3:
        return {"rate_per_s": 0.0, "n": 0}
    d = np.diff(np.log(np.maximum(a, 1e-12)), axis=0)
    med = np.median(d, axis=1)
    spread = np.median(np.abs(d - med[:, None]), axis=1)
    s = np.median(np.abs(med)) + 1e-12
    shared = (np.abs(med) > z * s) & (spread < np.median(spread))
    return {"n": int(shared.sum()), "frac_samples": float(shared.mean()),
            "why": "a step in the median across subcarriers with LOW spread is a gain change"}


# ----------------------------------------------------------------- C4 (ported)

@lru_cache(maxsize=16)
def _notch_sos(fs: float, f0: float, q: float) -> np.ndarray:
    b, a = signal.iirnotch(f0, q, fs=fs)
    return signal.tf2sos(b, a)


def c4_notch(amp: np.ndarray, fs: float, f0: float = NOTCH_HZ, q: float = NOTCH_Q) -> np.ndarray:
    """PORTED from id_branch.notch. Zero-phase narrow notch, per subcarrier."""
    a = np.asarray(amp, float)
    if a.ndim != 2:
        raise ValueError(f"expected (n_samples, n_sub), got {a.shape}")
    if a.shape[0] < 20:
        return a.astype(np.float32)
    sos = _notch_sos(float(fs), float(f0), float(q))
    pad = min(3 * 3 * 4, a.shape[0] - 1)
    return signal.sosfiltfilt(sos, a, axis=0, padlen=pad).astype(np.float32)


# ----------------------------------------------------------------- C5

def c5_static(amp: np.ndarray, fs: float, mode: str = "running_mean",
              win_s: float = 1.0) -> np.ndarray:
    """Static-path removal. Running-mean subtraction, or SVD first-component removal."""
    a = np.asarray(amp, float)
    if mode == "svd":
        if min(a.shape) < 2:
            return a
        U, S, Vt = np.linalg.svd(a - a.mean(0, keepdims=True), full_matrices=False)
        S1 = S.copy()
        S1[0] = 0.0
        return (U * S1) @ Vt
    from scipy.ndimage import uniform_filter1d
    w = max(int(win_s * fs), 3)
    return a - uniform_filter1d(a, size=w, axis=0, mode="nearest")


# ----------------------------------------------------------------- C6

def c6_subcarriers(amp: np.ndarray, drop_pc1: bool = True, keep: int = 4) -> tuple:
    """Drop dead subcarriers, then PCA ACROSS subcarriers, fitted PER RECORDING.

    Per-recording, label-free fitting is declared exception (a) in the pre-registration. The CARM
    convention discards PC1, which carries the bulk static reflection; whether that helps here is
    an ablation, not an assumption.
    """
    a = np.asarray(amp, float)
    sd = a.std(axis=0)
    keep_sub = sd > (1e-6 + 0.01 * np.median(sd))
    a = a[:, keep_sub] if keep_sub.sum() >= 2 else a
    a = a - a.mean(axis=0, keepdims=True)
    U, S, Vt = np.linalg.svd(a, full_matrices=False)
    comp = (U * S)
    start = 1 if drop_pc1 else 0
    return comp[:, start:start + keep], {"n_subcarriers_kept": int(keep_sub.sum()),
                                         "dropped_pc1": bool(drop_pc1),
                                         "n_components": int(keep)}


# ----------------------------------------------------------------- C7 (ported spectrogram)

def c7_bands(x: np.ndarray, fs: float, notch_hz: Sequence = (NOTCH_HZ,),
             band_a=BAND_A, band_b_lo: float = BAND_B_LO) -> dict:
    """Split into band (a), the envelope band, and band (b), the path-rate band."""
    a = np.asarray(x, float)
    if a.ndim == 1:
        a = a[:, None]
    nyq = fs / 2.0
    hi_b = min(0.98 * nyq, nyq - 2.0)
    out = {}
    if a.shape[0] > 30:
        sos_a = signal.butter(4, [band_a[0] / nyq, band_a[1] / nyq], btype="bandpass", output="sos")
        out["band_a"] = signal.sosfiltfilt(sos_a, a, axis=0)
        sos_b = signal.butter(4, [band_b_lo / nyq, hi_b / nyq], btype="bandpass", output="sos")
        b = signal.sosfiltfilt(sos_b, a, axis=0)
        for f0 in notch_hz:
            if band_b_lo < f0 < hi_b:
                b = c4_notch(b, fs, f0)
        out["band_b"] = b
    else:
        out["band_a"] = a
        out["band_b"] = a
    out["band_b_hz"] = (band_b_lo, round(float(hi_b), 2))
    return out


def doppler_spectrogram(amp: np.ndarray, fs: float, nperseg: int, noverlap: int) -> tuple:
    """PORTED from id_branch.doppler_spectrogram. Magnitude only, mean across subcarriers."""
    a = np.asarray(amp, float)
    if a.ndim == 1:
        a = a[:, None]
    f, t, Z = signal.stft(a, fs=fs, nperseg=nperseg, noverlap=noverlap, axis=0,
                          padded=True, boundary="zeros")
    mag = np.abs(Z).mean(axis=1).T
    return f, t, mag.astype(np.float32)


def energy_percentile_contour(f: np.ndarray, mag: np.ndarray, pct: float,
                              f_min: float = 0.0) -> np.ndarray:
    """The frequency below which `pct` of each frame's energy lies. WifiU's torso and leg proxies.

    The 50th percentile is the torso proxy and the 95th the leg proxy. Frames with no energy return
    NaN rather than zero, because a zero would be read as a stationary torso.
    """
    f = np.asarray(f, float)
    m = np.asarray(mag, float) ** 2
    sel = f >= f_min
    f, m = f[sel], m[:, sel]
    tot = m.sum(axis=1)
    c = np.cumsum(m, axis=1)
    out = np.full(m.shape[0], np.nan)
    ok = tot > 0
    if ok.any():
        idx = (c[ok] >= (pct / 100.0) * tot[ok][:, None]).argmax(axis=1)
        out[ok] = f[idx]
    return out


def path_rate_to_speed(hz: np.ndarray, F: float, channel_hz: float = 2.437e9) -> np.ndarray:
    """f = 2 F v / lambda, inverted. FIGURES AND VALIDATION ONLY, never an identification feature."""
    lam = 299_792_458.0 / float(channel_hz)
    return np.asarray(hz, float) * lam / max(2.0 * float(F), 1e-9)
