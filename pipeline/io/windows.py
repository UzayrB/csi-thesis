"""Cut every recording into 2 s fusion windows with the metadata a result needs.

A window is 300 samples at 150 Hz by 107 subcarriers by 3 receivers, cut on
the shared absolute lattice so the same instant is the same window on every
link, at a 1.0 s stride for training. The 0.5 s stride is for real time only;
it inflates window counts about four times with near copies and is never
used to report a dataset size. Windows are cut per recording, so an overlap
never crosses a file boundary, and every recording is cut once: the splits
are by session and file, so they select recordings, not windows.

Every window carries the metadata that later stages cannot recover without
re-windowing:

* ``file_id`` and ``rx_files``: provenance, back to a printable file list.
* ``t_start_abs``: window start on the device-anchored common time base
  (host monotonic seconds), plus ``t_start_epoch`` for the wall clock.
* ``dwell_id`` / ``pass_id``: which grid dwell or walking pass produced it.
  Load-bearing: a within-session cell split must never put two halves of
  one dwell on opposite sides, and grouping by cell would not prevent it.
* ``cell_id``, ``xy``, ``facing``: the dwell's cell centre and cup colour, or
  the pass position interpolated at the window midpoint. Interpolation
  never extrapolates before the first anchor or after the last; windows
  outside get a null position. The operator reaction-time bias is NOT
  subtracted here: ``anchor_times`` are raw press times and
  :func:`_interp_xy` interpolates against them directly. The correction
  exists only in the live capture path,
  ``pipeline.io.ground_truth.interpolate_position``. See
  ``reports/v2/label_uncertainty.md``; the residual is about 7 cm at
  1.4 m/s and is a disclosed limitation, not a defect to repair.
* ``walk_speed``: the pass's mean speed over its anchors, the floor every
  identification claim must clear.
* ``clothing``, ``footwear``, ``height_cm``, ``weight_kg``: from the sidecar.
* ``max_packet_gap`` and ``gap_flag``: the longest gap between source
  packets under the window on any link, and whether it exceeds the verified
  interpolation ceiling. Losses are non-random in time and are carried.
* ``gate``: filled in at Stage 3; null until then.

Storage: one ``.npz`` per recording under ``<out>/room_<R>/session_<S>/``
holding ``X`` and the per-window arrays, and a ``.meta.json`` beside it with
the full metadata list. The dtype of ``X`` is :data:`STORE_DTYPE`, chosen
after measuring float16 against float32 on a real session; see the
constant.
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np

from pipeline.io.clean import (
    DEFAULT_KEEP,
    MAX_VERIFIED_GAP_S,
    CleanedNode,
    anchor_times,
    baseline_shape,
    clean_arrays,
)
from pipeline.io.capture_logger import read_capture_file

FS: float = 150.0
WINDOW_S: float = 2.0
STRIDE_S: float = 1.0
REALTIME_STRIDE_S: float = 0.5
NODES: tuple[str, ...] = ("RX1", "RX2", "RX3")
#: Windows nearer than this to a pass, but outside its anchors, are ``walk_edge``:
#: the run-in and run-out, walking but without a position.
WALK_EDGE_S: float = 3.0

#: Storage dtype for the window tensor. Measured 10 September 2026 on one
#: real recording before choosing (tools/check_float16.py, result in
#: reports/audit/float16_check.txt): PA5 session 02, 806 windows of
#: baseline-subtracted shape deviations ranging -1.36 to +2.43 with a
#: median magnitude of 0.10. Float16 against float32: relative quantisation
#: error median 1.7e-4, 99th percentile 4.3e-4, worst 2.7e-2 on the
#: smallest values; no exact zeros introduced; the 0.3 to 2 Hz gate-band
#: energy shifted by a median 3.8e-6 and at most 1.3e-4, against a 1
#: percent limit. Float16 it is, at half the disk: 155 MB per recording
#: instead of 310. Set by that measurement, not by the saving.
STORE_DTYPE = np.float16

BASELINE_DIR_RE = re.compile(r"^\d{8}-\d{6}$")


@dataclass
class WindowMeta:
    participant: str
    session_id: str
    room: str
    file_id: str
    rx_files: dict
    index: int
    t_start_abs: float
    t_start_epoch: float
    mode: str
    dwell_id: Optional[int] = None
    pass_id: Optional[int] = None
    path_name: Optional[str] = None
    cell_id: Optional[str] = None
    xy: Optional[list] = None
    facing: Optional[str] = None
    walk_speed: Optional[float] = None
    clothing: str = ""
    footwear: str = ""
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    max_packet_gap: float = 0.0
    max_packet_gap_per_rx: dict = field(default_factory=dict)
    gap_flag: bool = False
    flagged: bool = False
    gate: Optional[str] = None


def load_node(path: str) -> tuple[np.ndarray, np.ndarray, int, float]:
    """Raw 128-subcarrier amplitude, anchored times, stale packets dropped, mono-to-epoch offset."""
    _header, fr = read_capture_file(path)
    ts, start = anchor_times(fr["local_timestamp"], fr["t_mono"])
    fr = fr[start:]
    amp = np.sqrt((fr["data"].astype(np.float32).reshape(len(fr), 128, 2) ** 2).sum(-1))
    epoch_offset = float(fr["t_host"][0] - fr["t_mono"][0]) if len(fr) else 0.0
    return amp, ts, start, epoch_offset


def session_baseline(baseline_dir: str) -> dict[str, np.ndarray]:
    """The per-node baseline shape from an empty-room capture directory."""
    out = {}
    for n in NODES:
        p = os.path.join(baseline_dir, f"{n}.bin")
        if not os.path.exists(p):
            raise FileNotFoundError(f"baseline {baseline_dir} has no {n}.bin")
        amp, _ts, _s, _e = load_node(p)
        out[n] = baseline_shape(amp)
    return out


def window_starts(nodes: dict[str, CleanedNode], window_s: float, stride_s: float, fs: float) -> np.ndarray:
    """Absolute start times common to every node's grid, on the stride lattice."""
    lo = max(c.grid[0] for c in nodes.values())
    hi = min(c.grid[-1] for c in nodes.values()) - window_s
    if hi < lo:
        return np.zeros(0)
    first = math.ceil(lo / stride_s - 1e-9) * stride_s
    n = int(math.floor((hi - first) / stride_s + 1e-9)) + 1
    return first + np.arange(n) * stride_s


