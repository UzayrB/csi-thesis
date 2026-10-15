"""ilw_score. The link-weighting run's offline scorer and plumbing checks (`runs/identify/linkweight/PREREG_LW.md`,
section 6): `engine.Session` driven from bank rows in the replay's order (the shipped replay's `te` and `path_used`),
one window at a time, classify then add (as `Engine.poll`), calibration pools per layout as the harness keeps them.

    PYTHONPATH=. python3 -m pipeline.identify.ilw_score plumb-train             # (a) loso_A3_v4's feature components
    PYTHONPATH=. python3 -m pipeline.identify.ilw_score plumb-score --device mps # (b) three sessions against the replays
    PYTHONPATH=. python3 -m pipeline.identify.ilw_score score --model <dir> --session A3 --bank <dir> --device mps

Exploratory development, all data seen.
"""

from __future__ import annotations

import json
import os
import pickle
import sys
import tempfile
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import ilw_cache as LC

T = 4.0
REP = os.path.join(EN.ENG, "replays")
SC = os.path.join(LC.LW, "scores")
PLUMB = os.path.join(LC.LW, "plumb")


def order(session: str) -> dict:
    """The replay harness's order for a session (the shipped loso replay): rows and the paths it used."""
    z = np.load(os.path.join(REP, f"loso_{session}_v4_{session}_T{T:.1f}.npz"))
    return {"te": z["te"], "path_used": z["path_used"]}


def wkey(model_dir: str) -> str:
    a = json.load(open(os.path.join(model_dir, "manifest.json")))["alpha"]
    return "wifi_speed" if a == 0.5 else f"wifi_speed_a{a}"


def score(model_dir: str, session: str, bank_dir: str, device: str = "mps", out: str = None) -> dict:
    X = np.load(os.path.join(bank_dir, "features.npy"))
    maps = pickle.load(open(os.path.join(bank_dir, "maps.pkl"), "rb"))
    meta = json.load(open(os.path.join(bank_dir, "meta.json")))["passes"]
    o = order(session)
    key = wkey(model_dir)
    sess = EN.Session(EN.Model(model_dir, device))
    ens, nop = [], []
    t0 = time.time()
    for i, path in zip(o["te"], o["path_used"]):
        ex = {"features": X[i], "maps": maps[i], "wifi_speed": meta[i][key], "path": str(path),
              "layout": "id_spot" if meta[i]["kind"] == "idcap" else "home"}
        d = sess.classify(ex)
        ens.append(d["ensemble"])
        nop.append(d["ensemble_nopace"])
        sess.add(ex)
    res = {"te": o["te"], "ensemble": np.array(ens), "ensemble_nopace": np.array(nop)}
    if out:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        np.savez(out, **res)
    print(f"{time.strftime('%H:%M:%S')} {os.path.basename(model_dir)} on {session} ({bank_dir}, {key}, {device}): "
          f"{len(ens)} windows in {time.time() - t0:.0f} s", flush=True)
    return res


def plumb_score(device: str = "mps") -> dict:
    """(b): the offline scorer against the existing replays: decisions equal on every walk, log-probabilities within 1e-6."""
    res = {"label": LC.LABEL, "device": device, "cells": {}}
    for model, s in (("loso_A3_v4", "A3"), ("xr_AB_v4", "A3"), ("xr_AB_v4", "B2")):
        z = np.load(os.path.join(REP, f"{model}_{s}_T{T:.1f}.npz"))
        o = order(s)
        assert np.array_equal(z["te"], o["te"]) and np.array_equal(z["path_used"], o["path_used"]), (model, s, "order")
        r = score(os.path.join(EN.ENG, "models", model), s, EN.bank_dir(T), device)
        same = int((r["ensemble"].argmax(1) == z["ensemble"].argmax(1)).sum())
        diff = float(np.abs(r["ensemble"] - z["ensemble"]).max())
        res["cells"][f"{model} {s}"] = {"n": int(len(z["te"])), "same_decision": same, "max_abs_logp_diff": diff,
                                       "PASSED": same == len(z["te"]) and diff <= 1e-6}
        print(f"{model} {s}: {same} of {len(z['te'])} decisions; max |diff| {diff:.2e}", flush=True)
    res["PASSED"] = all(c["PASSED"] for c in res["cells"].values())
    os.makedirs(PLUMB, exist_ok=True)
    json.dump(res, open(os.path.join(PLUMB, "plumb_b.json"), "w"), indent=1)
    print("PASSED" if res["PASSED"] else "FAILED", flush=True)
    return res


def plumb_train() -> dict:
    """(a): loso_A3_v4's five feature components retrained on a bank carrying the shipped speed (V0, built by this run's
    own bank code) reproduce the shipped feat_*.pkl predictions exactly on A3's rows."""
    from pipeline.identify import idw_core as W
    from pipeline.identify import idx_loso as L
    from pipeline.identify import idz_core as Z
    from pipeline.identify import ilw_bank as LB
    bank_dir = os.path.join(PLUMB, "bank_T4.0_v0")
    if not os.path.exists(os.path.join(bank_dir, "meta.json")):
        LB.make_bank(bank_dir, "V0", LB.estimator_speeds("V0"))
    with tempfile.TemporaryDirectory() as d:
        out = LB.retrain("loso_A3_v4", bank_dir, os.path.join(d, "loso_A3_v0"), "V0")
        bank = L.load(EN.bank_dir(T))
        a = bank["a"]
        te = np.flatnonzero(a["session"] == "A3")
        pk = Z.path_key(a, False)
        res = {"label": LC.LABEL, "model": "loso_A3_v4", "rows": int(len(te)), "components": {}}
        for comp, (_h, norm, pace) in W.FEAT.items():
            Xf = Z.feature_matrix(bank, pace, "v2")
            P = []
            for p in (os.path.join(EN.ENG, "models", "loso_A3_v4"), out):
                dd = pickle.load(open(os.path.join(p, f"feat_{comp}.pkl"), "rb"))
                Bm = dd["state"].transform(Xf[te], pk[te]) if norm == "perpath" else dd["state"].apply(Xf, pk, te, None)
                P.append(dd["clf"].predict_proba(Bm))
            res["components"][comp] = bool(np.array_equal(P[0], P[1]))
    res["PASSED"] = all(res["components"].values())
    os.makedirs(PLUMB, exist_ok=True)
    json.dump(res, open(os.path.join(PLUMB, "plumb_a.json"), "w"), indent=1)
    print(json.dumps(res, indent=1), flush=True)
    return res


if __name__ == "__main__":
    what = sys.argv[1]
    arg = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d  # noqa: E731
    if what == "plumb-train":
        sys.exit(0 if plumb_train()["PASSED"] else 1)
    elif what == "plumb-score":
        sys.exit(0 if plumb_score(arg("--device", "mps"))["PASSED"] else 1)
    elif what == "score":
        m, s = arg("--model"), arg("--session")
        score(m, s, arg("--bank"), arg("--device", "mps"),
              out=os.path.join(SC, f"{os.path.basename(m)}_{s}.npz"))
    else:
        raise SystemExit(what)
    sys.exit(0)
