# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The model's input: the slowly varying part of the normalised shape, and the RSSI series.

from __future__ import annotations

from functools import lru_cache

import numpy as np
from scipy import signal

TRACKING_LOWPASS_HZ: float = 2.0
FS: float = 150.0
NS: int = 300


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


# RSSI on each window's own sample lattice, (n, n_samples), and out-of-span window count.
def rssi_series(bin_path: str, t0: np.ndarray, n_samples: int = NS) -> tuple:
    from pipeline.io.capture_logger import read_capture_file
    _hdr, fr = read_capture_file(bin_path)
    t = np.asarray(fr["t_host"], dtype=np.float64)
    r = np.asarray(fr["rssi"], dtype=np.float32)
    o = np.argsort(t, kind="stable")
    t, r = t[o], r[o]
    t0 = np.asarray(t0, dtype=np.float64)
    ns = int(n_samples)
    lat = t0[:, None] + (np.arange(ns) / FS)[None, :]
    outside = int(np.sum((t0 < t[0]) | (t0 + ns / FS > t[-1])))
    return np.interp(lat.ravel(), t, r).reshape(len(t0), ns).astype(np.float32), outside
