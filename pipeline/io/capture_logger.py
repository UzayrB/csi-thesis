# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Streaming multi-node CSI capture: serial readers, rate monitor, writer.

from __future__ import annotations

import argparse
import glob
import json
import os
import queue
import signal
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol, Sequence

import numpy as np

from pipeline.io.parse import (
    CSI_LEN,
    CsiRecord,
    ParseCounters,
    extract_sta_mac,
    parse_line,
)

DEFAULT_BAUD: int = 921600

PORT_GLOB: str = "/dev/cu.usbserial-*"

DEFAULT_EXPECT_TX_HZ: float = 150.0

GATE_SENT_TOLERANCE: float = 0.97

GATE_MAX_DROP_PCT: float = 5.0

GATE_TREND_SLOPE_PCT_PER_MIN: float = 1.0

GATE_TREND_STEP_PCT: float = 2.0

GATE_TREND_MIN_SAMPLES: int = 30

BOOT_SETTLE_S: float = 2.0

MAX_LINE_BYTES: int = 65536

UART_SATURATION_PCT: float = 85.0

QUEUE_MAXSIZE: int = 60000

_WRAP_MODULI: tuple[int, ...] = (1 << 16, 1 << 32, 1 << 64)

FRAME_DTYPE = np.dtype(
    [
        ("t_host", "<f8"),
        ("t_mono", "<f8"),
        ("pkt_id", "<i8"),
        ("local_timestamp", "<u8"),
        ("rssi", "<i2"),
        ("noise_floor", "<i2"),
        ("ampdu_cnt", "<u4"),
        ("sig_len", "<u4"),
        ("rate", "u1"),
        ("sig_mode", "u1"),
        ("mcs", "u1"),
        ("bandwidth", "u1"),
        ("smoothing", "u1"),
        ("not_sounding", "u1"),
        ("aggregation", "u1"),
        ("stbc", "u1"),
        ("fec_coding", "u1"),
        ("sgi", "u1"),
        ("channel", "u1"),
        ("secondary_channel", "u1"),
        ("ant", "u1"),
        ("rx_format", "u1"),
        ("first_word", "u1"),
        ("gain", "<f4"),
        ("data", "i1", (CSI_LEN,)),
    ]
)

FILE_MAGIC: bytes = b"CSIBIN01"




# Find attached USB-serial receivers.
def discover_ports(pattern: str = PORT_GLOB) -> list[str]:
    return sorted(glob.glob(pattern))


