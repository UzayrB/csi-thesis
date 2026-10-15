"""Identify which esp-csi firmware is running on a serial port.

A ``/dev/cu.usbserial-*`` name comes from the CP2102's own USB serial-number
string, not from attachment order: a bridge reporting ``0001`` becomes
``/dev/cu.usbserial-0001``. Cheap boards very often all ship with serial
``0001``, so names collide and shift between sessions, and the port tells you
nothing reliable about which physical ESP32 is on the other end. That matters
most in one situation: flashing. Putting ``csi_send`` onto a receiver costs a
reflash and a confusing hour, and knowing which board you are addressing is
the only thing that prevents it.

Identification is primarily by the project name ESP-IDF logs during
start-up (``Project name: csi_recv`` / ``csi_send``), because that is printed
unconditionally before any application code runs. The application banners
are a fallback only: ``csi_recv`` prints its
``================ CSI RECV ================`` from inside the CSI callback,
so a perfectly healthy receiver stays silent for as long as the transmitter
is switched off, and relying on the banner alone reported such boards as
INCONCLUSIVE. A receiver already streaming is also identified by its
``CSI_DATA`` rows.

The board's station MAC is reported alongside the verdict when the boot
banner reveals it, since that is the durable physical identity.

A transmitter, though, is silent after boot: its loop only prints when a send
fails. Identifying one therefore needs a reboot, and asking the operator to
press EN at the right moment is unreliable. Instead this toggles the
CP2102's RTS line, which is wired to the ESP32's EN pin by the usual
auto-reset circuit, and reboots the board itself. DTR is held false
throughout so GPIO0 stays high and the chip boots its application rather
than entering the serial bootloader.

The console baud is also not assumed: ``csi_recv`` runs at 921600 but the
transmitter may have been left at the ESP-IDF default, so each candidate
baud is tried in turn. Listening at the wrong baud yields replacement
characters rather than silence, which is why a raw preview is printed on
failure: "nothing at all" and "garbage" are different faults.

Nothing here writes to the device or flashes anything.

Run it with ``python -m pipeline.io.identify_board [PORT]``.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from typing import Optional, Sequence

from pipeline.io.capture_logger import DEFAULT_BAUD, discover_ports, reset_board

#: Marker printed by csi_send once it starts broadcasting.
SEND_BANNER: str = "CSI SEND"

#: Marker printed by csi_recv. Note this lives INSIDE the CSI callback, so it
#: appears only after a packet has actually been received: with the
#: transmitter switched off, a perfectly healthy receiver never prints it.
#: Relying on it alone made silent-room receivers look INCONCLUSIVE.
RECV_BANNER: str = "CSI RECV"

#: A receiver that is already streaming is identifiable without a reset.
CSI_ROW: str = "CSI_DATA,"

#: The reliable marker. ESP-IDF logs the project name during start-up, before
#: any application code runs, so it appears whether or not a transmitter is
#: on. This is what identifies a board in an otherwise silent room.
PROJECT_RE = re.compile(r"Project name:\s*(csi_recv|csi_send)")

#: The board's own station MAC, printed by the Wi-Fi driver at boot. This is
#: the durable physical identity, unlike the port name.
STA_MAC_RE = re.compile(r"mode\s*:\s*sta\s*\(([0-9a-fA-F:]{17})\)")

#: Station MAC recovered per port during this run, filled in by
#: :func:`identify` and reported in the summary table.
MACS: dict[str, Optional[str]] = {}


#: Baud rates tried, in order. csi_recv uses 921600; a transmitter left at
#: the ESP-IDF default answers on 115200.
CANDIDATE_BAUDS: tuple[int, ...] = (921600, 115200)


def classify(text: str) -> Optional[str]:
    """Decide which firmware produced some console text.

    Args:
        text: Decoded console output.

    Returns:
        ``"transmitter"``, ``"receiver"``, or ``None`` if undecidable.

    Constraints:
        The boot-time project name is checked first because it is printed
        unconditionally. The application banners are checked only as a
        fallback, since csi_recv prints its banner from inside the CSI
        callback and therefore stays silent while the transmitter is off.
    """
    m = PROJECT_RE.search(text)
    if m:
        return "receiver" if m.group(1) == "csi_recv" else "transmitter"
    if SEND_BANNER in text:
        return "transmitter"
    if RECV_BANNER in text or CSI_ROW in text:
        return "receiver"
    return None


def find_sta_mac(text: str) -> Optional[str]:
    """Extract the board's own station MAC from boot output.

    Args:
        text: Decoded console output.

    Returns:
        The lower-cased MAC, or ``None`` if the banner was not seen.
    """
    m = STA_MAC_RE.search(text)
    return m.group(1).lower() if m else None


def identify_at_baud(port: str, baud: int, timeout_s: float = 4.0) -> tuple[Optional[str], str]:
    """Reset the board and listen at one baud rate.

    Args:
        port: Device path.
        baud: Console baud rate to try.
        timeout_s: How long to listen after the reset.

    Returns:
        A tuple of (verdict or ``None``, the raw text seen, truncated).

    Constraints:
        Read-only apart from the reset pulse; nothing is flashed.
    """
    try:
        import serial
    except ImportError as exc:  # pragma: no cover - environment dependent
        print(f"pyserial not installed ({exc}); pip install pyserial")
        return None, ""
    try:
        ser = serial.Serial(port, baud, timeout=0.2)
    except Exception as exc:  # noqa: BLE001
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
            # Keep reading until the MAC has been seen too. ESP-IDF logs the
            # project name during start-up but the Wi-Fi driver prints the
            # station MAC later, so stopping at the verdict alone loses the
            # one piece of durable board identity this tool exists to report.
            if verdict and find_sta_mac(text):
                break
    finally:
        try:
            ser.close()
        except Exception:  # noqa: BLE001
            pass
    return verdict, buf.decode("utf-8", errors="replace")


def identify(port: str, baud: Optional[int] = None, timeout_s: float = 4.0) -> Optional[str]:
    """Identify the firmware on a port, trying each candidate baud.

    Args:
        port: Device path, e.g. ``/dev/cu.usbserial-0001``.
        baud: A single baud to try, or ``None`` to try
            :data:`CANDIDATE_BAUDS` in order.
        timeout_s: Seconds to listen at each baud after resetting.

    Returns:
        ``"transmitter"``, ``"receiver"``, or ``None`` if nothing
        identifying appeared at any baud.

    Constraints:
        An inconclusive result means exactly that. It must never be reported
        as "transmitter" by elimination, because a receiver whose
        transmitter is switched off is also quiet.
    """
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


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point for ``python -m pipeline.io.identify_board``."""
    p = argparse.ArgumentParser(
        prog="python -m pipeline.io.identify_board",
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
        results[port] = identify(port, args.baud, args.timeout)

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
