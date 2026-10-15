"""pd_dispend: the display head (DISP_END) for the FINAL model's renders (29 September 2026, QUEUE item 3).

WHAT IT IS. The shipped display draws the dot, after the lock, from a DISPLAY-ONLY head labelled at the
window END (`s2a_dispend`). The only existing one was trained on Room A with the old per-link recipe and
absolute RSSI, and none exists for Room B. This module trains one with the FINAL model's recipe:
  - one shared encoder over the three links, with a learned fusion head (`pd_arch`, fuse);
  - augmentation and relative RSSI (`pd_train` with aug; `pd_cells.install_rrel`);
  - 25 cells, seed 0, 24 epochs;
  - on the A1+A2+B1 walking windows relabelled at the window END by s2a_dispend's own rule
    (`end_labelled_windows`, include_edge False).

TRAINED ON A1+A2+B1 ONLY, as Uzayr asked. It never enters the committed decision, the lock or a
switch decision. It supplies ONE thing: the emissions of the restricted along-line decode that draws
the dot after the lock (and the paths a switch slides to).

    python3 -m pipeline.constrained.pd_dispend train --cell fin_A3             # once; the GPU if free
    python3 -m pipeline.constrained.pd_dispend infer --cell fin_A3             # A3's windows
    python3 -m pipeline.constrained.pd_dispend infer --cell fin_B2             # B2's, the same weights

Everything is written under runs/dc2_results/dispend_final/. Nothing existing is touched.
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
ROOT = J(REPO_ROOT, "runs", "dc2_results", "dispend_final")
TAG = "s0102B1_dispend_final"          #: trained on A1+A2+B1; one set of weights serves A3 and B2
N_CELLS, SEED = 25, 0


def model_file() -> str:
    return J(ROOT, "models", f"{TAG}_g{N_CELLS}_s{SEED}_fuse.pt")


def posterior_file(test: str) -> str:
    return J(ROOT, "posteriors", f"{TAG}_on_{test}_full.npz")


def _setup(cell: str, device: str):
    """Relative RSSI BEFORE the data modules import (pd_cells' own order), then the cell's roots."""
    from pipeline.constrained import pd_cells as PC
    PC.install_rrel()
    if device == "cpu":
        from pipeline.constrained.pd_clean import force_cpu
        force_cpu()
    from pipeline.constrained.pd_clean import _bound
    PC, c, _tfs = _bound(cell)
    return PC, c


def train_inner(cell: str, device: str) -> int:
    t0 = time.time()
    PC, c = _setup(cell, device)
    assert tuple(c["train"]) == ("01", "02", "B1"), f"{cell}: the display head trains on A1+A2+B1 only"
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
    assert sess <= {"01", "02", "B1"}, f"sessions outside A1+A2+B1 in the display head's windows: {sess}"
    for s in c["train"]:
        leak = set(np.asarray(tr.stem).astype(str).tolist()) & PC.cal_stems(s)
        assert not leak, f"calibration recordings among the display head's windows: {leak}"
    X = stack_all(tr.X, tr.rssi)
    y = cell_index(tr.xy, N_CELLS)
    opts = {"aug": True, "rssi_unit": 1.0}
    model, mu, sd, r = fit_link(X, y, "g", N_CELLS, SEED, opts, sessions=tr.session, arch="fuse")
    r.pop("_snapshots", None)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    _save(model, mu, sd, out, {"kind": "g", "out_dim": N_CELLS, "n_links": X.shape[1], "in_channels": X.shape[2],
                               "epochs": r.get("epochs_run"), "seed": SEED, "tag": TAG, "link": 0, "arch": "fuse",
                               "pd_train": r, "labels": "END of the window, not its centre. DISPLAY ONLY."})
    rec = {"tag": TAG, "cell_env": cell, "train": list(c["train"]), "windows": int(len(tr)),
           "by_session": {s: int(np.sum(np.asarray(tr.session).astype(str) == s)) for s in c["train"]},
           "coverage": cov, "opts": opts, "arch": "fuse", "epochs_run": r.get("epochs_run"),
           "device": str(torch.device("mps") if (device != "cpu" and torch.backends.mps.is_available()) else "cpu"),
           "minutes": round((time.time() - t0) / 60.0, 2), "at": time.strftime("%Y-%m-%d %H:%M:%S"),
           "marginal_xy": [list(map(float, q)) for q in np.asarray(tr.xy)]}
    with open(J(ROOT, "train.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f)
    print(f"[{time.strftime('%H:%M:%S')}] DISP_END final: {len(tr)} windows {rec['by_session']}, "
          f"{rec['epochs_run']} epochs, {rec['minutes']} min on {rec['device']}", flush=True)
    return 0


def infer_inner(cell: str, device: str) -> int:
    PC, c = _setup(cell, device)
    PC.install_arch_infer()
    from pipeline.constrained.artefacts import _load, infer_recording
    from pipeline.constrained.recordings import session_recordings
    m = _load(model_file())
    models = [m, m, m]                  # posterior_of reads the shared network from link 0
    b = c["test"]
    out = posterior_file(b)
    if os.path.exists(out):
        raise SystemExit(f"REFUSING to overwrite {out}")
    flat, stems = {}, []
    for _s, stem in session_recordings(b):
        prob, per_link, rec = infer_recording(models, b, stem, "g")
        block = {"prob": prob.astype(np.float32), "per_link": per_link.astype(np.float32),
                 "t0": rec.t0, "t0_epoch": rec.t0_epoch, "mode": rec.mode.astype("U10"),
                 "pass_id": rec.pass_id, "path_name": rec.path_name.astype("U10")}
        for k, v in block.items():
            flat[f"{stem}::{k}"] = v
        stems.append(stem)
    flat["__stems__"] = np.array(sorted(stems), dtype="U64")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    np.savez_compressed(out + ".tmp.npz", **flat)
    os.replace(out + ".tmp.npz", out)
    print(f"[{time.strftime('%H:%M:%S')}] DISP_END final on {b}: {len(stems)} recordings -> {out}", flush=True)
    return 0


def end_emissions(test: str, st, alpha: float) -> dict:
    """{stem: (n, states) emission} of the final display head, scaled by ITS OWN training marginal, as
    s2_display.end_emissions and LiveEndHead build the shipped one."""
    from pipeline.constrained.artefacts import read_full_posteriors
    from pipeline.constrained.emissions import cell_marginal, scaled_cell_emission
    with open(J(ROOT, "train.json"), encoding="utf-8") as f:
        marg = cell_marginal(np.asarray(json.load(f)["marginal_xy"], float), N_CELLS)
    return {stem: scaled_cell_emission(b["prob"].astype(float), st.xy, N_CELLS, marg, alpha=alpha)
            for stem, b in read_full_posteriors(posterior_file(test)).items()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["train", "infer"])
    ap.add_argument("--cell", required=True)
    ap.add_argument("--device", choices=["gpu", "cpu"], default="cpu")
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    if a.inner:
        return (train_inner if a.cmd == "train" else infer_inner)(a.cell, a.device)
    sys.path.insert(0, REPO_ROOT)
    from pipeline.constrained import pd_cells as PC
    c = PC.cfg(a.cell, "decode")
    env = dict(PC.env_for(c, "half", "decode"), PYTHONPATH=REPO_ROOT)
    return subprocess.call([sys.executable, "-m", "pipeline.constrained.pd_dispend", a.cmd, "--inner", "--cell",
                            a.cell, "--device", a.device], cwd=REPO_ROOT, env=env)


if __name__ == "__main__":
    sys.exit(main())
