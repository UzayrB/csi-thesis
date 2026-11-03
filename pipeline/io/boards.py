# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The boards.

from __future__ import annotations

import argparse
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

from pipeline.io.serial_capture import FRAME_DTYPE, discover_ports, reset_board, run_capture

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BOARDS = os.path.join(REPO_ROOT, "runs", "public_model", "boards.json")
RECORD_ROOT = os.path.join(REPO_ROOT, "runs", "live", "hw_2026-10-15")
INJECT_ENV = "RIG_TEST_INJECT"



# The tracking receivers' MACs from boards.json.
def board_macs() -> dict:
    if not os.path.exists(BOARDS):
        raise SystemExit(f"REFUSED: {BOARDS} is missing: write your receivers' MACs there ({{\"RX1\": ..., \"RX2\": ..., "
                         "\"RX3\": ...}}; `python -m pipeline.io.boards` prints them)")
    with open(BOARDS, encoding="utf-8") as f:
        m = {k: str(v).lower() for k, v in json.load(f).items()}
    if set(m) != {"RX1", "RX2", "RX3"}:
        raise SystemExit(f"REFUSED: {BOARDS} must name RX1, RX2 and RX3 exactly")
    return m


# {port: (mac or None, kind)}, from this file's own table (python -m pipeline.io.boards, read only), run as...
def find_boards() -> dict:
    out = subprocess.run([sys.executable, "-m", "pipeline.io.boards"], cwd=REPO_ROOT,
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


# {"RX1": port, "RX2": port, "RX3": port}: the receivers in boards.json, found on the ports by their MACs.
def receiver_ports() -> dict:
    nodes = mapping_by_mac(find_boards(), board_macs())
    return {k: v for k, v in nodes.items() if k in ("RX1", "RX2", "RX3")}


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



# Capture from the named ports with the consumer in process, keys read on the same clock.
def run(consumer, nodes: dict, duration=None, mode: str = "tracking", stem: str = None, record: bool = True,
        run_config: dict = None) -> int:
    stem = stem or time.strftime("rig_%Y%m%d_%H%M%S")
    rec = os.path.join(RECORD_ROOT, time.strftime(f"rig_{mode}_%Y%m%d_%H%M%S")) if record else None
    consumer.record_dir = rec
    if rec:
        os.makedirs(rec, exist_ok=True)
    tee, states, stop_keys = KeyTee(consumer.keys), {}, threading.Event()
    consumer.key_input = tee
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


# One keypress, stamped on the same clocks as the CSI records.
@dataclass(frozen=True)
class KeyEvent:

    key: str
    t_mono: float
    t_host: float


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


SILENT_S = 1.0
ALL_SILENT_S = 5.0


# The receivers that are silent, from each one's latest packet (t_mono) and the wall clock now.
def silent_receivers(last: dict, now: float) -> set:
    if not last:
        return set()
    ref = max(max(last.values()), now - ALL_SILENT_S)
    return {n for n, t in last.items() if ref - t > SILENT_S}


# One record as a one-row capture frame (the fields the identification extractor reads).
def frame_of(rec):
    fr = np.zeros(1, FRAME_DTYPE)
    for f in ("t_host", "t_mono", "local_timestamp", "rssi", "channel"):
        if f in FRAME_DTYPE.names and hasattr(rec, f):
            fr[f] = getattr(rec, f)
    fr["data"] = np.asarray(rec.data, np.int8)
    return fr



# The board rigs' start-up status in the Terminal: numbered steps with their time.
class RigSteps:

    # Sets up the object.
    def __init__(self, n: int):
        self.n, self.i, self.t0, self.t = n, 0, time.time(), None

    # Function step.
    def step(self, what: str) -> None:
        self.done()
        self.i += 1
        self.t = time.time()
        print(f"[{self.i}/{self.n}] {what} ...", flush=True)

    # Function done.
    def done(self, note: str = "") -> None:
        if self.t is not None:
            print(f"      done in {time.time() - self.t:.0f} s{(': ' + note) if note else ''}", flush=True)
            self.t = None


# The board rigs' READY banner in the Terminal: where the keys go, what to press.
def rig_banner(lines: list) -> None:
    w = max(len(x) for x in lines) + 4
    print("\n" + "=" * w, flush=True)
    for x in lines:
        print(f"  {x}", flush=True)
    print("=" * w + "\n", flush=True)



SEND_BANNER: str = "CSI SEND"


RECV_BANNER: str = "CSI RECV"
CSI_ROW: str = "CSI_DATA,"
PROJECT_RE = re.compile(r"Project name:\s*(csi_recv|csi_send)")
STA_MAC_RE = re.compile(r"mode\s*:\s*sta\s*\(([0-9a-fA-F:]{17})\)")
MACS: dict[str, Optional[str]] = {}
CANDIDATE_BAUDS: tuple[int, ...] = (921600, 115200)


# Decide which firmware produced some console text.
def classify(text: str) -> Optional[str]:
    m = PROJECT_RE.search(text)
    if m:
        return "receiver" if m.group(1) == "csi_recv" else "transmitter"
    if SEND_BANNER in text:
        return "transmitter"
    if RECV_BANNER in text or CSI_ROW in text:
        return "receiver"
    return None


# Extract the board's own station MAC from boot output.
def find_sta_mac(text: str) -> Optional[str]:
    m = STA_MAC_RE.search(text)
    return m.group(1).lower() if m else None


# Reset the board and listen at one baud rate.
def identify_at_baud(port: str, baud: int, timeout_s: float = 4.0) -> tuple[Optional[str], str]:
    try:
        import serial
    except ImportError as exc:
        print(f"pyserial not installed ({exc}); pip install pyserial")
        return None, ""
    try:
        ser = serial.Serial(port, baud, timeout=0.2)
    except Exception as exc:
        return None, f"<cannot open: {exc}>"

    buf = b""
    verdict: Optional[str] = None
    try:
        reset_board(ser)
        end = time.monotonic() + timeout_s
        while time.monotonic() < end:
            buf += ser.read(4096)
            text = buf.decode("utf-8", errors="replace")
            verdict = classify(text)
            if verdict and find_sta_mac(text):
                break
    finally:
        try:
            ser.close()
        except Exception:
            pass
    return verdict, buf.decode("utf-8", errors="replace")


# Identify the firmware on a port, trying each candidate baud.
def probe_port(port: str, baud: Optional[int] = None, timeout_s: float = 4.0) -> Optional[str]:
    bauds = (baud,) if baud else CANDIDATE_BAUDS
    last_text = ""
    for b in bauds:
        print(f"  trying {b} baud ...", end=" ", flush=True)
        verdict, text = identify_at_baud(port, b, timeout_s)
        last_text = text or last_text
        if verdict:
            mac = find_sta_mac(text)
            print(f"identified as {verdict}" + (f", station MAC {mac}" if mac else ""))
            MACS[port] = mac
            return verdict
        print(f"nothing ({len(text)} bytes seen)")
    preview = "".join(ch if ch.isprintable() or ch in "\n\r\t" else "." for ch in last_text[-300:])
    if preview.strip():
        print("\n  last output seen (tail):")
        for line in preview.splitlines()[-6:]:
            print(f"    | {line[:100]}")
    return None


# Python -m pipeline.io.boards: a table of the boards on the ports (each port reset and listened to).
def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m pipeline.io.boards",
        description="Say whether the board on a port runs csi_send or csi_recv. Read-only.",
    )
    p.add_argument("port", nargs="?", default=None, help="device path (default: check every attached port)")
    p.add_argument("--baud", type=int, default=None, help="a single baud to try (default: try 921600 then 115200)")
    p.add_argument("--timeout", type=float, default=4.0, help="seconds to listen at each baud (default: 4)")
    args = p.parse_args(argv)

    ports = [args.port] if args.port else discover_ports()
    if not ports:
        print("No /dev/cu.usbserial-* devices found.")
        return 2

    results: dict[str, Optional[str]] = {}
    for port in ports:
        print(f"\n{port}")
        results[port] = probe_port(port, args.baud, args.timeout)

    print("\n" + "=" * 74)
    print(f"  {'port':<28} {'station MAC':<18} firmware")
    print("  " + "-" * 70)
    for port, verdict in results.items():
        mac = MACS.get(port) or "-"
        if verdict == "transmitter":
            print(f"  {port:<28} {mac:<18} TRANSMITTER (csi_send)")
        elif verdict == "receiver":
            print(f"  {port:<28} {mac:<18} RECEIVER (csi_recv)")
        else:
            print(f"  {port:<28} {'-':<18} INCONCLUSIVE")
    print("=" * 74)

    if any(v is None for v in results.values()):
        print("\nInconclusive ports gave no recognisable banner at any baud tried.")
        print("A quiet port is NOT proof it is the transmitter: a receiver whose")
        print("transmitter is switched off is also quiet. If a port shows garbage")
        print("above, the console is at a baud not tried; pass --baud.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