def _interp_xy(pass_doc: dict, t: float) -> Optional[list]:
    """Linear position at ``t`` from a pass's anchors, with NO reaction-time correction.

    ``anchor_times`` are raw press times, as the sidecar documents, and they are used here
    unchanged. The measured +51 ms operator bias is therefore still present in every window
    position this function produces, which is about 7 cm at 1.4 m/s along the direction of travel.

    That is deliberate and disclosed rather than accidental. The correction is not applied because
    the pressing convention itself was inconsistent (waist intended, heel frequently caught), so the
    offset is a random variable rather than a constant and a fixed shift would remove a constant
    that was never there. Both terms act along the direction of travel and largely cancel across the
    balanced forward and reverse passes, leaving spread rather than bias. See
    ``reports/v2/label_uncertainty.md`` for the full characterisation.

    Do not "fix" this without reading that report: it would invalidate every cached window and every
    number on record for a correction that is not clearly an improvement.
    """
    times = pass_doc["anchor_times"]
    coords = pass_doc["anchor_coords"]
    if t < times[0] or t > times[-1]:
        return None
    x = float(np.interp(t, times, [c[0] for c in coords]))
    y = float(np.interp(t, times, [c[1] for c in coords]))
    return [round(x, 4), round(y, 4)]


def pass_speed(pass_doc: dict) -> Optional[float]:
    times = pass_doc.get("anchor_times") or []
    coords = pass_doc.get("anchor_coords") or []
    if len(times) < 2:
        return None
    dist = sum(math.dist(coords[i], coords[i + 1]) for i in range(len(coords) - 1))
    dur = times[-1] - times[0]
    return round(dist / dur, 4) if dur > 0 else None


