"""The staged extraction's pass rules for its confirmation run (Uzayr, 12 Oct; QUEUE_STAGED.md, step C), applied with the rules
fixed before it (staged/rules_staged.json): exactness against the replay on mps (299 of 299, difference 0), every decision
before its cap, the lag at every press at most 0.5 s, memory as parallel/rules2.json unchanged ((1) the total's slope from
minute 10 at most 2.0625 GB/h; (2) each of the 4 workers' slope from minute 10 at most 10 MB/h and none above 150 MB; (3) no
swap growth, pressure never critical, level 2 only while free memory is at or above 30 %), and WORTH IT: the median decision
delay after t0 + 4.0 s at most 0.60 s. Writes the measurements and the decision into rules_staged.json. decide2.py's
statements, with the tag, the folder, the worker count and the median rule changed.

    cd <Code> && python3 runs/identify/v5/staged/decide_staged.py

Development evaluation, all data seen.
"""

import glob
import json
import os
import time

import numpy as np

V5D = os.path.join("runs", "identify", "v5")
PAR = os.path.join(V5D, "staged")
LOGS = os.path.join(V5D, "logs")
TAG = "confirm_staged"
WORKERS = 4


def rows(p: str, n: int) -> list:
    return [l.rstrip("\n").split(",", n - 1) for l in open(p) if l.strip() and not l.startswith("clock")]


def memory(ru: dict) -> dict:
    main = rows(os.path.join(LOGS, f"{TAG}_memory.csv"), 4)
    wk = rows(os.path.join(LOGS, f"{TAG}_workers.csv"), 5)
    sy = rows(os.path.join(LOGS, f"{TAG}_system.csv"), 6)
    t0 = float(main[0][1])
    start = ru["start_minute"]
    workers, tracker = {}, []
    for _c, e, p, g, cmd in wk:
        (tracker.append(float(g)) if "resource_tracker" in cmd else workers.setdefault(p, []).append((float(e), float(g))))
    tot = {e: float(g) for _c, e, g, _f in main}
    for pid, pts in workers.items():
        for e, g in pts:
            if str(int(e)) in tot:
                tot[str(int(e))] += g
    te = np.array(sorted(float(e) for e in tot))
    tv = np.array([tot[str(int(e))] for e in te])
    m = (te - t0) / 60.0
    k = m >= start
    slope = float(np.polyfit(m[k] / 60.0, tv[k], 1)[0])
    out = {"total": {"samples": int(len(tv)), "peak_gb": round(float(tv.max()), 3), "at_10_min_gb": round(float(tv[k][0]), 3),
                     "last_gb": round(float(tv[-1]), 3), "slope_gb_per_h_from_minute_10": round(slope, 4),
                     "limit_gb_per_h": ru["total_slope_max_gb_per_h"], "PASSED": bool(slope <= ru["total_slope_max_gb_per_h"])},
           "workers": {}, "resource_tracker_mb_max": round(1024 * max(tracker), 1) if tracker else None}
    for i, (pid, pts) in enumerate(sorted(workers.items(), key=lambda x: int(x[0]))):
        e = np.array([x for x, _g in pts])
        g = 1024.0 * np.array([v for _x, v in pts])                       # top's own MB
        mm = (e - t0) / 60.0
        kk = mm >= start
        sl = float(np.polyfit(mm[kk] / 60.0, g[kk], 1)[0]) if kk.sum() >= 3 else float("nan")
        out["workers"][f"worker {i + 1} (pid {pid})"] = {
            "fixed_size_at_10_min_mb": round(float(g[kk][0]), 1), "max_mb": round(float(g.max()), 1), "last_mb": round(float(g[-1]), 1),
            "samples": int(len(g)), "slope_mb_per_h_from_minute_10": round(sl, 2),
            "PASSED": bool(np.isfinite(sl) and sl <= ru["worker_slope_max_mb_per_h"] and g.max() <= ru["worker_max_mb"])}
    su = np.array([float(r[2]) for r in sy])
    so = np.array([float(r[3]) for r in sy])
    pl = np.array([int(r[4]) for r in sy])
    fr = np.array([float(r[5]) for r in sy])
    lv2 = [(r[0], int(r[4]), float(r[5])) for r in sy if int(r[4]) != 1]
    out["system"] = {"samples": int(len(sy)), "swap_used_mb_start": float(su[0]), "swap_used_mb_max": float(su.max()),
                     "swap_used_mb_end": float(su[-1]), "swapouts_start": int(so[0]), "swapouts_end": int(so[-1]),
                     "pressure_levels_seen": sorted({int(x) for x in pl}), "samples_not_normal": lv2, "free_pct_min": float(fr.min()),
                     "PASSED": bool(su.max() <= su[0] and so[-1] == so[0] and ru["pressure_critical_level"] not in set(pl.tolist())
                                    and all(f >= ru["pressure_level_2_min_free_pct"] for _c, lv, f in lv2 if lv == 2)
                                    and all(lv in (1, 2) for _c, lv, _f in lv2))}
    out["PASSED"] = bool(out["total"]["PASSED"] and len(out["workers"]) == WORKERS and all(w["PASSED"] for w in out["workers"].values())
                         and out["system"]["PASSED"])
    return out


