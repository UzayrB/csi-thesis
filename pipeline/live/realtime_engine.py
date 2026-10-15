"""Streaming inference: 2 s windows on the shared lattice, emitted as they complete.

The offline pipeline and this engine run the SAME code. Every cleaning step
and every branch already takes one window and fits no whole-file statistic,
which is what makes that possible: the engine slices its ring buffers,
hands the slice to :func:`pipeline.io.clean.clean_arrays`, and hands
the result to the branches unchanged.

TIMING CONTRACT (filed in the Overview report, section 4)
---------------------------------------------------------
* update interval T = 2.0 s +/- 0.5 s  -> :data:`STRIDE_S` 0.5 s of new data
  per emission, each covering :data:`WINDOW_S` 2.0 s.
* per-window latency <= 0.5 s          -> :data:`MAX_LATENCY_S`, measured
  from the arrival of the window's last packet to the result being emitted.
* maximum output gap <= 4 s            -> :data:`MAX_OUTPUT_GAP_S`.
Every emitted :class:`Result` carries its own latency and the gap since the
previous one, so the contract is verified from the output rather than
asserted.

RULES CARRIED FROM THE OFFLINE PATH
-----------------------------------
* The gate LABELS the window and never routes it. All three branches run on
  every window whatever the gate says.
* The presence threshold comes from THIS session's own empty-room baseline
  and has no default; the engine cannot be constructed without one.
* Windows sit on the absolute lattice (multiples of 1/fs from 0.0), so a
  window is the same instant on all three receivers.
* A window whose worst source-packet gap exceeds
  :data:`pipeline.io.clean.MAX_VERIFIED_GAP_S` is flagged, not dropped.

The engine never opens a serial port. It consumes records that something
else pushes in: ``pipeline.io.capture_logger`` in deployment, a capture
file in :mod:`pipeline.live.realtime_replay` for testing.
"""

from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol, Sequence

import numpy as np

from pipeline.constrained.gate import MOTION_THETA, GateLabel, label_window
from pipeline.io.clean import MAX_VERIFIED_GAP_S, clean_arrays

WINDOW_S: float = 2.0
STRIDE_S: float = 0.5
MAX_LATENCY_S: float = 0.5
MAX_OUTPUT_GAP_S: float = 4.0
NODES: tuple[str, ...] = ("RX1", "RX2", "RX3")


@dataclass(frozen=True)
class Result:
    """One window's verdict, with the numbers the timing contract is judged on."""

    t_start: float
    t_end: float
    gate: str
    band_energy: float
    identity: Optional[str]
    identity_confidence: Optional[float]
    cell: Optional[str]
    xy: Optional[tuple[float, float]]
    max_packet_gap: float
    gap_flag: bool
    latency_s: float
    gap_since_previous_s: Optional[float]
    n_links: int

    def within_contract(self) -> bool:
        return self.latency_s <= MAX_LATENCY_S and (self.gap_since_previous_s or 0.0) <= MAX_OUTPUT_GAP_S


class Predictor(Protocol):
    """What the engine needs from a model. Implemented by the trained fusion models."""

    def identify(self, window: np.ndarray) -> tuple[Optional[str], Optional[float]]:
        """Name and confidence for a cleaned ``(n_links, n_samples, n_sub)`` window."""

    def locate(self, window: np.ndarray) -> tuple[Optional[str], Optional[tuple[float, float]]]:
        """Cell id and (x, y) in metres for the same window."""


class NullPredictor:
    """A predictor that declines to answer. The engine's timing is testable without a model."""

    def identify(self, window: np.ndarray) -> tuple[Optional[str], Optional[float]]:
        return None, None

    def locate(self, window: np.ndarray) -> tuple[Optional[str], Optional[tuple[float, float]]]:
        return None, None


@dataclass
class _NodeBuffer:
    """Raw per-packet amplitude and device-anchored time for one receiver."""

    t: deque = field(default_factory=lambda: deque())
    amp: deque = field(default_factory=lambda: deque())

    def push(self, t: float, amp: np.ndarray) -> None:
        self.t.append(float(t))
        self.amp.append(np.asarray(amp, dtype=np.float32))

    def trim(self, before: float) -> None:
        while self.t and self.t[0] < before:
            self.t.popleft()
            self.amp.popleft()

    def slice(self, t0: float, t1: float) -> tuple[np.ndarray, np.ndarray]:
        idx = [i for i, tt in enumerate(self.t) if t0 <= tt <= t1]
        if not idx:
            return np.zeros((0, 128), np.float32), np.zeros(0)
        return np.stack([self.amp[i] for i in idx]), np.array([self.t[i] for i in idx])

    def covers(self, t0: float, t1: float) -> bool:
        return bool(self.t) and self.t[0] <= t0 and self.t[-1] >= t1