# Parse an explicit --nodes mapping.
def parse_nodes_arg(spec: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    seen_ports: set[str] = set()
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            raise ValueError(f"--nodes entry {chunk!r} is not NAME=PORT")
        name, port = chunk.split("=", 1)
        name, port = name.strip(), port.strip()
        if not name or not port:
            raise ValueError(f"--nodes entry {chunk!r} has an empty name or port")
        if name in mapping:
            raise ValueError(f"--nodes repeats node id {name!r}")
        if port in seen_ports:
            raise ValueError(f"--nodes repeats port {port!r}")
        mapping[name] = port
        seen_ports.add(port)
    if not mapping:
        raise ValueError("--nodes was empty")
    return mapping


# Decide which node id maps to which serial port.
def resolve_nodes(nodes_arg: Optional[str], pattern: str = PORT_GLOB) -> dict[str, str]:
    if nodes_arg:
        mapping = parse_nodes_arg(nodes_arg)
        print(f"Using {len(mapping)} explicitly named node(s).")
        return mapping
    ports = discover_ports(pattern)
    print(f"Found {len(ports)} serial port(s) matching {pattern}")
    for p in ports:
        print(f"  {p}")
    return {f"RX{i}": p for i, p in enumerate(ports, start=1)}




# Everything the run knows about one receiver.
@dataclass
class NodeState:

    node_id: str
    port: str
    counters: ParseCounters = field(default_factory=ParseCounters)
    sta_mac: Optional[str] = None
    bytes_read: int = 0
    oversize_discards: int = 0
    queue_dropped: int = 0
    read_errors: int = 0
    opened: bool = False
    error: Optional[str] = None


# Record the PHY configuration the packets actually arrived with.
class ConfigWatch:

    FIELDS: tuple[str, ...] = ("channel", "secondary_channel", "bandwidth", "sig_mode", "rate", "mcs")

    # Create an empty watch.
    def __init__(self) -> None:
        self.seen: dict[str, dict[str, dict[int, int]]] = {}

    # Count the configuration this packet reported.
    def handle(self, record: CsiRecord) -> None:
        node = self.seen.setdefault(record.node_id, {f: {} for f in self.FIELDS})
        for f in self.FIELDS:
            v = int(getattr(record, f))
            node[f][v] = node[f].get(v, 0) + 1

    # Nothing periodic to do.
    def tick(self, now: float) -> None:
        return None

    # Nothing to release.
    def close(self) -> None:
        return None

    # Return the most common value of each field for one node.
    def dominant(self, node_id: str) -> dict[str, int]:
        node = self.seen.get(node_id, {})
        return {f: max(vals, key=vals.get) for f, vals in node.items() if vals}

    # List configuration inconsistencies worth stopping for.
    def problems(self) -> list[str]:
        out: list[str] = []
        for node_id, fields in sorted(self.seen.items()):
            for f, vals in fields.items():
                if len(vals) > 1:
                    total = sum(vals.values())
                    minor = {v: c for v, c in vals.items() if v != max(vals, key=vals.get)}
                    out.append(
                        f"{node_id}: {f} changed mid-session, {minor} against "
                        f"{max(vals, key=vals.get)} ({total} packets)"
                    )
        nodes = sorted(self.seen)
        if len(nodes) > 1:
            ref = self.dominant(nodes[0])
            for n in nodes[1:]:
                d = self.dominant(n)
                for f in self.FIELDS:
                    if f in ref and f in d and ref[f] != d[f]:
                        out.append(f"{f} differs: {nodes[0]}={ref[f]} but {n}={d[f]}")
        return out


# Check that nothing went missing between the wire and the file.
def reconcile(
    states: dict[str, NodeState],
    writer: Optional["FileWriter"] = None,
    config_watch: Optional[ConfigWatch] = None,
) -> tuple[bool, list[str]]:
    lines: list[str] = []
    ok = True

    lines.append("=" * 124)
    lines.append("RECONCILIATION  (every packet accounted for, or explained)")
    lines.append("=" * 124)
    head = (
        f"{'node':<6} {'lines':>8} {'parsed':>8} {'non-CSI':>8} {'torn':>6} {'badlen':>7} "
        f"{'baddata':>8} {'queue':>6} {'oversz':>7} {'readerr':>8} {'written':>8} {'wrerr':>6} {'verdict':>9}"
    )
    lines.append(head)
    lines.append("-" * len(head))

    for node_id, st in sorted(states.items()):
        c = st.counters
        written = writer.written.get(node_id, 0) if writer else None
        wrerr = writer.write_errors.get(node_id, 0) if writer else 0

        accounted = c.ok + c.non_csi + c.torn + c.bad_field_count + c.bad_metadata + c.bad_len + c.bad_data
        node_ok = accounted == c.lines_seen
        if writer is not None:
            node_ok = node_ok and (written + wrerr + st.queue_dropped == c.ok)
        ok = ok and node_ok

        lines.append(
            f"{node_id:<6} {c.lines_seen:>8} {c.ok:>8} {c.non_csi:>8} {c.torn:>6} {c.bad_len:>7} "
            f"{c.bad_data:>8} {st.queue_dropped:>6} {st.oversize_discards:>7} {st.read_errors:>8} "
            f"{(written if written is not None else '-'):>8} {wrerr:>6} "
            f"{'ok' if node_ok else 'MISMATCH':>9}"
        )

    lines.append("-" * len(head))

    for node_id, st in sorted(states.items()):
        c = st.counters
        accounted = c.ok + c.non_csi + c.torn + c.bad_field_count + c.bad_metadata + c.bad_len + c.bad_data
        if accounted != c.lines_seen:
            lines.append(f"  {node_id}: {c.lines_seen - accounted} lines unaccounted for in the parse counters")
        if writer is not None:
            written = writer.written.get(node_id, 0)
            wrerr = writer.write_errors.get(node_id, 0)
            missing = c.ok - written - wrerr - st.queue_dropped
            if missing:
                lines.append(f"  {node_id}: {missing} parsed packets neither written nor counted as dropped")
        if st.counters.bad_len:
            lines.append(f"  {node_id}: {c.bad_len} rows declared a payload length other than {CSI_LEN}")
        if writer is not None and writer.write_errors.get(node_id, 0):
            lines.append(
                f"  {node_id}: {writer.write_errors[node_id]} frames dropped at the writer because a field "
                f"overflowed its on-disk width"
            )
        if st.queue_dropped:
            lines.append(f"  {node_id}: {st.queue_dropped} frames dropped at the queue; a consumer was too slow")
        if st.oversize_discards:
            lines.append(f"  {node_id}: {st.oversize_discards} oversize line-buffer discards")

    if config_watch is not None:
        problems = config_watch.problems()
        nodes = sorted(config_watch.seen)
        if nodes:
            d = config_watch.dominant(nodes[0])
            lines.append(
                "  PHY: channel {channel} sec {secondary_channel} bw {bandwidth} "
                "sig_mode {sig_mode} rate {rate} mcs {mcs}".format(**d)
            )
        for p in problems:
            ok = False
            lines.append(f"  CONFIG: {p}")

    lines.append(f"\n  {'ALL PACKETS ACCOUNTED FOR' if ok else 'RECONCILIATION FAILED - see above'}")
    lines.append("=" * 124)
    return ok, lines


# Reboot an attached ESP32 by pulsing the auto-reset lines.
def reset_board(ser: object) -> None:
    try:
        ser.dtr = False
        ser.rts = True
        time.sleep(0.1)
        ser.rts = False
        time.sleep(0.05)
        ser.reset_input_buffer()
    except Exception:
        pass


# Read one receiver's console, parse it, and enqueue tagged records.
class SerialReader(threading.Thread):

    # Create a reader for one port.
    def __init__(
        self,
        state: NodeState,
        out_queue: "queue.Queue[CsiRecord]",
        stop_event: threading.Event,
        baud: int = DEFAULT_BAUD,
        read_timeout: float = 0.05,
        reset: bool = False,
    ) -> None:
        super().__init__(name=f"reader-{state.node_id}", daemon=True)
        self.state = state
        self.queue = out_queue
        self.stop_event = stop_event
        self.baud = baud
        self.read_timeout = read_timeout
        self.reset = reset
        self._ser: object = None

    # Open the serial port.
    def open(self) -> bool:
        try:
            import serial
        except ImportError as exc:
            self.state.error = f"pyserial not installed ({exc}); pip install pyserial"
            return False
        try:
            self._ser = serial.Serial(self.state.port, self.baud, timeout=self.read_timeout)
        except Exception as exc:
            self.state.error = str(exc)
            return False
        if self.reset:
            reset_board(self._ser)
        self.state.opened = True
        return True

    # Stream lines until asked to stop.
    def run(self) -> None:
        if self._ser is None:
            return
        buf = bytearray()
        st = self.state
        while not self.stop_event.is_set():
            try:
                chunk = self._ser.read(4096)
            except Exception:
                st.read_errors += 1
                time.sleep(0.1)
                continue
            if not chunk:
                continue
            t_mono = time.monotonic()
            t_host = time.time()
            st.bytes_read += len(chunk)
            buf.extend(chunk)
            if len(buf) > MAX_LINE_BYTES:
                del buf[:-1024]
                st.oversize_discards += 1
            while True:
                nl = buf.find(b"\n")
                if nl < 0:
                    break
                raw = bytes(buf[:nl])
                del buf[: nl + 1]
                line = raw.decode("utf-8", errors="replace")
                rec = parse_line(line, st.node_id, st.counters, t_mono, t_host)
                if rec is None:
                    if st.sta_mac is None:
                        mac = extract_sta_mac(line)
                        if mac:
                            st.sta_mac = mac
                    continue
                try:
                    self.queue.put_nowait(rec)
                except queue.Full:
                    st.queue_dropped += 1

    # Close the serial port, ignoring errors on an already-dead board.
    def close(self) -> None:
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:
                pass




# Anything that can subscribe to the record stream.
class Consumer(Protocol):

    # Process one record.
    def handle(self, record: CsiRecord) -> None:
        pass

    # Periodic callback, roughly once per second, from the dispatcher.
    def tick(self, now: float) -> None:
        pass

    # Flush and release resources at end of run.
    def close(self) -> None:
        pass


# Compute how many packets the transmitter sent between two ids.
def wrap_delta(prev_id: int, cur_id: int) -> Optional[int]:
    if cur_id >= prev_id:
        return cur_id - prev_id
    for m in _WRAP_MODULI:
        d = cur_id - prev_id + m
        if 0 < d < m // 2:
            return d
    return None


# Rolling and cumulative rate figures for one node.
@dataclass
class NodeRateStats:

    recv_total: int = 0
    sent_total: int = 0
    recv_window: int = 0
    sent_window: int = 0
    rssi_sum: float = 0.0
    last_noise_floor: Optional[int] = None
    first_id: Optional[int] = None
    last_id: Optional[int] = None
    unexplained_steps: int = 0
    bytes_at_last_tick: int = 0
    drop_series: list[float] = field(default_factory=list)
    uart_series: list[float] = field(default_factory=list)


# Print one line per node per second and judge the run at the end.
class RateMonitor:

    # Create the monitor.
    def __init__(
        self,
        states: dict[str, NodeState],
        interval: float = 1.0,
        baud: int = DEFAULT_BAUD,
        expect_tx_hz: float = DEFAULT_EXPECT_TX_HZ,
        quiet: bool = False,
    ) -> None:
        self.states = states
        self.interval = interval
        self.baud = baud
        self.expect_tx_hz = expect_tx_hz
        self.quiet = quiet
        self.min_sent_hz = expect_tx_hz * GATE_SENT_TOLERANCE
        self.byte_capacity = baud / 10.0
        self.stats: dict[str, NodeRateStats] = {n: NodeRateStats() for n in states}
        self.t_start = time.monotonic()
        self._next_tick = self.t_start + interval
        self._last_tick = self.t_start

    # Discard everything counted so far and start the run clock again.
    def restart(self, now: float) -> None:
        for node_id, st in self.states.items():
            self.stats[node_id] = NodeRateStats(bytes_at_last_tick=st.bytes_read)
        self.t_start = now
        self._last_tick = now
        self._next_tick = now + self.interval

    # Fold one record into the current window's statistics.
    def handle(self, record: CsiRecord) -> None:
        s = self.stats.get(record.node_id)
        if s is None:
            s = self.stats.setdefault(record.node_id, NodeRateStats())
        s.recv_total += 1
        s.recv_window += 1
        s.rssi_sum += record.rssi
        s.last_noise_floor = record.noise_floor
        if s.first_id is None:
            s.first_id = record.pkt_id
        if s.last_id is not None:
            d = wrap_delta(s.last_id, record.pkt_id)
            if d is None:
                s.unexplained_steps += 1
            else:
                s.sent_window += d
                s.sent_total += d
        s.last_id = record.pkt_id

    # Emit the per-second lines if the interval has elapsed.
    def tick(self, now: float) -> None:
        if now < self._next_tick:
            return
        elapsed = now - self._last_tick
        if elapsed <= 0:
            return
        t_run = now - self.t_start
        for node_id, st in self.states.items():
            s = self.stats[node_id]
            recv_hz = s.recv_window / elapsed
            sent_hz = s.sent_window / elapsed
            drop_pct = 100.0 * (1.0 - (s.recv_window / s.sent_window)) if s.sent_window > 0 else float("nan")
            if s.sent_window > 0:
                s.drop_series.append(max(0.0, drop_pct))
            mean_rssi = (s.rssi_sum / s.recv_window) if s.recv_window else float("nan")
            nf = s.last_noise_floor
            d_bytes = st.bytes_read - s.bytes_at_last_tick
            s.bytes_at_last_tick = st.bytes_read
            uart_pct = 100.0 * (d_bytes / elapsed) / self.byte_capacity
            s.uart_series.append(uart_pct)
            if not self.quiet:
                print(
                    f"[{t_run:6.1f}s] {node_id:<6} "
                    f"recv {recv_hz:6.1f}/s  sent {sent_hz:6.1f}/s  "
                    f"drop {drop_pct:6.2f}%  "
                    f"malformed {st.counters.malformed:6d}  "
                    f"len!=256 {st.counters.bad_len:5d}  "
                    f"rssi {mean_rssi:7.1f}  nf {nf if nf is not None else '--':>4}  "
                    f"uart {uart_pct:5.1f}%",
                    flush=True,
                )
            s.recv_window = 0
            s.sent_window = 0
            s.rssi_sum = 0.0
        self._last_tick = now
        self._next_tick = now + self.interval

    # Least-squares slope of a per-second drop series.
    def trend_slope_pct_per_min(self, series: Sequence[float]) -> float:
        n = len(series)
        if n < 2:
            return 0.0
        x = np.arange(n, dtype=np.float64)
        y = np.asarray(series, dtype=np.float64)
        slope = float(np.polyfit(x, y, 1)[0])
        return slope * 60.0

    # Build the end-of-run figures for every node.
    def summarise(self) -> dict[str, dict]:
        duration = max(time.monotonic() - self.t_start, 1e-9)
        out: dict[str, dict] = {}
        for node_id, st in self.states.items():
            s = self.stats[node_id]
            sent_total = s.sent_total
            recv_total = s.recv_total
            sent_hz = sent_total / duration
            recv_hz = recv_total / duration
            drop_pct = 100.0 * (1.0 - recv_total / sent_total) if sent_total > 0 else float("nan")
            drop_pct = max(0.0, drop_pct) if sent_total > 0 else drop_pct

            slope = self.trend_slope_pct_per_min(s.drop_series)
            n_series = len(s.drop_series)
            if n_series >= GATE_TREND_MIN_SAMPLES:
                third = n_series // 3
                step = float(np.mean(s.drop_series[-third:]) - np.mean(s.drop_series[:third]))
                trend_ok = not (slope > GATE_TREND_SLOPE_PCT_PER_MIN and step > GATE_TREND_STEP_PCT)
                trend_applicable = True
            else:
                step = float("nan")
                trend_ok = True
                trend_applicable = False

            sent_ok = sent_hz >= self.min_sent_hz
            drop_ok = sent_total > 0 and drop_pct < GATE_MAX_DROP_PCT
            out[node_id] = {
                "port": st.port,
                "sta_mac": st.sta_mac,
                "duration_s": duration,
                "recv_total": recv_total,
                "sent_total": sent_total,
                "recv_hz": recv_hz,
                "sent_hz": sent_hz,
                "drop_pct": drop_pct,
                "drop_trend_pct_per_min": slope,
                "drop_trend_step_pct": step,
                "trend_applicable": trend_applicable,
                "uart_pct_mean": float(np.mean(s.uart_series)) if s.uart_series else float("nan"),
                "bytes_read": st.bytes_read,
                "oversize_discards": st.oversize_discards,
                "bytes_per_packet": (st.bytes_read / recv_total) if recv_total else float("nan"),
                "queue_dropped": st.queue_dropped,
                "read_errors": st.read_errors,
                "unexplained_id_steps": s.unexplained_steps,
                "counters": st.counters.as_dict(),
                "gate_sent": sent_ok,
                "gate_drop": drop_ok,
                "gate_trend": trend_ok,
                "pass": bool(sent_ok and drop_ok and trend_ok),
            }
        return out

    # Print the summary table and the PASS/FAIL verdict.
    def print_summary(self, summary: dict[str, dict]) -> bool:
        print()
        print("=" * 124)
        print("SUMMARY")
        print("=" * 124)
        head = (
            f"{'node':<6} {'port':<26} {'sta mac':<18} {'recv':>8} {'sent':>8} "
            f"{'recv/s':>8} {'sent/s':>8} {'drop%':>7} {'uart%':>7} {'B/pkt':>6} {'trend':>9} {'malf':>6} {'verdict':>8}"
        )
        print(head)
        print("-" * 124)
        all_pass = bool(summary)
        for node_id, r in summary.items():
            all_pass = all_pass and r["pass"]
            trend = f"{r['drop_trend_pct_per_min']:+.2f}" if r["trend_applicable"] else "n/a"
            bpp = f"{r['bytes_per_packet']:.0f}" if r["recv_total"] else "-"
            print(
                f"{node_id:<6} {os.path.basename(r['port']):<26} {str(r['sta_mac'] or '-'):<18} "
                f"{r['recv_total']:>8} {r['sent_total']:>8} "
                f"{r['recv_hz']:>8.1f} {r['sent_hz']:>8.1f} {r['drop_pct']:>7.2f} "
                f"{r['uart_pct_mean']:>7.1f} {bpp:>6} "
                f"{trend:>9} {r['counters']['malformed']:>6} "
                f"{'PASS' if r['pass'] else 'FAIL':>8}"
            )
        print("-" * 124)
        print(
            f"Gates: sent >= {self.min_sent_hz:.0f} pkt/s (expecting {self.expect_tx_hz:.0f}), "
            f"drop < {GATE_MAX_DROP_PCT:.0f} %, "
            f"drop not trending upward (> {GATE_TREND_SLOPE_PCT_PER_MIN:.1f} pp/min and "
            f"> {GATE_TREND_STEP_PCT:.1f} pp worse by the final third)."
        )
        for node_id, r in summary.items():
            if r["pass"]:
                continue
            reasons = []
            if not r["gate_sent"]:
                reasons.append(f"sent {r['sent_hz']:.1f} < {self.min_sent_hz:.0f} pkt/s")
            if not r["gate_drop"]:
                reasons.append(f"drop {r['drop_pct']:.2f} % >= {GATE_MAX_DROP_PCT:.0f} %")
            if not r["gate_trend"]:
                reasons.append(f"drop trending up {r['drop_trend_pct_per_min']:+.2f} pp/min")
            print(f"  {node_id} FAIL: {'; '.join(reasons)}")
            if r["queue_dropped"]:
                print(f"  {node_id} note: {r['queue_dropped']} frames dropped at the queue (a consumer is too slow)")
            if r["recv_total"] == 0:
                if r["bytes_read"] == 0:
                    print(
                        f"  {node_id} CAUSE: not one byte arrived. The board is not powered, "
                        f"is not running csi_recv, or this is the wrong port."
                    )
                else:
                    print(
                        f"  {node_id} CAUSE: {r['bytes_read']} bytes arrived but not one valid CSI row "
                        f"({r['counters']['non_csi']} unrecognised lines, "
                        f"{r['oversize_discards']} oversize buffer discards). This port is not a csi_recv "
                        f"receiver at {self.baud} baud. Most often it is the TRANSMITTER, whose console "
                        f"is at the ESP-IDF default of 115200: check with "
                        f"'python -m pipeline.io.identify_board', then exclude it using --nodes."
                    )
            elif r["uart_pct_mean"] > UART_SATURATION_PCT:
                cap = self.byte_capacity / r["bytes_per_packet"] if r["bytes_per_packet"] else float("nan")
                print(
                    f"  {node_id} CAUSE: console is {r['uart_pct_mean']:.0f} % of the {self.baud} baud ceiling. "
                    f"At {r['bytes_per_packet']:.0f} bytes per row that caps this link at about {cap:.0f} rows/s, "
                    f"which is below the transmit rate. The loss is the serial console, NOT the radio: "
                    f"moving the board or re-aiming the aerial will not help: the console is the "
                    f"limit, not the radio. A ~900 B row takes ~10.4 ms to print against an "
                    f"8 ms packet interval."
                )
        if not summary:
            print("  No nodes were read. Nothing to judge.")
        print(f"\nRESULT: {'PASS' if all_pass else 'FAIL'}")
        print("=" * 124)
        return all_pass

    # No resources to release; present for the consumer protocol.
    def close(self) -> None:
        return None


# Persist records to one binary file per node, plus a JSON sidecar.
class FileWriter:

    # Open one file per node.
    def __init__(
        self,
        out_dir: str,
        states: dict[str, NodeState],
        run_config: dict,
        chunk: int = 256,
        prefix: str = "",
    ) -> None:
        self.out_dir = out_dir
        self.states = states
        self.run_config = dict(run_config)
        self.chunk = chunk
        self.prefix = prefix
        self.t_start_host = time.time()
        os.makedirs(out_dir, exist_ok=True)
        self._files: dict[str, object] = {}
        self._buffers: dict[str, list[CsiRecord]] = {n: [] for n in states}
        self.written: dict[str, int] = {n: 0 for n in states}
        self.write_errors: dict[str, int] = {n: 0 for n in states}
        for node_id, st in states.items():
            path = os.path.join(out_dir, f"{prefix}{node_id}.bin")
            f = open(path, "wb")
            header = json.dumps(
                {
                    "node_id": node_id,
                    "port": st.port,
                    "sta_mac_at_open": st.sta_mac,
                    "dtype": [list(d) for d in FRAME_DTYPE.descr],
                    "csi_len": CSI_LEN,
                    "data_layout": "interleaved int8 (imag, real) per subcarrier, LLTF then HT-LTF",
                    "t_start_host": self.t_start_host,
                    "t_start_mono": time.monotonic(),
                },
                sort_keys=True,
            ).encode("utf-8")
            f.write(FILE_MAGIC)
            f.write(np.uint32(len(header)).tobytes())
            f.write(header)
            self._files[node_id] = f

    # Buffer one record, flushing when the chunk is full.
    def handle(self, record: CsiRecord) -> None:
        buf = self._buffers.get(record.node_id)
        if buf is None:
            return
        buf.append(record)
        if len(buf) >= self.chunk:
            self._flush(record.node_id)

    # Pack and write one node's buffered records.
    def _flush(self, node_id: str) -> None:
        buf = self._buffers.get(node_id)
        if not buf:
            return
        arr = np.empty(len(buf), dtype=FRAME_DTYPE)
        n = 0
        for rec in buf:
            try:
                row = arr[n]
                row["t_host"] = rec.t_host
                row["t_mono"] = rec.t_mono
                row["pkt_id"] = rec.pkt_id
                row["local_timestamp"] = rec.local_timestamp
                row["rssi"] = rec.rssi
                row["noise_floor"] = rec.noise_floor
                row["ampdu_cnt"] = rec.ampdu_cnt
                row["sig_len"] = rec.sig_len
                row["rate"] = rec.rate
                row["sig_mode"] = rec.sig_mode
                row["mcs"] = rec.mcs
                row["bandwidth"] = rec.bandwidth
                row["smoothing"] = rec.smoothing
                row["not_sounding"] = rec.not_sounding
                row["aggregation"] = rec.aggregation
                row["stbc"] = rec.stbc
                row["fec_coding"] = rec.fec_coding
                row["sgi"] = rec.sgi
                row["channel"] = rec.channel
                row["secondary_channel"] = rec.secondary_channel
                row["ant"] = rec.ant
                row["rx_format"] = rec.rx_format
                row["first_word"] = rec.first_word
                row["gain"] = rec.compensate_gain
                row["data"] = rec.data
                n += 1
            except (OverflowError, ValueError):
                self.write_errors[node_id] += 1
        buf.clear()
        if n:
            f = self._files[node_id]
            f.write(arr[:n].tobytes())
            self.written[node_id] += n

    # Flush every node once a second so a crash loses at most a second.
    def tick(self, now: float) -> None:
        for node_id in list(self._buffers):
            self._flush(node_id)
        for f in self._files.values():
            try:
                f.flush()
            except Exception:
                pass

    # Write the run-level JSON sidecar.
    def write_sidecar(self, summary: dict[str, dict]) -> str:
        path = os.path.join(self.out_dir, f"{self.prefix}run.json")
        doc = {
            "run_config": self.run_config,
            "t_start_host": self.t_start_host,
            "t_start_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(self.t_start_host)),
            "frame_dtype": [list(d) for d in FRAME_DTYPE.descr],
            "file_format": "8-byte magic CSIBIN01, uint32 LE header length, JSON header, then FRAME_DTYPE frames",
            "nodes": {
                node_id: {
                    "port": st.port,
                    "sta_mac": st.sta_mac,
                    "file": f"{self.prefix}{node_id}.bin",
                    "frames_written": self.written.get(node_id, 0),
                    "write_errors": self.write_errors.get(node_id, 0),
                    "counters": st.counters.as_dict(),
                    "queue_dropped": st.queue_dropped,
                    "read_errors": st.read_errors,
                }
                for node_id, st in self.states.items()
            },
            "summary": summary,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, sort_keys=True, default=str)
        return path

    # Flush all buffers and close all files.
    def close(self) -> None:
        for node_id in list(self._buffers):
            self._flush(node_id)
        for f in self._files.values():
            try:
                f.close()
            except Exception:
                pass


# Read back a.bin capture file written by:class:FileWriter.
def read_capture_file(path: str) -> tuple[dict, np.ndarray]:
    with open(path, "rb") as f:
        blob = f.read()
    if not blob.startswith(FILE_MAGIC):
        raise ValueError(f"{path} is not a CSIBIN01 capture file")
    off = len(FILE_MAGIC)
    hdr_len = int(np.frombuffer(blob[off : off + 4], dtype="<u4")[0])
    off += 4
    header = json.loads(blob[off : off + hdr_len].decode("utf-8"))
    off += hdr_len
    body = blob[off:]
    try:
        dtype = np.dtype([tuple(d) for d in header["dtype"]])
    except (KeyError, TypeError, ValueError):
        dtype = FRAME_DTYPE
    if len(body) % dtype.itemsize:
        raise ValueError(f"{path} has a partial trailing frame")
    return header, np.frombuffer(body, dtype=dtype)




# Run one capture: start readers, dispatch to consumers, then report.
def run_capture(
    nodes: dict[str, str],
    baud: int = DEFAULT_BAUD,
    duration: Optional[float] = None,
    out_dir: Optional[str] = None,
    interval: float = 1.0,
    run_config: Optional[dict] = None,
    expect_tx_hz: float = DEFAULT_EXPECT_TX_HZ,
    reset: bool = False,
    extra_consumers: Sequence[object] = (),
    stop_when: Optional[Callable[[], bool]] = None,
    writer_prefix: str = "",
    timestamped_subdir: bool = True,
    states_out: Optional[dict] = None,
    quiet_monitor: bool = False,
) -> int:
    states = {node_id: NodeState(node_id=node_id, port=port) for node_id, port in nodes.items()}
    if states_out is not None:
        states_out.update(states)
    record_queue: "queue.Queue[CsiRecord]" = queue.Queue(maxsize=QUEUE_MAXSIZE)
    stop_event = threading.Event()

    readers: list[SerialReader] = []
    for st in states.values():
        r = SerialReader(st, record_queue, stop_event, baud=baud, reset=reset)
        if r.open():
            readers.append(r)
            print(f"  opened {st.node_id} on {st.port} @ {baud} baud")
        else:
            print(f"  FAILED to open {st.node_id} on {st.port}: {st.error}")

    if not readers:
        print("\nNo ports could be opened. Is the board plugged in, and is another")
        print("process (idf.py monitor, screen, Arduino IDE) holding the port?")
        return 1

    monitor = RateMonitor(states, interval=interval, baud=baud, expect_tx_hz=expect_tx_hz, quiet=quiet_monitor)
    config_watch = ConfigWatch()
    consumers: list[object] = [monitor, config_watch]
    consumers.extend(extra_consumers)
    writer: Optional[FileWriter] = None
    if out_dir:
        run_dir = os.path.join(out_dir, time.strftime("%Y%m%d-%H%M%S")) if timestamped_subdir else out_dir
        writer = FileWriter(run_dir, states, run_config or {}, prefix=writer_prefix)
        consumers.append(writer)
        print(f"  writing binary capture to {run_dir}/")

    interrupted = threading.Event()

    # Function on stop signal.
    def _on_stop_signal(signum, frame) -> None:
        interrupted.set()
        stop_event.set()

    previous_handlers = {
        sig: signal.signal(sig, _on_stop_signal)
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
    }

    if reset:
        print(f"\nReset pulsed on every port; waiting {BOOT_SETTLE_S:.0f}s for boot banners.")
    print(f"\nCapturing from {len(readers)} node(s). Ctrl+C to stop.\n")
    for r in readers:
        r.start()

    settle_until = time.monotonic() + BOOT_SETTLE_S if reset else None
    t0 = time.monotonic()
    try:
        while not stop_event.is_set():
            if duration is not None and (time.monotonic() - t0) >= duration:
                stop_event.set()
                break
            if stop_when is not None and stop_when():
                stop_event.set()
                break
            try:
                rec = record_queue.get(timeout=0.05)
            except queue.Empty:
                rec = None
            if rec is not None:
                for c in consumers:
                    c.handle(rec)
            now = time.monotonic()
            if settle_until is not None and now >= settle_until:
                settle_until = None
                monitor.restart(now)
                t0 = now
                found = {n: st.sta_mac for n, st in states.items()}
                named = sum(1 for v in found.values() if v)
                print(f"Boot settle done; station MAC recovered for {named}/{len(found)} node(s).")
                for n, mac in found.items():
                    print(f"  {n}  {states[n].port}  {mac or 'no banner seen'}")
                print()
            for c in consumers:
                if settle_until is not None and (c is monitor or getattr(c, "owns_terminal", False)):
                    continue
                c.tick(now)
    finally:
        stop_event.set()
        for r in readers:
            r.join(timeout=2.0)
        while True:
            try:
                rec = record_queue.get_nowait()
            except queue.Empty:
                break
            for c in consumers:
                c.handle(rec)
        for r in readers:
            r.close()
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)

    if interrupted.is_set():
        print("\nInterrupted; shutting down cleanly.")

    summary = monitor.summarise()
    ok = monitor.print_summary(summary)

    if writer is not None:
        writer.close()

    reconciled, report = reconcile(states, writer, config_watch)
    print()
    for line in report:
        print(line)
    ok = ok and reconciled

    if writer is not None:
        sidecar = writer.write_sidecar(summary)
        total = sum(writer.written.values())
        print(f"Wrote {total} frames to {writer.out_dir}/ (sidecar: {os.path.basename(sidecar)})")
    monitor.close()
    return 0 if ok else 1


