"""iv6_components. Part 1 of Uzayr's components-and-features TEST (15 Oct 2026; rules in `runs/identify/engine/PLAN.md`,
the note of 2026-10-15 14:53, committed in 0243a768 before any candidate score): engine v5's nine components from the
stored replay arrays, no retraining.

    PYTHONPATH=. python3 -m pipeline.identify.iv6_components check    # v5's ensemble recomputed = stored (0.0), first
    PYTHONPATH=. python3 -m pipeline.identify.iv6_components run      # diagnostics, oracles, the five candidates

Development evaluation, all data seen; exploratory. Nothing is adopted.
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
from scipy.optimize import minimize, minimize_scalar

from pipeline.identify import idw_eval as EV
from pipeline.identify import ilp_cand as PC
from pipeline.identify import ilr_report as RR
from pipeline.identify import iv6_common as K
from pipeline.identify import ixr_eval as XE

ONES = {c: 1.0 for c in K.COMPS}
CANDS = ("INVLL", "TEMP", "STACK", "TOP3", "BEST1")


def check() -> bool:
    """v5's ensemble and confidence recomputed from the stored component arrays with `engine.Session.combine`'s formula
    must equal the stored ones (max abs difference 0.0) on all 13 replays before anything else runs."""
    res = {"built": time.strftime("%Y-%m-%d %H:%M:%S"), "label": K.LABEL, "replays": {}}
    for m, (model, sessions) in K.MODELS.items():
        for s in sessions:
            r = K.replay(model, s)
            got = K.combine(r, ONES, rule=True)
            res["replays"][f"{model}|{s}"] = {
                "n": int(len(r["te"])), "weights_a": sorted({float(x) for x in r["a"]}),
                "ensemble_max_abs_diff": float(np.abs(got["ensemble"] - r["ensemble"]).max()),
                "confidence_max_abs_diff": float(np.abs(got["confidence"] - r["confidence"]).max()),
                "argmax_equal": int((got["ensemble"].argmax(1) == r["ensemble"].argmax(1)).sum())}
    res["max_abs_diff"] = max(v["ensemble_max_abs_diff"] for v in res["replays"].values())
    res["PASSED"] = res["max_abs_diff"] == 0.0
    os.makedirs(os.path.join(K.OUT, "checks"), exist_ok=True)
    json.dump(res, open(os.path.join(K.OUT, "checks", "ensemble_equal.json"), "w"), indent=1)
    print(json.dumps({k: res[k] for k in ("max_abs_diff", "PASSED")}
                     | {"confidence_max": max(v["confidence_max_abs_diff"] for v in res["replays"].values()),
                        "n_walks": sum(v["n"] for v in res["replays"].values())}), flush=True)
    return res["PASSED"]


# ------------------------------------------------------------------ every walk of every replay, in one table

class Walks:
    """All 2,695 replayed walks concatenated (13 model-sessions): m_c (N, 6), the window-0 c_0 (N, 6), the stored a,
    the class y, the participant, the test session, and the key's slice. A cell maps to global indices."""

    def __init__(self):
        b = PC.bank()
        self.keys = K.keys()
        self.slices, parts = {}, []
        i0 = 0
        for k in self.keys:
            m, s = k.split("|")
            r = K.replay(K.MODELS[m][0], s)
            n = len(r["te"])
            self.slices[k] = slice(i0, i0 + n)
            i0 += n
            parts.append((r, s))
        self.N = i0
        self.M = {c: np.concatenate([K.walk_mean(r)[c] for r, _ in parts]) for c in K.COMPS}
        self.C0 = {c: np.concatenate([r["c"][c][0] for r, _ in parts]) for c in K.COMPS}
        self.a = np.concatenate([r["a"] for r, _ in parts])
        self.te = np.concatenate([r["te"] for r, _ in parts])
        self.y = K.labels(self.te)
        self.who = b["a"]["anon"][self.te]
        self.sess = np.concatenate([np.full(len(r["te"]), s) for r, s in parts])
        self.key = np.concatenate([np.full(len(r["te"]), k) for (r, _), k in zip(parts, self.keys)])
        self.idx_store = {k: (self.te[self.slices[k]], np.zeros(self.slices[k].stop - self.slices[k].start),
                              np.arange(self.slices[k].start, self.slices[k].stop)) for k in self.keys}

    def cell(self, cells: list) -> np.ndarray:
        return K.cell(cells, self.idx_store)[2]

    def pool(self, S: str) -> np.ndarray:
        """P(S): the loso replays' walks of the four sessions other than S."""
        return np.flatnonzero(np.isin(self.key, [f"loso_{x}|{x}" for x in K.SESSIONS if x != S]))

    def g(self, rule: bool) -> np.ndarray:
        return self.a if rule else np.ones(self.N)

    def logits(self, w: dict, rule: bool, idx=None) -> np.ndarray:
        idx = np.arange(self.N) if idx is None else idx
        g = self.g(rule)[idx]
        z = 0
        for c in K.COMPS:
            k = np.where(np.isin(c, K.FEATC), g, 1.0) * float(w[c])
            z = z + k[:, None] * self.M[c][idx]
        return z


