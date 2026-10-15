"""ilb_core. The best-model run's candidates on this morning's combine scorecard (`runs/identify/best/POA_B.md`): for a
configuration (a "+"-joined set of F7, A1, A3, A4, A5, P1, P2, M2, M3), the five feature components of each of the nine
models retrained with it (each model's rows, cfg, seeds and speed column), scored by the feature-side scorer in the
replay's order; the CNN components are the shipped replays' (A4's offset windows from the GPU cache). Every scored
configuration is a look at A3 and B2 and is counted. Selection is on A3 and B2; nothing here is confirmatory.

    PYTHONPATH=. python3 -m pipeline.identify.ilb_core score --config P1
    PYTHONPATH=. python3 -m pipeline.identify.ilb_core summarise

Exploratory development, all data seen; selection on A3 and B2.
"""

from __future__ import annotations

import json
import os
import pickle
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import ilc_outer as CO
from pipeline.identify import ilp_cand as PC

BD = os.path.join("runs", "identify", "best")
OUTD = os.path.join(BD, "outer")
CB_OUT = os.path.join("runs", "identify", "combine", "outer")
TOKENS = {"F7": "f7", "A1": "a1", "A3": "a3", "A4": "a4", "A5": "a5", "P1": "p1", "P2": "p2", "M2": "m2", "M3": "m3"}
LABEL = "exploratory development, all data seen; selection on A3 and B2"


def flags_of(name: str) -> dict:
    f = {TOKENS[t]: True for t in name.split("+") if t in TOKENS}
    for t in name.split("+"):
        if t.startswith("CNN:"):
            f["cnn"] = t[4:]
    if f.get("a1"):
        f.pop("f7", None)                          # A1's dense offsets include F7's 0.15 and 0.30
    return f


# ------------------------------------------------------------------ training rows from the extractions

def _rows(paths: list, tr: np.ndarray, alpha: float, factor_key: str = None) -> dict:
    rows, F, sp, fac = [], [], [], []
    for p in paths:
        d = np.load(p, allow_pickle=True) if p.endswith(".npz") else pickle.load(open(p, "rb"))
        k = np.isin(d["rows"], tr)
        rows.append(np.asarray(d["rows"])[k])
        F.append(np.asarray(d["F"])[k])
        sp.append(np.asarray(d[f"speed_{alpha}"])[k])
        fac.append(np.asarray(d[factor_key])[k] if factor_key else np.ones(int(k.sum())))
    return {"rows": np.concatenate(rows), "F": np.vstack(F), "speed": np.concatenate(sp), "factor": np.concatenate(fac)}


def extra_rows(fl: dict, tr: np.ndarray, alpha: float) -> dict:
    S = ("A1", "A2", "A3", "B1", "B2")
    parts = []
    if fl.get("f7") or fl.get("a1"):
        parts.append(_rows([os.path.join("runs", "identify", "combine", "extract", "f7", f"{s}.npz") for s in S], tr, alpha))
    if fl.get("a1"):
        for g in ("dense0", "dense1"):
            parts.append(_rows([os.path.join(BD, "extract", g, f"{s}.pkl") for s in S], tr, alpha))
    if fl.get("a3"):
        parts.append(_rows([os.path.join(BD, "extract", "stretch", f"{s}.pkl") for s in S], tr, alpha, "factor"))
    if not parts:
        return None
    return {k: (np.vstack([p[k] for p in parts]) if k == "F" else np.concatenate([p[k] for p in parts])) for k in parts[0]}


# ------------------------------------------------------------------ training (idz_core.train's feature part, with the hooks)

