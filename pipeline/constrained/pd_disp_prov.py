"""pd_disp_prov: Part D, the display's provenance, run exactly as rule/DISPLAY_PREREG.md (hashed 09:15, ad7eeb5a...).

    python3 -m pipeline.constrained.pd_disp_prov sweep        # the spread grid on the three rotations
    python3 -m pipeline.constrained.pd_disp_prov cap          # cap 0.80 against 0.8205: every lock and drawn path
    python3 -m pipeline.constrained.pd_disp_prov app_cap      # the app at both caps on A1+A2 -> B1: every output
    python3 -m pipeline.constrained.pd_disp_prov report       # runs/dc2_results/display/SPREAD_SWEEP.json

The frozen model's rotation form: the d4c_fuse cells, relgateU + abstain + A2 weight 0.25, the frozen A1+A2 pace,
the clean reader map, decoded by pd_clean (the offline decoder). It is used only on rotations where the app's
legacy-mode replay gate is EXACT against the offline DT0 decode (runs/live/final/gate_<cell>.json).
Nothing is adopted: the 15:39 configuration is unchanged.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = os.path.join
RES = J(REPO_ROOT, "runs", "dc2_results")
OUT = J(RES, "display")
ROT = {"B1": ("d4c_fuse_0102_to_B1", 2.0), "A2": ("d4c_fuse_01B1_to_02", 1.0), "A1": ("d4c_fuse_02B1_to_01", 1.0)}
V = "relgateU+abstain+a2w0.25"
GRID = (2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0)
CAPS = (0.80, 0.8205)
PACE = ("1.3034113357347858", "0.11254567809955889")
PREREG = J(RES, "rule", "DISPLAY_PREREG.md")


def prereg_ok():
    import hashlib
    want = open(PREREG + ".sha256", encoding="utf-8").read().split()[0]
    if hashlib.sha256(open(PREREG, "rb").read()).hexdigest() != want:
        raise SystemExit("REFUSED: DISPLAY_PREREG.md changed")


def gate_ok(cell: str) -> bool:
    p = J(REPO_ROOT, "runs", "live", "final", f"gate_{cell}.json")
    if not os.path.exists(p):
        return False
    g = json.load(open(p, encoding="utf-8"))
    return bool(g.get("EXACT")) and g.get("mode", "legacy") == "legacy" and "DT0." in g.get("ref", "")


def _env(cell: str, prefix: str) -> dict:
    sys.path.insert(0, REPO_ROOT)
    from pipeline.constrained import pd_cells as PC
    return dict(PC.env_for(PC.cfg(cell, "decode"), "half", "decode"), PYTHONPATH=REPO_ROOT, OMP_NUM_THREADS="1",
                PD_CLEAN_PREFIX=prefix, PD_PACE_MEAN=PACE[0], PD_PACE_SD=PACE[1])


def sweep() -> int:
    prereg_ok()
    for nm, (cell, _w) in ROT.items():
        if not gate_ok(cell):
            raise SystemExit(f"REFUSED: the app's legacy gate on {cell} is not EXACT against DT0; sweep by app replays instead")
        todo = [f"{V}+sd{x}" for x in GRID if not os.path.exists(J(RES, "cells", cell, "d3", f"SD.{V}+sd{x}", "decode.json"))]
        if todo:
            code = subprocess.call([sys.executable, "-m", "pipeline.constrained.pd_clean", "decode", "--inner", "--cell", cell,
                                    "--variants", *todo], cwd=REPO_ROOT, env=_env(cell, "SD"))
            if code:
                raise SystemExit(f"sweep failed on {cell}")
    return 0


def cap_inner(cell: str, cap: float, out: str) -> int:
    """The offline decode at one cap, every pass's lock line and drawn path (the free path before the lock step, the
    locked path from it) captured from night_track's own display rows."""
    import pipeline.constrained.dc2_scorerlock as S
    import pipeline.constrained.night_arms as NA
    S.CAP = float(cap)
    cap_rows = {}
    ont = NA.night_track
    norm = lambda x: json.loads(json.dumps(x, default=float))                    # noqa: E731

    def nt(*a, **k):
        rows = ont(*a, **k)
        if k.get("want_display"):
            rec = a[1]
            for r in rows:
                Lk = (r.get("display_locked") or {}).get("2|2.0")
                if Lk:
                    # the whole drawn path, every field: the free path (before the lock) and the locked one
                    cap_rows[r["key"]] = {
                        "lock": Lk["lock_line"], "lock_step": int(Lk["lock_step"]), "locked_path": norm(Lk["path"]),
                        "free_path": norm((r.get("display_paths") or {}).get("2") or [])}
        return rows
    NA.night_track = nt
    from pipeline.constrained import pd_clean
    code = pd_clean.decode_inner(cell, [V], False)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"cell": cell, "cap": cap, "passes": cap_rows}, f)
    return code


