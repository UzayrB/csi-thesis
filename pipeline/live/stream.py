"""The live window stream: packets in, the shipped tree's windows out, re-cut at every start press.

The offline tree (`y4_pressalign.cut_one`, through `windows.cut_recording`) is cut AFTER the recording:

  - each receiver is cleaned in ONE pass over the whole file (`clean_arrays`, grid origin 0);
  - the base lattice is every multiple of the stride from the first instant all three receivers cover;
  - each window belongs to the pass whose SEGMENT holds its base start, where segments meet halfway
    between one pass's END press and the next pass's START press (the first segment reaches back to
    the recording's start), and is shifted onto that pass's press phase (`pa_starts`).

Live, three things about that are not causal, and this module handles each one exactly:

  1  CLEANING. Only two steps reach beyond a packet: the Hampel filter (`remove_outliers`,
     `OUTLIER_WINDOW` packets each side) and the resampler's linear interpolation (the two packets
     bracketing a sample). A window cut from a slice holding `MARGIN_PACKETS` packets beyond each
     bracketing packet is therefore cleaned from the same neighbourhood as in the whole file. The
     pinned engine cuts with 0.05 s instead (under 10 packets), and its windows differ from the tree's:
     measured 2026-09-25, 94 of 94 windows, by up to 0.93 against a typical value of 0.11. The price
     here is waiting for `MARGIN_PACKETS` packets after a window ends, about 0.09 s.
  2  THE PHASE BEFORE A PRESS. Windows between a segment's boundary and its start press are cut before
     the press exists. At the press they are re-cut on its phase from the buffered radio (`press`
     returns them), back to `RECUT_BACK_S` before the press, which covers everything the decision and
     the start terms read; at the FIRST press, back to the recording's start, because the veto's AdaBN
     statistics come from the idle windows before it.
  3  THE BOUNDARY needs the previous pass's END press. The operator presses it; the decoder is never
     told it (the decision stays semi-bounded). Without it the boundary is unknown and the re-cut
     falls back to the whole look-back, which differs from the tree wherever two passes are closer
     than 2 x RECUT_BACK_S; that fallback is recorded on the pass (`boundary_known`).

Press times are the RAW key times. The tree's lattice is phased on the sidecar's `t_start`, which is the
key's raw `time.monotonic()` (`ground_truth.py` appends `ev.t_mono` unchanged; the reaction-time bias
is subtracted only inside position interpolation). Subtracting the bias here would put every live
window 51 ms off the tree's.

The packet times must be anchored exactly as offline for the windows to be equal, and offline anchors
each receiver with ONE fit over the whole file (`anchor_times`), which no live system has. Replays
push the offline anchoring (the stream gate); a live capture pushes a causal fit, and the difference
is measured, not assumed away.

RSSI is resampled on each window's own lattice exactly as `features.rssi_series`: interpolated
against every packet's host time (all packets, the stale-boot ones included), at the window's epoch
start (`round(t0 + epoch_offset, 6)`, the offset taken from RX1's first packet) plus the sample offsets.
"""

from __future__ import annotations

import math
from bisect import bisect_left, bisect_right

import numpy as np

#: packets kept beyond each window's bracketing packets: the Hampel half-window (10) plus three
MARGIN_PACKETS = 13
#: at a start press (not the first), windows are re-cut back to this long before the press. The
#: decision and the display read back `decoder.LOOKBACK_W` = 8 windows (4 s) before the first walk
#: window (press - 1 s), so to press - 5 s; the start terms read windows starting at press - 4 s
RECUT_BACK_S = 6.0
#: raw radio kept behind the newest emitted window once the first press has happened
RETAIN_S = 20.0
#: a press re-cuts consecutive windows by cleaning each receiver ONCE over their joint span, at most
#: this many windows (20 s) at a time, then slicing the windows from it. Each sample still sits on the
#: whole file's grid instant with the whole file's neighbourhood, so the windows are the same bits;
#: it is about four times cheaper than one slice per window, which overlap fourfold
SPAN_WINDOWS = 40


def clean_window(amp: np.ndarray, ts: np.ndarray, grid: np.ndarray, baseline: np.ndarray) -> tuple:
    """`clean_arrays`' chain on a slice of packets, sampled at the given grid instants.

    The same pinned steps in the same order (subcarrier selection, per-packet shape normalisation, the
    Hampel filter on the packets, de-duplication and linear interpolation, the gap record, baseline
    subtraction). Only the grid is supplied rather than built, so the samples sit at the whole file's
    float64 instants. The duplicate-fraction refusal is the whole file's to make, and is not repeated
    on a slice."""
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