def train_feat_b(F, v, tr, extra=None, mixup=False, m3=False, seed=0) -> dict:
    from pipeline.identify import idw_core as W
    b = PC.bank()
    a = b["a"]
    pk = a["path"].astype(str)
    n0 = len(tr)
    Fr, vr, pkr, sr, yr = F[tr], v[tr], pk[tr], a["session"][tr], a["anon"][tr]
    if extra is not None:
        src = extra["rows"]
        Fr, vr = np.vstack([Fr, extra["F"]]), np.r_[vr, extra["speed"]]
        pkr, sr, yr = np.r_[pkr, pk[src]], np.r_[sr, a["session"][src]], np.r_[yr, a["anon"][src]]
    mix = None
    if mixup:                                       # A5: partners among the original rows: same person, route, other day
        rng = np.random.default_rng(seed)
        pi, pj, lam = [], [], []
        for i in range(n0):
            cand = np.flatnonzero((yr[:n0] == yr[i]) & (pkr[:n0] == pkr[i]) & (sr[:n0] != sr[i]))
            if len(cand):
                pi.append(i)
                pj.append(int(rng.choice(cand)))
                lam.append(float(rng.uniform(0.2, 0.8)))
        mix = (np.array(pi, int), np.array(pj, int), np.array(lam))
    out = {}
    for comp, (head, norm, pace) in W.FEAT.items():
        Xf = np.c_[Fr, vr] if pace else Fr
        if norm == "perpath":
            st = W.PerPath().fit(Xf, pkr)
            A = st.transform(Xf, pkr)
        else:
            st = W.Prior()
            A = st.fit(Xf, pkr, sr)
        Afit, yfit = A, yr
        if mix is not None and len(mix[0]):
            i, j, l_ = mix
            Afit = np.vstack([A, l_[:, None] * A[i] + (1 - l_[:, None]) * A[j]])
            yfit = np.r_[yr, yr[i]]
        clf = PC.make_head(head).fit(Afit, yfit)
        out[comp] = {"state": st, "clf": clf, "classes": list(clf.classes_)}
        if m3 and comp == "rf_pace_prior":
            from sklearn.ensemble import HistGradientBoostingClassifier
            hgb = HistGradientBoostingClassifier(random_state=0).fit(Afit, yfit)
            out["_hgb"] = {"state_of": "rf_pace_prior", "clf": hgb, "classes": list(hgb.classes_)}
    if "_hgb" in out:
        out["hgb_pace_prior"] = out.pop("_hgb")
    return out


# ------------------------------------------------------------------ scoring, with A4's offset windows

def _comp_row(models, row, path, P, n):
    """`Session.classify`'s feature part for one window against pool P (n earlier windows of its layout)."""
    from pipeline.identify import idv2_core as C
    from pipeline.identify import idw_core as W
    from pipeline.identify import idx_loso as L
    out, hidden = {}, {}
    for comp, d in models.items():
        base = d.get("state_of", comp)
        _h, norm, pace = W.FEAT[base]
        r = np.r_[row[0], row[1]] if pace else row[0]
        if norm == "perpath":
            Bm = d["state"].transform(r[None, :], np.array([path]))
        elif base in hidden:
            Bm = hidden[base]
        else:
            if n:
                pool = np.c_[np.asarray(P["X"]), np.asarray(P["speed"])] if pace else np.asarray(P["X"])
                Xall = np.vstack([pool, r[None, :]])
                paths = np.array(P["paths"] + [path])
                calib = np.arange(n)
            else:
                Xall, paths, calib = r[None, :], np.array([path]), None
            Bm = models[base]["state"].apply(Xall, paths, np.array([len(Xall) - 1]), calib)
            hidden[base] = Bm
        out[comp] = L._order(C.logp_from_proba(d["clf"].predict_proba(Bm)), d["classes"])[0]
    return out


