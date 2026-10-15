"""Step 3 of Uzayr's decision (DECISION_1p0.md): why the A2-rotation walk (participant_PA6_walk, pass 11) switches at
1.0 s and not at 0.75 s. Development data only; the decision is not changed.

    python3 runs/head_offset_2026-10-14/switch_explain.py --arm 1.0

The recording is replayed by the head-offset harness (ho_harness.build_session and dot_harness.feed), with
`switching.decide_walk` wrapped in this process only: after each call on the walk's lock line (B_rev), every decision frame
in the walk's span is re-read with decide_walk's own quantities (the lead over the drawn line, the radius distance from the
marker's drawn position to the best line's state, the drawn marker's furthest arc against the final-zone limit), so the
condition that differs between the arms is named from the code, not assumed. Output: switch_explain_<arm>.json.

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
ROT, STEM, PID, T0, T1 = "A2", "participant_PA6_walk", 11, 20637.0, 20647.0


def main(arm: float) -> int:
    import ho_harness as H
    sys.path.insert(0, H.DOT)
    opened = {}
    H.install_guard(opened)
    H.register()
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    import pipeline.constrained.switching as SW
    from pipeline.constrained.render_display import xy_of
    from dot_harness import APP_VARIANT, feed
    from pipeline.live.final_model import _components
    orig = SW.decide_walk
    calls = []

    def wrapped(lock_line, decs, adj, theta, st, dots_lock, dots_for_line, radius=None, max_switches=SW.MAX_SWITCHES,
                final_m=SW.FINAL_M):
        res = orig(lock_line, decs, adj, theta, st, dots_lock, dots_for_line, radius=radius, max_switches=max_switches,
                   final_m=final_m)
        xs = [float(d["x"]) for d in decs]
        if lock_line == "B_rev" and xs and T0 <= xs[0] <= T1:
            fr = [(float(x), p) for x, p in dots_lock if p is not None]
            fx = np.asarray([x for x, _p in fr], float)
            L = SW.line_length(st, lock_line)
            arcs = np.maximum.accumulate([SW.arc_along(st, lock_line, p) for _x, p in fr]) if fr else []
            rows = []
            for d in decs:
                x = float(d["x"])
                n_up = int(np.searchsorted(fx, x + 1e-9, side="right"))
                if n_up == 0:
                    continue
                tot = {nm: d["raw"][nm] + float((adj or {}).get(nm, 0.0)) for nm in d["raw"]}
                best = max(tot, key=tot.get)
                dot_now = fr[n_up - 1][1]
                q = xy_of(st, d["end"][best]) if best != lock_line else None
                rows.append({"x": x, "x_minus_press_s": round(x - 20637.669736791, 4), "best": best,
                             "lead_nats": float(tot[best] - tot[lock_line]), "theta": float(theta),
                             "dot_now_xy": [float(dot_now[0]), float(dot_now[1])],
                             "radius_dist_m": (float(np.hypot(q[0] - dot_now[0], q[1] - dot_now[1])) if q is not None else None),
                             "radius_m": radius, "dot_max_arc_m": float(arcs[n_up - 1]), "final_zone_from_m": float(L - final_m),
                             "in_final_zone": bool(float(arcs[n_up - 1]) >= L - final_m)})
            calls.append({"n_decisions": len(decs), "switches": [{"x": s["x"], "old": s["old"], "new": s["new"]}
                                                                for s in res["switches"]],
                          "disabled_final_m_at": res["disabled_final_m_at"], "rows": rows})
        return res
    SW.decide_walk = wrapped
    comps = _components(H.CELLS[ROT], APP_VARIANT)
    s, sdir, _held = H.build_session(ROT, STEM, arm, comps)
    feed(s, sdir, STEM)
    out = {"rotation": ROT, "stem": STEM, "pid": PID, "arm_head_offset_s": arm, "n_calls": len(calls),
           "last_call": calls[-1] if calls else None,
           "first_call_with_a_switch": next((c for c in calls if c["switches"]), None)}
    json.dump(out, open(J(HERE, f"switch_explain_{arm:g}.json"), "w", encoding="utf-8"), indent=1, default=float)
    print(json.dumps({"arm": arm, "calls": len(calls), "last_switches": out["last_call"]["switches"] if calls else None}))
    return 0


if __name__ == "__main__":
    a = float(sys.argv[sys.argv.index("--arm") + 1])
    if "--inner" in sys.argv:
        sys.exit(main(a))
    import subprocess
    sys.path.insert(0, REPO)
    import ho_harness as H
    H.register()
    from pipeline.live.final_model import _env
    env = dict(_env(H.CELLS[ROT]), OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", VECLIB_MAXIMUM_THREADS="1")
    env.pop("PD_PACE_MEAN", None)
    env.pop("PD_PACE_SD", None)
    sys.exit(subprocess.call(["nice", "-n", "10", sys.executable, os.path.abspath(__file__), "--arm", repr(a), "--inner"],
                             cwd=REPO, env=env))
