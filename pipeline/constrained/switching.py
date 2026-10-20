# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: MID-WALK SWITCHING as a DISPLAY decision.

from __future__ import annotations

import numpy as np

THETAS = (0.5, 1.0, 1.5, 2.0, 3.0)
PERSIST_STEPS = 2
MAX_SWITCHES = 1
FINAL_M = 1.0
SLIDE_S = 0.5
RADIUS_M = 1.5
LATENCY_S = 2.0
WINDOW_S = 2.0
STRIDE_S = 0.5
ENTRY_WINDOW_M = 1.0
NEG_BIG = -1.0e9



# Function line arcs.
def line_arcs(st, line: str):
    a, b = st.slice_of[line]
    return np.asarray(st.xy, float)[a:b], np.asarray(st.s_of, float)[a:b]


# Metres of arc from the line's entry to the point's projection on the line's polyline.
def arc_along(st, line: str, xy) -> float:
    P, S = line_arcs(st, line)
    q = np.asarray(xy, float)
    best, arc = np.inf, 0.0
    for i in range(len(P) - 1):
        d = P[i + 1] - P[i]
        L2 = float(d @ d)
        f = 0.0 if L2 <= 0 else float(np.clip((q - P[i]) @ d / L2, 0.0, 1.0))
        foot = P[i] + f * d
        dist = float(np.hypot(*(q - foot)))
        if dist < best:
            best, arc = dist, float(S[i] + f * (S[i + 1] - S[i]))
    return arc - float(S[0])


# Function line length.
def line_length(st, line: str) -> float:
    _P, S = line_arcs(st, line)
    return float(S[-1] - S[0])



# X_k = press + 2.0 + k * 0.5 s, k >= 1, while x_k < end press + 2.0 (video time).
def decision_frames(press_start: float, press_end: float):
    out, k = [], 1
    while True:
        x = float(press_start) + LATENCY_S + k * STRIDE_S
        if x >= float(press_end) + LATENCY_S - 1e-9:
            return out
        out.append(x)
        k += 1


# Each line's within-chain Viterbi total over the causal windows, prior withheld, and its END STATE (a...
class Scorer:

    # Sets up the object.
    def __init__(self, st, cfg, transit):
        from pipeline.constrained.decoder import transition_matrix
        from pipeline.constrained.decoder2 import Space
        self.st = st
        self.sp = Space(st, cfg)
        self.lT_chains = transition_matrix(st, "tight", with_null=False)
        from pipeline.constrained.decoder import decoded_paths
        names = np.asarray(decoded_paths(np.arange(self.sp.N), st)).astype(str)
        self.on_chain = names != ""
        self.first_state = np.zeros(self.sp.N, bool)
        for nm in st.names:
            self.first_state[st.slice_of[nm][0]] = True

    # Function stack.
    def stack(self, e_path, ge, ne):
        from pipeline.constrained.decoder2 import stack2
        return stack2(e_path, ge, ne, self.sp)

    # Function start.
    def start(self, E, lo):
        from pipeline.constrained.night_arms import entry_start
        sl = np.asarray(entry_start("soft", E, self.st, self.sp, lo, self.on_chain,
                                    self.first_state), float).copy()
        s_arr = np.asarray(self.st.s_of, float)
        for nm in self.st.names:
            a, b = self.st.slice_of[nm]
            far = a + np.flatnonzero((s_arr[a:b] - s_arr[a]) > ENTRY_WINDOW_M + 1e-9)
            if len(far):
                sl[far] = NEG_BIG
        return sl

    # Function totals and ends.
    def totals_and_ends(self, E, lo, hi, sl):
        from pipeline.constrained.decoder import viterbi
        tot, end = {}, {}
        for nm in self.st.names:
            a, b = self.st.slice_of[nm]
            sub = np.asarray(E[lo:hi + 1, a:b], float)
            ls = np.asarray(sl[a:b], float)
            s = viterbi(sub, self.lT_chains[a:b, a:b], log_start=ls)
            tot[nm] = float(sub[np.arange(len(s)), s].sum()) + float(ls[int(s[0])])
            end[nm] = int(a + s[-1])
        return tot, end

    # One entry per decision frame, reading ONLY windows with t_start + WINDOW_S <= x.
    def decisions(self, E, t, lo, sl, frames):
        t = np.asarray(t, float)
        out = []
        for x in frames:
            ok = np.flatnonzero(t + WINDOW_S <= x + 1e-9)
            w = int(ok[-1]) if len(ok) else -1
            if w <= lo:
                continue
            tot, end = self.totals_and_ends(E, lo, w, sl)
            out.append({"x": float(x), "w": w, "evidence_bound_s": float(t[w] + WINDOW_S - x),
                        "raw": tot, "end": end})
        return out



