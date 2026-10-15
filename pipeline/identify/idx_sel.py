"""idx_sel. Identification batch 2 (the operator's direction of 2026-09-28): the model chosen by inner
leave-one-session-out, never by the test session.

For each held-out session, every candidate is scored by an inner leave-one-session-out over the four
training sessions (accuracy on their tracking passes); the best is refitted on all four and tested.

Components:
- F1 `rf`: RF on the gait features, per-path z;
- F2 `rf_prior`: the same, causal session normalisation;
- F3 `rf_pace_prior`: F2 with press pace as ONE parameter inside the gait feature set;
- C1 `cnn`, C2 `cnn_prior` (AdaBN from earlier recordings): one training gives both;
- C3 `cnn_f`, C4 `cnn_f_prior`: the pace-normalised frequency axis, one training gives both.

Candidates: every component, and the equal-weight product fusions F2+C2, F3+C2, F2+C4 and F3+C4. Every
component is causal: test-session information comes only from recordings that started earlier, without
labels. Inner folds use `inner_steps` and one seed; the final fit uses `steps` and `seeds`.

    PYTHONPATH=. python3 -m pipeline.identify.idx_sel --tag NAME [--inner-steps 1500 --steps 3000 --seeds 0 1 2]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

from pipeline.identify import idmax_common as IC
from pipeline.identify import idv2_core as C
from pipeline.identify import idx_dev as X
from pipeline.identify import idx_loso as L

CLASSES = L.CLASSES
FEATURES = {"rf": dict(), "rf_prior": dict(norm="prior"), "rf_pace_prior": dict(norm="prior", pace=True)}
FUSIONS = {"rf_prior+cnn_prior": ("rf_prior", "cnn_prior"), "rf_pace_prior+cnn_prior": ("rf_pace_prior", "cnn_prior"),
           "rf_prior+cnn_f_prior": ("rf_prior", "cnn_f_prior"), "rf_pace_prior+cnn_f_prior": ("rf_pace_prior", "cnn_f_prior"),
           "rf_prior+cnn_perlink_prior": ("rf_prior", "cnn_perlink_prior"),
           "rf_pace_prior+cnn_perlink_prior": ("rf_pace_prior", "cnn_perlink_prior")}
PERLINK = False          # set by --perlink: adds the per-link CNN family (one CNN per link, product fusion)
NO_CNNF = False          # set by --no-cnnf: drops the pace-normalised CNN family
WIDE_FEATURES = {"et_pace_prior": dict(head="et", norm="prior", pace=True),
                 "lda_pace_prior": dict(head="lda", norm="prior", pace=True)}
WIDE_FUSIONS = {"et_pace_prior+cnn_prior": ("et_pace_prior", "cnn_prior"),
                "lda_pace_prior+cnn_prior": ("lda_pace_prior", "cnn_prior"),
                "et_pace_prior+cnn_perlink_prior": ("et_pace_prior", "cnn_perlink_prior"),
                "lda_pace_prior+cnn_perlink_prior": ("lda_pace_prior", "cnn_perlink_prior")}


def widen() -> None:
    """--wide: the extra-trees and shrinkage-LDA heads, and their fusions with the CNNs."""
    FEATURES.update(WIDE_FEATURES)
    FUSIONS.update(WIDE_FUSIONS)


def cnn_both(bank, tr, te, seeds, steps, fnorm, device="cpu") -> dict:
    """One training per seed; the plain output and the AdaBN-from-earlier-recordings output."""
    a, W = bank["a"], bank["W"]
    dirs = X._dirs(a)
    maps = None
    prior = X.prior_recordings(a, te)
    if fnorm:
        f_ref = float(np.nanmedian(a["f_t"][tr]))
        need = set(np.r_[tr, te].tolist())
        for v in prior.values():
            need |= set(v.tolist())
        maps = [C.rescale_freq(m, f, f_ref) if i in need else None for i, (m, f) in enumerate(zip(bank["maps"], a["f_t"]))]
    Xtr, dtr, ptr = X._stack(W, tr, dirs, None, maps)
    ytr = np.array([CLASSES.index(v) for v in a["anon"][tr]])[ptr]
    st = C.norm_stats(Xtr, dtr)
    Xtr = C.apply_norm(Xtr, dtr, st)
    Xte, dte, pte = X._stack(W, te, dirs, None, maps)
    Xte = C.apply_norm(Xte, dte, st)
    rid = X.recording_ids(a)
    plain, adapted = [], []
    for s in seeds:
        net = C.train_cnn(Xtr, ytr, dtr, 6, s, device, steps)
        plain.append(C.normalise_logp(C.pass_logp(net, Xte, dte, pte, len(te), 6, device)))
        lp = np.zeros((len(te), 6))
        for r, prev in prior.items():
            k = np.flatnonzero(rid[te] == r)
            sub = np.asarray(te)[k]
            netr = net
            if len(prev):
                Xo, do, _p = X._stack(W, prev, dirs, None, maps)
                netr = C.adabn(net, C.apply_norm(Xo, do, st), do, device)
            Xs, ds, ps = X._stack(W, sub, dirs, None, maps)
            lp[k] = C.pass_logp(netr, C.apply_norm(Xs, ds, st), ds, ps, len(sub), 6, device)
        adapted.append(C.normalise_logp(lp))
    return {"plain": C.normalise_logp(np.mean(plain, axis=0)), "prior": C.normalise_logp(np.mean(adapted, axis=0))}


def components(bank, tr, te, seeds, steps, need=None, device="cpu") -> dict:
    """Every component's test log-probabilities (or only those in `need`)."""
    need = set(need) if need is not None else (set(FEATURES) | {"cnn", "cnn_prior"}
                                                | (set() if NO_CNNF else {"cnn_f", "cnn_f_prior"})
                                                | ({"cnn_perlink_prior"} if PERLINK else set()))
    out = {}
    for name, kw in FEATURES.items():
        if name in need:
            out[name] = X.features(bank, tr, te, **kw)
    if need & {"cnn", "cnn_prior"}:
        r = cnn_both(bank, tr, te, seeds, steps, fnorm=False, device=device)
        out["cnn"], out["cnn_prior"] = r["plain"], r["prior"]
    if need & {"cnn_f", "cnn_f_prior"}:
        r = cnn_both(bank, tr, te, seeds, steps, fnorm=True, device=device)
        out["cnn_f"], out["cnn_f_prior"] = r["plain"], r["prior"]
    if "cnn_perlink_prior" in need:
        out["cnn_perlink_prior"] = C.normalise_logp(sum(X.cnn(bank, tr, te, seeds=seeds, steps=steps, device=device, chan=c,
                                                              adabn="prior") for c in range(3)))
    return out


