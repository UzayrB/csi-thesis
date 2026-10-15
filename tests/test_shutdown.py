"""The capture shuts down cleanly on every signal a terminal can send.

Ctrl+C was always handled. SIGTERM (``kill <pid>``) and SIGHUP (the terminal
window closed) were not: their default action ends the interpreter with no
``finally`` at all, so a ground-truth session killed that way would lose its
labels exactly as the missing ``close()`` call did on 9 Sept 2026.

These tests run the REAL CLI as a subprocess - real entry point, real
``run_capture`` with its real handlers, real loop, real ``finally`` - via
``_shutdown_driver.py``, which only swaps the serial port for a silent
stand-in. They then send the process a real signal. No hardware, no skips:
if the process cannot reach its capture loop, that is a failure.
"""

from __future__ import annotations

import glob
import json
import os
import select
import signal
import subprocess
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVER = os.path.join(ROOT, "tests", "_shutdown_driver.py")

#: Printed by run_capture AFTER the port is open and the handlers are
#: installed, immediately before the loop. Seeing it means the signal will
#: land on a running capture, not on start-up or an early exit.
IN_THE_LOOP = "Capturing from"

SIGNALS = [signal.SIGTERM, signal.SIGHUP, signal.SIGINT]


def _launch(target: str, args: list[str]) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, DRIVER, target, *args],
        cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )


def _read_until(proc, marker: str, deadline_s: float) -> str:
    out, fd, t0 = "", proc.stdout.fileno(), time.time()
    while time.time() - t0 < deadline_s:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            chunk = os.read(fd, 65536).decode("utf-8", "replace")
            if not chunk:
                break
            out += chunk
            if marker in out:
                return out
        elif proc.poll() is not None:
            break
    return out


def _drain(proc, seconds: float) -> str:
    out, fd, t0 = "", proc.stdout.fileno(), time.time()
    while time.time() - t0 < seconds:
        r, _, _ = select.select([fd], [], [], 0.2)
        if not r:
            if proc.poll() is not None:
                break
            continue
        chunk = os.read(fd, 65536).decode("utf-8", "replace")
        if not chunk:
            break
        out += chunk
    return out


def _signal_and_collect(proc, sig, settle_s: float) -> str:
    """Wait for the loop, send the signal, insist on a prompt clean exit."""
    out = _read_until(proc, IN_THE_LOOP, 20.0)
    assert IN_THE_LOOP in out, f"never reached the capture loop:\n{out[-1500:]}"
    time.sleep(settle_s)
    assert proc.poll() is None, f"exited before the signal was sent:\n{out[-1500:]}"
    os.kill(proc.pid, sig)
    try:
        proc.wait(timeout=25)
    except subprocess.TimeoutExpired:
        proc.kill()
        pytest.fail(f"{sig.name}: did not exit within 25 s - it would have run until killed")
    out += _drain(proc, 2.0)
    assert proc.returncode not in (-sig, 128 + sig), f"{sig.name} killed the interpreter outright:\n{out[-1500:]}"
    assert "shutting down cleanly" in out, f"{sig.name} did not take the clean path:\n{out[-1500:]}"
    return out


@pytest.mark.parametrize("sig", SIGNALS, ids=[s.name for s in SIGNALS])
def test_capture_finishes_its_shutdown_on_every_stop_signal(tmp_path, sig) -> None:
    """Stop flag set, loop ends, finally runs, the run is written to disk."""
    proc = _launch("capture", ["--nodes", "RX1=/dev/fake0", "--out", str(tmp_path),
                               "--duration", "40", "--expect-hz", "150"])
    try:
        _signal_and_collect(proc, sig, settle_s=1.0)
    finally:
        if proc.poll() is None:
            proc.kill()
    assert glob.glob(os.path.join(str(tmp_path), "*", "run.json")), "run.json was never written"


@pytest.mark.parametrize("sig", SIGNALS, ids=[s.name for s in SIGNALS])
def test_a_ground_truth_session_keeps_its_labels_on_every_stop_signal(tmp_path, sig) -> None:
    """The failure of 9 Sept, provoked on purpose: signal mid-session, sidecar must exist."""
    proc = _launch("session", [
        "--participant", "P01", "--room", "A", "--session", "01", "--mode", "grid",
        "--rx-positions", "RX1=2.5,5.5 RX2=-0.5,2.5 RX3=5.5,2.5",
        "--height-cm", "178", "--weight-kg", "72",
        "--nodes", "RX1=/dev/fake0", "--no-images", "--data-root", str(tmp_path),
    ])
    try:
        out = _signal_and_collect(proc, sig, settle_s=3.5)     # past the 2 s boot settle
    finally:
        if proc.poll() is None:
            proc.kill()

    sidecars = list(tmp_path.glob("room_A/session_01/*.gt.json"))
    assert sidecars, f"{sig.name} lost the ground truth:\n{out[-1500:]}"
    doc = json.loads(sidecars[0].read_text())
    assert doc["aborted"] is True, "a session cut short must not read as complete"
    assert "SESSION ABORTED" in out, "the operator must be told the session did not finish"
