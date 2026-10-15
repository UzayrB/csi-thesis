"""idw_run. The identification-walks brief: train one training set for one fold (once, saved), then score
the test day's identification passes under the three calibration settings (PLAN.md sections 2 to 4).

    PYTHONPATH=. python3 -m pipeline.identify.idw_run --set TR-B --fold toB2 [--direction away] [--extra]

Outputs: `runs/identify/idwalks/models/<name>/` (the trained components) and
`runs/identify/idwalks/outputs/<name>_<cal>.npz` (test rows, every component's log-probabilities, the
ensemble, the ensemble without the pace components, and S0).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

from pipeline.identify import idmax_common as IC
from pipeline.identify import idw_core as W
from pipeline.identify import idx_loso as L

OUTPUTS = os.path.join("runs", "identify", "idwalks", "outputs")
SETS = ("TR-B", "TR-B+", "TR-AB")
TEST = {"toB2": "B2", "toB1": "B1"}
DIRPATH = {"away": "A_fwd", "towards": "A_rev"}


def train_rows(a, set_, fold, direction=None) -> np.ndarray:
    test = TEST[fold]
    other = "B1" if test == "B2" else "B2"
    idc = (a["session"] == other) & (a["kind"] == "idcap")
    if direction:
        idc &= a["path"] == DIRPATH[direction]
    if set_ == "TR-B":
        m = idc
    elif set_ == "TR-B+":
        m = idc | ((a["session"] == other) & (a["kind"] == "track"))
    elif set_ == "TR-AB":
        m = idc | ((a["session"] != test) & (a["kind"] == "track"))
    else:
        raise ValueError(set_)
    assert not np.any(a["session"][m] == test)
    return np.flatnonzero(m)


def test_rows(a, fold) -> np.ndarray:
    return np.flatnonzero((a["session"] == TEST[fold]) & (a["kind"] == "idcap"))


def name_of(set_, fold, direction=None, extra=False) -> str:
    return f"{set_}{'-' + direction if direction else ''}{'-X' if extra else ''}_{fold}"


def run(set_, fold, direction=None, extra_path=None, steps=6000, seeds=(0, 1, 2)) -> None:
    bank = L.load()
    a = bank["a"]
    extra = np.load(extra_path) if extra_path else None
    name = name_of(set_, fold, direction, extra is not None)
    tr, te = train_rows(a, set_, fold, direction), test_rows(a, fold)
    mdir = os.path.join(W.MODELS, name)
    log = lambda s: print(s, flush=True)  # noqa: E731
    device = W.wait_for_tracking(log)
    if not os.path.exists(os.path.join(mdir, "meta.json")):
        log(f"{time.strftime('%H:%M:%S')} training {name}: {len(tr)} rows, device {device}")
        W.train(bank, tr, mdir, seeds=seeds, steps=steps, device=device, extra=extra, log=log)
    else:
        log(f"{time.strftime('%H:%M:%S')} {name}: saved models found, not retrained")
    device = W.wait_for_tracking(log)
    tr_idc = tr[a["kind"][tr] == "idcap"]
    s0 = W.s0(bank, np.flatnonzero((a["session"] == ("B1" if TEST[fold] == "B2" else "B2")) & (a["kind"] == "idcap")), te)
    os.makedirs(OUTPUTS, exist_ok=True)
    for cal in ("others", "causal", "none"):
        t0 = time.time()
        out = W.apply(bank, mdir, te, W.calibration_groups(a, te, cal), device=device, extra=extra)
        np.savez(os.path.join(OUTPUTS, f"{name}_{cal}.npz"), te=te, s0=s0, **out)
        acc = float(np.mean(np.array(L.CLASSES)[out["ensemble"].argmax(1)] == a["anon"][te]))
        log(f"{time.strftime('%H:%M:%S')} {name} {cal}: scored {len(te)} passes in {time.time() - t0:.0f} s "
            f"(all paces, both directions: {100 * acc:.2f})")
    meta = {"name": name, "set": set_, "fold": fold, "direction": direction, "extra": extra is not None,
            "n_train": int(len(tr)), "n_train_idcap": int(len(tr_idc)), "n_test": int(len(te)),
            "built": time.strftime("%Y-%m-%dT%H:%M:%S")}
    txt = json.dumps(meta, indent=1)
    assert IC.no_names(txt)
    open(os.path.join(OUTPUTS, f"{name}.json"), "w").write(txt)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--set", required=True, choices=SETS)
    ap.add_argument("--fold", required=True, choices=tuple(TEST))
    ap.add_argument("--direction", choices=tuple(DIRPATH))
    ap.add_argument("--extra", help="the gated arm's extra feature matrix (.npy, one row per bank pass)")
    ap.add_argument("--steps", type=int, default=6000)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    a = ap.parse_args(argv)
    run(a.set, a.fold, a.direction, a.extra, a.steps, tuple(a.seeds))
    return 0


if __name__ == "__main__":
    sys.exit(main())
