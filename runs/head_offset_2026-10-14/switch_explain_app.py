"""Uzayr's decision after the A3 and B2 results (DECISION_1p0.md): the mechanism of the two corrective switches B2 loses at
1.0 s (PA4, PA4, walk 5: locked E_row5, true D_fwd; PA6, PA6, walk 5: locked B_rev, true D_rev), from the code.

    python3 runs/head_offset_2026-10-14/switch_explain_app.py --stem participant_PA4_walk --lock E_row5 --arm 0.75

The recording runs through the live app's own replay (`app_replay.replay_inner`, the final model, semi mode, the causal
clock, the clean profile with head_offset_s set to the arm in this process only, the output under this folder), with
`switching.decide_walk` wrapped as in switch_explain.py: every decision frame of the walk is re-read with decide_walk's own
quantities (the lead over the drawn line and theta; the distance from the marker's drawn position to the best line's state
against the 1.5 m radius; the drawn marker's furthest arc against the final-zone limit). The replay must reproduce the
existing log of the same configuration row for row (the shipped 0.75 s replay, or step 4's 1.0 s one), so it re-runs a
configuration already decoded and is not a new look. Output: explain/<stem>_<arm>.json.

Development evaluation, all data seen.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, REPO)
PID = 5


def main(stem: str, lock_line: str, arm: float, pid: int = PID) -> int:
    import ho_harness as H
    opened = {}
    H.install_guard(opened)
    import step4
    step4.cpu_only()                                   # the app's command line forces the CPU (STEP4_INVALID.md)
    import pipeline.constrained.switching as SW
    import pipeline.live.app_replay as AR
    import pipeline.live.final_model as FM
    from pipeline.constrained.render_display import xy_of
    ref = (J(REPO, "runs", "live", "replay", "final", "semi_disp-K1gf_causal") if arm == 0.75
           else J(HERE, "step4_cpu", "final", "semi_disp-K1gf_causal"))
    ref_rows = [json.loads(ln) for ln in open(J(ref, f"B2__{stem}.jsonl"), encoding="utf-8")]
    press = next(float(r["t"]) for r in ref_rows if r["kind"] == "press" and r["pid"] == pid)
    assert FM.DISPLAY_PROFILE == "clean" and FM.DISPLAY_PROFILES["clean"]["sett"]["head_offset_s"] == 0.75
    FM.DISPLAY_PROFILES["clean"]["sett"]["head_offset_s"] = arm                      # this process only
    AR.OUT = J(HERE, "explain_cpu", f"o{arm:g}")
    orig = SW.decide_walk
    calls = []

    def wrapped(lock_line_, decs, adj, theta, st, dots_lock, dots_for_line, radius=None, max_switches=SW.MAX_SWITCHES,
                final_m=SW.FINAL_M):
        res = orig(lock_line_, decs, adj, theta, st, dots_lock, dots_for_line, radius=radius, max_switches=max_switches,
                   final_m=final_m)
        xs = [float(d["x"]) for d in decs]
        if lock_line_ == lock_line and xs and press <= xs[0] <= press + 20.0:
            fr = [(float(x), p) for x, p in dots_lock if p is not None]
            fx = np.asarray([x for x, _p in fr], float)
            L = SW.line_length(st, lock_line_)
            arcs = np.maximum.accumulate([SW.arc_along(st, lock_line_, p) for _x, p in fr]) if fr else []
            rows = []
            for d in decs:
                x = float(d["x"])
                n_up = int(np.searchsorted(fx, x + 1e-9, side="right"))
                if n_up == 0:
                    continue
                tot = {nm: d["raw"][nm] + float((adj or {}).get(nm, 0.0)) for nm in d["raw"]}
                best = max(tot, key=tot.get)
                dot_now = fr[n_up - 1][1]
                q = xy_of(st, d["end"][best]) if best != lock_line_ else None
                rows.append({"x_minus_press_s": round(x - press, 4), "best": best, "lead_nats": float(tot[best] - tot[lock_line_]),
                             "theta": float(theta), "radius_dist_m": (float(np.hypot(q[0] - dot_now[0], q[1] - dot_now[1]))
                                                                     if q is not None else None),
                             "radius_m": radius, "dot_max_arc_m": float(arcs[n_up - 1]), "final_zone_from_m": float(L - final_m),
                             "in_final_zone": bool(float(arcs[n_up - 1]) >= L - final_m)})
            calls.append({"switches": [{"x_minus_press_s": round(float(s["x"]) - press, 4), "old": s["old"], "new": s["new"]}
                                       for s in res["switches"]],
                          "disabled_final_m_at_minus_press_s": (None if res["disabled_final_m_at"] is None
                                                                else round(float(res["disabled_final_m_at"]) - press, 4)),
                          "rows": rows})
        return res
    SW.decide_walk = wrapped
    summ = AR.replay_inner("final", "B2", stem, "start", "causal", False)
    new_rows = [json.loads(ln) for ln in open(summ["log"], encoding="utf-8")]
    out = {"stem": stem, "pid": pid, "device": "cpu", "lock_line": lock_line, "arm_head_offset_s": arm, "press": press,
           "reproduces_reference": new_rows == ref_rows, "reference": os.path.relpath(J(ref, f"B2__{stem}.jsonl"), REPO),
           "n_calls": len(calls), "last_call": calls[-1] if calls else None}
    os.makedirs(J(HERE, "explain_cpu"), exist_ok=True)
    json.dump(out, open(J(HERE, "explain_cpu", f"{stem}_{pid}_{arm:g}.json"), "w", encoding="utf-8"), indent=1, default=float)
    print(json.dumps({k: out[k] for k in ("stem", "arm_head_offset_s", "reproduces_reference", "n_calls")}))
    return 0 if out["reproduces_reference"] else 1


if __name__ == "__main__":
    a = sys.argv[1:]
    stem, lock, arm = a[a.index("--stem") + 1], a[a.index("--lock") + 1], float(a[a.index("--arm") + 1])
    pid = int(a[a.index("--pid") + 1]) if "--pid" in a else PID
    if "--inner" in a:
        sys.exit(main(stem, lock, arm, pid))
    import subprocess
    from pipeline.live.app_replay import cell_for
    from pipeline.live.final_model import _env
    env = dict(_env(cell_for("final", "B2")), OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
               VECLIB_MAXIMUM_THREADS="1")
    sys.exit(subprocess.call(["nice", "-n", "10", sys.executable, os.path.abspath(__file__), "--stem", stem, "--lock", lock,
                              "--arm", repr(arm), "--pid", str(pid), "--inner"], cwd=REPO, env=env))
