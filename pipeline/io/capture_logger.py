"""Streaming multi-node CSI capture: serial readers, rate monitor, writer.

This is a streaming architecture, not a dump script. One reader thread per
receiver pushes parsed records onto a single shared queue; consumers pull
from that queue and are free to be slow. A consumer can never stall a
serial port: readers only ever ``put_nowait``, and a full queue costs a
counted dropped frame rather than back-pressure onto the UART, because a
stalled UART loses packets silently and would corrupt the very drop-rate
measurement this stage exists to make.

    /dev/cu.usbserial-A ──> SerialReader(RX1) ─┐
    /dev/cu.usbserial-B ──> SerialReader(RX2) ─┼──> Queue ──> dispatcher ──┬──> RateMonitor  ──> terminal
    /dev/cu.usbserial-C ──> SerialReader(RX3) ─┘   (bounded)   (main thread)└──> FileWriter   ──> .bin + .json
                                                                            └──> (future: ML consumer)

Each reader owns: bytes -> lines -> :func:`pipeline.io.parse.parse_line` ->
tagged :class:`~pipeline.io.parse.CsiRecord`. The dispatcher owns fan-out.
Consumers own presentation and persistence, and know nothing about serial.

PROJECT RULES ENCODED HERE
--------------------------
* ONE process owns every receiver, so all nodes share one monotonic clock.
  That is what makes cross-node comparison of packet ids meaningful, and it
  is why this will also host the keypress anchor logger in the next stage.
* Malformed lines are counted and dropped, never fatal.
* Every persisted record carries ``node_id`` and both host timestamps.
* Ports are addressed as ``/dev/cu.*``. Never ``/dev/tty.*``: the tty
  device blocks on open waiting for carrier detect and will hang the run.

Run it with ``python -m pipeline.io.capture_logger``.
"""

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

#: Console baud rate of the ``csi_recv`` firmware.
DEFAULT_BAUD: int = 921600

#: Glob for USB-serial devices on macOS. ``cu`` not ``tty``: see module docs.
PORT_GLOB: str = "/dev/cu.usbserial-*"

#: Expected transmit rate in packets per second. This is the rate ACHIEVED,
#: not the value of CONFIG_SEND_FREQUENCY in the esp-csi csi_send example:
#: that loop calls esp_now_send and then sleeps for the full nominal period,
#: so the send call's own duration is added on top and the achieved rate is
#: always lower than configured. Measure it, then set this to what you see.
DEFAULT_EXPECT_TX_HZ: float = 150.0

#: Acceptance gate: the mean observed transmit rate must reach this share of
#: the expected rate, else the transmitter is misconfigured or off.
GATE_SENT_TOLERANCE: float = 0.97

#: Acceptance gate: mean packet loss per node must stay below this, in %.
GATE_MAX_DROP_PCT: float = 5.0

#: Acceptance gate: drop must not trend upward. Failed when the least
#: squares slope of per-second drop % exceeds this many percentage points
#: per minute AND the final third of the run is materially worse than the
#: first third (see :data:`GATE_TREND_STEP_PCT`).
GATE_TREND_SLOPE_PCT_PER_MIN: float = 1.0

#: Companion to the slope test: the final third's mean drop must not exceed
#: the first third's by more than this many percentage points.
GATE_TREND_STEP_PCT: float = 2.0

#: A trend verdict needs at least this many one-second samples to mean
#: anything; shorter runs report the trend gate as not applicable.
GATE_TREND_MIN_SAMPLES: int = 30

#: Seconds to let a board boot after a reset pulse before rate counting
#: starts. The ROM bootloader burst, the ESP-IDF logs and the banner all
#: arrive in this window, and no CSI does, so counting it would understate
#: the rate for the first report.
BOOT_SETTLE_S: float = 2.0

#: A CSI row is about 1 kB. A buffer far larger than that with no newline in
#: it is not a long line, it is a stream with no line structure at all: a
#: board at the wrong baud, or electrical noise. Discard rather than grow,
#: because an unbounded buffer on a ten-minute run is hundreds of megabytes.
MAX_LINE_BYTES: int = 65536

#: Above this share of the baud-rate ceiling the console is the bottleneck:
#: the firmware's CSI callback fires but the UART cannot print the rows, so
#: whole rows are dropped on the device. Measured loss is then a transport
#: limit and says nothing about the radio link.
UART_SATURATION_PCT: float = 85.0

