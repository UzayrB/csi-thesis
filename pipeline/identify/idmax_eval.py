# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: IDMAX evaluation engine: nested selection, sealed test labels, and every scope of section 5.

from __future__ import annotations

import itertools
import json
import os
import time
from dataclasses import dataclass, field

import warnings

import numpy as np

from pipeline.identify import idmax_common as IC

warnings.filterwarnings("ignore", message="All-NaN slice encountered")
warnings.filterwarnings("ignore", category=FutureWarning)
TOP_K = 8
N_BOOT = 1000
N_PERM = 1000



_FEAT_CACHE: dict = {}


# Function load variant.
def load_variant(variant: str) -> dict:
    if variant == "S0_ORACLE_SPEED" and variant not in _FEAT_CACHE:
        inv = IC.pass_inventory()
        X = np.array([[r["speed_m_s"]] for r in inv], float)
        _FEAT_CACHE[variant] = {"X": X, "names": ["S0|-|-|-|speed"], "fam": np.array(["S0"]),
                                "rb": np.array(["-"]), "link": np.array(["-"]),
                                "chan": np.array(["-"]), "nm": np.array(["speed"]),
                                "keys": [IC.pass_key(r) for r in inv]}
    if variant not in _FEAT_CACHE:
        d = np.load(os.path.join(IC.FEAT, f"{variant}.npz"), allow_pickle=False)
        names = [str(x) for x in d["names"]]
        parts = [n.split("|") for n in names]
        _FEAT_CACHE[variant] = {"X": d["X"].astype(np.float64), "names": names,
                                "fam": np.array([p[0] for p in parts]),
                                "rb": np.array([p[1] for p in parts]),
                                "link": np.array([p[2] for p in parts]),
                                "chan": np.array([p[3] for p in parts]),
                                "nm": np.array([p[4] for p in parts]),
                                "keys": [str(k) for k in d["keys"]]}
    return _FEAT_CACHE[variant]


# Function meta.
def meta() -> dict:
    inv = IC.pass_inventory()
    return {"inv": inv,
            "y": np.array([r["anon"] for r in inv]),
            "session": np.array([r["session"] for r in inv]),
            "rec": np.array([r["rec"] for r in inv]),
            "line": np.array([r["line"] for r in inv]),
            "base_line": np.array([r["base_line"] for r in inv]),
            "direction": np.array([r["direction"] for r in inv]),
            "order": np.array([r["order"] for r in inv]),
            "t": np.array([r["t_start_press"] for r in inv]),
            "key": np.array([IC.pass_key(r) for r in inv])}



CH = ("mean@b03_2", "mean@b08_35", "rms@b08_35", "rms@full", "rms@dop", "pca@b08_35",
      "rssi@b03_2", "rssi@b08_35")
FEATURE_SETS = {
    "B1_rhythm": lambda ch: [("cad", None), ("rhy", ch, "scalar")],
    "B2_acfshape": lambda ch: [("rhy", ch, "acfshape")],
    "B3_templates": lambda ch: [("tplacf", ch, None)],
    "B3p_templates_peaks": lambda ch: [("tplpeaks", ch, None)],
    "B4_spectral": lambda ch: [("spec", ch, None)],
    "B5_doppler": lambda ch: [("dop", "pca-pc1@w0.1", None), ("dop", "pca-pc1@w0.2", None),
                              ("dop", "pca-pc1@w0.43", None)],
    "B5k_doppler_keep_pc1": lambda ch: [("dop", "pca+pc1@w0.1", None),
                                        ("dop", "pca+pc1@w0.2", None),
                                        ("dop", "pca+pc1@w0.43", None)],
    "B6_wavelet": lambda ch: [("wav", None, None)],
    "B7_handcrafted": lambda ch: [("cad", None), ("rhy", ch, "scalar"),
                                  ("dop", "pca-pc1@w0.2", "scalar"), ("mod", None, None),
                                  ("tplacf", ch, "scalar")],
    "B8_linkmod": lambda ch: [("tplacf", ch, None), ("mod", None, None), ("prof", None, None)],
    "U_rhythm_shape": lambda ch: [("cad", None), ("rhy", ch, None), ("tplacf", ch, None)],
    "U_env_spec": lambda ch: [("cad", None), ("rhy", ch, "scalar"), ("spec", ch, None),
                              ("dop", "pca-pc1@w0.2", None)],
    "U_all_gait": lambda ch: [("cad", None), ("rhy", ch, None), ("tplacf", ch, None),
                              ("spec", ch, None), ("dop", "pca-pc1@w0.2", None),
                              ("wav", None, None), ("mod", None, None)],
    "RECSIG": lambda ch: [("RECSIG", None, None)],
    "S0": lambda ch: [("S0", None, None)],
}
GAIT_SETS = tuple(k for k in FEATURE_SETS if k not in ("RECSIG", "S0"))
LINK_SETS = {"all": ("RX1", "RX2", "RX3"), "noRX1": ("RX2", "RX3"), "noRX2": ("RX1", "RX3"),
             "noRX3": ("RX1", "RX2"), "RX1": ("RX1",), "RX2": ("RX2",), "RX3": ("RX3",)}
