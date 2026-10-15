"""ilp_cand. The last push's candidates H3, F1 to F6, F8 and F9 on the development folds (`runs/identify/lastpush/
PREREG_LP.md`, sections 3 to 6): a trainer equivalent to `idz_core.train`'s feature part (with the candidates' hooks) and a
feature-side scorer that replays `engine.Session.classify`'s five feature components walk by walk (pools per layout, the
same `Prior.apply` / `PerPath.transform` calls and 10- and 3-walk rules), the three CNN components taken from the v4
baseline scoring of the same fold; the development score (DS) with its slow and fast guard.

    PYTHONPATH=. python3 -m pipeline.identify.ilp_cand selftest            # the scorer against loso_A1_v4's replay on A1
    PYTHONPATH=. python3 -m pipeline.identify.ilp_cand null                # the null switch on D1 (PREREG_LP section 4)
    PYTHONPATH=. python3 -m pipeline.identify.ilp_cand run H3 F1 F2 ...    # candidates, each its grid; dev.json

Exploratory development, all data seen; selection on A1, A2 and B1 only.
"""

from __future__ import annotations

import json
import os
import pickle
import sys
import time

import numpy as np
import warnings

from pipeline.identify import engine as EN
from pipeline.identify import ilp_score as PS
from pipeline.identify import ilp_train as LT

T = 4.0
CLASSES = ("P1", "P2", "P3", "P4", "P5", "P6")
CL = np.array(CLASSES)
FEATC = ("rf", "rf_prior", "rf_pace_prior", "et_pace_prior", "lda_pace_prior")
CNNC = ("cnn", "cnn_prior", "cnn_perlink_prior")
PACE = ("rf_pace_prior", "et_pace_prior", "lda_pace_prior")
TREES = ("rf", "rf_prior", "rf_pace_prior", "et_pace_prior")
OUT = os.path.join(LT.LP, "dev")
_B = {}


# ------------------------------------------------------------------ data

def bank() -> dict:
    """The v4 bank's raw features as the Session sees them (float64, the 630 v2 columns), speeds, labels, paths."""
    if not _B:
        from pipeline.identify import idx_loso as L
        b = L.load(EN.bank_dir(T))
        meta = json.load(open(os.path.join(EN.bank_dir(T), "meta.json")))["passes"]
        cols = EN.v2_columns(b["names"])
        L.register_variant("dev", b["X"], b["names"])
        _B.update({"F": b["X"][:, cols].astype(np.float64), "names": [b["names"][j] for j in cols], "a": b["a"],
                   "names_all": b["names"],
                   "speed": np.array([m["wifi_speed"] for m in meta], float),
                   "kind": np.array([m["kind"] for m in meta]), "block": np.array([m["block"] for m in meta]),
                   "layout": np.where((b["a"]["room"] == "B") & (b["a"]["kind"] == "idcap"), "id_spot", "home")})
    return _B


def fold(f: str) -> dict:
    """A development fold: its model, training rows and the v4 baseline scoring (order, paths, layouts, components)."""
    s, model = PS.FOLDS[f]
    z = np.load(os.path.join(PS.SC, f"v4_{f}_{s}.npz"))
    return {"name": f, "session": s, "model": model, "tr": np.load(os.path.join(model, "train_rows.npy")),
            **{k: z[k] for k in z.files}}


def cells(f: str, te: np.ndarray) -> dict:
    b = bank()
    k = b["kind"][te]
    out = {"path": k == "track"}
    if f == "D3":
        out.update({blk: (k == "idcap") & (b["block"][te] == blk) for blk in ("natural", "slow", "fast")})
    return out


# ------------------------------------------------------------------ training (idz_core.train's feature part)

def make_head(head: str, params: dict = None):
    from pipeline.identify import idmax_eval as E
    if not params or head == "lda":
        return E.make_model(head)
    from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
    cls = RandomForestClassifier if head == "rf" else ExtraTreesClassifier
    return cls(n_estimators=300, max_features=params.get("max_features", "sqrt"), max_depth=params.get("max_depth"),
               min_samples_leaf=params.get("min_samples_leaf", 1), random_state=0, n_jobs=1)