#: Bound on the shared queue. At 3 nodes x 150 Hz this is roughly 130 s of
#: slack, far more than any consumer hiccup, so a full queue means a
#: consumer is broken rather than merely busy.
QUEUE_MAXSIZE: int = 60000

#: Moduli tried when a packet id goes backwards, smallest first.
_WRAP_MODULI: tuple[int, ...] = (1 << 16, 1 << 32, 1 << 64)

#: On-disk frame layout for :class:`FileWriter`. Fixed width, so a capture
#: file is ``np.frombuffer``-able in one call. See :func:`read_capture_file`.
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
        # AGC gain compensation for this packet. Stored rather than applied,
        # so `data` always holds exactly what the radio reported and the
        # correction stays auditable. 1.0 for legacy decimal captures, where
        # the device applied it before printing.
        ("gain", "<f4"),
        ("data", "i1", (CSI_LEN,)),
    ]
)

#: Magic bytes beginning every ``.bin`` capture file.
FILE_MAGIC: bytes = b"CSIBIN01"


# --------------------------------------------------------------------------
# Port discovery and node naming
# --------------------------------------------------------------------------


def discover_ports(pattern: str = PORT_GLOB) -> list[str]:
    """Find attached USB-serial receivers.

    Args:
        pattern: Glob for candidate device paths.

    Returns:
        Matching device paths, sorted, so that node numbering is stable
        within a single boot of the host.

    Constraints:
        Returns ``/dev/cu.*`` paths only. The names are NOT unique across
        physical boards and may be reassigned on replug, so the ordering
        here is a convenience, not an identity. Physical identity comes from
        the station MAC in each board's boot banner.
    """
    return sorted(glob.glob(pattern))


def parse_nodes_arg(spec: str) -> dict[str, str]:
    """Parse an explicit ``--nodes`` mapping.

    Args:
        spec: Comma-separated ``NAME=PORT`` pairs, e.g.
            ``"RX1=/dev/cu.usbserial-0001,RX2=/dev/cu.usbserial-0002"``.

    Returns:
        Mapping of node id to device path, preserving the given order.

    Raises:
        ValueError: If an entry is not ``NAME=PORT``, a name repeats, or a
            port repeats. This is start-up configuration, not stream data,
            so failing loudly here is correct.
    """
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


def resolve_nodes(nodes_arg: Optional[str], pattern: str = PORT_GLOB) -> dict[str, str]:
    """Decide which node id maps to which serial port.

    Args:
        nodes_arg: Explicit ``--nodes`` string, or ``None`` to autodiscover.
        pattern: Glob used when autodiscovering.

    Returns:
        Mapping of node id to device path. Autodiscovered nodes are named
        ``RX1..RXN`` in sorted port order.

    Constraints:
        Prints the number of ports found, because "I expected three boards
        and it found two" is the single most common failure of this stage.
    """
    if nodes_arg:
        mapping = parse_nodes_arg(nodes_arg)
        print(f"Using {len(mapping)} explicitly named node(s).")
        return mapping
    ports = discover_ports(pattern)
    print(f"Found {len(ports)} serial port(s) matching {pattern}")
    for p in ports:
        print(f"  {p}")
    return {f"RX{i}": p for i, p in enumerate(ports, start=1)}


# --------------------------------------------------------------------------
# Reader threads
# --------------------------------------------------------------------------


@dataclass
class NodeState:
    """Everything the run knows about one receiver.

    Attributes:
        node_id: Receiver identifier.
        port: Device path being read.
        counters: Parse outcome tallies for this node.
        sta_mac: The board's own station MAC, once its boot banner is seen.
            ``None`` if the board booted before the reader attached, which
            is normal and not an error.
        bytes_read: Raw bytes read from the port, used to work out how
            close the console is to its baud-rate ceiling.
        oversize_discards: Times the line buffer was discarded for growing
            past :data:`MAX_LINE_BYTES` without a newline.
        queue_dropped: Records discarded because the shared queue was full.
        read_errors: Serial read failures, e.g. a board unplugged mid-run.
        opened: Whether the port was opened successfully.
        error: Failure text if the port could not be opened.
    """

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


