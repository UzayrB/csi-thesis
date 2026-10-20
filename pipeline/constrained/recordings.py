# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Whole recordings, end to end, every window in time order.

from __future__ import annotations

import glob
import json
import os
from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

from pipeline.constrained.common import ART_DIR, SIX, status

WINDOWS_ROOT = os.environ.get("TDR_WINDOWS_ROOT", "runs/constrained/windows_s1.0_roomA")
DATA_ROOT = os.environ.get("TDR_DATA_ROOT", "data")
ROOM = os.environ.get("TDR_ROOM", "room_A")
NODES = ("RX1", "RX2", "RX3")
FS = 150.0
NS = 300

OFF_PATH_MODES = ("idle", "grid")
GRACE_MODES = ("walk_edge",)


# One recording's windows in time order, with everything a decoder or a metric needs.
@dataclass
class Recording:

    session: str
    stem: str
    participant: str
    t0: np.ndarray
    t0_epoch: np.ndarray
    mode: np.ndarray
    pass_id: np.ndarray
    path_name: np.ndarray
    xy: np.ndarray
    cell_id: np.ndarray
    gap_flag: np.ndarray

    # The number of items.
    def __len__(self) -> int:
        return int(len(self.t0))

    # Function key.
    @property
    def key(self) -> str:
        return f"{self.participant}|{self.session}"

    # Participant|session|pass_id per window, '' off-path.
    def pass_keys(self) -> np.ndarray:
        return np.array([f"{self.participant}|{self.session}|{int(p)}" if p >= 0 else ""
                         for p in self.pass_id])

    # Function on path.
    def on_path(self) -> np.ndarray:
        return self.mode == "walk"

    # Function off path.
    def off_path(self) -> np.ndarray:
        return np.isin(self.mode, OFF_PATH_MODES)

    # Function grace.
    def grace(self) -> np.ndarray:
        return np.isin(self.mode, GRACE_MODES)

    # (pass_id, path_name, first_index, last_index) for each pass, in time order.
    def pass_spans(self) -> list:
        out = []
        for pid in sorted({int(p) for p in self.pass_id if p >= 0}):
            idx = np.flatnonzero(self.pass_id == pid)
            if len(idx):
                out.append((pid, str(self.path_name[idx[0]]), int(idx[0]), int(idx[-1])))
        return out


# The eighteen labelled recordings as (session, stem).
def recordings() -> list:
    out = []
    for mp in sorted(glob.glob(os.path.join(WINDOWS_ROOT, ROOM, "session_*", "*.meta.json"))):
        stem = os.path.basename(mp)[:-len(".meta.json")]
        if "_DEMO_" in stem:
            continue
        who = stem.replace("participant_", "").split("_")[0]
        if who not in SIX:
            continue
        sid = mp.split("session_")[1][:2]
        out.append((sid, stem))
    return out


# One recording's per-window metadata.
def load_meta(session: str, stem: str) -> Recording:
    mp = os.path.join(WINDOWS_ROOT, ROOM, f"session_{session}", f"{stem}.meta.json")
    with open(mp, encoding="utf-8") as f:
        wins = json.load(f)["windows"]
    n = len(wins)
    xy = np.full((n, 2), np.nan)
    for i, w in enumerate(wins):
        if w.get("xy"):
            xy[i] = w["xy"]
    return Recording(
        session=session, stem=stem, participant=str(wins[0]["participant"]),
        t0=np.array([w["t_start_abs"] for w in wins], dtype=float),
        t0_epoch=np.array([w["t_start_epoch"] for w in wins], dtype=float),
        mode=np.array([w["mode"] for w in wins]),
        pass_id=np.array([-1 if w.get("pass_id") is None else int(w["pass_id"]) for w in wins]),
        path_name=np.array([w.get("path_name") or "" for w in wins]),
        xy=xy,
        cell_id=np.array([w.get("cell_id") or "" for w in wins]),
        gap_flag=np.array([bool(w.get("gap_flag")) for w in wins]),
    )


# Function feature cache path.
def feature_cache_path(session: str, stem: str) -> str:
    return os.path.join(ART_DIR, "features", f"session_{session}_{stem}.npy")


# Compute a whole recording's model input once and keep it.
def build_feature_cache(session: str, stem: str, force: bool = False) -> str:
    from pipeline.constrained.features import tracking_features_links
    p = feature_cache_path(session, stem)
    if os.path.exists(p) and not force:
        return p
    raw = np.load(os.path.join(WINDOWS_ROOT, ROOM, f"session_{session}", f"{stem}.npz"))["X"]
    out = np.stack([tracking_features_links(raw[i].astype(np.float32), FS) for i in range(len(raw))])
    os.makedirs(os.path.dirname(p), exist_ok=True)
    np.save(p, out.astype(np.float32))
    return p


