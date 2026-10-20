# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The display model: what the red dot does, and the one rule it obeys on every frame.

from __future__ import annotations

import numpy as np

SWITCH_CAP_M_S = 2.0
CENTRE = (2.5, 2.5)



# The decoded position at each display step, from a fixed-lag Viterbi backtrace.
def fixed_lag_path(e_stacked, lT, st_lo, st, lo, hi, lag_w):
    from pipeline.constrained.decoder import viterbi
    n = hi - lo + 1
    out, held = [], 0
    last_on = None
    for i in range(n):
        end = min(hi, lo + i + lag_w)
        s = viterbi(e_stacked[lo:end + 1], lT, log_start=st_lo)
        k = int(s[i]) if i < len(s) else int(s[-1])
        on_chain = k < st.n_states
        if on_chain:
            last_on = k
        elif last_on is not None:
            held += 1
            k = last_on
        else:
            held += 1
        name = chain_of(st, k) if k < st.n_states else ""
        out.append({"step": i, "window": lo + i, "evidence_window": int(end), "state": int(k),
                    "line": name, "on_chain": bool(on_chain)})
    return out, held


# The drawn path AFTER the lock: a fixed-lag Viterbi restricted to ONE chain.
def locked_chain_path(e_res, lT_chains, st, lo, hi, lag_w, chain, log_start=None):
    from pipeline.constrained.decoder import viterbi
    a, b = st.slice_of[chain]
    sub_T = lT_chains[a:b, a:b]
    e_sub = np.asarray(e_res)[:, a:b]
    ls = None
    if log_start is not None:
        ls = np.asarray(log_start, float)[a:b].copy()
        m = float(np.max(ls[np.isfinite(ls)])) if np.isfinite(ls).any() else 0.0
        ls = ls - m
    out = []
    n = hi - lo + 1
    for i in range(n):
        end = min(hi, lo + i + lag_w)
        s_ = viterbi(e_sub[lo:end + 1], sub_T, log_start=ls)
        k = int(s_[i]) if i < len(s_) else int(s_[-1])
        out.append({"step": i, "window": lo + i, "evidence_window": int(end), "state": int(a + k),
                    "line": chain, "on_chain": True})
    return out


# Function chain of.
def chain_of(st, state_idx):
    for nm in st.names:
        a, b = st.slice_of[nm]
        if a <= state_idx < b:
            return nm
    return ""


# Function xy of.
def xy_of(st, state_idx):
    from pipeline.constrained.decoder import decoded_xy
    q = decoded_xy(np.array([int(state_idx)]), st)
    return (float(q[0][0]), float(q[0][1]))


# Where the dot jumps to at the start press: the best ON-CHAIN state under the entry prior.
def entry_position(e_stacked, st_lo, st, lo):
    v = np.asarray(st_lo, float)[:st.n_states] + np.asarray(e_stacked[lo], float)[:st.n_states]
    if not np.isfinite(v).any():
        return None, ""
    k = int(np.nanargmax(np.where(np.isfinite(v), v, -np.inf)))
    return k, chain_of(st, k)


# Backward steps ALONG A LINE.
def monotonicity_violations(path, st):
    bad = 0
    for a, b in zip(path, path[1:]):
        if a["line"] and a["line"] == b["line"] and b["state"] < a["state"]:
            bad += 1
    return bad


# The same census on the OLD per-window argmax display, which had no continuity constraint.
def backward_steps(names, states):
    bad = 0
    for i in range(1, len(names)):
        if names[i] and names[i] == names[i - 1] and 0 <= states[i] < states[i - 1]:
            bad += 1
    return bad



# The drawn red position, frame by frame.
class Dot:

    # Sets up the object.
    def __init__(self, cap_m_s=SWITCH_CAP_M_S):
        self.cap = cap_m_s
        self.pos = CENTRE
        self.line = ""
        self.anchor = CENTRE
        self.target = CENTRE
        self.crossing = False
        self.arrivals = 0
        self.capped_frames = 0

    # Between walks the dot is parked at the room centre, the null state's own position.
    def park(self):
        self.pos = CENTRE
        self.line = ""
        self.anchor = self.target = CENTRE
        self.crossing = False

    # At the start press the dot jumps to the entry position.
    def jump_to_entry(self, xy, line):
        self.pos = tuple(xy)
        self.line = line
        self.anchor = self.target = tuple(xy)
        self.crossing = False

    # Advance one frame.
    def step(self, dt, dec_line, p_prev, p_now, frac):
        if p_now is None:
            return self.pos
        if self.line == dec_line and not self.crossing:
            a = p_prev if p_prev is not None else p_now
            self.anchor, self.target = tuple(a), tuple(p_now)
            f = float(np.clip(frac, 0.0, 1.0))
            self.pos = (a[0] + (p_now[0] - a[0]) * f, a[1] + (p_now[1] - a[1]) * f)
            return self.pos
        if not self.crossing:
            self.crossing = True
            if p_prev is not None:
                self.pos = tuple(p_prev)
                self.anchor = tuple(p_prev)
            else:
                self.anchor = tuple(self.pos)
        self.target = tuple(p_now)
        vx, vy = self.target[0] - self.pos[0], self.target[1] - self.pos[1]
        d = float(np.hypot(vx, vy))
        reach = self.cap * dt if self.cap is not None else d
        if d <= reach or d < 1e-9:
            self.pos = self.target
            self.line = dec_line
            self.crossing = False
            self.anchor = self.target
            self.arrivals += 1
        else:
            self.capped_frames += 1
            self.pos = (self.pos[0] + vx / d * reach, self.pos[1] + vy / d * reach)
        return self.pos