if __name__ == "__main__":
    ru = json.load(open(os.path.join(PAR, "rules_staged.json")))
    cp = json.load(open(os.path.join(V5D, f"rig_timing_{TAG}.json")))
    zp = np.load(sorted(glob.glob(os.path.join(V5D, "rig", f"rig_timing_{TAG}_2*.npz")))[-1])
    med = float(np.median(zp["delay_after_t0_plus_4_s"]))
    mem = memory(ru)
    exact = bool(cp["PASSED_exact"])
    cap = bool(cp["all"]["decisions_before_cap"] == cp["all"]["n"] == cp["timed_decisions"] == 299)
    lag = bool(cp["max_lag_at_a_press_s"] <= ru["lag_max_s"])
    better = bool(med <= ru["median_at_most_s"])
    keep = exact and cap and lag and mem["PASSED"] and better
    s_ = mem["system"]
    conds = [f"exactness on the GPU: {cp['equals_harness']['argmax_equal']} of {cp['equals_harness']['of']}, difference "
             f"{cp['equals_harness']['max_abs_ensemble_diff']:.3g}: **{'holds' if exact else 'FAILS'}**",
             f"every decision before its cap: {cp['all']['decisions_before_cap']} of {cp['all']['n']}: **{'holds' if cap else 'FAILS'}**",
             f"the stream's lag at every press at most 0.5 s: largest {cp['max_lag_at_a_press_s']} s: **{'holds' if lag else 'FAILS'}**",
             f"memory (1), the total: slope from minute 10 {mem['total']['slope_gb_per_h_from_minute_10']} GB/h against at most "
             f"{ru['total_slope_max_gb_per_h']}, peak {mem['total']['peak_gb']} GB: **{'holds' if mem['total']['PASSED'] else 'FAILS'}**",
             "memory (2), the workers by trend: " + "; ".join(
                 f"{k_}: fixed {v['fixed_size_at_10_min_mb']} MB at minute 10, slope {v['slope_mb_per_h_from_minute_10']} MB/h, "
                 f"largest {v['max_mb']} MB ({'holds' if v['PASSED'] else 'FAILS'})" for k_, v in mem["workers"].items())
             + f": **{'holds' if all(v['PASSED'] for v in mem['workers'].values()) and len(mem['workers']) == WORKERS else 'FAILS'}**",
             f"memory (3), swap and pressure: swap in use {s_['swap_used_mb_start']:.0f} MB at the start, at most {s_['swap_used_mb_max']:.0f}, "
             f"{s_['swap_used_mb_end']:.0f} at the end; Swapouts {s_['swapouts_start']} to {s_['swapouts_end']}; pressure levels "
             f"{s_['pressure_levels_seen']}" + (f", not normal at {len(s_['samples_not_normal'])} samples (" + ", ".join(
                 f"{c} level {lv}, free {f:.0f} %" for c, lv, f in s_["samples_not_normal"]) + ")" if s_["samples_not_normal"] else "")
             + f"; free memory at least {s_['free_pct_min']:.0f} %: **{'holds' if s_['PASSED'] else 'FAILS'}**",
             f"worth it, the median delay after t0 + 4.0 s at most {ru['median_at_most_s']} s: {med:.4f} s: **{'holds' if better else 'FAILS'}**"]
    ru["measured"] = {"memory": mem, "median_s": med}
    ru["decision"] = {"decided": time.strftime("%Y-%m-%d %H:%M:%S"),
                      "verdict": "KEPT (staged extraction ships; this run's figures)" if keep else "REVERT to the shipped pool (and stop)",
                      "why": ("Every condition of Uzayr's pass rules holds." if keep else
                              "Not every condition of Uzayr's pass rules holds (below), so the app returns to the shipped "
                              "one-job-per-window pool, its figures (0.714 s, 299 of 299) stand, and the work stops (no "
                              "redefinition, no re-run)."),
                      "conditions": conds}
    json.dump(ru, open(os.path.join(PAR, "rules_staged.json"), "w"), indent=1, default=float)
    print(json.dumps(ru["decision"], indent=1), flush=True)
