"""Stage 1's offline gates (PREREG_DOT.md section 4, stage 1; POA_DOT.md E4): s2_display's (i) dwell drift and (iii)
substitution, on the rotations.

    python3 runs/a3_clean_2026-10-08/gates.py dwell                          # A1 and A2 rotations (B1 has no grid dwells)
    python3 runs/a3_clean_2026-10-08/gates.py subst --rot A2 --cell f05r_01B1_to_02 --register <reg.py> \
        --sd 2.5 --entry soft --window 1.0

(i) DWELL DRIFT, s2's `dwell_drift` (copied below unchanged): the mean speed of each head's posterior-mean estimate over
the static grid dwells of the rotation's test session. centre_labelled is the rotation cell's half head (the "centre
head" s2 used; unchanged by the 0.5 s ship), DISP_END the rotation's held-out display head (heads.py infer). DISP_END
passes when its drift is at most 1.25 times centre_labelled's, averaged over the A1 and A2 rotations as s2 averaged.

(iii) SUBSTITUTION, s2's `substitution_on_arc` (copied below unchanged): the rotation's lock decode is run as
`pd_decode.inner` runs it (lock_side.py's process: the clean reader map, the frozen A1+A2 pace, readers fitted fresh),
with the lock side held at the given spread, entry and window. Each of its display decodes is then run again with four
display emissions: the recording's own pooled emission and display-head emission, and the NEXT recording's (s2's
substitution partner), every one at the stage's prior (flatten 0.50). A step counts as changed when the substituted
path's arc moves by more than 0.25 m; the ceiling is the share of the same steps whose two truths differ by more than
that. Per rotation the observed and ceiling shares are weighted (2 B1 + A2 + A1) / 4; DISP_END passes when its ratio is
no worse than centre_labelled's (s2's rule as revised before its run).

Writes only under gates/ in this folder.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

import numpy as np

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUT = J(HERE, "gates")
SUB_TOL_M = 0.25
PRIOR_F = 0.50
VARIANT = "relgateU+abstain+a2w0.25"


# ------------------------------------------------------------------------------------------ s2_display's code, copied

def dwell_drift(session: str, post_path: str) -> dict:
    """s2_display.dwell_drift, unchanged."""
    from pipeline.constrained.artefacts import read_full_posteriors
    from pipeline.constrained.grid import centres
    cc = centres(25)
    spd, res, n_runs, n_win = [], [], 0, 0
    for stem, b in sorted(read_full_posteriors(post_path).items()):
        mode = np.asarray(b["mode"]).astype(str)
        t = np.asarray(b["t0"], float)
        xy = np.asarray(b["xy"], float)
        prob = np.asarray(b["prob"], float)
        est = prob @ cc
        g = np.flatnonzero(mode == "grid")
        if not len(g):
            continue
        runs, i = [], 0
        while i < len(g):
            j = i
            while (j + 1 < len(g) and g[j + 1] == g[j] + 1
                   and np.allclose(xy[g[j + 1]], xy[g[i]], equal_nan=True)):
                j += 1
            if j - i >= 3:
                runs.append(g[i:j + 1])
            i = j + 1
        for r in runs:
            d = np.diff(est[r], axis=0)
            dt = np.diff(t[r])
            ok = dt > 1e-6
            if ok.sum() < 3:
                continue
            step = np.linalg.norm(d[ok], axis=1)
            spd += list(step / dt[ok])
            u = d[ok][step > 1e-9] / step[step > 1e-9][:, None]
            if len(u) >= 3:
                res.append(float(np.linalg.norm(u.mean(axis=0))))
            n_runs += 1
            n_win += len(r)
    return {"session": session, "n_dwell_runs": n_runs, "n_windows": n_win,
            "mean_drift_m_per_s": float(np.mean(spd)) if spd else None,
            "median_drift_m_per_s": float(np.median(spd)) if spd else None,
            "direction_consistency": float(np.mean(res)) if res else None}


def arc_of_xy(st, line: str, xy) -> float:
    """s2_display.arc_of_xy, unchanged: the arc of the nearest state on the chain."""
    a, b = st.slice_of[line]
    p = np.asarray(st.xy)[a:b]
    d = np.linalg.norm(p - np.asarray(xy, float)[None, :], axis=1)
    return float(np.asarray(st.s_of)[a + int(np.argmin(d))])


def substitution_on_arc(path_own, path_sub, st, line, rec, sub_rec):
    """s2_display.substitution_on_arc, unchanged."""
    s_of = np.asarray(st.s_of, float)
    xy_o, xy_s = np.asarray(rec.xy, float), np.asarray(sub_rec.xy, float)
    n_sub = len(sub_rec)
    obs, ceil = [], []
    for a, b in zip(path_own, path_sub):
        w = int(a["window"])
        to_, ts_ = xy_o[w] if w < len(xy_o) else None, xy_s[w % n_sub]
        if to_ is None or not np.isfinite(to_).all() or not np.isfinite(ts_).all():
            continue
        obs.append(bool(abs(s_of[int(a["state"])] - s_of[int(b["state"])]) > SUB_TOL_M))
        ceil.append(bool(abs(arc_of_xy(st, line, to_) - arc_of_xy(st, line, ts_)) > SUB_TOL_M))
    return obs, ceil


# ------------------------------------------------------------------------------------------ (i) dwell drift

def dwell() -> int:
    sys.path.insert(0, REPO)
    sys.path.insert(0, HERE)
    import heads as H
    from pipeline.constrained import pd_cells as PC
    out = J(OUT, "dwell.json")
    if os.path.exists(out):
        raise SystemExit(f"REFUSED: {out} exists")
    per = {}
    for rot in ("A2", "A1"):
        c = PC.cfg(H.ROT_CELL[rot], "decode")
        centre_p = J(c["tree"]("half"), "posteriors", f"{c['heads_tag']}_g25_e24_s0_full.npz")
        end_p = H.posterior_file(rot)
        for p in (centre_p, end_p):
            if not os.path.exists(p):
                raise SystemExit(f"REFUSED: {p} is missing (run heads.py infer first)")
        per[rot] = {"centre_labelled": dwell_drift(c["test"], centre_p), "DISP_END": dwell_drift(c["test"], end_p),
                    "files": [os.path.relpath(centre_p, REPO), os.path.relpath(end_p, REPO)]}

    def avg(which):
        v = [d[which]["mean_drift_m_per_s"] for d in per.values() if d[which]["mean_drift_m_per_s"] is not None]
        return float(np.mean(v)) if len(v) == len(per) else None
    c_, d_ = avg("centre_labelled"), avg("DISP_END")
    res = {"per_rotation": per, "centre_labelled_mean_drift": c_, "DISP_END_mean_drift": d_,
           "ratio_to_centre": (d_ / c_) if (c_ and d_) else None, "rule": "DISP_END passes at a ratio of at most 1.25",
           "B1": "not measured: no grid dwells in Room B (disclosed in PREREG_DOT)"}
    res["PASSES"] = {"centre_labelled": True, "DISP_END": bool(res["ratio_to_centre"] is not None
                                                                and res["ratio_to_centre"] <= 1.25)}
    res["at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs(OUT, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: res[k] for k in ("ratio_to_centre", "PASSES")}), flush=True)
    return 0


# ------------------------------------------------------------------------------------------ (iii) substitution

def end_emissions(rot: str, st, alpha: float) -> dict:
    """{stem: emission} of the rotation's held-out display head, scaled by its own training marginal (FinalEndHead's)."""
    sys.path.insert(0, HERE)
    import heads as H
    from pipeline.constrained.artefacts import read_full_posteriors
    from pipeline.constrained.emissions import cell_marginal, scaled_cell_emission
    tj = (J(REPO, "runs", "dc2_results", "dispend_zeroshot", "train.json") if rot == "B1" else H.train_json(rot))
    with open(tj, encoding="utf-8") as f:
        marg = cell_marginal(np.asarray(json.load(f)["marginal_xy"], float), H.N_CELLS)
    return {stem: scaled_cell_emission(b["prob"].astype(np.float32).astype(float), st.xy, H.N_CELLS, marg, alpha=alpha)
            for stem, b in read_full_posteriors(H.posterior_file(rot)).items()}


def subst_inner(a) -> int:
    sys.path.insert(0, REPO)
    sys.path.insert(0, HERE)
    import dot_harness as DH
    from lock_side import a3_inputs, geometry_from_session_01, install_guard
    opened = {}
    install_guard(opened)
    DH.register_from(a.register)
    from pipeline.constrained import pd_clean as CL
    CL.force_cpu()
    PC, c0, tfs = CL._bound(a.cell)
    plan = CL.plan_for(c0, tfs)
    tmap = json.loads(os.environ.get("TDR_TEST_TAG_MAP") or "{}")
    for s, p in plan.items():
        if p["changed"]:
            tmap[s] = p["clean"]
    os.environ["TDR_TEST_TAG_MAP"] = json.dumps(tmap)
    pace = CL.apply_pace()
    assert pace is not None
    stage = J(OUT, f"subst_{a.rot}")
    if os.path.exists(J(stage, "subst.json")):
        raise SystemExit(f"REFUSED: {stage}/subst.json exists")
    os.makedirs(stage, exist_ok=True)
    orig_cfg = PC.cfg
    PC.cfg = lambda cell_, cmd=None: (dict(orig_cfg(cell_, cmd), base=stage) if cell_ == a.cell else orig_cfg(cell_, cmd))
    import pipeline.constrained.night_arms as NA
    import pipeline.constrained.pd_decode as PD
    PD.plumb = lambda *x, **k: None
    orig_nt, calls = NA.night_track, []

    def night_track(*args, **kw):
        if kw.get("want_display"):
            o = dict(args[8], entry=a.entry, entry_window_m=(a.window or None))
            args = args[:8] + (o,) + args[9:]
            calls.append((args, dict(kw)))
        return orig_nt(*args, **kw)
    NA.night_track = night_track
    code = PD.inner(a.cell, [f"{VARIANT}+sd{a.sd}"])
    NA.night_track = orig_nt
    assert code == 0 and calls, "the lock decode did not run"
    # the display decodes again, with the four display emissions
    import pipeline.constrained.decoder as D
    import pipeline.constrained.decoder2 as D2
    from pipeline.constrained.dc2_scorerlock import CAP, DELAY_S, LAG_W
    st = args_st = calls[0][0][2]
    from pipeline.constrained.night_common import shipped_pieces
    _st, _cfg, _ne, _tr, _kind, alpha = shipped_pieces()
    E_end = end_emissions(a.rot, args_st, alpha)
    stems = [args[1].stem for args, _kw in calls]
    obs, ceil = {"DISP_END": [], "centre_labelled": []}, {"DISP_END": [], "centre_labelled": []}
    for k, (args, kw) in enumerate(calls):
        sub_args = calls[(k + 1) % len(calls)][0]
        e, rec, sub_e, sub_rec = args[0], args[1], sub_args[0], sub_args[1]
        # night_track resizes a display emission to the decode's length without a word: the lengths must agree
        assert len(E_end[rec.stem]) == len(e) and len(E_end[sub_rec.stem]) == len(sub_e), (rec.stem, sub_rec.stem)
        alt = {"end": E_end[rec.stem], "end_sub": E_end[sub_rec.stem], "centre": e, "centre_sub": sub_e}
        kw2 = dict(kw, display_alt_e=alt, display_alt_flatten={q: PRIOR_F for q in alt})
        D.MAX_ADVANCE_M = CAP
        D2._LT_CACHE.clear()
        rows = orig_nt(*args, **kw2)
        D.MAX_ADVANCE_M = None
        D2._LT_CACHE.clear()
        for r in rows:
            L = (r.get("display_locked") or {}).get(f"{LAG_W}|{DELAY_S}")
            if not L or "paths_alt" not in L:
                continue
            li, line = int(L["lock_step"]), L["lock_line"]
            for arm, own, sub in (("DISP_END", "end", "end_sub"), ("centre_labelled", "centre", "centre_sub")):
                o_, c_ = substitution_on_arc(L["paths_alt"][own][li:], L["paths_alt"][sub][li:], st, line, rec, sub_rec)
                obs[arm] += o_
                ceil[arm] += c_
    res = {"rotation": a.rot, "cell": a.cell, "lock_side": {"sd": a.sd, "entry": a.entry, "window": a.window},
           "prior_f": PRIOR_F, "stems": stems, "pace": pace,
           "per_arm": {arm: {"n_steps": len(obs[arm]), "observed_pct": 100.0 * float(np.mean(obs[arm])) if obs[arm] else None,
                             "ceiling_pct": 100.0 * float(np.mean(ceil[arm])) if ceil[arm] else None} for arm in obs},
           "a3_inputs_opened": [p for p in a3_inputs(opened)
                                if not p.endswith(".gt.json") or "/data/room_A/session_03/" not in p],
           "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    res["geometry_equals_session_01_alone"] = geometry_from_session_01()
    if not res["geometry_equals_session_01_alone"]:
        raise SystemExit("STOP: the line geometry is not session 01's alone")
    if res["a3_inputs_opened"]:
        raise SystemExit(f"STOP: inputs naming session 03: {res['a3_inputs_opened']}")
    with open(J(stage, "subst.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    print(json.dumps(res["per_arm"]), flush=True)
    return 0


def subst_outer(a) -> int:
    sys.path.insert(0, REPO)
    sys.path.insert(0, HERE)
    import dot_harness as DH
    DH.register_from(a.register)
    from pipeline.constrained import pd_cells as PC
    with open(J(REPO, "runs", "dc2_results", "final", "PACE_A1A2.json"), encoding="utf-8") as f:
        p = json.load(f)
    c = PC.cfg(a.cell, "decode")
    env = dict(PC.env_for(c, "half", "decode"), PYTHONPATH=REPO, PD_PACE_MEAN=repr(p["v_mean"]),
               PD_PACE_SD=repr(p["v_sd"]), PD_CLEAN_NOCACHE="1", PD_CLEAN_PREFIX="A3CD", OMP_NUM_THREADS="1")
    args = ["nice", "-n", "10", sys.executable, os.path.abspath(__file__), "subst", "--inner", "--rot", a.rot,
            "--cell", a.cell, "--sd", str(a.sd), "--entry", a.entry, "--window", str(a.window or 0)]
    args += ["--register", a.register] if a.register else []
    return subprocess.call(args, cwd=REPO, env=env)


def subst_summary() -> dict:
    """The gate from the three rotations' subst.json: weighted observed and ceiling shares, ratio per arm."""
    W = {"B1": 2.0, "A2": 1.0, "A1": 1.0}
    per = {r: json.load(open(J(OUT, f"subst_{r}", "subst.json"), encoding="utf-8"))["per_arm"] for r in W}
    out = {}
    for arm in ("DISP_END", "centre_labelled"):
        o = sum(W[r] * per[r][arm]["observed_pct"] for r in W) / sum(W.values())
        c = sum(W[r] * per[r][arm]["ceiling_pct"] for r in W) / sum(W.values())
        out[arm] = {"observed_pct": o, "ceiling_pct": c, "ratio": o / c if c else None}
    out["PASSES"] = {"centre_labelled": True,
                     "DISP_END": bool(out["DISP_END"]["ratio"] is not None and out["centre_labelled"]["ratio"] is not None
                                      and out["DISP_END"]["ratio"] >= out["centre_labelled"]["ratio"])}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["dwell", "subst", "subst-summary"])
    ap.add_argument("--rot", choices=["B1", "A2", "A1"])
    ap.add_argument("--cell")
    ap.add_argument("--register", default=None)
    ap.add_argument("--sd", type=float)
    ap.add_argument("--entry", choices=["soft", "free"], default="soft")
    ap.add_argument("--window", type=float, default=1.0)
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    a.window = a.window if a.window else None
    if a.cmd == "dwell":
        return dwell()
    if a.cmd == "subst-summary":
        r = subst_summary()
        print(json.dumps(r, indent=1))
        return 0
    return subst_inner(a) if a.inner else subst_outer(a)


if __name__ == "__main__":
    sys.exit(main())
