"""R1: the BEFORE numbers. What the old display did, measured with the new instrument.

TWO QUESTIONS, both about the render that shipped at freeze 18m.

BACKWARD STEPS. The old live dot was a per-window argmax with no continuity constraint of any
kind. This counts, per pass, how many times it stepped BACKWARDS along the line it was already
showing. A Viterbi path cannot do that, because the chain structure forbids backward transitions,
so this number is the record of what the change fixes.

ON-SCREEN TRACKING. The old render is replayed frame by frame, at the same 10 fps and the same 1 s
display lag, and scored with the SAME function the new render will be scored with. A frame where
the old renderer hid the dot counts against it rather than being dropped, because a frame with no
red dot is not tracking the green one.
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.constrained.night_common import set_half_roots                      # noqa: E402
set_half_roots(REPO_ROOT)
from pipeline.constrained._guard import assert_isolated                           # noqa: E402
assert_isolated("r1_oldcensus", os.path.join(REPO_ROOT, "runs", "artefacts_half"))

import json                                                                       # noqa: E402
import time                                                                       # noqa: E402

import numpy as np                                                                # noqa: E402

from pipeline.constrained.common import status                                     # noqa: E402
from pipeline.constrained.decoder import decoded_xy                                # noqa: E402
from pipeline.constrained.fh_common import check_contract, claim_fh, release, save  # noqa: E402
from pipeline.constrained.g3_final import shipped_pool_emissions                   # noqa: E402
from pipeline.constrained.night_arms import default_opts, night_track              # noqa: E402
from pipeline.constrained.night_common import STRIDE, assert_motion_model, shipped_pieces  # noqa
from pipeline.constrained.n2_arms import fit_chain_prior                           # noqa: E402
from pipeline.constrained.rebuild_common import WINDOW_S, findings, headline        # noqa: E402
from pipeline.constrained.render_display import backward_steps, on_screen_tracking  # noqa: E402

STAGE = "r1_oldcensus"
TAG, TRAIN, TEST = "s0102_to_s03", ("01", "02"), ("03",)
NIGHT_COMBO = ["C_family", "G_maxlik", "I_chainprior"]
FPS, OLD_LAG_S, OLD_SLIDE_S = 10, 1.0, 0.3


def shipped_opts(st, tr_s):
    n2 = json.load(open(os.path.join(REPO_ROOT, "runs", "constrained", "night", "n2_arms",
                                     "results.json"), encoding="utf-8"))
    arm = {}
    for _t, v in (n2.get("per_pairing") or {}).items():
        for n_, row in (v.get("arms") or {}).items():
            if row and row.get("opts") is not None:
                arm[n_] = {k: ("FIT" if val == "fitted" else val) for k, val in row["opts"].items()}
        break
    prior = fit_chain_prior(st, tr_s)
    opts = default_opts()
    for n_ in NIGHT_COMBO:
        for k, val in (arm.get(n_) or {}).items():
            opts[k] = prior if val == "FIT" else val
    return opts


def replay_old(walk, t, sc, truth_at, st):
    """The old renderer's dot, frame by frame: hold for five frames, step, 0.3 s slide on a switch,
    hidden before the lag has elapsed. Reproduced so the before and after are scored alike."""
    names, states, lo = walk["display_names"], walk["display_state"], walk["lo"]
    t_start = float(t[lo]) + WINDOW_S / 2.0
    t_press = walk["t_press"]
    lag_w = int(round(OLD_LAG_S / STRIDE))
    frames = np.arange(t_start, t_press, 1.0 / FPS)
    red, green, shown, drawn = [], [], "", None
    slide_from, slide_t0 = None, -9.0
    for tq in frames:
        g, _gl, _p = truth_at(sc, float(tq))
        green.append((float(g[0]), float(g[1])) if g else None)
        idx = int(np.floor((tq - t_start) / STRIDE)) - lag_w
        if idx < 0 or idx >= len(names):
            red.append(drawn)                       # the old render drew nothing before the lag
            continue
        s_ = states[idx]
        target = None
        if s_ is not None and s_ >= 0:
            q = decoded_xy(np.array([int(s_)]), st)
            target = (float(q[0][0]), float(q[0][1]))
        if target is not None:
            if names[idx] and names[idx] != shown:
                slide_from, slide_t0 = drawn, tq
                shown = names[idx]
            if slide_from is not None and tq - slide_t0 < OLD_SLIDE_S:
                f = (tq - slide_t0) / OLD_SLIDE_S
                drawn = (slide_from[0] + (target[0] - slide_from[0]) * f,
                         slide_from[1] + (target[1] - slide_from[1]) * f)
            else:
                drawn, slide_from = target, None
        red.append(drawn)
    return red, green


def main() -> int:
    lock = claim_fh(STAGE)
    t0 = time.time()
    st, cfg, ne, transit, kind, alpha = shipped_pieces()
    mm = assert_motion_model()
    from pipeline.constrained.rb7_demo import sidecar_for, truth_at
    from pipeline.constrained.sb2_structural import press_ends
    status(f"{STAGE} START: the old display, censused. motion model {mm}")

    src, info = shipped_pool_emissions(TAG, TRAIN, TEST, False, st, kind, alpha)
    if src is None:
        status(f"{STAGE}: no pooled emissions")
        release(lock)
        return 1
    opts = shipped_opts(st, TRAIN)
    RES = {"stage": STAGE, "tag": TAG, "n_heads": info.get("heads"),
           "old_display": "per-window argmax of the forward pass, no continuity constraint",
           "old_lag_s": OLD_LAG_S, "fps": FPS, "per_recording": {}, "failures": []}

    tot_back, tot_pass, all_red, all_green, per_pass = 0, 0, [], [], []
    for stem, rec, ge, e in src:
        who = stem.replace("participant_", "").split("_")[0]
        try:
            rows = night_track(e, rec, st, cfg, transit, ne, ge, STRIDE, opts, None,
                               want_display=True)
            presses = press_ends(rec.session, rec.stem)
            sc = sidecar_for(stem)
            t = np.asarray(rec.t0, float)
            recnode, back_here = [], 0
            for r in rows:
                b = backward_steps(r["display_names"], r["display_state"])
                back_here += b
                walk = {"display_names": r["display_names"], "display_state": r["display_state"],
                        "lo": r["lo"], "t_press": float(presses[int(r["pass_id"])])}
                red, green = replay_old(walk, t, sc, truth_at, st)
                tr = on_screen_tracking(red, green)
                all_red += red
                all_green += green
                node = {"pass_id": int(r["pass_id"]), "true": r["true_line"],
                        "committed": r["final_line"], "correct": bool(r["found_final"]),
                        "backward_steps": int(b), "tracking": tr}
                recnode.append(node)
                per_pass.append(node)
            tot_back += back_here
            tot_pass += len(rows)
            RES["per_recording"][who] = {"n_passes": len(rows), "backward_steps": int(back_here),
                                         "passes": recnode}
            status(f"  {who:8s} {len(rows)} passes, {back_here} backward steps, tracking "
                   f"{np.mean([p['tracking']['within_pct'] for p in recnode]):5.1f} percent")
        except Exception as exc:                                         # noqa: BLE001
            import traceback
            RES["failures"].append({"who": who, "error": repr(exc),
                                    "traceback": traceback.format_exc()[-1200:]})
            status(f"  {who}: FAILED {exc!r}")

    RES["pooled_tracking"] = on_screen_tracking(all_red, all_green)
    ok = [p for p in per_pass if p["correct"]]
    bad = [p for p in per_pass if not p["correct"]]

    def agg(rows_):
        v = [r["tracking"]["within_pct"] for r in rows_ if r["tracking"]["within_pct"] is not None]
        m = [r["tracking"]["mean_m"] for r in rows_ if r["tracking"]["mean_m"] is not None]
        return {"n_passes": len(rows_), "within_pct_mean_over_passes": float(np.mean(v)) if v else None,
                "mean_m_over_passes": float(np.mean(m)) if m else None}

    RES["split"] = {"correct_line": agg(ok), "wrong_line": agg(bad), "all": agg(per_pass)}
    RES["backward_steps"] = {
        "total": int(tot_back), "n_passes": int(tot_pass),
        "per_pass_mean": float(tot_back / max(1, tot_pass)),
        "passes_with_at_least_one": int(sum(1 for p in per_pass if p["backward_steps"] > 0)),
        "why": ("a per-window argmax has no continuity constraint, so the drawn dot could step "
                "backwards along the line it was already showing. A Viterbi path cannot, because "
                "the chain structure forbids backward transitions")}
    RES["minutes"] = round((time.time() - t0) / 60.0, 1)
    RES["contract"] = check_contract(RES, ["per_recording", "pooled_tracking", "backward_steps",
                                           "split"], {"per_recording": 6})
    save(STAGE, RES)
    release(lock)

    P, B = RES["pooled_tracking"], RES["backward_steps"]
    status(f"  BEFORE: on-screen tracking {P['within_pct']:.1f} percent of frames within 0.5 m, "
           f"mean {P['mean_m']:.2f} m, frames with NO red dot {P['n_no_red_dot']}")
    status(f"  BEFORE: {B['total']} backward steps over {B['n_passes']} passes, "
           f"{B['per_pass_mean']:.2f} per pass, on {B['passes_with_at_least_one']} passes")
    headline(f"R1 BEFORE: the old display tracked the green dot on {P['within_pct']:.1f} percent "
             f"of frames within 0.5 m, mean {P['mean_m']:.2f} m, with {B['total']} backward steps "
             f"over {B['n_passes']} passes.")
    findings("r1", bool(RES["contract"]["SATISFIED"]), (
        f"THE BEFORE NUMBERS, measured on the render frozen at 18m with the same instrument the "
        f"new render will be measured with.\n\n"
        f"ON-SCREEN TRACKING, at the displayed time so the 1 s lag counts against it: "
        f"{P['within_pct']:.2f} percent of frames within 0.5 m of the green dot, mean distance "
        f"{P['mean_m']:.2f} m over {P['n_frames']} frames. {P['n_no_red_dot']} frames had NO RED "
        f"DOT at all and count as misses, because a frame with no dot is not tracking anything.\n"
        f"  correct-line passes: {RES['split']['correct_line']}\n"
        f"  wrong-line passes:   {RES['split']['wrong_line']}\n\n"
        f"BACKWARD STEPS: {B['total']} over {B['n_passes']} passes, {B['per_pass_mean']:.2f} per "
        f"pass, occurring on {B['passes_with_at_least_one']} passes. {B['why']}."))
    status(f"{STAGE} DONE in {RES['minutes']:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
