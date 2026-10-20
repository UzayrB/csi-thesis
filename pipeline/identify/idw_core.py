# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The identification ensemble: training and saving its models, and applying them with calibration.

from __future__ import annotations

import json
import os
import pickle
import subprocess
import time

import numpy as np

from pipeline.identify import idv2_core as C
from pipeline.identify import idx_dev as X
from pipeline.identify import idx_loso as L

CLASSES = L.CLASSES
COMPONENTS = ("rf", "rf_prior", "rf_pace_prior", "et_pace_prior", "lda_pace_prior", "cnn", "cnn_prior",
              "cnn_perlink_prior")
PACE_COMPONENTS = ("rf_pace_prior", "et_pace_prior", "lda_pace_prior")
FEAT = {"rf": ("rf", "perpath", False), "rf_prior": ("rf", "prior", False), "rf_pace_prior": ("rf", "prior", True),
        "et_pace_prior": ("et", "prior", True), "lda_pace_prior": ("lda", "prior", True)}
RF_ONLY = ("rf", "rf_prior", "rf_pace_prior")
MODELS = os.path.join("runs", "identify", "idwalks", "models")



# Function tracking training running.
def tracking_training_running() -> list:
    out = subprocess.run(["ps", "-Ao", "pid,command"], capture_output=True, text=True).stdout.splitlines()
    return [l.strip() for l in out if "pipeline.constrained" in l and " train" in l and "grep" not in l]


# Block while a tracking training process runs; then return the device to use ('mps' when no tracking...
def wait_for_tracking(log=print, poll_s=60) -> str:
    import torch
    waited = False
    while True:
        busy = tracking_training_running()
        if not busy:
            break
        if not waited:
            log(f"{time.strftime('%H:%M:%S')} waiting: tracking training running ({busy[0][:100]})")
            waited = True
        time.sleep(poll_s)
    if waited:
        log(f"{time.strftime('%H:%M:%S')} tracking training finished; continuing")
    return "mps" if torch.backends.mps.is_available() else "cpu"



# Function feature matrix.
def feature_matrix(bank, pace: bool, extra=None) -> np.ndarray:
    a = bank["a"]
    Xf = bank["X"][:, L.columns("U_all_gait")]
    if extra is not None:
        Xf = np.c_[Xf, extra]
    if pace:
        Xf = np.c_[Xf, a["speed_m_s"]]
    return Xf


# Idmax_eval.prep(Xtr, Xte, ltr, lte, "perline_z"), split into fit and transform.
class PerPath:

    # Function fit.
    def fit(self, Xtr, ptr):
        Xtr = np.array(Xtr, float)
        med = np.nanmedian(Xtr, axis=0)
        self.ok = np.isfinite(med)
        self.med = med[self.ok]
        Z = self._impute(Xtr)
        self.keep = Z.std(axis=0) > 1e-12
        Z = Z[:, self.keep]
        self.mu_g, self.sd_g = Z.mean(0), Z.std(0)
        self.stats = {}
        for p in np.unique(ptr):
            itr = ptr == p
            if itr.sum() >= 3:
                mu, s = Z[itr].mean(0), Z[itr].std(0)
                self.stats[p] = (mu, np.where(s > 1e-9, s, self.sd_g))
        return self

    # Function impute.
    def _impute(self, Xr):
        Z = np.array(Xr, float)[:, self.ok]
        r, c = np.nonzero(~np.isfinite(Z))
        Z[r, c] = self.med[c]
        return Z

    # Function transform.
    def transform(self, Xr, pr):
        Z = self._impute(Xr)[:, self.keep]
        out = np.empty_like(Z)
        for p in np.unique(pr):
            m = pr == p
            mu, s = self.stats.get(p, (self.mu_g, np.where(self.sd_g > 1e-9, self.sd_g, self.sd_g)))
            out[m] = (Z[m] - mu) / s
        return out


