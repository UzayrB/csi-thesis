"""ils_feat. The lever screen's feature side (PLAN note 2026-10-01 17:18): the five feature components retrained on a
lever's inputs with `idz_core.train`'s feature arithmetic (`ixa_score.train_feat`), and each walks fold's session
re-scored in replay order with causal calibration as `engine.Session.classify` does. Anchor A-F: the engine's own
configuration must reproduce the replays' feature components (1e-9) and every decision.

A configuration `cfg` (every key optional; {} is the engine):
    cols      "rx2" | "rx23"            the 630 columns by receiver (with the 3 cross-link step-rate columns)
    families  "no_rhy_tpl" | "dop_spec_wav_mod"
    seed      random_state of the RF and ET heads (the engine: 0)
    lda       ("shrink", 0.7) | ("shrink", 0.9) | ("logreg", 0.01) | "drop"
    weight    2 | 4                     the matched rows (the other Room B day's identification walks) repeated
    rows      "matched"                 train on the matched rows only
    std       "id_layout" | "perpath" | "global" | "nopath"   (Tier 2.5 a to d; training and test sides)
    pool      "layout"                  test side only: calibrate on earlier windows of the same layout (fix L)
    G         an alternative (1019, 630) gait matrix (fix F's re-extracted bank)
    pace      an alternative (1019,) pace column (the window and gait brief's per-arm Wi-Fi speed)
    nopace    True: no pace column in any component
    extra     a (1019, k) matrix of added columns, after the column mask (the window and gait brief's Part B)
    colidx    explicit column indices into the 630 (the lean-in brief's stable-feature and placement-robust levers)

Development evaluation, all data seen. A screen: the engine does not change.
"""

from __future__ import annotations

import os
import re
import sys
import time

import numpy as np

from pipeline.identify import idv2_core as C
from pipeline.identify import idw_core as W
from pipeline.identify import idx_loso as L
from pipeline.identify import ils_common as IL


def column_mask(gnames: list, cfg: dict) -> np.ndarray:
    if cfg.get("colidx") is not None:                 # an explicit subset of the 630 (the lean-in brief's levers)
        return np.asarray(cfg["colidx"], int)
    keep = np.ones(len(gnames), bool)
    links = [set(re.findall(r"RX[123]", n)) for n in gnames]
    if cfg.get("cols") == "rx2":
        keep &= np.array([not lk or lk == {"RX2"} for lk in links])
    elif cfg.get("cols") == "rx23":
        keep &= np.array([not lk or lk <= {"RX2", "RX3"} for lk in links])
    fam = np.array([n.split("|")[0] for n in gnames])
    if cfg.get("families") == "no_rhy_tpl":
        keep &= ~np.isin(fam, ["rhy", "tplacf"])
    elif cfg.get("families") == "dop_spec_wav_mod":
        keep &= np.isin(fam, ["dop", "spec", "wav", "mod"])
    return np.flatnonzero(keep)


class Global(W.Prior):
    """Tier 2.5c: the global training statistics on both sides; no session, no path."""

    def fit(self, Xtr, ptr, str_):
        super().fit(Xtr, ptr, str_)
        return (self.Z(Xtr) - self.g_mu) / self.g_sd

    def apply(self, Xall, paths, rows, calib):
        return (self.Z(Xall[rows]) - self.g_mu) / self.g_sd


def head(name: str, cfg: dict):
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    from sklearn.linear_model import LogisticRegression
    from pipeline.identify import idmax_eval as E
    if name == "lda" and isinstance(cfg.get("lda"), tuple):
        kind, v = cfg["lda"]
        if kind == "shrink":
            return LinearDiscriminantAnalysis(solver="lsqr", shrinkage=v)
        return LogisticRegression(C=v, max_iter=5000)
    return E.make_model(name, seed=cfg.get("seed", 0))


def feat_components(cfg: dict) -> tuple:
    return tuple(c for c in IL.FEATC if not (c == "lda_pace_prior" and cfg.get("lda") == "drop"))


def _groups(d, rows, cfg):
    s = d["a"]["session"][rows]
    if cfg.get("std") == "id_layout":
        s = np.char.add(np.char.add(s.astype(str), "|"), d["a"]["layout"][rows].astype(str))
    return s


def _paths(p, cfg):
    return np.full(len(p), "-") if cfg.get("std") == "nopath" else p


