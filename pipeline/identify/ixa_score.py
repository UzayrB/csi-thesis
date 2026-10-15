"""ixa_score. The extras brief's section 2 scoring (`runs/identify/engine/PLAN.md`, the extras note, E0): the five
feature components retrained on a candidate's inputs (the arithmetic of `idz_core.train`'s feature part), each
replayed session's windows re-scored in replay order with every earlier window as calibration (the arithmetic of
`engine.Session.classify`), the replay's saved CNN outputs added, and the audit's adoption rule.

Development evaluation, all data seen.
"""

from __future__ import annotations

import json
import os

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idv2_core as C
from pipeline.identify import idw_core as W
from pipeline.identify import idw_eval as EV
from pipeline.identify import idx_loso as L

SESS = ("A1", "A2", "A3", "B1", "B2")
CL = np.array(L.CLASSES)
CNN = ("cnn", "cnn_prior", "cnn_perlink_prior")
FOLD_OF = {"B2": "toB2", "B1": "toB1"}


def base(suffix: str = "") -> dict:
    """The engine bank's labels and gait columns, and the C0 replays (the baseline) per session. suffix "" is engine v1
    (the A stage's anchor and record); `EN.SUFFIX` is engine v2 (the cadence bug fix: its bank and replays)."""
    T = EN.T_S if suffix == EN.SUFFIX else 3.0                 # engine v4 (2 Oct): the current engine's window
    bdir = os.path.join(EN.ENG, f"bank_T{T:.1f}{suffix}")
    meta = json.load(open(os.path.join(bdir, "meta.json")))["passes"]
    names = json.load(open(os.path.join(bdir, "feature_names.json")))
    X = np.load(os.path.join(bdir, "features.npy")).astype(np.float64)
    a = {k: np.array([m[k] for m in meta]) for k in ("session", "room", "kind", "block", "anon", "path", "t_start",
                                                      "press_speed_m_s", "wifi_speed")}
    rep = {}
    for s in SESS:
        z = np.load(os.path.join(EN.ENG, "replays", f"loso_{s}{suffix}_{s}_T{T:.1f}.npz"))
        rep[s] = {k: z[k] for k in z.files}
    return {"a": a, "G": X[:, EN.v2_columns(names)], "meta": meta, "rep": rep, "names": names}


def matrix(G, extra, pace, pace_flag):
    M = G if extra is None else np.c_[G, extra]
    return np.c_[M, pace] if pace_flag else M


def train_feat(G, extra, pace, a, tr, off=None) -> dict:
    """The five feature components on rows `tr` (`idz_core.train`'s feature part). off: extra TRAINING rows
    (A3), a list of dicts {G, extra, pace, rows} whose rows index `a`; they are standardised with statistics
    fitted on the t0 rows only."""
    from pipeline.identify import idmax_eval as E
    out = {}
    for comp, (head, norm, pace_flag) in W.FEAT.items():
        M = matrix(G, extra, pace, pace_flag)[tr]
        p, s, y = a["path"][tr], a["session"][tr], a["anon"][tr]
        if norm == "perpath":
            st = W.PerPath().fit(M, p)
            A = st.transform(M, p)
        else:
            st = W.Prior()
            A = st.fit(M, p, s)
        if off:
            As, ys = [A], [y]
            for o in off:
                Mo = matrix(o["G"], o["extra"], o["pace"], pace_flag)
                po, so = a["path"][o["rows"]], a["session"][o["rows"]]
                if norm == "perpath":
                    Ao = st.transform(Mo, po)
                else:
                    Zo, Zt = st.Z(Mo), st.Z(M)
                    Ao = np.empty((len(Mo), Zt.shape[1]))
                    for ss in np.unique(so):
                        m = so == ss
                        Ao[m] = st.zs(Zo[m], po[m], Zt[s == ss], p[s == ss])
                As.append(Ao)
                ys.append(a["anon"][o["rows"]])
            A, y = np.vstack(As), np.concatenate(ys)
        clf = E.make_model(head).fit(A, y)
        out[comp] = {"state": st, "clf": clf, "classes": list(clf.classes_)}
    return out


