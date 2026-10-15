"""ilp_train. The last push's development fold models (`runs/identify/lastpush/PREREG_LP.md`, section 2): `dev_A1_v4`
(A2 + B1) and `dev_A2_v4` (A1 + B1) with the full v4 recipe of `ixr_train` (registered at run time in its SPECS, the module
itself unchanged), saved to `runs/identify/lastpush/models/`, each under the open-file trace; and the check that
`xr_A_v4`'s five feature components, retrained with its rows, cfg and seeds, reproduce its predictions exactly on B1.

    PYTHONPATH=. python3 -m pipeline.identify.ilp_train train dev_A1 [--device mps]
    PYTHONPATH=. python3 -m pipeline.identify.ilp_train audit dev_A1
    PYTHONPATH=. python3 -m pipeline.identify.ilp_train check-xr-A

Exploratory development, all data seen; selection on A1, A2 and B1 only.
"""

from __future__ import annotations

import json
import os
import pickle
import sys
import tempfile

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import ixr_train as XT

LP = os.path.join("runs", "identify", "lastpush")
MODELS = os.path.join(LP, "models")
LABEL = "exploratory development, all data seen; selection on A1, A2 and B1 only"
DEV = {"dev_A1": {"sessions": ("A2", "B1"), "kinds": ("track", "idcap"), "n": 480, "role": "development fold D1 (tests A1)"},
       "dev_A2": {"sessions": ("A1", "B1"), "kinds": ("track", "idcap"), "n": 480, "role": "development fold D2 (tests A2)"}}
XT.SPECS.update(DEV)                       # run-time registration only; ixr_train.py is not edited


def out_dir(base: str) -> str:
    return os.path.join(MODELS, XT.name_of(base))


def trace(base: str) -> str:
    return os.path.join(LP, "audit", f"{XT.name_of(base)}_open_trace.tsv")


def train(base: str, device: str = "mps") -> str:
    assert not {"A3", "B2"} & set(DEV[base]["sessions"])
    out = XT.train(base, device, out=out_dir(base), trace=trace(base))
    man = json.load(open(os.path.join(out, "manifest.json")))
    man.update({"label": LABEL, "plan": "runs/identify/lastpush/PREREG_LP.md",
                "use": "the last push's development fold only; never scores A3 or B2"})
    json.dump(man, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    return out


def audit(base: str) -> bool:
    os.makedirs(os.path.join(LP, "audit"), exist_ok=True)
    res = XT.audit(base, out_dir=out_dir(base), trace=trace(base), save=False)
    json.dump(res, open(os.path.join(LP, "audit", f"{XT.name_of(base)}_audit.json"), "w"), indent=1)
    return bool(res["PASSED"])


def check_xr_a() -> bool:
    """`xr_A_v4`'s five feature components retrained (its rows, cfg, seeds) reproduce its predictions exactly on B1."""
    from pipeline.identify import idw_core as W
    from pipeline.identify import idx_loso as L
    from pipeline.identify import idz_core as Z
    src = os.path.join(EN.ENG, "models", "xr_A_v4")
    bank = L.load(EN.bank_dir(4.0))
    tr = np.load(os.path.join(src, "train_rows.npy"))
    cfg = json.load(open(os.path.join(src, "meta_feat_cnn.json")))["cfg"]
    te = np.flatnonzero(bank["a"]["session"] == "B1")
    pk = Z.path_key(bank["a"], False)
    res = {"label": LABEL, "model": "xr_A_v4", "rows": int(len(te)), "components": {}}
    with tempfile.TemporaryDirectory() as d:
        Z.train(bank, tr, d, cfg, parts=("feat",), log=lambda s: None)
        for comp, (_h, norm, pace) in W.FEAT.items():
            Xf = Z.feature_matrix(bank, pace, "v2")
            P = []
            for p in (src, d):
                dd = pickle.load(open(os.path.join(p, f"feat_{comp}.pkl"), "rb"))
                Bm = dd["state"].transform(Xf[te], pk[te]) if norm == "perpath" else dd["state"].apply(Xf, pk, te, None)
                P.append(dd["clf"].predict_proba(Bm))
            res["components"][comp] = bool(np.array_equal(P[0], P[1]))
    res["PASSED"] = all(res["components"].values())
    os.makedirs(os.path.join(LP, "checks"), exist_ok=True)
    json.dump(res, open(os.path.join(LP, "checks", "xr_A_v4_feature_reproduction.json"), "w"), indent=1)
    print(json.dumps(res, indent=1), flush=True)
    return res["PASSED"]


if __name__ == "__main__":
    what = sys.argv[1]
    dev = sys.argv[sys.argv.index("--device") + 1] if "--device" in sys.argv else "mps"
    if what == "train":
        train(sys.argv[2], dev)
    elif what == "audit":
        sys.exit(0 if audit(sys.argv[2]) else 1)
    elif what == "check-xr-A":
        sys.exit(0 if check_xr_a() else 1)
    else:
        raise SystemExit(what)
    sys.exit(0)
