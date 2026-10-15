"""The dot side's measures on the app's replay logs, and the five stage rules (PREREG_DOT.md section 4; POA_DOT.md E4).

Every measure reads a replay log (`app_replay.Logger`'s rows) beside the recording's ground-truth sidecar, as
`pipeline.live.app_score` does; the truth a frame is scored against is the truth at frame time minus 2.0 s (V1). Per
rotation figures are combined with the weights (2 B1 + A2 + A1) / 4; intervals are a 95 % percentile bootstrap, 1,000
draws, seed 0, walks resampled within each rotation.

Pure functions only: nothing here runs the app or writes a file.
"""

from __future__ import annotations

import json
import os

import numpy as np

LATENCY_S = 2.0
KEY = 1e-4
WEIGHTS = {"B1": 2.0, "A2": 1.0, "A1": 1.0}
SLIDE_S = 0.5                       #: switching.SLIDE_S, the slide between lines (checked in the tests)


# ------------------------------------------------------------------------------------------ the log, per walk

def truth_at(p: dict, t: float):
    at, ac = p["anchor_times"], p["anchor_coords"]
    if not at[0] - 1e-9 <= t <= at[-1] + 1e-9:
        return None
    return np.array([np.interp(t, at, [c[0] for c in ac]), np.interp(t, at, [c[1] for c in ac])])


def walks(log_rows: list, gt: dict) -> dict:
    """{pid: everything one walk's measures read}: its truth, press, lock (line, t_dec0), committed line, switches and
    its dot frames in time order."""
    out = {}
    press = {r["pid"]: float(r["t"]) for r in log_rows if r["kind"] == "press"}
    lock = {r["pid"]: r for r in log_rows if r["kind"] == "lock"}
    com = {r["pid"]: r["line"] for r in log_rows if r["kind"] == "committed"}
    margin = {r["pid"]: float(r["min_margin_s"]) for r in log_rows if r["kind"] == "margin"}
    sw = {}
    for r in log_rows:
        if r["kind"] == "switch":
            sw.setdefault(r["pid"], []).append(r)
    dots = {}
    for r in log_rows:
        if r["kind"] == "dot":
            dots.setdefault(r["pid"], []).append(r)
    for pid, p in gt.items():
        L = lock.get(pid)
        out[pid] = {"pid": pid, "true": p["path_name"], "truth": p, "press": press.get(pid),
                    "lock": L["line"] if L else None, "t_dec0": (float(L["t_dec0"]) if L and L.get("t_dec0") is not None
                                                                else None),
                    "committed": com.get(pid), "margin": margin.get(pid),
                    "switches": sorted(sw.get(pid, []), key=lambda r: r["x"]),
                    "dots": sorted(dots.get(pid, []), key=lambda r: r["x"])}
    return out


def load(log_path: str, gt_path: str) -> dict:
    rows = [json.loads(ln) for ln in open(log_path, encoding="utf-8")]
    with open(gt_path, encoding="utf-8") as f:
        gt = {int(p["pass_id"]): p for p in json.load(f)["passes"]}
    return walks(rows, gt)


def decoded_frames(w: dict) -> list:
    """The frames from the first decoded frame on (app_score's: the park and the anchor span excluded, rule 2b)."""
    if w["t_dec0"] is None:
        return []
    return [d for d in w["dots"] if float(d["x"]) >= w["t_dec0"] - KEY]


def from_press_frames(w: dict) -> list:
    """The frames from press + 2.0 s on (dot_from_press's: the anchor span included, the park excluded)."""
    if w["press"] is None:
        return []
    return [d for d in w["dots"] if float(d["x"]) >= w["press"] + LATENCY_S - KEY]


def errors(w: dict, frames: list) -> list:
    out = []
    for d in frames:
        g = truth_at(w["truth"], float(d["x"]) - LATENCY_S)
        if g is not None:
            out.append(float(np.hypot(*(np.asarray(d["xy"], float) - g))))
    return out