def score_feat_b(models, F, v, fd, tta=None, own_speed=True) -> dict:
    """{window: {component: (n, 6)}} for window 0 and, with `tta`, the 0.15 and 0.30 s windows (each classified against
    the same pool of earlier offset-0 windows; only offset 0 enters the pool). An offset window carries its own Wi-Fi
    speed (as the engine would compute it); under P1 or P2 (`own_speed` False) the walk's pace value."""
    te, pu, lay = fd["te"], fd["path_used"], fd["layout"]
    wins = ["0"] + (sorted(tta) if tta else [])
    out = {w: {c: np.zeros((len(te), 6)) for c in models} for w in wins}
    pools = {}
    for j, i in enumerate(te):
        P = pools.setdefault(lay[j], {"X": [], "speed": [], "paths": []})
        n = len(P["X"])
        for c, val in _comp_row(models, (F[i], v[i]), str(pu[j]), P, n).items():
            out["0"][c][j] = val
        for w in wins[1:]:
            f_o, path_o, v_o = tta[w][int(i)]
            for c, val in _comp_row(models, (f_o, v_o if own_speed else v[i]), path_o, P, n).items():
                out[w][c][j] = val
        P["X"].append(F[i])
        P["speed"].append(v[i])
        P["paths"].append(str(pu[j]))
    return out


def tta_windows(session: str, alpha: float) -> dict:
    d = pickle.load(open(os.path.join(BD, "extract", "tta", f"{session}.pkl"), "rb"))
    out = {}
    for r, o, f, p, sp in zip(d["rows"], d["offset"], d["F"], d["path_used"], d[f"speed_{alpha}"]):
        out.setdefault(f"{o:.2f}", {})[int(r)] = (f, str(p), float(sp))
    return out


_M2 = {}


def m2_weights() -> dict:
    """M2: the feature components' weight (0, 0.5, 1, 2; CNN weight 1) per walk type, chosen on last night's development
    folds with v4's components: path walks on A1, A2 and B1 path; identification walks on B1 natural; ties go to 1."""
    if _M2:
        return _M2
    PC.load_folds()
    res = {}
    for typ, cells in (("path", [("D1", "path"), ("D2", "path"), ("D3", "path")]), ("id", [("D3", "natural")])):
        best, bw = -1, 1.0
        for w in (1.0, 0.0, 0.5, 2.0):
            accs = []
            for f, cell in cells:
                fd = PC.FD[f]
                comps = {c: fd[f"c_{c}"] for c in PC.FEATC + PC.CNNC}
                lp = PC.ensemble(comps, {c: w for c in PC.FEATC})
                m = PC.cells(f, fd["te"])[cell]
                accs.append(PC.accuracy(lp, fd["te"])[m].mean())
            if np.mean(accs) > best + 1e-12:
                best, bw = float(np.mean(accs)), w
        res[typ] = bw
    _M2.update(res)
    json.dump(res | {"built": time.strftime("%Y-%m-%d %H:%M:%S"), "label": LABEL},
              open(os.path.join(BD, "m2_weights.json"), "w"), indent=1)
    return _M2