def path_keys(rows: np.ndarray, paths, layouts, by_layout: bool) -> np.ndarray:
    p = np.asarray(paths).astype(str)
    return np.char.add(np.char.add(p, "|"), np.asarray(layouts).astype(str)) if by_layout else p


def train_feat(F: np.ndarray, v: np.ndarray, tr: np.ndarray, opt: dict, extra: dict = None) -> dict:
    """The five feature components on rows `tr` of features F and speeds v (`idz_core.train`, parts "feat"); `extra`
    appends further training rows (F7's offset windows: their own features and speeds, the source rows' labels, paths,
    days)."""
    from pipeline.identify import idw_core as W
    b = bank()
    a = b["a"]
    labels = opt.get("labels", a["anon"])
    pk = path_keys(None, a["path"], b["layout"], opt.get("by_layout", False))
    Fr, vr, pkr, sr, yr = F[tr], v[tr], pk[tr], a["session"][tr], labels[tr]
    if extra is not None:
        src = extra["rows"]
        Fr, vr = np.vstack([Fr, extra["F"]]), np.r_[vr, extra["speed"]]
        pkr, sr, yr = np.r_[pkr, pk[src]], np.r_[sr, a["session"][src]], np.r_[yr, labels[src]]
    out = {}
    for comp, (head, norm, pace) in W.FEAT.items():
        Xf = np.c_[Fr, vr] if pace else Fr
        if norm == "perpath":
            st = W.PerPath().fit(Xf, pkr)
            A = st.transform(Xf, pkr)
        else:
            st = W.Prior()
            A = st.fit(Xf, pkr, sr)
        clf = make_head(head, opt.get("head_params") if comp in TREES else None).fit(A, yr)
        out[comp] = {"state": st, "clf": clf, "classes": list(clf.classes_)}
    return out


def f7_extra(tr: np.ndarray) -> dict:
    """F7: the offset windows (0.15 and 0.30 s) of the training rows, from `ilp_extract offsets`."""
    from pipeline.identify import ilp_extract as X
    parts = [np.load(os.path.join(X.X_DIR, "f7", f"{s}.npz")) for s in X.DEV_SESSIONS]
    rows = np.concatenate([p["rows"] for p in parts])
    keep = np.isin(rows, tr)
    return {"rows": rows[keep], "F": np.concatenate([p["F"] for p in parts])[keep],
            "speed": np.concatenate([p["speed"] for p in parts])[keep]}


def load_feat(model_dir: str) -> dict:
    return {c: pickle.load(open(os.path.join(model_dir, f"feat_{c}.pkl"), "rb")) for c in FEATC}


# ------------------------------------------------------------------ the feature-side scorer (Session.classify's feature part)

def apply_shrunk(st, Xall, paths, rows, calib, k):
    """`Prior.apply` with the pool's per-path statistics shrunk towards the training statistics (F3)."""
    Zr = st.Z(Xall[rows])
    if calib is None or len(calib) < 10:
        return (Zr - st.g_mu) / st.g_sd
    Zref, pref, prows = st.Z(Xall[calib]), paths[calib], paths[rows]
    out = np.empty_like(Zr)
    for p in np.unique(prows):
        m = prows == p
        rr = pref == p
        if rr.sum() < 3:
            rr = np.ones(len(pref), bool)
        n = rr.sum()
        mu = (n * Zref[rr].mean(0) + k * st.g_mu) / (n + k)
        sd = (n * Zref[rr].std(0) + k * st.g_sd) / (n + k)
        out[m] = (Zr[m] - mu) / np.where(sd > 1e-9, sd, st.g_sd)
    return out


