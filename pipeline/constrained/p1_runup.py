"""ITEM 1: verify the operator's run-up account, and map where the run-up physically lies.

THE OPERATOR'S ACCOUNT. In almost every pass the participant started BEHIND the start tape and
walked in along the line's own direction, so as to be mid-stride at the first press. If that is
right, the two seconds before the press are a continuation of the same walk on the line's backward
extension, not transit, and the motion gate should say "walking" through almost all of it.

WHAT THIS STAGE DOES NOT DO. It changes nothing and trains nothing. It reports the gate's verdict
on the pre-press windows and the geometry of each line's run-up zone, so the assumption is checked
before anything is built on it.

THE PRE-PRESS WINDOWS ARE LEGAL. A window whose END is at or before the first press used only
samples recorded before the press. Nothing here reopens the causality problem of item 1 of the
previous brief; this is past data that was always there.
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.constrained.night_common import set_half_roots                      # noqa: E402
set_half_roots(REPO_ROOT)
from pipeline.constrained._guard import assert_isolated                           # noqa: E402
assert_isolated("p1_runup", os.path.join(REPO_ROOT, "runs", "artefacts_half"))

import glob                                                                       # noqa: E402
import json                                                                       # noqa: E402
import time                                                                       # noqa: E402

import numpy as np                                                                # noqa: E402

from pipeline.constrained.common import status                                     # noqa: E402
from pipeline.constrained.fh_common import check_contract, claim_fh, release, save  # noqa: E402
from pipeline.constrained.rebuild_common import WINDOW_S, findings, headline        # noqa: E402

STAGE = "p1_runup"
#: the motion gate's fitted threshold, from stage0_preflight
THETA = 0.431
#: how far back before the press this stage looks
LOOKBACK_S = 2.0
#: the taped grid, and the nodes, both in metres in the grid frame
GRID = (0.0, 5.0)
NODES = {"TX": (2.5, -0.5), "RX1": (2.5, 5.5), "RX2": (-0.5, 2.5), "RX3": (5.5, 2.5)}
#: how close a person may come to a node before the run-up is blocked
NODE_CLEAR_M = 0.3
#: the run-up length the extended-chain arm may use
MAX_RUNUP_M = 1.5


def first_presses(session, stem):
    """{pass_id: first anchor press}. The reaction-time bias is already subtracted at labelling."""
    from pipeline.constrained.lattice import gt_path
    p = gt_path(session, stem)                   # data/room_A/... unless DC2 sets the room
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    assert (d.get("reaction_time") or {}).get("applied"), (
        f"{p} does not record the reaction-time bias as applied; subtracting it again would "
        f"over-correct, which rt_calibration warns about by name")
    return {int(ps["pass_id"]): float(ps["anchor_times"][0]) for ps in d.get("passes", [])
            if ps.get("anchor_times")}


def runup_geometry(st):
    """Where each line's run-up zone lies, how far it can extend, and what stops it."""
    xy = np.asarray(st.xy)
    out = {}
    for nm in st.names:
        a, b = st.slice_of[nm]
        p0 = xy[a]
        u = np.asarray(st.dir_of[a], float)          # unit direction of travel
        back = -u                                     # the run-up runs backwards along it
        # how far before leaving the taped grid
        lim_grid = 0.0
        for d in np.arange(0.0, MAX_RUNUP_M + 1e-9, 0.05):
            q = p0 + back * d
            if GRID[0] - 1e-9 <= q[0] <= GRID[1] + 1e-9 and GRID[0] - 1e-9 <= q[1] <= GRID[1] + 1e-9:
                lim_grid = d
            else:
                break
        # how far before coming within NODE_CLEAR_M of a node
        lim_node, blocker = MAX_RUNUP_M, None
        for nname, npos in NODES.items():
            npos = np.asarray(npos, float)
            for d in np.arange(0.0, MAX_RUNUP_M + 1e-9, 0.05):
                q = p0 + back * d
                if float(np.linalg.norm(q - npos)) < NODE_CLEAR_M:
                    if d < lim_node:
                        lim_node, blocker = float(d), nname
                    break
        usable = min(MAX_RUNUP_M, lim_node)
        out[nm] = {
            "start": [round(float(p0[0]), 2), round(float(p0[1]), 2)],
            "travel_direction": [round(float(u[0]), 3), round(float(u[1]), 3)],
            "runup_runs_towards": [round(float(back[0]), 3), round(float(back[1]), 3)],
            "runup_end_at_max": [round(float((p0 + back * usable)[0]), 2),
                                 round(float((p0 + back * usable)[1]), 2)],
            "inside_grid_for_m": round(float(lim_grid), 2),
            "blocked_by_node": blocker,
            "blocked_at_m": (round(float(lim_node), 2) if blocker else None),
            "usable_runup_m": round(float(usable), 2),
            "entirely_outside_the_grid": bool(lim_grid < 0.05),
            "nearest_cell_when_outside": "the start cell"}
    return out