# The model's input for a recording: the lowpassed tracking features, (n, 3, 300, 107).
def load_features(session: str, stem: str, indices: Optional[Sequence[int]] = None) -> np.ndarray:
    p = feature_cache_path(session, stem)
    if os.path.exists(p):
        arr = np.load(p, mmap_mode="r")
        if indices is None:
            return np.asarray(arr)
        idx = np.asarray(indices, dtype=int)
        return np.asarray(arr[idx])
    from pipeline.constrained.features import tracking_features_links
    raw = np.load(os.path.join(WINDOWS_ROOT, ROOM, f"session_{session}", f"{stem}.npz"))["X"]
    idx = np.arange(len(raw)) if indices is None else np.asarray(indices, dtype=int)
    return np.stack([tracking_features_links(raw[i].astype(np.float32), FS) for i in idx])


# Samples per window for THIS recording, from its own metadata.
def window_samples(session: str, stem: str) -> int:
    meta = os.path.join(WINDOWS_ROOT, ROOM, f"session_{session}", f"{stem}.meta.json")
    try:
        with open(meta, encoding="utf-8") as f:
            summary = json.load(f)["summary"]
        return int(round(float(summary["window_s"]) * float(summary.get("fs", FS))))
    except (OSError, KeyError, ValueError, TypeError):
        return int(NS)


# RSSI on each window's own sample lattice, (n, 3, n_samples), cached under ART_DIR.
def load_rssi(session: str, stem: str, t0_epoch: np.ndarray) -> np.ndarray:
    ns = window_samples(session, stem)
    cache = os.path.join(ART_DIR, "rssi_full", f"session_{session}_{stem}.npz")
    if os.path.exists(cache):
        d = np.load(cache, allow_pickle=False)
        if (len(d["rssi"]) == len(t0_epoch) and d["rssi"].shape[-1] == ns
                and np.allclose(d["t0"], t0_epoch)):
            return d["rssi"]
    from pipeline.constrained.features import rssi_series
    out = np.zeros((len(t0_epoch), 3, ns), dtype=np.float32)
    missing = []
    for li, node in enumerate(NODES):
        bp = os.path.join(DATA_ROOT, ROOM, f"session_{session}", f"{stem}_{node}.bin")
        if not os.path.exists(bp):
            missing.append(node)
            continue
        s, _outside = rssi_series(bp, t0_epoch, n_samples=ns)
        out[:, li] = s
    if missing:
        raise RuntimeError(f"{stem}: RSSI source missing for {missing} under "
                           f"{os.path.join(DATA_ROOT, ROOM, f'session_{session}')}; refusing to "
                           f"fill with zeros")
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    np.savez_compressed(cache, rssi=out, t0=t0_epoch)
    return out


# The 0.3 to 2 Hz band energy of every window, cached.
def gate_energy(session: str, stem: str) -> np.ndarray:
    cache = os.path.join(ART_DIR, "gate_energy", f"session_{session}_{stem}.npy")
    if os.path.exists(cache):
        return np.load(cache)
    from pipeline.constrained.gate import band_energy
    raw = np.load(os.path.join(WINDOWS_ROOT, ROOM, f"session_{session}", f"{stem}.npz"))["X"]
    e = np.array([band_energy(raw[i].astype(np.float32), FS) for i in range(len(raw))], dtype=float)
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    np.save(cache, e)
    return e


# The shape of one recording: waiting, passes and the gaps between them, in seconds.
def timeline(rec: Recording) -> dict:
    spans = rec.pass_spans()
    dur = float(rec.t0[-1] - rec.t0[0]) if len(rec) > 1 else 0.0
    if not spans:
        return {"stem": rec.stem, "session": rec.session, "duration_s": dur, "n_passes": 0}
    first, last = spans[0][2], spans[-1][3]
    gaps = [float(rec.t0[spans[i + 1][2]] - rec.t0[spans[i][3]]) for i in range(len(spans) - 1)]
    short = [g for g in gaps if g <= 60]
    long_ = [g for g in gaps if g > 60]
    return {
        "stem": rec.stem, "session": rec.session, "participant": rec.participant,
        "duration_s": round(dur, 1), "n_windows": len(rec), "n_passes": len(spans),
        "before_first_pass_s": round(float(rec.t0[first] - rec.t0[0]), 1),
        "after_last_pass_s": round(float(rec.t0[-1] - rec.t0[last]), 1),
        "inter_pass_gaps_s": [round(g, 1) for g in gaps],
        "transit_gaps_n": len(short),
        "transit_gap_median_s": round(float(np.median(short)), 1) if short else None,
        "transit_gap_min_s": round(float(np.min(short)), 1) if short else None,
        "transit_gap_max_s": round(float(np.max(short)), 1) if short else None,
        "dwell_block_s": round(float(np.max(long_)), 1) if long_ else None,
        "continuous": len(long_) <= 1,
        "mode_counts": {m: int((rec.mode == m).sum()) for m in
                        ("walk", "walk_edge", "grid", "idle")},
    }


# Function session recordings.
def session_recordings(session: str) -> list:
    return [(s, st) for s, st in recordings() if s == session]