def lsm(z: np.ndarray) -> np.ndarray:
    return K.normalise(z)


def nll(lp: np.ndarray, y: np.ndarray) -> float:
    return float(-lp[np.arange(len(y)), y].mean())


# ------------------------------------------------------------------ the five candidates' fits (PLAN, 14:53)

def comp_ll(W: Walks, idx: np.ndarray) -> dict:
    return {c: nll(lsm(W.M[c][idx]), W.y[idx]) for c in K.COMPS}


def fit_temp(W: Walks, idx: np.ndarray) -> dict:
    T = {}
    for c in K.COMPS:
        M, y = W.M[c][idx], W.y[idx]
        f = lambda lt: nll(lsm(M / np.exp(lt)), y)      # noqa: E731
        T[c] = float(np.exp(minimize_scalar(f, bounds=(-4, 4), method="bounded").x))
    return T


def fit_stack(W: Walks, idx: np.ndarray, rule: bool) -> dict:
    g = W.g(rule)[idx]
    X = np.stack([(np.where(c in K.FEATC, 1.0, 0.0) * g + np.where(c in K.FEATC, 0.0, 1.0))[:, None] * W.M[c][idx]
                  for c in K.COMPS])                                   # (9, n, 6)
    y = W.y[idx]
    Y = np.eye(6)[y]

    def f(w):
        z = np.tensordot(w, X, 1)
        lp = lsm(z)
        P = np.exp(lp)
        return -lp[np.arange(len(y)), y].mean(), np.einsum("cnk,nk->c", X, P - Y) / len(y)
    r = minimize(f, np.ones(len(K.COMPS)), jac=True, method="L-BFGS-B", bounds=[(0, None)] * len(K.COMPS))
    w = r.x
    w = w * (9.0 / w.sum()) if w.sum() > 0 else np.ones(len(K.COMPS))
    return {"w": {c: float(v) for c, v in zip(K.COMPS, w)}, "converged": bool(r.success), "nll": float(r.fun),
            "nit": int(r.nit)}


def fit(cand: str, W: Walks, idx: np.ndarray, rule: bool) -> dict:
    LL = comp_ll(W, idx)
    order = sorted(K.COMPS, key=lambda c: (LL[c], K.COMPS.index(c)))
    if cand == "INVLL":
        inv = {c: 1.0 / LL[c] for c in K.COMPS}
        s = sum(inv.values())
        return {"w": {c: 9.0 * inv[c] / s for c in K.COMPS}, "LL": LL}
    if cand == "TEMP":
        T = fit_temp(W, idx)
        return {"w": {c: 1.0 / T[c] for c in K.COMPS}, "T": T}
    if cand == "STACK":
        return fit_stack(W, idx, rule)
    if cand == "TOP3":
        return {"w": {c: (1.0 if c in order[:3] else 0.0) for c in K.COMPS}, "chosen": order[:3], "LL": LL}
    if cand == "BEST1":
        return {"w": {c: (1.0 if c == order[0] else 0.0) for c in K.COMPS}, "chosen": order[:1], "LL": LL}
    raise KeyError(cand)


def cross_fitted(cand: str, W: Walks, rule: bool) -> dict:
    return {S: fit(cand, W, W.pool(S), rule) for S in K.SESSIONS}


