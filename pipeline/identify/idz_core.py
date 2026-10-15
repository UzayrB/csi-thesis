"""idz_core. Identification audit (`runs/identify/audit/PLAN.md`): the final ensemble's train-and-save and
apply-with-calibration (as `idw_core`), made configurable for the audit's fixes and candidates:

- `cols`: "v2" = the gait columns without `dwt_6` (bug B-1); the bank's maps are v2 (bug B-2) when the bank
  is `runs/identify/audit/bank_*`;
- `layout` (candidate L2): every statistic keyed by (path, layout) instead of path, and the CNN input
  normalisation by (direction, layout); layout is `id_spot` for Room B identification walks, else `home`;
- `fn` (candidate FN): maps frame-normalised (each frame minus its mean over frequency, per link);
- calibration settings: `others`, `others_idcap` (candidate L1), `causal`, `none`;
- fusion (candidates F1 to F3) is applied afterwards to the saved components (`fuse`).

Feature components and CNN components are trained and saved separately (`parts`), so a candidate that
changes only one family retrains only that family.
"""

from __future__ import annotations

import json
import os
import pickle
import time

import numpy as np

from pipeline.identify import idv2_core as C
from pipeline.identify import idw_core as W
from pipeline.identify import idx_dev as X
from pipeline.identify import idx_loso as L
from pipeline.identify import idz_bank as ZB

CLASSES = L.CLASSES
FEAT = W.FEAT
COMPONENTS = W.COMPONENTS
PACE_COMPONENTS = W.PACE_COMPONENTS
TREES = ("rf", "rf_prior", "rf_pace_prior", "et_pace_prior")
AUDIT = os.path.join("runs", "identify", "audit")


def layout_tag(a) -> np.ndarray:
    return np.where((a["room"] == "B") & (a["kind"] == "idcap"), "id_spot", "home")


def path_key(a, layout: bool) -> np.ndarray:
    return np.char.add(np.char.add(a["path"].astype(str), "|"), layout_tag(a)) if layout else a["path"].astype(str)


def columns(bank, cols: str) -> np.ndarray:
    return ZB.columns_v2(bank) if cols == "v2" else L.columns("U_all_gait")


def feature_matrix(bank, pace: bool, cols: str) -> np.ndarray:
    Xf = bank["X"][:, columns(bank, cols)]
    return np.c_[Xf, bank["a"]["speed_m_s"]] if pace else Xf


def windows_of(bank, fn: bool) -> list:
    key = "W_fn" if fn else "W"
    if key not in bank:
        maps = bank["maps"]
        if fn:
            maps = [(m - m.mean(axis=1, keepdims=True)).astype(np.float32) for m in maps]
        bank[key] = [C.windows(m) for m in maps]
    return bank[key]


# ------------------------------------------------------------------ CNN input normalisation, optionally by layout

def norm_stats_keyed(Xw, dw, lw) -> dict:
    st = C.norm_stats(Xw, dw)
    out = {("*", k): st[k] for k in (0, 1)}
    if lw is not None:
        for lay in np.unique(lw):
            for k in (0, 1):
                sel = (dw == k) & (lw == lay)
                if sel.any():
                    out[(lay, k)] = (Xw[sel].mean(axis=(0, 2, 3)), Xw[sel].std(axis=(0, 2, 3)) + 1e-6)
    return out


def apply_norm_keyed(Xw, dw, lw, st) -> np.ndarray:
    out = np.empty_like(Xw)
    for k in (0, 1):
        for lay in (np.unique(lw) if lw is not None else ["*"]):
            sel = (dw == k) & ((lw == lay) if lw is not None else True)
            if not np.any(sel):
                continue
            mu, sd = st.get((lay, k), st[("*", k)])
            out[sel] = (Xw[sel] - mu[None, :, None, None]) / sd[None, :, None, None]
    return out


