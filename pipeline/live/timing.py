"""Gate 6's timing model: the live clock, emulated from replayed service times.

Kept apart from `gates.py`, which binds the half-stride roots when imported (tests import this).
"""

from __future__ import annotations

import numpy as np


def live_queue(events) -> dict:
    """Gate 6's timing on the live clock: one worker serving each window when its last packet arrives
    and each press when it is pressed, for the service time measured here. A window's LATENCY is how
    long after it ended (t0 + 2 s) its outputs were ready; the GAP is the time between outputs."""
    free, outs, lat = -np.inf, [], []
    for arrival, service, kind, t0 in sorted(events, key=lambda e: e[0]):
        free = max(free, arrival) + service
        if kind == "window":
            outs.append(free)
            lat.append(free - (t0 + 2.0))
    gaps = np.diff(outs) if len(outs) > 1 else np.zeros(1)
    return {"windows": len(outs), "max_latency_s": float(np.max(lat)) if lat else None,
            "p99_latency_s": float(np.percentile(lat, 99)) if lat else None,
            "max_gap_s": float(np.max(gaps)), "windows_over_0_5_s": int(sum(1 for x in lat if x > 0.5))}