def score_feat(models: dict, F: np.ndarray, v: np.ndarray, fd: dict, opt: dict) -> dict:
    """Every feature component's log-probabilities for the fold's test walks, in the replay's order, causal per layout."""
    from pipeline.identify import idv2_core as C
    from pipeline.identify import idw_core as W
    from pipeline.identify import idx_loso as L
    te, pu, lay = fd["te"], fd["path_used"], fd["layout"]
    keys = path_keys(None, pu, lay, opt.get("by_layout", False))
    pools = {}
    out = {c: np.zeros((len(te), 6)) for c in models}
    for j, i in enumerate(te):
        P = pools.setdefault(lay[j], {"X": [], "speed": [], "paths": []})
        n = len(P["X"])
        g = F[i]
        path = keys[j]
        hidden = {}
        for comp in models:
            d = models[comp]
            base = d.get("state_of", comp)
            head, norm, pace = W.FEAT[base]
            row = np.r_[g, v[i]] if pace else g
            if norm == "perpath":
                Bm = d["state"].transform(row[None, :], np.array([path]))
            else:
                if base in hidden:
                    Bm = hidden[base]
                else:
                    if n:
                        pool = np.c_[np.asarray(P["X"]), np.asarray(P["speed"])] if pace else np.asarray(P["X"])
                        Xall = np.vstack([pool, row[None, :]])
                        paths = np.array(P["paths"] + [path])
                        calib = np.arange(n)
                    else:
                        Xall, paths, calib = row[None, :], np.array([path]), None
                    st = models[base]["state"]
                    Bm = (apply_shrunk(st, Xall, paths, np.array([len(Xall) - 1]), calib, opt["shrink_k"]) if opt.get("shrink_k")
                          else st.apply(Xall, paths, np.array([len(Xall) - 1]), calib))
                    hidden[base] = Bm
            if "mlp" in d:
                out[comp][j] = d["mlp"](Bm)[0]
            else:
                out[comp][j] = L._order(C.logp_from_proba(d["clf"].predict_proba(Bm)), d["classes"])[0]
        P["X"].append(g)
        P["speed"].append(v[i])
        P["paths"].append(path)
    return out


def ensemble(comps: dict, weights: dict = None) -> np.ndarray:
    from pipeline.identify import idv2_core as C
    w = weights or {}
    return C.normalise_logp(sum(w.get(c, 1.0) * comps[c] for c in comps if w.get(c, 1.0) != 0))


def accuracy(lp: np.ndarray, te: np.ndarray) -> np.ndarray:
    return (CL[lp.argmax(1)] == bank()["a"]["anon"][te]).astype(float)


def ds_of(lps: dict) -> dict:
    """{fold: ensemble log-probabilities} -> the four DS cells, slow, fast and DS."""
    r = {}
    for f, lp in lps.items():
        fd = FD[f]
        c = accuracy(lp, fd["te"])
        for name, m in cells(f, fd["te"]).items():
            r[f"{fd['session']}_{name}"] = round(100 * float(c[m].mean()), 2)
    r["DS"] = round(float(np.mean([r["A1_path"], r["A2_path"], r["B1_path"], r["B1_natural"]])), 2)
    return r


FD = {}


def load_folds() -> None:
    for f in ("D1", "D2", "D3"):
        FD[f] = fold(f)


# ------------------------------------------------------------------ the candidates

def transform(cfg: dict, tr: np.ndarray) -> tuple:
    """(F, v) for a configuration, fitted on the training rows only."""
    b = bank()
    F, v = b["F"].copy(), b["speed"].copy()
    names = b["names"]
    if cfg.get("residual"):                                     # F1
        s = np.where(np.isfinite(v), v, np.nanmedian(v[tr]))
        for j in range(F.shape[1]):
            x = F[tr, j]
            ok = np.isfinite(x)
            if ok.sum() < 3 or np.var(s[tr][ok]) <= 0:
                continue
            bj = np.cov(x[ok], s[tr][ok], bias=True)[0, 1] / np.var(s[tr][ok])
            aj = x[ok].mean() - bj * s[tr][ok].mean()
            F[:, j] = F[:, j] - (aj + bj * s)
        if cfg.get("no_pace"):
            v = np.zeros_like(v)
    if cfg.get("drop_families"):                                # F5
        fam = np.array([n.split("|")[0] for n in names])
        F[:, np.isin(fam, cfg["drop_families"])] = 0.0
    if cfg.get("icc_k"):                                        # F4
        keep = icc_top(F, tr, cfg["icc_k"])
        F[:, ~keep] = 0.0
    return F, v


