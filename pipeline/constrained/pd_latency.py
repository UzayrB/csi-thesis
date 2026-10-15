"""pd_latency: per-window compute of a cell's five heads, for FINAL's latency section.

    python3 -m pipeline.constrained.pd_latency --cells d2pc_ar_0102_to_B1 d4c_fuse_0102_to_B1 --n 200

For each cell, every head's networks are run on single windows exactly as a live system would (one
window, three links, batch 1, on this machine's accelerator), and the time per window is recorded:
feature standardisation, transfer, the forward pass and the softmax, summed over the five heads. The
windows are the first n windows of a DEVELOPMENT recording (A1, participant PA5): timing does not
depend on content, and no test session is read. Median, 95th and 99th percentiles, in milliseconds.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = os.path.join


def inner(cells, n):
    import torch
    from pipeline.constrained import pd_cells as PC
    PC.install_arch_infer()
    import pipeline.constrained.artefacts as A
    import pipeline.constrained.nets as N
    from pipeline.constrained.common import E_POST
    from pipeline.constrained.recordings import load_features, load_meta, load_rssi
    s, stem = "01", "participant_PA5_walk"
    rec = load_meta(s, stem)
    X = np.asarray(load_features(s, stem, np.arange(n)), np.float32)
    R = np.asarray(load_rssi(s, stem, rec.t0_epoch)[:n], np.float32)
    out = {}
    for cell in cells:
        c = PC.cfg(cell)
        heads = []
        for h in c["heads"]:
            for kind, cells_n, seed in PC.HEADS[h][1]:
                if kind != "g":
                    continue
                models = [A._load(J(c["tree"](h), "models", f"{c['heads_tag']}_g{cells_n}_e{E_POST}_s{seed}_link{li}.pt"))
                          for li in range(3)]
                heads.append((h, models))
        for _h, models in heads:                      # warm-up
            for i in range(5):
                N.posterior_of(models, X[i:i + 1], R[i:i + 1], batch=1)
        per_window = []
        for i in range(n):
            t0 = time.perf_counter()
            for _h, models in heads:
                N.posterior_of(models, X[i:i + 1], R[i:i + 1], batch=1)
            if torch.backends.mps.is_available():
                torch.mps.synchronize()
            per_window.append(1000.0 * (time.perf_counter() - t0))
        v = np.asarray(per_window)
        out[cell] = {"heads": [h for h, _m in heads], "n_windows": n, "device": str(N.device()),
                     "ms_median": round(float(np.median(v)), 2), "ms_p95": round(float(np.percentile(v, 95)), 2),
                     "ms_p99": round(float(np.percentile(v, 99)), 2), "ms_max": round(float(v.max()), 2)}
        print(cell, out[cell], flush=True)
    os.makedirs(J(PC.RES, "final"), exist_ok=True)
    with open(J(PC.RES, "final", "latency_heads.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", nargs="+", required=True)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    if a.inner:
        return inner(a.cells, a.n)
    from pipeline.constrained import pd_cells as PC
    env = PC.env_for(PC.cfg(a.cells[0], "infer"), "half", "infer")
    return subprocess.call([sys.executable, "-m", "pipeline.constrained.pd_latency", "--inner", "--n", str(a.n),
                            "--cells", *a.cells], cwd=REPO_ROOT, env=env)


if __name__ == "__main__":
    sys.exit(main())
