# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The rig: capture_logger.run_capture's extra consumer, the key reader, and the screen.

from __future__ import annotations

import json
import os
import queue
import threading
import time

import numpy as np

REFRESH_S = 0.1
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RECORD_ROOT = os.path.join(REPO_ROOT, "runs", "live", "hw_2026-10-15")
INJECT_ENV = "RIG_TEST_INJECT"


# TEST ONLY: SPACE at first_s, then every every_s, into the consumer's key queue (through the tee, so the...
def key_injector(tee, stop, spec: str) -> dict:
    from pipeline.io.ground_truth import KeyEvent
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
    from pipeline.io.capture_logger import FRAME_DTYPE
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
        from pipeline.live.anchor import CausalAnchor
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


# Class Identify Consumer.
class IdentifyConsumer:
    owns_terminal = True

    # Sets up the object.
    def __init__(self, recording, identifier, screen=None, names=None, nodes=("RX1", "RX2", "RX3")):
        self.r, self.ident, self.screen, self.names = recording, identifier, screen, names or {}
        self.nodes = tuple(nodes)
        self.buf = {n: [] for n in self.nodes}
        self.keys = queue.Queue()
        self.stop = threading.Event()
        self.open = False
        self.results = []
        self.last_draw = 0.0

    # Function handle.
    def handle(self, rec) -> None:
        if rec.node_id in self.buf:
            self.buf[rec.node_id].append(frame_of(rec))

    # Function flush.
    def _flush(self) -> list:
        out = []
        for n in self.nodes:
            if self.buf[n]:
                out += self.r.push(n, np.concatenate(self.buf[n]))
                self.buf[n] = []
        return out

    # Function tick.
    def tick(self, now: float) -> None:
        from pipeline.live.identify import combine
        done = self._flush()
        while not self.keys.empty():
            ev = self.keys.get_nowait()
            if ev.key == "q":
                self.stop.set()
            elif ev.key == " ":
                if not self.open:
                    self.r.press(ev.t_mono)
                else:
                    done += self.r.end_press(ev.t_mono)
                self.open = not self.open
        if done:
            self.results += self.ident.predict(done)
        if self.screen is not None and now - self.last_draw >= REFRESH_S:
            self.last_draw = now
            waiting = len(self.r.pending)
            self.screen.identification(
                result=self.results[-1] if self.results else None,
                combined=combine([q["proba"] for q in self.results]) if len(self.results) > 1 else None,
                n_passes=len(self.results), names=self.names,
                status=(f"{waiting} pass(es) waiting for the clock map to settle (about 21 s after the end press)"
                        if waiting else ""))


# Capture from the named ports with the consumer in process, keys read on the same clock.
def run(consumer, nodes: dict, duration=None, mode: str = "tracking", stem: str = None, record: bool = True,
        run_config: dict = None) -> int:
    from pipeline.io.capture_logger import run_capture
    from pipeline.io.ground_truth import KeyReader
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
