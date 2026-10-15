"""idgp_eval. IDGP item 5: the arms of brief 2026-09-23f section 5, nested, in every scope of section 6.

THE ONE RULE, as in idmax_eval. Every choice (training scope, head, link fusion, Doppler form, the
cadence margin) is made on the training side. A fold's inner splits are subsets of its training
rows; the test labels are a SealedLabels revealed only after the fold's predictions are committed.

TARGETS. "A_fwd" (the headline): inner criterion and test scoring on A_fwd passes. "ALL" (the
secondary table and the within-day rows): scope (b) only, inner criterion and scoring on every line.

ARMS (menus fixed in reports/QUEUE_IDGP.md before any run):
  S0          S_se alone (pace from walk start and end); scope x head
  S0_fixed    S_se, shrinkage LDA, scope (b): the reference
  G           rhythm and shape, no pace and no spatial parameter
  GP          G plus S_se, step length, walk ratio and speed-adjusted cadence
  G_RX1..3    G on one link alone, that link's own cadence (per-link rows beside mean F)
  GPCNN_early GP (concatenated) plus the 16-d training-side PCA of the five-seed CNN embedding
  GPCNN_late  GP's selected posterior and the CNN's, temperature-calibrated on inner out-of-fold
              posteriors, log-probabilities summed
  GP_stack    logistic stacker on G, S0 and CNN out-of-fold log-posteriors (scope b bases)
Tree heads (rf, gb) never receive speed-adjusted cadence (the 23b fault 3).

CLI: `python -m pipeline.identify.idgp_eval run <target> <fold_tag>` (one fold, every arm, its own
checkpoint), then `python -m pipeline.identify.idgp_eval summarise`.
"""

from __future__ import annotations

import itertools
import json
import os
import sys
import time
import warnings

import numpy as np

from pipeline.identify import idmax_common as IC
from pipeline.identify import idmax_eval as E
from pipeline.identify.idgp_contract import LINKS, RIG_ROOM_A, mean_F, path_length

warnings.filterwarnings("ignore")
STAGE = "idgp_eval"
BANK = os.path.join("runs", "identify", "idgp")
OUT = os.path.join(BANK, STAGE)
HEADS = ("lda", "logreg_C0.1", "linsvm_C0.1", "rf", "gb")
TREES = ("rf", "gb")
SCOPES = ("b", "a")
FUSIONS = ("concat", "late_F", "late_uniform")
FORMS = ("cor", "raw")
LOSO_TAGS = ("s0102_to_s03", "s0103_to_s02", "s0203_to_s01")
PAIR_TAGS = ("s01_to_s02", "s01_to_s03", "s02_to_s01", "s02_to_s03", "s03_to_s01", "s03_to_s02")
WD_TAGS = ("wd_temporal_s01", "wd_temporal_s02", "wd_temporal_s03")
PACE_ARMS = ("GP", "GPCNN_early", "GPCNN_late", "GP_stack")
META_ARMS = ("G", "GP", "GPCNN_early", "GPCNN_late", "GP_stack")


# ------------------------------------------------------------------ data

_BANKS: dict = {}


def bank(margin: float) -> dict:
    if margin not in _BANKS:
        d = np.load(os.path.join(BANK, f"bank_m{margin}.npz"), allow_pickle=False)
        names = [str(x) for x in d["names"]]
        keys = [str(k) for k in d["keys"]]
        assert keys == [IC.pass_key(r) for r in IC.pass_inventory()]
        _BANKS[margin] = {"X": d["X"], "names": names, "col": {n: j for j, n in enumerate(names)}}
    return _BANKS[margin]


def meta() -> dict:
    M = E.meta()
    M["S_se"] = np.array([path_length(r["line"]) / (r["t_end_press"] - r["t_start_press"])
                          for r in M["inv"]])
    return M


def cols(B: dict, pred) -> np.ndarray:
    return np.array([j for n, j in B["col"].items() if pred(n.split("|"))], int)


_MF: dict = {}


def link_weights(line: str, mode: str) -> dict:
    if mode == "late_uniform":
        return {L: 1.0 / 3 for L in LINKS}
    if line not in _MF:
        _MF[line] = mean_F(line, RIG_ROOM_A)
    f = _MF[line]
    s = sum(f.values())
    return {L: f[L] / s for L in LINKS}