class ConfigWatch:
    """Record the PHY configuration the packets actually arrived with.

    The session records what it INTENDED to configure. Nothing until now
    checked what the radio actually did, so a receiver left on the wrong
    channel or bandwidth would produce a capture that passes every other
    check and is quietly incomparable with the rest of the dataset.
    """

    #: Fields compared. Each should hold exactly one value for a whole
    #: session, and the same value on every node.
    FIELDS: tuple[str, ...] = ("channel", "secondary_channel", "bandwidth", "sig_mode", "rate", "mcs")

    def __init__(self) -> None:
        """Create an empty watch."""
        self.seen: dict[str, dict[str, dict[int, int]]] = {}

    def handle(self, record: CsiRecord) -> None:
        """Count the configuration this packet reported."""
        node = self.seen.setdefault(record.node_id, {f: {} for f in self.FIELDS})
        for f in self.FIELDS:
            v = int(getattr(record, f))
            node[f][v] = node[f].get(v, 0) + 1

    def tick(self, now: float) -> None:
        """Nothing periodic to do."""
        return None

    def close(self) -> None:
        """Nothing to release."""
        return None

    def dominant(self, node_id: str) -> dict[str, int]:
        """Return the most common value of each field for one node."""
        node = self.seen.get(node_id, {})
        return {f: max(vals, key=vals.get) for f, vals in node.items() if vals}

    def problems(self) -> list[str]:
        """List configuration inconsistencies worth stopping for.

        Returns:
            Human-readable descriptions: a field that changed mid-session on
            one node, or a field that differs between nodes.
        """
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


def reconcile(
    states: dict[str, NodeState],
    writer: Optional["FileWriter"] = None,
    config_watch: Optional[ConfigWatch] = None,
) -> tuple[bool, list[str]]:
    """Check that nothing went missing between the wire and the file.

    Args:
        states: Per-node state carrying the parse counters.
        writer: The file writer, if the run wrote anything.
        config_watch: The PHY configuration watch, if one ran.

    Returns:
        A tuple of (whether everything reconciles, the report lines).

    Constraints:
        Every packet that was parsed must be accounted for: either written
        to disk, or explained by a counted drop. Silence is the failure mode
        this guards against, so the report prints in full whether or not
        anything is wrong, and the totals are shown even when they agree.
    """
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


def reset_board(ser: object) -> None:
    """Reboot an attached ESP32 by pulsing the auto-reset lines.

    Args:
        ser: An open ``serial.Serial`` handle.

    Returns:
        None.

    Constraints:
        On the usual CP2102 auto-reset circuit RTS drives EN and DTR drives
        GPIO0. DTR is held false throughout so the chip boots its
        application rather than entering the serial bootloader. Failures are
        ignored: a board wired without the circuit simply does not reset,
        which costs the banner but breaks nothing.
    """
    try:
        ser.dtr = False  # type: ignore[attr-defined]
        ser.rts = True  # type: ignore[attr-defined]  # EN low: hold in reset
        time.sleep(0.1)
        ser.rts = False  # type: ignore[attr-defined]  # EN high: boot
        time.sleep(0.05)
        ser.reset_input_buffer()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass


class SerialReader(threading.Thread):
    """Read one receiver's console, parse it, and enqueue tagged records.

    The thread owns exactly one port. It never touches consumer state and
    never blocks on the queue, so a slow or crashed consumer cannot cause
    UART overruns and thereby fake a packet loss result.
    """

    def __init__(
        self,
        state: NodeState,
        out_queue: "queue.Queue[CsiRecord]",
        stop_event: threading.Event,
        baud: int = DEFAULT_BAUD,
        read_timeout: float = 0.05,
        reset: bool = False,
    ) -> None:
        """Create a reader for one port.

        Args:
            state: This node's mutable state, updated in place.
            out_queue: Shared record queue.
            stop_event: Set to ask the reader to finish.
            baud: Serial baud rate.
            read_timeout: Serial read timeout in seconds. Kept small so
                that shutdown is prompt.
            reset: Reboot the board on open, so that it reprints its boot
                banner and its station MAC can be recorded.
        """
        super().__init__(name=f"reader-{state.node_id}", daemon=True)
        self.state = state
        self.queue = out_queue
        self.stop_event = stop_event
        self.baud = baud
        self.read_timeout = read_timeout
        self.reset = reset
        self._ser: object = None

    def open(self) -> bool:
        """Open the serial port.

        Returns:
            True on success. On failure the reason is recorded on
            :attr:`state` and False is returned, so that one dead board
            does not abort a multi-node run.
        """
        try:
            import serial  # imported lazily: parsing and tests need no pyserial
        except ImportError as exc:  # pragma: no cover - environment dependent
            self.state.error = f"pyserial not installed ({exc}); pip install pyserial"
            return False
        try:
            self._ser = serial.Serial(self.state.port, self.baud, timeout=self.read_timeout)
        except Exception as exc:  # noqa: BLE001 - any driver error is just a dead node
            self.state.error = str(exc)
            return False
        if self.reset:
            reset_board(self._ser)
        self.state.opened = True
        return True

    def run(self) -> None:
        """Stream lines until asked to stop.

        Bytes are accumulated and split on newlines, so a read boundary
        falling mid-line does not manufacture a torn line. Anything still
        unterminated at shutdown is discarded rather than parsed.

        Constraints:
            Decodes with ``errors="replace"``: the boot burst is the ROM
            bootloader talking at a different baud and is not valid UTF-8.
            No exception from decoding, parsing or the queue may escape.
        """
        if self._ser is None:
            return
        buf = bytearray()
        st = self.state
        while not self.stop_event.is_set():
            try:
                chunk = self._ser.read(4096)
            except Exception:  # noqa: BLE001 - board unplugged, USB reset, etc.
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
                # No line structure at all: keep the tail in case a real
                # line is starting, and drop the rest rather than grow.
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

    def close(self) -> None:
        """Close the serial port, ignoring errors on an already-dead board."""
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:  # noqa: BLE001
                pass


# --------------------------------------------------------------------------
# Consumers
# --------------------------------------------------------------------------


class Consumer(Protocol):
    """Anything that can subscribe to the record stream.

    A future ML consumer implements exactly this and is added to the
    dispatcher's list; no reader or queue code changes.
    """

    def handle(self, record: CsiRecord) -> None:
        """Process one record. Must not raise and must not block."""

    def tick(self, now: float) -> None:
        """Periodic callback, roughly once per second, from the dispatcher."""

    def close(self) -> None:
        """Flush and release resources at end of run."""


def wrap_delta(prev_id: int, cur_id: int) -> Optional[int]:
    """Compute how many packets the transmitter sent between two ids.

    Args:
        prev_id: Previously seen packet id.
        cur_id: Current packet id.

    Returns:
        The forward distance from ``prev_id`` to ``cur_id``, or ``None`` if
        the step cannot be explained.

    Constraints:
        The id counter may wrap and its width is not documented by the
        firmware, so a backwards step is retried against 16-, 32- and
        64-bit moduli, smallest first, accepting the first that yields a
        forward step of less than half that modulus. A step that no modulus
        explains returns ``None`` and the interval is excluded from the
        sent-rate estimate rather than being allowed to invent traffic.
    """
    if cur_id >= prev_id:
        return cur_id - prev_id
    for m in _WRAP_MODULI:
        d = cur_id - prev_id + m
        if 0 < d < m // 2:
            return d
    return None


@dataclass
class NodeRateStats:
    """Rolling and cumulative rate figures for one node.

    Attributes:
        recv_total: Records received since the run began.
        sent_total: Transmitted packets inferred from id gaps.
        recv_window: Records received in the current one-second window.
        sent_window: Transmitted packets inferred in the current window.
        rssi_sum: Sum of RSSI in the current window, for the mean.
        last_noise_floor: Most recent noise floor seen.
        first_id: First packet id seen, for the run-wide sent total.
        last_id: Most recent packet id seen.
        unexplained_steps: Backwards id steps no wrap modulus explained.
        bytes_at_last_tick: Byte count at the previous report, so the rate
            over the window can be differenced out.
        uart_series: Per-second console utilisation percentages.
        drop_series: Per-second drop percentages, for the trend gate.
    """

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


