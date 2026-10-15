"""PLAN.md steps 2 and 3 after training: swap the new heads into the new cells, infer the five heads on the GPU (one job at
a time, as the fin cells were inferred, under the memory watchdog), then the FC decode of each new cell on the CPU.
Order: f05_A3, f05_B2 (shares f05_A3's weights), z05_B2. Stops at the first failure. Log: logs/post.log.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)
from run_train import footprint_gb, free_pct  # noqa: E402

PY = sys.executable
LOG = J(HERE, "logs", "post.log")
CELLS = ("f05_A3", "f05_B2", "z05_B2")


def say(m: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def guarded(cmd, env, log_path, what) -> None:
    with open(log_path, "a", encoding="utf-8") as log:
        p = subprocess.Popen(cmd, cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT)
        t0, peak = time.time(), 0.0
        while p.poll() is None:
            fr, gb = free_pct(), footprint_gb(p.pid)
            peak = max(peak, gb)
            if fr < 15 or gb > 14:
                p.kill()
                say(f"KILLED {what}: free {fr}%, footprint {gb:.1f} GB; stopping")
                raise SystemExit(3)
            time.sleep(5)
    if p.returncode:
        say(f"FAILED {what} (exit {p.returncode}); see {log_path}; stopping")
        raise SystemExit(p.returncode)
    say(f"{what}: done in {(time.time() - t0) / 60:.1f} min, peak {peak:.1f} GB")


def main() -> int:
    from pipeline.constrained import pd_cells as P
    caf = subprocess.Popen(["caffeinate", "-dimsu", "-w", str(os.getpid())])
    say(f"start: pid {os.getpid()}, caffeinate {caf.pid}")
    base_env = dict(os.environ, PYTHONPATH=REPO, OMP_NUM_THREADS="1",
                    PYTORCH_MPS_HIGH_WATERMARK_RATIO="0.3", PYTORCH_MPS_LOW_WATERMARK_RATIO="0.2")
    for cell in CELLS:
        c = P.cfg(cell)
        if not os.path.exists(J(c["base"], "SWAPPED_0p5.json")):
            guarded([PY, J(HERE, "build_cells.py"), "swap", cell], base_env, J(HERE, "logs", f"swap_{cell}.log"),
                    f"{cell} swap")
        for h in c["heads"]:
            out = J(c["tree"](h), "posteriors", f"{c['heads_tag']}_g{100 if h == 'g100' else 25}_e24_s"
                    f"{ {'half': 0, 'fh1s': 0, 'g1s1': 1, 'g1s2': 2, 'g100': 0}[h] }_full.npz")
            if os.path.exists(out):
                say(f"{cell} infer {h}: already done")
                continue
            env = dict(P.env_for(c, h, "infer"), PYTHONPATH=REPO, OMP_NUM_THREADS="1",
                       PYTORCH_MPS_HIGH_WATERMARK_RATIO="0.3", PYTORCH_MPS_LOW_WATERMARK_RATIO="0.2")
            guarded([PY, "-m", "pipeline.constrained.pd_cells", "infer", "--cell", cell, "--head", h], env,
                    J(HERE, "logs", f"infer_{cell}.log"), f"{cell} infer {h}")
        if not os.path.exists(J(c["base"], "d3", "FC.relgateU+abstain+a2w0.25")):
            guarded([PY, J(HERE, "build_cells.py"), "decode", cell], base_env, J(HERE, "logs", f"decode_{cell}.log"),
                    f"{cell} FC decode")
    say("all three cells swapped, inferred and decoded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