def lps_of(fits: dict, rule: bool) -> dict:
    """{model|session: ensemble} with the weights fitted for each test session, through the engine's form (K.combine)."""
    out = {}
    for m, (model, sessions) in K.MODELS.items():
        for s in sessions:
            out[f"{m}|{s}"] = K.combine(K.replay(model, s), fits[s]["w"], rule)
    return out


# ------------------------------------------------------------------ scoring against v5

def cells_named() -> dict:
    out = {}
    for c in K.ZERO:
        out["Z " + "|".join(c)] = [c]
    for c in K.CROSS:
        out["D " + "|".join(c)] = [c]
    for nm, cc in K.GUARDS.items():
        out["guard " + nm] = cc
    for nm, cc in K.CORE.items():
        out["core " + nm] = cc
    return out


def pct(ok) -> float:
    return round(100 * float(np.mean(ok)), 2)


def score(st: dict, v5: dict) -> dict:
    """The headline, guards, core and every cell of a store against v5's on the same walks."""
    who_all = PC.bank()["a"]["anon"]
    zd = RR.zd(st, v5)
    z = np.mean([K.cell([c], st)[1].mean() for c in K.ZERO])
    d = np.mean([K.cell([c], st)[1].mean() for c in K.CROSS])
    out = {"Z": round(100 * z, 2), "D": round(100 * d, 2), "score": round(50 * (z + d), 2),
           "Z_minus_v5": zd["Z"], "D_minus_v5": zd["D"], "score_minus_v5": zd["score"], "cells": {}}
    for nm, cc in cells_named().items():
        r1, ok1, _ = K.cell(cc, st)
        r0, ok0, _ = K.cell(cc, v5)
        assert np.array_equal(r1, r0)
        w = who_all[r1]
        out["cells"][nm] = {"n": int(len(r1)), "acc": EV._boot(ok1, w), "v5": pct(ok0), "minus_v5": XE.paired(ok1, ok0, w)}
    g_ok = {nm: out["cells"]["guard " + nm]["acc"]["pct"] >= out["cells"]["guard " + nm]["v5"] - K.GUARD_MARGIN
            for nm in K.GUARDS}
    c_ok = {nm: out["cells"]["core " + nm]["acc"]["pct"] >= out["cells"]["core " + nm]["v5"] for nm in K.CORE}
    out["guards_hold"], out["core_holds"] = g_ok, c_ok
    out["headline_above_zero"] = bool(zd["score"]["ci95"][0] > 0)
    out["PASSES"] = bool(out["headline_above_zero"] and all(g_ok.values()) and all(c_ok.values()))
    return out


def confidence_medians(lps: dict, W: Walks) -> dict:
    """The displayed confidence (top class) on loso natural walks, median for right and wrong decisions."""
    st = K.store({k: v["ensemble"] for k, v in lps.items()})
    cs = {k: (st[k][0], st[k][1], v["confidence"].max(1)) for k, v in lps.items()}
    _r, ok, conf = K.cell([("loso", "*", "natural")], cs)
    return {"right": round(float(np.median(conf[ok == 1])), 3), "wrong": round(float(np.median(conf[ok == 0])), 3)}


# ------------------------------------------------------------------ diagnostics (1a; no weight fitted)

