"""idx_dev. Identification development levers (the operator's direction of 2026-09-28), on the pass bank.

Each arm maps (bank, training rows, test rows) to test log-probabilities (n_te, 6). Test-session
information enters only causally and without labels: a test pass may be calibrated with its session's
RECORDINGS THAT STARTED BEFORE ITS OWN (other walks the live system has already seen); the first
recording of a session falls back to the training statistics.

`select` chooses among candidate arms by an inner leave-one-session-out over the training sessions only,
then fits the winner on all training sessions; the inner folds' out-of-fold log-probabilities also give
the temperature for multi-pass decisions. `multipass` turns per-pass log-probabilities into decisions
over the first k passes of each walk (k = 1, 3, 5, 10), as a live system identifying a tracked walker
would, never using a later pass.

    PYTHONPATH=. python3 -m pipeline.identify.idx_dev --arms ... --select name:a,b,c --tag NAME
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time

import numpy as np

from pipeline.identify import idmax_common as IC
from pipeline.identify import idv2_core as C
from pipeline.identify import idx_loso as L

SESSIONS = L.SESSIONS
CLASSES = L.CLASSES


def recording_ids(a) -> np.ndarray:
    """One id per recording: the session, the participant and the block (a tracking walk, or a block of
    identification captures)."""
    return np.array([f"{s}|{p}|{b}" for s, p, b in zip(a["session"], a["anon"], a["block"])])


def prior_recordings(a, rows_te) -> dict:
    """For each test recording, the rows of its session's recordings that STARTED before it (causal)."""
    rid = recording_ids(a)
    start = {}
    for r in np.unique(rid):
        start[r] = a["t_start"][rid == r].min()
    out = {}
    for r in np.unique(rid[rows_te]):
        s = r.split("|")[0]
        prev = [q for q in start if q.split("|")[0] == s and start[q] < start[r]]
        out[r] = np.flatnonzero(np.isin(rid, prev))
    return out


# ------------------------------------------------------------------ the CNN family

def _dirs(a):
    return np.array([1 if p.endswith("_rev") else 0 for p in a["path"]])


def _stack(W, idx, dirs, chan=None, maps=None):
    Xs, ds, po = [], [], []
    for k, i in enumerate(idx):
        w = C.windows(maps[i]) if maps is not None else W[i]
        if chan is not None:
            w = w[:, chan:chan + 1]
        Xs.append(w)
        ds.append(np.full(len(w), dirs[i]))
        po.append(np.full(len(w), k))
    return np.concatenate(Xs), np.concatenate(ds).astype(int), np.concatenate(po).astype(int)


def cnn(bank, tr, te, seeds=(0,), steps=3000, device="cpu", chan=None, fnorm=False, adabn="none", tilt_sd=0.0):
    """CNN-v2. chan: one link only. fnorm: frequency axis rescaled by each pass's TX-RX2 torso frequency
    to the training median. adabn: 'none', or 'prior' (BatchNorm statistics per test recording from its
    session's earlier recordings, causal and label-free)."""
    a, W = bank["a"], bank["W"]
    dirs = _dirs(a)
    maps = None
    if fnorm:
        f_ref = float(np.nanmedian(a["f_t"][tr]))
        need = set(np.r_[tr, te].tolist())
        if adabn == "prior":
            for v in prior_recordings(a, te).values():
                need |= set(v.tolist())
        maps = [C.rescale_freq(m, f, f_ref) if i in need else None for i, (m, f) in enumerate(zip(bank["maps"], a["f_t"]))]
    Xtr, dtr, ptr = _stack(W, tr, dirs, chan, maps)
    ytr = np.array([CLASSES.index(v) for v in a["anon"][tr]])[ptr]
    st = C.norm_stats(Xtr, dtr)
    Xtr = C.apply_norm(Xtr, dtr, st)
    Xte, dte, pte = _stack(W, te, dirs, chan, maps)
    Xte = C.apply_norm(Xte, dte, st)
    rid = recording_ids(a)
    prior = prior_recordings(a, te) if adabn == "prior" else {}
    lps = []
    for s in seeds:
        if tilt_sd > 0:
            from pipeline.identify import idx_train
            net = idx_train.train_cnn(Xtr, ytr, dtr, 6, s, device, steps, tilt_sd=tilt_sd)
        else:
            net = C.train_cnn(Xtr, ytr, dtr, 6, s, device, steps)
        if adabn == "none":
            lps.append(C.normalise_logp(C.pass_logp(net, Xte, dte, pte, len(te), 6, device)))
            continue
        lp = np.zeros((len(te), 6))
        for r, prev in prior.items():
            k = np.flatnonzero(rid[te] == r)
            sub = np.asarray(te)[k]
            netr = net
            if len(prev):
                Xo, do, _p = _stack(W, prev, dirs, chan, maps)
                netr = C.adabn(net, C.apply_norm(Xo, do, st), do, device)
            Xs, ds, ps = _stack(W, sub, dirs, chan, maps)
            lp[k] = C.pass_logp(netr, C.apply_norm(Xs, ds, st), ds, ps, len(sub), 6, device)
        lps.append(C.normalise_logp(lp))
    return C.normalise_logp(np.mean(lps, axis=0))


