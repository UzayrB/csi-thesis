# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Talks to the boards.

from __future__ import annotations

import json
import os
import queue
import threading
import time

import numpy as np

REFRESH_S = 0.1
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
RECORD_ROOT = os.path.join(REPO_ROOT, "runs", "live", "hw_2026-10-15")
INJECT_ENV = "RIG_TEST_INJECT"


# TEST ONLY: SPACE at first_s, then every every_s, into the consumer's key queue (through the tee, so the...
def key_injector(tee, stop, spec: str) -> dict:
    first, every = (float(x) for x in spec.split(",")[:2])
    t0 = time.monotonic()

    # Function go.
    def go():
        k = 0
        while not stop.is_set():
            due = t0 + first + k * every
            while not stop.is_set() and time.monotonic() < due:
                time.sleep(min(0.002, max(0.0, due - time.monotonic())))
            if stop.is_set():
                return
            tee.put_nowait(KeyEvent(" ", time.monotonic(), time.time()))
            k += 1
    threading.Thread(target=go, name="test-key-injector", daemon=True).start()
    print(f"TEST KEY INJECTOR ON ({INJECT_ENV}={spec}): SPACE at {first:g} s, then every {every:g} s", flush=True)
    return {"spec": spec, "first_s": first, "every_s": every, "t0_mono": t0}


# The consumer's key queue, keeping every key as the app received it (the recording's key sidecar).
class KeyTee:

    # Sets up the object.
    def __init__(self, q):
        self.q, self.keys = q, []

    # Function put nowait.
    def put_nowait(self, ev) -> None:
        self.keys.append({"key": ev.key, "t_mono": float(ev.t_mono), "t_host": float(ev.t_host)})
        self.q.put_nowait(ev)

    # Function put.
    def put(self, ev, block: bool = True, timeout=None) -> None:
        self.put_nowait(ev)


# Windows.load_node's amplitude, for one record: sqrt(I^2 + Q^2) over 128 subcarriers.
def amplitude(data) -> np.ndarray:
    d = np.asarray(data, np.int8).astype(np.float32).reshape(128, 2)
    return np.sqrt((d ** 2).sum(-1))


# One record as a one-row capture frame (the fields the identification extractor reads).
def frame_of(rec):
    from pipeline.io.RunLive.serial_capture import FRAME_DTYPE
    fr = np.zeros(1, FRAME_DTYPE)
    for f in ("t_host", "t_mono", "local_timestamp", "rssi", "channel"):
        if f in FRAME_DTYPE.names and hasattr(rec, f):
            fr[f] = getattr(rec, f)
    fr["data"] = np.asarray(rec.data, np.int8)
    return fr


SILENT_S = 1.0
ALL_SILENT_S = 5.0


# The receivers that are silent, from each one's latest packet (t_mono) and the wall clock now.
def silent_receivers(last: dict, now: float) -> set:
    if not last:
        return set()
    ref = max(max(last.values()), now - ALL_SILENT_S)
    return {n for n, t in last.items() if ref - t > SILENT_S}