def signed_offsets(w: dict, frames: list) -> list:
    """The dot minus the truth along the TRUE line's direction: positive, the dot is ahead."""
    a0 = np.asarray(w["truth"]["anchor_coords"][0], float)
    a1 = np.asarray(w["truth"]["anchor_coords"][-1], float)
    u = (a1 - a0) / max(float(np.hypot(*(a1 - a0))), 1e-9)
    out = []
    for d in frames:
        g = truth_at(w["truth"], float(d["x"]) - LATENCY_S)
        if g is not None:
            out.append(float((np.asarray(d["xy"], float) - a0) @ u - (g - a0) @ u))
    return out


def jumps(frames: list, over_m: float = 0.5) -> int:
    xy = [np.asarray(d["xy"], float) for d in frames]
    return int(sum(1 for a, b in zip(xy, xy[1:]) if float(np.hypot(*(b - a))) > over_m))


def state_arc(st, line: str):
    """s2_display.arc_of_xy for one line, as r3_prior and the substitution test read it: the arc of the NEAREST state
    on the chain (0.25 m spacing)."""
    a, b = st.slice_of[line]
    p = np.asarray(st.xy, float)[a:b]
    s = np.asarray(st.s_of, float)[a:b]
    return lambda xy: float(s[int(np.argmin(np.linalg.norm(p - np.asarray(xy, float)[None, :], axis=1)))])


def motion(w: dict, frames: list, arc) -> dict:
    """r3_prior.motion_stats on the app's frames: frame-to-frame displacement, excess motion (the dot moved more than
    the truth moved plus 0.5 m, the truth at frame time minus 2.0 s) and backwards steps in along-line arc on the
    locked line (`arc`: xy -> metres, state_arc's in the runs)."""
    disp, excess, back, b25, b50 = [], 0, 0.0, 0, 0
    prev = None
    for d in frames:
        p, x = np.asarray(d["xy"], float), float(d["x"])
        if prev is not None:
            pp, px = prev
            dd = float(np.hypot(*(p - pp)))
            disp.append(dd)
            g0, g1 = truth_at(w["truth"], px - LATENCY_S), truth_at(w["truth"], x - LATENCY_S)
            if g0 is not None and g1 is not None:
                excess += int(dd > float(np.hypot(*(g1 - g0))) + 0.5)
            step_back = arc(pp) - arc(p)
            back = max(back, step_back)
            b25 += int(step_back > 0.25 + 1e-9)
            b50 += int(step_back > 0.5 + 1e-9)
        prev = (p, x)
    return {"displacements": disp, "excess": excess, "largest_back": back, "back25": b25, "back50": b50}


def named_line(w: dict, x: float) -> str:
    """The line the display names at frame x: the lock, then each switch's new line from its frame on."""
    ln = w["lock"]
    for s in w["switches"]:
        if x >= float(s["x"]) - 1e-9:
            ln = s["new"]
    return ln


# ------------------------------------------------------------------------------------------ bootstrap

def weighted_mean(per_rot: dict) -> float:
    W = sum(WEIGHTS[r] for r in per_rot)
    return sum(WEIGHTS[r] * per_rot[r] for r in per_rot) / W


def boot_weighted(vals: dict, stat=np.mean, n_boot: int = 1000, seed: int = 0) -> list:
    """95 % interval of the weighted statistic, walks (the units in vals[rot]) resampled within each rotation."""
    rng = np.random.default_rng(seed)
    W = sum(WEIGHTS[r] for r in vals)
    acc = np.zeros(n_boot)
    for r in sorted(vals):
        v = np.asarray(vals[r], float)
        idx = rng.integers(0, len(v), size=(n_boot, len(v)))
        acc += WEIGHTS[r] * np.array([stat(v[i]) for i in idx])
    acc /= W
    return [float(np.percentile(acc, 2.5)), float(np.percentile(acc, 97.5))]