def icc_top(F: np.ndarray, tr: np.ndarray, k: int) -> np.ndarray:
    """Top k columns by cross-day ICC on the training rows (per-path z-scores, person-and-day means)."""
    a = bank()["a"]
    Z = np.full((len(tr), F.shape[1]), np.nan)
    paths = a["path"][tr]
    for p in np.unique(paths):
        m = paths == p
        x = F[tr][m]
        Z[m] = (x - np.nanmean(x, 0)) / np.where(np.nanstd(x, 0) > 1e-12, np.nanstd(x, 0), np.nan)
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    who, day = a["anon"][tr], a["session"][tr]
    days = np.unique(day)
    assert len(days) >= 2, "F4 needs two training days"
    M = np.array([[np.nanmean(Z[(who == p) & (day == d)], 0) for d in days] for p in CLASSES])   # people x days x cols
    between = np.nanvar(np.nanmean(M, 1), 0)
    within = np.nanmean(np.nanvar(M, 1), 0)
    icc = np.where(within > 0, between / within, 0.0)
    icc = np.where(np.isfinite(icc), icc, -np.inf)
    keep = np.zeros(F.shape[1], bool)
    keep[np.argsort(-icc, kind="stable")[:k]] = True
    return keep


def run_config(cfg: dict) -> dict:
    """One configuration on the three folds: {fold: ensemble log-probabilities}, the components kept for H3 pairs."""
    lps = {}
    for f, fd in FD.items():
        tr = fd["tr"]
        comps = {c: fd[f"c_{c}"] for c in FEATC + CNNC}
        if cfg.get("kind") == "H3":
            lps[f] = ensemble(comps, cfg["weights"])
            continue
        if cfg.get("icc_k") and len(np.unique(bank()["a"]["session"][tr])) < 2:
            lps[f] = ensemble(comps)
            continue
        F, v = transform(cfg, tr)
        opt = {k: cfg[k] for k in ("by_layout", "shrink_k", "head_params") if k in cfg}
        if cfg.get("routed"):                                   # F8
            lps[f] = routed(fd, F, v, opt, comps)
            continue
        models = train_feat(F, v, tr, opt, extra=f7_extra(tr) if cfg.get("f7") else None)
        if cfg.get("mlp"):                                      # F9
            models.update(mlp_component(F, v, tr, cfg["mlp"], models))
        new = score_feat(models, F, v, fd, opt)
        if cfg.get("mlp_mode") == "replace":
            comps = {c: comps[c] for c in CNNC} | {"mlp": new["mlp"]}
        else:
            comps.update(new)
        lps[f] = ensemble(comps, cfg.get("weights"))
    return lps


def routed(fd, F, v, opt, comps) -> np.ndarray:
    b = bank()
    tr = fd["tr"]
    out = dict(comps)
    path_tr, id_tr = tr[b["kind"][tr] == "track"], tr[b["kind"][tr] == "idcap"]
    new_path = score_feat(train_feat(F, v, path_tr, opt), F, v, fd, opt)
    is_path = b["kind"][fd["te"]] == "track"
    for c in FEATC:
        out[c] = np.where(is_path[:, None], new_path[c], comps[c])
    if len(id_tr):
        new_id = score_feat(train_feat(F, v, id_tr, opt), F, v, fd, opt)
        for c in FEATC:
            out[c] = np.where(is_path[:, None], out[c], new_id[c])
    return ensemble(out)


# ------------------------------------------------------------------ F9: an MLP across training days

def mlp_component(F, v, tr, loss: str, models: dict) -> dict:
    """A ninth component on rf_pace_prior's Prior-standardised inputs, trained across days (seeds 0 to 2 averaged)."""
    import torch
    from pipeline.identify import idv2_core as C
    a = bank()["a"]
    st = models["rf_pace_prior"]["state"]
    A = st.fit(np.c_[F, v][tr], a["path"][tr], a["session"][tr])     # the same fit as the component's (deterministic)
    y = np.array([CLASSES.index(p) for p in a["anon"][tr]])
    g = np.unique(a["session"][tr], return_inverse=True)[1]
    nets = [_train_mlp(A, y, g, loss, s) for s in (0, 1, 2)]

    def predict(Bm):
        with torch.no_grad():
            x = torch.tensor(np.asarray(Bm, np.float32))
            lp = np.mean([torch.log_softmax(n(x)[0], 1).numpy() for n in nets], axis=0)
        return C.normalise_logp(lp)
    return {"mlp": {"state_of": "rf_pace_prior", "mlp": predict}}