# Class Tracking Consumer.
class TrackingConsumer:
    owns_terminal = True

    # Sets up the object.
    def __init__(self, session, screen=None, nodes=("RX1", "RX2", "RX3")):
        self.s, self.screen, self.nodes = session, screen, tuple(nodes)
        self.anchor = {n: CausalAnchor() for n in self.nodes}
        self.held = {n: {} for n in self.nodes}
        self.keys = queue.Queue()
        self.stop = threading.Event()
        self.pid, self.open = 0, False
        self.last_draw = 0.0
        self.refused = None
        self.last_pkt = {}
        self.silent, self.outages = set(), []

    # A start press, refused cleanly.
    def _press(self, pid: int, t: float) -> None:
        if getattr(getattr(self.s, "stream", None), "first_base", 0) is None:
            self.refused = ("REFUSED: no packets had reached the app before the first press; stand still for at least "
                            "10 s before the first walk")
            self.stop.set()
            raise SystemExit(self.refused)
        try:
            self.s.press(pid, t)
        except SystemExit as e:
            self.refused = str(e)
            self.stop.set()
            raise

    # The silent-receiver guard for tracking: tracking cuts a window only when every receiver has data, so a...
    def _announce(self, now: float) -> None:
        silent = silent_receivers(self.last_pkt, now)
        for n in sorted(silent - self.silent):
            print(f"TRACKING: {n} is silent (no frames for over {SILENT_S:g} s); a walk while it is silent cannot be "
                  f"tracked reliably. Check its power and cable.", flush=True)
            self.outages.append({"node": n, "from": float(self.last_pkt[n]), "to": None})
        for n in sorted(self.silent - silent):
            print(f"TRACKING: {n} is sending again.", flush=True)
            for o in reversed(self.outages):
                if o["node"] == n and o["to"] is None:
                    o["to"] = float(self.last_pkt[n])
                    break
        self.silent = silent

    # Function handle.
    def handle(self, rec) -> None:
        n = rec.node_id
        if n not in self.anchor or self.refused is not None:
            return
        self.last_pkt[n] = float(rec.t_mono)
        self.s.rssi(n, rec.t_host, rec.rssi)
        a = self.anchor[n]
        self.held[n][len(a.local)] = (amplitude(rec.data), rec.t_host, rec.t_mono)
        for i, t in a.push(rec.local_timestamp, rec.t_mono):
            amp, t_host, t_mono = self.held[n].pop(i)
            self.s.csi(n, t, amp, t_host, t_mono)

    # Function tick.
    def tick(self, now: float) -> None:
        self._announce(now)
        while not self.keys.empty():
            ev = self.keys.get_nowait()
            if ev.key == "q":
                self.stop.set()
            elif ev.key == " ":
                if getattr(self.s, "mode", None) == "semi":
                    self.pid += 1
                    self._press(self.pid, ev.t_mono)
                    continue
                if not self.open:
                    self.pid += 1
                    self._press(self.pid, ev.t_mono)
                else:
                    self.s.end_press(self.pid, ev.t_mono)
                self.open = not self.open
        if self.screen is not None and now - self.last_draw >= REFRESH_S:
            self.last_draw = now
            self.screen.tracking(**self.s.screen_state(now))

    # Function summary.
    def summary(self) -> dict:
        return {"passes": self.pid, "decisions": self.s.decisions, "timing": {k: len(v) for k, v in self.s.timing.items()}}


