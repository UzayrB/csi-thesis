# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The walking gate: the 0.3 to 2 Hz energy in a window, which tells someone walking from an empty, still room.

from __future__ import annotations


import numpy as np

MOTION_BAND_HZ: tuple[float, float] = (0.3, 2.0)

# 0.3 to 2 Hz band power of one window, mean over subcarriers and links.
def band_energy(window: np.ndarray, fs: float, band: tuple[float, float] = MOTION_BAND_HZ) -> float:
    x = np.asarray(window, dtype=np.float64)
    if x.ndim == 2:
        x = x[None]
    if x.ndim != 3:
        raise ValueError(f"expected (links, samples, sub) or (samples, sub), got {x.shape}")
    x = x - x.mean(axis=1, keepdims=True)
    f = np.fft.rfftfreq(x.shape[1], 1 / fs)
    P = (np.abs(np.fft.rfft(x, axis=1)) ** 2) / x.shape[1]
    sel = (f >= band[0]) & (f <= band[1])
    return float(P[:, sel, :].sum(axis=1).mean())
