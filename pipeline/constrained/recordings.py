"""Whole recordings, end to end, every window in time order.

WHY THIS EXISTS. Every artefact on record describes only the windows where a person was on a taped
line with a position label: ``load_grid`` selects ``mode == "walk" and xy is not None``, and that is
9.1 percent of a recording. The other 90.9 percent is waiting before the first pass, walking between
paths, and the grid-dwell block in the middle. A decoder that has to find the passes for itself, run
live on a stream, and hold a null state when the person is not on a line cannot be measured on the
9.1 percent, so this module reads the whole thing.

WHAT A RECORDING CONTAINS, measured over all eighteen:

    walk        9.1 %   on a taped line, position labelled
    walk_edge  11.9 %   the run-in and run-out, within 3 s of a pass, walking without a position
    grid       12.8 %   standing in a numbered cell during the dwell block
    idle       66.2 %   waiting before the first pass and walking between paths

Every recording is continuous: capture runs from before the first pass to the end of the last, so
the waiting and the transit are real and on tape, and nothing here is synthetic.

NOTHING UNDER data/ IS WRITTEN. The existing feature cache lives under ``data/features`` and holds
only the walk windows; this module recomputes features in memory and caches derived products under
``runs/artefacts`` instead.
"""

from __future__ import annotations

import glob
import json
import os
from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

from pipeline.constrained.common import ART_DIR, SIX, status

#: Where the cut windows live. Overridable ONLY through the environment, so that the 0.5 s stride
#: arm (amendment D1) can run against runs/constrained/windows_half in a separate process without a
#: monkeypatch and without any risk to the 1 s tree. The default is unchanged and no code path
#: writes here: data/ is read-only for this whole batch.
WINDOWS_ROOT = os.environ.get("TDR_WINDOWS_ROOT", "runs/constrained/windows_s1.0_roomA")
#: the raw data root. `data` unless DC2's view directory is in use (TDR_DATA_ROOT, 2026-09-23d): the
#: DC2 stand-in found this hard-coded while every other reader followed the view, and the RSSI of a
#: whole session was filled with zeros without a word
DATA_ROOT = os.environ.get("TDR_DATA_ROOT", "data")
#: WHICH ROOM. Defaults to room_A, so every existing caller is bit-identical and the suite proves
#: it. DC2 sets TDR_ROOM to the Room B folder name. The room name is a LAYOUT parameter, never a
#: data edit: data/room_A is read only and is never written, moved or renamed.
ROOM = os.environ.get("TDR_ROOM", "room_A")
NODES = ("RX1", "RX2", "RX3")
FS = 150.0
NS = 300

#: Windows whose mode is one of these are NOT on a taped path. The decoder should be in its null
#: state for all of them. ``walk_edge`` is deliberately excluded from both sets: it is the run-in and
#: run-out within 3 s of a pass, the person IS walking, and entering the path a little early or
#: leaving a little late there is defensible rather than wrong. Stage 4 treats it as a grace zone.
OFF_PATH_MODES = ("idle", "grid")
GRACE_MODES = ("walk_edge",)


@dataclass
class Recording:
    """One recording's windows in time order, with everything a decoder or a metric needs."""

    session: str
    stem: str
    participant: str
    t0: np.ndarray            # (n,) window start on the device-anchored base
    t0_epoch: np.ndarray      # (n,) wall clock, used to align RSSI
    mode: np.ndarray          # (n,) walk | walk_edge | grid | idle
    pass_id: np.ndarray       # (n,) -1 where the window is not in a pass
    path_name: np.ndarray     # (n,) '' where the window is not in a pass
    xy: np.ndarray            # (n, 2) nan where there is no position label
    cell_id: np.ndarray       # (n,) '' unless standing in a numbered cell
    gap_flag: np.ndarray      # (n,) worst source-packet gap exceeded the verified ceiling

    def __len__(self) -> int:
        return int(len(self.t0))

    @property
    def key(self) -> str:
        return f"{self.participant}|{self.session}"

    def pass_keys(self) -> np.ndarray:
        """``participant|session|pass_id`` per window, '' off-path. The bootstrap grouping key."""
        return np.array([f"{self.participant}|{self.session}|{int(p)}" if p >= 0 else ""
                         for p in self.pass_id])

    def on_path(self) -> np.ndarray:
        return self.mode == "walk"

    def off_path(self) -> np.ndarray:
        return np.isin(self.mode, OFF_PATH_MODES)

    def grace(self) -> np.ndarray:
        return np.isin(self.mode, GRACE_MODES)

    def pass_spans(self) -> list:
        """(pass_id, path_name, first_index, last_index) for each pass, in time order.

        Boundaries come from the window modes, which come from the recorded anchor times, so this is
        the ground truth a segmentation metric is scored against.
        """
        out = []
        for pid in sorted({int(p) for p in self.pass_id if p >= 0}):
            idx = np.flatnonzero(self.pass_id == pid)
            if len(idx):
                out.append((pid, str(self.path_name[idx[0]]), int(idx[0]), int(idx[-1])))
        return out


def recordings() -> list:
    """The eighteen labelled recordings as (session, stem). Demonstration captures never appear."""
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