def ens_multi_b(fl: dict, model: str, sessions: list, flags: list) -> dict:
    from pipeline.identify import idv2_core as C
    from pipeline.identify import ilb_p1 as P1
    b = PC.bank()
    zs = {s: np.load(os.path.join(CO.REP, f"{model}_{s}_T4.0.npz")) for s in sessions}
    cnn = {s: {c: z[f"c_{c}"] for c in PC.CNNC} for s, z in zs.items()}
    if fl.get("cnn"):
        for s in sessions:
            g = np.load(os.path.join(BD, "cnn", fl["cnn"], f"{model}_{s}.npz"))
            assert np.array_equal(g["te"], zs[s]["te"])
            cnn[s] = {c: g[f"c_{c}"] for c in PC.CNNC}
    fds = {s: {"te": z["te"], "path_used": z["path_used"],
               "layout": np.where(b["kind"][z["te"]] == "idcap", "id_spot", "home")} for s, z in zs.items()}
    tr = np.load(os.path.join(CO.mdir(model), "train_rows.npy"))
    v, alpha = CO.speed_col(model)
    if fl.get("p1"):
        pv, why = P1.pace_column(sorted(set(b["a"]["session"][tr])), alpha)
        if pv is None:
            flags.append(f"{model}: P1 {why}")
        else:
            v = pv
    if fl.get("p2"):
        from pipeline.identify import ilb_p2 as P2
        v = P2.pace_column(model, v, flags)
    if fl.get("a5") and len(set(b["a"]["session"][tr])) < 2:
        flags.append(f"{model}: A5 has no partner on one training day; no mixed rows")
    extra = extra_rows(fl, tr, alpha)
    if extra is not None and (fl.get("p1") or fl.get("p2")):
        pth = b["kind"][extra["rows"]] == "track"             # path rows: the source walk's pace value (scaled for A3)
        extra["speed"] = np.where(pth, v[extra["rows"]] / extra["factor"], extra["speed"])
    models = train_feat_b(b["F"], v, tr, extra, mixup=bool(fl.get("a5")), m3=bool(fl.get("m3")))
    w_feat = {"path": 1.0, "id": 1.0}
    if fl.get("m2"):
        test_sessions = set(sessions)
        if test_sessions <= {"A3", "B2"}:
            w_feat = m2_weights()
        else:
            flags.append(f"{model}: M2 not applied (its test session is a development session; choosing weights there "
                         f"would use the test day's labels)")
    out = {}
    for s in sessions:
        tta = None
        if fl.get("a4"):
            tta = tta_windows(s, alpha)
            cache = np.load(os.path.join(BD, "a4cache", f"{model}_{s}.npz"))
            assert np.array_equal(cache["te"], zs[s]["te"])
        comps = score_feat_b(models, b["F"], v, fds[s], tta, own_speed=not (fl.get("p1") or fl.get("p2")))
        ens = []
        for wn, cm in comps.items():
            cn = cnn[s] if wn == "0" else {c: cache[f"c_{c}_{wn}"] for c in PC.CNNC}
            is_path = b["kind"][fds[s]["te"]] == "track"
            wv = np.where(is_path, w_feat["path"], w_feat["id"])[:, None]
            allc = cm | cn
            s_ = sum((wv if c not in PC.CNNC else 1.0) * allc[c] for c in allc)
            ens.append(C.normalise_logp(s_))
        out[s] = C.normalise_logp(np.mean(ens, axis=0)) if len(ens) > 1 else ens[0]
    return out


def correct_all_b(fl: dict, flags: list) -> dict:
    out = {}
    for m, (model, sessions) in CO.MODELS.items():
        lps = ens_multi_b(fl, model, sessions, flags)
        for s in sessions:
            te = np.load(os.path.join(CO.REP, f"{model}_{s}_T4.0.npz"))["te"]
            out[f"{m}|{s}"] = (te, PC.accuracy(lps[s], te), lps[s])
        print(f"{time.strftime('%H:%M:%S')} {model}: {sessions}", flush=True)
    return out


def looks_add(name: str) -> int:
    lk = os.path.join(BD, "looks.lock")
    while True:
        try:
            os.mkdir(lk)
            break
        except FileExistsError:
            time.sleep(0.2)
    try:
        return _looks_add(name)
    finally:
        os.rmdir(lk)


def _looks_add(name: str) -> int:
    p = os.path.join(BD, "looks.json")
    d = json.load(open(p)) if os.path.exists(p) else {"label": LABEL, "configurations": {}}
    d["configurations"][name] = {"date": time.strftime("%Y-%m-%d %H:%M:%S"),
                                 "A3": ["xr_AB", "xr_ABtrk", "xr_A", "xr_B1", "loso_A3"],
                                 "B2": ["xr_AB", "xr_ABtrk", "xr_A", "xr_B1", "loso_B2"]}
    d["n_configurations"] = len(d["configurations"])
    d["model_session_looks_A3"] = 5 * d["n_configurations"]
    d["model_session_looks_B2"] = 5 * d["n_configurations"]
    json.dump(d, open(p, "w"), indent=1)
    return d["n_configurations"]


def score(name: str) -> str:
    fl = flags_of(name)
    flags = []
    st = correct_all_b(fl, flags)
    os.makedirs(OUTD, exist_ok=True)
    CO.OUTD = OUTD
    p = CO.save(name, st, flags)
    n = looks_add(name)
    print(f"{time.strftime('%H:%M:%S')} {name}: scored ({p}); flags {flags}; configurations counted {n}", flush=True)
    return p


