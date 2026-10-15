"""ixa_inner. The extras brief's candidate A4 (`runs/identify/engine/PLAN.md`, the extras note): the inner
leave-one-session-out loop inside each outer fold, to learn the engine's lean towards some people from the
training days only.

For an outer fold (a held-out test session), each of its training sessions is held out in turn: the full engine
(the current best configuration, `idz_core.train`, CNNs included) is trained on the other training sessions and
the held-out one is replayed through the engine exactly as the outer evaluation does (`ide_replay.replay`,
causal). Inner training sets shared between outer folds are trained once.

    PYTHONPATH=. python3 -m pipeline.identify.ixa_inner train <set> ...      # e.g. A2A3B1
    PYTHONPATH=. python3 -m pipeline.identify.ixa_inner replay <set> <session> [--device mps]
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import ide_replay as RP
from pipeline.identify import idx_loso as L
from pipeline.identify import idz_core as Z
from pipeline.identify import idz_run as ZR

OUT = os.path.join("runs", "identify", "final_extras", "a4")
BANK = os.path.join(EN.ENG, "bank_T3.0")
SESS = ("A1", "A2", "A3", "B1", "B2")
log = lambda s: print(s, flush=True)  # noqa: E731


def sessions_of(name: str) -> list:
    return [name[i:i + 2] for i in range(0, len(name), 2)]


def inner_plan(outer: str) -> list:
    """[(training-set name, held-out inner session)] for an outer test session."""
    train = [s for s in SESS if s != outer]
    return [("".join(s for s in train if s != h), h) for h in train]


def model_dir(name: str) -> str:
    return os.path.join(OUT, "models", f"inner_{name}")


def train(name: str) -> str:
    out = model_dir(name)
    if os.path.exists(os.path.join(out, "meta_feat_cnn.json")):
        log(f"{name}: exists")
        return out
    bank = L.load(BANK)
    a = bank["a"]
    tr = np.flatnonzero(np.isin(a["session"], sessions_of(name)))
    cfg = {"bank": BANK, "cols": "v2", "layout": False, "fn": False, "amp_norm": False, "engine_T": 3.0}
    dev = ZR.device()
    log(f"{time.strftime('%H:%M:%S')} inner training {name} ({len(tr)} rows) on {dev}")
    Z.train(bank, tr, out, cfg, device=dev, log=log)
    json.dump({"model": f"inner_{name}", "training_sessions": sessions_of(name), "n_train": int(len(tr)), "bank": BANK,
               "purpose": "A4 inner loop (extras brief); never scores a test day"},
              open(os.path.join(out, "manifest.json"), "w"), indent=1)
    return out


def replay(name: str, session: str, device: str = "mps") -> str:
    """The held-out inner session through the engine with the inner model; saves every component's output."""
    assert session not in sessions_of(name)
    p = os.path.join(OUT, "replays", f"inner_{name}_{session}.npz")
    if os.path.exists(p):
        return p
    bank = RP.load_bank(3.0, False)
    t0 = time.time()
    dec = RP.replay(session, model_dir(name), 3.0, False, device, RP.direction_mode())
    rows = np.array([bank["index"][(session, round(d["t0"], 6))] for d in dec])
    feq = np.array([np.array_equal(d["extraction"]["features"], bank["X"][i], equal_nan=True) for d, i in zip(dec, rows)])
    comps = {f"c_{c}": np.array([d["components"][c] for d in dec]) for c in dec[0]["components"]}
    os.makedirs(os.path.dirname(p), exist_ok=True)
    np.savez(p, te=rows, ensemble=np.array([d["ensemble"] for d in dec]), confidence=np.array([d["confidence"] for d in dec]),
             calib_n=np.array([d["calib_n"] for d in dec]), path_used=np.array([d["extraction"]["path"] for d in dec]),
             features_equal_bank=feq, **comps)
    log(f"{time.strftime('%H:%M:%S')} inner replay {name} -> {session}: {len(dec)} windows, features equal {int(feq.sum())}, "
        f"{time.time() - t0:.0f} s")
    return p


if __name__ == "__main__":
    if sys.argv[1] == "train":
        for nm in sys.argv[2:]:
            train(nm)
    elif sys.argv[1] == "replay":
        dev = sys.argv[4] if len(sys.argv) > 4 else "mps"
        replay(sys.argv[2], sys.argv[3], dev)
    sys.exit(0)
