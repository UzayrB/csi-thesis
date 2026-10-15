"""ixa_speed. The extras brief's A1 (precise Wi-Fi speed) and A2 (speed profile), exactly as the PLAN's extras note
defines them, from `ixa_data`'s identity-blind ingredients. Development evaluation, all data seen.

A1, identification-spot windows: RX2's conditioned spectrogram on 10 <= f < 35 Hz minus the empty-room spectrum
E(f) (the median over the empty idspot recordings of the model's TRAINING Room B days only), clipped at 0; per
frame the power-weighted centroid; frames above the window's 25th energy percentile; v = median x 0.123 /
(2 x 0.98). Every other window keeps the current estimator (torso contour median on the best link / F).

A2: the per-frame trace (A1's per-frame speeds; elsewhere the per-frame torso contour x 0.123 / (2 F)) and its
9 columns.
"""

from __future__ import annotations

import os
import pickle

import numpy as np

A_DATA = os.path.join("runs", "identify", "final_extras", "a_data")
LAMBDA, F_SPOT = 0.123, 0.98
PROFILE = ("v_0.5", "v_1.0", "v_1.5", "v_2.0", "v_2.5", "v_3.0", "t_90pct_max", "v_max", "distance")
FRAME_T0, FRAME_HOP = 16.0 / 150.0, 8.0 / 150.0


def load():
    return (pickle.load(open(os.path.join(A_DATA, "windows.pkl"), "rb")),
            pickle.load(open(os.path.join(A_DATA, "empty_idspot.pkl"), "rb")))


def empty_spectrum(emp: dict, days) -> np.ndarray:
    """E(f): the median over every frame of the given Room B days' empty idspot windows."""
    return np.median(np.concatenate([emp[d]["frames"] for d in days], axis=1), axis=1)


def room_b_training_days(held_out) -> tuple:
    """The Room B days in a model's training set: every day but the held-out session (None: both)."""
    return tuple(d for d in ("B1", "B2") if d != held_out)


def idspot_trace(row: dict, E: np.ndarray) -> np.ndarray:
    """A1's per-frame speed trace (NaN where a frame is not kept)."""
    f = np.asarray(row["f"], float)
    P = np.maximum(row["P"] - E[:, None], 0.0)
    e = P.sum(axis=0)
    out = np.full(P.shape[1], np.nan)
    if not P.shape[1]:
        return out
    keep = (e > np.percentile(e, 25)) & (e > 0)
    c = (f[:, None] * P).sum(axis=0) / np.where(e > 0, e, 1.0)
    out[keep] = c[keep] * LAMBDA / (2.0 * F_SPOT)
    return out


def other_trace(row: dict) -> np.ndarray:
    if row["contour"] is None or row["F"] < 0.3:
        return np.full(1, np.nan)
    return np.asarray(row["contour"], float) * LAMBDA / (2.0 * row["F"])


def speed(row: dict, E: np.ndarray, current: float) -> float:
    """A1's speed for a window: the new estimator on identification-spot windows, else the current value."""
    if not row["idspot"]:
        return current
    v = idspot_trace(row, E)
    return float(np.nanmedian(v)) if np.isfinite(v).any() else float("nan")


def profile(row: dict, E: np.ndarray) -> np.ndarray:
    """A2's 9 columns from the window's trace; all NaN with fewer than 3 finite frames."""
    v = idspot_trace(row, E) if row["idspot"] else other_trace(row)
    t = FRAME_T0 + FRAME_HOP * np.arange(len(v))
    ok = np.isfinite(v)
    out = np.full(len(PROFILE), np.nan)
    if ok.sum() < 3:
        return out
    for j, c in enumerate((0.5, 1.0, 1.5, 2.0, 2.5, 3.0)):
        m = ok & (np.abs(t - c) <= 0.25)
        if m.any():
            out[j] = float(np.median(v[m]))
    vmax = float(np.max(v[ok]))
    first = np.flatnonzero(ok & (v >= 0.9 * vmax))
    out[6] = float(t[first[0]])
    out[7] = vmax
    vi = np.interp(t, t[ok], v[ok])
    out[8] = float(np.sum((vi[1:] + vi[:-1]) * np.diff(t)) / 2.0)
    return out
