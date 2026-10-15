"""idw_eval. The identification-walks brief: stages A (training data, calibration check), B (direction) and
C (deployment measures), from the saved per-pass log-probabilities of `idw_run`, with the decision rules of
`runs/identify/idwalks/PLAN.md` section 6. No training here.

Statistics: 95 % percentile intervals by bootstrap over participants (10,000 resamples of the six, each
carrying all its passes in the scored set), paired where two settings score the same passes; seed 0.

    PYTHONPATH=. python3 -m pipeline.identify.idw_eval [--stage A|B|C|all]
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import time

import numpy as np

from pipeline.identify import idmax_common as IC
from pipeline.identify import idw_run as R
from pipeline.identify import idx_loso as L

OUT = os.path.join("runs", "identify", "idwalks")
CL = np.array(L.CLASSES)
NB, SEED = 10000, 0
FOLDS = ("toB2", "toB1")
CALS = ("others", "causal", "none")
LABEL = "development evaluation, all data seen"


# ------------------------------------------------------------------ bootstrap over participants

def _boot(values, who, n=NB, seed=SEED):
    """Mean of `values` with a 95 % interval, resampling participants (clusters) with replacement."""
    values, who = np.asarray(values, float), np.asarray(who)
    u = np.unique(who)
    s = np.array([values[who == p].sum() for p in u])
    c = np.array([(who == p).sum() for p in u])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(u), (n, len(u)))
    bs = s[idx].sum(1) / np.maximum(c[idx].sum(1), 1)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return {"pct": round(100 * float(values.mean()), 2), "ci95": [round(100 * float(lo), 2), round(100 * float(hi), 2)],
            "n": int(len(values))}


def acc(correct, who):
    return _boot(correct, who)


def paired(ca, cb, who):
    d = _boot(np.asarray(ca, float) - np.asarray(cb, float), who)
    d["ABOVE_ZERO"] = d["ci95"][0] > 0
    d["EXCLUDES_ZERO"] = d["ci95"][0] > 0 or d["ci95"][1] < 0
    return d


# ------------------------------------------------------------------ loading

def load_cfg(name: str, cal: str, a) -> dict:
    """Both folds of one configuration: rows, log-probabilities (ensemble, no-pace, S0, components)."""
    parts = []
    for f in FOLDS:
        p = os.path.join(R.OUTPUTS, f"{name}_{f}_{cal}.npz")
        if not os.path.exists(p):
            return None
        z = np.load(p)
        parts.append({k: z[k] for k in z.files} | {"fold": np.full(len(z["te"]), f)})
    d = {k: np.concatenate([q[k] for q in parts]) for k in parts[0]}
    te = d["te"]
    d.update({"who": a["anon"][te], "block": a["block"][te], "path": a["path"][te], "t_start": a["t_start"][te],
              "session": a["session"][te]})
    return d


def correct(d, key="ensemble") -> np.ndarray:
    return (CL[d[key].argmax(1)] == d["who"]).astype(float)


def masks(d) -> dict:
    nat = d["block"] == "natural"
    return {"natural_both": nat, "natural_away": nat & (d["path"] == "A_fwd"), "natural_towards": nat & (d["path"] == "A_rev"),
            "slow": d["block"] == "slow", "fast": d["block"] == "fast"}


def cell(d, key, m) -> dict:
    """Per fold and pooled, on the passes in mask m."""
    c = correct(d, key)
    out = {}
    for f in FOLDS:
        k = m & (d["fold"] == f)
        out[f] = _boot(c[k], d["who"][k]) if k.any() else None
    out["pooled"] = _boot(c[m], d["who"][m])
    return out


# ------------------------------------------------------------------ stage A

def stage_a(a) -> dict:
    res = {"label": LABEL, "rows": {}, "controls": {}, "rule": {}, "calibration_check": {}}
    data = {(s, c): load_cfg(s, c, a) for s in R.SETS for c in CALS}
    for (s, c), d in data.items():
        if d is None:
            continue
        mk = masks(d)
        res["rows"][f"{s}|{c}"] = {b: cell(d, "ensemble", m) for b, m in mk.items()}
        res["controls"][f"{s}|{c}"] = {"no_pace": {b: cell(d, "ensemble_nopace", m) for b, m in mk.items()},
                                       "S0": {b: cell(d, "s0", m) for b, m in mk.items()}}
    # the headline rule: the first set S (TR-B, TR-B+, TR-AB) that no larger set clearly beats
    nat = {s: data[(s, "others")] for s in R.SETS}
    if all(v is not None for v in nat.values()):
        base = nat["TR-B"]
        for s in R.SETS:
            assert np.array_equal(nat[s]["te"], base["te"])
        m = masks(base)["natural_both"]
        who = base["who"][m]
        comps = {}
        for i, s in enumerate(R.SETS):
            for s2 in R.SETS[i + 1:]:
                comps[f"{s2} - {s}"] = paired(correct(nat[s2])[m], correct(nat[s])[m], who)
        chosen = R.SETS[-1]
        for i, s in enumerate(R.SETS):
            if not any(comps[f"{s2} - {s}"]["ABOVE_ZERO"] for s2 in R.SETS[i + 1:]):
                chosen = s
                break
        res["rule"] = {"paired_natural_pooled_CAL_others": comps, "headline_set": chosen}
        for s in R.SETS:
            dc, do = data[(s, "causal")], data[(s, "others")]
            dn = data[(s, "none")]
            res["calibration_check"][s] = {
                "causal_minus_others": paired(correct(dc)[m], correct(do)[m], who),
                "none_minus_others": paired(correct(dn)[m], correct(do)[m], who)}
        h = res["calibration_check"][chosen]["causal_minus_others"]
        res["calibration_check"]["SLOT_STRUCTURE_FLAG"] = abs(h["pct"]) > 5.0
        # per participant and confusion, headline configuration (natural, pooled)
        d = nat[chosen]
        c = correct(d)
        res["per_participant"] = {p: round(100 * float(c[m & (d["who"] == p)].mean()), 2) for p in L.CLASSES}
        pred = CL[d["ensemble"].argmax(1)]
        res["confusion_natural_pooled"] = {"rows_true_cols_pred": L.CLASSES,
                                           "matrix": [[int(np.sum(m & (d["who"] == t) & (pred == q))) for q in L.CLASSES]
                                                      for t in L.CLASSES]}
    return res


# ------------------------------------------------------------------ stage B

def round_trip_pairs(a, d) -> list:
    """Positions (away, towards) in d of the round-trip pairs (idw_setup's definition)."""
    pairs = np.load(os.path.join(OUT, "round_trip_pairs.npy"))
    pos = {int(r): k for k, r in enumerate(d["te"])}
    return [(pos[int(i)], pos[int(j)]) for i, j in pairs if int(i) in pos and int(j) in pos]


def stage_b(a, headline: str) -> dict:
    res = {"label": LABEL, "pooled_models": {}, "direction_specific": {}}
    for s in sorted({headline, "TR-B"}):
        d = load_cfg(s, "others", a)
        if d is None:
            continue
        pr = [(i, j) for i, j in round_trip_pairs(a, d) if d["block"][i] == "natural"]
        c = correct(d)
        ia, it = np.array([p[0] for p in pr]), np.array([p[1] for p in pr])
        out = {}
        for f in FOLDS + ("pooled",):
            k = np.ones(len(pr), bool) if f == "pooled" else d["fold"][ia] == f
            out[f] = {"away": _boot(c[ia][k], d["who"][ia][k]), "towards": _boot(c[it][k], d["who"][it][k]),
                      "away_minus_towards": paired(c[ia][k], c[it][k], d["who"][ia][k]), "n_pairs": int(k.sum())}
        out["per_participant_away_towards"] = {p: [round(100 * float(c[ia][d["who"][ia] == p].mean()), 1),
                                                   round(100 * float(c[it][d["who"][it] == p].mean()), 1)] for p in L.CLASSES}
        out["verdict"] = ("better: " + ("away" if out["pooled"]["away_minus_towards"]["pct"] > 0 else "towards")
                          if out["pooled"]["away_minus_towards"]["EXCLUDES_ZERO"] else "no detectable difference at this sample size")
        res["pooled_models"][s] = out
    for s in ("TR-B", "TR-AB"):
        for dr in ("away", "towards"):
            d = load_cfg(f"{s}-{dr}", "others", a)
            if d is None:
                continue
            nat = d["block"] == "natural"
            same = nat & (d["path"] == R.DIRPATH[dr])
            other = nat & (d["path"] != R.DIRPATH[dr])
            res["direction_specific"][f"{s}|{dr}"] = {"same_direction": cell(d, "ensemble", same),
                                                      "other_direction": cell(d, "ensemble", other)}
    phys = os.path.join(OUT, "physics", "physics.json")
    if os.path.exists(phys):
        p = json.load(open(phys))
        res["physics"] = {"direction_RX2": p["direction_RX2"],
                          "band_ratios": {k: v for k, v in p["links"].items() if k.startswith("RX2|")}}
    return res


# ------------------------------------------------------------------ stage C

def groups_consecutive(d, m, k) -> list:
    """Non-overlapping groups of k consecutive same-day natural passes by the same person."""
    out = []
    for ses in np.unique(d["session"][m]):
        for p in L.CLASSES:
            idx = np.flatnonzero(m & (d["session"] == ses) & (d["who"] == p))
            idx = idx[np.argsort(d["t_start"][idx], kind="stable")]
            out += [idx[i:i + k] for i in range(0, len(idx) - k + 1, k)]
    return out


def deployment(d, a) -> dict:
    nat = d["block"] == "natural"
    lp, who = d["ensemble"], d["who"]
    res = {}
    top1 = (CL[lp.argmax(1)] == who).astype(float)
    order = np.argsort(-lp, axis=1)
    top2 = np.array([who[i] in CL[order[i, :2]] for i in range(len(who))], float)
    res["single_top1"] = acc(top1[nat], who[nat]) | {"chance": 16.67}
    res["single_top2"] = acc(top2[nat], who[nat]) | {"chance": 33.33}
    for tag, sel in (("natural", True), ("all_paces", False)):
        pr = [(i, j) for i, j in round_trip_pairs(a, d) if (not sel or d["block"][i] == "natural")]
        cc = np.array([CL[(lp[i] + lp[j]).argmax()] == who[i] for i, j in pr], float)
        res[f"round_trip_{tag}"] = acc(cc, who[[i for i, _ in pr]]) | {"chance": 16.67, "n_pairs": len(pr)}
    for k in (3, 5):
        g = groups_consecutive(d, nat, k)
        cc = np.array([CL[lp[x].sum(0).argmax()] == who[x[0]] for x in g], float)
        res[f"walks_k{k}"] = acc(cc, who[[x[0] for x in g]]) | {"chance": 16.67, "n_groups": len(g)}
    for gsz in (2, 3, 4, 5, 6):
        subsets = list(itertools.combinations(range(6), gsz))
        score = np.zeros(int(nat.sum()))
        idx = np.flatnonzero(nat)
        for k, i in enumerate(idx):
            t = L.CLASSES.index(who[i])
            ss = [S for S in subsets if t in S]
            score[k] = np.mean([S[int(np.argmax(lp[i, list(S)]))] == t for S in ss])
        res[f"group_size_{gsz}"] = acc(score, who[idx]) | {"chance": round(100 / gsz, 2)}
    return res


def stage_c(a, headline: str) -> dict:
    res = {"label": LABEL}
    for s in sorted({headline, "TR-B"}):
        d = load_cfg(s, "others", a)
        if d is not None:
            res[f"{s}|others"] = deployment(d, a)
    return res


# ------------------------------------------------------------------ the gated EXPLORATORY arm

def stage_x(a, headline: str) -> dict:
    """The headline configuration with the limb-band feature group in its three RF components, against
    the frozen ensemble on the same passes (natural, pooled, CAL-others). EXPLORATORY."""
    dx, d0 = load_cfg(f"{headline}-X", "others", a), load_cfg(headline, "others", a)
    if dx is None or d0 is None:
        return {}
    assert np.array_equal(dx["te"], d0["te"])
    mk = masks(d0)
    m = mk["natural_both"]
    return {"label": "EXPLORATORY; " + LABEL, "exploratory": {b: cell(dx, "ensemble", mm) for b, mm in mk.items()},
            "frozen": {b: cell(d0, "ensemble", mm) for b, mm in mk.items()},
            "exploratory_minus_frozen_natural": paired(correct(dx)[m], correct(d0)[m], d0["who"][m])}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage", default="all", choices=("A", "B", "C", "all"))
    ap.add_argument("--headline", help="override only for inspection; the rule's choice is used by default")
    x = ap.parse_args(argv)
    bank = L.load()
    a = bank["a"]
    res = {"built": time.strftime("%Y-%m-%dT%H:%M:%S")}
    ra = stage_a(a)
    res["A"] = ra
    headline = x.headline or ra.get("rule", {}).get("headline_set")
    if x.stage in ("B", "all") and headline:
        res["B"] = stage_b(a, headline)
    if x.stage in ("C", "all") and headline:
        res["C"] = stage_c(a, headline)
    if x.stage == "all" and headline:
        res["X"] = stage_x(a, headline)
    txt = json.dumps(res, indent=1, default=str)
    assert IC.no_names(txt)
    open(os.path.join(OUT, f"eval_{x.stage}.json"), "w").write(txt)
    print(json.dumps({"rule": ra.get("rule"), "calibration_check": ra.get("calibration_check")}, indent=1, default=str)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