def cap() -> int:
    prereg_ok()
    os.makedirs(OUT, exist_ok=True)
    res = {}
    for nm, (cell, _w) in ROT.items():
        files = {}
        for c_ in CAPS:
            out = J(OUT, f"cap_{cell}_{c_}.json")
            if not os.path.exists(out):
                code = subprocess.call([sys.executable, "-m", "pipeline.constrained.pd_disp_prov", "cap_inner", "--cell", cell,
                                        "--cap", str(c_), "--out", out], cwd=REPO_ROOT, env=_env(cell, f"CAP{c_}"))
                if code:
                    raise SystemExit(f"cap run failed on {cell} at {c_}")
            files[c_] = json.load(open(out, encoding="utf-8"))["passes"]
        a, b = files[CAPS[0]], files[CAPS[1]]
        ks = sorted(set(a) | set(b))
        res[nm] = {"passes": len(ks), "locks_equal": sum(a.get(k, {}).get("lock") == b.get(k, {}).get("lock") for k in ks),
                   "paths_equal": sum(a.get(k) == b.get(k) for k in ks)}
    res["BIT_IDENTICAL"] = all(v["locks_equal"] == v["passes"] == v["paths_equal"] for k, v in res.items() if isinstance(v, dict))
    with open(J(OUT, "CAP_EQUIVALENCE.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res, indent=1))
    return 0 if res["BIT_IDENTICAL"] else 1


def cap_code() -> int:
    """(a) from the code: the three kinds of matrix the cap reaches, built at caps 0.7499, 0.80, 0.8205 and 0.8212
    (the display decode's `transition_matrix2`, the chains' `transition_matrix`, the switching scorer's), compared
    bit for bit."""
    prereg_ok()
    import dataclasses
    import pipeline.constrained.decoder as D
    import pipeline.constrained.decoder2 as D2
    from pipeline.constrained import switching as SW
    from pipeline.constrained.night_common import shipped_pieces
    st, cfg, _ne, transit, _kind, _alpha = shipped_pieces()
    cfg_disp, cfg_dec = dataclasses.replace(cfg, sd_scale=4.5), dataclasses.replace(cfg, sd_scale=1.0)
    mats = {}
    for c_ in (0.7499, 0.80, 0.8205, 0.8212):
        D.MAX_ADVANCE_M = c_
        D2._LT_CACHE.clear()
        sc = SW.Scorer(st, cfg_dec, transit)
        arrs = {f"scorer.{k}": np.asarray(v) for k, v in vars(sc).items() if isinstance(v, np.ndarray)}
        mats[c_] = {"display.transition_matrix2": np.asarray(D2.transition_matrix2(st, cfg_disp, transit)),
                    "chains.transition_matrix": np.asarray(D.transition_matrix(st, "tight", with_null=False)), **arrs}
        D.MAX_ADVANCE_M = None
        D2._LT_CACHE.clear()
    same = lambda a, b: {k: bool(np.array_equal(mats[a][k], mats[b][k])) for k in mats[a]}      # noqa: E731
    out = {"matrices": sorted(mats[0.80]), "0.80_vs_0.8205": same(0.80, 0.8205), "0.80_vs_0.7499": same(0.80, 0.7499),
           "0.80_vs_0.8212": same(0.80, 0.8212)}
    out["IDENTICAL_AT_0.80_AND_0.8205"] = all(out["0.80_vs_0.8205"].values())
    out["DIFFER_OUTSIDE_THE_RANGE"] = (not all(out["0.80_vs_0.7499"].values())) and (not all(out["0.80_vs_0.8212"].values()))
    os.makedirs(OUT, exist_ok=True)
    with open(J(OUT, "CAP_MATRICES.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))
    return 0 if out["IDENTICAL_AT_0.80_AND_0.8205"] else 1


def app_cap_inner(cap: float) -> int:
    """The app, semi mode, causal clock, on the A1+A2 -> B1 rotation, with the display cap set to `cap`: every
    output logged by the replay harness (dots, locks, committed lines, switches) under display/app_cap_<cap>/."""
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    import pipeline.live.app_replay as AR
    import pipeline.live.display as DSP
    DSP.DISPLAY_CAP_M_PER_WINDOW = float(cap)
    AR.MODEL_SETS["rotB1"] = {"B1": ROT["B1"][0], "end_head": "final"}
    AR.OUT = J(OUT, f"app_cap_{cap}")
    from pipeline.live.final_model import _components
    from pipeline.constrained.recordings import session_recordings
    comp = _components(ROT["B1"][0], V)
    cal = comp[0].cal_stems("B1")
    for _s, stem in session_recordings("B1"):
        if stem not in cal:
            AR.replay_inner("rotB1", "B1", stem, "start", "causal", False, components=comp)
    with open(J(AR.OUT, "DONE"), "w", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S"))
    return 0


def app_cap() -> int:
    """Both caps through the app on B1, then every logged output compared line for line."""
    prereg_ok()
    import hashlib
    from pipeline.live.final_model import _env
    for c_ in CAPS:
        d = J(OUT, f"app_cap_{c_}", "rotB1", "semi_causal")
        if os.path.isdir(d) and not os.path.exists(J(OUT, f"app_cap_{c_}", "DONE")):
            raise SystemExit(f"REFUSED: {d} exists without DONE: a run is incomplete or still running elsewhere")
        if not os.path.isdir(d):
            code = subprocess.call([sys.executable, "-m", "pipeline.constrained.pd_disp_prov", "app_cap_inner", "--cap", str(c_)],
                                   cwd=REPO_ROOT, env=dict(_env(ROT["B1"][0]), OMP_NUM_THREADS="1"))
            if code:
                raise SystemExit(f"app cap run failed at {c_}")
    a, b = (J(OUT, f"app_cap_{c_}", "rotB1", "semi_causal") for c_ in CAPS)
    res = {"recordings": {}}
    for n in sorted(x for x in os.listdir(a) if x.endswith(".jsonl")):
        ra = [json.loads(ln) for ln in open(J(a, n), encoding="utf-8")]
        rb = [json.loads(ln) for ln in open(J(b, n), encoding="utf-8")]
        dots = lambda rr: [r for r in rr if r["kind"] == "dot"]                  # noqa: E731
        res["recordings"][n] = {"rows": [len(ra), len(rb)], "dots": [len(dots(ra)), len(dots(rb))],
                                "every_row_equal": ra == rb,
                                "sha256": [hashlib.sha256(open(J(x, n), "rb").read()).hexdigest()[:16] for x in (a, b)]}
    res["BIT_IDENTICAL"] = all(v["every_row_equal"] for v in res["recordings"].values())
    with open(J(OUT, "APP_CAP_EQUIVALENCE.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res, indent=1))
    return 0 if res["BIT_IDENTICAL"] else 1


def report() -> int:
    prereg_ok()
    sys.path.insert(0, REPO_ROOT)
    from pipeline.constrained.pd_report import lock_rows
    rows = {}
    for x in GRID:
        rows[x] = {}
        for nm, (cell, _w) in ROT.items():
            d = J(RES, "cells", cell, "d3", f"SD.{V}+sd{x}")
            (node,) = lock_rows(J(d, "scorerlock.json"), "display_lock").values()
            rows[x][nm] = {r["key"]: int(r["correct"]) for r in node["A"]}
    W = {nm: w for nm, (_c, w) in ROT.items()}
    curve = {x: sum(W[nm] * 100.0 * np.mean(list(rows[x][nm].values())) for nm in ROT) / sum(W.values()) for x in GRID}
    best = max(GRID, key=lambda x: (curve[x], -x))          # exact ties to the smallest spread
    rng = np.random.default_rng(0)
    est, boots = 0.0, np.zeros(1000)
    for nm in ROT:
        ks = sorted(rows[4.5][nm])
        dlt = np.array([100.0 * (rows[4.5][nm][k] - rows[best][nm][k]) for k in ks])
        est += W[nm] * dlt.mean()
        boots += W[nm] * dlt[rng.integers(0, len(dlt), size=(1000, len(dlt)))].mean(axis=1)
    Wt = sum(W.values())
    lo, hi = np.percentile(boots / Wt, [2.5, 97.5])
    out = {"curve_rotation_weighted_display_lock_pct": {str(x): round(v, 4) for x, v in curve.items()},
           "per_rotation": {str(x): {nm: round(100.0 * np.mean(list(rows[x][nm].values())), 2) for nm in ROT} for x in GRID},
           "argmax": best, "argmax_is_4_5": best == 4.5,
           "paired_4_5_minus_argmax": {"points": float(est / Wt), "ci95": [float(lo), float(hi)]},
           "at": time.strftime("%Y-%m-%d %H:%M")}
    with open(J(OUT, "SPREAD_SWEEP.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sweep", "cap", "cap_inner", "cap_code", "app_cap", "app_cap_inner", "report"])
    ap.add_argument("--cell")
    ap.add_argument("--cap", type=float)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.cmd == "cap_inner":
        return cap_inner(a.cell, a.cap, a.out)
    if a.cmd == "app_cap_inner":
        return app_cap_inner(a.cap)
    return {"sweep": sweep, "cap": cap, "cap_code": cap_code, "app_cap": app_cap, "report": report}[a.cmd]()


if __name__ == "__main__":
    sys.exit(main())
