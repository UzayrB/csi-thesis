"""Run the real CLI in a subprocess with the serial port faked, for signal tests.

Not a test. ``test_shutdown.py`` launches this as a child process and sends
it real signals. Everything inside is the genuine entry point - the real
``run_capture`` with its real signal handlers, the real loop, the real
``finally`` chain, the real ``GroundTruthSession.close()`` - except that the
board on the other end of the port is a stand-in that stays silent.

The stand-in is installed as the ``serial`` module before anything imports
it: ``SerialReader.open()`` imports pyserial lazily, so this is the one seam
where a fake can be placed without touching project code.

Usage::

    python tests/_shutdown_driver.py capture  <args for capture_logger.main>
    python tests/_shutdown_driver.py session  <args for ground_truth.main>
"""

from __future__ import annotations

import os
import sys
import time
import types


class _SilentSerial:
    """Opens like a port, honours the read timeout, never says anything."""

    def __init__(self, port: str, baudrate: int, timeout: float = 0.05, **_: object) -> None:
        self.port, self.baudrate, self.timeout = port, baudrate, timeout
        self.dtr = False
        self.rts = False
        self.is_open = True

    def read(self, n: int = 1) -> bytes:
        time.sleep(self.timeout)
        return b""

    def reset_input_buffer(self) -> None:
        pass

    def close(self) -> None:
        self.is_open = False


fake = types.ModuleType("serial")
fake.Serial = _SilentSerial  # type: ignore[attr-defined]
sys.modules["serial"] = fake

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    which, rest = sys.argv[1], sys.argv[2:]
    if which == "capture":
        from pipeline.io.capture_logger import main
    elif which == "session":
        from pipeline.io.ground_truth import main
    else:
        raise SystemExit(f"unknown target {which!r}")
    sys.exit(main(rest))