def train(d: dict, fold: str, cfg: dict) -> dict:
    """The feature components for one walks fold (`fold` is the replayed session; training rows are its model's)."""
    a = d["a"]
    G = (cfg["G"] if "G" in cfg else d["G"])[:, column_mask(d["gnames"], cfg)]
    if cfg.get("extra") is not None:
        G = np.c_[G, cfg["extra"]]
    pace_col = cfg["pace"] if cfg.get("pace") is not None else a["wifi_speed"]
    tr = d["tr"][fold]
    matched = tr[a["kind"][tr] == "idcap"]
    rows = matched if cfg.get("rows") == "matched" else tr
    out = {}
    for comp in feat_components(cfg):
        hname, norm, pace = W.FEAT[comp]
        pace = pace and not cfg.get("nopace")
        M = np.c_[G, pace_col] if pace else G
        p, y = a["path"][rows], a["anon"][rows]
        if norm == "perpath" or cfg.get("std") == "perpath":
            st = W.PerPath().fit(M[rows], p)
            A = st.transform(M[rows], p)
            kind = "perpath"
        else:
            st = Global() if cfg.get("std") == "global" else W.Prior()
            A = st.fit(M[rows], _paths(p, cfg), _groups(d, rows, cfg))
            kind = "prior"
        w = int(cfg.get("weight", 1))
        if w > 1:
            extra = np.flatnonzero(np.isin(rows, matched))
            A = np.vstack([A] + [A[extra]] * (w - 1))
            y = np.concatenate([y] + [y[extra]] * (w - 1))
        clf = head(hname, cfg).fit(A, y)
        out[comp] = {"state": st, "clf": clf, "classes": list(clf.classes_), "kind": kind, "pace": pace}
    out["_G"] = G
    out["_pace"] = pace_col
    return out


def rescore(models: dict, d: dict, s: str, cfg: dict) -> dict:
    """Session s in replay order, each window standardised on its calibration pool (earlier windows)."""
    a, r = d["a"], d["rep"][s]
    te, paths = r["te"], r["path_used"].astype(str)
    lay = a["layout"][te]
    G = models["_G"]
    out = {}
    for comp in feat_components(cfg):
        m = models[comp]
        M = (np.c_[G, models["_pace"]] if m["pace"] else G)[te]
        if m["kind"] == "perpath":
            Bm = m["state"].transform(M, paths)
        else:
            pp = _paths(paths, cfg)
            Bm = np.empty((len(te), len(m["state"].g_mu)))
            for k in range(len(te)):
                pool = np.arange(k) if cfg.get("pool") != "layout" and cfg.get("std") != "id_layout" else \
                    np.flatnonzero(lay[:k] == lay[k])
                Xall = np.vstack([M[pool], M[k:k + 1]])
                pa = np.r_[pp[pool], pp[k:k + 1]]
                Bm[k] = m["state"].apply(Xall, pa, np.array([len(pool)]), np.arange(len(pool)) if len(pool) else None)[0]
        out[comp] = L._order(C.logp_from_proba(m["clf"].predict_proba(Bm)), m["classes"])
    return out


def lever(cfg: dict, cnn: dict = None) -> tuple:
    """Train and re-score both folds; the ensemble with the CNN components (the replays' unless given). Returns
    (ensembles per session, feature components per session, seconds)."""
    d = IL.data()
    t = time.time()
    ens, feats = {}, {}
    for s in IL.SESS:
        f = rescore(train(d, s, cfg), d, s, cfg)
        cc = cnn[s] if cnn is not None else {c: d["rep"][s][f"c_{c}"] for c in IL.CNNC}
        comps = {**f, **cc}
        ens[s] = IL.ensemble(comps, use=tuple(feat_components(cfg)) + IL.CNNC)
        feats[s] = f
    return ens, feats, time.time() - t


def anchor() -> dict:
    """A-F: the engine's configuration reproduces the replays' feature components and decisions."""
    d = IL.data()
    ens, feats, sec = lever({})
    out = {}
    for s in IL.SESS:
        r = d["rep"][s]
        diff = {c: float(np.abs(feats[s][c] - r[f"c_{c}"]).max()) for c in IL.FEATC}
        same = int((ens[s].argmax(1) == r["ensemble"].argmax(1)).sum())
        out[s] = {"max_abs_diff": diff, "ensemble_max_abs_diff": float(np.abs(ens[s] - r["ensemble"]).max()),
                  "decisions_equal": f"{same} of {len(r['te'])}",
                  "PASS": bool(max(diff.values()) <= 1e-9 and same == len(r["te"]))}
    out["PASS"] = all(out[s]["PASS"] for s in IL.SESS)
    out["seconds"] = round(sec, 1)
    IL.dump(os.path.join(IL.OUT, "anchor_feat.json"), out)
    print(out, flush=True)
    return out


if __name__ == "__main__":
    sys.exit(0 if anchor()["PASS"] else 1)
