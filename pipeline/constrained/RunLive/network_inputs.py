# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: What the networks are fed: the slowly changing part of the signal's shape, and the signal-strength series.

from __future__ import annotations

from functools import lru_cache

import numpy as np
from scipy import signal

TRACKING_LOWPASS_HZ: float = 2.0
FS: float = 150.0
# Function lowpass sos.
@lru_cache(maxsize=16)
def _lowpass_sos(fs: float, cutoff: float, order: int) -> np.ndarray:
    return signal.butter(order, cutoff / (0.5 * fs), btype="lowpass", output="sos")


# Zero-phase lowpass of one link's window, DC and near-DC passed through intact.
def lowpass(amplitude: np.ndarray, fs: float = FS, cutoff: float = TRACKING_LOWPASS_HZ,
            order: int = 4) -> np.ndarray:
    a = np.asarray(amplitude, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError(f"expected (n_samples, n_sub), got {a.shape}")
    pad = min(3 * (2 * order + 1) * 4, a.shape[0] - 1)
    return signal.sosfiltfilt(_lowpass_sos(float(fs), float(cutoff), int(order)), a, axis=0,
                              padlen=pad).astype(np.float32)


# The lowpass applied to every link of a fusion window (n_links, n_samples, n_sub).
def tracking_features_links(window: np.ndarray, fs: float = FS,
                            cutoff: float = TRACKING_LOWPASS_HZ) -> np.ndarray:
    w = np.asarray(window)
    if w.ndim != 3:
        raise ValueError(f"expected (n_links, n_samples, n_sub), got {w.shape}")
    return np.stack([lowpass(w[i], fs, cutoff) for i in range(w.shape[0])])