def check_f7() -> bool:
    """This path with F7 alone equals this morning's F7 scoring (`ilc_outer`, combine/outer/F7.npz) on every model and
    session (a reproduction of a configuration already scored: no new look)."""
    flags = []
    st = correct_all_b(flags_of("F7"), flags)
    CO.OUTD = CB_OUT
    ref = CO.load("F7")
    diff = {k: float(np.abs(st[k][2] - ref[k][2]).max()) for k in ref}
    same = {k: bool(np.array_equal(st[k][0], ref[k][0])) for k in ref}
    res = {"what": "F7 through ilb_core against combine/outer/F7.npz", "max_abs_diff": diff, "same_rows": same,
           "built": time.strftime("%Y-%m-%d %H:%M:%S")}
    res["PASSED"] = max(diff.values()) <= 1e-9 and all(same.values())
    os.makedirs(os.path.join(BD, "checks"), exist_ok=True)
    json.dump(res, open(os.path.join(BD, "checks", "f7_reproduction.json"), "w"), indent=1)
    print(json.dumps({"max": max(diff.values()), "PASSED": res["PASSED"]}), flush=True)
    return res["PASSED"]


# ------------------------------------------------------------------ the summary

PER_SESSION = [("loso", "B1", "natural"), ("loso", "B2", "natural"), ("loso", "B1", "slow"), ("loso", "B2", "slow"),
               ("loso", "B1", "fast"), ("loso", "B2", "fast")] + [("loso", s, "path") for s in ("A1", "A2", "A3", "B1", "B2")]


def cell_rows_b(c, store: dict) -> tuple:
    """`ilc_outer.cell_rows`, and a loso cell of one session (its own fold only)."""
    m, s, kind = c
    if m != "loso" or s == "*":
        return CO.cell_rows(c, store)
    b = PC.bank()
    te, ok, lp = store[f"loso_{s}|{s}"]
    msk = (b["kind"][te] == "track") if kind == "path" else ((b["kind"][te] == "idcap") & (b["block"][te] == kind))
    return te[msk], ok[msk], lp[msk]


def s0_session(c) -> np.ndarray:
    """S0 on one loso session's cell, as `ilc_outer.s0_cell`."""
    from pipeline.identify import ixr_eval as XE
    a = XE.labels()
    b = PC.bank()
    _m, x, kind = c
    z = np.load(os.path.join(CO.REP, f"loso_{x}_v4_{x}_T4.0.npz"))
    te = z["te"]
    msk = (b["kind"][te] == "track") if kind == "path" else ((b["kind"][te] == "idcap") & (b["block"][te] == kind))
    if kind == "path":
        tr = np.load(os.path.join(CO.mdir(f"loso_{x}_v4"), "train_rows.npy"))
    else:
        tr = np.flatnonzero((a["session"] == ("B1" if x == "B2" else "B2")) & (a["kind"] == "idcap"))
    return XE.correct(XE.lda_one(a, "press_speed_m_s", tr, te[msk]), a["anon"][te[msk]])


def s0_natural_lp() -> np.ndarray:
    """S0's log-probabilities on the loso natural walks (B1 then B2, `cell_rows`' order) for the ranking measures."""
    from pipeline.identify import ixr_eval as XE
    a = XE.labels()
    b = PC.bank()
    out = []
    for x in ("A1", "A2", "A3", "B1", "B2"):
        te = np.load(os.path.join(CO.REP, f"loso_{x}_v4_{x}_T4.0.npz"))["te"]
        msk = (b["kind"][te] == "idcap") & (b["block"][te] == "natural")
        if msk.any():
            tr = np.flatnonzero((a["session"] == ("B1" if x == "B2" else "B2")) & (a["kind"] == "idcap"))
            out.append(XE.lda_one(a, "press_speed_m_s", tr, te[msk]))
    return np.vstack(out)

