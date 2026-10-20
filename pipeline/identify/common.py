# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Shared pieces for the identification branch.

from __future__ import annotations

import os

import numpy as np

SIX = ("PA5", "PA1", "PA2", "PA3", "PA4", "PA6")
RETIRED = ("retired_1", "retired_2")
CHANCE_PCT = 100.0 / len(SIX)
GAIT_LO, GAIT_HI = 0.8, 3.5
CADENCE_LO, CADENCE_HI = 1.2, 2.8
STRIDE_LO, STRIDE_HI = 0.4, 1.0
FS = 150.0
SEED = 0
RUN_DIR = os.path.join("runs", "identify")
PINDEX = {p: f"P{i + 1}" for i, p in enumerate(SIX)}


# Function anon.
def anon(name: str) -> str:
    return PINDEX.get(str(name), "P?")


# Zero-phase Butterworth band-pass.
def bandpass(x: np.ndarray, lo: float = GAIT_LO, hi: float = GAIT_HI, fs: float = FS,
             axis: int = -1) -> np.ndarray:
    from scipy.signal import butter, filtfilt
    b, a = butter(4, [lo / (fs / 2), hi / (fs / 2)], btype="band")
    return filtfilt(b, a, np.asarray(x, float), axis=axis)


# A continuous 150 Hz per-link amplitude stream for one pass, (3, n_samples, 107).
def pass_stream(session: str, stem: str, windows: np.ndarray) -> np.ndarray:
    from pipeline.constrained.recordings import WINDOWS_ROOT
    p = os.path.join(WINDOWS_ROOT, "room_A", f"session_{session}", f"{stem}.npz")
    raw = np.load(p, allow_pickle=False)["X"]
    half = int(FS)
    return np.concatenate([np.asarray(raw[i], np.float32)[:, :half, :] for i in windows], axis=1)


# Per link, one gait-band envelope: band-pass every subcarrier then average across them.
def envelopes(stream: np.ndarray) -> np.ndarray:
    return bandpass(np.asarray(stream, float), axis=1).mean(axis=2)


# Step frequency from the Welch peak inside the plausible band, and the peak's prominence.
def cadence_of(env: np.ndarray, fs: float = FS) -> tuple:
    from scipy.signal import welch
    f, pxx = welch(np.asarray(env, float), fs=fs, nperseg=min(512, np.asarray(env).shape[-1]))
    band = (f >= CADENCE_LO) & (f <= CADENCE_HI)
    if not band.any():
        return None, None
    p = np.atleast_2d(pxx)[:, band]
    fb = f[band]
    peak = fb[p.argmax(axis=1)]
    frac = p.max(axis=1) / np.maximum(np.atleast_2d(pxx).sum(axis=1), 1e-12)
    return float(np.median(peak)), float(np.median(frac))


# Identification runs live in runs/identify/, NOT runs/constrained/.
def id_stage_dir(name: str) -> str:
    p = os.path.join(RUN_DIR, name)
    os.makedirs(p, exist_ok=True)
    return p


# Function id save.
def id_save(name: str, res: dict) -> str:
    import json
    p = os.path.join(id_stage_dir(name), "results.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    return p


# Function id load.
def id_load(name: str) -> dict:
    import json
    p = os.path.join(RUN_DIR, name, "results.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


# Windows of one pass for GAIT: walk AND walk_edge.
def gait_windows(rec, pass_id: int) -> np.ndarray:
    m = np.asarray(rec.mode).astype(str)
    return np.flatnonzero((np.asarray(rec.pass_id) == pass_id) & ((m == "walk") | (m == "walk_edge")))