PC_OPTS = {"pc1-3": (0, 1, 2), "pc2-4": (1, 2, 3), "pc1-6": (0, 1, 2, 3, 4, 5), "pc2-6": (1, 2, 3, 4, 5),
           "pc1": (0,)}


# Class FConf.
@dataclass(frozen=True)
class FConf:
    variant: str
    fset: str
    ch: str = "mean@b08_35"
    links: str = "all"
    pc: str = "pc1-3"
    norm: str = "none"

    # Function tag.
    def tag(self) -> str:
        return f"{self.variant}/{self.fset}/{self.ch}/{self.links}/{self.pc}/{self.norm}"


_MASK_CACHE: dict = {}


# Function columns.
def columns(fc: FConf) -> np.ndarray:
    k = (fc.variant, fc.fset, fc.ch, fc.links, fc.pc)
    if k in _MASK_CACHE:
        return _MASK_CACHE[k]
    V = load_variant(fc.variant)
    links = set(LINK_SETS[fc.links]) | {"-"}
    m = np.zeros(len(V["names"]), bool)
    for spec in FEATURE_SETS[fc.fset](fc.ch):
        fam = spec[0]
        rb = spec[1] if len(spec) > 1 else None
        sub = spec[2] if len(spec) > 2 else None
        mm = V["fam"] == fam
        if rb is not None:
            mm &= V["rb"] == rb
        if sub == "scalar":
            mm &= ~np.char.startswith(V["nm"], "acfshape") & ~np.char.startswith(V["nm"], "tpl_") \
                  & ~np.char.startswith(V["nm"], "tplharm") & ~np.char.startswith(V["nm"], "uprof") \
                  & ~np.char.find(V["nm"], "_cyc").__ge__(0)
        elif sub == "acfshape":
            mm &= np.char.startswith(V["nm"], "acfshape")
        m |= mm
    m &= np.isin(V["link"], list(links))
    ispca = np.char.startswith(V["rb"], "pca@")
    if ispca.any():
        allowed = {str(i) for i in PC_OPTS[fc.pc]}
        m &= ~ispca | np.isin(V["chan"], list(allowed))
    idx = np.flatnonzero(m)
    _MASK_CACHE[k] = idx
    return idx



# Training-side median imputation, drop dead columns, then global or per-line z-scoring.
def prep(Xtr, Xte, ltr=None, lte=None, norm="none"):
    Xtr = np.array(Xtr, float)
    Xte = np.array(Xte, float)
    med = np.nanmedian(Xtr, axis=0)
    ok = np.isfinite(med)
    Xtr, Xte, med = Xtr[:, ok], Xte[:, ok], med[ok]
    for X in (Xtr, Xte):
        r, c = np.nonzero(~np.isfinite(X))
        X[r, c] = med[c]
    sd = Xtr.std(axis=0)
    ok = sd > 1e-12
    Xtr, Xte = Xtr[:, ok], Xte[:, ok]
    if norm == "perline_z" and ltr is not None:
        mu_g, sd_g = Xtr.mean(0), Xtr.std(0)
        A, B = np.empty_like(Xtr), np.empty_like(Xte)
        for L in np.unique(np.concatenate([ltr, lte])):
            itr = ltr == L
            mu, s = (Xtr[itr].mean(0), Xtr[itr].std(0)) if itr.sum() >= 3 else (mu_g, sd_g)
            s = np.where(s > 1e-9, s, sd_g)
            A[itr] = (Xtr[itr] - mu) / s
            B[lte == L] = (Xte[lte == L] - mu) / s
        return A, B
    mu, s = Xtr.mean(0), Xtr.std(0)
    return (Xtr - mu) / s, (Xte - mu) / s