# The one switch, or None.
def decide(lock_line: str, decs, adj, theta: float, st, dot_frames, radius=None):
    from pipeline.constrained.render_display import xy_of
    L = line_length(st, lock_line)
    fr = [(float(x), p) for x, p in dot_frames if p is not None]
    cummax = np.maximum.accumulate([arc_along(st, lock_line, p) for _x, p in fr]) if fr else []
    fx = np.asarray([x for x, _p in fr], float)
    streak_line, streak, leads = None, 0, []
    for d in decs:
        x = d["x"]
        n_up = int(np.searchsorted(fx, x + 1e-9, side="right"))
        if n_up == 0:
            continue
        upto_last = fr[n_up - 1][1]
        max_arc = float(cummax[n_up - 1])
        if max_arc >= L - FINAL_M:
            return {"switched": False, "disabled_final_m_at": x, "leads": leads}
        tot = {nm: d["raw"][nm] + float((adj or {}).get(nm, 0.0)) for nm in d["raw"]}
        best = max(tot, key=tot.get)
        lead = float(tot[best] - tot[lock_line])
        near = True
        if radius is not None and best != lock_line:
            q = xy_of(st, d["end"][best])
            near = bool(float(np.hypot(q[0] - upto_last[0], q[1] - upto_last[1])) <= radius)
        qualifies = best != lock_line and lead > theta and near
        leads.append({"x": x, "best": best, "lead": lead, "qualifies": bool(qualifies),
                      "dot_max_arc_m": float(max_arc), "evidence_bound_s": d["evidence_bound_s"]})
        if qualifies:
            streak = streak + 1 if best == streak_line else 1
            streak_line = best
        else:
            streak_line, streak = None, 0
        if streak >= PERSIST_STEPS:
            return {"switched": True, "x": x, "old": lock_line, "new": best, "w": d["w"],
                    "evidence_bound_s": d["evidence_bound_s"], "lead": lead,
                    "persist": [q for q in leads[-PERSIST_STEPS:]], "dot_max_arc_m": float(max_arc),
                    "line_length_m": L, "leads": leads}
    return {"switched": False, "leads": leads}


# The line the display NAMES at frame x: the new line from the switch frame, marked there.
def named_line_at(lock_line: str, sw, x: float) -> str:
    if sw and sw.get("switched") and x >= sw["x"] - 1e-9:
        return sw["new"]
    return lock_line



# The dot on [x_s, x_s + SLIDE_S): the straight segment p_old -> q_new by elapsed fraction of the fixed...
def slide(p_old, q_new, x_s: float, frames):
    out = []
    p0, q1 = np.asarray(p_old, float), np.asarray(q_new, float)
    tot = float(np.hypot(*(q1 - p0)))
    for x in frames:
        if not (x_s - 1e-9 <= x < x_s + SLIDE_S - 1e-9):
            continue
        f = float(np.clip((x - x_s) / SLIDE_S, 0.0, 1.0))
        p = p0 + (q1 - p0) * f
        off = abs(float(np.hypot(*(p - p0))) + float(np.hypot(*(q1 - p))) - tot) > 1e-6
        out.append((float(x), (float(p[0]), float(p[1])), bool(off)))
    return out



# Up to max_switches switches in one walk.
def decide_walk(lock_line: str, decs, adj, theta: float, st, dots_lock, dots_for_line,
                radius=None, max_switches: int = MAX_SWITCHES, final_m: float = FINAL_M):
    from pipeline.constrained.render_display import xy_of

    # Function segment.
    def segment(dots):
        fr = [(float(x), p) for x, p in dots if p is not None]
        return fr, np.asarray([x for x, _p in fr], float)

    line, drawn_lines = lock_line, {lock_line}
    L = line_length(st, line)
    fr, fx = segment(dots_lock)
    arcs = None
    hist, leads, disabled_at = [], [], None
    streak_line, streak = None, 0
    for d in decs:
        x = d["x"]
        if hist and x < hist[-1]["x"] + SLIDE_S - 1e-9:
            continue
        n_up = int(np.searchsorted(fx, x + 1e-9, side="right"))
        if n_up == 0:
            continue
        if arcs is None:
            arcs = np.maximum.accumulate([arc_along(st, line, p) for _x, p in fr]) if fr else []
        max_arc, dot_now = float(arcs[n_up - 1]), fr[n_up - 1][1]
        if max_arc >= L - final_m:
            disabled_at = x
            break
        tot = {nm: d["raw"][nm] + float((adj or {}).get(nm, 0.0)) for nm in d["raw"]}
        best = max(tot, key=tot.get)
        lead = float(tot[best] - tot[line])
        near = True
        if radius is not None and best != line:
            q = xy_of(st, d["end"][best])
            near = bool(float(np.hypot(q[0] - dot_now[0], q[1] - dot_now[1])) <= radius)
        qualifies = best not in drawn_lines and lead > theta and near
        leads.append({"x": x, "line": line, "best": best, "lead": lead, "qualifies": bool(qualifies),
                      "dot_max_arc_m": max_arc, "evidence_bound_s": d["evidence_bound_s"]})
        if qualifies:
            streak = streak + 1 if best == streak_line else 1
            streak_line = best
        else:
            streak_line, streak = None, 0
        if streak >= PERSIST_STEPS:
            hist.append({"k": len(hist) + 1, "switched": True, "x": x, "old": line, "new": best,
                         "w": d["w"], "evidence_bound_s": d["evidence_bound_s"], "lead": lead,
                         "persist": leads[-PERSIST_STEPS:], "dot_max_arc_m": max_arc,
                         "line_length_m": L, "final_m": final_m})
            if len(hist) >= max_switches:
                break
            line = best
            drawn_lines.add(best)
            L = line_length(st, line)
            fr, fx = segment(dots_for_line(best, x + SLIDE_S))
            arcs = None
            streak_line, streak = None, 0
    return {"switches": hist, "disabled_final_m_at": disabled_at, "leads": leads}


# The line the display NAMES at frame x: each switch's new line from its own frame.
def named_line_at_multi(lock_line: str, switches, x: float) -> str:
    line = lock_line
    for s in switches:
        if x >= s["x"] - 1e-9:
            line = s["new"]
    return line