class RateMonitor:
    """Print one line per node per second and judge the run at the end.

    ``recv`` is counted host-side: records this process actually parsed.
    ``sent`` is inferred from the transmitter's own packet counter, which
    every receiver hears, so a gap in ids at one node is a packet that node
    missed. ``drop`` is therefore genuinely that node's loss and not a
    guess against a nominal rate.

    A gap means the row never reached the host, but NOT necessarily that the
    radio missed the packet. ``csi_recv`` prints with ``ets_printf``, which
    blocks until the UART FIFO drains, so while a row is printing the Wi-Fi
    driver discards the CSI of any packet that arrives. Device-side console
    drops and true radio loss are therefore both counted here, and they are
    only separable by lowering the transmit rate until ``uart`` utilisation
    is comfortably below the ceiling: whatever loss remains is the radio.
    """

    def __init__(
        self,
        states: dict[str, NodeState],
        interval: float = 1.0,
        baud: int = DEFAULT_BAUD,
        expect_tx_hz: float = DEFAULT_EXPECT_TX_HZ,
        quiet: bool = False,
    ) -> None:
        """Create the monitor.

        Args:
            states: Per-node state, used to read parse counters.
            interval: Reporting period in seconds.
            baud: Serial baud rate, used to express the observed byte rate
                as a share of what the console can physically carry.
            expect_tx_hz: Transmit rate this run should achieve.
            quiet: Suppress the per-second lines but keep measuring. A
                ground-truth session owns the terminal and shows its own
                status line, but still needs the console-utilisation figure
                for the end-of-run summary; silencing the monitor by setting
                a huge interval instead stopped it measuring at all and left
                uart% as nan.
        """
        self.states = states
        self.interval = interval
        self.baud = baud
        self.expect_tx_hz = expect_tx_hz
        self.quiet = quiet
        self.min_sent_hz = expect_tx_hz * GATE_SENT_TOLERANCE
        #: Usable bytes per second: 8N1 framing costs 10 bits per byte.
        self.byte_capacity = baud / 10.0
        self.stats: dict[str, NodeRateStats] = {n: NodeRateStats() for n in states}
        self.t_start = time.monotonic()
        self._next_tick = self.t_start + interval
        self._last_tick = self.t_start

    def restart(self, now: float) -> None:
        """Discard everything counted so far and start the run clock again.

        Args:
            now: Current monotonic time, the new start of the run.

        Returns:
            None.

        Constraints:
            Used after a reset settle period so that the boot window, which
            carries no CSI, does not drag the first reported rates down.
            Parse counters on the node states are left alone: a malformed
            line during boot is still worth reporting.
        """
        for node_id, st in self.states.items():
            self.stats[node_id] = NodeRateStats(bytes_at_last_tick=st.bytes_read)
        self.t_start = now
        self._last_tick = now
        self._next_tick = now + self.interval

    def handle(self, record: CsiRecord) -> None:
        """Fold one record into the current window's statistics."""
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

    def tick(self, now: float) -> None:
        """Emit the per-second lines if the interval has elapsed.

        Args:
            now: Current monotonic time.

        Constraints:
            The rates are divided by the true elapsed interval rather than
            by the nominal one, so a late tick cannot understate the rate.
        """
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

    def trend_slope_pct_per_min(self, series: Sequence[float]) -> float:
        """Least-squares slope of a per-second drop series.

        Args:
            series: Per-second drop percentages.

        Returns:
            Slope in percentage points per minute; 0.0 if there is too
            little data to fit.
        """
        n = len(series)
        if n < 2:
            return 0.0
        x = np.arange(n, dtype=np.float64)
        y = np.asarray(series, dtype=np.float64)
        slope = float(np.polyfit(x, y, 1)[0])
        return slope * 60.0

    def summarise(self) -> dict[str, dict]:
        """Build the end-of-run figures for every node.

        Returns:
            Per-node dict of run totals, mean rates, drop percentage, the
            three gate verdicts and an overall node verdict.

        Constraints:
            Gates are: mean sent rate at least
            :data:`GATE_MIN_SENT_HZ`; mean drop below
            :data:`GATE_MAX_DROP_PCT`; and drop not trending upward, judged
            only when at least :data:`GATE_TREND_MIN_SAMPLES` one-second
            samples exist.
        """
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

    def print_summary(self, summary: dict[str, dict]) -> bool:
        """Print the summary table and the PASS/FAIL verdict.

        Args:
            summary: Output of :meth:`summarise`.

        Returns:
            True if every node passed every applicable gate.
        """
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
            # A slope fitted to a handful of samples is noise, so say so
            # rather than printing a number that invites over-reading.
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
                # No valid rows at all is a different fault from a saturated
                # console, and must not borrow its explanation.
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

    def close(self) -> None:
        """No resources to release; present for the consumer protocol."""
        return None