def rescore(models: dict, G, extra, pace, rep: dict) -> dict:
    """One session's windows in replay order: the feature components with every earlier window as calibration."""
    te, paths = rep["te"], rep["path_used"]
    out = {}
    for comp, (_head, norm, pace_flag) in W.FEAT.items():
        d = models[comp]
        M = matrix(G, extra, pace, pace_flag)[te]
        if norm == "perpath":
            Bm = d["state"].transform(M, paths)
        else:
            Bm = np.empty((len(te), len(d["state"].g_mu)))
            for k in range(len(te)):
                Bm[k] = d["state"].apply(M, paths, np.array([k]), np.arange(k) if k else None)[0]
        out[comp] = L._order(C.logp_from_proba(d["clf"].predict_proba(Bm)), d["classes"])
    return out


def ensemble(feat: dict, rep: dict) -> np.ndarray:
    return C.normalise_logp(sum(feat[c] for c in W.FEAT) + sum(rep[f"c_{c}"] for c in CNN))


def collect(ens: dict, a) -> dict:
    """Per-window correctness and labels over the two walks folds and the 600 tracking passes."""
    walks, track = [], []
    for s in SESS:
        te = ens[s]["te"]
        ok = (CL[ens[s]["ensemble"].argmax(1)] == a["anon"][te]).astype(float)
        for i, (r, c) in enumerate(zip(te, ok)):
            if a["kind"][r] == "idcap" and s in FOLD_OF:
                walks.append((r, c, FOLD_OF[s], i))
            elif a["kind"][r] == "track":
                track.append((r, c))
    w = {"te": np.array([x[0] for x in walks]), "ok": np.array([x[1] for x in walks]), "fold": np.array([x[2] for x in walks])}
    w.update({"who": a["anon"][w["te"]], "block": a["block"][w["te"]], "path": a["path"][w["te"]]})
    t = {"te": np.array([x[0] for x in track]), "ok": np.array([x[1] for x in track])}
    t["who"] = a["anon"][t["te"]]
    return {"walks": w, "track": t}


def table(c: dict) -> dict:
    w = c["walks"]
    out = {}
    for b, m in EV.masks(w).items():
        out[b] = EV._boot(w["ok"][m], w["who"][m]) | {f: round(100 * float(w["ok"][m & (w["fold"] == f)].mean()), 2)
                                                       for f in ("toB2", "toB1")}
    out["loso_tracking_pooled"] = EV._boot(c["track"]["ok"], c["track"]["who"])
    return out


def rule(cand: dict, best: dict) -> dict:
    """The audit's rule (brief 2.1): natural paired interval above 0; slow and fast >= -3; tracking pooled >= -3."""
    cw, bw = cand["walks"], best["walks"]
    assert np.array_equal(cw["te"], bw["te"]) and np.array_equal(cand["track"]["te"], best["track"]["te"])
    mk = EV.masks(bw)
    nat = EV.paired(cw["ok"][mk["natural_both"]], bw["ok"][mk["natural_both"]], bw["who"][mk["natural_both"]])
    slow = 100 * (cw["ok"][mk["slow"]].mean() - bw["ok"][mk["slow"]].mean())
    fast = 100 * (cw["ok"][mk["fast"]].mean() - bw["ok"][mk["fast"]].mean())
    trk = 100 * (cand["track"]["ok"].mean() - best["track"]["ok"].mean())
    c1, c2, c3 = bool(nat["ci95"][0] > 0), bool(slow >= -3.0 and fast >= -3.0), bool(trk >= -3.0)
    return {"paired_natural": nat, "paired_by_block": {b: EV.paired(cw["ok"][m], bw["ok"][m], bw["who"][m]) for b, m in mk.items()},
            "slow_change": round(slow, 2), "fast_change": round(fast, 2), "tracking_pooled_change": round(trk, 2),
            "condition_1": c1, "condition_2": c2, "condition_3": c3, "ADOPT": c1 and c2 and c3}