def summarise() -> dict:
    """Every scored configuration against v4 and F7 (this morning's files): Z, D, (Z + D) / 2 with paired bootstrap
    intervals (10,000 draws, seed 0, participants jointly), the guard, every cell with v4 and S0."""
    import glob
    b = PC.bank()
    who_all = b["a"]["anon"]
    counts = CO.boot_counts()
    CO.OUTD = CB_OUT
    ref = {"v4": CO.load("v4"), "F7": CO.load("F7")}
    CO.OUTD = OUTD
    names = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(OUTD, "*.npz")))
    s0 = {CO.key(c): CO.s0_cell(c) for c in CO.ZERO + CO.CROSS + CO.GUARD + CO.EXTRA}
    for c in PER_SESSION:
        s0[CO.key(c)] = s0_session(c)
    s0_nat_lp = s0_natural_lp()
    res = {"label": LABEL, "built": time.strftime("%Y-%m-%d %H:%M:%S"), "configs": {}}

    def zd(st):
        pp = {"Z": [], "D": []}
        for g, cells in (("Z", CO.ZERO), ("D", CO.CROSS)):
            for c in cells:
                rows, ok, _ = CO.cell_rows(c, st)
                w = who_all[rows]
                pp[g].append(CO.per_part(ok, w))
        return pp

    refpp = {k: zd(v) for k, v in ref.items()}

    def boot(pp):
        return {g: np.mean([(counts @ a_[0]) / (counts @ a_[1]) for a_ in pp[g]], axis=0) for g in ("Z", "D")}

    def point(pp):
        return {g: float(np.mean([a_[0].sum() / a_[1].sum() for a_ in pp[g]])) for g in ("Z", "D")}
    refb = {k: boot(v) for k, v in refpp.items()}
    refp = {k: point(v) for k, v in refpp.items()}
    for name in ["v4", "F7"] + names:
        st = ref.get(name) or CO.load(name)
        pp = refpp.get(name) or zd(st)
        bb, pt = boot(pp), point(pp)
        rec = {"Z": round(100 * pt["Z"], 2), "D": round(100 * pt["D"], 2), "score": round(50 * (pt["Z"] + pt["D"]), 2)}
        for r in ("v4", "F7"):
            for g in ("Z", "D"):
                d = bb[g] - refb[r][g]
                lo, hi = np.percentile(d, [2.5, 97.5])
                rec[f"{g}_minus_{r}"] = {"pct": round(100 * (pt[g] - refp[r][g]), 2), "ci95": [round(100 * lo, 2), round(100 * hi, 2)]}
            sc = (bb["Z"] + bb["D"]) / 2 - (refb[r]["Z"] + refb[r]["D"]) / 2
            lo, hi = np.percentile(sc, [2.5, 97.5])
            rec[f"score_minus_{r}"] = {"pct": round(50 * (pt["Z"] + pt["D"] - refp[r]["Z"] - refp[r]["D"]), 2),
                                       "ci95": [round(100 * lo, 2), round(100 * hi, 2)]}
        from pipeline.identify import idw_eval as EV
        from pipeline.identify import ixr_eval as XE
        cells = {}
        for c in CO.ZERO + CO.CROSS + CO.GUARD + CO.EXTRA + PER_SESSION:
            rows, ok, lp = cell_rows_b(c, st)
            ok0, ok7 = cell_rows_b(c, ref["v4"])[1], cell_rows_b(c, ref["F7"])[1]
            w = who_all[rows]
            cells[CO.key(c)] = {"n": int(len(rows)), "new": EV._boot(ok, w), "v4": round(100 * float(ok0.mean()), 2),
                                "F7": round(100 * float(ok7.mean()), 2), "S0": round(100 * float(s0[CO.key(c)].mean()), 2),
                                "new_minus_v4": XE.paired(ok, ok0, w), "new_minus_F7": XE.paired(ok, ok7, w)}
        rec["cells"] = cells
        rec["guard"] = all(cells[k]["new"]["pct"] >= cells[k]["v4"] - 5 for k in ("loso|*|natural", "loso|*|slow", "loso|*|fast"))
        zl, dl = rec["Z_minus_v4"], rec["D_minus_v4"]
        rec["verdict_vs_v4"] = ("reference" if name == "v4" else "BETTER" if zl["ci95"][0] > 0 and dl["ci95"][0] > 0 and rec["guard"]
                                else "HIGHER, NOT SEPARABLE" if zl["pct"] > 0 and dl["pct"] > 0 and rec["guard"] else "NOT BETTER")
        rows, _o, lp = CO.cell_rows(("loso", "*", "natural"), st)
        w = who_all[rows]
        rk = CO.ranking(lp, w)
        rk0 = CO.ranking(CO.cell_rows(("loso", "*", "natural"), ref["v4"])[2], w)
        rks = CO.ranking(s0_nat_lp, w)
        rec["ranking"] = {m: {"new": EV._boot(rk[m], w), "v4": round(100 * float(rk0[m].mean()), 2),
                              "S0": round(100 * float(rks[m].mean()), 2), "new_minus_v4": XE.paired(rk[m], rk0[m], w)}
                          for m in ("top2", "group2")}
        rec["top2"], rec["group2"] = rec["ranking"]["top2"]["new"]["pct"], rec["ranking"]["group2"]["new"]["pct"]
        if name not in ("v4", "F7"):
            rec["flags"] = json.load(open(os.path.join(OUTD, f"{name}.json")))["flags"]
        res["configs"][name] = rec
    res["n_configurations_scored_here"] = len(names)
    json.dump(res, open(os.path.join(BD, "scorecard.json"), "w"), indent=1, default=str)
    lines = ["| configuration | Z | D | (Z+D)/2 | minus v4 [95 %] | minus F7 [95 %] | guard |", "|---|---|---|---|---|---|---|"]
    for n, r in sorted(res["configs"].items(), key=lambda kv: -kv[1]["score"]):
        a_, f_ = r["score_minus_v4"], r["score_minus_F7"]
        lines.append(f"| {n} | {r['Z']:.2f} | {r['D']:.2f} | {r['score']:.2f} | {a_['pct']:+.2f} [{a_['ci95'][0]:+.2f}, "
                     f"{a_['ci95'][1]:+.2f}] | {f_['pct']:+.2f} [{f_['ci95'][0]:+.2f}, {f_['ci95'][1]:+.2f}] | "
                     f"{'holds' if r['guard'] else 'FAILS'} |")
    open(os.path.join(BD, "scorecard.md"), "w").write("\n".join(lines))
    print("\n".join(lines), flush=True)
    return res


