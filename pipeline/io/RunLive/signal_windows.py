# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Cuts recordings into 2 s windows (300 samples by 107 subcarriers by 3 receivers) and reads a session's...

from __future__ import annotations

import json
import os

import numpy as np

from pipeline.io.RunLive.signal_cleaning import anchor_times, baseline_shape
from pipeline.io.RunLive.serial_capture import read_capture_file

FS: float = 150.0
WINDOW_S: float = 2.0
NODES: tuple[str, ...] = ("RX1", "RX2", "RX3")
WALK_EDGE_S: float = 3.0


# Raw 128-subcarrier amplitude, anchored times, stale packets dropped, mono-to-epoch offset.
def load_node(path: str) -> tuple[np.ndarray, np.ndarray, int, float]:
    _header, fr = read_capture_file(path)
    ts, start = anchor_times(fr["local_timestamp"], fr["t_mono"])
    fr = fr[start:]
    amp = np.sqrt((fr["data"].astype(np.float32).reshape(len(fr), 128, 2) ** 2).sum(-1))
    epoch_offset = float(fr["t_host"][0] - fr["t_mono"][0]) if len(fr) else 0.0
    return amp, ts, start, epoch_offset


# The per-node baseline shape from an empty-room capture directory.
def session_baseline(baseline_dir: str) -> dict[str, np.ndarray]:
    out = {}
    for n in NODES:
        p = os.path.join(baseline_dir, f"{n}.bin")
        if not os.path.exists(p):
            raise FileNotFoundError(f"baseline {baseline_dir} has no {n}.bin")
        amp, _ts, _s, _e = load_node(p)
        out[n] = baseline_shape(amp)
    return out


# Function baseline dir for.
def baseline_dir_for(session_dir: str, stem: str) -> str:
    with open(os.path.join(session_dir, f"{stem}.gt.json"), encoding="utf-8") as f:
        b = json.load(f).get("baseline_capture")
    if not b:
        raise ValueError(f"{stem}: sidecar names no baseline capture")
    return b.rstrip("/")