def _stack(bank, rows, chan, fn, layout):
    Wl = windows_of(bank, fn)
    dirs = X._dirs(bank["a"])
    Xw, dw, pw = X._stack(Wl, rows, dirs, chan)
    lw = np.repeat(layout_tag(bank["a"])[np.asarray(rows)], [len(Wl[i]) for i in rows]) if layout else None
    return Xw, dw, pw, lw


# ------------------------------------------------------------------ train and save

def train(bank, tr, out_dir, cfg: dict, parts=("feat", "cnn"), seeds=(0, 1, 2), steps=6000, device="cpu", log=print) -> dict:
    import torch
    from pipeline.identify import idmax_eval as E
    a = bank["a"]
    tr = np.asarray(tr)
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    pk = path_key(a, cfg.get("layout", False))
    if "feat" in parts:
        for comp, (head, norm, pace) in FEAT.items():
            Xf = feature_matrix(bank, pace, cfg.get("cols", "v2"))
            if norm == "perpath":
                st = W.PerPath().fit(Xf[tr], pk[tr])
                A = st.transform(Xf[tr], pk[tr])
            else:
                st = W.Prior()
                A = st.fit(Xf[tr], pk[tr], a["session"][tr])
            clf = E.make_model(head).fit(A, a["anon"][tr])
            pickle.dump({"state": st, "clf": clf, "classes": list(clf.classes_)}, open(os.path.join(out_dir, f"feat_{comp}.pkl"), "wb"))
        log(f"{time.strftime('%H:%M:%S')} feature components saved ({time.time() - t0:.0f} s)")
    if "cnn" in parts:
        for chan in (None, 0, 1, 2):
            Xw, dw, pw, lw = _stack(bank, tr, chan, cfg.get("fn", False), cfg.get("layout", False))
            yw = np.array([CLASSES.index(v) for v in a["anon"][tr]])[pw]
            st = norm_stats_keyed(Xw, dw, lw)
            Xn = apply_norm_keyed(Xw, dw, lw, st)
            tag = "cnn3" if chan is None else f"cnn_link{chan}"
            for s in seeds:
                net = C.train_cnn(Xn, yw, dw, 6, s, device, steps)
                torch.save(net.to("cpu").state_dict(), os.path.join(out_dir, f"{tag}_seed{s}.pt"))
            pickle.dump({"st": st, "dir_map": W._dir_map(dw)}, open(os.path.join(out_dir, f"{tag}_norm.pkl"), "wb"))
            log(f"{time.strftime('%H:%M:%S')} {tag} saved ({time.time() - t0:.0f} s)")
    meta = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "n_train": int(len(tr)), "seeds": list(seeds), "steps": steps,
            "device": device, "cfg": cfg, "parts": list(parts), "seconds": round(time.time() - t0, 1)}
    np.save(os.path.join(out_dir, "train_rows.npy"), tr)
    json.dump(meta, open(os.path.join(out_dir, f"meta_{'_'.join(parts)}.json"), "w"), indent=1)
    return meta


# ------------------------------------------------------------------ calibration and apply

def calibration_groups(a, te, setting: str) -> list:
    te = np.asarray(te)
    if setting in ("others", "causal", "none"):
        return W.calibration_groups(a, te, setting)
    if setting == "others_idcap":
        out = []
        for p in np.unique(a["anon"][te]):
            k = np.flatnonzero(a["anon"][te] == p)
            ses = np.unique(a["session"][te[k]])
            assert len(ses) == 1
            out.append((k, np.flatnonzero((a["session"] == ses[0]) & (a["anon"] != p) & (a["kind"] == "idcap"))))
        return out
    raise ValueError(setting)