# Capture from the named ports with the consumer in process, keys read on the same clock.
def run(consumer, nodes: dict, duration=None, mode: str = "tracking", stem: str = None, record: bool = True,
        run_config: dict = None) -> int:
    from pipeline.io.RunLive.serial_capture import run_capture
    stem = stem or time.strftime("rig_%Y%m%d_%H%M%S")
    rec = os.path.join(RECORD_ROOT, time.strftime(f"rig_{mode}_%Y%m%d_%H%M%S")) if record else None
    consumer.record_dir = rec
    if rec:
        os.makedirs(rec, exist_ok=True)
    tee, states, stop_keys = KeyTee(consumer.keys), {}, threading.Event()
    meta = {"mode": mode, "stem": stem, "nodes": dict(nodes), "started": time.strftime("%Y-%m-%d %H:%M:%S"),
            "run_config": run_config or {}}
    rc = None
    try:
        with KeyReader(tee, stop_keys):
            if os.environ.get(INJECT_ENV):
                meta["test_injector"] = key_injector(tee, stop_keys, os.environ[INJECT_ENV])
            rc = run_capture(nodes, duration=duration, extra_consumers=[consumer],
                             stop_when=consumer.stop.is_set, quiet_monitor=True, states_out=states,
                             out_dir=rec, timestamped_subdir=False, writer_prefix=f"{stem}_" if rec else "",
                             run_config={"rig": mode, "stem": stem, **(run_config or {})})
            return rc
    finally:
        stop_keys.set()
        time.sleep(0.2)
        if rec:
            meta.update({"ended": time.strftime("%Y-%m-%d %H:%M:%S"), "exit": rc, "keys": tee.keys,
                         "station_macs": {n: getattr(st_, "sta_mac", None) for n, st_ in states.items()},
                         "receivers": {n: {"counters": {k: v for k, v in getattr(getattr(st_, "counters", None), "__dict__",
                                                                                     {}).items() if isinstance(v, int)},
                                           "queue_dropped": int(getattr(st_, "queue_dropped", 0)),
                                           "read_errors": int(getattr(st_, "read_errors", 0)),
                                           "bytes_read": int(getattr(st_, "bytes_read", 0))}
                                       for n, st_ in states.items()}})
            with open(os.path.join(rec, f"{stem}.keys.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=1, default=str)


from typing import Optional
from dataclasses import dataclass
import sys

# One keypress, stamped on the same clocks as the CSI records.
@dataclass(frozen=True)
class KeyEvent:

    key: str
    t_mono: float
    t_host: float


# Read single keypresses without blocking anything else.
class KeyReader(threading.Thread):

    # Create the reader.
    def __init__(self, out_queue: "queue.Queue[KeyEvent]", stop_event: threading.Event) -> None:
        super().__init__(name="key-reader", daemon=True)
        self.queue = out_queue
        self.stop_event = stop_event
        self.enabled = sys.stdin.isatty()
        self._fd: Optional[int] = None
        self._saved = None

    # Put the terminal into cbreak mode and start reading.
    def __enter__(self) -> "KeyReader":
        if self.enabled:
            import termios
            import tty

            self._fd = sys.stdin.fileno()
            self._saved = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)
            self.start()
        return self

    # Stop reading and always restore the terminal.
    def __exit__(self, *exc: object) -> None:
        self.stop_event.set()
        self.restore()

    # Restore the terminal mode, tolerating an already-restored state.
    def restore(self) -> None:
        if self._fd is not None and self._saved is not None:
            try:
                import termios

                termios.tcsetattr(self._fd, termios.TCSADRAIN, self._saved)
            except Exception:
                pass
            self._saved = None

    # Push keypresses onto the queue until asked to stop.
    def run(self) -> None:
        import select

        while not self.stop_event.is_set():
            try:
                ready, _, _ = select.select([sys.stdin], [], [], 0.05)
                if not ready:
                    continue
                ch = sys.stdin.read(1)
                if not ch:
                    continue
                self.queue.put_nowait(KeyEvent(ch.lower(), time.monotonic(), time.time()))
            except Exception:
                time.sleep(0.05)


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
        from pipeline.io.RunLive.signal_cleaning import DEVICE_CLOCK_MODULUS_US, WRAP_MARGIN_US, fit_timebase
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


import subprocess

# {port: (mac or None, kind)} from pipeline.io.RunLive.board_identify's table (the tool is read only).
def identify() -> dict:
    out = subprocess.run([sys.executable, "-m", "pipeline.io.RunLive.board_identify"], cwd=REPO_ROOT,
                         capture_output=True, text=True, timeout=600).stdout
    found = {}
    for ln in out.splitlines():
        p = ln.split()
        if p and p[0].startswith("/dev/"):
            if "RECEIVER" in ln:
                found[p[0]] = (p[1].lower(), "receiver")
            elif "TRANSMITTER" in ln:
                found[p[0]] = (p[1].lower() if p[1] != "-" else None, "transmitter")
            else:
                found[p[0]] = (None, "inconclusive")
    return found


# {name: port}.
def mapping_by_mac(found: dict, tracking_macs: dict) -> dict:
    by_mac = {mac: port for port, (mac, kind) in found.items() if kind == "receiver" and mac}
    missing = [n for n, m in tracking_macs.items() if m not in by_mac]
    if missing:
        raise SystemExit(f"REFUSING: tracking board(s) {missing} not found by MAC "
                         f"{[tracking_macs[n] for n in missing]}; seen {sorted(by_mac)}")
    out = {n: by_mac[m] for n, m in tracking_macs.items()}
    extra = sorted(p for m, p in by_mac.items() if m not in set(tracking_macs.values()))
    if len(extra) > 1:
        raise SystemExit(f"REFUSING: more than one non-tracking receiver {extra}; one ID link expected")
    if extra:
        out["RX4"] = extra[0]
    return out
