"""Score the dwell ablation under PLAN.md's fixed rule; write results.json and RESULTS.md here.

Primary: W+D minus W on pooled committed-line error (A3 + B2, 240 walks), paired by seed set, mean and 95 %
t-interval over the seed sets. Everything else is reported and does not change the verdict.
"""

from __future__ import annotations

import json
import os
import statistics
import sys

from scipy import stats

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
CELLS = {"A3": "fin_A3", "B2": "fin_B2"}
EDGES = ("E_col1", "E_col5", "E_row1", "E_row5")


def load(arm: str, k: int) -> dict | None:
    out = {}
    for room, cell in CELLS.items():
        p = J(HERE, "runs", f"{arm}_k{k}", f"eval_{cell}.json")
        if not os.path.exists(p):
            return None
        out[room] = json.load(open(p))
    a3, b2 = out["A3"], out["B2"]
    n = a3["walks"] + b2["walks"]
    pooled = {m: (a3[m] * a3["walks"] + b2[m] * b2["walks"]) / n
              for m in ("committed_err_pct", "committed_pct", "lock_pct")}
    pooled["frame_err_median_m"] = None  # medians do not pool by weighting; reported per room
    pooled["frame_err_mean_m"] = (a3["frame_err_mean_m"] * a3["frames"] + b2["frame_err_mean_m"] * b2["frames"]) / \
        (a3["frames"] + b2["frames"])
    out["pooled"] = pooled
    return out


def interval(d: list) -> tuple:
    m = statistics.fmean(d)
    if len(d) < 2:
        return m, float("nan"), float("nan")
    h = stats.t.ppf(0.975, len(d) - 1) * statistics.stdev(d) / len(d) ** 0.5
    return m, m - h, m + h


def main() -> int:
    runs = {(arm, k): load(arm, k) for arm in ("W", "WD") for k in range(3)}
    pairs = [k for k in range(3) if runs[("W", k)] and runs[("WD", k)]]
    table = []
    for (arm, k), r in sorted(runs.items()):
        if not r:
            continue
        row = {"arm": arm, "k": k}
        for room in ("A3", "B2"):
            x = r[room]
            row[room] = {"committed_err_pct": x["committed_err_pct"], "lock_pct": x["lock_pct"],
                         "frame_err_median_m": x["frame_err_median_m"], "frame_err_mean_m": x["frame_err_mean_m"],
                         "edges": {e: (x["edges"][e]["committed"], x["edges"][e]["lock"]) for e in EDGES}}
        row["pooled"] = r["pooled"]
        table.append(row)
    diff = [runs[("WD", k)]["pooled"]["committed_err_pct"] - runs[("W", k)]["pooled"]["committed_err_pct"]
            for k in pairs]
    m, lo, hi = interval(diff) if diff else (float("nan"),) * 3
    verdict = ("incomplete" if len(pairs) < 3 else "dwells help" if hi < 0 else "dwells hurt" if lo > 0
               else "no measurable gain")
    second = {}
    for key, get in (("lock_pct_pooled", lambda r: r["pooled"]["lock_pct"]),
                     ("committed_err_A3", lambda r: r["A3"]["committed_err_pct"]),
                     ("committed_err_B2", lambda r: r["B2"]["committed_err_pct"]),
                     ("frame_err_mean_pooled_m", lambda r: r["pooled"]["frame_err_mean_m"])):
        d = [get(runs[("WD", k)]) - get(runs[("W", k)]) for k in pairs]
        second[key] = dict(zip(("mean", "lo", "hi"), interval(d))) if d else None
    res = {"pairs": pairs, "primary": {"metric": "pooled committed-line error, WD minus W, percentage points",
                                       "per_seed": diff, "mean": m, "ci95": [lo, hi], "verdict": verdict},
           "secondary": second, "table": table}
    with open(J(HERE, "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    write_md(res)
    print(json.dumps(res["primary"], indent=1))
    return 0


def write_md(res: dict) -> None:
    """RESULTS.md: per-seed tables, the paired differences and the verdict. Development evaluation of a further
    look at A3 and B2; three seed sets (PLAN addendum of 20:12)."""
    rows = res["table"]
    L = ["# Do the static dwells help the final walking tracker? Results", "",
         "Arms: W, the final tracker's recipe (walking windows of A1, A2, B1); W+D, the same plus every A1 and A2 dwell "
         "window. Tested on A3 and B2 (never trained on), semi-constrained mode, the shipped decode (equal to the live "
         "app). Three seed sets (PLAN.md addendum, 6 October 20:12). W seed set 0 is byte-identical to the shipped "
         "tracker and reproduces its published A3 and B2 figures exactly.", "",
         "## Per seed set (committed / lock, %; per-frame dot error median m)", "",
         "| arm | seed set | A3 committed | A3 lock | A3 frame | B2 committed | B2 lock | B2 frame | pooled committed | pooled lock |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        a, b, p = r["A3"], r["B2"], r["pooled"]
        L.append(f"| {r['arm'].replace('WD', 'W+D')} | {r['k']} | {100 - a['committed_err_pct']:.2f} | {a['lock_pct']:.2f} | "
                 f"{a['frame_err_median_m']:.3f} | {100 - b['committed_err_pct']:.2f} | {b['lock_pct']:.2f} | "
                 f"{b['frame_err_median_m']:.3f} | {p['committed_pct']:.2f} | {p['lock_pct']:.2f} |")
    L += ["", "## Edge lines (committed / lock, %, 6 walks each)", "",
          "| arm | seed set | A3 E_col1 | A3 E_col5 | A3 E_row1 | A3 E_row5 | B2 E_col1 | B2 E_col5 | B2 E_row1 | B2 E_row5 |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        cells = [f"{r[room]['edges'][e][0]:.0f} / {r[room]['edges'][e][1]:.0f}" for room in ("A3", "B2") for e in EDGES]
        L.append(f"| {r['arm'].replace('WD', 'W+D')} | {r['k']} | " + " | ".join(cells) + " |")
    for arm in ("W", "WD"):
        xs = [r for r in rows if r["arm"] == arm]
        if len(xs) > 1:
            c = [r["pooled"]["committed_pct"] for r in xs]
            k = [r["pooled"]["lock_pct"] for r in xs]
            L.append("")
            L.append(f"**{arm.replace('WD', 'W+D')} mean +- SD over {len(xs)} seed sets:** pooled committed "
                     f"{statistics.fmean(c):.2f} +- {statistics.stdev(c):.2f}, pooled lock "
                     f"{statistics.fmean(k):.2f} +- {statistics.stdev(k):.2f}.")
    pr = res["primary"]
    L += ["", "## Paired differences, W+D minus W (percentage points; 95 % t-interval over seed sets)", "",
          f"- **Primary, pooled committed-line error:** per seed set {', '.join(f'{d:+.2f}' for d in pr['per_seed'])}; "
          f"mean {pr['mean']:+.2f} [{pr['ci95'][0]:+.2f}, {pr['ci95'][1]:+.2f}].", ""]
    for key, v in res["secondary"].items():
        if v:
            L.append(f"- {key}: mean {v['mean']:+.2f} [{v['lo']:+.2f}, {v['hi']:+.2f}]")
    L += ["", f"## Verdict under the rule fixed in PLAN.md: **{pr['verdict']}**", ""]
    with open(J(HERE, "RESULTS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


if __name__ == "__main__":
    sys.exit(main())