def with_fusions(comp: dict) -> dict:
    out = dict(comp)
    for f, parts in FUSIONS.items():
        if all(p in comp for p in parts):
            out[f] = C.normalise_logp(sum(comp[p] for p in parts))
    return out


def needs(cand: str) -> list:
    return list(FUSIONS[cand]) if cand in FUSIONS else [cand]


def run(tag, inner_steps, steps, seeds, out_dir=L.OUT, device="cpu") -> dict:
    import torch
    torch.set_num_threads(min(4, int(os.environ.get("OMP_NUM_THREADS", "4"))))
    bank = L.load()
    a = bank["a"]
    doc = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "inner_steps": inner_steps, "steps": steps, "seeds": list(seeds), "device": device,
           "folds": {}}
    preds = {}
    for s in L.SESSIONS:
        t0 = time.time()
        tr, te = np.flatnonzero(a["session"] != s), np.flatnonzero(a["session"] == s)
        oof = {}
        ytr = np.array([CLASSES.index(v) for v in a["anon"][tr]])
        for s_in in np.unique(a["session"][tr]):
            m = a["session"][tr] == s_in
            comp = with_fusions(components(bank, tr[~m], tr[m], (0,), inner_steps, device=device))
            for k, v in comp.items():
                oof.setdefault(k, np.zeros((len(tr), 6)))[m] = v
        trk = a["kind"][tr] == "track"
        inner = {k: round(100 * float(np.mean(v[trk].argmax(1) == ytr[trk])), 2) for k, v in oof.items()}
        best = max(inner, key=inner.get)
        T = C.fit_temperature(oof[best], ytr)
        final = with_fusions(components(bank, tr, te, tuple(seeds), steps, need=needs(best), device=device))[best]
        m = a["kind"][te] == "track"
        res = {"choice": best, "inner_acc": inner, "temperature": T,
               "T_tracking": L.score(bank, te[m], final[m], f"sel|{s}|T"),
               "multipass_T": X.multipass(bank, te, final, T)}
        if (~m).any():
            res["I_idcap"] = L.score(bank, te[~m], final[~m], f"sel|{s}|I")
            blk = a["block"][te]
            res["I_by_block"] = {b: round(100 * float(np.mean(np.array(CLASSES)[final[(~m) & (blk == b)].argmax(1)]
                                                                == a["anon"][te][(~m) & (blk == b)])), 2)
                                 for b in ("natural", "slow", "fast")}
        res["seconds"] = round(time.time() - t0, 1)
        doc["folds"][s] = res
        preds[s] = {"te": te.tolist(), "pred": np.array(CLASSES)[final.argmax(1)].tolist()}
        print(f"{time.strftime('%H:%M:%S')} {s}: chose {best} (inner {inner[best]}), test {res['T_tracking']['acc_pct']} "
              f"{res['T_tracking']['ci95_pct']}, {res['seconds']} s", flush=True)
        _write(doc, preds, tag, out_dir)
    from pipeline.identify import id29_dc2_score as D
    for room in ("A", "B"):
        te = np.concatenate([np.array(preds[s]["te"]) for s in L.SESSIONS if s[0] == room])
        pr = np.concatenate([np.array(preds[s]["pred"]) for s in L.SESSIONS if s[0] == room])
        m = a["kind"][te] == "track"
        doc[f"room_{room}_T"] = D.id_stats([{"tag": f"sel|{room}", "te": list(map(int, te[m])), "pred": pr[m].tolist(),
                                              "truth": a["anon"][te[m]].tolist()}], {"anon": a["anon"]}, D.Config())
    _write(doc, preds, tag, out_dir)
    print(f"rooms: A {doc['room_A_T']['acc_pct']} {doc['room_A_T']['ci95_pct']}, B {doc['room_B_T']['acc_pct']} {doc['room_B_T']['ci95_pct']}")
    return doc


def _write(doc, preds, tag, out_dir):
    txt = json.dumps({**doc, "preds": preds}, indent=1, default=str)
    assert IC.no_names(txt)
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, f"sel_{tag}.json"), "w").write(txt)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tag", required=True)
    ap.add_argument("--inner-steps", type=int, default=1500)
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--device", default="cpu", choices=("cpu", "mps"))
    ap.add_argument("--perlink", action="store_true")
    ap.add_argument("--wide", action="store_true")
    ap.add_argument("--no-cnnf", action="store_true")
    a = ap.parse_args(argv)
    global PERLINK, NO_CNNF
    PERLINK = a.perlink
    NO_CNNF = a.no_cnnf
    if a.wide:
        widen()
    run(a.tag, a.inner_steps, a.steps, a.seeds, device=a.device)
    return 0


if __name__ == "__main__":
    sys.exit(main())
