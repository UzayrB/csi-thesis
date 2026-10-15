"""ADDENDUM.md, start to SELECTION.json, in order; any failure stops the run and is logged (logs/run_all.log).

  1. plumbing: build_rot.py plumb on the three rotations (three CPU processes, nice 10); all three must be EXACT
  2. swap and infer, one rotation at a time (the GPU, one inference at a time)
  3. the D05 reference decodes (three CPU processes, nice 10)
  4. the 32-arm lock-side grid, four lanes (nice 10): lane r runs the shipped arm and 23 more on rotation r; lane 4
     waits until all three shipped arms have passed, then runs the last 8 arms of each rotation. mem_guard.py pauses the
     newest decode below 25 % free memory.
  5. lock_side.py score: lock/SELECTION.json

Each stage is written into runs/MACHINE_STATE.md's log as it starts and ends. Nothing here touches A3.
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
LOG = J(HERE, "logs", "run_all.log")
STATE = J(REPO, "runs", "MACHINE_STATE.md")
ROTS = ("B1", "A2", "A1")
sys.path.insert(0, HERE)
from lock_side import GRID, OUT  # noqa: E402

ENV = dict(os.environ, PYTHONPATH=REPO, OMP_NUM_THREADS="1")
#: --grid-only resumes at stage 4 (stages 1 to 3 done; 9 Oct 07:18 the grid stopped on a registration check's order)
GRID_ONLY = "--grid-only" in sys.argv
stop = threading.Event()
live: list = []


def say(m: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def state(m: str) -> None:
    """One line at the top of MACHINE_STATE.md's log."""
    with open(STATE, encoding="utf-8") as f:
        s = f.read()
    s = s.replace("## Log\n\n", f"## Log\n\n- 09 Oct {time.strftime('%H:%M')}: {m}\n", 1)
    with open(STATE, "w", encoding="utf-8") as f:
        f.write(s)


def call(args: list, log: str) -> int:
    with open(J(HERE, "logs", log), "a", encoding="utf-8") as f:
        p = subprocess.Popen(args, cwd=REPO, env=ENV, stdout=f, stderr=subprocess.STDOUT)
        live.append(p)
        rc = p.wait()
    return rc


def parallel(stage: str, jobs: list) -> None:
    """jobs: (name, args, log). All must exit 0."""
    out = {}

    def one(name, args, log):
        out[name] = call(args, log)
    th = [threading.Thread(target=one, args=j) for j in jobs]
    for t in th:
        t.start()
    for t in th:
        t.join()
    bad = {k: v for k, v in out.items() if v}
    if bad:
        say(f"STOP at {stage}: exits {out}")
        state(f"Overall run STOPPED at {stage} ({bad}); nothing heavy running")
        raise SystemExit(1)
    say(f"{stage}: done {out}")


def lane(name: str, work: list, wait_for: list = ()) -> None:
    while wait_for and not stop.is_set():
        if all(os.path.exists(p) for p in wait_for):
            break
        time.sleep(20)
    for rot, arms in work:
        if stop.is_set():
            return
        say(f"lane {name}: {rot} {len(arms)} arms start")
        rc = call([PY, J(HERE, "lock_side.py"), "decode", "--rot", rot, "--arms", *arms], f"lock_{name}.log")
        say(f"lane {name}: {rot} exit {rc}")
        if rc:
            stop.set()
            for p in live:
                if p.poll() is None:
                    p.terminate()
            return


def main() -> int:
    os.makedirs(J(HERE, "logs"), exist_ok=True)
    say(f"start: pid {os.getpid()}{' (grid only)' if GRID_ONLY else ''}")
    t0 = time.time()
    if not GRID_ONLY:
        stages_1_to_3()
    run_grid(t0)
    return 0


def stages_1_to_3() -> None:
    state("plumbing decodes of the three f05r cells start (3 CPU processes, nice 10, about 10 min)")
    parallel("plumbing", [(r, [PY, J(HERE, "build_rot.py"), "plumb", r], f"plumb_{r}.out") for r in ROTS])
    state("plumbing EXACT on all three; swap and GPU inference start (one at a time, about 6 min)")
    for r in ROTS:
        for cmd in ("swap", "infer"):
            rc = call([PY, J(HERE, "build_rot.py"), cmd, r], f"{cmd}_{r}.out")
            if rc:
                say(f"STOP at {cmd} {r}: exit {rc}")
                state(f"Overall run STOPPED at {cmd} {r}; nothing heavy running")
                raise SystemExit(1)
    say("swap and infer: done")
    state("GPU inference done (GPU free); D05 reference decodes start (3 CPU processes, nice 10)")
    parallel("reference", [(r, [PY, J(HERE, "build_rot.py"), "ref", r], f"ref_{r}.out") for r in ROTS])


def run_grid(t0: float) -> None:
    state("lock-side grid starts: 96 decodes in 4 lanes (4 CPU processes, nice 10, about 2 h)")
    guard = subprocess.Popen([PY, J(HERE, "mem_guard.py"), str(os.getpid()), "lock"], cwd=REPO, env=ENV)
    os.makedirs(J(OUT, "logs"), exist_ok=True)
    shipped = [J(OUT, "decodes", r, GRID[0], "arm.json") for r in ROTS]
    th = [threading.Thread(target=lane, args=(r, [(r, GRID[:24])])) for r in ROTS]
    th.append(threading.Thread(target=lane, args=("L4", [(r, GRID[24:]) for r in ROTS], shipped)))
    for t in th:
        t.start()
    for t in th:
        t.join()
    if stop.is_set():
        say("STOP in the lock-side grid; see the lane logs")
        state("Overall run STOPPED in the lock-side grid; nothing heavy running")
        guard.terminate()
        raise SystemExit(1)
    guard.terminate()
    rc = call([PY, J(HERE, "lock_side.py"), "score"], "score.out")
    say(f"score exit {rc}; {(time.time() - t0) / 60:.1f} min in all")
    state(f"lock-side selection done (score exit {rc}); CPU free, Overall's next step is light (config, then one A3 replay)")
    if rc:
        raise SystemExit(rc)


if __name__ == "__main__":
    sys.exit(main())
