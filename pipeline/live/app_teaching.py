"""The teaching pack from the live app (Uzayr, 30 September 2026, part E): B2, P5, passes 2 and 10.

    python3 -m pipeline.live.app_teaching            # reports/tracking/teaching/teaching-pack-app.json (TEACHING_OUT names it;
                                                     # the current pack, v3, is 2026-10-01_teaching-pack-app-v3.json)

One model, and it is the live app. The worked example's two passes (tools/teaching_pack.py chose them from
FINAL's saved rows: P5's pass 2, lock and committed right; pass 10, lock wrong and committed right) are
rebuilt from the APP: P5's B2 recording is replayed through `pipeline.live` (the final model set, the
semi-constrained mode, one start press per walk, the as-it-arrives clock) and every figure below is the
app's own:
  - per window: the app's cut window, its band energy (raw, and scaled by the recording's gate), the five
    heads' posteriors computed by the app's own heads on that window, pooled (the log-opinion pool) and over
    the training marginal;
  - per pass: the lock (the line first drawn, at press + 2.0 s), the committed line and when it was
    announced, the exit window, the switches;
  - per frame: the dot the app's screen shows, its scene time, the truth at that scene time and the error.
The truth is read HERE, as the scorer reads it, never by the app. Plumbing: the app's committed line and lock
on all 20 of P5's passes against the corrected offline decode (FC), and the two passes against the old pack.
Participants: the code P5 and, since 30 Sep (names allowed), the name. The v2 export (item 8 of the second
brief) adds the unconstrained view: the same walks as the app saw them with no press at all.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = os.path.join
OUT = J(REPO_ROOT, "reports", "tracking", "teaching", os.environ.get("TEACHING_OUT", "teaching-pack-app.json"))
#: the app's no-press replay of the same recording (the unconstrained mode, m = 4), for the unconstrained view
UNC_LOG = os.environ.get("TEACHING_UNC_LOG") or J(REPO_ROOT, "runs", "live", "replay", "final", "unconstrained_m4_causal",
                                                  "B2__participant_PA2_walk.jsonl")
NAME = "PA2"          # names are allowed in outputs since 30 Sep (Uzayr); the code P5 is kept beside it
OLD = J(REPO_ROOT, "reports", "tracking", "teaching", "2026-09-29_teaching-pack-first.json")
SESSION, STEM, PASSES, CODE = "B2", "participant_PA2_walk", (2, 10), "P5"
FC = J(REPO_ROOT, "runs", "dc2_results", "cells", "fin_B2", "d3", "FC.relgateU+abstain+a2w0.25")


def r_(x, k=3):
    return None if x is None or not np.isfinite(float(x)) else round(float(x), k)


def unconstrained_view(gt: dict, latency: float, truth_at) -> dict:
    """The same two walks as the app saw them with NO press (the unconstrained mode, m = 4): whether it detected
    them, how far its detected start was from the true press, its lock and committed line, and its drawn dots."""
    if not os.path.exists(UNC_LOG):
        return {"available": False}
    from pipeline.live.app_score import match
    rows = [json.loads(ln) for ln in open(UNC_LOG, encoding="utf-8")]
    det = {r["pid"]: float(r["t"]) for r in rows if r["kind"] == "detected_start"}
    mt = match({p: float(g["t_start"]) for p, g in gt.items()}, det)
    out = {"available": True, "log": os.path.relpath(UNC_LOG, REPO_ROOT), "m": 4, "walks": {}}
    for pid in PASSES:
        d = mt.get(pid)
        if d is None:
            out["walks"][str(pid)] = {"detected": False}
            continue
        p = gt[pid]
        P = float(p["t_start"])
        lk = next((r for r in rows if r["kind"] == "lock" and r["pid"] == d), None)
        cm = next((r for r in rows if r["kind"] == "committed" and r["pid"] == d), None)
        F = []
        for r in sorted((r for r in rows if r["kind"] == "dot" and r["pid"] == d), key=lambda r: r["x"]):
            g = truth_at(p, float(r["x"]) - latency)
            F.append({"video_s": r_(float(r["x"]) - P), "xy": [r_(r["xy"][0]), r_(r["xy"][1])],
                      "truth_xy": ([r_(g[0]), r_(g[1])] if g is not None else None),
                      "err_m": (r_(float(np.hypot(r["xy"][0] - g[0], r["xy"][1] - g[1]))) if g is not None else None),
                      "computed_late_s": r_(max(0.0, float(r["computed_at"]) - float(r["x"]))) if r.get("computed_at") else None})
        out["walks"][str(pid)] = {"detected": True, "app_walk": int(d), "detected_start_minus_press_s": r_(det[d] - P),
                                  "lock_line": lk["line"] if lk else None, "committed_line": cm["line"] if cm else None,
                                  "true_line": p["path_name"], "committed_announced_at_s": r_(float(cm["at"]) - P) if cm else None,
                                  "frames": F}
    return out


def inner() -> int:
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    from pipeline.live.app_replay import VARIANT, code_of, replay_inner
    from pipeline.live.app_score import truth_at
    from pipeline.live.display import LATENCY_S
    from pipeline.live.final_model import _components
    from pipeline.live.model_sets import check
    assert code_of(STEM) == CODE
    chk = check("final")
    if not chk["ok"]:
        raise SystemExit(f"REFUSED: the final model set differs from its manifest: {chk['mismatched'][:5]}")
    comp = _components("fin_B2", VARIANT)
    PC, c = comp[0], comp[1]
    from pipeline.constrained.g3_final import g100_to_25          # after the cell's roots are bound (import guard)
    hold = []
    summ = replay_inner("final", SESSION, STEM, "start", "causal", False, components=comp, hold=hold)
    s = hold[0]
    with open(J(PC.raw_dir(SESSION), f"{STEM}.gt.json"), encoding="utf-8") as f:
        gt = {int(p["pass_id"]): p for p in json.load(f)["passes"]}
    # plumbing: all of P5's passes against the corrected offline decode
    fc_c = {int(r["pass_id"]): r["final_line"] for r in json.load(open(J(FC, "decode.json")))["sessions"][SESSION]["rows"]["A"]
            if r["stem"] == STEM}
    fc_l = {int(r["pass_id"]): r["display_lock"] for r in json.load(open(J(FC, "scorerlock.json")))["sessions"][SESSION]["rows"]["A"]
            if r["stem"] == STEM}
    app_c = {int(d["pass_id"]): d["final_line"] for d in s.decisions}
    app_l = {int(p): ln for p, ln in s.first_lock.items()}
    plumb = {"passes_checked": len(fc_c), "committed_equal_to_FC": sum(app_c.get(p) == fc_c[p] for p in fc_c),
             "lock_equal_to_FC": sum(app_l.get(p) == fc_l.get(p) for p in fc_c),
             "differences": [{"pass": p, "app": [app_c.get(p), app_l.get(p)], "FC": [fc_c[p], fc_l.get(p)]}
                             for p in fc_c if app_c.get(p) != fc_c[p] or app_l.get(p) != fc_l.get(p)]}
    old = json.load(open(OLD, encoding="utf-8"))
    old_meta = {int(p["meta"]["pass_id"]): p["meta"] for p in old["passes"]}
    ks = sorted(s.win)
    t0 = np.array([float(s.win[k]["t0"]) for k in ks])
    theta = float(comp[2][2].motion_theta)                  # the null emission's motion threshold (pieces' ne)
    marg = s.pool.marg
    passes = []
    for pid in PASSES:
        p = gt[pid]
        P = float(p["t_start"])
        dec = next(d for d in s.decisions if int(d["pass_id"]) == pid)
        t_exit = float(s.decoder.t0[dec["exit_window"]]) + 1.0
        meta_d = s.display.meta.get(pid, {})
        # the windows: centres from press - 2 s to the exit
        idx = [i for i, t in enumerate(t0) if P - 2.0 - 1e-6 <= t + 1.0 <= t_exit + 1e-6]
        W = []
        for i in idx:
            w = s.win[ks[i]]
            probs = s.pool.head_probs(np.asarray(w["feats"])[None], np.asarray(w["rssi"])[None], s.rrel)
            parts = []
            for name, cells, _m, _p in s.pool.heads:
                pr = probs[name].astype(float)
                if cells == 100:
                    pr = g100_to_25(pr)
                pr = pr / np.maximum(pr.sum(axis=1, keepdims=True), 1e-300)
                parts.append(np.log(np.maximum(pr[0], 1e-300)))
            pp = np.exp(np.mean(parts, axis=0))
            pp = pp / pp.sum()
            pm = None
            if marg is not None:
                pm = pp / np.maximum(np.asarray(marg, float), 1e-300)
                pm = pm / pm.sum()
            tc = float(w["t0"]) + 1.0
            g = truth_at(p, tc)
            W.append({"t_centre_s": r_(tc - P), "band_energy_raw": r_(float(w["ge"]) / float(s.gate_scale or 1.0), 4),
                      "band_energy_scaled": r_(w["ge"], 4),
                      "still": (bool(float(w["ge"]) < theta) if theta is not None else None),
                      "p_pool": [r_(v, 4) for v in pp], "p_pool_over_marginal": ([r_(v, 4) for v in pm] if pm is not None else None),
                      "truth_xy": ([r_(g[0]), r_(g[1])] if g is not None else None)})
        # the frames the screen shows for this walk, with the scene moment each shows (V1)
        out = s.display.out.get(pid, {})
        F = []
        for x in sorted(out):
            xy = out[x]
            g = truth_at(p, x - LATENCY_S)
            F.append({"video_s": r_(x - P), "scene_s": r_(x - LATENCY_S - P), "xy": [r_(xy[0]), r_(xy[1])],
                      "truth_xy": ([r_(g[0]), r_(g[1])] if g is not None else None),
                      "err_m": (r_(float(np.hypot(xy[0] - g[0], xy[1] - g[1]))) if g is not None else None),
                      "phase": ("park" if x < P + LATENCY_S - 1e-6 else
                                "anchor (held at the locked line's entry)" if meta_d.get("t_dec0") and x < float(meta_d["t_dec0"]) - 1e-6
                                else "decoded")})
        dec_err = [f["err_m"] for f in F if f["phase"] == "decoded" and f["err_m"] is not None]
        om = old_meta.get(pid, {})
        passes.append({
            "role": f"lock {'right' if app_l.get(pid) == p['path_name'] else 'wrong'}, "
                    f"committed {'right' if app_c.get(pid) == p['path_name'] else 'wrong'}",
            "meta": {"participant": CODE, "session": SESSION, "pass_id": pid, "true_line": p["path_name"],
                     "lock_line_app": app_l.get(pid), "lock_at_s": 2.0,
                     "committed_line_app": app_c.get(pid),
                     "committed_announced_at_s": r_(float(s.decoder.t0[dec["decided_at_window"]]) + 2.0 - P),
                     "exit_window_centre_s": r_(t_exit - P),
                     "switches": [{"video_s": r_(float(sw["x"]) - P), "old": sw["old"], "new": sw["new"]}
                                  for sw in (meta_d.get("switches") or [])],
                     "press_times_s": [r_(t - P) for t in p["anchor_times"]],
                     "the_app_was_given": "the radio and this walk's FIRST press only",
                     "decoded_dot_median_err_m": r_(float(np.median(dec_err))) if dec_err else None,
                     "old_pack_offline_relgateU": {"lock_line": om.get("lock_line"), "committed_line": om.get("committed_line"),
                                                   "note": "the old pack decoded variant relgateU, before the final "
                                                           "variant relgateU+abstain+a2w0.25 was chosen"}},
            "windows": W, "frames": F})
    pack = {
        "what": "Two B2 test passes of P5, from the LIVE APP (the tracking model since 30 Sep): one start press per "
                "walk, the as-it-arrives clock, every figure the app's own",
        "made": time.strftime("%Y-%m-%d %H:%M SAST"),
        "model_set": "runs/live/models/final.json (final model; display head DISP_END final)",
        "replay": {k: summ[k] for k in ("mode", "clock", "variant", "n_committed", "n_locks", "n_frames", "stats")},
        "plumbing": plumb,
        "conventions": {
            "times": "seconds from the walk's start press (raw key time)",
            "video_s / scene_s": "a frame at video time x shows the scene moment x - 2.0 s (V1); the dot error "
                                 "compares the drawn dot with the truth at the scene moment",
            "phases": "park (room centre) until press + 2.0 s; then the locked line's entry, held until the first "
                      "decoded position (rule 2a, live form); then the decoded path",
            "p_pool": "exp(mean over the app's five heads of log p_head(cell)), renormalised over 25 cells, on the "
                      "app's own window",
            "band_energy": "raw, and scaled by the recording's gate max(1, G0 / g_rec)",
            "truth": "linear between the pass's anchor presses; read by this export, never by the app"},
        "passes": passes}
    pack["participant"] = {"code": CODE, "name": NAME}
    pack["display_candidate"] = s.display_candidate
    pack["unconstrained_view"] = unconstrained_view(gt, LATENCY_S, truth_at)
    txt = json.dumps(pack, indent=None, separators=(",", ":"))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"wrote {os.path.relpath(OUT, REPO_ROOT)} ({len(txt) // 1024} KB); plumbing {plumb['committed_equal_to_FC']}/"
          f"{plumb['passes_checked']} committed, {plumb['lock_equal_to_FC']} locks equal to FC")
    return 0 if not plumb["differences"] else 1


def main(argv=None) -> int:
    if "--inner" in (argv or sys.argv[1:]):
        return inner()
    from pipeline.live.final_model import _env
    return subprocess.call([sys.executable, "-m", "pipeline.live.app_teaching", "--inner"], cwd=REPO_ROOT,
                           env=dict(_env("fin_B2"), OMP_NUM_THREADS="1"))


if __name__ == "__main__":
    sys.exit(main())
