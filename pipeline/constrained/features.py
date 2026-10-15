"""The model's input: the slowly varying part of the normalised shape, and the RSSI series.

RESTATED HERE, not imported, because the target layout archives ``pipeline/branches/tracking_branch``
and ``pipeline/v2/rssi`` while the final model still needs exactly these two transforms. Both are
reproduced verbatim from the code that built every artefact on record, and any change to either
invalidates the frozen numbers.

WHY LOWPASS AND NEVER BANDPASS. A person's position changes the static multipath structure, and that
change appears as a slow drift in the RELATIVE amplitude across subcarriers, which is near-DC content
in the per-packet-normalised shape. The identification branch throws that away on purpose; this one
must keep it. So: no bandpass, no highpass, no detrending, no per-window mean removal along time.
A subcarrier's normalised value drifting slowly IS position.

WHY THE RSSI SERIES IS NOT AVERAGED. Averaging a window's RSSI to a scalar destroys the shadowing
swing, which is the entire signal the second channel carries. It is resampled onto the window's own
300-sample lattice instead and broadcast across the subcarrier axis.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from scipy import signal

TRACKING_LOWPASS_HZ: float = 2.0
FS: float = 150.0
NS: int = 300


@lru_cache(maxsize=16)
def _lowpass_sos(fs: float, cutoff: float, order: int) -> np.ndarray:
    return signal.butter(order, cutoff / (0.5 * fs), btype="lowpass", output="sos")


def lowpass(amplitude: np.ndarray, fs: float = FS, cutoff: float = TRACKING_LOWPASS_HZ,
            order: int = 4) -> np.ndarray:
    """Zero-phase lowpass of one link's window, DC and near-DC passed through intact.

    Never given a lower edge: a constant input comes out unchanged, which is the point.
    """
    a = np.asarray(amplitude, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError(f"expected (n_samples, n_sub), got {a.shape}")
    pad = min(3 * (2 * order + 1) * 4, a.shape[0] - 1)
    return signal.sosfiltfilt(_lowpass_sos(float(fs), float(cutoff), int(order)), a, axis=0,
                              padlen=pad).astype(np.float32)


def tracking_features_links(window: np.ndarray, fs: float = FS,
                            cutoff: float = TRACKING_LOWPASS_HZ) -> np.ndarray:
    """The lowpass applied to every link of a fusion window ``(n_links, n_samples, n_sub)``."""
    w = np.asarray(window)
    if w.ndim != 3:
        raise ValueError(f"expected (n_links, n_samples, n_sub), got {w.shape}")
    return np.stack([lowpass(w[i], fs, cutoff) for i in range(w.shape[0])])


def rssi_series(bin_path: str, t0: np.ndarray, n_samples: int = NS) -> tuple:
    """RSSI on each window's own sample lattice, ``(n, n_samples)``, and out-of-span window count.

    Read-only recovery straight from the capture file, aligned by ``t_host`` against each window's
    own ``t_start_epoch``. Nothing here writes under ``data/``.

    n_samples DEFAULTS to NS, the 300-sample lattice of the shipped two-second window, so every
    existing caller is bit-identical. It became an argument on 2026-09-19, when the window probe
    found that a one-second CSI window was being concatenated with a 300-sample RSSI series: the
    lattice is a property of the WINDOW LENGTH, and a constant named NS hid that. The feasibility
    phase had enumerated the brief's six window-quantised parameters and missed this one because
    nothing asked about it.
    """
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