class FileWriter:
    """Persist records to one binary file per node, plus a JSON sidecar.

    File format, per node, written to ``<out>/<run>/<node_id>.bin``::

        magic     8 bytes  b"CSIBIN01"
        hdr_len   uint32 little-endian
        header    hdr_len bytes of UTF-8 JSON (node id, port, MAC, dtype,
                  start time, format notes)
        frames    hdr_len onwards: fixed-width records of FRAME_DTYPE,
                  little-endian, one per packet, in arrival order

    Read one back with :func:`read_capture_file`. Never ASCII: at 150 Hz per
    node a text log is both large and lossy about float timestamps.
    """

    def __init__(
        self,
        out_dir: str,
        states: dict[str, NodeState],
        run_config: dict,
        chunk: int = 256,
        prefix: str = "",
    ) -> None:
        """Open one file per node.

        Args:
            out_dir: Directory for this run's files; created if absent.
            states: Per-node state, used for the file headers.
            run_config: Run configuration recorded in the sidecar.
            chunk: Records buffered per node before a write.
            prefix: Prepended to every filename, so a ground-truth session
                can name its CSI files after the participant and mode and
                have them sit beside the matching .gt.json sidecar.
        """
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
                    # Null when the board booted before the reader attached,
                    # since the banner is printed once at boot. The final
                    # node -> port -> MAC mapping is in run.json.
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

    def handle(self, record: CsiRecord) -> None:
        """Buffer one record, flushing when the chunk is full."""
        buf = self._buffers.get(record.node_id)
        if buf is None:
            return
        buf.append(record)
        if len(buf) >= self.chunk:
            self._flush(record.node_id)

    def _flush(self, node_id: str) -> None:
        """Pack and write one node's buffered records."""
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
                # A field outside its on-disk width means firmware output we
                # did not anticipate. Drop the frame, count it, keep going.
                self.write_errors[node_id] += 1
        buf.clear()
        if n:
            f = self._files[node_id]
            f.write(arr[:n].tobytes())  # type: ignore[attr-defined]
            self.written[node_id] += n

    def tick(self, now: float) -> None:
        """Flush every node once a second so a crash loses at most a second."""
        for node_id in list(self._buffers):
            self._flush(node_id)
        for f in self._files.values():
            try:
                f.flush()  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass

    def write_sidecar(self, summary: dict[str, dict]) -> str:
        """Write the run-level JSON sidecar.

        Args:
            summary: End-of-run figures from :meth:`RateMonitor.summarise`.

        Returns:
            Path to the sidecar file.

        Constraints:
            Records the run config, the node -> port -> MAC mapping, the
            start time and the final counters, so a ``.bin`` is never
            orphaned from the conditions that produced it.
        """
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

    def close(self) -> None:
        """Flush all buffers and close all files."""
        for node_id in list(self._buffers):
            self._flush(node_id)
        for f in self._files.values():
            try:
                f.close()  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass


def read_capture_file(path: str) -> tuple[dict, np.ndarray]:
    """Read back a ``.bin`` capture file written by :class:`FileWriter`.

    Args:
        path: Path to a ``<node_id>.bin`` file.

    Returns:
        A tuple of (JSON header dict, structured array of
        :data:`FRAME_DTYPE` frames in arrival order).

    Raises:
        ValueError: If the magic bytes are wrong, or the frame region is not
            a whole number of frames.
    """
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
    # Use the dtype recorded in this file's own header rather than whatever
    # the module defines today, so a capture stays readable after the frame
    # layout changes. Falling back to the current dtype covers files written
    # before the header carried one.
    try:
        dtype = np.dtype([tuple(d) for d in header["dtype"]])
    except (KeyError, TypeError, ValueError):
        dtype = FRAME_DTYPE
    if len(body) % dtype.itemsize:
        raise ValueError(f"{path} has a partial trailing frame")
    return header, np.frombuffer(body, dtype=dtype)


