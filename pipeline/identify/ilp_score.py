"""ilp_score. The last push's offline scoring with every component saved (`runs/identify/lastpush/PREREG_LP.md`,
sections 2 and 4): `ilw_score`'s scorer (`engine.Session` from bank rows in the replay's order, classify then add, pools per
layout; exact against the replays on mps), keeping the eight components' log-probabilities, the ensemble and the
paths and layouts used, for the development folds' v4 baseline.

    PYTHONPATH=. python3 -m pipeline.identify.ilp_score baseline --device mps     # D1, D2, D3 with v4

Exploratory development, all data seen; selection on A1, A2 and B1 only.
"""

from __future__ import annotations

import json
import os
import pickle
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import ilp_train as LT
from pipeline.identify import ilw_score as LS

T = 4.0
SC = os.path.join(LT.LP, "scores")
FOLDS = {"D1": ("A1", os.path.join(LT.MODELS, "dev_A1_v4")), "D2": ("A2", os.path.join(LT.MODELS, "dev_A2_v4")),
         "D3": ("B1", os.path.join(EN.ENG, "models", "xr_A_v4"))}


def score(model_dir: str, session: str, bank_dir: str = None, device: str = "mps", maps: list = None,
          empty_cache: bool = True) -> dict:
    """Every walk of `session` through one model; `maps` replaces the bank's maps when given (R and W candidates).
    `empty_cache`: on mps, the allocator's cached memory is released after each walk (no number changes; checked on D1
    against the saved baseline, `check-d1`), so a long session's footprint stays inside the 12 GB limit."""
    bank_dir = bank_dir or EN.bank_dir(T)
    X = np.load(os.path.join(bank_dir, "features.npy"))
    maps = maps if maps is not None else pickle.load(open(os.path.join(bank_dir, "maps.pkl"), "rb"))
    meta = json.load(open(os.path.join(bank_dir, "meta.json")))["passes"]
    o = LS.order(session)
    key = LS.wkey(model_dir)
    sess = EN.Session(EN.Model(model_dir, device))
    comps, ens, lay = {}, [], []
    t0 = time.time()
    for i, path in zip(o["te"], o["path_used"]):
        layout = "id_spot" if meta[i]["kind"] == "idcap" else "home"
        ex = {"features": X[i], "maps": maps[i], "wifi_speed": meta[i][key], "path": str(path), "layout": layout}
        d = sess.classify(ex)
        for c, v in d["components"].items():
            comps.setdefault(c, []).append(v)
        ens.append(d["ensemble"])
        lay.append(layout)
        sess.add(ex)
        if empty_cache and device == "mps":
            import torch
            torch.mps.empty_cache()
    print(f"{time.strftime('%H:%M:%S')} {os.path.basename(model_dir)} on {session} ({device}): {len(ens)} windows in "
          f"{time.time() - t0:.0f} s", flush=True)
    return {"te": o["te"], "path_used": o["path_used"], "layout": np.array(lay), "ensemble": np.array(ens),
            **{f"c_{c}": np.array(v) for c, v in comps.items()}}


def baseline(device: str = "mps", only: str = None) -> None:
    os.makedirs(SC, exist_ok=True)
    for f, (s, m) in FOLDS.items():
        if only and f != only:
            continue
        p = os.path.join(SC, f"v4_{f}_{s}.npz")
        if os.path.exists(p):
            print(f"{p} exists", flush=True)
            continue
        np.savez(p, **score(m, s, device=device))


if __name__ == "__main__":
    what = sys.argv[1]
    dev = sys.argv[sys.argv.index("--device") + 1] if "--device" in sys.argv else "mps"
    if what == "baseline":
        baseline(dev, sys.argv[sys.argv.index("--fold") + 1] if "--fold" in sys.argv else None)
    elif what == "check-d1":
        s, m = FOLDS["D1"]
        r = score(m, s, device=dev)
        z = np.load(os.path.join(SC, f"v4_D1_{s}.npz"))
        diff = max(float(np.abs(r[k] - z[k]).max()) for k in z.files if k.startswith("c_") or k == "ensemble")
        res = {"what": "D1 rescored with the per-walk empty_cache against the saved baseline", "device": dev,
               "max_abs_diff": diff, "same_decisions": int((r["ensemble"].argmax(1) == z["ensemble"].argmax(1)).sum()),
               "n": int(len(z["te"]))}
        res["PASSED"] = diff == 0.0 and res["same_decisions"] == res["n"]
        os.makedirs(os.path.join(LT.LP, "checks"), exist_ok=True)
        json.dump(res, open(os.path.join(LT.LP, "checks", "empty_cache_D1.json"), "w"), indent=1)
        print(json.dumps(res, indent=1), flush=True)
        sys.exit(0 if res["PASSED"] else 1)
    else:
        raise SystemExit(what)
    sys.exit(0)
