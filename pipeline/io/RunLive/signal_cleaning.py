# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Cleans the signal: amplitude, the board's clock, resampling onto an even grid, removing outliers and...

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

from pipeline.io.RunLive.serial_parse_csi import N_SUBCARRIERS

HALF: int = N_SUBCARRIERS // 2

LLTF_NULLS: tuple[int, ...] = (0, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37)
HT_NULLS: tuple[int, ...] = tuple(HALF + k for k in (0, 29, 30, 31, 32, 33, 34, 35))
INVALID_FIRST_WORD: tuple[int, ...] = (0, 1)

DEAD_SUBCARRIERS: tuple[int, ...] = tuple(sorted(set(LLTF_NULLS) | set(HT_NULLS) | set(INVALID_FIRST_WORD)))

DEFAULT_KEEP: tuple[int, ...] = tuple(i for i in range(N_SUBCARRIERS) if i not in DEAD_SUBCARRIERS)

MIN_PACKET_MEAN: float = 1e-3

OUTLIER_WINDOW: int = 10

OUTLIER_SIGMAS: float = 4.0

_MAD_TO_SIGMA: float = 1.4826

DEVICE_CLOCK_MODULUS_US: int = 1 << 32

NOMINAL_SLOPE: float = 1e-6

MAX_CLOCK_PPM: float = 500.0

WRAP_MARGIN_US: int = 2_000_000

ARRIVAL_QUANTILE: float = 0.02

# Drop guard/null subcarriers and keep a usable subcarrier set.
def select_subcarriers(amplitude: np.ndarray, keep: Optional[Sequence[int]] = None) -> np.ndarray:
    a = np.asarray(amplitude)
    if a.ndim != 2:
        raise ValueError(f"expected (n_samples, n_sub), got {a.shape}")
    idx = np.asarray(DEFAULT_KEEP if keep is None else list(keep), dtype=int)
    if idx.size == 0:
        raise ValueError("keep must retain at least one subcarrier")
    if idx.min() < 0 or idx.max() >= a.shape[1]:
        raise ValueError(f"keep indices out of range for {a.shape[1]} subcarriers")
    return a[:, idx]


# A fit relating one receiver's device clock to host time.
@dataclass(frozen=True)
class Timebase:

    slope: float
    offset: float
    residual_std: float
    n: int
    n_wraps: int
    ppm_error: float
    ok: bool
    reason: str = ""


# Undo the wrapping of the device's 32-bit microsecond counter.
def unwrap_device_time(local_us: np.ndarray) -> tuple[np.ndarray, int]:
    t = np.asarray(local_us, dtype=np.int64)
    if t.size < 2:
        return t, 0
    d = np.diff(t)
    wraps = (d < 0) & (t[:-1] > DEVICE_CLOCK_MODULUS_US - WRAP_MARGIN_US)
    n_wraps = int(wraps.sum())
    if n_wraps:
        t = t + np.concatenate(([0], np.cumsum(wraps))) * DEVICE_CLOCK_MODULUS_US
    return t, n_wraps


# Index of the first packet of the device's current boot.
def device_epoch_start(local_us: np.ndarray) -> int:
    t = np.asarray(local_us, dtype=np.int64)
    if t.size < 2:
        return 0
    d = np.diff(t)
    restarts = np.flatnonzero((d < 0) & ~(t[:-1] > DEVICE_CLOCK_MODULUS_US - WRAP_MARGIN_US))
    return int(restarts[-1] + 1) if restarts.size else 0


# Device-anchored host times for a capture, dropping any stale epoch.
def anchor_times(local_us: np.ndarray, t_mono: np.ndarray) -> tuple[np.ndarray, int]:
    local = np.asarray(local_us, dtype=np.int64)
    ts = np.asarray(t_mono, dtype=np.float64)
    start = device_epoch_start(local)
    local, ts = local[start:], ts[start:]
    tb = fit_timebase(local, ts)
    return (apply_timebase(local, tb) if tb.ok else ts), start


# Anchor a receiver's device clock to host time.
def fit_timebase(local_us: np.ndarray, t_host: np.ndarray) -> Timebase:
    x_us, n_wraps = unwrap_device_time(local_us)
    y = np.asarray(t_host, dtype=np.float64)
    n = int(x_us.size)

    start = device_epoch_start(local_us)
    if start:
        return Timebase(NOMINAL_SLOPE, 0.0, float("nan"), n, n_wraps, 0.0, False,
                        f"device counter restarted at packet {start}: {start} stale packet(s) from a "
                        f"previous boot precede it; drop them before fitting")
    if n < 100:
        return Timebase(NOMINAL_SLOPE, 0.0, float("nan"), n, n_wraps, 0.0, False, f"only {n} packets")
    if np.unique(x_us).size < n // 2:
        return Timebase(NOMINAL_SLOPE, 0.0, float("nan"), n, n_wraps, 0.0, False, "device clock is not unique per packet")

    x = x_us.astype(np.float64)
    x0 = x[0]
    xs = (x - x0) * NOMINAL_SLOPE
    m, intercept = np.polyfit(xs, y, 1)
    slope = m * NOMINAL_SLOPE

    ppm = (slope / NOMINAL_SLOPE - 1.0) * 1e6
    if abs(ppm) > MAX_CLOCK_PPM:
        return Timebase(slope, intercept, float("nan"), n, n_wraps, float(ppm), False, f"clock rate {ppm:+.0f} ppm from nominal")

    resid = y - (m * xs + intercept)
    intercept += float(np.quantile(resid, ARRIVAL_QUANTILE))

    return Timebase(
        slope=float(slope),
        offset=float(intercept - slope * x0),
        residual_std=float(resid.std()),
        n=n,
        n_wraps=n_wraps,
        ppm_error=float(ppm),
        ok=True,
    )