def label_window(meta: WindowMeta, t0: float, t1: float, sidecar: dict) -> None:
    """Attach dwell / pass labels to one window from the sidecar."""
    t_mid = 0.5 * (t0 + t1)
    for c in sidecar.get("cells", []):
        if t0 >= c["t_start"] and t1 <= c["t_end"]:
            meta.mode = "grid"
            meta.dwell_id = int(c["cell_index"])
            meta.cell_id = str(c["cell_id"])
            meta.xy = [float(v) for v in c["cell_centre_xy"]]
            meta.facing = str(c.get("facing_cup") or c.get("facing") or "")
            meta.flagged = bool(c.get("flagged", False))
            return
    nearest = None
    for p in sidecar.get("passes", []):
        if p["t_start"] <= t_mid <= p["t_end"]:
            meta.mode = "walk"
            meta.pass_id = int(p["pass_id"])
            meta.path_name = str(p.get("path_name", ""))
            meta.xy = _interp_xy(p, t_mid)
            meta.walk_speed = pass_speed(p)
            meta.flagged = bool(p.get("flagged", False))
            return
        gap = min(abs(t_mid - p["t_start"]), abs(t_mid - p["t_end"]))
        if gap <= WALK_EDGE_S and (nearest is None or gap < nearest[0]):
            nearest = (gap, p)
    if nearest is not None:
        p = nearest[1]
        meta.mode = "walk_edge"
        meta.pass_id = int(p["pass_id"])
        meta.path_name = str(p.get("path_name", ""))
        meta.walk_speed = pass_speed(p)
        meta.xy = None
        return
    meta.mode = "idle"


def cut_recording(
    session_dir: str,
    stem: str,
    baselines: dict[str, np.ndarray],
    fs: float = FS,
    window_s: float = WINDOW_S,
    stride_s: float = STRIDE_S,
    dtype=STORE_DTYPE,
    keep: Optional[Sequence[int]] = None,
) -> tuple[np.ndarray, list[WindowMeta], dict]:
    """Cut one recording (three receiver files plus sidecar) into fusion windows.

    Returns:
        ``X`` of shape ``(n_windows, 3, n_samples, n_sub)``, the metadata
        list, and a small summary dict.
    """
    with open(os.path.join(session_dir, f"{stem}.gt.json"), encoding="utf-8") as f:
        sidecar = json.load(f)
    if sidecar.get("mode") == "demo":
        raise ValueError(f"{stem}: demonstration recordings are never windowed for training or evaluation")
    nodes: dict[str, CleanedNode] = {}
    rx_files: dict[str, str] = {}
    epoch_offset = None
    dropped = {}
    for n in NODES:
        path = os.path.join(session_dir, f"{stem}_{n}.bin")
        amp, ts, start, eo = load_node(path)
        nodes[n] = clean_arrays(amp, ts, fs, keep=keep, baseline=baselines[n], grid_origin=0.0, n_dropped_restart=start)
        rx_files[n] = os.path.relpath(path)
        dropped[n] = start
        if epoch_offset is None:
            epoch_offset = eo
    n_samp = int(round(window_s * fs))
    starts = window_starts(nodes, window_s, stride_s, fs)
    n_sub = nodes[NODES[0]].amplitude.shape[1]
    X = np.zeros((len(starts), len(NODES), n_samp, n_sub), dtype=dtype)
    metas: list[WindowMeta] = []
    part = sidecar.get("participant", {})
    for k, T in enumerate(starts):
        gaps = {}
        for j, n in enumerate(NODES):
            c = nodes[n]
            i0 = int(round((T - c.grid[0]) * fs))
            X[k, j] = c.amplitude[i0:i0 + n_samp].astype(dtype)
            gaps[n] = round(float(c.packet_gap_s[i0:i0 + n_samp].max()), 4)
        m = WindowMeta(
            participant=str(sidecar["participant_code"]), session_id=str(sidecar["session_id"]), room=str(sidecar["room"]),
            file_id=stem, rx_files=rx_files, index=k, t_start_abs=round(float(T), 6),
            t_start_epoch=round(float(T + (epoch_offset or 0.0)), 6), mode="idle",
            clothing=str(part.get("clothing") or ""), footwear=str(part.get("footwear") or ""),
            height_cm=part.get("height_cm"), weight_kg=part.get("weight_kg"),
            max_packet_gap=max(gaps.values()), max_packet_gap_per_rx=gaps, gap_flag=max(gaps.values()) > MAX_VERIFIED_GAP_S,
        )
        label_window(m, float(T), float(T + window_s), sidecar)
        metas.append(m)
    summary = {
        "stem": stem, "n_windows": len(metas), "window_s": window_s, "stride_s": stride_s, "fs": fs,
        "dtype": np.dtype(dtype).name, "stale_packets_dropped": dropped,
        "modes": {md: sum(1 for m in metas if m.mode == md) for md in ("grid", "walk", "walk_edge", "idle")},
        "dwells": len({m.dwell_id for m in metas if m.dwell_id is not None}),
        "passes": len({m.pass_id for m in metas if m.pass_id is not None}),
        "gap_flagged": sum(1 for m in metas if m.gap_flag),
        "grid_span_s": {n: [float(c.grid[0]), float(c.grid[-1])] for n, c in nodes.items()},
    }
    return X, metas, summary