def boot_weighted_pooled(per_walk: dict, fn, n_boot: int = 1000, seed: int = 0) -> list:
    """As boot_weighted for a statistic of POOLED frames: per_walk[rot] is a list of per-walk frame lists, the walks
    are resampled within each rotation and fn is applied to the concatenation of the drawn walks' frames."""
    rng = np.random.default_rng(seed)
    W = sum(WEIGHTS[r] for r in per_walk)
    acc = np.zeros(n_boot)
    for r in sorted(per_walk):
        ws = per_walk[r]
        idx = rng.integers(0, len(ws), size=(n_boot, len(ws)))
        acc += WEIGHTS[r] * np.array([fn([e for j in row for e in ws[j]]) for row in idx])
    acc /= W
    return [float(np.percentile(acc, 2.5)), float(np.percentile(acc, 97.5))]


# ------------------------------------------------------------------------------------------ per arm figures

def within(errs: list) -> float:
    return 100.0 * float(np.mean(np.asarray(errs) <= 0.5)) if errs else float("nan")


def arm_figures(per_rot_walks: dict, arc_of) -> dict:
    """Every figure the five stages read, for one arm: per_rot_walks[rot] = {key: walk} over the rotation's recordings."""
    out = {"per_rotation": {}}
    for rot, ws in per_rot_walks.items():
        ok = [w for w in ws.values() if w["lock"] == w["true"]]
        e_all = [errors(w, decoded_frames(w)) for w in ws.values()]
        e_ok_dec = [errors(w, decoded_frames(w)) for w in ok]
        e_ok_press = [errors(w, from_press_frames(w)) for w in ok]
        mo = [motion(w, decoded_frames(w), arc_of(w["lock"])) for w in ws.values() if w["lock"]]
        disp = [d for m in mo for d in m["displacements"]]
        n_disp = len(disp)
        out["per_rotation"][rot] = {
            "n_walks": len(ws), "n_lock_correct": len(ok),
            "min_margin_s": min((w["margin"] for w in ws.values() if w["margin"] is not None), default=None),
            "jumps_over_0_5m": int(sum(jumps(decoded_frames(w)) for w in ws.values())),
            "mean_error_all_m": float(np.mean([e for v in e_all for e in v])) if any(e_all) else None,
            "median_error_from_press_ok_m": (float(np.median([e for v in e_ok_press for e in v]))
                                             if any(e_ok_press) else None),
            "within_0_5m_ok_pct": within([e for v in e_ok_dec for e in v]),
            "signed_offset_ok_mean_m": (float(np.mean([s for w in ok for s in signed_offsets(w, decoded_frames(w))]))
                                        if ok else None),
            "displacement_p95_m": float(np.percentile(disp, 95)) if disp else None,
            "excess_frames": int(sum(m["excess"] for m in mo)), "n_displacements": n_disp,
            "excess_pct": (100.0 * sum(m["excess"] for m in mo) / n_disp) if n_disp else None,
            "back50_per_walk": (sum(m["back50"] for m in mo) / len(mo)) if mo else None,
            "n_switches": int(sum(len(w["switches"]) for w in ws.values())),
            "_e_all": e_all, "_e_ok_dec": e_ok_dec, "_e_ok_press": e_ok_press}
    R = out["per_rotation"]
    for k in ("mean_error_all_m", "median_error_from_press_ok_m", "within_0_5m_ok_pct", "signed_offset_ok_mean_m",
              "displacement_p95_m", "excess_pct", "back50_per_walk"):
        vals = {r: v[k] for r, v in R.items() if v[k] is not None}
        out[k] = weighted_mean(vals) if len(vals) == len(R) else None
    out["excess_frames_weighted"] = weighted_mean({r: v["excess_frames"] for r, v in R.items()})
    out["jumps_over_0_5m"] = int(sum(v["jumps_over_0_5m"] for v in R.values()))
    out["min_margin_s"] = min((v["min_margin_s"] for v in R.values() if v["min_margin_s"] is not None), default=None)
    out["n_switches"] = int(sum(v["n_switches"] for v in R.values()))
    return out


# ------------------------------------------------------------------------------------------ the stage rules