def ece(P: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
    conf, pred = P.max(1), P.argmax(1)
    ok = (pred == y).astype(float)
    b = np.minimum((conf * bins).astype(int), bins - 1)
    return float(sum(abs(ok[b == i].mean() - conf[b == i].mean()) * (b == i).mean() for i in range(bins) if (b == i).any()))


def comp_diag(W: Walks, idx: np.ndarray, E: np.ndarray, Eloco: dict) -> dict:
    """Per component on the walks idx: accuracy (participant interval), log-loss, Brier, ECE, sharpness, margin share,
    leave-one-out flips and the leave-one-out ensemble's accuracy paired against v5."""
    y, who = W.y[idx], W.who[idx]
    top = E[idx].argmax(1)
    ok5 = (top == y).astype(float)
    second = np.argsort(-E[idx], 1)[:, 1]
    g = W.a[idx]
    terms = {c: (g if c in K.FEATC else 1.0) * (W.M[c][idx][np.arange(len(idx)), top] - W.M[c][idx][np.arange(len(idx)), second])
             for c in K.COMPS}
    tot = sum(terms.values())
    out = {}
    for c in K.COMPS:
        lp = lsm(W.M[c][idx])
        P = np.exp(lp)
        okc = (lp.argmax(1) == y).astype(float)
        lo = Eloco[c][idx].argmax(1)
        okl = (lo == y).astype(float)
        out[c] = {"acc": EV._boot(okc, who), "logloss": round(nll(lp, y), 4),
                  "brier": round(float(((P - np.eye(6)[y]) ** 2).sum(1).mean()), 4), "ece": round(ece(P, y), 4),
                  "sharpness": round(float((lp.max(1) - lp.min(1)).mean()), 3),
                  "sharpness_w0": round(float((W.C0[c][idx].max(1) - W.C0[c][idx].min(1)).mean()), 3),
                  "margin_share": round(float(np.mean(terms[c] / tot)), 4),
                  # added 15 Oct after the first run showed the per-walk ratio exploding on near-tie walks (disclosed):
                  "margin_share_pooled": round(float(terms[c].sum() / tot.sum()), 4),
                  "margin_share_median": round(float(np.median(terms[c] / tot)), 4),
                  "loco_flips": int((lo != top).sum()), "loco_right_to_wrong": int(((ok5 == 1) & (okl == 0)).sum()),
                  "loco_wrong_to_right": int(((ok5 == 0) & (okl == 1)).sum()),
                  "loco_acc": pct(okl), "loco_minus_v5": XE.paired(okl, ok5, who)}
    return out


def pairs(W: Walks, idx: np.ndarray) -> dict:
    y = W.y[idx]
    pred = {c: W.M[c][idx].argmax(1) for c in K.COMPS}
    err = {c: (pred[c] != y).astype(float) for c in K.COMPS}
    out = {}
    for i, a in enumerate(K.COMPS):
        for b in K.COMPS[i + 1:]:
            r = np.corrcoef(err[a], err[b])[0, 1] if err[a].std() > 0 and err[b].std() > 0 else float("nan")
            out[f"{a}|{b}"] = {"error_corr": round(float(r), 3), "disagreement": round(float((pred[a] != pred[b]).mean()), 3)}
    return out


def oracle(W: Walks, idx: np.ndarray) -> dict:
    y, who = W.y[idx], W.who[idx]
    accs = {c: pct(W.M[c][idx].argmax(1) == y) for c in K.COMPS}
    best = max(K.COMPS, key=lambda c: (accs[c], -K.COMPS.index(c)))
    st = fit_stack(W, idx, rule=True)
    ok = (W.logits(st["w"], True, idx).argmax(1) == y).astype(float)
    return {"best_single": best, "best_single_acc": accs[best], "stack_in_cell_acc": EV._boot(ok, who),
            "stack_in_cell_w": {c: round(v, 3) for c, v in st["w"].items()}}


def run() -> dict:
    t0 = time.time()
    assert check(), "the ensemble check failed: nothing else runs"
    W = Walks()
    res = {"label": K.LABEL, "built": time.strftime("%Y-%m-%d %H:%M:%S"), "plan": "runs/identify/engine/PLAN.md, note of "
           "2026-10-15 14:53 (commit 0243a768)", "n_walks": W.N}
    E = lsm(W.logits(ONES, True))
    Eloco = {c: lsm(W.logits(ONES | {c: 0.0}, True)) for c in K.COMPS}
    # v5 from W equals the replays (algebraic form) in every decision
    lps5 = lps_of({s: {"w": ONES} for s in K.SESSIONS}, True)
    v5 = K.store({k: v["ensemble"] for k, v in lps5.items()})
    dec = np.concatenate([v5[k][2].argmax(1) for k in W.keys])
    res["algebraic_form_decisions_equal"] = int((dec == E.argmax(1)).sum())
    allho0 = np.isin(W.key, [f"loso_{s}|{s}" for s in K.SESSIONS])
    res["v5_all_held_out_acc"] = EV._boot((E.argmax(1) == W.y)[allho0].astype(float), W.who[allho0])
    assert res["algebraic_form_decisions_equal"] == W.N

    # 1a diagnostics
    named = cells_named()
    res["diagnostics"] = {"cells": {}, "sessions": {}}
    for nm, cc in named.items():
        res["diagnostics"]["cells"][nm] = comp_diag(W, W.cell(cc), E, Eloco)
    for s in K.SESSIONS:
        idx = np.flatnonzero(W.key == f"loso_{s}|{s}")
        res["diagnostics"]["sessions"][s] = comp_diag(W, idx, E, Eloco)
    allho = np.flatnonzero(np.isin(W.key, [f"loso_{s}|{s}" for s in K.SESSIONS]))
    res["diagnostics"]["all_held_out"] = comp_diag(W, allho, E, Eloco)
    res["diagnostics"]["pairs"] = {"all_held_out": pairs(W, allho)} | {nm: pairs(W, W.cell(K.CORE[nm])) for nm in K.CORE}
    best = {}
    for s in K.SESSIONS:
        d = res["diagnostics"]["sessions"][s]
        best[s] = {"by_acc": max(K.COMPS, key=lambda c: (d[c]["acc"]["pct"], -K.COMPS.index(c))),
                   "by_logloss": min(K.COMPS, key=lambda c: (d[c]["logloss"], K.COMPS.index(c)))}
    seq = [best[s]["by_acc"] for s in K.SESSIONS]
    seql = [best[s]["by_logloss"] for s in K.SESSIONS]
    res["diagnostics"]["best_by_session"] = {
        "per_session": best, "distinct_by_acc": len(set(seq)), "changes_by_acc": int(sum(a != b for a, b in zip(seq, seq[1:]))),
        "distinct_by_logloss": len(set(seql)), "changes_by_logloss": int(sum(a != b for a, b in zip(seql, seql[1:])))}
    res["oracles"] = {nm: oracle(W, W.cell(cc)) for nm, cc in named.items()}
    print(f"{time.strftime('%H:%M:%S')} diagnostics and oracles done ({time.time() - t0:.0f} s)", flush=True)

    # 1b candidates, with the installation rule (judged) and without (information)
    res["v5"] = {"store_check": "every decision equal to the replays", "confidence_natural": confidence_medians(lps5, W)}
    lps5n = lps_of({s: {"w": ONES} for s in K.SESSIONS}, False)
    v5n = K.store({k: v["ensemble"] for k, v in lps5n.items()})
    res["v5_without_rule"] = score(v5n, v5)
    res["candidates"] = {}
    for cand in CANDS:
        rec = {}
        for rule in (True, False):
            fits = cross_fitted(cand, W, rule)
            lps = lps_of(fits, rule)
            st = K.store({k: v["ensemble"] for k, v in lps.items()})
            sc = score(st, v5)
            sc["weights"] = {S: {c: round(f["w"][c], 4) for c in K.COMPS} for S, f in fits.items()}
            sc["fit_info"] = {S: {k: v for k, v in f.items() if k != "w"} for S, f in fits.items()}
            sc["confidence_natural"] = confidence_medians(lps, W)
            if not rule:
                sc["PASSES"] = None
                sc["note"] = "information only (without the installation rule); cannot pass"
            rec["with_rule" if rule else "without_rule"] = sc
        res["candidates"][cand] = rec
        w = rec["with_rule"]
        print(f"{time.strftime('%H:%M:%S')} {cand}: (Z+D)/2 {w['score']} minus v5 {w['score_minus_v5']} guards "
              f"{w['guards_hold']} core {w['core_holds']} PASSES {w['PASSES']}", flush=True)
    res["any_passes"] = any(res["candidates"][c]["with_rule"]["PASSES"] for c in CANDS)
    res["seconds"] = round(time.time() - t0, 1)
    os.makedirs(K.OUT, exist_ok=True)
    json.dump(res, open(os.path.join(K.OUT, "part1.json"), "w"), indent=1, default=str)
    return res


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "check":
        sys.exit(0 if check() else 1)
    if what == "run":
        run()
        sys.exit(0)
    sys.exit(2)