# Idx_dev.prior_standardise, split into fit (training side) and apply (per calibration group).
class Prior:

    # Function fit.
    def fit(self, Xtr, ptr, str_):
        Xtr = np.array(Xtr, float)
        med = np.nanmedian(Xtr, axis=0)
        self.ok = np.isfinite(med)
        self.med = med[self.ok]
        Z = self._impute(Xtr)
        self.keep = Z.std(axis=0) > 1e-12
        Z = Z[:, self.keep]
        self.g_mu, self.g_sd = Z.mean(0), Z.std(0) + 1e-9
        A = np.empty_like(Z)
        for s in np.unique(str_):
            m = str_ == s
            A[m] = self.zs(Z[m], ptr[m], Z[m], ptr[m])
        return A

    # Function impute.
    def _impute(self, Xr):
        Z = np.array(Xr, float)[:, self.ok]
        r, c = np.nonzero(~np.isfinite(Z))
        Z[r, c] = self.med[c]
        return Z

    # Function Z.
    def Z(self, Xr):
        return self._impute(Xr)[:, self.keep]

    # Function zs.
    def zs(self, Zrows, prows, Zref, pref):
        out = np.empty_like(Zrows)
        for p in np.unique(prows):
            m = prows == p
            rr = pref == p
            if rr.sum() < 3:
                rr = np.ones(len(pref), bool)
            mu, sd = Zref[rr].mean(0), Zref[rr].std(0)
            out[m] = (Zrows[m] - mu) / np.where(sd > 1e-9, sd, self.g_sd)
        return out

    # Function apply.
    def apply(self, Xall, paths, rows, calib):
        Zr = self.Z(Xall[rows])
        if calib is not None and len(calib) >= 10:
            return self.zs(Zr, paths[rows], self.Z(Xall[calib]), paths[calib])
        return (Zr - self.g_mu) / self.g_sd



# Function dir map.
def _dir_map(dtr) -> dict:
    present = sorted(set(int(v) for v in np.unique(dtr)))
    return {0: 0 if 0 in present else present[0], 1: 1 if 1 in present else present[0]}


# Train every component on the rows tr and save them under out_dir.
def train(bank, tr, out_dir, seeds=(0, 1, 2), steps=6000, device="cpu", extra=None, log=print) -> dict:
    import torch
    from pipeline.identify import idmax_eval as E
    a, W = bank["a"], bank["W"]
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    y = a["anon"][tr]
    for comp, (head, norm, pace) in FEAT.items():
        Xf = feature_matrix(bank, pace, extra if comp in RF_ONLY else None)
        if norm == "perpath":
            st = PerPath().fit(Xf[tr], a["path"][tr])
            A = st.transform(Xf[tr], a["path"][tr])
        else:
            st = Prior()
            A = st.fit(Xf[tr], a["path"][tr], a["session"][tr])
        clf = E.make_model(head).fit(A, y)
        pickle.dump({"state": st, "clf": clf, "classes": list(clf.classes_)}, open(os.path.join(out_dir, f"feat_{comp}.pkl"), "wb"))
    log(f"{time.strftime('%H:%M:%S')} feature heads saved ({time.time() - t0:.0f} s)")
    dirs = X._dirs(a)
    nets = {}
    for chan in (None, 0, 1, 2):
        Xw, dw, pw = X._stack(W, tr, dirs, chan)
        yw = np.array([CLASSES.index(v) for v in a["anon"][tr]])[pw]
        st = C.norm_stats(Xw, dw)
        Xn = C.apply_norm(Xw, dw, st)
        tag = "cnn3" if chan is None else f"cnn_link{chan}"
        for s in seeds:
            net = C.train_cnn(Xn, yw, dw, 6, s, device, steps)
            torch.save(net.to("cpu").state_dict(), os.path.join(out_dir, f"{tag}_seed{s}.pt"))
        pickle.dump({"st": st, "dir_map": _dir_map(dw)}, open(os.path.join(out_dir, f"{tag}_norm.pkl"), "wb"))
        log(f"{time.strftime('%H:%M:%S')} {tag} saved ({time.time() - t0:.0f} s)")
    meta = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "n_train": int(len(tr)), "seeds": list(seeds), "steps": steps,
            "device": device, "extra_features": extra is not None, "seconds": round(time.time() - t0, 1)}
    np.save(os.path.join(out_dir, "train_rows.npy"), np.asarray(tr, int))
    json.dump(meta, open(os.path.join(out_dir, "meta.json"), "w"), indent=1)
    return meta



