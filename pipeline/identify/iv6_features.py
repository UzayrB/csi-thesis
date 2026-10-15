"""iv6_features. Part 2 of Uzayr's components-and-features TEST (15 Oct 2026; rules in `runs/identify/engine/PLAN.md`,
Part 2's note, committed before any permuted score): what the 630 gait features use.

The offline path is engine v5's feature side exactly as `ilb_core.score_feat_b` replays it (each window standardised by
`idw_core`'s `Prior.apply` against the causal pool of earlier 0 s windows of its layout, `PerPath` for rf, the three
windows at 0, 0.15 and 0.30 s, hgb on rf_pace_prior's state), with one change of arithmetic order only: each component's
classifier is called once on the stacked rows instead of once per row. `equal` proves the output equals the stored
replays' `c_*` arrays (max abs difference 0.0) before anything is permuted. The CNN components are the stored arrays.

    PYTHONPATH=. python3 -m pipeline.identify.iv6_features equal          # the offline equality check (and its timing)
    PYTHONPATH=. python3 -m pipeline.identify.iv6_features permute        # 2a (and 2c's family + speed groups)
    PYTHONPATH=. python3 -m pipeline.identify.iv6_features analyse        # 2a's tables; 2b, 2c, 2d
    PYTHONPATH=. python3 -m pipeline.identify.iv6_features figure

Development evaluation, all data seen; exploratory.
"""

from __future__ import annotations

import json
import os
import pickle
import resource
import sys
import time

import numpy as np

from pipeline.identify import idv2_core as C
from pipeline.identify import idw_core as W
from pipeline.identify import idw_eval as EV
from pipeline.identify import idx_loso as L
from pipeline.identify import ilb_core as B
from pipeline.identify import ilc_outer as CO
from pipeline.identify import ilp_cand as PC
from pipeline.identify import iv6_common as K

P2 = os.path.join(K.OUT, "part2")
WINS = ("0", "0.15", "0.30")
SUFFIX = {"0": "", "0.15": "_0.15", "0.30": "_0.30"}
# the model-sessions Part 2 scores, with the layouts its cells need (pools are per layout, so the others never matter)
UNITS = (("xr_ABtrk", "A3", ("home",)), ("xr_ABtrk", "B2", ("home",)), ("xr_A", "B2", ("home", "id_spot")),
         ("loso_B1", "B1", ("id_spot",)), ("loso_B2", "B2", ("id_spot",)))
REPEATS = 20
# the LDA's batched call differs from the replay by up to 4.3e-14 (BLAS on a matrix against a row); called row by row it
# is exact (PLAN, Part 2 note: the pre-committed fallback; checks/offline_equal_batched_lda.json and offline_equal.json)
PER_ROW = ("lda_pace_prior",)
MEM_GUARD_GB = 13.0


def model_of(m: str) -> str:
    return K.MODELS[m][0]


# ------------------------------------------------------------------ groups of the 630 columns

def groups() -> dict:
    """{name: (column indices into the 630, whether the speed column joins)}; families from the names
    (`family|variant|link|sub|name`)."""
    names = PC.bank()["names"]
    fam = np.array([n.split("|")[0] for n in names])
    link = np.array([n.split("|")[2] for n in names])
    F = {"rhy": "rhythm", "tplacf": "cycle templates", "dop": "Doppler contours", "spec": "spectral shape",
         "wav": "wavelets", "mod": "modulation", "cad": "cadence"}
    out = {}
    for f, nm in F.items():
        out[nm] = (np.flatnonzero(fam == f), False)
    for f, nm in F.items():
        for lk in ("RX1", "RX2", "RX3"):
            out[f"{nm} {lk}"] = (np.flatnonzero((fam == f) & (link == lk)), False)
        cross = np.flatnonzero((fam == f) & ~np.isin(link, ["RX1", "RX2", "RX3"]))
        if len(cross):
            out[f"{nm} across links"] = (cross, False)
    for lk in ("RX1", "RX2", "RX3"):
        out[f"all families {lk}"] = (np.flatnonzero(link == lk), False)
    out["Wi-Fi speed"] = (np.array([], int), True)
    for f, nm in F.items():
        out[f"{nm} + Wi-Fi speed"] = (np.flatnonzero(fam == f), True)
    assert sum(len(out[nm][0]) for nm in F.values()) == 630
    return out