def cnn_perlink_product(bank, tr, te, **kw):
    """Per-link encoders (one CNN per link), fused by summing log-probabilities (product fusion)."""
    return C.normalise_logp(sum(cnn(bank, tr, te, chan=c, **kw) for c in range(3)))


# ------------------------------------------------------------------ the feature family

def features(bank, tr, te, fset="U_all_gait", head="rf", norm="perpath", pace=False):
    """A feature arm. norm: 'perpath' (training statistics per path) or 'prior' (each test recording
    standardised per path with its session's earlier recordings; training passes with their own
    session). pace: press pace added as ONE column inside the gait feature set."""
    from pipeline.identify import idmax_eval as E
    a = bank["a"]
    X = bank["X"][:, L.columns(fset)]
    if pace:
        X = np.c_[X, a["speed_m_s"]]
    if norm == "perpath":
        A, Bm = E.prep(X[tr], X[te], a["path"][tr], a["path"][te], "perline_z")
    else:
        A, Bm = prior_standardise(a, X, tr, te)
    clf = E.make_model(head).fit(A, a["anon"][tr])
    return L._order(C.logp_from_proba(clf.predict_proba(Bm)), list(clf.classes_))


def prior_standardise(a, X, tr, te):
    Xtr = np.array(X[tr], float)
    med = np.nanmedian(Xtr, axis=0)
    ok = np.isfinite(med)
    Z = np.array(X[:, ok], float)
    r, c = np.nonzero(~np.isfinite(Z))
    Z[r, c] = med[ok][c]
    keep = Z[tr].std(0) > 1e-12
    Z = Z[:, keep]
    g_mu, g_sd = Z[tr].mean(0), Z[tr].std(0) + 1e-9

    def zs(rows, ref):
        out = np.empty((len(rows), Z.shape[1]))
        for p in np.unique(a["path"][rows]):
            m = a["path"][rows] == p
            rr = ref[a["path"][ref] == p]
            if len(rr) < 3:
                rr = ref
            mu, sd = Z[rr].mean(0), Z[rr].std(0)
            out[m] = (Z[rows][m] - mu) / np.where(sd > 1e-9, sd, g_sd)
        return out
    A = np.empty((len(tr), Z.shape[1]))
    for s in np.unique(a["session"][tr]):
        m = a["session"][tr] == s
        A[m] = zs(np.asarray(tr)[m], np.asarray(tr)[m])
    Bm = np.empty((len(te), Z.shape[1]))
    rid = recording_ids(a)
    for rr, prev in prior_recordings(a, te).items():
        k = np.flatnonzero(rid[te] == rr)
        rows = np.asarray(te)[k]
        if len(prev) >= 10:
            Bm[k] = zs(rows, prev)
        else:
            Bm[k] = (Z[rows] - g_mu) / g_sd
    return A, Bm