def load_meta(session: str, stem: str) -> Recording:
    """One recording's per-window metadata. Cheap: no window tensor is touched."""
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


def feature_cache_path(session: str, stem: str) -> str:
    return os.path.join(ART_DIR, "features", f"session_{session}_{stem}.npy")


def build_feature_cache(session: str, stem: str, force: bool = False) -> str:
    """Compute a whole recording's model input once and keep it.

    Worth the disk. Without it the same 2 Hz lowpass is recomputed for every pairing and every seed
    that touches the recording, which is thirty-six times over the batch for about half an hour of
    pure repetition. Stored at float32, NOT float16: the frozen path is float16 raw cast to float32
    and then filtered, so storing the result at half precision would make the rebuilt model disagree
    with the frozen artefact for a reason that has nothing to do with the model.
    """
    from pipeline.constrained.features import tracking_features_links
    p = feature_cache_path(session, stem)
    if os.path.exists(p) and not force:
        return p
    raw = np.load(os.path.join(WINDOWS_ROOT, ROOM, f"session_{session}", f"{stem}.npz"))["X"]
    out = np.stack([tracking_features_links(raw[i].astype(np.float32), FS) for i in range(len(raw))])
    os.makedirs(os.path.dirname(p), exist_ok=True)
    np.save(p, out.astype(np.float32))
    return p


def load_features(session: str, stem: str, indices: Optional[Sequence[int]] = None) -> np.ndarray:
    """The model's input for a recording: the lowpassed tracking features, ``(n, 3, 300, 107)``.

    This is the SAME transform the frozen artefacts were built through
    (``tracking_features_links``, a 2 Hz lowpass that passes DC). It is recomputed here rather than
    read from ``data/features`` because that cache holds only the walk windows, and nothing in this
    batch writes under ``data/``.

    Reads the whole-recording cache when it exists, memory-mapped so that asking for two hundred
    windows does not page in a 385 MB file.
    """
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


def window_samples(session: str, stem: str) -> int:
    """Samples per window for THIS recording, from its own metadata. Falls back to NS.

    The RSSI lattice must match the CSI window it is concatenated with, and the window length is a
    property of the tree being read, not a constant. Added 2026-09-19 after a one-second CSI window
    met a 300-sample RSSI series in stack_link.
    """
    meta = os.path.join(WINDOWS_ROOT, ROOM, f"session_{session}", f"{stem}.meta.json")
    try:
        with open(meta, encoding="utf-8") as f:
            summary = json.load(f)["summary"]
        return int(round(float(summary["window_s"]) * float(summary.get("fs", FS))))
    except (OSError, KeyError, ValueError, TypeError):
        return int(NS)


def load_rssi(session: str, stem: str, t0_epoch: np.ndarray) -> np.ndarray:
    """RSSI on each window's own sample lattice, ``(n, 3, n_samples)``, cached under ART_DIR.

    Resampled rather than averaged to a scalar: averaging destroys the shadowing swing, which is the
    entire signal the second channel carries. The lattice length follows the recording's own window
    length, so a tree cut at a different window gets a matching series.
    """
    ns = window_samples(session, stem)
    cache = os.path.join(ART_DIR, "rssi_full", f"session_{session}_{stem}.npz")
    if os.path.exists(cache):
        d = np.load(cache, allow_pickle=False)
        # THE SHAPE IS PART OF THE CACHE KEY. The old check compared only the window count and the
        # timestamps, so a series cached at one lattice would have been served for another.
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
        # A REFUSAL, NOT A STATUS LINE (2026-09-23d). Zero RSSI on a link is not "no signal", it is
        # an input the heads never saw, and it drove the DC2 stand-in's emissions to saturation
        # (spread 27.6 nats against 2.11) while printing one line that scrolled past.
        raise RuntimeError(f"{stem}: RSSI source missing for {missing} under "
                           f"{os.path.join(DATA_ROOT, ROOM, f'session_{session}')}; refusing to "
                           f"fill with zeros")
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    np.savez_compressed(cache, rssi=out, t0=t0_epoch)
    return out


def gate_energy(session: str, stem: str) -> np.ndarray:
    """The 0.3 to 2 Hz band energy of every window, cached. The motion gate's own statistic.

    Measured over all eighteen recordings: median 1.247 on a taped path against 0.489 between paths,
    with the threshold at 0.431. It separates moving from still cleanly (97.3 percent against 8.0 on
    the dwells) but calls 53.2 percent of transit windows walking, because during transit the person
    genuinely is walking. So it is a feature of the null-state emission, never the decision.
    """
    cache = os.path.join(ART_DIR, "gate_energy", f"session_{session}_{stem}.npy")
    if os.path.exists(cache):
        return np.load(cache)
    from pipeline.constrained.gate import band_energy
    raw = np.load(os.path.join(WINDOWS_ROOT, ROOM, f"session_{session}", f"{stem}.npz"))["X"]
    e = np.array([band_energy(raw[i].astype(np.float32), FS) for i in range(len(raw))], dtype=float)
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    np.save(cache, e)
    return e


def timeline(rec: Recording) -> dict:
    """The shape of one recording: waiting, passes and the gaps between them, in seconds."""
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


def session_recordings(session: str) -> list:
    return [(s, st) for s, st in recordings() if s == session]