# ------------------------------------------------------------------ the exact offline feature side

def load_models(model: str) -> tuple:
    md = CO.mdir(model)
    models, njobs = {}, {}
    for c in K.FEATC:
        d = pickle.load(open(os.path.join(md, f"feat_{c}.pkl"), "rb"))
        if hasattr(d["clf"], "n_jobs"):
            njobs[c] = d["clf"].n_jobs
            d["clf"].n_jobs = 1
        models[c] = d
    return models, njobs


def inputs(m: str, s: str) -> dict:
    """One model-session's per-walk inputs for the three windows (features, Wi-Fi speed, path), in replay order."""
    b = PC.bank()
    model = model_of(m)
    z = np.load(os.path.join(K.REP, f"{model}_{s}_T4.0.npz"))
    te = z["te"]
    v, alpha = CO.speed_col(model)
    tta = B.tta_windows(s, alpha)
    X = {"0": b["F"][te].copy()}
    V = {"0": v[te].copy()}
    P = {"0": np.array([str(p) for p in z["path_used"]])}
    for w in WINS[1:]:
        X[w] = np.stack([tta[w][int(i)][0] for i in te]).astype(np.float64)
        V[w] = np.array([tta[w][int(i)][2] for i in te], float)
        P[w] = np.array([tta[w][int(i)][1] for i in te])
    lay = np.where(b["kind"][te] == "idcap", "id_spot", "home")
    stored = {w: {c: z[f"c_{c}{SUFFIX[w]}"] for c in K.COMPS} for w in WINS}
    return {"m": m, "s": s, "model": model, "te": te, "X": X, "V": V, "P": P, "lay": lay, "alpha": alpha,
            "a": z["weight_a"].astype(float), "stored": stored}


def score(models: dict, X: dict, V: dict, P: dict, lay: np.ndarray, keep: tuple, per_row: tuple = ()) -> tuple:
    """(walks scored, {window: {component: (n_kept, 6)}}). Bm rows exactly as `ilb_core._comp_row` builds them; each
    classifier then called once on its stacked rows (components in `per_row` called row by row instead)."""
    bases = {c: models[c].get("state_of", c) for c in models}
    order = [j for j in range(len(lay)) if lay[j] in keep]
    rows = {w: {bs: [] for bs in set(bases.values())} for w in WINS}
    pools = {}
    for j in order:
        Pl = pools.setdefault(lay[j], {"X": [], "speed": [], "paths": []})
        n = len(Pl["X"])
        poolX = np.asarray(Pl["X"]) if n else None
        poolXs = np.c_[poolX, np.asarray(Pl["speed"])] if n else None
        for w in WINS:
            g, vv, path = X[w][j], V[w][j], str(P[w][j])
            for bs in rows[w]:
                _h, norm, pace = W.FEAT[bs]
                r = np.r_[g, vv] if pace else g
                st = models[bs]["state"]
                if norm == "perpath":
                    Bm = st.transform(r[None, :], np.array([path]))
                else:
                    if n:
                        Xall = np.vstack([poolXs if pace else poolX, r[None, :]])
                        paths = np.array(Pl["paths"] + [path])
                        calib = np.arange(n)
                    else:
                        Xall, paths, calib = r[None, :], np.array([path]), None
                    Bm = st.apply(Xall, paths, np.array([len(Xall) - 1]), calib)
                rows[w][bs].append(Bm[0])
        Pl["X"].append(X["0"][j])
        Pl["speed"].append(V["0"][j])
        Pl["paths"].append(str(P["0"][j]))
    out = {}
    for w in WINS:
        out[w] = {}
        for c, d in models.items():
            Bm = np.asarray(rows[w][bases[c]])
            if c in per_row:
                pr = np.vstack([d["clf"].predict_proba(Bm[i:i + 1]) for i in range(len(Bm))])
            else:
                pr = d["clf"].predict_proba(Bm)
            out[w][c] = L._order(C.logp_from_proba(pr), d["classes"])
    return np.asarray(order, int), out