# ------------------------------------------------------------------ feature blocks

def pass_cols(B, arm: str) -> np.ndarray:
    if arm == "S0":
        return cols(B, lambda p: p[0] == "P" and p[1] == "pace")
    base = cols(B, lambda p: p[0] == "P" and p[1] == "rhy")
    if arm.startswith("GP"):
        base = np.r_[base, cols(B, lambda p: p[0] == "P" and p[1] in ("pace", "spat"))]
    return base


def link_cols(B, L: str, form: str, cadv: str) -> np.ndarray:
    if cadv == "lk":
        return cols(B, lambda p: p[0] == L and ((p[1] == "rhy" and p[3] == "lk") or p[1] == "env" or
                                                (p[1] == "dop" and p[2] == form and p[3] == "lk")))
    return cols(B, lambda p: p[0] == L and ((p[1] == "rhy" and p[3] == "fu") or p[1] == "env" or
                                            (p[1] == "dop" and p[2] == form and
                                             (p[3] == "fu" or "_cyc" not in p[4]))))


def sac_column(B, M, rows_fit, rows_all) -> np.ndarray:
    """Speed-adjusted cadence: the residual of fused cadence on S_se, fitted on rows_fit only."""
    c = B["X"][:, B["col"]["P|rhy|-|fu|cadence_hz"]]
    s = M["S_se"]
    ok = rows_fit[np.isfinite(c[rows_fit])]
    b1, b0 = np.polyfit(s[ok], c[ok], 1)
    return (c - (b0 + b1 * s))[rows_all]


# ------------------------------------------------------------------ models

