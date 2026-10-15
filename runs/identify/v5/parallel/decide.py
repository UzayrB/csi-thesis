"""The parallel extraction's ship rule (Uzayr, 12 Oct), applied to the confirmation run with the rules fixed before it
(parallel/rules.json): exactness (extract_exact, cpu_exact, the run against the replay), the run's pass (every decision before
its cap; the lag at every press at most 0.5 s; memory by rule (a): the total's slope, each worker flat, no new swap and no
memory pressure) and the median delay better than serial's. Writes the measurements and the decision into rules.json.

    cd <Code> && python3 runs/identify/v5/parallel/decide.py

Development evaluation, all data seen.
"""

import glob
import json
import os
import time

import numpy as np

V5D = os.path.join("runs", "identify", "v5")
PAR = os.path.join(V5D, "parallel")
LOGS = os.path.join(V5D, "logs")


def rows(p: str, n: int) -> list:
    return [l.rstrip("\n").split(",", n - 1) for l in open(p) if l.strip() and not l.startswith("clock")]


def memory(ru: dict) -> dict:
    main = rows(os.path.join(LOGS, "confirm_par_memory.csv"), 4)
    wk = rows(os.path.join(LOGS, "confirm_par_workers.csv"), 5)
    sy = rows(os.path.join(LOGS, "confirm_par_system.csv"), 6)
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
           "workers": {}, "resource_tracker_gb_max": round(max(tracker), 3) if tracker else None}
    for i, (pid, pts) in enumerate(sorted(workers.items(), key=lambda x: int(x[0]))):
        e = np.array([x for x, _g in pts])
        g = np.array([v for _x, v in pts])
        mm = (e - t0) / 60.0
        kk = mm >= start
        fixed = float(g[kk][0])
        sl = float(np.polyfit(mm[kk] / 60.0, g[kk], 1)[0]) if kk.sum() >= 3 else float("nan")
        out["workers"][f"worker {i + 1} (pid {pid})"] = {
            "fixed_size_at_10_min_gb": round(fixed, 3), "max_after_10_min_gb": round(float(g[kk].max()), 3),
            "first_gb": round(float(g[0]), 3), "last_gb": round(float(g[-1]), 3), "slope_gb_per_h_from_minute_10": round(sl, 4),
            "growth_max_fraction": round(float(g[kk].max() / fixed - 1.0), 4),
            "PASSED": bool(g[kk].max() <= fixed * (1.0 + ru["worker_growth_max_fraction"]))}
    su = np.array([float(r[2]) for r in sy])
    so = np.array([float(r[3]) for r in sy])
    pl = np.array([int(r[4]) for r in sy])
    out["system"] = {"samples": int(len(sy)), "swap_used_mb_start": su[0], "swap_used_mb_end": su[-1], "swap_used_mb_max": su.max(),
                     "swapouts_start": int(so[0]), "swapouts_end": int(so[-1]), "pressure_levels_seen": sorted({int(x) for x in pl}),
                     "free_pct_min": min(float(r[5]) for r in sy),
                     "PASSED": bool(su[-1] <= su[0] and so[-1] <= so[0] and set(pl.tolist()) == {1})}
    out["PASSED"] = bool(out["total"]["PASSED"] and all(w["PASSED"] for w in out["workers"].values()) and out["system"]["PASSED"]
                         and len(out["workers"]) == 3)
    return out


if __name__ == "__main__":
    ru = json.load(open(os.path.join(PAR, "rules.json")))
    cp = json.load(open(os.path.join(V5D, "rig_timing_confirm_par.json")))
    ee = json.load(open(os.path.join(PAR, "extract_exact.json")))
    ce = json.load(open(os.path.join(PAR, "cpu_exact.json")))
    zp = np.load(sorted(glob.glob(os.path.join(V5D, "rig", "rig_timing_confirm_par_2*.npz")))[-1])
    zs = np.load(sorted(glob.glob(os.path.join(V5D, "rig", "rig_timing_confirm_lat_2*.npz")))[-1])
    med_p, med_s = float(np.median(zp["delay_after_t0_plus_4_s"])), float(np.median(zs["delay_after_t0_plus_4_s"]))
    mem = memory(ru)
    exact = bool(ee["PASSED"] and ce["PASSED"] and cp["PASSED_exact"])
    cap = bool(cp["all"]["decisions_before_cap"] == cp["all"]["n"] == cp["timed_decisions"] == 299)
    lag = bool(cp["max_lag_at_a_press_s"] <= ru["lag_max_s"])
    better = bool(med_p < med_s)
    keep = exact and cap and lag and mem["PASSED"] and better
    conds = [f"exactness: every window of every B2 walk identical pool against serial ({ee['identical_windows']} of {ee['windows']}), the "
             f"live app on cpu bit-identical to serial and within yesterday's tolerances of the replay, the run equal to the replay "
             f"({cp['equals_harness']['argmax_equal']} of {cp['equals_harness']['of']}, difference {cp['equals_harness']['max_abs_ensemble_diff']:.3g}): "
             f"**{'holds' if exact else 'FAILS'}**",
             f"every decision before its cap: {cp['all']['decisions_before_cap']} of {cp['all']['n']}: **{'holds' if cap else 'FAILS'}**",
             f"the stream's lag at every press at most 0.5 s: largest {cp['max_lag_at_a_press_s']} s: **{'holds' if lag else 'FAILS'}**",
             f"memory, rule (a): the total's slope from minute 10 {mem['total']['slope_gb_per_h_from_minute_10']} GB/h against at most "
             f"{ru['total_slope_max_gb_per_h']} ({'holds' if mem['total']['PASSED'] else 'FAILS'}); each worker flat after minute 10 within "
             f"10 % (" + "; ".join(f"{k}: fixed {v['fixed_size_at_10_min_gb']} GB, largest after {v['max_after_10_min_gb']} GB, "
                                   f"slope {v['slope_gb_per_h_from_minute_10']} GB/h, {'flat' if v['PASSED'] else 'GROWS'}"
                                   for k, v in mem["workers"].items())
             + f"); swap in use {mem['system']['swap_used_mb_start']:.0f} to {mem['system']['swap_used_mb_end']:.0f} MB, Swapouts "
             f"{mem['system']['swapouts_start']} to {mem['system']['swapouts_end']}, pressure levels {mem['system']['pressure_levels_seen']} "
             f"({'holds' if mem['system']['PASSED'] else 'FAILS'}); peak total {mem['total']['peak_gb']} GB: "
             f"**{'holds' if mem['PASSED'] else 'FAILS'}**",
             f"the median delay better than serial's: {med_p:.4f} s against {med_s:.4f} s: **{'holds' if better else 'FAILS'}**"]
    ru["measured"] = {"memory": mem, "median_parallel_s": med_p, "median_serial_s": med_s}
    ru["decision"] = {"decided": time.strftime("%Y-%m-%d %H:%M:%S"),
                      "verdict": "KEPT (parallel extraction ships)" if keep else "REVERTED to serial extraction",
                      "why": ("Every condition of Uzayr's ship rule holds." if keep else
                              "Not every condition of Uzayr's ship rule holds (below), so the app returns to serial extraction and "
                              "last night's figures (1.05 s, 298 of 299) stand."),
                      "conditions": conds}
    json.dump(ru, open(os.path.join(PAR, "rules.json"), "w"), indent=1, default=float)
    print(json.dumps(ru["decision"], indent=1), flush=True)
