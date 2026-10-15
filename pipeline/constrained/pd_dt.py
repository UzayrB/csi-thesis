"""pd_dt: item 2 of Uzayr's message of 29 September: the 1 s time-step units inside the 0.5 s decoder,
DISCLOSED on the development rotations for the 15:39 model. Nothing is adopted from it.

    python3 -m pipeline.constrained.pd_dt geometry                       # the 0.5 s transit file, once
    python3 -m pipeline.constrained.pd_dt decode --cell d4c_fuse_0102_to_B1 --arm 1
    python3 -m pipeline.constrained.pd_dt report                         # reports/tracking/2026-09-30_time-step-disclosure.md

THE MISMATCH (reports/tracking/2026-09-29_architecture.md, 17.3). The decoder rebuild ran at a 1 s
stride (`rebuild_common.STRIDE_S = 1.0`). `decoder2.py` takes Dt = 1.0 from `common.py`, while
`night_common.shipped_pieces` sets the 0.5 s stride only in `decoder.py`. So in the 0.5 s decoder:
  - late entry reaches v x 1.0 s x (k + 1) and costs 1 nat per 1 s of arc left unexplained;
  - the minimum transit windows are ceil(d / 1.298 m/s / 1 s) (`rb0_preflight/transit_geometry.json`);
  - the transit clock saturates at 8 windows, which the rebuild meant as 8 s.

THE ARMS, each the 15:39 configuration (`rule/FINAL_CONFIG.md`: relgateU + abstain + A2 weight 0.25,
display lock, the A1+A2 pace, the clean reader map), on the three rotations' final-architecture cells:
  0    as shipped;
  1    Uzayr's arm: late-entry reach and cost, and the minimum transit windows, in 0.5 s units
       (`decoder2.DT = 0.5`; `runs/dc2_results/v2/transit_geometry_s05.json`); the clock left at 8;
  1K   a DIAGNOSTIC beside it, not asked for: arm 1 with the clock at 16 windows (8 s). With the clock at 8,
       42 of 144 line-to-line transits need 9 to 11 windows and become impossible. 1K is V2_PREREG's
       base (V2-B), so it is decoded once and shared.
Each decode also records every committed pass's causal exit window, so the report counts how many move.
Writes cells/<rotation>/d3/DT<arm>.<variant>/ (decode.json, scorerlock.json, clean.json, exits.json), the
geometry file, and the report. The rb0 file and every frozen file are only read.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import os
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = os.path.join
RES = J(REPO_ROOT, "runs", "dc2_results")
RB0 = J(REPO_ROOT, "runs", "constrained", "rb0_preflight", "transit_geometry.json")
GEOM = J(RES, "v2", "transit_geometry_s05.json")
VARIANT = "relgateU+abstain+a2w0.25"
ROT_CELLS = {"B1": "d4c_fuse_0102_to_B1", "A2": "d4c_fuse_01B1_to_02", "A1": "d4c_fuse_02B1_to_01"}
ARMS = ("0", "1", "1K")
PACE = ("1.3034113357347858", "0.11254567809955889")
STRIDE = 0.5


def sha(p: str) -> str:
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def write_geometry() -> int:
    """min_windows in 0.5 s windows from rb0's own min_time_s, by rb0's own rounding (ceil)."""
    with open(RB0, encoding="utf-8") as f:
        g = json.load(f)
    for k, v in g.items():                                  # the rule rb0 used, verified on every entry
        assert v["min_windows"] == math.ceil(v["min_time_s"] - 1e-9), (k, v)
    out = {k: {"distance_m": v["distance_m"], "min_time_s": v["min_time_s"],
               "min_windows": int(math.ceil(v["min_time_s"] / STRIDE - 1e-9)), "min_windows_1s": v["min_windows"]}
           for k, v in g.items()}
    os.makedirs(os.path.dirname(GEOM), exist_ok=True)
    if os.path.exists(GEOM):
        with open(GEOM, encoding="utf-8") as f:
            old = json.load(f)
        assert old == out, f"{GEOM} exists and differs"
        print(f"{GEOM} exists and matches", flush=True)
        return 0
    with open(GEOM, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    over = sum(1 for v in out.values() if v["min_windows"] > 8)
    print(f"{len(out)} transits; {over} need more than 8 windows at 0.5 s; source sha {sha(RB0)[:16]}", flush=True)
    return 0


def install(arm: str, exits: dict) -> dict:
    """Patch the decoder pieces for the arm, before pd_decode.inner asks for them; record committed exits."""
    import pipeline.constrained.decoder2 as D2
    import pipeline.constrained.night_arms as NA
    import pipeline.constrained.night_common as NC
    orig = NC.shipped_pieces
    info = {"arm": arm}

    def pieces():
        st, cfg, ne, transit, kind, alpha = orig()
        if arm in ("1", "1K"):
            D2.DT = STRIDE
            with open(GEOM, encoding="utf-8") as f:
                transit = json.load(f)
            if arm == "1K":
                cfg = dataclasses.replace(cfg, clock_max=16)
            D2._LT_CACHE.clear()
        info.update({"decoder2_DT": D2.DT, "clock_max": cfg.clock_max,
                     "transit_file": os.path.relpath(GEOM if arm != "0" else RB0, REPO_ROOT)})
        return st, cfg, ne, transit, kind, alpha
    NC.shipped_pieces = pieces
    ont = NA.night_track

    def night_track(*a, **k):
        rows = ont(*a, **k)
        if not k.get("want_display"):
            for r in rows:
                exits[r["key"]] = {"lo": r["lo"], "exit": r["own_end_i"], "timeout": r["timeout_fired"],
                                   "final": r["final_line"], "true": r["true_line"]}
        return rows
    NA.night_track = night_track
    return info


def decode_inner(cell: str, arm: str) -> int:
    assert os.environ.get("PD_CLEAN_PREFIX") == f"DT{arm}", os.environ.get("PD_CLEAN_PREFIX")
    exits = {}
    info = install(arm, exits)
    from pipeline.constrained import pd_clean
    code = pd_clean.decode_inner(cell, [VARIANT], False)
    if code:
        return code
    dst = J(RES, "cells", cell, "d3", f"DT{arm}.{VARIANT}")
    with open(J(dst, "clean.json"), encoding="utf-8") as f:
        cj = json.load(f)
    assert "copied_from" not in cj, f"{dst}: copied rather than decoded"
    with open(J(dst, "exits.json"), "w", encoding="utf-8") as f:
        json.dump({"arm": info, "exits": exits}, f, indent=1)
    print(f"{cell} DT{arm}: {len(exits)} committed passes, arm {info}", flush=True)
    return 0


def decode_outer(cell: str, arm: str) -> int:
    sys.path.insert(0, REPO_ROOT)
    from pipeline.constrained import pd_cells as PC
    c = PC.cfg(cell, "decode")
    env = dict(PC.env_for(c, "half", "decode"), PYTHONPATH=REPO_ROOT, PD_CLEAN_PREFIX=f"DT{arm}",
               PD_PACE_MEAN=PACE[0], PD_PACE_SD=PACE[1], OMP_NUM_THREADS="1")
    return subprocess.call([sys.executable, "-m", "pipeline.constrained.pd_dt", "decode", "--inner", "--cell", cell,
                            "--arm", arm], cwd=REPO_ROOT, env=env)


# ------------------------------------------------------------------------------------------ the report

def _rows(cell: str, arm: str):
    from pipeline.constrained.pd_report import decode_rows, lock_rows
    base = J(RES, "cells", cell, "d3", f"DT{arm}.{VARIANT}")
    (b,) = list(decode_rows(J(base, "decode.json")))
    com = decode_rows(J(base, "decode.json"))[b]["A"]
    lk = lock_rows(J(base, "scorerlock.json"), "display_lock")[b]["A"]
    with open(J(base, "exits.json"), encoding="utf-8") as f:
        ex = json.load(f)["exits"]
    return com, lk, ex


def _paired(base: dict, arm: dict, what: str, n_boot: int = 1000, seed: int = 0) -> dict:
    """One component (committed or lock), paired per pass, weighted over the rotations as pd_rule."""
    import numpy as np
    from pipeline.constrained.pd_rule import ROTS
    rng = np.random.default_rng(seed)
    w = {nm: wt for nm, _t, _v, wt in ROTS}
    est, boots, per = 0.0, np.zeros(n_boot), {}
    for nm in w:
        b = {r["key"]: int(r["correct"]) for r in base[nm][what]}
        a = {r["key"]: int(r["correct"]) for r in arm[nm][what]}
        ks = sorted(set(b) & set(a))
        assert len(ks) == len(b) == len(a), f"{nm}: base and arm score different passes"
        d = np.array([100.0 * (a[k] - b[k]) for k in ks])
        per[nm] = {"n": len(ks), "base": 100.0 * np.mean([b[k] for k in ks]), "arm": 100.0 * np.mean([a[k] for k in ks]),
                   "diff": float(d.mean()), "passes_gained": int(sum(1 for k in ks if a[k] > b[k])),
                   "passes_lost": int(sum(1 for k in ks if a[k] < b[k]))}
        est += w[nm] * d.mean()
        boots += w[nm] * d[rng.integers(0, len(d), size=(n_boot, len(d)))].mean(axis=1)
    W = sum(w.values())
    lo, hi = np.percentile(boots / W, [2.5, 97.5])
    return {"diff": float(est / W), "ci95": [float(lo), float(hi)], "per_rotation": per}


def report() -> int:
    t = time.strftime("%Y-%m-%d %H:%M")
    R, EX = {}, {}
    for arm in ARMS:
        R[arm], EX[arm] = {}, {}
        for nm, cell in ROT_CELLS.items():
            com, lk, ex = _rows(cell, arm)
            R[arm][nm] = {"committed": com, "lock": lk}
            EX[arm][nm] = ex
    res = {}
    for arm in ("1", "1K"):
        cmp_ = {"committed": _paired(R["0"], R[arm], "committed"), "lock": _paired(R["0"], R[arm], "lock")}
        ex = {}
        for nm in ROT_CELLS:
            a0, a1 = EX["0"][nm], EX[arm][nm]
            evald = {r["key"] for r in R["0"][nm]["committed"]}      # the evaluated passes only (session|stem|pass)
            ks = sorted(set(a0) & set(a1) & evald)
            assert len(ks) == len(evald), f"{nm}: {len(ks)} of {len(evald)} evaluated passes have exits"
            moved = [k for k in ks if a0[k]["exit"] != a1[k]["exit"]]
            ex[nm] = {"passes": len(ks), "exit_changed": len(moved),
                      "exit_shift_windows": sorted(a1[k]["exit"] - a0[k]["exit"] for k in moved),
                      "committed_line_changed": sum(1 for k in ks if a0[k]["final"] != a1[k]["final"]),
                      "timeouts_arm0": sum(1 for k in ks if a0[k]["timeout"]),
                      "timeouts_arm": sum(1 for k in ks if a1[k]["timeout"])}
        res[arm] = {"paired": cmp_, "exits": ex}
    with open(GEOM, encoding="utf-8") as f:
        g = json.load(f)
    over = sorted(k for k, v in g.items() if v["min_windows"] > 8)
    out = {"made": t, "variant": VARIANT, "cells": ROT_CELLS, "results": res,
           "transits_over_8_windows_at_0.5s": over}
    with open(J(RES, "v2", "DT_MISMATCH.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({a: {w: {"diff": v["paired"][w]["diff"], "ci95": v["paired"][w]["ci95"]} for w in ("committed", "lock")}
                      for a, v in res.items()}, indent=1))
    print(json.dumps({a: {nm: {k: x for k, x in v["exits"][nm].items() if k != "exit_shift_windows"} for nm in ROT_CELLS}
                      for a, v in res.items()}, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["geometry", "decode", "report"])
    ap.add_argument("--cell")
    ap.add_argument("--arm", choices=ARMS)
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "geometry":
        return write_geometry()
    if a.cmd == "report":
        sys.path.insert(0, REPO_ROOT)
        return report()
    if a.inner:
        return decode_inner(a.cell, a.arm)
    return decode_outer(a.cell, a.arm)


if __name__ == "__main__":
    sys.exit(main())