class RealTimeEngine:
    """Consumes per-node packets, emits one :class:`Result` per stride.

    Args:
        baseline: Per-node baseline SHAPE from THIS session's empty-room
            capture, in the retained subcarrier space. Required: there is no
            default, because a presence threshold carried across sessions
            reads half an empty room as occupied.
        presence_theta: From this session's own baseline windows. Required.
        predictor: Supplies identity and position. Defaults to declining.
        fs: Uniform grid rate.
        emit: Optional callback invoked with each result as it is produced.

    Constraints:
        Holds no serial port and starts no thread. Something else pushes
        records in; this decides only what a window means.
    """

    def __init__(self, baseline: dict[str, np.ndarray], presence_theta: float, predictor: Optional[Predictor] = None,
                 fs: float = 150.0, window_s: float = WINDOW_S, stride_s: float = STRIDE_S,
                 emit: Optional[Callable[[Result], None]] = None, nodes: Sequence[str] = NODES,
                 motion_theta: float = MOTION_THETA, cells: Optional[dict] = None) -> None:
        if not baseline or any(n not in baseline for n in nodes):
            raise ValueError(f"a baseline SHAPE is required for every node {tuple(nodes)}; this session's own, never another's")
        if not np.isfinite(presence_theta) or presence_theta <= 0:
            raise ValueError(f"presence_theta must be a positive number from this session's baseline, got {presence_theta!r}")
        self.baseline = {n: np.asarray(v, dtype=np.float32) for n, v in baseline.items()}
        self.presence_theta = float(presence_theta)
        self.motion_theta = float(motion_theta)
        self.predictor = predictor or NullPredictor()
        self.fs, self.window_s, self.stride_s = float(fs), float(window_s), float(stride_s)
        self.nodes = tuple(nodes)
        self.emit = emit
        self.buffers = {n: _NodeBuffer() for n in self.nodes}
        self.next_start: Optional[float] = None
        #: the lattice PHASE in seconds: windows start at phase + k * stride. 0.0 is the absolute
        #: lattice; `rephase_to_press` moves it onto the press (the ONE lattice, 2026-09-23d)
        self.phase: float = 0.0
        self.rephases: list = []
        self.results: list[Result] = []
        self._last_emit_t: Optional[float] = None
        self.n_windows = 0
        self.n_gap_flagged = 0
        self.n_skipped_windows = 0

    # -- ingest ---------------------------------------------------------
    def push(self, node: str, t: float, amplitude: np.ndarray) -> list[Result]:
        """Add one packet and emit every window it completes."""
        if node not in self.buffers:
            return []
        self.buffers[node].push(t, amplitude)
        if self.next_start is None and all(self.buffers[n].t for n in self.nodes):
            # The first window starts at the next stride boundary on the absolute lattice
            # that EVERY receiver already covers. Taking it from whichever node pushed
            # first would pick an instant the others have no data for, and no window
            # would ever complete.
            first = max(self.buffers[n].t[0] for n in self.nodes)
            self.next_start = self._on_phase_at_or_after(first)
        return self._drain()

    def _drain(self) -> list[Result]:
        out: list[Result] = []
        while self.next_start is not None:
            t0, t1 = self.next_start, self.next_start + self.window_s
            # A receiver whose earliest buffered packet is already past t0 can never
            # cover this window: skip forward rather than stalling for ever.
            behind = max((self.buffers[n].t[0] for n in self.nodes if self.buffers[n].t), default=None)
            if behind is not None and behind > t0:
                self.next_start = self._on_phase_at_or_after(behind)
                self.n_skipped_windows += 1
                continue
            if not all(self.buffers[n].covers(t0, t1) for n in self.nodes):
                break
            r = self._emit_window(t0, t1)
            self.next_start = t0 + self.stride_s
            for n in self.nodes:
                self.buffers[n].trim(self.next_start - 0.05)
            if r is not None:
                out.append(r)
        return out

    def _on_phase_at_or_after(self, t: float) -> float:
        return self.phase + math.ceil((t - self.phase) / self.stride_s - 1e-9) * self.stride_s

    def rephase_to_press(self, t_press: float, eps: float) -> dict:
        """THE PRESS-ALIGNED LATTICE, live. Called at the operator's start press.

        Offline, every pass's windows sit on a lattice with one window starting `eps` after the
        press, so the first walk window starts half a window before it and the lock's last window
        ends exactly at press + 2.0 s (`pipeline/constrained/y4_pressalign.py`,
        `reports/FINDING_lock_phase_2026-09-23.md`). Live, that first window has not been emitted
        at the press (it ends a second later) and its radio is still buffered, so the lattice can
        be moved onto the press phase without inventing or re-reading anything. Windows continue on
        the new phase from the earliest aligned start not yet emitted.
        """
        target = float(t_press) + float(eps) - self.window_s / 2.0
        self.phase = target - math.floor(target / self.stride_s) * self.stride_s
        late = self.next_start is not None and target < self.next_start - 1e-9
        if self.next_start is None or late:
            self.next_start = self._on_phase_at_or_after(self.next_start or target)
        else:
            m = math.floor((target - self.next_start) / self.stride_s + 1e-9)
            self.next_start = target - m * self.stride_s
        rec = {"t_press": float(t_press), "first_walk_window_start": target,
               "next_start": self.next_start, "phase": self.phase,
               "FIRST_WINDOW_ALREADY_EMITTED": bool(late)}
        self.rephases.append(rec)
        return rec

    # -- one window -----------------------------------------------------
    def _emit_window(self, t0: float, t1: float) -> Optional[Result]:
        started = time.monotonic()
        n_samp = int(round(self.window_s * self.fs))
        links, gaps = [], []
        for n in self.nodes:
            amp, ts = self.buffers[n].slice(t0 - 0.05, t1 + 0.05)
            if len(amp) < 10:
                return None
            c = clean_arrays(amp, ts, self.fs, baseline=self.baseline[n], grid_origin=0.0)
            i0 = int(round((t0 - c.grid[0]) * self.fs))
            if i0 < 0 or i0 + n_samp > len(c.amplitude):
                return None
            links.append(c.amplitude[i0:i0 + n_samp])
            gaps.append(float(c.packet_gap_s[i0:i0 + n_samp].max()))
        window = np.stack(links)

        g: GateLabel = label_window(window, self.fs, presence_theta=self.presence_theta, motion_theta=self.motion_theta)
        # The gate labels; it does not route. Both branches run whatever it said.
        who, conf = self.predictor.identify(window)
        cell, xy = self.predictor.locate(window)

        max_gap = max(gaps)
        latency = time.monotonic() - started
        gap_since = None if self._last_emit_t is None else t0 - self._last_emit_t
        self._last_emit_t = t0
        r = Result(t_start=t0, t_end=t1, gate=g.label, band_energy=g.band_energy, identity=who, identity_confidence=conf,
                   cell=cell, xy=xy, max_packet_gap=max_gap, gap_flag=max_gap > MAX_VERIFIED_GAP_S,
                   latency_s=latency, gap_since_previous_s=gap_since, n_links=len(self.nodes))
        self.results.append(r)
        self.n_windows += 1
        self.n_gap_flagged += int(r.gap_flag)
        if self.emit is not None:
            self.emit(r)
        return r

    # -- contract -------------------------------------------------------
    def timing_report(self) -> dict:
        """Whether the run met the filed timing contract, from the output itself."""
        if not self.results:
            return {"windows": 0, "meets_contract": None}
        lat = np.array([r.latency_s for r in self.results])
        gaps = np.array([r.gap_since_previous_s for r in self.results if r.gap_since_previous_s is not None])
        return {
            "windows": len(self.results),
            "latency_s": {"median": float(np.median(lat)), "p90": float(np.percentile(lat, 90)), "max": float(lat.max()), "limit": MAX_LATENCY_S},
            "output_gap_s": {"median": float(np.median(gaps)) if len(gaps) else None, "max": float(gaps.max()) if len(gaps) else None, "limit": MAX_OUTPUT_GAP_S},
            "update_interval_s": {"nominal": self.stride_s, "window_s": self.window_s},
            "gap_flagged_windows": self.n_gap_flagged,
            "skipped_windows_no_coverage": self.n_skipped_windows,
            "meets_contract": bool(lat.max() <= MAX_LATENCY_S and (not len(gaps) or gaps.max() <= MAX_OUTPUT_GAP_S)),
            "gate_counts": {k: sum(1 for r in self.results if r.gate == k) for k in ("empty", "standing", "walking")},
        }