def stage1(figs: dict, gates: dict) -> dict:
    """Head choice: arms 'centre_labelled' and 'DISP_END'. gates[arm] = {'i': bool, 'iii': bool} (offline); (iv) is the
    app's margin. Ranking: zero jumps over 0.5 m first, then the lowest weighted mean error (all walks, from the first
    decoded frame). No arm passing keeps the shipped head (DISP_END) and its label."""
    rows = {}
    for arm, f in figs.items():
        g_iv = f["min_margin_s"] is not None and f["min_margin_s"] >= 0.0
        rows[arm] = {"i_dwell": bool(gates[arm]["i"]), "iii_substitution": bool(gates[arm]["iii"]), "iv_causality": g_iv,
                     "passes": bool(gates[arm]["i"] and gates[arm]["iii"] and g_iv),
                     "jumps_over_0_5m": f["jumps_over_0_5m"], "mean_error_all_m": f["mean_error_all_m"]}
    ok = [a for a in rows if rows[a]["passes"]]
    if not ok:
        return {"rows": rows, "chosen": "DISP_END", "no_arm_passed": True}
    best = min(ok, key=lambda a: (rows[a]["jumps_over_0_5m"] > 0, rows[a]["mean_error_all_m"]))
    return {"rows": rows, "chosen": best, "no_arm_passed": False}


def stage2(figs: dict) -> dict:
    """The prior: arms 'f0.00' ... 'f1.00'. THE RULE AS LAST APPLIED selects: eligible = excess motion under 0.5 % of
    frames and no switch; then the chain 0.50, 0.25, 0.00, the first eligible one with at most 1.0 backwards step over
    0.5 m per walk; none, 0.00. THE ORIGINAL RULE, shown: the weakest arm whose p95 displacement and excess-motion count
    are no worse than 0.00's."""
    elig = {a: bool(f["excess_pct"] is not None and f["excess_pct"] < 0.5 and f["n_switches"] == 0)
            for a, f in figs.items()}
    chain = ["f0.50", "f0.25", "f0.00"]
    chosen, checks = "f0.00", {}
    for a in chain:
        per = figs[a]["back50_per_walk"]
        ok = bool(elig[a] and per is not None and per <= 1.0)
        checks[a] = {"eligible": elig[a], "back50_per_walk": per, "passes": ok}
        if ok:
            chosen = a
            break
    base = figs["f0.00"]
    weakest_first = sorted(figs, key=lambda a: -float(a[1:]))
    original = next((a for a in weakest_first
                     if figs[a]["displacement_p95_m"] <= base["displacement_p95_m"] + 1e-12
                     and figs[a]["excess_frames_weighted"] <= base["excess_frames_weighted"] + 1e-12), "f0.00")
    return {"eligible": elig, "chain_checks": checks, "chosen": chosen, "original_rule_would_choose": original}


def stage3(figs: dict) -> dict:
    """The head offset: arms 'o0.75' ... 'o0': the lowest weighted median error over correct-lock walks, frames from
    press + 2.0 s; differences within 0.005 m are ties, to the larger offset."""
    E = {a: f["median_error_from_press_ok_m"] for a, f in figs.items()}
    lo = min(E.values())
    tied = [a for a in E if E[a] <= lo + 0.005 + 1e-12]
    chosen = max(tied, key=lambda a: float(a[1:]))
    return {"E": E, "tied_with_lowest": tied, "chosen": chosen}


def stage4(figs: dict, intervals: dict) -> dict:
    """SHIFT_W: arms 's0' ... 's1': the highest weighted within-0.5 m share over correct-lock walks (frames from the
    first decoded frame); ties (within 0.01 points) to the value closest to 0.50. Shown: the old tie-break, among the
    arms whose point estimate lies inside the best arm's 95 % interval, the one whose mean signed offset is closest to
    zero."""
    P = {a: f["within_0_5m_ok_pct"] for a, f in figs.items()}
    hi = max(P.values())
    tied = [a for a in P if P[a] >= hi - 0.01 - 1e-12]
    chosen = min(tied, key=lambda a: (abs(float(a[1:]) - 0.5), float(a[1:])))
    best = max(P, key=lambda a: (P[a], -abs(float(a[1:]) - 0.5)))
    lo_b, hi_b = intervals[best]
    inside = [a for a in P if lo_b - 1e-12 <= P[a] <= hi_b + 1e-12]
    old = min(inside, key=lambda a: abs(figs[a]["signed_offset_ok_mean_m"]))
    return {"P": P, "chosen": chosen, "best_interval": [lo_b, hi_b], "inside_best_interval": inside,
            "old_tie_break_would_choose": old}