# Build the command-line parser for the module entry point.
def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m pipeline.io.capture_logger",
        description=(
            "Stream CSI from N ESP32 receivers at once and measure per-node "
            "packet rate and drop rate. Writing to disk is off unless --out is given."
        ),
    )
    p.add_argument("--duration", type=float, default=None, metavar="S", help="run length in seconds (default: until Ctrl+C)")
    p.add_argument("--out", type=str, default=None, metavar="DIR", help="write binary capture into DIR (default: measure only, write nothing)")
    p.add_argument("--nodes", type=str, default=None, metavar="SPEC", help='explicit mapping, e.g. "RX1=/dev/cu.usbserial-0001,RX2=/dev/cu.usbserial-0002"')
    p.add_argument("--baud", type=int, default=DEFAULT_BAUD, help=f"serial baud rate (default: {DEFAULT_BAUD})")
    p.add_argument("--interval", type=float, default=1.0, metavar="S", help="reporting period in seconds (default: 1.0)")
    p.add_argument("--expect-hz", type=float, default=DEFAULT_EXPECT_TX_HZ, metavar="HZ", help=f"transmit rate this run should achieve, for the sent gate (default: {DEFAULT_EXPECT_TX_HZ:.0f}). Note the achieved rate is always below CONFIG_SEND_FREQUENCY in csi_send.")
    p.add_argument("--reset", action="store_true", help="reboot every board at start-up so each reprints its boot banner, recording which physical board (station MAC) is on which port")
    p.add_argument("--glob", type=str, default=PORT_GLOB, help=f"port discovery glob (default: {PORT_GLOB})")
    return p


# Entry point for python -m pipeline.io.capture_logger.
def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        nodes = resolve_nodes(args.nodes, args.glob)
    except ValueError as exc:
        print(f"error: {exc}")
        return 2
    if not nodes:
        print(f"\nNo receivers found matching {args.glob}.")
        print("Plug a board in, and remember this project uses /dev/cu.* not /dev/tty.*.")
        return 1
    run_config = {
        "baud": args.baud,
        "duration_s": args.duration,
        "interval_s": args.interval,
        "nodes": nodes,
        "expect_tx_hz": args.expect_hz,
        "reset": args.reset,
        "gates": {
            "min_sent_hz": args.expect_hz * GATE_SENT_TOLERANCE,
            "max_drop_pct": GATE_MAX_DROP_PCT,
            "trend_slope_pct_per_min": GATE_TREND_SLOPE_PCT_PER_MIN,
            "trend_step_pct": GATE_TREND_STEP_PCT,
        },
    }
    return run_capture(
        nodes=nodes,
        baud=args.baud,
        duration=args.duration,
        out_dir=args.out,
        interval=args.interval,
        run_config=run_config,
        expect_tx_hz=args.expect_hz,
        reset=args.reset,
    )


if __name__ == "__main__":
    sys.exit(main())