# [(positions in te, calibration rows or None)] for 'causal', 'others' or 'none'.
def calibration_groups(a, te, setting: str) -> list:
    te = np.asarray(te)
    if setting == "none":
        return [(np.arange(len(te)), None)]
    if setting == "causal":
        rid = X.recording_ids(a)
        return [(np.flatnonzero(rid[te] == r), prev) for r, prev in X.prior_recordings(a, te).items()]
    if setting == "others":
        out = []
        for p in np.unique(a["anon"][te]):
            k = np.flatnonzero(a["anon"][te] == p)
            ses = np.unique(a["session"][te[k]])
            assert len(ses) == 1
            out.append((k, np.flatnonzero((a["session"] == ses[0]) & (a["anon"] != p))))
        return out
    raise ValueError(setting)


# Function load net.
def _load_net(path, c_in):
    import torch
    net = C.make_net(c_in, 6)
    net.load_state_dict(torch.load(path, map_location="cpu"))
    return net.eval()


# Every component's (len(te), 6) normalised log-probabilities, and the ensemble.
def apply(bank, model_dir, te, groups, device="cpu", extra=None) -> dict:
    a, W = bank["a"], bank["W"]
    te = np.asarray(te)
    meta = json.load(open(os.path.join(model_dir, "meta.json")))
    out = {}
    for comp, (_head, norm, pace) in FEAT.items():
        Xf = feature_matrix(bank, pace, extra if (comp in RF_ONLY and meta.get("extra_features")) else None)
        d = pickle.load(open(os.path.join(model_dir, f"feat_{comp}.pkl"), "rb"))
        if norm == "perpath":
            Bm = d["state"].transform(Xf[te], a["path"][te])
        else:
            Bm = np.empty((len(te), len(d["state"].g_mu)))
            for k, calib in groups:
                Bm[k] = d["state"].apply(Xf, a["path"], te[k], calib)
        out[comp] = L._order(C.logp_from_proba(d["clf"].predict_proba(Bm)), d["classes"])
    dirs = X._dirs(a)
    seeds = meta["seeds"]
    for chan in (None, 0, 1, 2):
        tag = "cnn3" if chan is None else f"cnn_link{chan}"
        nd = pickle.load(open(os.path.join(model_dir, f"{tag}_norm.pkl"), "rb"))
        st, dmap = nd["st"], nd["dir_map"]
        remap = lambda d: np.array([dmap[int(v)] for v in d], int)
        Xte, dte, pte = X._stack(W, te, dirs, chan)
        dte = remap(dte)
        Xte = C.apply_norm(Xte, dte, st)
        plain, adapted = [], []
        for s in seeds:
            net = _load_net(os.path.join(model_dir, f"{tag}_seed{s}.pt"), 3 if chan is None else 1).to(device)
            if chan is None:
                plain.append(C.normalise_logp(C.pass_logp(net, Xte, dte, pte, len(te), 6, device)))
            lp = np.zeros((len(te), 6))
            for k, calib in groups:
                sub = te[k]
                netr = net
                if calib is not None and len(calib):
                    Xo, do, _p = X._stack(W, calib, dirs, chan)
                    do = remap(do)
                    netr = C.adabn(net, C.apply_norm(Xo, do, st), do, device)
                Xs, ds, ps = X._stack(W, sub, dirs, chan)
                ds = remap(ds)
                lp[k] = C.pass_logp(netr, C.apply_norm(Xs, ds, st), ds, ps, len(sub), 6, device)
            adapted.append(C.normalise_logp(lp))
        if chan is None:
            out["cnn"] = C.normalise_logp(np.mean(plain, axis=0))
            out["cnn_prior"] = C.normalise_logp(np.mean(adapted, axis=0))
        else:
            out[f"_link{chan}"] = C.normalise_logp(np.mean(adapted, axis=0))
    out["cnn_perlink_prior"] = C.normalise_logp(sum(out.pop(f"_link{c}") for c in range(3)))
    out["ensemble"] = C.normalise_logp(sum(out[c] for c in COMPONENTS))
    out["ensemble_nopace"] = C.normalise_logp(sum(out[c] for c in COMPONENTS if c not in PACE_COMPONENTS))
    return out


# S0: press pace alone, an LDA on that one number, trained on the training set's identification captures.
def s0(bank, tr_idcap, te) -> np.ndarray:
    return L.arm_s0(bank, np.asarray(tr_idcap), np.asarray(te))