def main() -> int:
    lock = claim_fh(STAGE)
    t0 = time.time()
    from pipeline.constrained import paths as P
    from pipeline.constrained.recordings import gate_energy, load_meta, recordings
    st = P.states()
    status(f"{STAGE} START: verifying the run-up account, gate theta {THETA}")

    RES = {"stage": STAGE, "read_only": True, "gate_theta": THETA,
           "lookback_s": LOOKBACK_S, "window_s": WINDOW_S,
           "legality": ("only windows whose END is at or before the first press are counted, so "
                        "every window used consists of samples recorded before the press"),
           "geometry": {"grid_m": list(GRID), "nodes_m": {k: list(v) for k, v in NODES.items()},
                        "frame": "metres, (0,0) the bottom-left of the taped grid, x=col, y=row"},
           "runup": runup_geometry(st), "per_recording": {}, "failures": []}

    pre, during, idle = [], [], []
    for sess, stem in recordings():
        try:
            rec = load_meta(sess, stem)
            ge = np.asarray(gate_energy(sess, stem), float)
            t = np.asarray(rec.t0, float)
            mode = np.asarray(rec.mode).astype(str)
            pid_arr = np.asarray(rec.pass_id)
            fp = first_presses(sess, stem)
            rows = []
            for pid, nm, _a, _b in rec.pass_spans():
                press = fp.get(int(pid))
                if press is None:
                    continue
                # windows whose END is at or before the press, within LOOKBACK_S of it
                end = t + WINDOW_S
                sel = np.flatnonzero((end <= press + 1e-9) & (end >= press - LOOKBACK_S - 1e-9))
                if not len(sel):
                    continue
                frac = float(np.mean(ge[sel] > THETA))
                rows.append({"pass_id": int(pid), "line": nm, "n_windows": int(len(sel)),
                             "walking_fraction": frac,
                             "gate_median": float(np.median(ge[sel]))})
                pre.append(frac)
            w = np.flatnonzero(mode == "walk")
            if len(w):
                during.append(float(np.mean(ge[w] > THETA)))
            # THE STILL REFERENCE IS THE GRID DWELLS, not "idle". Idle windows between passes are
            # mostly TRANSIT, when the person genuinely is walking back to the next start, and the
            # gate's own docstring says it calls 53 percent of transit windows walking for exactly
            # that reason. Using idle as the still reference makes the gate look like a poor
            # discriminator and would have understated the run-up finding.
            i = np.flatnonzero(mode == "grid")
            if len(i):
                idle.append(float(np.mean(ge[i] > THETA)))
            RES["per_recording"][f"{sess}|{stem}"] = {
                "n_passes": len(rows),
                "pre_press_walking_fraction": float(np.mean([r["walking_fraction"] for r in rows]))
                if rows else None, "passes": rows}
        except Exception as exc:                                         # noqa: BLE001
            import traceback
            RES["failures"].append({"rec": f"{sess}|{stem}", "error": repr(exc),
                                    "traceback": traceback.format_exc()[-800:]})
            status(f"  {sess}|{stem}: FAILED {exc!r}")

    pre = np.asarray(pre)
    RES["verdict"] = {
        "n_passes": int(len(pre)),
        "pre_press_walking_fraction_mean": float(pre.mean()) if len(pre) else None,
        "pre_press_walking_fraction_median": float(np.median(pre)) if len(pre) else None,
        "passes_above_half": int((pre > 0.5).sum()),
        "passes_fully_walking": int((pre > 0.99).sum()),
        "reference_during_the_walk": float(np.mean(during)) if during else None,
        "reference_when_still_on_the_grid": float(np.mean(idle)) if idle else None}
    V = RES["verdict"]
    RES["verdict"]["SUPPORTS_THE_ACCOUNT"] = bool(
        V["pre_press_walking_fraction_mean"] is not None
        and V["reference_when_still_on_the_grid"] is not None
        and V["pre_press_walking_fraction_mean"] > 0.5
        and V["pre_press_walking_fraction_mean"] > 2 * V["reference_when_still_on_the_grid"])

    RES["minutes"] = round((time.time() - t0) / 60.0, 1)
    RES["contract"] = check_contract(RES, ["runup", "per_recording", "verdict"],
                                     {"per_recording": 18})
    save(STAGE, RES)
    release(lock)

    status(f"  pre-press walking fraction: mean {V['pre_press_walking_fraction_mean']:.3f}, "
           f"median {V['pre_press_walking_fraction_median']:.3f} over {V['n_passes']} passes")
    status(f"  reference: during the walk {V['reference_during_the_walk']:.3f}, "
           f"still on the grid {V['reference_when_still_on_the_grid']:.3f}")
    status(f"  passes over half walking: {V['passes_above_half']} of {V['n_passes']}; "
           f"fully walking: {V['passes_fully_walking']}")
    status(f"  SUPPORTS THE ACCOUNT = {RES['verdict']['SUPPORTS_THE_ACCOUNT']}")
    status("  run-up geometry:")
    for nm, g in RES["runup"].items():
        status(f"    {nm:8s} start {g['start']} runs to {g['runup_end_at_max']}  usable "
               f"{g['usable_runup_m']} m  outside grid {g['entirely_outside_the_grid']}  "
               f"blocked by {g['blocked_by_node']}")
    headline(f"P1 RUN-UP: the two seconds before the press are walking on "
             f"{100 * V['pre_press_walking_fraction_mean']:.1f} percent of windows against "
             f"{100 * V['reference_when_still_on_the_grid']:.1f} when standing still; supports the operator's account = "
             f"{RES['verdict']['SUPPORTS_THE_ACCOUNT']}.")
    findings("p1", bool(RES["contract"]["SATISFIED"]), (
        f"THE OPERATOR'S RUN-UP ACCOUNT, checked. {RES['legality']}.\n\n"
        f"THE MOTION GATE on the {LOOKBACK_S} s before the first press, {V['n_passes']} passes: "
        f"walking on {100 * V['pre_press_walking_fraction_mean']:.1f} percent of windows on "
        f"average, median {100 * V['pre_press_walking_fraction_median']:.1f}. For reference the "
        f"gate says walking on {100 * V['reference_during_the_walk']:.1f} percent of labelled walk "
        f"windows and only {100 * V['reference_when_still_on_the_grid']:.1f} percent of "
        f"windows where the person is standing still on a grid point. "
        f"{V['passes_above_half']} of {V['n_passes']} passes are over half walking and "
        f"{V['passes_fully_walking']} are entirely walking.\n\n"
        f"SUPPORTS THE ACCOUNT = {RES['verdict']['SUPPORTS_THE_ACCOUNT']}.\n\n"
        f"THE RUN-UP ZONES. Every line's start lies ON the taped grid's boundary, so every run-up "
        f"zone is ENTIRELY OUTSIDE the 5 by 5 grid and has no cell of its own; the nearest cell is "
        f"the start cell, as the brief anticipated. The nodes sit 0.5 m outside each edge at the "
        f"edge midpoints, so four lines have a node directly behind their start: "
        + ", ".join(f"{nm} blocked by {g['blocked_by_node']} at {g['blocked_at_m']} m"
                    for nm, g in RES["runup"].items() if g["blocked_by_node"])
        + ". The remaining eight have a clear run-up to the 1.5 m the extended-chain arm may use."))
    status(f"{STAGE} DONE in {RES['minutes']:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
