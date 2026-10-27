# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Identification development: leave one session out over A1, A2, A3, B1 and B2 on the pass bank (idx_bank).

from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time

import numpy as np

from pipeline.identify import id29_dc2_score as D
from pipeline.identify import idmax_common as IC
from pipeline.identify import idv2_core as C
from pipeline.identify import idx_bank as B

OUT = os.path.join("runs", "identify", "dev", "loso")
SESSIONS = ("A1", "A2", "A3", "B1", "B2")
PATHS = ("A_fwd", "A_rev", "B_fwd", "B_rev", "C_fwd", "C_rev", "D_fwd", "D_rev", "E_col1", "E_col5", "E_row1", "E_row5")



# Function load.
def load(bank: str = B.OUT) -> dict:
    meta = json.load(open(os.path.join(bank, "meta.json")))["passes"]
    X = np.load(os.path.join(bank, "features.npy")).astype(np.float64)
    names = json.load(open(os.path.join(bank, "feature_names.json")))
    maps = pickle.load(open(os.path.join(bank, "maps.pkl"), "rb"))
    a = {k: np.array([m[k] for m in meta]) for k in ("session", "room", "kind", "block", "anon", "path", "t_start", "speed_m_s")}
    a["f_t"] = np.array([m["torso_hz"]["RX2"] for m in meta], float)
    a["n"] = len(meta)
    a["path_idx"] = np.array([PATHS.index(p) for p in a["path"]])
    register_variant("dev", X, names)
    return {"a": a, "X": X, "names": names, "maps": maps, "W": [C.windows(m) for m in maps]}


# Make the bank a feature variant of the frozen idmax_eval, so its column sets select by name.
def register_variant(variant: str, X: np.ndarray, names: list) -> None:
    from pipeline.identify import idmax_eval as E
    parts = [n.split("|") for n in names]
    E._FEAT_CACHE[variant] = {"X": X, "names": names, "fam": np.array([p[0] for p in parts]),
                              "rb": np.array([p[1] for p in parts]), "link": np.array([p[2] for p in parts]),
                              "chan": np.array([p[3] for p in parts]), "nm": np.array([p[4] for p in parts]),
                              "keys": [str(i) for i in range(len(X))]}
    E._MASK_CACHE.clear()


# Function columns.
def columns(fset: str, variant: str = "dev", links: str = "all") -> np.ndarray:
    from pipeline.identify import idmax_eval as E
    return E.columns(E.FConf(variant, fset, "mean@b08_35", links, "pc1-3", "perline_z"))


# The pool passes of the test pass's session that STARTED before it: causal pre-pass data.
def causal_rows(a, te_i: int, pool: np.ndarray) -> np.ndarray:
    s = a["session"][te_i]
    return pool[(a["session"][pool] == s) & (a["t_start"][pool] < a["t_start"][te_i])]



CLASSES = ("P1", "P2", "P3", "P4", "P5", "P6")


# Function order.
def _order(L, cl):
    out = np.full((L.shape[0], 6), np.log(C.HP["prob_floor"]))
    for j, c in enumerate(cl):
        out[:, CLASSES.index(str(c))] = L[:, j]
    return C.normalise_logp(out)


# A feature arm.
def arm_features(bank, tr, te, fset="U_all_gait", head="rf", norm="perpath"):
    from pipeline.identify import idmax_eval as E
    a, X = bank["a"], bank["X"][:, columns(fset)]
    y = a["anon"]
    if norm == "perpath":
        A, Bm = E.prep(X[tr], X[te], a["path"][tr], a["path"][te], "perline_z")
    else:
        A, Bm = session_standardise(a, X, tr, te)
    clf = E.make_model(head).fit(A, y[tr])
    return _order(C.logp_from_proba(clf.predict_proba(Bm)), list(clf.classes_))


# Training passes: z by their own session's statistics.
def session_standardise(a, X, tr, te):
    Xtr, Xte = np.array(X[tr], float), np.array(X[te], float)
    med = np.nanmedian(Xtr, axis=0)
    ok = np.isfinite(med)
    Xall = np.array(X[:, ok], float)
    r, c = np.nonzero(~np.isfinite(Xall))
    Xall[r, c] = med[ok][c]
    keep = Xall[tr].std(0) > 1e-12
    Xall = Xall[:, keep]
    g_mu, g_sd = Xall[tr].mean(0), Xall[tr].std(0) + 1e-9
    A = np.empty((len(tr), Xall.shape[1]))
    for s in np.unique(a["session"][tr]):
        m = a["session"][tr] == s
        mu, sd = Xall[tr][m].mean(0), Xall[tr][m].std(0)
        A[m] = (Xall[tr][m] - mu) / np.where(sd > 1e-9, sd, g_sd)
    Bm = np.empty((len(te), Xall.shape[1]))
    allrows = np.arange(a["n"])
    for k, i in enumerate(te):
        prev = causal_rows(a, i, allrows)
        if len(prev) >= 10:
            mu, sd = Xall[prev].mean(0), Xall[prev].std(0)
            Bm[k] = (Xall[i] - mu) / np.where(sd > 1e-9, sd, g_sd)
        else:
            Bm[k] = (Xall[i] - g_mu) / g_sd
    return A, Bm


# Function arm s0.
def arm_s0(bank, tr, te):
    a = bank["a"]
    P, cl = C.lda_proba(a["speed_m_s"][tr][:, None], a["speed_m_s"][te][:, None], a["anon"][tr])
    return _order(C.logp_from_proba(P), cl)


