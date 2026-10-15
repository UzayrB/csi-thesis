"""Memory guard for the stride ablation's CPU decodes (8 Oct 2026, added at Uzayr's request: "we can not crash again").

Every 15 s it reads the system free-memory percentage (memory_pressure). Below PAUSE_BELOW it pauses (SIGSTOP) this
ablation's newest running decode, with its child steps, one more per check while memory stays low. Paused decodes
keep their memory but stop growing. At or above RESUME_AT it resumes (SIGCONT) every decode it paused. It only ever
signals processes whose command line is this ablation's eval_one.py or their children. Training has its own watchdog
in run.py (stop below 15 %). Log: logs/mem_guard.log. It exits when the driver named on its command line exits, after
resuming everything it paused.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "logs", "mem_guard.log")
PAUSE_BELOW, RESUME_AT, EVERY_S = 25, 40, 15
MARK = os.path.join(HERE, "eval_one.py")


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
    """[(start order key, pid)] of this ablation's eval_one.py processes, oldest first."""
    out = subprocess.run(["ps", "-A", "-o", "pid=,etime=,command="], capture_output=True, text=True).stdout
    rows = []
    for ln in out.splitlines():
        parts = ln.split(None, 2)
        if len(parts) == 3 and MARK in parts[2] and "mem_guard" not in parts[2]:
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
    say(f"start: driver {driver}, pause below {PAUSE_BELOW} %, resume at {RESUME_AT} %")
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
