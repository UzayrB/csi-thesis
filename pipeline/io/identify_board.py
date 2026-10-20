# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Identify which esp-csi firmware is running on a serial port.

from __future__ import annotations

import argparse
import re
import sys
import time
from typing import Optional, Sequence

from pipeline.io.capture_logger import DEFAULT_BAUD, discover_ports, reset_board

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
def identify(port: str, baud: Optional[int] = None, timeout_s: float = 4.0) -> Optional[str]:
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


# Entry point for python -m pipeline.io.identify_board.
def main(argv: Optional[Sequence[str]] = None) -> int:
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
