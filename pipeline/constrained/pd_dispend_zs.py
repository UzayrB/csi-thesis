"""pd_dispend_zs: the ZERO-SHOT model's display head (DISP_END on A1+A2 only), for the app (30 September 2026).

The final display head (`pd_dispend`, tag s0102B1_dispend_final) was trained on A1+A2+B1. The zero-shot model
may not read B1 anywhere, its display included (rule/APP_PREREG.md). This trains the same head with the same
recipe on A1+A2 only:
  - one shared encoder over the three links with a learned fusion head (`pd_arch`, fuse);
  - augmentation and relative RSSI;
  - 25 cells, seed 0, 24 epochs;
  - the window-END labels of `s2a_dispend.end_labelled_windows` (include_edge False).

It is display-only: it never enters a committed line, a lock or a switch decision.

    python3 -m pipeline.constrained.pd_dispend_zs train      # once; the GPU when Identification's jobs leave it free

It writes only under runs/dc2_results/dispend_zeroshot/.
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
ROOT = J(REPO_ROOT, "runs", "dc2_results", "dispend_zeroshot")
TAG = "s0102_dispend_zeroshot"          #: trained on A1+A2 only
CELL = "zsf_B2"                         #: the zero-shot cell's view (sessions 01, 02; test B2 unread here)
N_CELLS, SEED = 25, 0


def model_file() -> str:
    return J(ROOT, "models", f"{TAG}_g{N_CELLS}_s{SEED}_fuse.pt")


def train_inner() -> int:
    t0 = time.time()
    from pipeline.constrained import pd_cells as PC
    PC.install_rrel()
    from pipeline.constrained.pd_clean import _bound
    PC, c, _tfs = _bound(CELL)
    assert tuple(c["train"]) == ("01", "02"), f"{CELL}: the zero-shot display head trains on A1+A2 only"
    import torch
    from pipeline.constrained.artefacts import _save
    from pipeline.constrained.grid import cell_index
    from pipeline.constrained.pd_arch import stack_all
    from pipeline.constrained.pd_train import fit_link
    from pipeline.constrained.s2a_dispend import end_labelled_windows
    out = model_file()
    if os.path.exists(out):
        raise SystemExit(f"REFUSING to overwrite {out}")
    tr, cov = end_labelled_windows(tuple(c["train"]), with_features=True, include_edge=False)
    sess = set(np.asarray(tr.session).astype(str).tolist())
    assert sess <= {"01", "02"}, f"sessions outside A1+A2 in the zero-shot display head's windows: {sess}"
    X = stack_all(tr.X, tr.rssi)
    y = cell_index(tr.xy, N_CELLS)
    opts = {"aug": True, "rssi_unit": 1.0}
    model, mu, sd, r = fit_link(X, y, "g", N_CELLS, SEED, opts, sessions=tr.session, arch="fuse")
    r.pop("_snapshots", None)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    _save(model, mu, sd, out, {"kind": "g", "out_dim": N_CELLS, "n_links": X.shape[1], "in_channels": X.shape[2],
                               "epochs": r.get("epochs_run"), "seed": SEED, "tag": TAG, "link": 0, "arch": "fuse",
                               "pd_train": r, "labels": "END of the window, not its centre. DISPLAY ONLY. A1+A2 only."})
    rec = {"tag": TAG, "cell_env": CELL, "train": list(c["train"]), "windows": int(len(tr)),
           "by_session": {s: int(np.sum(np.asarray(tr.session).astype(str) == s)) for s in c["train"]},
           "coverage": cov, "opts": opts, "arch": "fuse", "epochs_run": r.get("epochs_run"),
           "device": str(torch.device("mps") if torch.backends.mps.is_available() else "cpu"),
           "minutes": round((time.time() - t0) / 60.0, 2), "at": time.strftime("%Y-%m-%d %H:%M:%S"),
           "marginal_xy": [list(map(float, q)) for q in np.asarray(tr.xy)]}
    with open(J(ROOT, "train.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f)
    print(f"[{time.strftime('%H:%M:%S')}] DISP_END zero-shot: {len(tr)} windows {rec['by_session']}, "
          f"{rec['epochs_run']} epochs, {rec['minutes']} min on {rec['device']}", flush=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["train"])
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    if a.inner:
        return train_inner()
    sys.path.insert(0, REPO_ROOT)
    from pipeline.constrained import pd_cells as PC
    env = dict(PC.env_for(PC.cfg(CELL, "decode"), "half", "decode"), PYTHONPATH=REPO_ROOT, OMP_NUM_THREADS="1")
    return subprocess.call([sys.executable, "-m", "pipeline.constrained.pd_dispend_zs", "train", "--inner"],
                           cwd=REPO_ROOT, env=env)


if __name__ == "__main__":
    sys.exit(main())