def _train_mlp(A, y, g, loss, seed):
    import torch
    torch.manual_seed(seed)
    x = torch.tensor(np.nan_to_num(np.asarray(A, np.float32)))
    yt, gt = torch.tensor(y), torch.tensor(g)
    G = int(gt.max()) + 1

    class Net(torch.nn.Module):
        def __init__(self, d):
            super().__init__()
            self.h = torch.nn.Sequential(torch.nn.Linear(d, 128), torch.nn.ReLU(), torch.nn.Dropout(0.2))
            self.o = torch.nn.Linear(128, 6)

        def forward(self, x):
            z = self.h(torch.nan_to_num(x))
            return self.o(z), z
    net = Net(x.shape[1])
    opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-4)
    q = torch.ones(G) / G
    ce = torch.nn.functional.cross_entropy
    for _ in range(300):
        net.train()
        logits, z = net(x)
        per = torch.stack([ce(logits[gt == k], yt[gt == k]) for k in range(G)])
        if loss == "groupdro":
            q = q * torch.exp(0.1 * per.detach())
            q = q / q.sum()
            L = (q * per).sum()
        elif loss == "vrex":
            L = per.mean() + 1.0 * per.var(unbiased=False)
        elif loss == "coral":
            pen = 0.0
            covs = [torch.cov(z[gt == k].T) for k in range(G)]
            for i in range(G):
                for j in range(i + 1, G):
                    pen = pen + ((covs[i] - covs[j]) ** 2).sum() / (4 * z.shape[1] ** 2)
            L = ce(logits, yt) + 1.0 * pen
        elif loss == "supcon":
            e = torch.nn.functional.normalize(z, dim=1)
            sim = e @ e.T / 0.1
            n = len(yt)
            eye = torch.eye(n, dtype=torch.bool)
            pos = (yt[:, None] == yt[None, :]) & (gt[:, None] != gt[None, :])
            logprob = sim - torch.logsumexp(sim.masked_fill(eye, -1e9), 1, keepdim=True)
            has = pos.sum(1) > 0
            sc = -(logprob * pos).sum(1)[has] / pos.sum(1)[has]
            L = ce(logits, yt) + 1.0 * sc.mean()
        else:
            raise ValueError(loss)
        opt.zero_grad()
        L.backward()
        opt.step()
    net.eval()
    return net


# ------------------------------------------------------------------ grids (PREREG_LP section 5, fixed)

def grid(name: str) -> dict:
    W8 = FEATC + CNNC
    if name == "H3":
        g = {f"H3_drop_{c}": {"kind": "H3", "weights": {c: 0.0}} for c in W8}
        g["H3_drop_pace"] = {"kind": "H3", "weights": {c: 0.0 for c in PACE}}
        g["H3_feature_only"] = {"kind": "H3", "weights": {c: 0.0 for c in CNNC}}
        g["H3_cnn_only"] = {"kind": "H3", "weights": {c: 0.0 for c in FEATC}}
        g["H3_feature_w0.5"] = {"kind": "H3", "weights": {c: 0.5 for c in FEATC}}
        g["H3_feature_w2.0"] = {"kind": "H3", "weights": {c: 2.0 for c in FEATC}}
        return g
    if name == "F1":
        return {"F1a_residual_pace": {"residual": True}, "F1b_residual_no_pace": {"residual": True, "no_pace": True}}
    if name == "F2":
        return {"F2_path_layout": {"by_layout": True}}
    if name == "F3":
        return {f"F3_shrink_k{k}": {"shrink_k": k} for k in (10, 40, 160)}
    if name == "F4":
        return {f"F4_icc_top{k}": {"icc_k": k} for k in (100, 200, 400)}
    if name == "F5":
        return {"F5a_drop_mod": {"drop_families": ["mod"]}, "F5b_drop_wav": {"drop_families": ["wav"]},
                "F5c_drop_mod_wav": {"drop_families": ["mod", "wav"]}}
    if name == "F6":
        P = [{"min_samples_leaf": 5}, {"min_samples_leaf": 20}, {"max_depth": 8}, {"max_features": 0.05},
             {"min_samples_leaf": 5, "max_features": 0.05}]
        return {"F6_" + "_".join(f"{k}{v}" for k, v in p.items()): {"head_params": p} for p in P}
    if name == "F8":
        return {"F8_layout_routed": {"routed": True}}
    if name == "F7":
        return {"F7_offset_augmentation": {"f7": True}}
    if name == "F9":
        return {f"F9_{l}_{m}": {"mlp": l, "mlp_mode": m} for l in ("groupdro", "vrex", "coral", "supcon")
                for m in ("extra", "replace")}
    raise ValueError(name)