# --------------------------------------------------------------------------
# Run loop
# --------------------------------------------------------------------------


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
    """Run one capture: start readers, dispatch to consumers, then report.

    Args:
        nodes: Mapping of node id to serial device path.
        baud: Serial baud rate for every node.
        duration: Run length in seconds, or ``None`` to run until Ctrl+C.
        out_dir: Directory for binary output. ``None`` disables the writer,
            which is the default: this stage measures, it does not collect.
        interval: Reporting period in seconds.
        run_config: Configuration echoed into the JSON sidecar.
        expect_tx_hz: Transmit rate the run should achieve, used for the
            sent-rate gate.
        reset: Reboot every board at start-up so each reprints its boot
            banner, letting the run record which physical board (by station
            MAC) sat on which port. Costs the first couple of seconds.
        extra_consumers: Further consumers to fan records out to, appended
            after the monitor and writer. Used to run the ground-truth
            logger in this process, so that CSI and ground truth share one
            monotonic clock.
        stop_when: Optional predicate polled each loop; the run ends when it
            returns True. Lets a ground-truth session end the capture when
            its last pass closes.
        writer_prefix: Prepended to the names of the files the writer
            creates.
        quiet_monitor: Suppress the monitor's per-second lines while still
            measuring, for callers that own the terminal.
        states_out: Optional dict populated in place with this run's node
            states. A ground-truth session passes the same dict it holds, so
            that the station MACs recovered at boot reach its sidecar: the
            recording has to be tied to physical boards, not to port names.
        timestamped_subdir: Whether to place the run's files in a timestamped
            directory under ``out_dir``. A ground-truth session turns this
            off so its CSI files sit directly beside the .gt.json sidecar
            that labels them.

    Returns:
        Process exit code: 0 if every node passed every gate, else 1.

    Constraints:
        * Shuts down cleanly on Ctrl+C or on ``duration`` elapsing: readers
          stop, ports close, the queue drains, files flush, summary prints.
        * Consumers never block readers; a full queue costs counted frames.
    """
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

    def _on_stop_signal(signum, frame) -> None:  # noqa: ANN001 - signal handler signature
        interrupted.set()
        stop_event.set()

    # Ctrl+C, `kill <pid>` and a closed terminal all take the same path: set
    # the stop flag and let the loop finish normally, so every `finally`
    # downstream runs - the writer flushes, and a ground-truth session gets
    # to write its sidecar. Left at their defaults, SIGTERM and SIGHUP kill
    # the interpreter outright with no `finally` at all, which is how a
    # closed terminal window would lose a participant's labels. SIGKILL
    # cannot be caught by anything; there is no defence against it.
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
                    c.handle(rec)  # type: ignore[attr-defined]
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
                # The monitor stays silent through the boot settle: those
                # seconds carry no CSI and its run clock has not started.
                #
                # Anything else that draws an in-place status line stays
                # silent for the same window, and for a harder reason: the
                # settle report above is printed straight to stdout, so a
                # consumer redrawing with a bare carriage return collides
                # with it and both lines are mangled on screen.
                if settle_until is not None and (c is monitor or getattr(c, "owns_terminal", False)):
                    continue
                c.tick(now)  # type: ignore[attr-defined]
    finally:
        stop_event.set()
        for r in readers:
            r.join(timeout=2.0)
        # Drain whatever the readers enqueued before stopping, so the
        # counters and the files agree with each other.
        while True:
            try:
                rec = record_queue.get_nowait()
            except queue.Empty:
                break
            for c in consumers:
                c.handle(rec)  # type: ignore[attr-defined]
        for r in readers:
            r.close()
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)

    if interrupted.is_set():
        print("\nInterrupted; shutting down cleanly.")

    summary = monitor.summarise()
    ok = monitor.print_summary(summary)

    # Close the writer BEFORE reconciling: it buffers a chunk per node, so
    # reconciling first counts the unflushed tail as missing. The check found
    # that in itself the first time it ran.
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


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for the module entry point."""
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


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point for ``python -m pipeline.io.capture_logger``.

    Args:
        argv: Argument vector, defaulting to ``sys.argv[1:]``.

    Returns:
        Process exit code: 0 if the run passed every gate, else 1.
    """
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