MODELS = {
    "lda": {}, "logreg_C0.01": {"C": 0.01}, "logreg_C0.1": {"C": 0.1}, "logreg_C1": {"C": 1.0},
    "linsvm_C0.01": {"C": 0.01}, "linsvm_C0.1": {"C": 0.1},
    "rbfsvm_C1": {"C": 1.0}, "rbfsvm_C10": {"C": 10.0},
    "knn_1": {"k": 1}, "knn_7": {"k": 7}, "knn_15": {"k": 15},
    "rf": {}, "et": {}, "gb": {},
    "dtw1nn": {}, "stack": {}, "latefuse": {}, "latefuse_w": {},
}
SPECIAL = ("dtw1nn", "stack", "latefuse", "latefuse_w")


# Function make model.
def make_model(name: str, seed: int = 0):
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    from sklearn.ensemble import (ExtraTreesClassifier, HistGradientBoostingClassifier,
                                  RandomForestClassifier)
    from sklearn.linear_model import LogisticRegression
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.svm import SVC, LinearSVC
    p = MODELS[name]
    nj = int(os.environ.get("IDMAX_THREADS", "1"))
    if name == "lda":
        return LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
    if name.startswith("logreg"):
        return LogisticRegression(C=p["C"], max_iter=3000)
    if name.startswith("linsvm"):
        return LinearSVC(C=p["C"], max_iter=5000)
    if name.startswith("rbfsvm"):
        return SVC(C=p["C"], gamma="scale", probability=False, random_state=seed)
    if name.startswith("knn"):
        return KNeighborsClassifier(n_neighbors=p["k"])
    if name == "rf":
        return RandomForestClassifier(n_estimators=300, max_features="sqrt", random_state=seed,
                                      n_jobs=nj)
    if name == "et":
        return ExtraTreesClassifier(n_estimators=300, max_features="sqrt", random_state=seed,
                                    n_jobs=nj)
    if name == "gb":
        return HistGradientBoostingClassifier(max_iter=150, learning_rate=0.05, max_depth=3,
                                              random_state=seed)
    if name == "stack":
        from sklearn.ensemble import StackingClassifier
        return StackingClassifier(
            estimators=[("lda", make_model("lda")), ("lr", make_model("logreg_C0.1")),
                        ("rf", make_model("rf", seed)), ("knn", make_model("knn_7"))],
            final_estimator=LogisticRegression(C=0.1, max_iter=3000), cv=3,
            stack_method="predict_proba")
    raise ValueError(name)