def run(names: list, part: str = None) -> dict:
    """Score the named candidates' grids; with `part`, into dev/part_<part>.json (one per process; `merge` joins them)."""
    load_folds()
    p = os.path.join(OUT, f"part_{part}.json" if part else "dev.json")
    res = json.load(open(p)) if os.path.exists(p) else {"label": LT.LABEL, "configs": {}}
    if "v4" not in res["configs"]:
        res["configs"]["v4"] = ds_of({f: fd["ensemble"] for f, fd in FD.items()})
    for name in names:
        for cname, cfg in grid(name).items():
            if cname in res["configs"]:
                continue
            t0 = time.time()
            r = ds_of(run_config(cfg))
            v4 = res["configs"]["v4"]
            r["guard"] = bool(r["B1_slow"] >= v4["B1_slow"] - 5 and r["B1_fast"] >= v4["B1_fast"] - 5)
            r["minus_v4"] = round(r["DS"] - v4["DS"], 2)
            r["seconds"] = round(time.time() - t0, 1)
            res["configs"][cname] = r
            res["n_configurations_scored"] = len(res["configs"]) - 1      # multiplicity, reported beside the +3 threshold
            print(f"{time.strftime('%H:%M:%S')} {cname}: DS {r['DS']} ({r['minus_v4']:+.2f}), guard {r['guard']}, "
                  f"{r['seconds']} s", flush=True)
            os.makedirs(OUT, exist_ok=True)
            json.dump(res, open(p, "w"), indent=1)
    return res


def record_scores(cand: str, label: str = None) -> dict:
    """R and W candidates: the folds' full scorings (`scores/<cand>_<fold>_<session>.npz`, every component, from the
    offline Session scorer) into dev.json beside the rest."""
    load_folds()
    p = os.path.join(OUT, "dev.json")
    p = os.path.join(OUT, f"part_{label or cand}.json")
    res = json.load(open(p)) if os.path.exists(p) else {"label": LT.LABEL, "configs": {}}
    if "v4" not in res["configs"]:
        res["configs"]["v4"] = ds_of({f: fd["ensemble"] for f, fd in FD.items()})
    lps = {}
    for f, fd in FD.items():
        z = np.load(os.path.join(PS.SC, f"{cand}_{f}_{fd['session']}.npz"))
        assert np.array_equal(z["te"], fd["te"])
        lps[f] = z["ensemble"]
    r = ds_of(lps)
    v4 = res["configs"]["v4"]
    r["guard"] = bool(r["B1_slow"] >= v4["B1_slow"] - 5 and r["B1_fast"] >= v4["B1_fast"] - 5)
    r["minus_v4"] = round(r["DS"] - v4["DS"], 2)
    res["configs"][label or cand] = r
    res["n_configurations_scored"] = len(res["configs"]) - 1
    json.dump(res, open(p, "w"), indent=1)
    print(f"{label or cand}: DS {r['DS']} ({r['minus_v4']:+.2f}), guard {r['guard']}", flush=True)
    return r


