# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: A recorded session as the live system would have received it: frames in arrival order, and presses.

from __future__ import annotations

import json
import os

import numpy as np


# (events, info).
def recording_events(session_dir: str, stem: str, end_presses: bool = True, causal_anchor: bool = False):
    from pipeline.io.clean import anchor_times
    from pipeline.io.capture_logger import read_capture_file
    from pipeline.live.realtime_engine import NODES
    with open(os.path.join(session_dir, f"{stem}.gt.json"), encoding="utf-8") as f:
        sc = json.load(f)
    ev = []
    info = {"stem": stem, "frames": {}, "stale": {}}
    for n in NODES:
        _h, fr = read_capture_file(os.path.join(session_dir, f"{stem}_{n}.bin"))
        if causal_anchor:
            from pipeline.live.anchor import causal_anchor_times
            ts, start = causal_anchor_times(fr["local_timestamp"], fr["t_mono"])
        else:
            ts, start = anchor_times(fr["local_timestamp"], fr["t_mono"])
        amp = np.sqrt((fr["data"][start:].astype(np.float32).reshape(len(fr) - start, 128, 2) ** 2).sum(-1))
        t_mono = np.asarray(fr["t_mono"], np.float64)
        t_host = np.asarray(fr["t_host"], np.float64)
        rssi = np.asarray(fr["rssi"], np.float32)
        for i in range(len(fr)):
            j = i - start
            ev.append((float(t_mono[i]), 1, "frame", n,
                       float(ts[j]) if j >= 0 else None, amp[j] if j >= 0 else None,
                       float(t_host[i]), float(rssi[i]), float(t_mono[i])))
        info["frames"][n], info["stale"][n] = int(len(fr)), int(start)
    for p in sc.get("passes", []):
        ev.append((float(p["t_start"]), 0, "press", float(p["t_start"]), int(p["pass_id"])))
        if end_presses:
            ev.append((float(p["t_end"]), 0, "end", float(p["t_end"]), int(p["pass_id"])))
    ev.sort(key=lambda e: (e[0], e[1]))
    info["passes"] = len(sc.get("passes", []))
    return ev, info


# Push the events through a LiveStream.
def feed(stream, events, on_windows=None, on_press=None, on_close=None):
    for e in events:
        kind = e[2]
        if kind == "frame":
            _t, _o, _k, n, ts, amp, t_host, rssi, t_mono = e
            stream.push_rssi(n, t_host, rssi)
            if ts is not None:
                out = stream.push_packet(n, ts, amp, t_host=t_host, t_mono=t_mono)
                if out and on_windows:
                    on_windows(out)
        elif kind == "press":
            r = stream.press(e[3])
            if on_press:
                on_press(e[4], r)
        elif kind == "end":
            stream.end_press(e[3])
    res = stream.close()
    if on_close:
        on_close(res["withdrawn"])
    if res["windows"] and on_windows:
        on_windows(res["windows"])