# ------------------------------------------------------------------ the greedy build (rounds appended to the CPU queue)

ORDER = ("F7", "A1", "A3", "A4", "A5", "P1", "M2", "M3", "P2")
CPU_CANDS = ("A1", "A3", "A4", "A5", "P1", "M2", "M3")          # P2 OFF in the build (Uzayr's toggle); P2 ON afterwards
PYS = "/opt/anaconda3/bin/python3"
Q = os.path.join(BD, "STEPS_CPU1")


def canon(tokens) -> str:
    t = set(tokens)
    if "A1" in t:
        t.discard("F7")                            # A1's dense offsets include F7's 0.15 and 0.30 s
    return "+".join(x for x in ORDER if x in t) or "v4"


def point(name: str) -> dict:
    """(Z, D, (Z + D) / 2, guard) point figures of a scored configuration (this run's or this morning's v4 and F7)."""
    CO.OUTD = CB_OUT if name in ("v4", "F7") else OUTD
    st = CO.load(name)
    CO.OUTD = CB_OUT
    v4 = CO.load("v4")
    z = np.mean([CO.cell_rows(c, st)[1].mean() for c in CO.ZERO])
    d = np.mean([CO.cell_rows(c, st)[1].mean() for c in CO.CROSS])
    g = all(CO.cell_rows(c, st)[1].mean() >= CO.cell_rows(c, v4)[1].mean() - 0.05 for c in CO.GUARD)
    CO.OUTD = OUTD
    return {"Z": round(100 * z, 2), "D": round(100 * d, 2), "score": round(50 * (z + d), 4), "guard": bool(g)}


