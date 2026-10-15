"""Memory guard for this folder's lock-side decodes (8 Oct 2026, at Uzayr's request: "we can not crash again").

The stride ablation's `mem_guard.py`, pointed at this folder. Every 15 s it reads the system free-memory percentage
(memory_pressure). Below PAUSE_BELOW it pauses (SIGSTOP) the newest running `lock_side.py decode` process of this folder,
with its children, one more per check while memory stays low. At or above RESUME_AT it resumes (SIGCONT) every process it
paused. It only ever signals processes whose command line names this folder's lock_side.py, and their children. Log:
lock/logs/mem_guard.log. It exits when the driver named on its command line exits, after resuming everything it paused.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "lock", "logs", "mem_guard.log")
PAUSE_BELOW, RESUME_AT, EVERY_S = 25, 40, 15
#: the processes it may signal: this folder's lock_side.py decodes, or (second argument "a3") its a3_replay.py replays
MARKS = {"lock": "a3_clean_0p5_2026-10-09/lock_side.py decode", "a3": "a3_clean_0p5_2026-10-09/a3_replay.py replay"}
MARK = MARKS[sys.argv[2]] if len(sys.argv) > 2 else MARKS["lock"]


def say(m: str) -> None:
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {m}\n")


def free_pct() -> int:
    out = subprocess.run(["memory_pressure"], capture_output=True, text=True).stdout
    for ln in out.splitlines():
        if "free percentage" in ln:
            return int(ln.split(":")[1].strip().rstrip("%"))
    return 100


def decodes() -> list:
    """PIDs of this folder's outer `lock_side.py decode` processes (not --inner: their children)."""
    out = subprocess.run(["ps", "-A", "-o", "pid=,command="], capture_output=True, text=True).stdout
    rows = []
    for ln in out.splitlines():
        parts = ln.split(None, 1)
        if len(parts) == 2 and MARK in parts[1] and "--inner" not in parts[1] and "mem_guard" not in parts[1]:
            rows.append(int(parts[0]))
    return rows


def tree(pid: int) -> list:
    kids = subprocess.run(["pgrep", "-P", str(pid)], capture_output=True, text=True).stdout.split()
    out = [pid]
    for k in kids:
        out += tree(int(k))
    return out


def signal_tree(pid: int, sig) -> None:
    for p in tree(pid):
        try:
            os.kill(p, sig)
        except ProcessLookupError:
            pass


def main() -> int:
    driver = int(sys.argv[1])
    paused = []
    say(f"start: driver {driver}, watching {decodes()}, pause below {PAUSE_BELOW} %, resume at {RESUME_AT} %")
    while True:
        alive = subprocess.run(["ps", "-p", str(driver)], capture_output=True).returncode == 0
        fr = free_pct()
        paused = [p for p in paused if subprocess.run(["ps", "-p", str(p)], capture_output=True).returncode == 0]
        if not alive:
            for p in paused:
                signal_tree(p, signal.SIGCONT)
            say(f"driver gone; resumed {paused}; exit")
            return 0
        if fr < PAUSE_BELOW:
            running = [p for p in decodes() if p not in paused]
            if running:
                p = max(running)  # the newest decode
                signal_tree(p, signal.SIGSTOP)
                paused.append(p)
                say(f"free {fr} %: paused decode {p} (now paused: {paused})")
        elif fr >= RESUME_AT and paused:
            for p in paused:
                signal_tree(p, signal.SIGCONT)
            say(f"free {fr} %: resumed {paused}")
            paused = []
        time.sleep(EVERY_S)


if __name__ == "__main__":
    sys.exit(main())