# Function arm recsig.
def arm_recsig(bank, tr, te):
    from pipeline.identify import idmax_eval as E
    X = bank["X"][:, columns("RECSIG")]
    A, Bm = E.prep(X[tr], X[te], norm="none")
    clf = E.make_model("lda").fit(A, bank["a"]["anon"][tr])
    return _order(C.logp_from_proba(clf.predict_proba(Bm)), list(clf.classes_))


# CNN-v2 on the conditioned maps (v2's architecture and training), the direction input set by the path's...
def arm_cnn(bank, tr, te, seeds=(0,), steps=3000, device="cpu"):
    a, W = bank["a"], bank["W"]
    dirs = np.array([1 if p.endswith("_rev") else 0 for p in a["path"]])

    # Function stack.
    def stack(idx):
        Xs, ds, po = [], [], []
        for k, i in enumerate(idx):
            Xs.append(W[i])
            ds.append(np.full(len(W[i]), dirs[i]))
            po.append(np.full(len(W[i]), k))
        return np.concatenate(Xs), np.concatenate(ds).astype(int), np.concatenate(po).astype(int)
    Xtr, dtr, ptr = stack(tr)
    ytr = np.array([CLASSES.index(v) for v in a["anon"][tr]])[ptr]
    st = C.norm_stats(Xtr, dtr)
    Xtr = C.apply_norm(Xtr, dtr, st)
    Xte, dte, pte = stack(te)
    Xte = C.apply_norm(Xte, dte, st)
    lps = []
    for s in seeds:
        net = C.train_cnn(Xtr, ytr, dtr, 6, s, device, steps)
        lps.append(C.normalise_logp(C.pass_logp(net, Xte, dte, pte, len(te), 6, device)))
    return C.normalise_logp(np.mean(lps, axis=0))


ARMS = {
    "rf_primary": lambda bank, tr, te, **k: arm_features(bank, tr, te, "U_all_gait", "rf", "perpath"),
    "rf_primary_sesnorm": lambda bank, tr, te, **k: arm_features(bank, tr, te, "U_all_gait", "rf", "session_causal"),
    "s0": lambda bank, tr, te, **k: arm_s0(bank, tr, te),
    "recsig": lambda bank, tr, te, **k: arm_recsig(bank, tr, te),
    "cnn_v2": lambda bank, tr, te, **k: arm_cnn(bank, tr, te, **k),
}



# Function score.
def score(bank, te, L, tag, n_boot=1000, n_perm=1000) -> dict:
    a = bank["a"]
    pred = np.array(CLASSES)[L.argmax(1)]
    truth = IC.SealedLabels(a["anon"][te], tag).reveal(pred)
    return D.id_stats([{"tag": tag, "te": list(map(int, te)), "pred": pred.tolist(), "truth": truth.tolist()}],
                      {"anon": a["anon"]}, D.Config(n_boot=n_boot, n_perm=n_perm))


# Function loso.
def loso(bank, arm: str, **kw) -> dict:
    a = bank["a"]
    out, preds = {}, {}
    for s in SESSIONS:
        tr = np.flatnonzero(a["session"] != s)
        te = np.flatnonzero(a["session"] == s)
        L = ARMS[arm](bank, tr, te, **kw)
        preds[s] = {"te": te.tolist(), "pred": np.array(CLASSES)[L.argmax(1)].tolist()}
        res = {"T_tracking": score(bank, te[a["kind"][te] == "track"], L[a["kind"][te] == "track"], f"{arm}|{s}|T")}
        if (a["kind"][te] == "idcap").any():
            m = a["kind"][te] == "idcap"
            res["I_idcap"] = score(bank, te[m], L[m], f"{arm}|{s}|I")
        out[s] = res
    for room in ("A", "B"):
        te = np.concatenate([np.array(preds[s]["te"]) for s in SESSIONS if s[0] == room])
        pr = np.concatenate([np.array(preds[s]["pred"]) for s in SESSIONS if s[0] == room])
        m = a["kind"][te] == "track"
        truth = a["anon"][te][m]
        out[f"room_{room}_T"] = D.id_stats([{"tag": f"{arm}|{room}", "te": list(map(int, te[m])), "pred": pr[m].tolist(),
                                              "truth": truth.tolist()}], {"anon": a["anon"]}, D.Config())
    return out, preds


# Function main.
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--arms", nargs="+", default=["rf_primary", "s0", "recsig"])
    ap.add_argument("--tag", default=time.strftime("%Y%m%dT%H%M%S"))
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0])
    a = ap.parse_args(argv)
    import torch
    torch.set_num_threads(min(4, int(os.environ.get("OMP_NUM_THREADS", "4"))))
    bank = load()
    os.makedirs(OUT, exist_ok=True)
    doc = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "arms": {}}
    for arm in a.arms:
        kw = {"steps": a.steps, "seeds": tuple(a.seeds)} if arm.startswith("cnn") else {}
        t0 = time.time()
        res, preds = loso(bank, arm, **kw)
        doc["arms"][arm] = {"results": res, "preds": preds, "seconds": round(time.time() - t0, 1), "kw": kw}
        print(arm, {s: res[s]["T_tracking"]["acc_pct"] for s in SESSIONS},
              {k: res[k]["acc_pct"] for k in ("room_A_T", "room_B_T")},
              {s: res[s]["I_idcap"]["acc_pct"] for s in ("B1", "B2") if "I_idcap" in res[s]}, flush=True)
    txt = json.dumps(doc, indent=1, default=str)
    assert IC.no_names(txt)
    open(os.path.join(OUT, f"loso_{a.tag}.json"), "w").write(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
