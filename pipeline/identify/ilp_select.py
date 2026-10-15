"""ilp_select. The last push's selection (`runs/identify/lastpush/PREREG_LP.md`, section 6), on the development score only:
the best guard-passing single configuration; the best compatible pair built from the three best guard-passing
configurations of different candidates (compatible = changing different things: ensemble, feature transform,
normalisation, trainer, CNN or maps, window), each pair scored on the development folds; at most two forwarded, each
only if its DS is at least v4's + 3 points. Writes `runs/identify/lastpush/selection.json`.

    PYTHONPATH=. python3 -m pipeline.identify.ilp_select

Exploratory development, all data seen; selection on A1, A2 and B1 only.
"""

from __future__ import annotations

import itertools
import json
import os
import sys
import time

import numpy as np

from pipeline.identify import ilp_cand as PC
from pipeline.identify import ilp_score as PS
from pipeline.identify import ilp_train as LT

CLASS = {"H3": "ensemble", "F1": "transform", "F4": "transform", "F5": "transform", "F2": "normalisation",
         "F3": "normalisation", "F6": "trainer", "F7": "trainer", "F8": "trainer", "F9": "trainer", "R1": "cnn",
         "R2": "cnn", "R3": "cnn", "W1": "window"}
THRESH = 3.0


def candidate(name: str) -> str:
    return name.split("_")[0][:2] if name[0] in "FHRW" else name


def config_of(name: str) -> dict:
    c = candidate(name)
    if c in ("R1", "R2", "R3") or c == "W1":
        return {"scores": name}
    return PC.grid(c)[name]


def build_pair(a: str, b: str) -> tuple:
    """(ensemble log-probabilities per fold, None) for a compatible pair, or (None, reason) when it cannot be built."""
    ca, cb = config_of(a), config_of(b)
    scores = [c["scores"] for c in (ca, cb) if "scores" in c]
    rest = {k: v for c in (ca, cb) if "scores" not in c for k, v in c.items()}
    if len(scores) == 2:
        return None, "two score-only candidates (CNN or window) cannot be combined without retraining"
    if scores and scores[0].startswith("W1") and rest.get("kind") != "H3":
        return None, "a window candidate pairs only with ensemble weights (its features come from another bank)"
    if rest.get("kind") == "H3" and len(rest) > 2:
        rest.pop("kind")
    PC.load_folds()
    saved = {f: dict(fd) for f, fd in PC.FD.items()}
    if scores:
        for f, fd in PC.FD.items():
            z = np.load(os.path.join(PS.SC, f"{scores[0]}_{f}_{fd['session']}.npz"))
            assert np.array_equal(z["te"], fd["te"])
            for k in z.files:
                if k.startswith("c_"):
                    fd[k] = z[k]
            fd["ensemble"] = z["ensemble"]
    try:
        lps = PC.run_config(rest if rest else {"kind": "H3", "weights": {}})
    finally:
        PC.FD.clear()
        PC.FD.update(saved)
    return lps, None


def run() -> dict:
    dev = json.load(open(os.path.join(PC.OUT, "dev.json")))
    v4 = dev["configs"]["v4"]["DS"]
    ok = {k: c for k, c in dev["configs"].items() if k != "v4" and c["guard"]}
    ranked = sorted(ok, key=lambda k: -ok[k]["DS"])
    res = {"label": LT.LABEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "v4_DS": v4,
           "n_scored": dev.get("n_configurations_scored"), "threshold_points": THRESH,
           "guard_failures": sorted(k for k, c in dev["configs"].items() if k != "v4" and not c["guard"])}
    best = ranked[0] if ranked else None
    res.update({"best_single": best, "best_single_DS": ok[best]["DS"] if best else None,
                "best_single_minus_v4": round(ok[best]["DS"] - v4, 2) if best else None})
    fwd = [best] if best and ok[best]["DS"] >= v4 + THRESH else []
    top, seen = [], set()
    for k in ranked:
        if candidate(k) not in seen:
            top.append(k)
            seen.add(candidate(k))
        if len(top) == 3:
            break
    res["top3_different_candidates"] = top
    pairs = {}
    for a, b in itertools.combinations(top, 2):
        name = f"{a}+{b}"
        if CLASS.get(candidate(a)) == CLASS.get(candidate(b)):
            pairs[name] = {"built": False, "reason": f"incompatible: both change the {CLASS.get(candidate(a))}"}
            continue
        lps, why = build_pair(a, b)
        if lps is None:
            pairs[name] = {"built": False, "reason": why}
            continue
        PC.load_folds()
        r = PC.ds_of(lps)
        r["guard"] = bool(r["B1_slow"] >= dev["configs"]["v4"]["B1_slow"] - 5 and r["B1_fast"] >= dev["configs"]["v4"]["B1_fast"] - 5)
        r["minus_v4"] = round(r["DS"] - v4, 2)
        pairs[name] = {"built": True, **r}
        print(f"pair {name}: DS {r['DS']} ({r['minus_v4']:+.2f}), guard {r['guard']}", flush=True)
    res["pairs"] = pairs
    built = {k: p for k, p in pairs.items() if p.get("built") and p["guard"]}
    bp = max(built, key=lambda k: built[k]["DS"]) if built else None
    res["best_pair"] = bp
    if bp and built[bp]["DS"] >= v4 + THRESH and bp not in fwd:
        fwd.append(bp)
    res["forwarded"] = fwd[:2]
    res["n_scored_including_pairs"] = (res["n_scored"] or 0) + sum(1 for p in pairs.values() if p.get("built"))
    json.dump(res, open(os.path.join(LT.LP, "selection.json"), "w"), indent=1)
    print(json.dumps({k: res[k] for k in ("v4_DS", "best_single", "best_single_DS", "best_single_minus_v4", "best_pair",
                                          "forwarded", "n_scored_including_pairs")}, indent=1), flush=True)
    return res


