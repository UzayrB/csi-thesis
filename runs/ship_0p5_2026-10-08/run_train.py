"""PLAN.md step 1: train the all-0.5 s heads, one GPU job at a time, under a memory watchdog and caffeinate.

The first job retrains `half` (0.5 s, 25 cells, seed 0) for the deployed model and must be byte-identical to the shipped
file, or nothing else runs. Then the four new deployed heads, then the four new zero-shot heads. Log: logs/train.log.
Start from zsh with `setopt NO_BG_NICE` (see the stride ablation's PLAN addendum of 22:35).
"""

from __future__ import annotations

import filecmp
import os
import re
import subprocess
import sys
import time

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
PY = sys.executable
LOG = J(HERE, "logs", "train.log")
MAX_GB, MIN_FREE = 14.0, 15
TAG = {"fin_A3": "s0102B1_to_s03", "zsf_B2": "s0102_to_sB2"}
#: (cell, slot, cells, training seed, file seed); the first is the recipe check
JOBS = [("fin_A3", "half_check", 25, 0, 0),
        ("fin_A3", "fh1s", 25, 3, 0), ("fin_A3", "g1s1", 25, 1, 1), ("fin_A3", "g1s2", 25, 2, 2),
        ("fin_A3", "g100", 100, 0, 0),
        ("zsf_B2", "fh1s", 25, 3, 0), ("zsf_B2", "g1s1", 25, 1, 1), ("zsf_B2", "g1s2", 25, 2, 2),
        ("zsf_B2", "g100", 100, 0, 0)]


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
    out = subprocess.run(["top", "-l", "1", "-pid", str(pid), "-stats", "mem"], capture_output=True, text=True).stdout
    vals = re.findall(r"^\s*([\d.]+)([KMG])[+-]?\s*$", out, flags=re.M)
    if not vals:
        return 0.0
    num, unit = float(vals[-1][0]), vals[-1][1]
    return num / 1048576 if unit == "K" else num / 1024 if unit == "M" else num


def env_for(cell: str, out: str) -> dict:
    from pipeline.constrained import pd_cells as P
    c = P.cfg(cell)
    e = P.env_for(c, "half", "train")                      # the 0.5 s training view of the cell
    art = J(out, "train")
    os.makedirs(art, exist_ok=True)
    for sub in ("features", "rssi_full"):
        if not os.path.lexists(J(art, sub)):
            os.symlink(J(c["shared"], sub), J(art, sub))
    e.update(TDR_ART_DIR=art, PYTHONPATH=REPO, OMP_NUM_THREADS="1",
             PYTORCH_MPS_HIGH_WATERMARK_RATIO="0.3", PYTORCH_MPS_LOW_WATERMARK_RATIO="0.2")
    return e


def train(cell, slot, cells, seed, file_seed) -> str:
    out = J(HERE, "train", cell, slot)
    if os.path.exists(J(out, "train_net.json")):
        say(f"{cell} {slot}: already trained")
        return out
    os.makedirs(out, exist_ok=True)
    with open(J(out, "train.log"), "a", encoding="utf-8") as log:
        p = subprocess.Popen([PY, J(HERE, "train_head.py"), "--cell", cell, "--cells", str(cells), "--seed", str(seed),
                              "--file-seed", str(file_seed), "--out", out],
                             cwd=REPO, env=env_for(cell, out), stdout=log, stderr=subprocess.STDOUT)
        t0, peak = time.time(), 0.0
        while p.poll() is None:
            fr, gb = free_pct(), footprint_gb(p.pid)
            peak = max(peak, gb)
            if fr < MIN_FREE or gb > MAX_GB:
                p.kill()
                say(f"KILLED {cell} {slot}: free {fr}%, footprint {gb:.1f} GB; stopping")
                raise SystemExit(3)
            time.sleep(10)
    if p.returncode:
        say(f"FAILED {cell} {slot} (exit {p.returncode}); see {out}/train.log; stopping")
        raise SystemExit(p.returncode)
    say(f"{cell} {slot}: trained in {(time.time() - t0) / 60:.1f} min (seed {seed}, file seed {file_seed}, "
        f"{cells} cells), peak footprint {peak:.1f} GB")
    return out


def main() -> int:
    os.makedirs(J(HERE, "logs"), exist_ok=True)
    caf = subprocess.Popen(["caffeinate", "-dimsu", "-w", str(os.getpid())])
    say(f"start: pid {os.getpid()}, caffeinate pid {caf.pid}")
    for cell, slot, cells, seed, fs in JOBS:
        out = train(cell, slot, cells, seed, fs)
        if slot == "half_check":
            from pipeline.constrained import pd_cells as P
            ship = J(P.cfg(cell)["tree"]("half"), "models")
            pairs = [(J(out, "art", "models", f"{TAG[cell]}_g25_e24_s0_link{li}.pt"),
                      J(ship, f"{TAG[cell]}_g25_e24_s0_link{li}.pt")) for li in range(3)]
            same = all(filecmp.cmp(a, b, shallow=False) for a, b in pairs)
            say(f"RECIPE CHECK half: byte-identical to the shipped file: {same}")
            if not same:
                say("stopping: the wrapper does not reproduce the shipped recipe")
                return 2
    say("all heads trained")
    return 0


if __name__ == "__main__":
    sys.exit(main())
