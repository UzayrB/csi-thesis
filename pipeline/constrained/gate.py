# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Walking gate: 0.3 to 2 Hz band energy used to LABEL windows.

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

MOTION_BAND_HZ: tuple[float, float] = (0.3, 2.0)

MOTION_THETA: float = 0.431

PRESENCE_K: float = 1.04
PRESENCE_QUANTILE: float = 0.75

MAX_BASELINE_AGE_S: float = 3600.0


# The gate's verdict on one window.
@dataclass(frozen=True)
class GateLabel:

    label: str
    band_energy: float
    presence_theta: float
    motion_theta: float


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


# The per-session presence threshold from that session's own baseline.
def presence_threshold(baseline_band_energies: np.ndarray) -> float:
    e = np.asarray(baseline_band_energies, dtype=np.float64)
    if e.ndim != 1 or e.size < 5:
        raise ValueError("the presence threshold needs the band energies of at least five baseline windows")
    return float(PRESENCE_K * np.quantile(e, PRESENCE_QUANTILE))


# Whether a baseline was recorded recently enough to threshold this recording.
def baseline_is_fresh(recording_start: float, baseline_start: float, max_age_s: float = MAX_BASELINE_AGE_S) -> bool:
    age = recording_start - baseline_start
    if age < 0:
        raise ValueError(f"baseline starts {-age:.0f} s AFTER the recording it is meant to precede")
    return age <= max_age_s


# Label one window empty, standing or walking.
def label_window(window: np.ndarray, fs: float, presence_theta: float, motion_theta: float = MOTION_THETA) -> GateLabel:
    if not np.isfinite(presence_theta) or presence_theta <= 0:
        raise ValueError(f"presence_theta must be a positive number from this session's baseline, got {presence_theta!r}")
    e = band_energy(window, fs)
    if e >= motion_theta:
        label = "walking"
    elif e >= presence_theta:
        label = "standing"
    else:
        label = "empty"
    return GateLabel(label=label, band_energy=e, presence_theta=float(presence_theta), motion_theta=float(motion_theta))
