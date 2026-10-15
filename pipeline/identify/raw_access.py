"""The ONE place that knows how to get raw per-packet CSI for a pass. Everything else calls this.

WHY THIS MODULE IS SEPARATE. Addendum B established that C1 resampling needs per-packet timing,
that the timing exists in the `.bin` captures, and that it does NOT exist in the windowed artefact
`common.pass_stream` reads. What is NOT yet established, because it cannot be checked without
reading data, is whether the `.bin` host clock and the recording's window clock are the same clock,
and therefore whether a pass's span can be cut out of the raw frames at all.

That single unknown is confined to this file. Every stage from id12 onward calls `pass_raw` and
gets either raw frames with timing, or an explicit, labelled fallback. If the alignment turns out
to be wrong, ONE function is fixed rather than six stages, and the fallback means band (b) still
runs: only C1 is lost, and its loss is recorded rather than hidden.

`data/` IS READ ONLY. Nothing here writes to it, and nothing here writes anywhere at all.
"""

from __future__ import annotations

import glob
import os
from typing import Optional

import numpy as np

#: how far apart the two clocks may be before alignment is declared failed, in seconds
ALIGN_TOL_S = 2.0

SOURCE_RAW = "raw_bin_with_per_packet_timing"
SOURCE_WINDOWED = "windowed_artefact_NO_PER_PACKET_TIMING"


def bin_paths(session: str, stem: str) -> list:
    d = os.path.join("data", "room_A", f"session_{session}")
    return sorted(glob.glob(os.path.join(d, f"{stem}_RX*.bin")))


def verify_alignment(session: str, stem: str, rec=None) -> dict:
    """Do the .bin host clock and the recording's window clock describe the same timeline?

    This is the question the whole raw path rests on, so it is asked explicitly, answered with a
    number, and recorded. It is never assumed.
    """
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
        except Exception as e:                                             # noqa: BLE001
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


def _frames(path: str):
    """Read a capture once per process. The files are re-cut many times per recording."""
    if path not in _BIN_CACHE:
        from pipeline.io.capture_logger import read_capture_file
        try:
            _BIN_CACHE[path] = read_capture_file(path)[1]
        except Exception:                                                  # noqa: BLE001
            _BIN_CACHE[path] = None
    return _BIN_CACHE[path]


def amplitude_from_frames(sub) -> np.ndarray:
    """Subcarrier amplitude from the raw interleaved int8 payload, vectorised over packets.

    The `.bin` header states the layout: "interleaved int8 (imag, real) per subcarrier, LLTF then
    HT-LTF", 256 bytes giving 128 subcarriers. `parse.extract_amplitude` does this one RECORD at a
    time and expects a `CsiRecord`; a structured frame array is not one, which is why the first run
    returned amp=None for every link and id13 produced no features at all. Doing it as one array
    operation is both correct and far faster.
    """
    d = np.asarray(sub["data"], np.int8).astype(np.float32)
    imag, real = d[:, 0::2], d[:, 1::2]
    return np.sqrt(imag * imag + real * real)


def local_seconds(sub) -> np.ndarray:
    """The RECEIVER's own microsecond clock, in seconds, unwrapped.

    THIS IS THE CLOCK C1 MUST USE, and not `t_host`. Measured on session 01 RX1: `t_host` and
    `t_mono` both run at 19.9 Hz with a median gap of 50.1 ms, because the host drains the serial
    buffer twenty times a second and stamps a whole batch at once. `local_timestamp` runs at
    143.1 Hz, which is the real packet rate and matches the project's nominal 150. Resampling on
    `t_host` would quantise every pass onto a 20 Hz grid and destroy the entire path-rate band:
    Nyquist would be 10 Hz rather than about 72.

    `t_host` remains correct for CUTTING a pass span, because it is wall clock and lines up with
    the recording's window timeline. The two clocks are used for different jobs.
    """
    lt = np.asarray(sub["local_timestamp"], np.float64) * 1e-6
    if len(lt) > 1:                       # the ESP32 microsecond counter wraps at 2^32 us
        d = np.diff(lt)
        wrap = np.flatnonzero(d < -1.0)
        for i in wrap:
            lt[i + 1:] += 2.0 ** 32 * 1e-6
    return lt - lt[0] if len(lt) else lt


def raw_for_span(session: str, stem: str, t0: float, t1: float,
                 min_packets: int = 30) -> Optional[dict]:
    """Per-packet amplitude, timing, gain and radio metadata for ONE TIME SPAN, per link.

    The generic cut. `pass_raw` is this with a pass's span, and id12 uses it for the `idle` and
    `grid` null windows, which have no pass_id.
    """
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
        except Exception:                                                  # noqa: BLE001
            amp = None
        names = fr.dtype.names
        links[name] = {
            "t": t[m],                       # wall clock, for alignment and span cutting
            "t_local": local_seconds(sub),   # the receiver clock, for C1 resampling
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


def windows_raw(session: str, stem: str, windows, rec=None,
                pad_s: float = 0.0) -> Optional[dict]:
    """Raw frames spanning a set of WINDOW indices. Used for the idle and grid nulls."""
    if rec is None:
        from pipeline.constrained.recordings import load_meta
        rec = load_meta(session, stem)
    idx = np.asarray(windows, int)
    if not len(idx):
        return None
    te = np.asarray(rec.t0_epoch, float)
    return raw_for_span(session, stem, float(te[idx].min()) - pad_s,
                        float(te[idx].max()) + pad_s)


def pass_raw(session: str, stem: str, pass_id: int, rec=None,
             pad_s: float = 0.0) -> Optional[dict]:
    """Per-packet amplitude, timing, gain and radio metadata for one pass, per link.

    Returns None if the raw path is unusable for this pass, which is a signal to the caller to use
    `pass_windowed` and to record the fallback. It never silently substitutes one for the other.
    """
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


def pass_windowed(session: str, stem: str, windows: np.ndarray, fs: float = 150.0) -> dict:
    """The declared fallback. Band (b) still runs; C1 does not, and that is recorded, not hidden."""
    from pipeline.identify.common import pass_stream
    stream = pass_stream(session, stem, windows)          # (3, n_samples, n_sub)
    n = stream.shape[1]
    t = np.arange(n) / fs                                  # NOMINAL, not measured
    return {"source": SOURCE_WINDOWED, "session": session, "stem": stem,
            "links": {f"RX{i + 1}": {"t": t, "t_local": t, "amp": np.asarray(stream[i], float),
                                     "gain": None, "channel": None, "pkt_id": None}
                      for i in range(stream.shape[0])},
            "c1_possible": False,
            "WARNING": ("timing is the NOMINAL grid, not measured per-packet timing. C1 cannot be "
                        "applied and any jitter or dropout is invisible here")}


def describe_source(d: dict) -> str:
    return ("raw per-packet frames; C1 available" if d.get("c1_possible")
            else "windowed artefact; C1 NOT available and every figure says so")