def _proba(clf, X):
    if hasattr(clf, "predict_proba"):
        return clf.predict_proba(X)
    d = clf.decision_function(X)
    if d.ndim == 1:
        d = np.c_[-d, d]
    e = np.exp(d - d.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


def fit_component(X, rows_fit, rows_te, y, M, head, scope):
    A, Bm = E.prep(X[rows_fit], X[rows_te], M["line"][rows_fit], M["line"][rows_te],
                   "perline_z" if scope == "b" else "none")
    if A.shape[1] == 0:
        return None
    clf = E.make_model(head).fit(A, y[rows_fit])
    return _proba(clf, Bm), [str(c) for c in clf.classes_]


class Ctx:
    """What a fit may see: the training side (all lines), its margin and its CNN."""

    def __init__(self, tr_side: np.ndarray, M: dict, target: str):
        self.tr = np.asarray(sorted(tr_side))
        self.M = M
        self.target = target
        self.margin = choose_margin(self.tr, M)
        self.B = bank(self.margin)
        self._cnn = None

    def rows_fit(self, scope):
        if scope == "a":
            assert self.target != "ALL"
            return self.tr[self.M["line"][self.tr] == self.target]
        return self.tr

    def cnn(self):
        k = tuple(self.tr)
        if k in _CNN_CACHE:
            self._cnn = _CNN_CACHE[k]
        if self._cnn is None:
            from pipeline.identify import idgp_cnn as C
            name = cnn_name(self.tr, self.M)
            self._cnn = C.load(name)
            assert np.array_equal(np.sort(self._cnn["tr"]), self.tr), "CNN trained on another side"
            _CNN_CACHE[k] = self._cnn
        return self._cnn

    def cnn_embedding(self) -> np.ndarray:
        """Five seeds' 64-d embeddings, standardised on the training side, concatenated, then the
        training-side PCA to 16 components. Rows: all 360 passes."""
        k = tuple(self.tr)
        if k in _EMB_CACHE:
            return _EMB_CACHE[k]
        if not hasattr(self, "_emb"):
            Z = []
            for Es in self.cnn()["E"]:
                mu, sd = Es[self.tr].mean(0), Es[self.tr].std(0) + 1e-9
                Z.append((Es - mu) / sd)
            Z = np.concatenate(Z, 1)
            mu = Z[self.tr].mean(0)
            _u, _s, Vt = np.linalg.svd(Z[self.tr] - mu, full_matrices=False)
            self._emb = (Z - mu) @ Vt[:16].T
            _EMB_CACHE[k] = self._emb
        return self._emb


_ICC_CACHE: dict = {}
_CNN_CACHE: dict = {}
_EMB_CACHE: dict = {}


def choose_margin(tr, M) -> float:
    """Section 3: the margin with the higher TRAINING-side person ICC of the fused cadence."""
    from pipeline.identify.idgp_cadence import icc1
    k = tuple(tr)
    if k not in _ICC_CACHE:
        v = {m: icc1(bank(m)["X"][tr, bank(m)["col"]["P|rhy|-|fu|cadence_hz"]], M["y"][tr])
             for m in (0.0, 0.5)}
        _ICC_CACHE[k] = 0.0 if v[0.0] >= v[0.5] else 0.5
    return _ICC_CACHE[k]


def cnn_name(tr, M) -> str:
    from pipeline.identify.idgp_cnn import training_sets
    for nm, idx in training_sets(M).items():
        if len(idx) == len(tr) and np.array_equal(np.sort(idx), tr):
            return nm
    raise KeyError("no CNN was trained on this training side")


def predict(arm: str, cand: dict, ctx: Ctx, rows_te: np.ndarray, y: np.ndarray):
    """(pred, P, classes) of one candidate of one arm, fitted on ctx's training side only."""
    B, M = ctx.B, ctx.M
    rf = ctx.rows_fit(cand.get("scope", "b"))
    head, scope = cand.get("head", "lda"), cand.get("scope", "b")
    if arm in ("S0", "S0_fixed"):
        return _combine([(B["X"][:, pass_cols(B, "S0")], 1.0)], rf, rows_te, y, M, head, scope)
    if arm.startswith("G_RX"):
        L = arm[2:]
        return _combine([(B["X"][:, link_cols(B, L, cand["form"], "lk")], 1.0)], rf, rows_te, y, M,
                        head, scope)
    base = "G" if arm in ("G", "GCNN_early") else "GP"   # GCNN_early: the speed-removed ablation
    P = B["X"][:, pass_cols(B, base)]
    if base == "GP" and head not in TREES:
        P = np.c_[P, np.full(len(P), np.nan)]
        P[rows_te, -1] = sac_column(B, M, rf, rows_te)
        P[rf, -1] = sac_column(B, M, rf, rf)
    fusion = cand.get("fusion", "concat")
    if fusion == "concat":
        X = np.concatenate([P] + [B["X"][:, link_cols(B, L, cand["form"], "fu")] for L in LINKS], 1)
        if arm in ("GPCNN_early", "GCNN_early"):
            X = np.c_[X, ctx.cnn_embedding()]
        return _combine([(X, 1.0)], rf, rows_te, y, M, head, scope)
    comps = [(P, 1.0)]
    for L in LINKS:
        w = np.array([link_weights(M["line"][i], fusion)[L] for i in rows_te])
        if np.all(w == 0):
            continue
        comps.append((B["X"][:, link_cols(B, L, cand["form"], "lk")], w))
    return _combine(comps, rf, rows_te, y, M, head, scope)


def _combine(comps, rf, rows_te, y, M, head, scope):
    logp, classes = 0.0, None
    for X, w in comps:
        out = fit_component(X, rf, rows_te, y, M, head, scope)
        if out is None:
            continue
        Pc, cl = out
        if classes is None:
            classes = cl
        assert cl == classes
        logp = logp + np.asarray(w, float).reshape(-1, 1) * np.log(np.clip(Pc, 1e-9, 1.0))
    if classes is None:
        return None
    Pn = np.exp(logp - logp.max(axis=1, keepdims=True))
    Pn /= Pn.sum(axis=1, keepdims=True)
    return np.asarray(classes)[Pn.argmax(1)], Pn, classes


def menu(arm: str, target: str) -> list:
    scopes = ("b",) if target == "ALL" else SCOPES
    if arm == "S0":
        return [{"scope": s, "head": h} for s in scopes for h in HEADS]
    if arm == "S0_fixed":
        return [{"scope": "b", "head": "lda"}]
    if arm.startswith("G_RX"):
        return [{"scope": s, "head": h, "form": f} for s in scopes for h in HEADS for f in FORMS]
    if arm == "GPCNN_early":
        return [{"scope": s, "head": h, "fusion": "concat", "form": f}
                for s in scopes for h in HEADS for f in FORMS]
    return [{"scope": s, "head": h, "fusion": u, "form": f}
            for s in scopes for h in HEADS for u in FUSIONS for f in FORMS]


def ctag(c: dict) -> str:
    return "/".join(f"{k}={c[k]}" for k in ("scope", "head", "fusion", "form") if k in c)


# ------------------------------------------------------------------ nested selection

def target_rows(idx: np.ndarray, M: dict, target: str, fallback: bool = True) -> np.ndarray:
    if target == "ALL":
        return idx
    t = idx[M["line"][idx] == target]
    return t if (len(t) >= 6 or not fallback) else idx


def select(arm: str, fold, M: dict, y_train: np.ndarray, target: str) -> dict:
    """Two inner splits (LOSO) or one (temporal), on the TRAINING side only. Test rows never enter."""
    trs = set(fold.tr.tolist())
    rank, oof = [], {}
    for ci, cand in enumerate(menu(arm, target)):
        accs, pts, ok, o = [], [], True, []
        for a, b in fold.inner:
            assert set(a.tolist()) <= trs and set(b.tolist()) <= trs
            ctx = Ctx(a, M, target)
            vb = target_rows(b, M, target)
            try:
                out = predict(arm, cand, ctx, vb, y_train)
            except ValueError:
                out = None
            if out is None:
                ok = False
                break
            pred, P, cl = out
            accs.append(float(np.mean(pred == y_train[vb])))
            pts.append(float(np.mean([P[i, cl.index(y_train[r])] if y_train[r] in cl else 0.0
                                      for i, r in enumerate(vb)])))
            o.append({"rows": vb.tolist(), "P": np.round(P, 5).tolist(), "classes": cl})
        if not ok:
            continue
        rank.append((float(np.mean(accs)), float(np.mean(pts)), ci))
        oof[ci] = o
    rank.sort(key=lambda z: (-z[0], -z[1], z[2]))
    return {"rank": rank, "oof": oof}


def run_arm(arm: str, fold, M: dict, target: str, ck: IC.Checkpoint, extra: dict = None) -> dict:
    key = f"{arm}|{target}|{fold.tag}"
    if ck.has(key):
        return ck.done[key]["r"]
    t0 = time.time()
    y = M["y"]
    yt = np.full(len(y), None, object)
    yt[fold.tr] = y[fold.tr]                 # the test side is blanked, not just unused
    yt = yt.astype(str)
    te = target_rows(fold.te, M, target, fallback=False)
    sealed = IC.SealedLabels(y[te], f"{arm}|{target}|{fold.tag}")
    cands = menu(arm, target)
    ctx = Ctx(fold.tr, M, target)
    if arm == "GPCNN_late":
        r = _run_late(fold, M, target, ctx, te, sealed, yt, extra)
    elif arm == "GP_stack":
        r = _run_stack(fold, M, target, ctx, te, sealed, yt, extra)
    else:
        sel = select(arm, fold, M, yt, target)
        acc_in, pt_in, ci = sel["rank"][0]
        pred, P, cl = predict(arm, cands[ci], ctx, te, yt)
        truth = sealed.reveal(pred)
        r = {"config": ctag(cands[ci]), "cand": cands[ci], "inner_acc": acc_in, "inner_ptrue": pt_in,
             "ranking": [(ctag(cands[c]), round(a, 4), round(p, 4)) for a, p, c in sel["rank"]],
             "oof": sel["oof"][ci], "margin": ctx.margin}
        # POST HOC CEILING: every candidate on the test side, AFTER the choice was committed
        if arm in ("S0", "G", "GP") and target == "A_fwd":
            ceil = {}
            for c in cands:
                out = predict(arm, c, ctx, te, yt)
                if out is not None:
                    ceil[ctag(c)] = round(float(np.mean(out[0] == truth)), 4)
            r["POST_HOC_ceiling"] = ceil
        r.update({"pred": pred.tolist(), "P": np.round(P, 5).tolist(), "classes": cl,
                  "truth": truth.tolist()})
    if "truth" not in r:
        r["truth"] = sealed.reveal(np.asarray(r["pred"])).tolist()
    r.update({"arm": arm, "target": target, "tag": fold.tag, "scope_family": fold.scope,
              "te": te.tolist(),
              "acc": float(np.mean(np.asarray(r["pred"]) == y[te])), "secs": round(time.time() - t0, 1)})
    ck.put(key, {"r": r})
    return r


# ------------------------------------------------------------------ calibration, late fusion, stack

TEMPS = np.logspace(-1, 1.5, 41)


def fit_temperature(P_list, truth_list) -> float:
    best = (np.inf, 1.0)
    for T in TEMPS:
        nll = 0.0
        for P, t in zip(P_list, truth_list):
            Q = np.clip(np.asarray(P), 1e-9, 1) ** (1.0 / T)
            Q /= Q.sum(1, keepdims=True)
            nll -= np.sum(np.log(Q[np.arange(len(t)), t]))
        if nll < best[0]:
            best = (nll, float(T))
    return best[1]


def tscale(P, T):
    Q = np.clip(np.asarray(P, float), 1e-9, 1) ** (1.0 / T)
    return Q / Q.sum(1, keepdims=True)


def align(P, cl, classes) -> np.ndarray:
    """Posterior columns re-ordered to `classes`; a class the model never saw gets 1e-9."""
    P = np.asarray(P, float)
    out = np.full((len(P), len(classes)), 1e-9)
    for j, c in enumerate(classes):
        if c in cl:
            out[:, j] = P[:, list(cl).index(c)]
    return out / out.sum(1, keepdims=True)


def _cnn_on(tr, rows, M, classes):
    c = Ctx(tr, M, "ALL").cnn()
    return align(c["P"][rows], c["classes"], classes)


def _run_late(fold, M, target, ctx, te, sealed, yt, extra):
    gp = extra["GP"]
    classes = gp["classes"]
    # temperatures from inner out-of-fold posteriors of GP's chosen candidate and of the CNN
    Pg, Pc, T_idx = [], [], []
    for (a, _b), o in zip(fold.inner, gp["oof"]):
        rows = np.asarray(o["rows"])
        Pg.append(align(o["P"], o["classes"], classes))
        Pc.append(_cnn_on(a, rows, M, classes))
        T_idx.append(np.array([classes.index(v) for v in yt[rows]]))
    Tg, Tc = fit_temperature(Pg, T_idx), fit_temperature(Pc, T_idx)
    inner = [float(np.mean(np.argmax(np.log(tscale(g, Tg)) + np.log(tscale(c, Tc)), 1) == t))
             for g, c, t in zip(Pg, Pc, T_idx)]
    pc_te = _cnn_on(fold.tr, te, M, classes)
    L = np.log(tscale(np.asarray(gp["P"]), Tg)) + np.log(tscale(pc_te, Tc))
    P = np.exp(L - L.max(1, keepdims=True))
    P /= P.sum(1, keepdims=True)
    pred = np.asarray(classes)[P.argmax(1)]
    return {"config": f"GP[{gp['config']}] + CNN, T_gp={Tg:.3g}, T_cnn={Tc:.3g}",
            "inner_acc": float(np.mean(inner)), "pred": pred.tolist(), "P": np.round(P, 5).tolist(),
            "classes": classes, "T": [Tg, Tc], "margin": ctx.margin}


def _run_stack(fold, M, target, ctx, te, sealed, yt, extra):
    """Bases refitted in scope (b) with their selected head, fusion and form; the stacker is fitted
    on inner out-of-fold log-posteriors of the training side's passes (all lines)."""
    from sklearn.linear_model import LogisticRegression
    bases = {"G": extra["G"]["cand"], "S0": extra["S0"]["cand"]}

    classes = sorted(set(yt[fold.tr]))

    def feats(tr, rows):
        c = Ctx(tr, M, "ALL")
        out = []
        for arm, cand in bases.items():
            pred = predict(arm, {**cand, "scope": "b"}, c, rows, yt)
            out.append(np.log(align(pred[1], pred[2], classes)))
        out.append(np.log(_cnn_on(tr, rows, M, classes)))
        return np.concatenate(out, 1), classes

    Z, Yz = [], []
    for a, b in fold.inner:
        z, _cl = feats(a, b)
        Z.append((z, b))
        Yz.append(yt[b])
    # inner accuracy: stacker fitted on one split's out-of-fold rows, scored on the other's target rows
    inner = []
    if len(Z) == 2:
        for i in (0, 1):
            st = LogisticRegression(C=1.0, max_iter=3000).fit(Z[i][0], Yz[i])
            j = 1 - i
            m = M["line"][Z[j][1]] == target if target != "ALL" else np.ones(len(Z[j][1]), bool)
            inner.append(float(np.mean(st.predict(Z[j][0][m]) == Yz[j][m])))
    st = LogisticRegression(C=1.0, max_iter=3000).fit(np.concatenate([z for z, _ in Z]),
                                                      np.concatenate(Yz))
    zt, cl = feats(fold.tr, te)
    P = st.predict_proba(zt)
    pred = st.classes_[P.argmax(1)]
    return {"config": f"stack(G[{ctag(bases['G'])}], S0[{ctag(bases['S0'])}], CNN), bases in scope b",
            "inner_acc": float(np.mean(inner)) if inner else np.nan,
            "inner_note": None if inner else "single inner split: no held-out stacker accuracy",
            "pred": pred.tolist(), "P": np.round(P, 5).tolist(), "classes": [str(c) for c in st.classes_],
            "margin": ctx.margin}


# ------------------------------------------------------------------ folds and drivers

def folds(M: dict) -> dict:
    out = {f.tag: f for f in E.crossday_folds(M, M["y"])}
    out.update({f.tag: f for f in E.withinday_temporal_folds(M, M["y"])})
    return out


def arms_for(target: str, tag: str) -> list:
    if tag.startswith("wd_"):
        return ["S0", "G", "GP"]
    if target == "ALL":
        return ["S0", "G", "GP", "GPCNN_early", "GPCNN_late"]
    return ["S0", "S0_fixed", "G", "GP", "G_RX1", "G_RX2", "G_RX3", "GPCNN_early", "GPCNN_late",
            "GP_stack"]


def run_fold(target: str, tag: str) -> None:
    IC.job_start(f"{STAGE}_{target}_{tag}")
    M = meta()
    f = folds(M)[tag]
    ck = IC.Checkpoint(os.path.join(OUT, f"ck_{target}_{tag}.jsonl"))
    done = {}
    for arm in arms_for(target, tag):
        if IC.should_stop():
            IC.status(STAGE, "SIGTERM: stopping after the last finished arm")
            return
        r = run_arm(arm, f, M, target, ck, extra=done)
        done[arm] = r
        IC.status(STAGE, f"{target} {tag} {arm}: {100 * r['acc']:.1f} on {len(r['te'])} "
                         f"(inner {100 * r['inner_acc']:.1f}) {r['config']} [{r['secs']} s]")


# ------------------------------------------------------------------ summaries

def summarise_rows(rs: list, M: dict, chance: float = 100 / 6) -> dict:
    te = np.concatenate([np.asarray(r["te"], int) for r in rs])
    pred = np.concatenate([np.asarray(r["pred"]) for r in rs])
    truth = np.concatenate([np.asarray(r["truth"]) for r in rs])
    corr = (pred == truth).astype(float)
    recs = np.array([f"{r['tag']}|{M['rec'][i]}" for r in rs for i in r["te"]])
    sess = np.array([f"{r['tag']}|{M['session'][i]}" for r in rs for i in r["te"]])
    return {"n": int(len(te)), "acc_pct": round(100 * float(corr.mean()), 2),
            "ci95_pct": E.cluster_bootstrap(corr, recs), "chance_pct": round(chance, 2),
            "perm_p": round(E.recording_permutation_p(pred, truth, sess), 4),
            "per_fold": {r["tag"]: round(100 * r["acc"], 2) for r in rs},
            "configs": {r["tag"]: r["config"] for r in rs},
            "inner_acc": {r["tag"]: round(100 * r["inner_acc"], 2) for r in rs}}


def paired_diff(ra: list, rb: list, M: dict, n: int = 1000, seed: int = 0) -> dict:
    """arm minus reference on the SAME passes, cluster bootstrap over test recordings."""
    da, db = {}, {}
    for r in ra:
        for i, p, t in zip(r["te"], r["pred"], r["truth"]):
            da[(r["tag"], i)] = float(p == t)
    for r in rb:
        for i, p, t in zip(r["te"], r["pred"], r["truth"]):
            db[(r["tag"], i)] = float(p == t)
    keys = sorted(set(da) & set(db))
    assert len(keys) == len(da) == len(db), "the arms were not scored on the same passes"
    d = np.array([da[k] - db[k] for k in keys])
    cl = np.array([f"{k[0]}|{M['rec'][k[1]]}" for k in keys])
    rng = np.random.default_rng(seed)
    u = np.unique(cl)
    by = [d[cl == c] for c in u]
    bs = [np.concatenate([by[i] for i in rng.integers(0, len(u), len(u))]).mean() for _ in range(n)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    per_fold = {}
    for tag in sorted({k[0] for k in keys}):
        m = np.array([k[0] == tag for k in keys])
        per_fold[tag] = round(100 * float(d[m].mean()), 2)
    return {"diff_pct": round(100 * float(d.mean()), 2), "ci95_pct": [round(100 * lo, 2), round(100 * hi, 2)],
            "n": int(len(d)), "per_fold": per_fold, "ABOVE_ZERO": bool(lo > 0)}


def load_results() -> dict:
    res = {}
    for p in sorted(os.listdir(OUT)):
        if p.startswith("ck_") and p.endswith(".jsonl"):
            for d in IC.Checkpoint(os.path.join(OUT, p)).done.values():
                r = d["r"]
                res.setdefault((r["arm"], r["target"]), []).append(r)
    return res


def summarise() -> dict:
    M = meta()
    res = load_results()
    out = {"stage": STAGE, "LABEL": "EXPLORATORY (Room A reopened, decision 11); nested; "
           "headline = LOSO scored on A_fwd", "rows": {}}
    for (arm, target), rs in sorted(res.items()):
        d = {}
        lo = [r for r in rs if r["tag"] in LOSO_TAGS]
        pa = [r for r in rs if r["tag"] in PAIR_TAGS]
        wd = [r for r in rs if r["tag"] in WD_TAGS]
        if len(lo) == 3:
            d["LOSO"] = summarise_rows(lo, M)
        if len(pa) == 6:
            d["pairings6_single_session"] = summarise_rows(pa, M)
            d["nine_pairings"] = summarise_rows(pa + lo, M) if len(lo) == 3 else None
            d["per_pairing"] = {r["tag"]: round(100 * r["acc"], 2) for r in pa + lo}
        if len(wd) == 3:
            d["WITHIN_DAY_same_recording_confounded"] = summarise_rows(wd, M)
        if target == "ALL" and len(lo) == 3:
            per = {}
            for L in IC.LINES:
                sub = [{**r, "te": [i for i in r["te"] if M["line"][i] == L],
                        "pred": [p for i, p in zip(r["te"], r["pred"]) if M["line"][i] == L],
                        "truth": [t for i, t in zip(r["te"], r["truth"]) if M["line"][i] == L]}
                       for r in lo]
                s = summarise_rows(sub, M)
                per[L] = {k: s[k] for k in ("acc_pct", "ci95_pct", "n", "perm_p")}
            d["per_line_LOSO"] = per
        out["rows"][f"{arm}|{target}"] = d
    # paired differences against S0, the integrity check 1 reading
    out["vs_S0"] = {}
    for (arm, target), rs in res.items():
        if arm.startswith("S0") or (("S0", target) not in res):
            continue
        lo = [r for r in rs if r["tag"] in LOSO_TAGS]
        s0 = [r for r in res[("S0", target)] if r["tag"] in LOSO_TAGS]
        if len(lo) == 3 and len(s0) == 3:
            out["vs_S0"][f"{arm}|{target}"] = paired_diff(lo, s0, M)
    IC.save_json(os.path.join(OUT, "results.json"), out)
    return out


def main(argv) -> int:
    if argv[1] == "run":
        run_fold(argv[2], argv[3])
        return 0
    if argv[1] == "summarise":
        IC.job_start(f"{STAGE}_summarise")
        s = summarise()
        for k, v in s["rows"].items():
            if "LOSO" in v:
                IC.status(STAGE, f"{k}: LOSO {v['LOSO']['acc_pct']} {v['LOSO']['ci95_pct']} "
                                 f"p {v['LOSO']['perm_p']} n {v['LOSO']['n']}")
        return 0
    raise SystemExit(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
