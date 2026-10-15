"""Shared pieces for the identification branch. Brief: reports/overnight_identification_prompt_2026-09-18.md.

SIX participants, never eight. Azrah and Zaid are retired and are never read, so every archived
identification figure, all of which were computed on eight classes, has to be recomputed here and is
never quoted except in a clearly labelled history paragraph. Chance for six-way is 16.7 percent.

The gait band is 0.8 to 3.5 Hz and belongs to THIS BRANCH ONLY. The tracking features use a 2 Hz
lowpass, which removes exactly the step rhythm this branch needs, and nothing here may be applied to
the tracking chain.
"""

from __future__ import annotations

import os

import numpy as np

SIX = ("PA5", "PA1", "PA2", "PA3", "PA4", "PA6")
RETIRED = ("Azrah", "Zaid")
CHANCE_PCT = 100.0 / len(SIX)
GAIT_LO, GAIT_HI = 0.8, 3.5          #: the identification band
CADENCE_LO, CADENCE_HI = 1.2, 2.8    #: where a plausible step frequency must lie
STRIDE_LO, STRIDE_HI = 0.4, 1.0      #: implied stride, speed over cadence, in metres
FS = 150.0
SEED = 0
RUN_DIR = os.path.join("runs", "identify")
#: participant names are ethics code names and never leave runs/. P1 to P6 by the fixed order above.
PINDEX = {p: f"P{i + 1}" for i, p in enumerate(SIX)}


def anon(name: str) -> str:
    return PINDEX.get(str(name), "P?")


def bandpass(x: np.ndarray, lo: float = GAIT_LO, hi: float = GAIT_HI, fs: float = FS,
             axis: int = -1) -> np.ndarray:
    """Zero-phase Butterworth band-pass. Zero-phase on purpose: a causal filter shifts the step
    peaks in time and cadence variability is read from the spacing of those peaks."""
    from scipy.signal import butter, filtfilt
    b, a = butter(4, [lo / (fs / 2), hi / (fs / 2)], btype="band")
    return filtfilt(b, a, np.asarray(x, float), axis=axis)


def pass_stream(session: str, stem: str, windows: np.ndarray) -> np.ndarray:
    """A continuous 150 Hz per-link amplitude stream for one pass, (3, n_samples, 107).

    Windows are 2 s long at a 1 s stride, so they overlap by half. Taking the FIRST 150 samples of
    each window gives continuous non-overlapping coverage at the true sample rate, which is what a
    cadence estimate needs; concatenating whole windows would repeat every sample twice and put a
    spurious 1 Hz periodicity into the spectrum.
    """
    from pipeline.constrained.recordings import WINDOWS_ROOT
    p = os.path.join(WINDOWS_ROOT, "room_A", f"session_{session}", f"{stem}.npz")
    raw = np.load(p, allow_pickle=False)["X"]
    half = int(FS)                                   # 1 s at 150 Hz
    return np.concatenate([np.asarray(raw[i], np.float32)[:, :half, :] for i in windows], axis=1)


def envelopes(stream: np.ndarray) -> np.ndarray:
    """Per link, one gait-band envelope: band-pass every subcarrier then average across them."""
    return bandpass(np.asarray(stream, float), axis=1).mean(axis=2)


def cadence_of(env: np.ndarray, fs: float = FS) -> tuple:
    """Step frequency from the Welch peak inside the plausible band, and the peak's prominence."""
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


def id_stage_dir(name: str) -> str:
    """Identification runs live in runs/identify/, NOT runs/constrained/.

    rebuild_common.stage_dir hardcodes the tracking run root, so using it here put phase C's results
    in runs/constrained/ where the chain's completion check could never find them and every phase
    would have looked failed.
    """
    p = os.path.join(RUN_DIR, name)
    os.makedirs(p, exist_ok=True)
    return p


def id_save(name: str, res: dict) -> str:
    import json
    p = os.path.join(id_stage_dir(name), "results.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    return p


def id_load(name: str) -> dict:
    import json
    p = os.path.join(RUN_DIR, name, "results.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def gait_windows(rec, pass_id: int) -> np.ndarray:
    """Windows of one pass for GAIT: walk AND walk_edge.

    The tracking chain selects mode == 'walk' only, because it needs an interpolated POSITION and
    the ramp windows straddle the pass anchors so they have none. Gait does not need a position. It
    needs samples, and the ramps are the person walking. Including them takes a pass from about four
    seconds to about ten, which is the difference between five and twelve step cycles and is why the
    first cadence gate failed on 28.9 percent of passes.
    """
    m = np.asarray(rec.mode).astype(str)
    return np.flatnonzero((np.asarray(rec.pass_id) == pass_id) & ((m == "walk") | (m == "walk_edge")))
