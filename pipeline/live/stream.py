# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The live window stream: packets in, the shipped tree's windows out, re-cut at every start press.

from __future__ import annotations

import math
from bisect import bisect_left, bisect_right

import numpy as np

MARGIN_PACKETS = 13
RECUT_BACK_S = 6.0
RETAIN_S = 20.0
SPAN_WINDOWS = 40


# Clean_arrays' chain on a slice of packets, sampled at the given grid instants.
def clean_window(amp: np.ndarray, ts: np.ndarray, grid: np.ndarray, baseline: np.ndarray) -> tuple:
    from pipeline.io.clean import (normalise_shape, packet_gap_on_grid, remove_outliers,
                                       select_subcarriers, subtract_baseline)
    a = select_subcarriers(np.asarray(amp, dtype=np.float32), None)
    a = normalise_shape(a, None)
    a = remove_outliers(a)
    a = np.asarray(a, dtype=np.float64)
    t = np.asarray(ts, dtype=np.float64)
    uniq, first = np.unique(t, return_index=True)
    a, t = a[first], uniq
    out = np.empty((len(grid), a.shape[1]), dtype=np.float32)
    for j in range(a.shape[1]):
        out[:, j] = np.interp(grid, t, a[:, j])
    gaps = packet_gap_on_grid(np.asarray(ts, dtype=np.float64), grid)
    return subtract_baseline(out, np.asarray(baseline, dtype=np.float32)), gaps


# One receiver's packets in arrival order.
class _Radio:

    # Sets up the object.
    def __init__(self):
        self.t, self.a = [], []
        self.trimmed = 0

    # Function push.
    def push(self, t: float, a) -> None:
        self.t.append(float(t))
        self.a.append(np.asarray(a, np.float32))

    # Function trim before.
    def trim_before(self, t: float) -> None:
        i = max(0, bisect_left(self.t, t) - MARGIN_PACKETS - 2)
        if i > 0:
            del self.t[:i]
            del self.a[:i]
            self.trimmed += i


