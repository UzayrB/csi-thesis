"""ide_train. The engine's models (`runs/identify/engine/PLAN.md`, section 3), trained on the engine's own bank by
the audit's unchanged trainer (`idz_core.train`: the eight components, columns v2, CNNs 6,000 steps, seeds 0 to
2). The pace column is the bank's Wi-Fi speed; labels, paths and directions are the recorded ones.

    PYTHONPATH=. python3 -m pipeline.identify.ide_train loso_A1 [loso_A2 ...] | T2.5_toB2 | deploy_all5
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idx_loso as L
from pipeline.identify import idz_core as Z
from pipeline.identify import idz_run as ZR

MODELS = os.path.join(EN.ENG, "models")
log = lambda s: print(s, flush=True)  # noqa: E731


def gs_adopted() -> bool:
    """Stage 1's committed decision (PLAN section 1): `runs/identify/engine/stage1/result.json`."""
    return bool(json.load(open(os.path.join(EN.ENG, "stage1", "result.json")))["ADOPT"])


def bank_path(T: float) -> str:
    return os.path.join(EN.ENG, f"bank_T{T:.1f}{'_gs' if gs_adopted() else ''}")


def spec(name: str) -> tuple:
    """(T, the held-out session or None for all five)."""
    if name.startswith("loso_"):
        return 3.0, name.split("_")[1]
    if name.startswith("T"):
        t, fold = name[1:].split("_to")
        return float(t), fold
    if name == "deploy_all5":
        return 3.0, None
    raise ValueError(name)


def train(name: str) -> str:
    T, held = spec(name)
    bp = bank_path(T)
    bank = L.load(bp)
    a = bank["a"]
    tr = np.flatnonzero(a["session"] != held) if held else np.arange(a["n"])
    out = os.path.join(MODELS, name)
    if os.path.exists(os.path.join(out, "meta_feat_cnn.json")):
        log(f"{name}: exists, not retrained")
        return out
    cfg = {"bank": bp, "cols": "v2", "layout": False, "fn": False, "amp_norm": gs_adopted(), "engine_T": T}
    dev = ZR.device()
    log(f"{time.strftime('%H:%M:%S')} engine training {name} ({len(tr)} rows, T {T}, GS {cfg['amp_norm']}) on {dev}")
    Z.train(bank, tr, out, cfg, device=dev, log=log)
    if name == "deploy_all5":
        head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        man = {"model": name, "use": "the rig's deployment model; never used to score anything",
               "trained_on": "every pass of A1, A2, A3, B1, B2 (engine bank)", "n_train": int(len(tr)),
               "bank": bp, "T_s": T, "gs_adopted": cfg["amp_norm"], "config": cfg,
               "engine_parameters": {"T_S": EN.T_S, "CAP_S": EN.CAP_S, "CLOCK_WIN_S": EN.CLOCK_WIN_S, "CLOCK_MIN": EN.CLOCK_MIN,
                                     "CLOCK_PCT": EN.CLOCK_PCT, "LAMBDA": EN.LAMBDA, "F_MIN": EN.F_MIN, "DIR_BAND": EN.DIR_BAND},
               "code_commit_at_training": head, "plan": "runs/identify/engine/PLAN.md", "label": EN.LABEL,
               "built": time.strftime("%Y-%m-%dT%H:%M:%S")}
        json.dump(man, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    return out


if __name__ == "__main__":
    for nm in sys.argv[1:]:
        train(nm)
    sys.exit(0)