# Convert device timestamps to host-referenced seconds.
def apply_timebase(local_us: np.ndarray, tb: Timebase) -> np.ndarray:
    x, _ = unwrap_device_time(local_us)
    return tb.slope * x.astype(np.float64) + tb.offset


# Divide each LTF half of each packet by that half's own mean.
def normalise_shape(amplitude: np.ndarray, keep: Optional[Sequence[int]] = None) -> np.ndarray:
    a = np.asarray(amplitude, dtype=np.float32)
    if a.ndim != 2:
        raise ValueError(f"expected (n_packets, n_live), got {a.shape}")
    if a.shape[1] == N_SUBCARRIERS:
        raise ValueError(
            f"normalise_shape received {N_SUBCARRIERS} subcarriers: dead bins are still "
            f"present. Call select_subcarriers first; the empty bins would drag every "
            f"packet's mean and the result would not be a shape."
        )
    idx = tuple(DEFAULT_KEEP if keep is None else keep)
    if a.shape[1] != len(idx):
        raise ValueError(
            f"normalise_shape got {a.shape[1]} columns but keep names {len(idx)} subcarriers: "
            f"pass the same keep that select_subcarriers used, or it cannot tell the legacy "
            f"half from the HT half."
        )
    is_lltf = np.fromiter((i < HALF for i in idx), dtype=bool, count=len(idx))

    out = np.empty_like(a)
    for cols in (is_lltf, ~is_lltf):
        if not cols.any():
            continue
        part = a[:, cols]
        m = part.mean(axis=1, keepdims=True)
        live = m > MIN_PACKET_MEAN
        safe = np.where(live, m, 1.0)
        scaled = part / safe
        scaled[~live.ravel()] = 0.0
        out[:, cols] = scaled
    return out


# The interval between the source packets that bracket each grid sample.
def packet_gap_on_grid(timestamps: np.ndarray, grid: np.ndarray) -> np.ndarray:
    t = np.asarray(timestamps, dtype=np.float64)
    g = np.asarray(grid, dtype=np.float64)
    if t.size < 2:
        return np.zeros(g.shape, dtype=np.float32)
    t = np.unique(t)
    hi = np.clip(np.searchsorted(t, g, side="right"), 1, t.size - 1)
    return (t[hi] - t[hi - 1]).astype(np.float32)


# Suppress impulsive amplitude spikes from packet-level glitches.
def remove_outliers(amplitude: np.ndarray) -> np.ndarray:
    a = np.asarray(amplitude, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError(f"expected (n_samples, n_sub), got {a.shape}")
    n = a.shape[0]
    w = OUTLIER_WINDOW
    if n < 2 * w + 1:
        return a.astype(np.float32)

    padded = np.pad(a, ((w, w), (0, 0)), mode="edge")
    windows = np.lib.stride_tricks.sliding_window_view(padded, 2 * w + 1, axis=0)
    med = np.median(windows, axis=-1)
    mad = np.median(np.abs(windows - med[..., None]), axis=-1)
    sigma = _MAD_TO_SIGMA * mad

    with np.errstate(invalid="ignore", divide="ignore"):
        is_outlier = np.abs(a - med) > OUTLIER_SIGMAS * sigma
    is_outlier &= sigma > 0

    out = np.where(is_outlier, med, a)
    return out.astype(np.float32)


# Estimate the per-session static baseline for each subcarrier.
def estimate_baseline(amplitude: np.ndarray) -> np.ndarray:
    a = np.asarray(amplitude, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError(f"expected (n_samples, n_sub), got {a.shape}")
    if a.shape[0] == 0:
        raise ValueError("cannot estimate a baseline from zero samples")
    overall = float(a[a.sum(axis=1) > 0].mean()) if np.any(a.sum(axis=1) > 0) else 1.0
    if abs(overall - 1.0) > 0.5:
        raise ValueError(
            f"estimate_baseline expects per-packet normalised input (mean ~1.0), got mean "
            f"{overall:.3g}. Call normalise_shape first; baselines live in shape space."
        )
    return np.median(a, axis=0).astype(np.float32)


# Subtract the per-session static baseline from an amplitude matrix.
def subtract_baseline(amplitude: np.ndarray, baseline: np.ndarray) -> np.ndarray:
    a = np.asarray(amplitude, dtype=np.float32)
    b = np.asarray(baseline, dtype=np.float32)
    if a.ndim != 2 or b.ndim != 1 or a.shape[1] != b.shape[0]:
        raise ValueError(f"shape mismatch: amplitude {a.shape}, baseline {b.shape}")
    if abs(float(b.mean()) - 1.0) > 0.5:
        raise ValueError(
            f"baseline mean is {float(b.mean()):.3g}, not ~1.0: this is a level baseline, "
            f"not a shape. Baselines must come from estimate_baseline on normalised data."
        )
    return a - b[None, :]


# The per-session baseline SHAPE from an empty-room capture.
def baseline_shape(amplitude: np.ndarray, keep: Optional[Sequence[int]] = None) -> np.ndarray:
    a = remove_outliers(normalise_shape(select_subcarriers(np.asarray(amplitude, dtype=np.float32), keep), keep))
    return estimate_baseline(a)
