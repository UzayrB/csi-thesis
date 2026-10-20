# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The ONE place that knows how to get raw per-packet CSI for a pass.

from __future__ import annotations

import glob
import os
from typing import Optional

import numpy as np

ALIGN_TOL_S = 2.0

SOURCE_RAW = "raw_bin_with_per_packet_timing"
SOURCE_WINDOWED = "windowed_artefact_NO_PER_PACKET_TIMING"


# Function bin paths.
def bin_paths(session: str, stem: str) -> list:
    d = os.path.join("data", "room_A", f"session_{session}")
    return sorted(glob.glob(os.path.join(d, f"{stem}_RX*.bin")))


# Do the.bin host clock and the recording's window clock describe the same timeline?
def verify_alignment(session: str, stem: str, rec=None) -> dict:
    from pipeline.io.capture_logger import read_capture_file
    if rec is None:
        from pipeline.constrained.recordings import load_meta
        rec = load_meta(session, stem)
    w0 = float(np.min(rec.t0_epoch))
    w1 = float(np.max(rec.t0_epoch))
    out = {"session": session, "stem": stem, "window_epoch_span": [w0, w1], "links": {}}
    offs = []
    for p in bin_paths(session, stem):
        try:
            _hdr, fr = read_capture_file(p)
        except Exception as e:
            out["links"][os.path.basename(p)] = {"error": str(e)}
            continue
        if not len(fr):
            continue
        t = np.asarray(fr["t_host"], float)
        b0, b1 = float(t.min()), float(t.max())
        off = b0 - w0
        offs.append(off)
        out["links"][os.path.basename(p)] = {
            "bin_span": [b0, b1], "start_offset_s": round(off, 3),
            "covers_windows": bool(b0 <= w0 + ALIGN_TOL_S and b1 >= w1 - ALIGN_TOL_S)}
    ok = bool(out["links"]) and all(v.get("covers_windows") for v in out["links"].values()
                                    if "error" not in v)
    out["median_offset_s"] = round(float(np.median(offs)), 3) if offs else None
    out["ALIGNED"] = ok
    out["consequence"] = ("raw frames can be cut per pass, so C1 runs as registered" if ok else
                          "the clocks do not line up. C1 is NOT POSSIBLE from the raw path and is "
                          "recorded as NOT RUN; band (b) still runs from the windowed artefact, "
                          "at the cost of uniform resampling")
    return out


_BIN_CACHE: dict = {}


# Read a capture once per process.
def _frames(path: str):
    if path not in _BIN_CACHE:
        from pipeline.io.capture_logger import read_capture_file
        try:
            _BIN_CACHE[path] = read_capture_file(path)[1]
        except Exception:
            _BIN_CACHE[path] = None
    return _BIN_CACHE[path]


# Subcarrier amplitude from the raw interleaved int8 payload, vectorised over packets.
def amplitude_from_frames(sub) -> np.ndarray:
    d = np.asarray(sub["data"], np.int8).astype(np.float32)
    imag, real = d[:, 0::2], d[:, 1::2]
    return np.sqrt(imag * imag + real * real)


# The RECEIVER's own microsecond clock, in seconds, unwrapped.
def local_seconds(sub) -> np.ndarray:
    lt = np.asarray(sub["local_timestamp"], np.float64) * 1e-6
    if len(lt) > 1:
        d = np.diff(lt)
        wrap = np.flatnonzero(d < -1.0)
        for i in wrap:
            lt[i + 1:] += 2.0 ** 32 * 1e-6
    return lt - lt[0] if len(lt) else lt


# Per-packet amplitude, timing, gain and radio metadata for ONE TIME SPAN, per link.
def raw_for_span(session: str, stem: str, t0: float, t1: float,
                 min_packets: int = 30) -> Optional[dict]:
    links = {}
    for p in bin_paths(session, stem):
        name = os.path.basename(p).rsplit("_", 1)[-1].replace(".bin", "")
        fr = _frames(p)
        if fr is None or not len(fr):
            continue
        t = np.asarray(fr["t_host"], float)
        m = (t >= t0) & (t <= t1)
        if m.sum() < min_packets:
            continue
        sub = fr[m]
        try:
            amp = amplitude_from_frames(sub)
        except Exception:
            amp = None
        names = fr.dtype.names
        links[name] = {
            "t": t[m],
            "t_local": local_seconds(sub),
            "amp": amp,
            "gain": np.asarray(sub["gain"], float) if "gain" in names else None,
            "rssi": np.asarray(sub["rssi"], float) if "rssi" in names else None,
            "noise_floor": (np.asarray(sub["noise_floor"], float)
                            if "noise_floor" in names else None),
            "channel": (int(np.median(np.asarray(sub["channel"])))
                        if "channel" in names else None),
            "pkt_id": np.asarray(sub["pkt_id"], np.int64) if "pkt_id" in names else None,
        }
    if not links:
        return None
    return {"source": SOURCE_RAW, "session": session, "stem": stem,
            "t_span": [t0, t1], "links": links, "c1_possible": True}


# Raw frames spanning a set of WINDOW indices.
def windows_raw(session: str, stem: str, windows, rec=None,
                pad_s: float = 0.0) -> Optional[dict]:
    if rec is None:
        from pipeline.constrained.recordings import load_meta
        rec = load_meta(session, stem)
    idx = np.asarray(windows, int)
    if not len(idx):
        return None
    te = np.asarray(rec.t0_epoch, float)
    return raw_for_span(session, stem, float(te[idx].min()) - pad_s,
                        float(te[idx].max()) + pad_s)


# Per-packet amplitude, timing, gain and radio metadata for one pass, per link.
def pass_raw(session: str, stem: str, pass_id: int, rec=None,
             pad_s: float = 0.0) -> Optional[dict]:
    if rec is None:
        from pipeline.constrained.recordings import load_meta
        rec = load_meta(session, stem)
    idx = np.flatnonzero(np.asarray(rec.pass_id) == int(pass_id))
    if not len(idx):
        return None
    te = np.asarray(rec.t0_epoch, float)
    out = raw_for_span(session, stem, float(te[idx].min()) - pad_s,
                       float(te[idx].max()) + pad_s)
    if out is not None:
        out["pass_id"] = int(pass_id)
    return out


# The declared fallback.
def pass_windowed(session: str, stem: str, windows: np.ndarray, fs: float = 150.0) -> dict:
    from pipeline.identify.common import pass_stream
    stream = pass_stream(session, stem, windows)
    n = stream.shape[1]
    t = np.arange(n) / fs
    return {"source": SOURCE_WINDOWED, "session": session, "stem": stem,
            "links": {f"RX{i + 1}": {"t": t, "t_local": t, "amp": np.asarray(stream[i], float),
                                     "gain": None, "channel": None, "pkt_id": None}
                      for i in range(stream.shape[0])},
            "c1_possible": False,
            "WARNING": ("timing is the NOMINAL grid, not measured per-packet timing. C1 cannot be "
                        "applied and any jitter or dropout is invisible here")}


# Function describe source.
def describe_source(d: dict) -> str:
    return ("raw per-packet frames; C1 available" if d.get("c1_possible")
            else "windowed artefact; C1 NOT available and every figure says so")