def apply(bank, feat_dir, cnn_dir, te, groups, cfg: dict, device="cpu") -> dict:
    a = bank["a"]
    te = np.asarray(te)
    pk = path_key(a, cfg.get("layout", False))
    out = {}
    for comp, (_head, norm, pace) in FEAT.items():
        Xf = feature_matrix(bank, pace, cfg.get("cols", "v2"))
        d = pickle.load(open(os.path.join(feat_dir, f"feat_{comp}.pkl"), "rb"))
        if norm == "perpath":
            Bm = d["state"].transform(Xf[te], pk[te])
        else:
            Bm = np.empty((len(te), len(d["state"].g_mu)))
            for k, calib in groups:
                Bm[k] = d["state"].apply(Xf, pk, te[k], calib)
        out[comp] = L._order(C.logp_from_proba(d["clf"].predict_proba(Bm)), d["classes"])
    meta = json.load(open(os.path.join(cnn_dir, "meta_cnn.json" if os.path.exists(os.path.join(cnn_dir, "meta_cnn.json"))
                                       else "meta_feat_cnn.json")))
    seeds = meta["seeds"]
    fn, layout = cfg.get("fn", False), cfg.get("layout", False)
    for chan in (None, 0, 1, 2):
        tag = "cnn3" if chan is None else f"cnn_link{chan}"
        nd = pickle.load(open(os.path.join(cnn_dir, f"{tag}_norm.pkl"), "rb"))
        st, dmap = nd["st"], nd["dir_map"]
        remap = lambda d: np.array([dmap[int(v)] for v in d], int)  # noqa: E731
        Xte, dte, pte, lte = _stack(bank, te, chan, fn, layout)
        dte = remap(dte)
        Xte = apply_norm_keyed(Xte, dte, lte, st)
        plain, adapted = [], []
        for s in seeds:
            net = W._load_net(os.path.join(cnn_dir, f"{tag}_seed{s}.pt"), 3 if chan is None else 1).to(device)
            if chan is None:
                plain.append(C.normalise_logp(C.pass_logp(net, Xte, dte, pte, len(te), 6, device)))
            lp = np.zeros((len(te), 6))
            for k, calib in groups:
                sub = te[k]
                netr = net
                if calib is not None and len(calib):
                    Xo, do, _p, lo = _stack(bank, calib, chan, fn, layout)
                    do = remap(do)
                    netr = C.adabn(net, apply_norm_keyed(Xo, do, lo, st), do, device)
                Xs, ds, ps, ls = _stack(bank, sub, chan, fn, layout)
                ds = remap(ds)
                lp[k] = C.pass_logp(netr, apply_norm_keyed(Xs, ds, ls, st), ds, ps, len(sub), 6, device)
            adapted.append(C.normalise_logp(lp))
        if chan is None:
            out["cnn"] = C.normalise_logp(np.mean(plain, axis=0))
            out["cnn_prior"] = C.normalise_logp(np.mean(adapted, axis=0))
        else:
            out[f"_link{chan}"] = C.normalise_logp(np.mean(adapted, axis=0))
    out["cnn_perlink_prior"] = C.normalise_logp(sum(out.pop(f"_link{c}") for c in range(3)))
    return out


# ------------------------------------------------------------------ fusion

def fuse(comp: dict, variant: str = "F0", keep=COMPONENTS) -> np.ndarray:
    """The ensemble's log-probabilities from the saved components (PLAN section 3)."""
    keep = [c for c in COMPONENTS if c in keep]
    if variant == "F0":
        return C.normalise_logp(sum(comp[c] for c in keep))
    P = {c: np.exp(comp[c]) for c in keep}
    if variant == "F1":
        Q = {c: (P[c] * 300 + 1) / 306 if c in TREES else np.maximum(P[c], 1e-3) for c in keep}
    elif variant == "F2":
        Q = {c: np.maximum(P[c], 1e-2) for c in keep}
    elif variant == "F3":
        return np.log(np.mean([P[c] / P[c].sum(1, keepdims=True) for c in keep], axis=0))
    else:
        raise ValueError(variant)
    return C.normalise_logp(sum(np.log(q / q.sum(1, keepdims=True)) for q in Q.values()))