# Class Live Stream.
class LiveStream:
    # Sets up the object.
    def __init__(self, baseline: dict, nodes=None, fs: float = None, window_s: float = None,
                 stride_s: float = None, eps: float = None):
        from pipeline.constrained.lattice import PRESS_EPS_S
        from pipeline.constrained.y4_pressalign import STRIDE_S
        from pipeline.live.realtime_engine import NODES
        from pipeline.io.windows import FS, WINDOW_S
        self.nodes = tuple(nodes or NODES)
        self.fs = float(fs or FS)
        self.window_s = float(window_s or WINDOW_S)
        self.stride_s = float(stride_s or STRIDE_S)
        self.eps = float(PRESS_EPS_S if eps is None else eps)
        self.n_samp = int(round(self.window_s * self.fs))
        self.baseline = {n: np.asarray(baseline[n], np.float32) for n in self.nodes}
        self.radio = {n: _Radio() for n in self.nodes}
        self.rssi_t = {n: [] for n in self.nodes}
        self.rssi_v = {n: [] for n in self.nodes}
        self.first_t = {}
        self.epoch_offset = None
        self.lo = None
        self.first_base = None
        self.next_k = 0
        self.k_min = 0
        self.passes = []
        self.windows = {}
        self.last_kept_t0 = -math.inf
        self.recuts = []
        self.n_dropped_backwards = 0

    # One CSI packet with its anchored time.
    def push_packet(self, node: str, t: float, amplitude, t_host: float = None, t_mono: float = None) -> list:
        if node not in self.radio:
            return []
        if self.epoch_offset is None and node == self.nodes[0] and t_host is not None:
            self.epoch_offset = float(t_host) - float(t_mono)
        r = self.radio[node]
        if r.t and float(t) <= r.t[-1]:
            self.n_dropped_backwards += 1
            return []
        r.push(t, amplitude)
        self.first_t.setdefault(node, float(t))
        if self.lo is None and all(self.radio[n].t for n in self.nodes):
            self.lo = max(math.ceil(self.radio[n].t[0] * self.fs - 1e-9) / self.fs for n in self.nodes)
            self.first_base = math.ceil(self.lo / self.stride_s - 1e-9) * self.stride_s
        return self._drain()

    # Function push rssi.
    def push_rssi(self, node: str, t_host: float, rssi: float) -> None:
        if node in self.rssi_t:
            ts = self.rssi_t[node]
            j = bisect_right(ts, float(t_host))
            ts.insert(j, float(t_host))
            self.rssi_v[node].insert(j, float(rssi))

    # A START press (raw key time).
    def press(self, t_press: float) -> dict:
        P = float(t_press)
        prev = self.passes[-1] if self.passes else None
        first = prev is None
        shift = self._shift(P)
        if first:
            boundary, known = -math.inf, True
        elif prev.get("t_end") is not None:
            boundary, known = 0.5 * (float(prev["t_end"]) + P), True
        else:
            boundary, known = -math.inf, False
        self.passes.append({"t_start": P, "t_end": None, "shift": shift, "boundary": boundary,
                            "boundary_known": known})
        floor_t = -math.inf if first else P - RECUT_BACK_S
        seg = len(self.passes) - 1
        todo, withdrawn = [], []
        for k in range(self.k_min, self.next_k):
            T = self._base(k)
            if T < boundary or T + shift < floor_t:
                continue
            if not self._ready(T + shift):
                withdrawn = list(range(k, self.next_k))
                self.next_k = k
                break
            todo.append(k)
        cut = {}
        for i in range(0, len(todo), SPAN_WINDOWS):
            cut.update(self._cut_span(todo[i:i + SPAN_WINDOWS], seg, shift))
        changed = [(k, cut[k]) for k in todo]
        for k in withdrawn:
            self.windows.pop(k, None)
        self._apply(changed)
        info = {"t_press": P, "shift": shift, "boundary": boundary, "boundary_known": known,
                "n_recut": len(changed), "n_withdrawn": len(withdrawn), "first": first}
        self.recuts.append(info)
        return {**info, "windows": [self.windows[k] for k, _r in changed if k in self.windows],
                "dropped": [k for k, r in changed if r is None or k not in self.windows],
                "withdrawn": withdrawn}

    # The current pass's END press: it places the next segment's boundary, nothing else.
    def end_press(self, t_end: float) -> None:
        if self.passes:
            self.passes[-1]["t_end"] = float(t_end)

    # The recording stopped: the tree's two end limits, applied now that the end is known.
    def close(self) -> dict:
        hi = min(self._grid_last(n) for n in self.nodes) - self.window_s
        if self.first_base is None:
            return {"windows": [], "withdrawn": []}
        k_max = int(math.floor((hi - self.first_base) / self.stride_s + 1e-9))
        withdrawn = [k for k in sorted(self.windows)
                     if k > k_max or self.windows[k]["t0_exact"] > hi + 1e-9]
        for k in withdrawn:
            self.windows.pop(k)
        self._apply([])
        self.next_k = min([self.next_k] + withdrawn)
        out = []
        while self.next_k <= k_max:
            T2 = self._base(self.next_k) + self._current_shift(self._base(self.next_k))[1]
            if T2 > hi + 1e-9:
                break
            out += self._emit(self.next_k)
        return {"windows": out, "withdrawn": withdrawn}

    # (receivers, samples) RSSI on the window's lattice, exactly as features.rssi_series.
    def rssi_window(self, t0_epoch: float) -> np.ndarray:
        lat = float(t0_epoch) + np.arange(self.n_samp) / self.fs
        out = np.zeros((len(self.nodes), self.n_samp), np.float32)
        for li, n in enumerate(self.nodes):
            ts, vs = self.rssi_t[n], self.rssi_v[n]
            if not ts:
                continue
            a = max(0, bisect_right(ts, float(lat[0])) - 1)
            b = bisect_right(ts, float(lat[-1])) + 1
            out[li] = np.interp(lat, np.asarray(ts[a:b], np.float64),
                                np.asarray(vs[a:b], np.float64)).astype(np.float32)
        return out

    # Function ordered.
    def ordered(self) -> list:
        return [self.windows[k] for k in sorted(self.windows)]

    # Function base.
    def _base(self, k: int) -> float:
        return self.first_base + k * self.stride_s

    # Pa_starts' shift for a press, with its arithmetic: d = (P + eps - base0) / stride.
    def _shift(self, P: float) -> float:
        d = (float(P) + self.eps - float(self.first_base)) / self.stride_s
        return (d - math.floor(d + 0.5)) * self.stride_s

    # (segment, shift) for base start T: the last pass whose boundary is at or before it, as pa_starts'...
    def _current_shift(self, T: float) -> tuple:
        seg, s = None, 0.0
        for i, p in enumerate(self.passes):
            if T >= p["boundary"]:
                seg, s = i, p["shift"]
        return seg, s

    # The receiver's whole-file grid origin, with resample_uniform's arithmetic (origin 0).
    def _grid_start(self, n: str) -> float:
        return 0.0 + np.ceil((self.first_t[n] - 0.0) * self.fs - 1e-9) / self.fs

    # Function grid last.
    def _grid_last(self, n: str) -> float:
        start = self._grid_start(n)
        m = int(np.floor((self.radio[n].t[-1] - start) * self.fs + 1e-9)) + 1
        return start + (m - 1) / self.fs

    # The window's samples on the WHOLE FILE's grid: start + i / fs, i from cut_recording's i0.
    def _grid(self, n: str, T2: float) -> np.ndarray:
        start = self._grid_start(n)
        i0 = int(round((T2 - start) * self.fs))
        return start + np.arange(i0, i0 + self.n_samp, dtype=np.float64) / self.fs

    # Function ready.
    def _ready(self, t0: float) -> bool:
        for n in self.nodes:
            r = self.radio[n]
            g_hi = t0 + self.window_s if n not in self.first_t else float(self._grid(n, t0)[-1])
            if len(r.t) <= bisect_right(r.t, g_hi) + MARGIN_PACKETS:
                return False
        if self.epoch_offset is not None and any(self.rssi_t[n] for n in self.nodes):
            e_last = round(t0 + self.epoch_offset, 6) + (self.n_samp - 1) / self.fs
            if any(not self.rssi_t[n] or self.rssi_t[n][-1] <= e_last for n in self.nodes):
                return False
        return True

    # The packets from MARGIN_PACKETS before the one bracketing g_lo to MARGIN_PACKETS after the one bracketing...
    def _slice(self, n: str, g_lo: float, g_hi: float):
        r = self.radio[n]
        a = bisect_right(r.t, g_lo) - 1 - MARGIN_PACKETS
        if a < 0 and r.trimmed:
            raise RuntimeError(f"{n}: the radio before {g_lo:.3f} was trimmed; the window cannot be cut exactly")
        b = bisect_right(r.t, g_hi) + 1 + MARGIN_PACKETS
        return np.stack(r.a[max(0, a):b]), np.asarray(r.t[max(0, a):b], np.float64)

    # Base window k on the given shift: the cleaned window as the tree stores it, or None if dropped.
    def _cut(self, k: int, seg, shift: float):
        T2 = float(self._base(k)) + shift
        if T2 < self.lo - 1e-9:
            return None
        links, gaps = [], []
        for n in self.nodes:
            grid = self._grid(n, T2)
            amp, ts = self._slice(n, float(grid[0]), float(grid[-1]))
            w, g = clean_window(amp, ts, grid, self.baseline[n])
            links.append(w)
            gaps.append(round(float(g.max()), 4))
        t0_epoch = round(T2 + (self.epoch_offset or 0.0), 6)
        return {"k": int(k), "t0_exact": T2, "t0": round(T2, 6), "t0_epoch": t0_epoch,
                "X": np.stack(links), "max_packet_gap": max(gaps), "rssi": self.rssi_window(t0_epoch),
                "provisional": seg is None, "segment": seg}

    # Consecutive base windows on one shift, cleaned once per receiver over their joint span.
    def _cut_span(self, ks: list, seg, shift: float) -> dict:
        out, valid = {}, []
        for k in ks:
            T2 = float(self._base(k)) + shift
            if T2 < self.lo - 1e-9:
                out[k] = None
            else:
                valid.append((k, T2))
        if not valid:
            return out
        per = {}
        for n in self.nodes:
            start = self._grid_start(n)
            i0s = [int(round((T2 - start) * self.fs)) for _k, T2 in valid]
            a, b = min(i0s), max(i0s) + self.n_samp
            grid = start + np.arange(a, b, dtype=np.float64) / self.fs
            amp, ts = self._slice(n, float(grid[0]), float(grid[-1]))
            w, g = clean_window(amp, ts, grid, self.baseline[n])
            per[n] = (a, i0s, w, g)
        for j, (k, T2) in enumerate(valid):
            links, gaps = [], []
            for n in self.nodes:
                a, i0s, w, g = per[n]
                o = i0s[j] - a
                links.append(w[o:o + self.n_samp])
                gaps.append(round(float(g[o:o + self.n_samp].max()), 4))
            t0_epoch = round(T2 + (self.epoch_offset or 0.0), 6)
            out[k] = {"k": int(k), "t0_exact": T2, "t0": round(T2, 6), "t0_epoch": t0_epoch,
                      "X": np.stack(links), "max_packet_gap": max(gaps), "rssi": self.rssi_window(t0_epoch),
                      "provisional": seg is None, "segment": seg}
        return out

    # Function apply.
    def _apply(self, changed: list) -> None:
        for k, rec in changed:
            if rec is None:
                self.windows.pop(k, None)
            else:
                self.windows[k] = rec
        last = -math.inf
        for k in sorted(self.windows):
            t = self.windows[k]["t0_exact"]
            if t <= last + 1e-6:
                self.windows.pop(k)
                continue
            last = t
        self.last_kept_t0 = last

    # Function emit.
    def _emit(self, k: int) -> list:
        seg, shift = self._current_shift(self._base(k))
        T2 = float(self._base(k)) + shift
        rec = self._cut(k, seg, shift)
        self.next_k = k + 1
        if rec is None or rec["t0_exact"] <= self.last_kept_t0 + 1e-6:
            return []
        self.windows[k] = rec
        self.last_kept_t0 = rec["t0_exact"]
        self._trim(T2)
        return [rec]

    # Function drain.
    def _drain(self) -> list:
        out = []
        while self.first_base is not None:
            T = self._base(self.next_k)
            T2 = T + self._current_shift(T)[1]
            if not self._ready(T2):
                break
            out += self._emit(self.next_k)
        return out

    # Function trim.
    def _trim(self, newest_t0: float) -> None:
        if not self.passes:
            return
        keep = newest_t0 - RETAIN_S
        for n in self.nodes:
            self.radio[n].trim_before(keep)
            j = bisect_left(self.rssi_t[n], keep + (self.epoch_offset or 0.0) - 1.0) - 1
            if j > 0:
                del self.rssi_t[n][:j]
                del self.rssi_v[n][:j]
        while self.k_min < self.next_k and self._base(self.k_min) + 0.25 < keep:
            self.windows.pop(self.k_min, None)
            self.k_min += 1