def w_models(T: float) -> list:
    """W1: for each fold, the five feature components retrained on the T bank's features and speed (rows and labels as
    v4's), the fold model's CNN files copied; scored afterwards by `ilp_score` with that bank (`w-score`)."""
    import shutil
    load_folds()
    bdir = os.path.join(LT.LP, f"bank_T{T:.1f}_lp")
    X = np.load(os.path.join(bdir, "features.npy"))
    meta = json.load(open(os.path.join(bdir, "meta.json")))["passes"]
    F = X[:, EN.v2_columns(bank()["names_all"])].astype(np.float64)
    v = np.array([m["wifi_speed"] for m in meta], float)
    outs = []
    for f, fd in FD.items():
        tr = fd["tr"]
        assert all(meta[int(i)]["extracted"] for i in tr), "a training row was not extracted"
        out = os.path.join(LT.MODELS, f"W1_T{T:.1f}_{f}")
        assert not os.path.exists(os.path.join(out, "meta_feat_cnn.json")), f"{out} exists"
        os.makedirs(out, exist_ok=True)
        for comp, d in train_feat(F, v, tr, {}).items():
            pickle.dump(d, open(os.path.join(out, f"feat_{comp}.pkl"), "wb"))
        for fn in os.listdir(fd["model"]):
            if fn.startswith("cnn"):
                shutil.copy(os.path.join(fd["model"], fn), os.path.join(out, fn))
        np.save(os.path.join(out, "train_rows.npy"), tr)
        m = json.load(open(os.path.join(fd["model"], "meta_feat_cnn.json")))
        m.update({"cfg": {**m["cfg"], "bank": bdir, "engine_T": T}, "feature_components": f"retrained on {bdir} ({LT.LABEL})",
                  "cnn_components": f"copied unchanged from {fd['model']}"})
        json.dump(m, open(os.path.join(out, "meta_feat_cnn.json"), "w"), indent=1)
        man = json.load(open(os.path.join(fd["model"], "manifest.json")))
        man.update({"model": os.path.basename(out), "T_s": T, "bank": bdir, "candidate": f"W1 T {T}", "label": LT.LABEL,
                    "use": "development fold only"})
        json.dump(man, open(os.path.join(out, "manifest.json"), "w"), indent=1)
        outs.append(out)
        print(f"{time.strftime('%H:%M:%S')} {out}", flush=True)
    return outs


def w_score(T: float, device: str = "mps") -> None:
    load_folds()
    bdir = os.path.join(LT.LP, f"bank_T{T:.1f}_lp")
    for f, fd in FD.items():
        p = os.path.join(PS.SC, f"W1_T{T:.1f}_{f}_{fd['session']}.npz")
        np.savez(p, **PS.score(os.path.join(LT.MODELS, f"W1_T{T:.1f}_{f}"), fd["session"], bank_dir=bdir, device=device))


def merge() -> dict:
    """dev.json = v4 and every configuration from dev/part_*.json (each computed in one process), with the count."""
    import glob
    res = {"label": LT.LABEL, "configs": {}, "parts": []}
    for p in sorted(glob.glob(os.path.join(OUT, "part_*.json"))):
        d = json.load(open(p))
        if "v4" in res["configs"]:
            assert d["configs"]["v4"] == res["configs"]["v4"], f"{p}: v4 differs"
        for k, v in d["configs"].items():
            assert k == "v4" or k not in res["configs"], f"{k} twice"
            res["configs"][k] = v
        res["parts"].append(os.path.basename(p))
    res["n_configurations_scored"] = len(res["configs"]) - 1
    json.dump(res, open(os.path.join(OUT, "dev.json"), "w"), indent=1)
    print(f"merged {len(res['parts'])} parts: {res['n_configurations_scored']} configurations", flush=True)
    return res


# ------------------------------------------------------------------ checks