def rss_gb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9          # bytes on macOS


def equal(per_row: tuple = ()) -> bool:
    """The offline path on the unpermuted bank equals the stored replays' c_* (every feature component, every window;
    max abs difference 0.0) on every Part 2 unit, with the units' timing."""
    os.makedirs(os.path.join(K.OUT, "checks"), exist_ok=True)
    res = {"built": time.strftime("%Y-%m-%d %H:%M:%S"), "label": K.LABEL, "per_row": list(per_row), "units": {}}
    for m in sorted({u[0] for u in UNITS}, key=[u[0] for u in UNITS].index):
        t0 = time.time()
        models, njobs = load_models(model_of(m))
        t_load = time.time() - t0
        for (mm, s, keep) in UNITS:
            if mm != m:
                continue
            I = inputs(m, s)
            t1 = time.time()
            idx, out = score(models, I["X"], I["V"], I["P"], I["lay"], keep, per_row)
            dt = time.time() - t1
            diffs = {f"{c}{SUFFIX[w]}": float(np.abs(out[w][c] - I["stored"][w][c][idx]).max()) for w in WINS for c in K.FEATC}
            res["units"][f"{m}|{s}"] = {"walks": int(len(idx)), "layouts": list(keep), "max_abs_diff": max(diffs.values()),
                                        "diffs": diffs, "seconds_score": round(dt, 2), "seconds_load": round(t_load, 2),
                                        "n_jobs_stored": njobs, "max_rss_gb": round(rss_gb(), 2)}
            print(f"{time.strftime('%H:%M:%S')} {m}|{s}: {len(idx)} walks, max abs diff {max(diffs.values())}, "
                  f"{dt:.1f} s (load {t_load:.1f} s), rss {rss_gb():.2f} GB", flush=True)
        del models
    res["max_abs_diff"] = max(u["max_abs_diff"] for u in res["units"].values())
    res["PASSED"] = res["max_abs_diff"] == 0.0
    json.dump(res, open(os.path.join(K.OUT, "checks", "offline_equal.json"), "w"), indent=1)
    print(json.dumps({"max_abs_diff": res["max_abs_diff"], "PASSED": res["PASSED"]}), flush=True)
    return res["PASSED"]


# ------------------------------------------------------------------ 2a: grouped permutation importance

def ensemble_of(I: dict, idx: np.ndarray, feat: dict) -> np.ndarray:
    """v5's ensemble on walks idx: the (possibly permuted) feature components and the stored CNN components."""
    r = {"a": I["a"][idx], "c": {c: np.stack([(feat[w][c] if c in K.FEATC else I["stored"][w][c][idx]) for w in WINS])
                                 for c in K.COMPS}}
    return K.combine(r, {c: 1.0 for c in K.COMPS}, rule=True)["ensemble"]


def walk_stats(I: dict, idx: np.ndarray, feat: dict) -> dict:
    """Per walk: the ensemble's correctness and NLL, and each feature component's (walk level: the windows' mean)."""
    y = K.labels(I["te"][idx])
    E = ensemble_of(I, idx, feat)
    ar = np.arange(len(idx))
    out = {"ens_ok": (E.argmax(1) == y), "ens_nll": -E[ar, y]}
    for c in K.FEATC:
        lp = K.normalise(np.mean([feat[w][c] for w in WINS], axis=0))
        out[f"{c}_ok"] = lp.argmax(1) == y
        out[f"{c}_nll"] = -lp[ar, y]
    return out