# DTW distance between every row of A (n, L) and every row of B (m, L).
def _dtw_batch(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    n, L = A.shape
    m = B.shape[0]
    cost = (A[:, None, :, None] - B[None, :, None, :]) ** 2
    D = np.full((n, m, L + 1, L + 1), np.inf)
    D[:, :, 0, 0] = 0.0
    for i in range(1, L + 1):
        for j in range(max(1, i - 6), min(L, i + 6) + 1):
            D[:, :, i, j] = cost[:, :, i - 1, j - 1] + np.minimum(
                np.minimum(D[:, :, i - 1, j], D[:, :, i, j - 1]), D[:, :, i - 1, j - 1])
    return np.sqrt(D[:, :, L, L])


# Function special fit predict.
def _special_fit_predict(fc, model, tr, te, y_tr, M, V, cols, proba):
    names = np.array(V["names"])[cols]
    Xa = V["X"][np.ix_(tr, cols)]
    Xb = V["X"][np.ix_(te, cols)]
    med = np.nanmedian(Xa, axis=0)
    med = np.where(np.isfinite(med), med, 0.0)
    Xa = np.where(np.isfinite(Xa), Xa, med)
    Xb = np.where(np.isfinite(Xb), Xb, med)
    classes = sorted(set(y_tr))
    if model == "dtw1nn":
        seqs = sorted({n.rsplit("|", 1)[0] for n in names if "|tpl_" in n})
        if not seqs:
            return None
        Dsum = np.zeros((len(te), len(tr)))
        for sq in seqs:
            ix = [i for i, n in enumerate(names) if n.startswith(sq + "|tpl_")]
            Dsum += _dtw_batch(Xb[:, ix], Xa[:, ix])
        nn = np.argmin(Dsum, axis=1)
        pred = np.asarray(y_tr)[nn]
        if not proba:
            return pred
        P = np.zeros((len(te), len(classes)))
        for k, c in enumerate(classes):
            d = Dsum[:, np.asarray(y_tr) == c].min(axis=1)
            P[:, k] = -d
        P = np.exp(P - P.max(axis=1, keepdims=True))
        return pred, P / P.sum(axis=1, keepdims=True), classes
    if model in ("latefuse", "latefuse_w"):
        links = [L for L in ("RX1", "RX2", "RX3") if any(f"|{L}|" in n for n in names)]
        logp = np.zeros((len(te), len(classes)))
        for L in links:
            ix = np.array([i for i, n in enumerate(names) if f"|{L}|" in n or "|-|-|" in n])
            A, B = prep(Xa[:, ix], Xb[:, ix])
            clf = make_model("lda").fit(A, y_tr)
            w = 1.0
            if model == "latefuse_w":
                from sklearn.model_selection import cross_val_score
                acc = cross_val_score(make_model("lda"), A, y_tr, cv=3).mean()
                w = max(acc - 1.0 / len(classes), 0.0) + 1e-3
            logp += w * np.log(np.clip(clf.predict_proba(B), 1e-9, 1))
        pred = np.asarray(classes)[np.argmax(logp, axis=1)]
        if not proba:
            return pred
        P = np.exp(logp - logp.max(axis=1, keepdims=True))
        return pred, P / P.sum(axis=1, keepdims=True), classes
    raise ValueError(model)


# Function fit predict.
def fit_predict(fc: FConf, model: str, tr: np.ndarray, te: np.ndarray, y_tr: np.ndarray,
                M: dict, proba: bool = False):
    V = load_variant(fc.variant)
    cols = columns(fc)
    if not len(cols):
        return None
    if model in ("dtw1nn", "latefuse", "latefuse_w"):
        return _special_fit_predict(fc, model, tr, te, y_tr, M, V, cols, proba)
    A, B = prep(V["X"][np.ix_(tr, cols)], V["X"][np.ix_(te, cols)], M["line"][tr], M["line"][te],
                fc.norm)
    if A.shape[1] == 0:
        return None
    clf = make_model(model)
    clf.fit(A, y_tr)
    pred = clf.predict(B)
    if not proba:
        return pred
    P = None
    if hasattr(clf, "predict_proba"):
        P = clf.predict_proba(B)
    elif hasattr(clf, "decision_function"):
        d = clf.decision_function(B)
        e = np.exp(d - d.max(axis=1, keepdims=True))
        P = e / e.sum(axis=1, keepdims=True)
    return pred, P, list(clf.classes_)



# Class Fold.
@dataclass
class Fold:
    tag: str
    scope: str
    tr: np.ndarray
    te: np.ndarray
    inner: list
    y_te: IC.SealedLabels = field(repr=False, default=None)


# Per recording (so per person in a session), earliest frac of passes by time vs the rest.
def temporal_split(idx: np.ndarray, M: dict, frac: float = 0.6) -> tuple:
    a, b = [], []
    for rec in np.unique(M["rec"][idx]):
        r = idx[M["rec"][idx] == rec]
        r = r[np.argsort(M["t"][r])]
        k = int(round(frac * len(r)))
        a += list(r[:k])
        b += list(r[k:])
    return np.array(sorted(a)), np.array(sorted(b))


# Function crossday folds.
def crossday_folds(M: dict, label: np.ndarray = None) -> list:
    y = M["y"] if label is None else label
    out = []
    S = M["session"]
    for tr_s in [("01",), ("02",), ("03",), ("01", "02"), ("01", "03"), ("02", "03")]:
        for te_s in IC.SESSIONS:
            if te_s in tr_s:
                continue
            tr = np.flatnonzero(np.isin(S, tr_s))
            te = np.flatnonzero(S == te_s)
            if len(tr_s) == 2:
                a = np.flatnonzero(S == tr_s[0])
                b = np.flatnonzero(S == tr_s[1])
                inner = [(a, b), (b, a)]
                scope = "LOSO"
            else:
                inner = [temporal_split(tr, M)]
                scope = "pairing"
            tag = f"s{''.join(tr_s)}_to_s{te_s}"
            out.append(Fold(tag, scope, tr, te, inner, IC.SealedLabels(y[te], tag)))
    return out


# Function withinday temporal folds.
def withinday_temporal_folds(M: dict, label: np.ndarray = None) -> list:
    y = M["y"] if label is None else label
    out = []
    for s in IC.SESSIONS:
        idx = np.flatnonzero(M["session"] == s)
        tr, te = temporal_split(idx, M, 0.6)
        inner = [temporal_split(tr, M, 0.6)]
        out.append(Fold(f"wd_temporal_s{s}", "WD_temporal", tr, te, inner,
                        IC.SealedLabels(y[te], f"wd_temporal_s{s}")))
    return out


# Function withinday lolo folds.
def withinday_lolo_folds(M: dict, label: np.ndarray = None) -> list:
    y = M["y"] if label is None else label
    out = []
    for s in IC.SESSIONS:
        for L in IC.LINES:
            idx = np.flatnonzero(M["session"] == s)
            te = idx[M["line"][idx] == L]
            tr = idx[M["line"][idx] != L]
            if not len(te):
                continue
            out.append(Fold(f"wd_lolo_s{s}_{L}", "WD_LOLO", tr, te, [temporal_split(tr, M, 0.6)],
                            IC.SealedLabels(y[te], f"wd_lolo_s{s}_{L}")))
    return out


# Function scope folds.
def scope_folds(M: dict, y: np.ndarray, scope: str) -> list:
    if scope == "LOSO":
        return [f for f in crossday_folds(M, y) if f.scope == "LOSO"]
    if scope == "pairings9":
        return crossday_folds(M, y)
    if scope == "WD_temporal":
        return withinday_temporal_folds(M, y)
    if scope == "WD_LOLO":
        return withinday_lolo_folds(M, y)
    raise ValueError(scope)


WITHIN_DAY_LABEL = ("WITHIN-DAY: same recording, learns the session and the recording as well as "
                    "the person")


# Function run scope.
def run_scope(name: str, scope: str, y: np.ndarray, M: dict, fconfs: list, models: list,
              ck: IC.Checkpoint, top_k: int = TOP_K, chance: float = 100 / 6,
              perm: str = "identity", log=None) -> tuple:
    folds = scope_folds(M, y, scope)
    register_fold_tr(folds)
    res = []
    for f in folds:
        key = f"{name}|{f.tag}|final"
        if ck.has(key):
            res.append(ck.done[key]["r"])
            continue
        r = run_fold(f, y, M, fconfs, models, ck=ck, top_k=top_k)
        ck.put(key, {"r": r})
        res.append(r)
        if log:
            log(f"{name} {f.tag}: {100 * r['acc']:.1f} ({r['config']}|{r['model']})")
    s = summarise(res, M, chance, perm=perm)
    s["scope"] = scope
    if scope.startswith("WD"):
        s["LABEL"] = WITHIN_DAY_LABEL
    return s, res



# Function inner score.
def inner_score(fc: FConf, model: str, fold: Fold, y: np.ndarray, M: dict) -> float:
    accs = []
    for a, b in fold.inner:
        try:
            pred = fit_predict(fc, model, a, b, y[a], M)
        except ValueError:
            return -1.0
        if pred is None:
            return -1.0
        accs.append(float(np.mean(pred == y[b])))
    return float(np.mean(accs))


# Two-stage nested selection on the TRAINING side of fold only.
def select(fold: Fold, y_train_full: np.ndarray, M: dict, fconfs: list, models: list,
           ck: IC.Checkpoint = None, top_k: int = TOP_K, screen: str = "lda") -> dict:
    tr = set(fold.tr.tolist())
    for a, b in fold.inner:
        assert set(a.tolist()) <= tr and set(b.tolist()) <= tr, "inner split leaves the train side"
    y = np.full(len(y_train_full), None, object)
    y[fold.tr] = y_train_full[fold.tr]
    y = y.astype(str)
    stage1 = []
    for fc in fconfs:
        key = f"{fold.tag}|S1|{fc.tag()}|{screen}"
        if ck is not None and ck.has(key):
            s = ck.done[key]["acc"]
        else:
            s = inner_score(fc, screen, fold, y, M)
            if ck is not None:
                ck.put(key, {"acc": s})
        stage1.append((s, fc))
        if IC.should_stop():
            raise SystemExit("SIGTERM during selection; checkpoint holds the progress")
    order = sorted(range(len(stage1)), key=lambda i: (-stage1[i][0], i))
    best_fc = [stage1[i][1] for i in order[:top_k]]
    stage2 = []
    for rank, fc in enumerate(best_fc):
        for m in models:
            if m == screen:
                s = stage1[[x[1] for x in stage1].index(fc)][0]
            else:
                key = f"{fold.tag}|S2|{fc.tag()}|{m}"
                if ck is not None and ck.has(key):
                    s = ck.done[key]["acc"]
                else:
                    s = inner_score(fc, m, fold, y, M)
                    if ck is not None:
                        ck.put(key, {"acc": s})
            stage2.append((s, rank, models.index(m), fc, m))
    stage2.sort(key=lambda z: (-z[0], z[1], z[2]))
    s, _r, _mi, fc, m = stage2[0]
    return {"fconf": fc, "model": m, "inner_acc": s,
            "ranked": [(z[3], z[4], z[0]) for z in stage2],
            "stage1_top": [(round(stage1[i][0], 4), stage1[i][1].tag()) for i in order[:top_k]]}


# Select on the training side, predict the test side once, then reveal and score.
def run_fold(fold: Fold, y: np.ndarray, M: dict, fconfs: list, models: list,
             ck: IC.Checkpoint = None, top_k: int = TOP_K, screen: str = "lda") -> dict:
    sel = select(fold, y, M, fconfs, models, ck, top_k, screen=screen)
    out = None
    for fc, m, s_in in sel["ranked"]:
        try:
            out = fit_predict(fc, m, fold.tr, fold.te, y[fold.tr], M, proba=True)
        except ValueError:
            out = None
        if out is not None:
            sel.update({"fconf": fc, "model": m, "inner_acc": s_in})
            break
    if out is None:
        raise RuntimeError(f"{fold.tag}: no candidate could be fitted")
    pred, P, classes = out
    truth = fold.y_te.reveal(pred)
    return {"tag": fold.tag, "scope": fold.scope, "config": sel["fconf"].tag(),
            "model": sel["model"], "inner_acc": sel["inner_acc"],
            "stage1_top": sel["stage1_top"],
            "te": fold.te.tolist(), "pred": pred.tolist(), "truth": truth.tolist(),
            "proba": None if P is None else np.round(P, 5).tolist(), "classes": classes,
            "acc": float(np.mean(pred == truth))}



# Function cluster bootstrap.
def cluster_bootstrap(correct: np.ndarray, clusters: np.ndarray, n: int = N_BOOT,
                      seed: int = 0) -> list:
    rng = np.random.default_rng(seed)
    u = np.unique(clusters)
    by = [correct[clusters == c] for c in u]
    acc = []
    for _ in range(n):
        pick = rng.integers(0, len(u), len(u))
        v = np.concatenate([by[i] for i in pick])
        acc.append(v.mean())
    return [round(100 * float(np.percentile(acc, 2.5)), 2),
            round(100 * float(np.percentile(acc, 97.5)), 2)]


# Permute unit-level labels among the units of each stratum, predictions held fixed.
def permutation_p(pred: np.ndarray, truth: np.ndarray, units: np.ndarray, strata: np.ndarray,
                  n: int = N_PERM, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    obs = float(np.mean(pred == truth))
    uu, inv_u = np.unique(units, return_inverse=True)
    ulab = np.empty(len(uu), dtype=truth.dtype)
    ulab[inv_u] = truth
    ustr = np.empty(len(uu), dtype=strata.dtype)
    ustr[inv_u] = strata
    groups = [np.flatnonzero(ustr == s) for s in np.unique(ustr)]
    hits = 0
    for _ in range(n):
        lab = ulab.copy()
        for g in groups:
            lab[g] = lab[rng.permutation(g)]
        if np.mean(pred == lab[inv_u]) >= obs:
            hits += 1
    return (1 + hits) / (n + 1)


# Identity: permute among the recordings WITHIN each test session.
def recording_permutation_p(pred, truth, sessions, n: int = N_PERM, seed: int = 0) -> float:
    units = np.array([f"{s}|{t}" for s, t in zip(sessions, truth)])
    return permutation_p(pred, truth, units, sessions, n, seed)


# Function summarise.
def summarise(results: list, M: dict, chance: float, label_name: str = "identity",
              perm: str = "identity") -> dict:
    te = np.concatenate([np.asarray(r["te"]) for r in results])
    pred = np.concatenate([np.asarray(r["pred"]) for r in results])
    truth = np.concatenate([np.asarray(r["truth"]) for r in results])
    corr = (pred == truth).astype(float)
    recs = np.array([f"{r['tag']}|{M['rec'][i]}" for r in results for i in r["te"]])
    sess = np.array([f"{r['tag']}|{M['session'][i]}" for r in results for i in r["te"]])
    out = {"n": int(len(te)), "acc_pct": round(100 * float(corr.mean()), 2),
           "ci95_pct": cluster_bootstrap(corr, recs), "chance_pct": round(chance, 2),
           "perm_p": round(_perm(perm, pred, truth, te, results, M, sess), 4),
           "perm_unit": perm,
           "per_fold": {r["tag"]: round(100 * r["acc"], 2) for r in results},
           "configs": {r["tag"]: f"{r['config']}|{r['model']}" for r in results}}
    lines = M["line"][te]
    out["edge_recall_pct"] = {L: (round(100 * float(corr[lines == L].mean()), 1)
                                  if (lines == L).any() else None) for L in IC.EDGE}
    return out


# Function perm.
def _perm(kind, pred, truth, te, results, M, sess) -> float:
    fold = np.array([r["tag"] for r in results for _ in r["te"]])
    if kind == "identity":
        return recording_permutation_p(pred, truth, sess)
    if kind == "session":
        units = np.array([f"{f}|{M['rec'][i]}" for f, i in zip(fold, te)])
        strata = np.array([f"{f}|{M['y'][i]}" for f, i in zip(fold, te)])
        return permutation_p(pred, truth, units, strata)
    if kind == "pass":
        units = np.array([f"{f}|{i}" for f, i in zip(fold, te)])
        strata = np.array([f"{f}|{M['rec'][i]}" for f, i in zip(fold, te)])
        return permutation_p(pred, truth, units, strata)
    raise ValueError(kind)



# Refit each fold's SELECTED configuration restricted to a cohort, on the training side of that cohort only...
def cohort_curve(results: list, y: np.ndarray, M: dict) -> dict:
    people = sorted(set(y))
    out = {}
    for k in range(2, 7):
        accs = []
        for sub in itertools.combinations(people, k):
            corr_all = []
            for r in results:
                fc = _fconf_from_tag(r["config"])
                tr = np.array([i for i in _fold_tr(r, M) if y[i] in sub])
                te = np.array([i for i in r["te"] if y[i] in sub])
                if not len(te):
                    continue
                pred = fit_predict(fc, r["model"], tr, te, y[tr], M)
                corr_all += list(pred == y[te])
            accs.append(100 * float(np.mean(corr_all)))
        out[str(k)] = {"chance_pct": round(100 / k, 2), "mean_pct": round(float(np.mean(accs)), 2),
                       "min_pct": round(float(np.min(accs)), 2),
                       "max_pct": round(float(np.max(accs)), 2), "n_subsets": len(accs),
                       "above_50_mean": bool(np.mean(accs) > 50)}
    return out


# Function fconf from tag.
def _fconf_from_tag(tag: str) -> FConf:
    v, fs, ch, links, pc, norm = tag.split("/")
    return FConf(v, fs, ch, links, pc, norm)


_FOLD_TR: dict = {}


# Function register fold tr.
def register_fold_tr(folds: list) -> None:
    for f in folds:
        _FOLD_TR[f.tag] = f.tr


# Function fold tr.
def _fold_tr(r: dict, M: dict) -> np.ndarray:
    return _FOLD_TR[r["tag"]]