ARMS = {
    "rf": lambda b, tr, te, **k: features(b, tr, te),
    "rf_prior": lambda b, tr, te, **k: features(b, tr, te, norm="prior"),
    "rf_pace": lambda b, tr, te, **k: features(b, tr, te, pace=True),
    "rf_pace_prior": lambda b, tr, te, **k: features(b, tr, te, norm="prior", pace=True),
    "et_pace_prior": lambda b, tr, te, **k: features(b, tr, te, head="et", norm="prior", pace=True),
    "gb_pace_prior": lambda b, tr, te, **k: features(b, tr, te, head="gb", norm="prior", pace=True),
    "lda_pace_prior": lambda b, tr, te, **k: features(b, tr, te, head="lda", norm="prior", pace=True),
    "cnn": lambda b, tr, te, **k: cnn(b, tr, te, **k),
    "cnn_prior": lambda b, tr, te, **k: cnn(b, tr, te, adabn="prior", **k),
    "cnn_f": lambda b, tr, te, **k: cnn(b, tr, te, fnorm=True, **k),
    "cnn_f_prior": lambda b, tr, te, **k: cnn(b, tr, te, fnorm=True, adabn="prior", **k),
    "cnn_perlink": lambda b, tr, te, **k: cnn_perlink_product(b, tr, te, **k),
    "cnn_prior_6k": lambda b, tr, te, **k: cnn(b, tr, te, adabn="prior", **{**k, "steps": 6000}),
    "cnn_prior_12k": lambda b, tr, te, **k: cnn(b, tr, te, adabn="prior", **{**k, "steps": 12000}),
    "cnn_prior_place": lambda b, tr, te, **k: cnn(b, tr, te, adabn="prior", tilt_sd=0.3, **k),
    "cnn_f_prior_place": lambda b, tr, te, **k: cnn(b, tr, te, fnorm=True, adabn="prior", tilt_sd=0.3, **k),
    "s0": lambda b, tr, te, **k: L.arm_s0(b, tr, te),
}
FEATURE_ARMS = ("rf", "rf_prior", "rf_pace", "rf_pace_prior", "et_pace_prior", "gb_pace_prior", "lda_pace_prior", "s0")


def _kw(arm, kw):
    return {} if arm in FEATURE_ARMS else kw


def inner_oof(bank, tr, arm, **kw):
    """Out-of-fold log-probabilities over the training sessions, leaving one training session out."""
    a = bank["a"]
    oof = np.zeros((len(tr), 6))
    for s in np.unique(a["session"][tr]):
        m = a["session"][tr] == s
        oof[m] = ARMS[arm](bank, np.asarray(tr)[~m], np.asarray(tr)[m], **_kw(arm, kw))
    return oof


def select(bank, tr, te, candidates, **kw):
    """Choose among candidates by inner leave-one-session-out accuracy on tracking passes, then fit the
    winner on all the training sessions. Returns (test log-probs, the choice, inner accuracies, the
    winner's out-of-fold log-probs)."""
    a = bank["a"]
    y = np.array([CLASSES.index(v) for v in a["anon"][tr]])
    trk = a["kind"][tr] == "track"
    inner, oofs = {}, {}
    for c in candidates:
        oofs[c] = inner_oof(bank, tr, c, **kw)
        inner[c] = round(100 * float(np.mean(oofs[c][trk].argmax(1) == y[trk])), 2)
    best = max(candidates, key=lambda c: inner[c])
    return ARMS[best](bank, tr, te, **_kw(best, kw)), best, inner, oofs[best]


def multipass(bank, te, Lte, T, ks=(1, 3, 5, 10)) -> dict:
    """Decisions from the first k passes of each test walk (tracking recordings), summing log-probs / T."""
    a = bank["a"]
    rid = recording_ids(a)
    out = {}
    trk = np.flatnonzero(a["kind"][te] == "track")
    for k in ks:
        dec, tru = [], []
        for r in np.unique(rid[np.asarray(te)[trk]]):
            idx = trk[rid[np.asarray(te)[trk]] == r]
            idx = idx[np.argsort(a["t_start"][np.asarray(te)[idx]])][:k]
            dec.append(CLASSES[int((Lte[idx] / T).sum(0).argmax())])
            tru.append(a["anon"][np.asarray(te)[idx[0]]])
        out[str(k)] = {"acc_pct": round(100 * float(np.mean(np.array(dec) == np.array(tru))), 2), "n_walks": len(dec)}
    return out