class _Radio:
    """One receiver's packets in arrival order."""

    def __init__(self):
        self.t, self.a = [], []
        self.trimmed = 0              # packets dropped from the front; 0 means the buffer holds the start

    def push(self, t: float, a) -> None:
        self.t.append(float(t))
        self.a.append(np.asarray(a, np.float32))

    def trim_before(self, t: float) -> None:
        i = max(0, bisect_left(self.t, t) - MARGIN_PACKETS - 2)
        if i > 0:
            del self.t[:i]
            del self.a[:i]
            self.trimmed += i


class LiveStream:
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
        self.rssi_t = {n: [] for n in self.nodes}      # host times, sorted; ties keep arrival order
        self.rssi_v = {n: [] for n in self.nodes}
        self.first_t = {}              # each receiver's first packet time, for the grid's end
        self.epoch_offset = None
        self.lo = None                 # max over receivers of the first grid instant (`window_starts`)
        self.first_base = None
        self.next_k = 0                # next base index to cut
        self.k_min = 0                 # lowest base index whose radio is still buffered
        self.passes = []               # {"t_start", "t_end", "shift", "boundary", "boundary_known"}
        self.windows = {}              # base index -> window record, for everything still retained
        self.last_kept_t0 = -math.inf
        self.recuts = []
        self.n_dropped_backwards = 0

    # -- inputs --------------------------------------------------------------------------------
    def push_packet(self, node: str, t: float, amplitude, t_host: float = None, t_mono: float = None) -> list:
        """One CSI packet with its anchored time. Returns every window it completes."""
        if node not in self.radio:
            return []
        if self.epoch_offset is None and node == self.nodes[0] and t_host is not None:
            self.epoch_offset = float(t_host) - float(t_mono)
        r = self.radio[node]
        if r.t and float(t) <= r.t[-1]:
            # a causal clock refit can step a packet behind the one before it; offline times are
            # strictly increasing, so the packet is dropped and counted, as a lost packet would be
            self.n_dropped_backwards += 1
            return []
        r.push(t, amplitude)
        self.first_t.setdefault(node, float(t))
        if self.lo is None and all(self.radio[n].t for n in self.nodes):
            self.lo = max(math.ceil(self.radio[n].t[0] * self.fs - 1e-9) / self.fs for n in self.nodes)
            self.first_base = math.ceil(self.lo / self.stride_s - 1e-9) * self.stride_s
        return self._drain()

    def push_rssi(self, node: str, t_host: float, rssi: float) -> None:
        if node in self.rssi_t:
            ts = self.rssi_t[node]
            j = bisect_right(ts, float(t_host))
            ts.insert(j, float(t_host))
            self.rssi_v[node].insert(j, float(rssi))

    def press(self, t_press: float) -> dict:
        """A START press (raw key time). Re-phases the lattice and re-cuts what the press re-assigns."""
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
                # on the new phase this window ends later than the radio received so far: withdraw it
                # and everything after it; they are cut again as the radio arrives
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

    def end_press(self, t_end: float) -> None:
        """The current pass's END press: it places the next segment's boundary, nothing else."""
        if self.passes:
            self.passes[-1]["t_end"] = float(t_end)

    def close(self) -> dict:
        """The recording stopped: the tree's two end limits, applied now that the end is known.

        `window_starts` keeps a BASE start only up to the last instant every receiver covers less a
        window, and `pa_starts` then keeps the SHIFTED start only up to the same instant. A window
        whose base start is past it can still have its shifted start inside it (a negative shift),
        and live it may already have been cut, because nobody knew the recording was about to stop.
        Such windows are WITHDRAWN here; the caller removes them before deciding an open pass.
        Returns {"windows": newly cut, "withdrawn": base indices}."""
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

    # -- windows ---------------------------------------------------------------------------------
    def rssi_window(self, t0_epoch: float) -> np.ndarray:
        """(receivers, samples) RSSI on the window's lattice, exactly as `features.rssi_series`."""
        lat = float(t0_epoch) + np.arange(self.n_samp) / self.fs
        out = np.zeros((len(self.nodes), self.n_samp), np.float32)
        for li, n in enumerate(self.nodes):
            ts, vs = self.rssi_t[n], self.rssi_v[n]
            if not ts:
                continue
            # np.interp reads, for each x, the LAST sample at or before it and the first after it
            # (ties included), so this slice gives the whole file's answer
            a = max(0, bisect_right(ts, float(lat[0])) - 1)
            b = bisect_right(ts, float(lat[-1])) + 1
            out[li] = np.interp(lat, np.asarray(ts[a:b], np.float64),
                                np.asarray(vs[a:b], np.float64)).astype(np.float32)
        return out

    def ordered(self) -> list:
        return [self.windows[k] for k in sorted(self.windows)]

    # -- internals --------------------------------------------------------------------------------
    def _base(self, k: int) -> float:
        return self.first_base + k * self.stride_s

    def _shift(self, P: float) -> float:
        """`pa_starts`' shift for a press, with its arithmetic: d = (P + eps - base0) / stride."""
        d = (float(P) + self.eps - float(self.first_base)) / self.stride_s
        return (d - math.floor(d + 0.5)) * self.stride_s

    def _current_shift(self, T: float) -> tuple:
        """(segment, shift) for base start T: the last pass whose boundary is at or before it, as
        `pa_starts`' searchsorted(side="right"). Before any press: (None, 0.0), the absolute lattice."""
        seg, s = None, 0.0
        for i, p in enumerate(self.passes):
            if T >= p["boundary"]:
                seg, s = i, p["shift"]
        return seg, s

    def _grid_start(self, n: str) -> float:
        """The receiver's whole-file grid origin, with `resample_uniform`'s arithmetic (origin 0)."""
        return 0.0 + np.ceil((self.first_t[n] - 0.0) * self.fs - 1e-9) / self.fs

    def _grid_last(self, n: str) -> float:
        start = self._grid_start(n)
        m = int(np.floor((self.radio[n].t[-1] - start) * self.fs + 1e-9)) + 1
        return start + (m - 1) / self.fs

    def _grid(self, n: str, T2: float) -> np.ndarray:
        """The window's samples on the WHOLE FILE's grid: `start + i / fs`, i from `cut_recording`'s i0.
        A slice's own grid (`slice_start + j / fs`) differs in the last bits and moves float16 values."""
        start = self._grid_start(n)
        i0 = int(round((T2 - start) * self.fs))
        return start + np.arange(i0, i0 + self.n_samp, dtype=np.float64) / self.fs

    def _ready(self, t0: float) -> bool:
        for n in self.nodes:
            r = self.radio[n]
            g_hi = t0 + self.window_s if n not in self.first_t else float(self._grid(n, t0)[-1])
            if len(r.t) <= bisect_right(r.t, g_hi) + MARGIN_PACKETS:
                return False
        if self.epoch_offset is not None and any(self.rssi_t[n] for n in self.nodes):
            # the RSSI sample AFTER the window's last lattice instant must have arrived, or np.interp
            # would hold the last value where the whole file interpolates
            e_last = round(t0 + self.epoch_offset, 6) + (self.n_samp - 1) / self.fs
            if any(not self.rssi_t[n] or self.rssi_t[n][-1] <= e_last for n in self.nodes):
                return False
        return True

    def _slice(self, n: str, g_lo: float, g_hi: float):
        """The packets from MARGIN_PACKETS before the one bracketing g_lo to MARGIN_PACKETS after the one
        bracketing g_hi: every packet the Hampel filter and the interpolation read for these samples."""
        r = self.radio[n]
        a = bisect_right(r.t, g_lo) - 1 - MARGIN_PACKETS
        if a < 0 and r.trimmed:
            raise RuntimeError(f"{n}: the radio before {g_lo:.3f} was trimmed; the window cannot be cut exactly")
        b = bisect_right(r.t, g_hi) + 1 + MARGIN_PACKETS
        return np.stack(r.a[max(0, a):b]), np.asarray(r.t[max(0, a):b], np.float64)

    def _cut(self, k: int, seg, shift: float):
        """Base window k on the given shift: the cleaned window as the tree stores it, or None if dropped."""
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

    def _cut_span(self, ks: list, seg, shift: float) -> dict:
        """Consecutive base windows on one shift, cleaned once per receiver over their joint span."""
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

    def _apply(self, changed: list) -> None:
        for k, rec in changed:
            if rec is None:
                self.windows.pop(k, None)
            else:
                self.windows[k] = rec
        # the tree keeps a window only if it starts after the one before it
        last = -math.inf
        for k in sorted(self.windows):
            t = self.windows[k]["t0_exact"]
            if t <= last + 1e-6:
                self.windows.pop(k)
                continue
            last = t
        self.last_kept_t0 = last

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

    def _drain(self) -> list:
        out = []
        while self.first_base is not None:
            T = self._base(self.next_k)
            T2 = T + self._current_shift(T)[1]
            if not self._ready(T2):
                break
            out += self._emit(self.next_k)
        return out

    def _trim(self, newest_t0: float) -> None:
        if not self.passes:
            return                     # everything is kept until the first press
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