def lps_of(name: str) -> dict:
    """{fold: ensemble log-probabilities} of a configuration (single or "a+b" pair), recomputed as when it was scored."""
    PC.load_folds()
    if name == "v4":
        return {f: fd["ensemble"] for f, fd in PC.FD.items()}
    if "+" in name:
        lps, why = build_pair(*name.split("+"))
        assert lps is not None, why
        return lps
    c = config_of(name)
    if "scores" in c:
        return {f: np.load(os.path.join(PS.SC, f"{c['scores']}_{f}_{fd['session']}.npz"))["ensemble"] for f, fd in PC.FD.items()}
    return PC.run_config(c)


def intervals(names: list, n_boot: int = 10000, seed: int = 0) -> dict:
    """For the report only (selection stays on DS point values): DS minus v4's DS with a paired participant-bootstrap
    95 % interval; the six participants are resampled jointly across the four DS cells."""
    PC.load_folds()
    b = PC.bank()
    cells = [("D1", "path"), ("D2", "path"), ("D3", "path"), ("D3", "natural")]
    rng = np.random.default_rng(seed)
    counts = np.zeros((n_boot, 6))
    np.add.at(counts, (np.repeat(np.arange(n_boot), 6), rng.integers(0, 6, (n_boot, 6)).ravel()), 1)

    def per_part(lps):
        out = []
        for f, cell in cells:
            fd = PC.FD[f]
            m = PC.cells(f, fd["te"])[cell]
            who = b["a"]["anon"][fd["te"]][m]
            ok = PC.accuracy(lps[f], fd["te"])[m]
            out.append((np.array([ok[who == p].sum() for p in PC.CLASSES]), np.array([(who == p).sum() for p in PC.CLASSES])))
        return out

    def ds_boot(pp):
        return np.mean([(counts @ s_) / (counts @ n_) for s_, n_ in pp], axis=0)
    v4 = per_part(lps_of("v4"))
    v4b = ds_boot(v4)
    res = {"n_boot": n_boot, "seed": seed, "clusters": "participants (6), jointly across the four DS cells", "rows": {}}
    for name in names:
        pp = per_part(lps_of(name))
        d = ds_boot(pp) - v4b
        point = np.mean([s_.sum() / n_.sum() for s_, n_ in pp]) - np.mean([s_.sum() / n_.sum() for s_, n_ in v4])
        lo, hi = np.percentile(d, [2.5, 97.5])
        res["rows"][name] = {"DS_minus_v4": round(100 * float(point), 2), "ci95": [round(100 * float(lo), 2), round(100 * float(hi), 2)]}
        print(f"{name}: {res['rows'][name]}", flush=True)
    return res


def write_intervals(k: int = 5) -> dict:
    dev = json.load(open(os.path.join(PC.OUT, "dev.json")))
    names = sorted((n for n in dev["configs"] if n != "v4"), key=lambda n: -dev["configs"][n]["DS"])[:k]
    sel = os.path.join(LT.LP, "selection.json")
    if os.path.exists(sel):
        names += [n for n, p in json.load(open(sel)).get("pairs", {}).items() if p.get("built")]
    res = intervals(names)
    res["n_configurations_scored"] = dev.get("n_configurations_scored")
    json.dump(res, open(os.path.join(PC.OUT, "ds_intervals.json"), "w"), indent=1)
    return res


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "intervals":
        write_intervals()
    else:
        run()
    sys.exit(0)