def write_recording(X: np.ndarray, metas: list[WindowMeta], summary: dict, out_dir: str, stem: str) -> tuple[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    npz = os.path.join(out_dir, f"{stem}.npz")
    meta_path = os.path.join(out_dir, f"{stem}.meta.json")
    np.savez(npz, X=X,
             t_start_abs=np.array([m.t_start_abs for m in metas]),
             max_packet_gap=np.array([m.max_packet_gap for m in metas], dtype=np.float32),
             gap_flag=np.array([m.gap_flag for m in metas]),
             dwell_id=np.array([-1 if m.dwell_id is None else m.dwell_id for m in metas]),
             pass_id=np.array([-1 if m.pass_id is None else m.pass_id for m in metas]))
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "windows": [m.__dict__ for m in metas]}, f)
    return npz, meta_path


def recordings_in(session_dir: str) -> list[str]:
    """Stems of the labelled participant recordings in a session directory (never the demo)."""
    stems = []
    for sc in sorted(glob.glob(os.path.join(session_dir, "participant_*.gt.json"))):
        stem = os.path.basename(sc)[:-len(".gt.json")]
        if "_DEMO_" in stem:
            continue
        if all(os.path.exists(os.path.join(session_dir, f"{stem}_{n}.bin")) for n in NODES):
            stems.append(stem)
    return stems


def baseline_dir_for(session_dir: str, stem: str) -> str:
    with open(os.path.join(session_dir, f"{stem}.gt.json"), encoding="utf-8") as f:
        b = json.load(f).get("baseline_capture")
    if not b:
        raise ValueError(f"{stem}: sidecar names no baseline capture")
    return b.rstrip("/")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Cut every labelled recording into 2 s fusion windows with metadata.")
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="data/windows")
    ap.add_argument("--sessions", nargs="*", default=None, help="session ids to cut, e.g. 01 02 (default: all present)")
    ap.add_argument("--stride", type=float, default=STRIDE_S)
    ap.add_argument("--dtype", default=np.dtype(STORE_DTYPE).name, choices=["float16", "float32"])
    args = ap.parse_args(argv)
    if args.stride < STRIDE_S:
        print(f"note: stride {args.stride} s is the real-time stride; never report a dataset size from it")
    dtype = np.dtype(args.dtype).type
    total = 0
    for session_dir in sorted(glob.glob(os.path.join(args.data, "room_*", "session_*"))):
        sid = os.path.basename(session_dir).split("_")[1]
        if args.sessions and sid not in args.sessions:
            continue
        out_dir = os.path.join(args.out, os.path.basename(os.path.dirname(session_dir)), os.path.basename(session_dir))
        cache: dict[str, dict[str, np.ndarray]] = {}
        for stem in recordings_in(session_dir):
            bdir = baseline_dir_for(session_dir, stem)
            if bdir not in cache:
                cache[bdir] = session_baseline(bdir)
            X, metas, summary = cut_recording(session_dir, stem, cache[bdir], stride_s=args.stride, dtype=dtype)
            npz, _ = write_recording(X, metas, summary, out_dir, stem)
            total += len(metas)
            md = summary["modes"]
            print(f"  {os.path.basename(session_dir)}/{stem:34s} {len(metas):5d} windows  grid {md['grid']:4d} walk {md['walk']:4d} edge {md['walk_edge']:3d} idle {md['idle']:4d}"
                  f"  dwells {summary['dwells']:2d} passes {summary['passes']:2d}  gap-flagged {summary['gap_flagged']:3d}  {X.nbytes / 1e6:6.0f} MB", flush=True)
    print(f"{total} windows written under {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
