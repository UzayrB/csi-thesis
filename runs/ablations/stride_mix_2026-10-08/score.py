"""Score the stride ablation under PLAN.md's fixed rule; write results.json and RESULTS.md here.

Primary: ALL05 minus MIX and ALL1 minus MIX on pooled committed-line error (the three rotations, 360 walks), paired
by seed set, mean and 95 % t-interval over the seed sets. Secondary: per-arm figures averaged over the seed sets with a
95 % bootstrap interval over walks (1,000 draws, seed 0), the lock, the edge lines and the per-rotation splits.
Development evaluation, all data seen.
"""

from __future__ import annotations

import json
import os
import statistics
import sys

import numpy as np
from scipy import stats

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
ROTS = ("B1", "A2", "A1")
ARMS = ("MIX", "ALL05", "ALL1")
KS = (0, 1, 2)
EDGES = ("E_col1", "E_col5", "E_row1", "E_row5")
LABEL = "development evaluation, all data seen"


def load(rot, arm, k):
    p = J(HERE, "runs", rot, f"eval_{arm}_k{k}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def complete(arm, k):
    return all(load(r, arm, k) for r in ROTS)


def pooled(arm, k) -> dict:
    ev = [load(r, arm, k) for r in ROTS]
    n = sum(e["walks"] for e in ev)
    out = {m: sum(e[m] * e["walks"] for e in ev) / n for m in ("committed_err_pct", "committed_pct", "lock_pct")}
    out["walks"] = n
    return out


def interval(d):
    m = statistics.fmean(d)
    if len(d) < 2:
        return m, float("nan"), float("nan")
    h = stats.t.ppf(0.975, len(d) - 1) * statistics.stdev(d) / len(d) ** 0.5
    return m, m - h, m + h


def walk_matrix(arm, ks, rots, field):
    """(walks, seed sets) of 0/1 correctness, walks in a fixed key order (rotation, key)."""
    cols = []
    for k in ks:
        col = []
        for r in rots:
            for row in sorted(load(r, arm, k)["rows"], key=lambda x: x["key"]):
                col.append(float(row[field] == row["true"]))
        cols.append(col)
    return np.asarray(cols, float).T


def boot(M, draws=1000, seed=0):
    rng = np.random.default_rng(seed)
    per = M.mean(axis=1)
    est = 100.0 * per.mean()
    bs = [100.0 * per[rng.integers(0, len(per), len(per))].mean() for _ in range(draws)]
    return est, float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def edges(arm, ks, rots):
    out = {}
    for e in EDGES:
        c = lk = n = 0
        for k in ks:
            for r in rots:
                for row in load(r, arm, k)["rows"]:
                    if row["true"] == e:
                        n += 1
                        c += row["committed"] == e
                        lk += row["lock"] == e
        out[e] = (100.0 * c / max(n, 1), 100.0 * lk / max(n, 1))
    return out


def main() -> int:
    ks = {a: [k for k in KS if complete(a, k)] for a in ARMS}
    res = {"label": LABEL, "seed_sets_complete": ks, "primary": {}, "arms": {}}
    for arm in ARMS:
        if not ks[arm]:
            continue
        a = {"pooled": {}, "per_rotation": {}, "per_seed_set": {k: pooled(arm, k) for k in ks[arm]}}
        for field, name in (("committed", "committed_pct"), ("lock", "lock_pct")):
            a["pooled"][name] = boot(walk_matrix(arm, ks[arm], ROTS, field))
            for r in ROTS:
                a["per_rotation"].setdefault(r, {})[name] = boot(walk_matrix(arm, ks[arm], (r,), field))
        a["pooled"]["edges"] = edges(arm, ks[arm], ROTS)
        for r in ROTS:
            a["per_rotation"][r]["edges"] = edges(arm, ks[arm], (r,))
        res["arms"][arm] = a
    for arm in ("ALL05", "ALL1"):
        pair = [k for k in KS if k in ks.get(arm, []) and k in ks.get("MIX", [])]
        if not pair:
            continue
        d = [pooled(arm, k)["committed_err_pct"] - pooled("MIX", k)["committed_err_pct"] for k in pair]
        dl = [pooled(arm, k)["lock_pct"] - pooled("MIX", k)["lock_pct"] for k in pair]
        m, lo, hi = interval(d)
        verdict = ("better than MIX" if hi < 0 else "worse than MIX" if lo > 0 else "no measurable difference") \
            if len(pair) >= 2 else "not enough seed sets"
        res["primary"][arm] = {"seed_sets": pair, "diff_committed_err_points": d, "mean": m, "ci95": [lo, hi],
                               "verdict": verdict, "lock_diff_points": dl, "lock_mean_ci95": list(interval(dl))}
    v = [p["verdict"] for p in res["primary"].values()]
    res["stride_mix_matters"] = (None if len(v) < 2 or "not enough seed sets" in v
                                 else any(x != "no measurable difference" for x in v))
    with open(J(HERE, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)

    L = [f"# Stride ablation: results ({LABEL})", "",
         "PLAN.md's rule. Committed and lock in percent, averaged over the complete seed sets, with a 95 % bootstrap "
         "interval over walks (1,000 draws, seed 0). Edge lines committed / lock. Rotations: A1+A2 to B1, A1+B1 to "
         "A2, A2+B1 to A1 (120 walks each, 360 pooled); A3 and B2 never read.", "",
         "## Primary: committed-line error, arm minus MIX (points), paired by seed set", "",
         "| arm | seed sets | per seed set | mean [95 % t-interval] | verdict | lock, arm minus MIX |", "|---|---|---|---|---|---|"]
    for arm, p in res["primary"].items():
        L.append(f"| {arm} | {p['seed_sets']} | {', '.join(f'{x:+.2f}' for x in p['diff_committed_err_points'])} | "
                 f"{p['mean']:+.2f} [{p['ci95'][0]:+.2f}, {p['ci95'][1]:+.2f}] | **{p['verdict']}** | "
                 f"{p['lock_mean_ci95'][0]:+.2f} [{p['lock_mean_ci95'][1]:+.2f}, {p['lock_mean_ci95'][2]:+.2f}] |")
    L += ["", f"**Does the stride mix matter?** {res['stride_mix_matters']}", "",
          "## Each arm, pooled and per rotation", "",
          "| arm | split | committed [95 %] | lock [95 %] | E_col1 | E_col5 | E_row1 | E_row5 |",
          "|---|---|---|---|---|---|---|---|"]
    for arm, a in res["arms"].items():
        for split, x in [("pooled", a["pooled"])] + [(r, a["per_rotation"][r]) for r in ROTS]:
            c, lk, e = x["committed_pct"], x["lock_pct"], x["edges"]
            L.append(f"| {arm} | {split} | {c[0]:.2f} [{c[1]:.2f}, {c[2]:.2f}] | {lk[0]:.2f} [{lk[1]:.2f}, {lk[2]:.2f}] | "
                     + " | ".join(f"{e[n][0]:.0f} / {e[n][1]:.0f}" for n in EDGES) + " |")
    L += ["", "## Per seed set, pooled", "", "| arm | seed set | committed | lock |", "|---|---|---|---|"]
    for arm, a in res["arms"].items():
        for k, p in a["per_seed_set"].items():
            L.append(f"| {arm} | {k} | {p['committed_pct']:.2f} | {p['lock_pct']:.2f} |")
    with open(J(HERE, "RESULTS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