def _steps(cfgs: list, tag: str) -> list:
    out = []
    for c in cfgs:
        cmd = f"{BD}/slot.sh {PYS} -m pipeline.identify.ilb_core score --config {c}"
        if "A4" in c:
            cmd = f"{BD}/waitfiles.sh {BD}/a4cache/DONE {BD}/a4cache/FAILED -- " + cmd
        out.append(f"PSTEP {tag}_{c} 6 0.3 0.2 {cmd}")
    out.append("PWAIT")
    a4ok = os.path.exists(os.path.join(BD, "a4cache", "DONE"))
    for c in cfgs:
        if "A4" not in c or a4ok:
            out.append(f"STEP expect_{tag}_{c} 6 0.3 0.2 {PYS} -m pipeline.identify.ilp_expect file {OUTD}/{c}.npz")
    return out


def next_round(r: int) -> None:
    """Round r of the greedy build: read round r - 1, choose, and append round r's steps (or the end) to the CPU queue.
    A candidate whose configuration is missing (A4 without its GPU cache) is dropped and logged."""
    gp = os.path.join(BD, "greedy.json")
    G = json.load(open(gp)) if os.path.exists(gp) else {"label": LABEL, "rounds": [], "current": ["F7"]}
    cur = G["current"]
    base = point(canon(cur))
    tried = {}
    for x in CPU_CANDS:
        if x in cur or (x == "A1" and "A1" in cur):
            continue
        c = canon(cur + [x])
        if c == canon(cur):
            continue
        if os.path.exists(os.path.join(OUTD, f"{c}.npz")):
            tried[x] = {"config": c, **point(c)}
        else:
            tried[x] = {"config": c, "missing": True}
    ok = {x: t for x, t in tried.items() if not t.get("missing") and t["guard"] and t["score"] > base["score"] + 1e-9}
    rec = {"round": r - 1, "date": time.strftime("%Y-%m-%d %H:%M:%S"), "current": canon(cur), "current_point": base,
           "tried": tried}
    lines = [f"# greedy round {r} (appended by ilb_core next at {time.strftime('%H:%M:%S')})"]
    if ok:
        best = max(ok, key=lambda x: ok[x]["score"])
        rec["chosen"] = best
        cur = cur + [best]
        G["current"] = cur
        nxt = [canon(cur + [x]) for x in CPU_CANDS if x not in cur and canon(cur + [x]) != canon(cur)]
        nxt = [c for c in dict.fromkeys(nxt) if not os.path.exists(os.path.join(OUTD, f"{c}.npz"))]
        if nxt:
            lines += _steps(nxt, f"g{r}")
        lines.append(f"STEP next_{r + 1} 6 0.3 0.2 {PYS} -m pipeline.identify.ilb_core next --round {r + 1}")
    else:
        rec["chosen"] = None
        G["winner"] = canon(cur)
        on = [c for c in dict.fromkeys([canon(cur + ["P2"])]) if not os.path.exists(os.path.join(OUTD, f"{c}.npz"))]
        lines.append(f"# greedy stops: winner {canon(cur)}; P2 ON on the winner, then the summary")
        if on:
            lines += _steps(on, "p2on")
        lines.append(f"STEP summarise 6 0.3 0.2 {PYS} -m pipeline.identify.ilb_core summarise")
        lines.append(f"STEP expect_scorecard 6 0.3 0.2 {PYS} -m pipeline.identify.ilp_expect file {BD}/scorecard.json")
        lines.append("ENDBLOCK block 2 (greedy build) done")
    G["rounds"].append(rec)
    json.dump(G, open(gp, "w"), indent=1)
    with open(Q, "a") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps(rec, indent=1), flush=True)
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "score":
        score(sys.argv[sys.argv.index("--config") + 1])
    elif what == "summarise":
        summarise()
    elif what == "next":
        next_round(int(sys.argv[sys.argv.index("--round") + 1]))
    elif what == "check-f7":
        sys.exit(0 if check_f7() else 1)
    sys.exit(0)
