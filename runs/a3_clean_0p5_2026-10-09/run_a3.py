"""The ONE A3 decode (A3's sixth look), after A3_CLEAN_CONFIG_0p5.md is committed: the six A3 recordings through
a3_replay.py, at most four at a time (nice 10), under mem_guard.py; then the score and the shipped files' hashes after.
Log: a3_lock/logs/driver.log. Each stage is written into runs/MACHINE_STATE.md's log.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PY = sys.executable
L = J(HERE, "a3_lock", "logs")
STEMS = [f"participant_{n}_TEST_walk" for n in ("PA5", "PA1", "PA2", "PA3", "PA4", "PA6")]
ENV = dict(os.environ, PYTHONPATH=REPO, OMP_NUM_THREADS="1")
sys.path.insert(0, HERE)
from run_all import state  # noqa: E402


def say(m: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    with open(J(L, "driver.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main() -> int:
    os.makedirs(L, exist_ok=True)
    assert os.path.exists(J(HERE, "a3_lock", "HASHES_before.json")), "hash the shipped files first"
    say(f"start: pid {os.getpid()}")
    state("A3's sixth look starts: six A3 replays through the live app, at most 4 CPU processes at nice 10 (about 20 min)")
    guard = subprocess.Popen([PY, J(HERE, "mem_guard.py"), str(os.getpid()), "a3"], cwd=REPO, env=ENV)
    todo, codes, lock = list(STEMS), {}, threading.Lock()

    def worker():
        while True:
            with lock:
                if not todo:
                    return
                stem = todo.pop(0)
            say(f"{stem} START")
            with open(J(L, f"{stem}.log"), "a", encoding="utf-8") as f:
                codes[stem] = subprocess.call([PY, J(HERE, "a3_replay.py"), "replay", "--stem", stem], cwd=REPO,
                                              env=ENV, stdout=f, stderr=subprocess.STDOUT)
            say(f"{stem} EXIT {codes[stem]}")
    th = [threading.Thread(target=worker) for _ in range(4)]
    for t in th:
        t.start()
    for t in th:
        t.join()
    guard.terminate()
    if any(codes.values()) or len(codes) != 6:
        say(f"STOP: exits {codes}")
        state(f"Overall: A3 replays STOPPED ({codes}); nothing heavy running")
        return 1
    with open(J(L, "score.log"), "a", encoding="utf-8") as f:
        rc = subprocess.call([PY, J(HERE, "a3_replay.py"), "score"], cwd=REPO, env=ENV, stdout=f, stderr=subprocess.STDOUT)
    say(f"score exit {rc}")
    with open(J(L, "score.log"), "a", encoding="utf-8") as f:
        rc2 = subprocess.call([PY, J(HERE, "a3_replay.py"), "hashes", "--out", J(HERE, "a3_lock", "HASHES_after.json")],
                              cwd=REPO, env=ENV, stdout=f, stderr=subprocess.STDOUT)
    say(f"hashes after exit {rc2}")
    state("A3 replays, score and hashes done; CPU free (Overall's remaining work is light)")
    return rc or rc2


if __name__ == "__main__":
    sys.exit(main())