def run(arms, selects, tag, seeds, steps, device="cpu") -> dict:
    import torch
    torch.set_num_threads(min(4, int(os.environ.get("OMP_NUM_THREADS", "4"))))
    bank = L.load()
    a = bank["a"]
    kw = {"seeds": tuple(seeds), "steps": steps, "device": device}
    doc = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "kw": kw, "arms": {}}
    jobs = [(x, [x]) for x in arms] + [(n, c.split(",")) for n, c in (s.split(":") for s in selects)]
    for name, cands in jobs:
        t0 = time.time()
        res, choices = {}, {}
        for s in SESSIONS:
            tr, te = np.flatnonzero(a["session"] != s), np.flatnonzero(a["session"] == s)
            if len(cands) == 1:
                Lte = ARMS[cands[0]](bank, tr, te, **_kw(cands[0], kw))
                oof, choice, inner = None, cands[0], None
            else:
                Lte, choice, inner, oof = select(bank, tr, te, cands, **kw)
            T = 1.0
            if oof is not None:
                ytr = np.array([CLASSES.index(v) for v in a["anon"][tr]])
                T = C.fit_temperature(oof, ytr)
            m = a["kind"][te] == "track"
            r = {"T_tracking": L.score(bank, te[m], Lte[m], f"{name}|{s}|T"), "choice": choice, "inner_acc": inner,
                 "temperature": T, "multipass_T": multipass(bank, te, Lte, T)}
            if (~m).any():
                r["I_idcap"] = L.score(bank, te[~m], Lte[~m], f"{name}|{s}|I")
            res[s] = r
            choices[s] = {"te": te.tolist(), "pred": np.array(CLASSES)[Lte.argmax(1)].tolist()}
            print(f"{time.strftime('%H:%M:%S')} {name} {s}: {r['T_tracking']['acc_pct']} (choice {choice}, inner {inner}) "
                  f"multipass {r['multipass_T']}", flush=True)
        for room in ("A", "B"):
            te = np.concatenate([np.array(choices[s]["te"]) for s in SESSIONS if s[0] == room])
            pr = np.concatenate([np.array(choices[s]["pred"]) for s in SESSIONS if s[0] == room])
            m = a["kind"][te] == "track"
            from pipeline.identify import id29_dc2_score as D
            res[f"room_{room}_T"] = D.id_stats([{"tag": f"{name}|{room}", "te": list(map(int, te[m])), "pred": pr[m].tolist(),
                                                  "truth": a["anon"][te[m]].tolist()}], {"anon": a["anon"]}, D.Config())
        doc["arms"][name] = {"results": res, "preds": choices, "seconds": round(time.time() - t0, 1), "candidates": cands}
        print(f"{time.strftime('%H:%M:%S')} {name} rooms: A {res['room_A_T']['acc_pct']} {res['room_A_T']['ci95_pct']}, "
              f"B {res['room_B_T']['acc_pct']} {res['room_B_T']['ci95_pct']}, {doc['arms'][name]['seconds']} s", flush=True)
        txt = json.dumps(doc, indent=1, default=str)
        assert IC.no_names(txt)
        open(os.path.join(L.OUT, f"dev_{tag}.json"), "w").write(txt)
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--arms", nargs="*", default=[])
    ap.add_argument("--select", nargs="*", default=[], help="name:cand1,cand2,...")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0])
    ap.add_argument("--steps", type=int, default=3000)
    a = ap.parse_args(argv)
    run(a.arms, a.select, a.tag, a.seeds, a.steps)
    return 0


if __name__ == "__main__":
    sys.exit(main())