def switch_walk(w: dict, w_off: dict) -> dict:
    """e2's quantities for one walk: time on the correct line (frames from press + 2.0 s whose named line is true,
    x 0.1 s) for the arm and for switching off, the switch events by kind, and the line named at the walk's end."""
    fr = from_press_frames(w)
    fr_off = from_press_frames(w_off)
    toc = 0.1 * sum(1 for d in fr if named_line(w, float(d["x"])) == w["true"])
    toc_off = 0.1 * sum(1 for d in fr_off if named_line(w_off, float(d["x"])) == w_off["true"])
    kinds = {"W2R": 0, "R2W": 0, "W2W": 0}
    big = 0
    for s in w["switches"]:
        old_ok, new_ok = s["old"] == w["true"], s["new"] == w["true"]
        if new_ok and not old_ok:
            kinds["W2R"] += 1
        elif old_ok and not new_ok:
            kinds["R2W"] += 1
        elif not old_ok and not new_ok:
            kinds["W2W"] += 1
        xs = float(s["x"])
        bef = [d for d in w["dots"] if float(d["x"]) < xs - 1e-9]
        aft = [d for d in w["dots"] if float(d["x"]) >= xs + SLIDE_S - 1e-9]
        if bef and aft and float(np.hypot(*(np.asarray(aft[0]["xy"], float) - np.asarray(bef[-1]["xy"], float)))) > 1.5:
            big += 1
    end_line = named_line(w, float(fr[-1]["x"])) if fr else w["lock"]
    return {"toc_delta_s": toc - toc_off, "kinds": kinds, "n_switches": len(w["switches"]), "jumps_over_1_5m": big,
            "end_on_committed": bool(end_line == w["committed"])}


def stage5(per_arm: dict) -> dict:
    """The switch arm: per_arm[arm][rot] = [switch_walk rows]. Qualify: weighted mean toc delta > 0 AND its 95 %
    interval above zero AND pooled W2R > R2W. Then the highest end-on-committed agreement; within 3 walks of the top,
    fewer switch events, then fewer jumps over 1.5 m. None qualifies: switching off."""
    rows = {}
    for arm, rots in per_arm.items():
        d = {r: [x["toc_delta_s"] for x in v] for r, v in rots.items()}
        mean = weighted_mean({r: float(np.mean(v)) for r, v in d.items()})
        ci = boot_weighted(d)
        k = {q: int(sum(x["kinds"][q] for v in rots.values() for x in v)) for q in ("W2R", "R2W", "W2W")}
        rows[arm] = {"toc_delta_mean_s": mean, "toc_ci95": ci, **k,
                     "qualifies": bool(mean > 0 and ci[0] > 0 and k["W2R"] > k["R2W"]),
                     "end_on_committed": int(sum(x["end_on_committed"] for v in rots.values() for x in v)),
                     "switch_events": int(sum(x["n_switches"] for v in rots.values() for x in v)),
                     "jumps_over_1_5m": int(sum(x["jumps_over_1_5m"] for v in rots.values() for x in v))}
    q = [a for a in rows if rows[a]["qualifies"]]
    if not q:
        return {"rows": rows, "chosen": "off", "none_qualified": True}
    top = max(rows[a]["end_on_committed"] for a in q)
    band = [a for a in q if rows[a]["end_on_committed"] >= top - 3]
    chosen = min(band, key=lambda a: (rows[a]["switch_events"], rows[a]["jumps_over_1_5m"], a))
    return {"rows": rows, "band": band, "chosen": chosen, "none_qualified": False}