# THE ONE RULE, per frame.
def check_rule(drawn, anchor, target, latest_xy_set, tol=1e-6):
    if anchor is None or target is None:
        return "no segment: the dot was drawn without two decoded endpoints"
    if tuple(np.round(target, 6)) not in latest_xy_set:
        return f"target {target} is not a decoded position the decoder has produced"
    a, b, p = np.asarray(anchor, float), np.asarray(target, float), np.asarray(drawn, float)
    ab = b - a
    L2 = float(ab @ ab)
    if L2 < 1e-12:
        off = float(np.linalg.norm(p - a))
        return None if off <= 1e-3 else f"drawn {drawn} is {off:.4f} m from the single decoded point"
    t = float((p - a) @ ab / L2)
    if t < -1e-6 or t > 1.0 + 1e-6:
        return f"drawn {drawn} is off the segment at t={t:.4f}, so it is beyond a decoded endpoint"
    off = float(np.linalg.norm(p - (a + t * ab)))
    if off > 1e-3:
        return f"drawn {drawn} is {off:.4f} m off the straight segment between two decoded points"
    return None



# The acceptance number, at the DISPLAYED time so the display lag counts against it.
def on_screen_tracking(red, green, within_m=0.5, missing_is_a_miss=True):
    d, skipped, missing = [], 0, 0
    for r, g in zip(red, green):
        if g is None:
            skipped += 1
            continue
        if r is None:
            missing += 1
            if missing_is_a_miss:
                d.append(float("inf"))
            continue
        d.append(float(np.hypot(r[0] - g[0], r[1] - g[1])))
    if not d:
        return {"n_frames": 0, "n_skipped": skipped, "n_no_red_dot": missing,
                "within_pct": None, "mean_m": None}
    d = np.asarray(d, float)
    fin = d[np.isfinite(d)]
    return {"n_frames": int(len(d)), "n_skipped": int(skipped), "n_no_red_dot": int(missing),
            "within_pct": float(100.0 * np.mean(d <= within_m)),
            "mean_m": (float(np.mean(fin)) if len(fin) else None),
            "median_m": (float(np.median(fin)) if len(fin) else None),
            "mean_excludes_frames_with_no_dot": bool(missing and missing_is_a_miss),
            "within_m": within_m}



# One walk, frame by frame.
def simulate_walk(path, st, t_start, t_press, entry_xy, entry_line, stride, lag_w, fps,
                  cap, green_at, frames=None, lead=False, shift_w=0.0):
    pts = [xy_of(st, p["state"]) if p["state"] >= 0 else None for p in path]
    lines = [p["line"] for p in path]
    dot = Dot(cap_m_s=cap)
    dot.jump_to_entry(entry_xy, entry_line)
    decoded = {tuple(np.round(entry_xy, 6))}
    red, green, viol = [], [], []
    frames = np.arange(t_start, t_press, 1.0 / fps) if frames is None else np.asarray(frames, float)
    prev_tq = None
    for tq in frames:
        dt = (1.0 / fps) if prev_tq is None else float(tq - prev_tq)
        prev_tq = tq
        g = green_at(float(tq))
        green.append(g)
        raw = (tq - t_start) / stride - lag_w + shift_w
        i_max = int(np.floor(raw))
        if i_max < 0:
            red.append(dot.pos)
            continue
        i_max = min(i_max, len(pts) - 1)
        for j in range(i_max + 1):
            if pts[j] is not None:
                decoded.add(tuple(np.round(pts[j], 6)))
        if lead:
            p_prev = pts[i_max]
            p_now = pts[i_max + 1] if (i_max + 1) < len(pts) else pts[i_max]
            if p_now is not None:
                decoded.add(tuple(np.round(p_now, 6)))
        else:
            p_now = pts[i_max]
            p_prev = pts[i_max - 1] if i_max > 0 else entry_xy
        frac = float(np.clip(raw - i_max, 0.0, 1.0))
        dot.step(dt, lines[i_max], p_prev, p_now, frac)
        bad = check_rule(dot.pos, dot.anchor, dot.target, decoded)
        if bad:
            viol.append({"t": float(tq), "step": int(i_max), "why": bad})
        red.append(dot.pos)
    return {"red": red, "green": green, "violations": viol, "frames": [float(x) for x in frames],
            "n_frames": int(len(frames)),
            "capped_frames": int(dot.capped_frames), "arrivals": int(dot.arrivals),
            "n_frames_without_dot": int(sum(1 for r in red if r is None))}
