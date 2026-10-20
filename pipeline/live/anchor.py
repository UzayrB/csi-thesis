# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Device-clock anchoring, live.

from __future__ import annotations

import numpy as np

REFIT_S = 10.0
MIN_PACKETS = 100


# One receiver.
class CausalAnchor:

    # Sets up the object.
    def __init__(self, refit_s: float = REFIT_S):
        self.refit_s = float(refit_s)
        self.local, self.mono, self.x = [], [], []
        self.wraps, self.tb, self.fit_at, self.timed = 0, None, None, 0

    # Function push.
    def push(self, local_us: int, t_mono: float) -> list:
        from pipeline.io.clean import DEVICE_CLOCK_MODULUS_US, WRAP_MARGIN_US, fit_timebase
        local_us = int(local_us)
        if self.local and local_us < self.local[-1] and self.local[-1] > DEVICE_CLOCK_MODULUS_US - WRAP_MARGIN_US:
            self.wraps += 1
        self.local.append(local_us)
        self.mono.append(float(t_mono))
        self.x.append(float(local_us + self.wraps * DEVICE_CLOCK_MODULUS_US))
        n = len(self.local)
        due = self.tb is None or (self.mono[-1] - self.fit_at >= self.refit_s)
        if due and n >= MIN_PACKETS:
            tb = fit_timebase(np.asarray(self.local, np.int64), np.asarray(self.mono, np.float64))
            if tb.ok:
                self.tb, self.fit_at = tb, self.mono[-1]
        if self.tb is None:
            return []
        out = [(i, float(self.tb.slope * self.x[i] + self.tb.offset)) for i in range(self.timed, n)]
        self.timed = n
        return out


# Anchor_times' interface, timed causally: (anchored times from the current boot, start index).
def causal_anchor_times(local_us, t_mono, refit_s: float = REFIT_S) -> tuple:
    from pipeline.io.clean import device_epoch_start
    local = np.asarray(local_us, np.int64)
    tm = np.asarray(t_mono, np.float64)
    start = device_epoch_start(local)
    ca = CausalAnchor(refit_s)
    ts = np.full(len(local) - start, np.nan)
    for i in range(start, len(local)):
        for j, t in ca.push(int(local[i]), float(tm[i])):
            ts[j] = t
    if np.isnan(ts).any():
        bad = np.isnan(ts)
        ts[bad] = tm[start:][bad]
    return ts, start
