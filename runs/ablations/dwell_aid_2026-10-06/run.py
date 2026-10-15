"""Run the dwell ablation (PLAN.md): train W_k and WD_k in turn on the GPU, decode each finished pair on the CPU.

One GPU job at a time under a memory watchdog with the identification guard's thresholds (stop the job if free
memory falls below 30 % or its footprint passes 6 GB). Decodes run in one CPU worker while the next run trains.
caffeinate holds the machine awake for exactly as long as this process lives. A finished head or decode is never
redone, so the run can be restarted after a stop. Log: logs/run.log.
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))  # runs/ablations/<this folder>
PY = sys.executable
HEADS = ("half", "fh1s", "g1s1", "g1s2", "g100")
JOBS = [(arm, k) for k in range(3) for arm in ("W", "WD")]  # three seed sets (PLAN addendum, 6 Oct 20:12)
LOG = J(HERE, "logs", "run.log")
MAX_GB, MIN_FREE = 18.0, 15  # per-job cap; the system free floor is the real guard (W half peaked 7.7 GB, W+D about double)


def say(m: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def free_pct() -> int:
    out = subprocess.run(["memory_pressure"], capture_output=True, text=True).stdout
    for ln in out.splitlines():
        if "free percentage" in ln:
            return int(ln.split(":")[1].strip().rstrip("%"))
    return 100


def footprint_gb(pid: int) -> float:
    """The job's memory footprint from top's MEM column (for example 1616K, 734M or 1.2G), in GB."""
    import re
    out = subprocess.run(["top", "-l", "1", "-pid", str(pid), "-stats", "mem"], capture_output=True, text=True).stdout
    vals = re.findall(r"^\s*([\d.]+)([KMG])[+-]?\s*$", out, flags=re.M)
    if not vals:
        return 0.0
    num, unit = float(vals[-1][0]), vals[-1][1]
    return num / 1048576 if unit == "K" else num / 1024 if unit == "M" else num


def train_env(head: str, run: str) -> dict:
    sys.path.insert(0, REPO)
    from pipeline.constrained import pd_cells as P
    e = P.env_for(P.cfg("fin_A3"), head, "train")
    art = J(run, f"train_{head}")
    os.makedirs(art, exist_ok=True)
    if head == "half":  # the shipped 0.5 s head's caches resolve (A1, A2 and B1), so read them, read only
        shared = J(REPO, "runs", "dc2_results", "cells", "fin_A3", "train_half")
        for sub in ("features", "rssi_full"):
            if not os.path.exists(J(art, sub)):
                os.symlink(J(shared, sub), J(art, sub))
    else:  # 1 s: features on the fly; one RSSI cache shared by every 1 s run of this ablation
        cache = J(HERE, "cache_1s_rssi_full")
        os.makedirs(cache, exist_ok=True)
        if not os.path.exists(J(art, "rssi_full")):
            os.symlink(cache, J(art, "rssi_full"))
    e.update(TDR_ART_DIR=art, PYTHONPATH=REPO, OMP_NUM_THREADS="1",
             PYTORCH_MPS_HIGH_WATERMARK_RATIO="0.3", PYTORCH_MPS_LOW_WATERMARK_RATIO="0.2")
    return e


def train(arm: str, k: int, head: str, run: str) -> None:
    if os.path.exists(J(run, f"train_{head}.json")):
        say(f"{arm}{k} {head}: already trained")
        return
    log = open(J(run, f"train_{head}.log"), "a", encoding="utf-8")
    p = subprocess.Popen([PY, J(HERE, "train_one.py"), "--arm", arm, "--k", str(k), "--head", head, "--run", run],
                         cwd=REPO, env=train_env(head, run), stdout=log, stderr=subprocess.STDOUT)
    t0, peak = time.time(), 0.0
    while p.poll() is None:
        fr, gb = free_pct(), footprint_gb(p.pid)
        peak = max(peak, gb)
        if fr < MIN_FREE or gb > MAX_GB:
            p.kill()
            say(f"KILLED {arm}{k} {head}: free {fr}%, footprint {gb:.1f} GB; stopping")
            raise SystemExit(3)
        time.sleep(10)
    if p.returncode:
        say(f"FAILED {arm}{k} {head} (exit {p.returncode}); see {run}/train_{head}.log; stopping")
        raise SystemExit(p.returncode)
    say(f"{arm}{k} {head}: trained in {(time.time() - t0) / 60:.1f} min, peak footprint {peak:.1f} GB")


N_DECODERS = 8  # training is finished when this driver starts, so the CPU is free for decoding


def evaluator(q: queue.Queue, errors: list) -> None:
    """One decode worker: takes (arm, k, run, cell) items until it meets None."""
    while True:
        item = q.get()
        if item is None:
            return
        arm, k, run, cell = item
        if os.path.exists(J(run, f"eval_{cell}.json")):
            continue
        t0 = time.time()
        with open(J(run, f"eval_{cell}.log"), "a", encoding="utf-8") as log:
            # training is the critical path, so the decodes yield the fast cores to it
            code = subprocess.call(["nice", "-n", "5", PY, J(HERE, "eval_one.py"), "--cell", cell, "--run", run,
                                    "--k", str(k)],
                                   cwd=REPO, env=dict(os.environ, PYTHONPATH=REPO, OMP_NUM_THREADS="1"),
                                   stdout=log, stderr=subprocess.STDOUT)
        if code:
            errors.append(f"{arm}{k} {cell}")
            say(f"DECODE FAILED {arm}{k} {cell} (exit {code}); see {run}/eval_{cell}.log")
        else:
            say(f"{arm}{k} {cell}: decoded in {(time.time() - t0) / 60:.1f} min")


def queue_run(q: queue.Queue, arm: str, k: int, run: str) -> None:
    for cell in ("fin_A3", "fin_B2"):
        if not os.path.exists(J(run, f"eval_{cell}.json")):
            q.put((arm, k, run, cell))


def main() -> int:
    os.makedirs(J(HERE, "logs"), exist_ok=True)
    caf = subprocess.Popen(["caffeinate", "-dimsu", "-w", str(os.getpid())])
    say(f"start: {len(JOBS)} runs, caffeinate pid {caf.pid}")
    q, errors = queue.Queue(), []
    workers = [threading.Thread(target=evaluator, args=(q, errors), daemon=True) for _ in range(N_DECODERS)]
    for w in workers:
        w.start()
    try:
        for arm, k in JOBS:
            run = J(HERE, "runs", f"{arm}_k{k}")
            os.makedirs(run, exist_ok=True)
            t0 = time.time()
            for head in HEADS:
                train(arm, k, head, run)
            say(f"{arm}{k}: five heads in {(time.time() - t0) / 60:.1f} min; queued for decoding")
            queue_run(q, arm, k, run)
    finally:
        for _ in workers:
            q.put(None)
        for w in workers:
            w.join()
        say(f"done; decode failures: {errors or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