def selftest() -> bool:
    """The feature-side scorer, with loso_A1_v4's own feature models, against loso_A1_v4's replay on A1 (development
    session): every feature component within 1e-9 and the ensemble (with the replay's CNN components) the same."""
    z = np.load(os.path.join(EN.ENG, "replays", "loso_A1_v4_A1_T4.0.npz"))
    fd = {"te": z["te"], "path_used": z["path_used"],
          "layout": np.where(bank()["kind"][z["te"]] == "idcap", "id_spot", "home")}
    b = bank()
    new = score_feat(load_feat(os.path.join(EN.ENG, "models", "loso_A1_v4")), b["F"], b["speed"], fd, {})
    diff = {c: float(np.abs(new[c] - z[f"c_{c}"]).max()) for c in FEATC}
    ens = ensemble(new | {c: z[f"c_{c}"] for c in CNNC})
    res = {"component_max_abs_diff": diff, "ensemble_max_abs_diff": float(np.abs(ens - z["ensemble"]).max()),
           "same_decisions": int((ens.argmax(1) == z["ensemble"].argmax(1)).sum()), "n": int(len(z["te"]))}
    res["PASSED"] = max(diff.values()) <= 1e-9 and res["same_decisions"] == res["n"] and res["ensemble_max_abs_diff"] <= 1e-9
    print(json.dumps(res, indent=1), flush=True)
    os.makedirs(os.path.join(LT.LP, "checks"), exist_ok=True)
    json.dump(res, open(os.path.join(LT.LP, "checks", "scorer_selftest_loso_A1.json"), "w"), indent=1)
    return res["PASSED"]


def null() -> bool:
    """The null switch (PREREG_LP section 4) on D1: (i) the scorer with the development model's own feature components
    reproduces the v4 baseline's ensemble (1e-9) and decisions; (ii) the trainer with every change off reproduces the
    model's feature-component predictions exactly; (iii) every family's code path with its change off (an empty config
    through run_config) reproduces the decisions."""
    load_folds()
    fd = FD["D1"]
    b = bank()
    comps = score_feat(load_feat(fd["model"]), b["F"], b["speed"], fd, {})
    ens = ensemble(comps | {c: fd[f"c_{c}"] for c in CNNC})
    i_ok = float(np.abs(ens - fd["ensemble"]).max()) <= 1e-9 and (ens.argmax(1) == fd["ensemble"].argmax(1)).all()
    mine = train_feat(b["F"], b["speed"], fd["tr"], {})
    new = score_feat(mine, b["F"], b["speed"], fd, {})
    ii = {c: float(np.abs(new[c] - comps[c]).max()) for c in FEATC}
    ens2 = ensemble(new | {c: fd[f"c_{c}"] for c in CNNC})
    ii_ok = max(ii.values()) == 0.0 and float(np.abs(ens2 - fd["ensemble"]).max()) <= 1e-9
    iii = {}
    for name, cfg in {"H": {"kind": "H3", "weights": {}}, "F_transform": {"residual": False}, "F3": {"shrink_k": 0},
                      "F6": {"head_params": {}}, "F2": {"by_layout": False}}.items():
        FD_one = {"D1": fd}
        saved = dict(FD)
        FD.clear()
        FD.update(FD_one)
        lp = run_config(cfg)["D1"]
        FD.clear()
        FD.update(saved)
        iii[name] = bool((lp.argmax(1) == fd["ensemble"].argmax(1)).all() and float(np.abs(lp - fd["ensemble"]).max()) <= 1e-9)
    res = {"fold": "D1", "scorer_reproduces_v4": bool(i_ok), "trainer_component_max_abs_diff": ii, "trainer_scores_reproduce_v4": bool(ii_ok),
           "families_switched_off": iii}
    res["PASSED"] = bool(i_ok and ii_ok and all(iii.values()))
    json.dump(res, open(os.path.join(LT.LP, "checks", "null_switch_D1.json"), "w"), indent=1)
    print(json.dumps(res, indent=1), flush=True)
    return res["PASSED"]


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "selftest":
        sys.exit(0 if selftest() else 1)
    elif what == "null":
        sys.exit(0 if null() else 1)
    elif what == "run":
        args = sys.argv[2:]
        part = None
        if "--part" in args:                       # drop "--part" and the one value after it, by position
            i = args.index("--part")
            part = args[i + 1]
            args = args[:i] + args[i + 2:]
        assert args, "no candidate named"
        run(args, part)
    elif what == "merge":
        merge()
    elif what == "record":
        record_scores(sys.argv[2])
    elif what == "w-models":
        w_models(float(sys.argv[2]))
    elif what == "w-score":
        w_score(float(sys.argv[2]), sys.argv[sys.argv.index("--device") + 1] if "--device" in sys.argv else "mps")
    else:
        raise SystemExit(what)
    sys.exit(0)