def permuted(I: dict, keep: tuple, cols: np.ndarray, speed: bool, seed: list) -> tuple:
    """(X, V) with the group's columns (and the speed when asked) permuted across the walks of each kept layout; the
    same permutation for all three windows, applied before the pool sees anything."""
    X = {w: I["X"][w].copy() for w in WINS}
    V = {w: I["V"][w].copy() for w in WINS}
    for li, lay in enumerate(("home", "id_spot")):
        if lay not in keep:
            continue
        idx = np.flatnonzero(I["lay"] == lay)
        pi = idx[np.random.default_rng(np.random.SeedSequence(seed + [li])).permutation(len(idx))]
        for w in WINS:
            if len(cols):
                X[w][np.ix_(idx, cols)] = I["X"][w][np.ix_(pi, cols)]
            if speed:
                V[w][idx] = I["V"][w][pi]
    return X, V


def free_pct() -> float:
    import subprocess
    out = subprocess.run(["memory_pressure"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if "free percentage" in line:
            return float(line.split(":")[1].strip().rstrip("%"))
    return 100.0


def permute(only: list = None) -> None:
    """Every group x REPEATS repeats on every unit; per unit an npz of per-walk statistics (repeat-level arrays)."""
    os.makedirs(P2, exist_ok=True)
    G = groups()
    names = list(G)
    log = open(os.path.join(P2, "permute.log"), "a")

    def say(msg):
        line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
        print(line, flush=True)
        log.write(line + "\n")
        log.flush()
    say(f"start: {len(names)} groups x {REPEATS} repeats x {len(UNITS)} units; device cpu; nice {os.nice(0)}; "
        f"OMP_NUM_THREADS {os.environ.get('OMP_NUM_THREADS')}")
    for m in sorted({u[0] for u in UNITS}, key=[u[0] for u in UNITS].index):
        if only and m not in only:
            continue
        models, _nj = load_models(model_of(m))
        for (mm, s, keep) in UNITS:
            if mm != m:
                continue
            path = os.path.join(P2, f"{m}_{s}.npz")
            if os.path.exists(path):
                say(f"{m}|{s}: exists, skipped")
                continue
            I = inputs(m, s)
            idx, base = score(models, I["X"], I["V"], I["P"], I["lay"], keep, PER_ROW)
            for w in WINS:
                for c in K.FEATC:
                    assert np.array_equal(base[w][c], I["stored"][w][c][idx]), (m, s, w, c)
            b0 = walk_stats(I, idx, base)
            acc = {k: np.zeros((len(names), REPEATS, len(idx))) for k in b0}
            t0 = time.time()
            for gi, nm in enumerate(names):
                cols, sp = G[nm]
                for rep in range(REPEATS):
                    X, V = permuted(I, keep, cols, sp, [gi, rep, K.SESSIONS.index(s)])
                    _i, out = score(models, X, V, I["P"], I["lay"], keep, PER_ROW)
                    for k, v in walk_stats(I, idx, out).items():
                        acc[k][gi, rep] = v
                rss = rss_gb()
                fp = free_pct()
                say(f"{m}|{s}: group {gi + 1}/{len(names)} {nm} done ({time.time() - t0:.0f} s; rss max {rss:.2f} GB; "
                    f"free {fp:.0f} %)")
                if rss > MEM_GUARD_GB or fp < 30:
                    say(f"STOP: memory guard (rss {rss:.2f} GB, free {fp:.0f} %)")
                    raise SystemExit(3)
            np.savez(path, te=I["te"][idx], groups=np.array(names), **{f"base_{k}": v for k, v in b0.items()},
                     **{f"perm_{k}": v for k, v in acc.items()})
            say(f"{m}|{s}: saved {path}")
        del models
    say("end")


# ------------------------------------------------------------------ analysis

def boot_mean(values, who, n=10000, seed=0) -> dict:
    """The mean of `values` with a 95 % participant-bootstrap interval (`idw_eval._boot`'s resampling, unscaled)."""
    values, who = np.asarray(values, float), np.asarray(who)
    u = np.unique(who)
    s = np.array([values[who == p].sum() for p in u])
    c = np.array([(who == p).sum() for p in u])
    idx = np.random.default_rng(seed).integers(0, len(u), (n, len(u)))
    bs = s[idx].sum(1) / np.maximum(c[idx].sum(1), 1)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return {"mean": round(float(values.mean()), 4), "ci95": [round(float(lo), 4), round(float(hi), 4)], "n": int(len(values))}


def cells_2a() -> dict:
    """{cell: [(unit, mask on the unit's scored walks)]}."""
    b = PC.bank()

    def kind(blk):
        return lambda te: (b["kind"][te] == "idcap") & (b["block"][te] == blk)
    path = lambda te: b["kind"][te] == "track"                      # noqa: E731
    every = lambda te: np.ones(len(te), bool)                       # noqa: E731
    return {"xr_ABtrk A3+B2 path": [("xr_ABtrk|A3", path), ("xr_ABtrk|B2", path)],
            "xr_A all B2": [("xr_A|B2", every)],
            "core pooled": [("xr_ABtrk|A3", path), ("xr_ABtrk|B2", path), ("xr_A|B2", every)],
            "loso natural": [("loso_B1|B1", kind("natural")), ("loso_B2|B2", kind("natural"))],
            "loso slow": [("loso_B1|B1", kind("slow")), ("loso_B2|B2", kind("slow"))],
            "loso fast": [("loso_B1|B1", kind("fast")), ("loso_B2|B2", kind("fast"))]}


def analyse_2a() -> dict:
    b = PC.bank()
    Z = {f"{m}|{s}": np.load(os.path.join(P2, f"{m}_{s}.npz")) for m, s, _k in UNITS}
    names = list(Z["xr_A|B2"]["groups"])
    out = {"groups": names, "cells": {}}
    for cell, parts in cells_2a().items():
        te = np.concatenate([Z[u]["te"][f(Z[u]["te"])] for u, f in parts])
        who = b["a"]["anon"][te]

        def cat(key):
            return np.concatenate([Z[u][key][..., f(Z[u]["te"])] for u, f in parts], axis=-1)
        rec = {"n": int(len(te)), "base_ens_acc": round(100 * float(cat("base_ens_ok").mean()), 2), "groups": {}}
        rec["base_comp_acc"] = {c: round(100 * float(cat(f"base_{c}_ok").mean()), 2) for c in K.FEATC}
        for gi, nm in enumerate(names):
            g = {}
            d_ok = cat("base_ens_ok").astype(float) - cat("perm_ens_ok")[gi].mean(0)
            g["ens_acc_drop"] = EV._boot(d_ok, who)
            g["ens_acc_drop_repeats_sd"] = round(float(np.std(100 * (cat("base_ens_ok").mean() - cat("perm_ens_ok")[gi].mean(1)))), 3)
            g["ens_nll_rise"] = boot_mean(cat("perm_ens_nll")[gi].mean(0) - cat("base_ens_nll"), who)
            g["comp"] = {}
            for c in K.FEATC:
                g["comp"][c] = {"acc_drop": EV._boot(cat(f"base_{c}_ok").astype(float) - cat(f"perm_{c}_ok")[gi].mean(0), who),
                                "nll_rise": boot_mean(cat(f"perm_{c}_nll")[gi].mean(0) - cat(f"base_{c}_nll"), who)}
            rec["groups"][nm] = g
        out["cells"][cell] = rec
    return out


def person_or_day() -> dict:
    """2b: per family, naming the person across days (leave one session out) and the session or day (leave one
    participant out), the same classifier (the engine's random forest) on the same walks; raw (global per-path z, no
    session information removed) and session-standardised (each session per path with its own rows, the engine's
    prior); and per column the ICC of person and of person x day."""
    from pipeline.identify import idmax_eval as E
    b = PC.bank()
    a = b["a"]
    rows = np.flatnonzero(np.isin(a["session"], K.SESSIONS))
    F, sess, who, path = b["F"][rows], a["session"][rows], a["anon"][rows], a["path"][rows]
    room = np.array([s[0] for s in sess])
    fam = np.array([n.split("|")[0] for n in b["names"]])
    FAM = {"rhy": "rhythm", "tplacf": "cycle templates", "dop": "Doppler contours", "spec": "spectral shape",
           "wav": "wavelets", "mod": "modulation", "cad": "cadence"}

    def rep(kind_):
        if kind_ == "raw":
            st = W.PerPath().fit(F, path)
            return st.transform(F, path), np.flatnonzero(st.ok)[st.keep]
        st = W.Prior()
        Z = st.fit(F, path, sess)
        return Z, np.flatnonzero(st.ok)[st.keep]

    def bal(y, p):
        return round(100 * float(np.mean([np.mean(p[y == k] == k) for k in np.unique(y)])), 2)

    def cv(Z, y, grp):
        pred = np.empty(len(y), dtype=object)
        for g in np.unique(grp):
            te = grp == g
            if len(np.unique(y[~te])) < 2:
                pred[te] = y[~te][0]
                continue
            clf = E.make_model("rf").fit(Z[~te], y[~te])
            pred[te] = clf.predict(Z[te])
        return bal(y, pred)
    out = {"label": K.LABEL, "rows": int(len(rows)), "classifier": "RandomForestClassifier(300, sqrt, random_state 0)",
           "scores": "balanced accuracy, %", "chance": {"person": 16.67, "session": 20.0, "day in Room A": 33.33, "day in Room B": 50.0}}
    for kind_ in ("raw", "session-standardised"):
        Z, keep = rep(kind_)
        famk = fam[keep]
        out[kind_] = {}
        for f, nm in list(FAM.items()) + [("ALL", "all 630")]:
            cols = np.flatnonzero(famk == f) if f != "ALL" else np.arange(Z.shape[1])
            Zf = Z[:, cols]
            A = room == "A"
            Bm = room == "B"
            r = {"columns": int(len(cols)),
                 "person across days (leave one session out)": cv(Zf, who, sess),
                 "session (leave one participant out)": cv(Zf, sess, who),
                 "day in Room A (leave one participant out)": cv(Zf[A], sess[A], who[A]),
                 "day in Room B (leave one participant out)": cv(Zf[Bm], sess[Bm], who[Bm])}
            out[kind_][nm] = r
            print(f"{time.strftime('%H:%M:%S')} 2b {kind_} {nm}: {r}", flush=True)
    # variance shares per column (raw representation): person, person x day, residual
    Z, keep = rep("raw")
    famk = fam[keep]
    icc = {}
    for f, nm in list(FAM.items()) + [("ALL", "all 630")]:
        cols = np.flatnonzero(famk == f) if f != "ALL" else np.arange(Z.shape[1])
        vp, vd, ratio = [], [], []
        for j in cols:
            x = Z[:, j]
            tot = x.var()
            if tot <= 0:
                continue
            pm = {p: x[who == p].mean() for p in np.unique(who)}
            pdm = {(p, s): x[(who == p) & (sess == s)].mean() for p in np.unique(who) for s in K.SESSIONS
                   if ((who == p) & (sess == s)).any()}
            mu = x.mean()
            v_person = np.mean([(pm[p] - mu) ** 2 for p in who])
            v_day = np.mean([(pdm[(p, s)] - pm[p]) ** 2 for p, s in zip(who, sess)])
            vp.append(v_person / tot)
            vd.append(v_day / tot)
            ratio.append(v_person / v_day if v_day > 0 else np.inf)
        icc[nm] = {"columns": int(len(vp)), "person share median": round(float(np.median(vp)), 4),
                   "person x day share median": round(float(np.median(vd)), 4),
                   "person over person x day, median": round(float(np.median(ratio)), 4),
                   "columns where person > person x day": int(np.sum(np.array(ratio) > 1))}
    out["variance_shares_raw"] = icc
    return out


def speed_in_disguise() -> dict:
    """2c: per family, the columns' correlation with the Wi-Fi speed and the press-implied speed (median and largest
    |r|, columns above 0.3), and a cross-validated ridge R^2 (leave one session out) of each speed from the family."""
    from pipeline.identify import ixr_eval as XE
    from sklearn.linear_model import RidgeCV
    b = PC.bank()
    a = b["a"]
    lab = XE.labels()
    rows = np.flatnonzero(np.isin(a["session"], K.SESSIONS))
    st = W.PerPath().fit(b["F"][rows], a["path"][rows])
    Z = st.transform(b["F"][rows], a["path"][rows])
    fam = np.array([n.split("|")[0] for n in b["names"]])[np.flatnonzero(st.ok)[st.keep]]
    sess = a["session"][rows]
    FAM = {"rhy": "rhythm", "tplacf": "cycle templates", "dop": "Doppler contours", "spec": "spectral shape",
           "wav": "wavelets", "mod": "modulation", "cad": "cadence"}
    out = {"label": K.LABEL, "rows": int(len(rows))}
    for sp_name, sp in (("Wi-Fi speed", lab["wifi_speed"][rows]), ("press speed", lab["press_speed_m_s"][rows])):
        ok = np.isfinite(sp)
        rec = {"walks": int(ok.sum())}
        for f, nm in list(FAM.items()) + [("ALL", "all 630")]:
            cols = np.flatnonzero(fam == f) if f != "ALL" else np.arange(Z.shape[1])
            r = np.array([np.corrcoef(Z[ok, j], sp[ok])[0, 1] if Z[ok, j].std() > 0 else 0.0 for j in cols])
            pred = np.empty(ok.sum())
            Zf, y, s_ = Z[ok][:, cols], sp[ok], sess[ok]
            for g in np.unique(s_):
                te = s_ == g
                pred[te] = RidgeCV(alphas=np.logspace(-2, 4, 13)).fit(Zf[~te], y[~te]).predict(Zf[te])
            r2 = 1 - np.sum((y - pred) ** 2) / np.sum((y - y.mean()) ** 2)
            rec[nm] = {"median |r|": round(float(np.median(np.abs(r))), 3), "largest |r|": round(float(np.max(np.abs(r))), 3),
                       "columns |r| > 0.3": int(np.sum(np.abs(r) > 0.3)), "columns": int(len(cols)),
                       "ridge R2 (leave one session out)": round(float(r2), 3)}
        out[sp_name] = rec
    out["wifi_vs_press_r"] = round(float(np.corrcoef(lab["wifi_speed"][rows][np.isfinite(lab["press_speed_m_s"][rows])],
                                                     lab["press_speed_m_s"][rows][np.isfinite(lab["press_speed_m_s"][rows])])[0, 1]), 3)
    return out


def secondary_2d() -> dict:
    """2d (secondary only; biased measures): the forests' impurity importances and the LDA's standardised coefficients
    (the mean |coefficient| over the six classes), summed by family, averaged over the Part 2 models."""
    b = PC.bank()
    fam = np.array([n.split("|")[0] for n in b["names"]] + ["speed"])
    FAM = ["rhy", "tplacf", "dop", "spec", "wav", "mod", "cad", "speed"]
    out = {}
    for m in sorted({u[0] for u in UNITS}):
        models, _ = load_models(model_of(m))
        rec = {}
        for c in ("rf", "rf_prior", "rf_pace_prior", "et_pace_prior", "lda_pace_prior"):
            st = models[c]["state"]
            pace = W.FEAT[c][2]
            cols = np.arange(631 if pace else 630)[st.ok][st.keep]
            clf = models[c]["clf"]
            imp = np.abs(clf.coef_).mean(0) if c.startswith("lda") else clf.feature_importances_
            imp = imp / imp.sum()
            rec[c] = {f: round(float(imp[fam[cols] == f].sum()), 4) for f in FAM if (fam[cols] == f).any()}
        out[m] = rec
        del models
    return out


def analyse() -> None:
    res = {"label": K.LABEL, "built": time.strftime("%Y-%m-%d %H:%M:%S")}
    res["2a"] = analyse_2a()
    res["2c_correlations"] = speed_in_disguise()
    res["2d_secondary"] = secondary_2d()
    res["2b"] = person_or_day()
    json.dump(res, open(os.path.join(K.OUT, "part2.json"), "w"), indent=1, default=str)


def figure() -> None:
    """The ensemble accuracy drop when each family (and the Wi-Fi speed alone) is permuted, the two core cells side by side,
    95 % participant intervals; Okabe-Ito blue and orange (validated: CVD dE 29.2), orange hatched with a dark edge for
    greyscale; 15.92 x 4.4 cm, the report's figure style (STIX, 8 pt)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    r = json.load(open(os.path.join(K.OUT, "part2.json")))["2a"]["cells"]
    G = ["rhythm", "cycle templates", "Doppler contours", "spectral shape", "wavelets", "modulation", "cadence", "Wi-Fi speed"]
    lab = ["rhythm", "cycle\ntemplates", "Doppler\ncontours", "spectral\nshape", "wavelets", "modulation", "cadence", "Wi-Fi\nspeed"]
    cells = [("xr_ABtrk A3+B2 path", "A1+A2+B1 path walks to A3+B2 path walks", "#0072B2", None),
             ("xr_A all B2", "A1+A2 to all B2 walks", "#E69F00", "////")]
    plt.rcParams.update({"font.family": "STIXGeneral", "mathtext.fontset": "stix", "font.size": 8, "axes.labelsize": 8,
                         "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "pdf.fonttype": 42, "axes.linewidth": 0.6,
                         "xtick.major.width": 0.6, "ytick.major.width": 0.6, "hatch.linewidth": 0.6})
    W_CM, H_CM = 15.92, 4.4
    fig = plt.figure(figsize=(W_CM / 2.54, H_CM / 2.54))
    ax = fig.add_axes([0.075, 0.25, 0.915, 0.62])
    x = np.arange(len(G))
    bw = 0.36
    for k, (cell, name, col, hatch) in enumerate(cells):
        d = [r[cell]["groups"][g]["ens_acc_drop"] for g in G]
        y = np.array([v["pct"] for v in d])
        lo = y - np.array([v["ci95"][0] for v in d])
        hi = np.array([v["ci95"][1] for v in d]) - y
        xs = x + (k - 0.5) * bw
        ax.bar(xs, y, bw * 0.92, color=col, edgecolor="#333333", linewidth=0.5, hatch=hatch, label=name, zorder=2)
        ax.errorbar(xs, y, yerr=[lo, hi], fmt="none", ecolor="#222222", elinewidth=0.6, capsize=1.6, capthick=0.6, zorder=3)
    ax.axhline(0, color="#444444", linewidth=0.6, zorder=1)
    ax.set_xticks(x)
    ax.set_xticklabels(lab, linespacing=1.0)
    ax.tick_params(axis="x", length=0, pad=2)
    ax.set_ylabel("accuracy drop (points)")
    ax.yaxis.grid(True, color="#dddddd", linewidth=0.4, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, fontsize=7, frameon=False, handlelength=1.6,
              borderaxespad=0.2, columnspacing=2.0)
    fig.savefig(os.path.join(K.OUT, "id_feature_importance.pdf"))
    fig.savefig(os.path.join(K.OUT, "id_feature_importance_preview.png"), dpi=200)
    json.dump({"source": "runs/identify/v6_test/part2.json, 2a", "cells": [c[0] for c in cells], "groups": G,
               "size_cm": [W_CM, H_CM], "palette": "Okabe-Ito #0072B2, #E69F00 (hatched, dark edge)", "label": K.LABEL},
              open(os.path.join(K.OUT, "id_feature_importance.json"), "w"), indent=1)


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "figure":
        figure()
        sys.exit(0)
    if what == "equal":
        sys.exit(0 if equal(tuple(sys.argv[2:])) else 1)
    if what == "permute":
        permute(sys.argv[2:] or None)
        sys.exit(0)
    if what == "analyse":
        analyse()
        sys.exit(0)
    sys.exit(2)
