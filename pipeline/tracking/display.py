# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: T10, the dot: what the tracking window draws for each walk.

from __future__ import annotations

import dataclasses

import numpy as np

from pipeline.tracking.decoder import (LOOKBACK_W, Space, decoded_paths, decoded_xy, entry_start, night_track, stack2,
                                       transition_matrix, viterbi)
from pipeline.tracking.settings import STRIDE, STRIDE_S, WINDOW_S, Recording

FPS = 10
LATENCY_S = 2.0
DELAY_S = 2.0
LAG_S = 1.0
DISPLAY_CAP_M_PER_WINDOW = 0.80
DISPLAY_CANDIDATES = {"K1gf": {"path_lag_extra": 1, "anchor": "glide_first"}}
DISPLAY_SD_SCALE = 4.5
DECISION_SD_SCALE = 1.0
TOL = 1e-9



# Frames for one recording, each computed from the windows that had ended by its time.
class LiveDisplay:

    # Sett: the display's settings (the frozen tracker's, with the display profile's on top).
    def __init__(self, st, cfg, ne, transit, opts_disp: dict, session: str, stem: str, sett: dict):
        self.st, self.ne, self.transit = st, ne, transit
        self.cfg_disp = dataclasses.replace(cfg, sd_scale=DISPLAY_SD_SCALE)
        self.cfg_dec = dataclasses.replace(cfg, sd_scale=DECISION_SD_SCALE)
        self.opts = dict(opts_disp)
        self.session, self.stem = session, stem
        self.sett = sett
        self.scorer = Scorer(st, self.cfg_dec, transit, DISPLAY_CAP_M_PER_WINDOW) if self.sett["switch"] else None
        self.t0, self.t0_epoch, self.e, self.ge = [], [], [], []
        self.passes = []
        self.origin = None
        self.frames = None
        self.next_frame = 0
        self.out = {}
        self.meta = {}
        self.n_decodes = 0

    # The recording's first window start: the frame grid's origin, as f3_render sets it.
    def set_origin(self, t0_first: float) -> None:
        self.origin = float(t0_first)
        self.frames = frame_times(self.origin, 200000)

    # Function press.
    def press(self, pid: int, t_press: float, a2_term: dict = None, committed_term: dict = None) -> None:
        self.passes.append({"pid": int(pid), "press": float(t_press), "end": None, "lo": None,
                            "a2": a2_term, "adj": committed_term})

    # Function end press.
    def end_press(self, pid: int, t_end: float) -> None:
        for p in self.passes:
            if p["pid"] == int(pid):
                p["end"] = float(t_end)

    # Function set terms.
    def set_terms(self, pid: int, a2_term: dict = None, committed_term: dict = None) -> None:
        for p in self.passes:
            if p["pid"] == int(pid):
                p["a2"], p["adj"] = a2_term, committed_term

    # One completed window.
    def push(self, t0: float, t0_epoch: float, e_row, ge: float) -> None:
        self.t0.append(float(t0))
        self.t0_epoch.append(float(t0_epoch))
        self.e.append(np.asarray(e_row, float))
        self.ge.append(float(ge))
        k = len(self.t0) - 1
        for p in self.passes:
            if p["lo"] is None and self.t0[k] + 1.0 >= p["press"]:
                p["lo"] = k

    # Function close.
    def close(self) -> None:
        self.draw_until(np.inf)

    # Draw every frame before x_stop from the windows held now (all of which ended by then).
    def draw_until(self, x_stop: float) -> None:
        if self.frames is None or not self.t0:
            return
        j0 = self.next_frame
        j1 = int(np.searchsorted(self.frames, x_stop, side="left"))
        if np.isinf(x_stop):
            j1 = len(np.arange(self.origin, self.t0[-1] + WINDOW_S, 1.0 / FPS))
        if j1 <= j0:
            return
        xs = [float(x) for x in self.frames[j0:j1]]
        for p in self.passes:
            lo_end = p["end"] + LATENCY_S if p["end"] is not None else np.inf
            need = [x for x in xs if p["press"] <= x < lo_end]
            if not need:
                continue
            out = self.out.setdefault(p["pid"], {})
            park_until = p["press"] + LATENCY_S
            for x in need:
                if x < park_until:
                    out[round(x, 4)] = CENTRE
            rest = [x for x in need if x >= park_until]
            if not rest or p["lo"] is None:
                continue
            drawn, sw, facts = self._compose(p, rest[-1])
            for x in rest:
                v = drawn.get(round(x, 4))
                if v is not None:
                    out[round(x, 4)] = v
            prev_m = (self.meta.get(p["pid"]) or {}).get("min_margin_s")
            now_m = facts.get("min_margin_s")
            self.meta[p["pid"]] = {"lock_line": facts.get("lock_line"), "switches": sw,
                                   "line_entry": facts.get("line_entry"), "t_dec0": facts.get("t_dec0"),
                                   "park_until": facts.get("park_until"),
                                   "min_margin_s": (now_m if prev_m is None else prev_m if now_m is None
                                                    else min(prev_m, now_m))}
        self.next_frame = j1

    # Function compose.
    def _compose(self, p, x_max: float):
        k = len(self.t0) - 1
        a = max(0, p["lo"] - LOOKBACK_W)
        lo_rel = p["lo"] - a
        if k < p["lo"] + 2:
            return {}, [], {}
        rec = _shim(self, a, k, p)
        e = np.asarray(self.e[a:k + 1], float)
        ge = np.asarray(self.ge[a:k + 1], float)
        o = dict(self.opts)
        o["start_term"] = ({f"{self.session}|{self.stem}|{p['pid']}": p["a2"]} if p["a2"] is not None else None)
        lag_w = int(round(LAG_S / STRIDE))
        rows = night_track(e, rec, self.st, self.cfg_disp, self.transit, self.ne, ge, STRIDE, o,
                           want_display=True, display_lags_w=(lag_w,), display_delays_s=(DELAY_S,),
                           display_to_horizon=True,
                           display_alt_e={"end": e},
                           display_alt_flatten=({"end": self.sett["prior_f"]} if self.sett["prior_f"] else None),
                           display_lead_in_w=0, display_switch_paths=bool(self.sett["switch"]),
                           max_advance=DISPLAY_CAP_M_PER_WINDOW,
                           path_lag_extra=int(self.sett.get("path_lag_extra") or 0))
        E_sw = None
        if self.sett["switch"]:
            self.ne.calibrate(e)
            E_sw = self.scorer.stack(e, ge, self.ne)
        self.n_decodes += 1
        rows = [r for r in rows if int(r["pass_id"]) == p["pid"]]
        if not rows:
            return {}, [], {}
        L = rows[0]["display_locked"][f"{lag_w}|{DELAY_S}"]
        frames = [float(x) for x in self.frames[:int(np.searchsorted(self.frames, x_max, side="right"))]
                  if x >= p["press"]]
        drawn, sw, facts = compose_walk(self.st, L, lo_rel, np.asarray(self.t0[a:k + 1]), p["press"],
                                        p["end"], frames, E_sw, self.scorer, self.sett, p["adj"])
        facts["lock_line"] = L["lock_line"]
        return drawn, sw, facts


# Function shim.
def _shim(d, a: int, b: int, p):
    n = b - a + 1
    walk = np.zeros(n, bool)
    walk[p["lo"] - a:] = True
    return Recording(session=d.session, stem=d.stem, participant="live",
                     t0=np.asarray(d.t0[a:b + 1], float), t0_epoch=np.asarray(d.t0_epoch[a:b + 1], float),
                     mode=np.where(walk, "walk", "idle").astype("U10"), pass_id=np.where(walk, p["pid"], -1),
                     path_name=np.full(n, "", dtype="U10"), xy=np.full((n, 2), np.nan),
                     cell_id=np.full(n, "", dtype="U10"), gap_flag=np.zeros(n, bool))


# F3_render's frame grid, np.arange from the recording's first window start at 1 / FPS.
def frame_times(origin: float, n: int) -> np.ndarray:
    return np.arange(float(origin), float(origin) + (n + 0.5) / FPS, 1.0 / FPS)[:n]


# ONE walk, composed exactly as f3_render.main composes it.
def compose_walk(st, L, lo, t, press_start, press_end, frames, E_sw, scorer, sett, adj):
    shift_w = float(sett["shift_w"])
    head_offset = float(sett["head_offset_s"])
    scene_start = float(t[lo]) + WINDOW_S - head_offset
    t_dec0 = scene_start + LATENCY_S
    park_until = float(press_start) + LATENCY_S
    fr = [x for x in frames if float(press_start) <= x
          and (press_end is None or x < float(press_end) + LATENCY_S)]
    pre = [x for x in fr if x < park_until]
    anch = [x for x in fr if park_until <= x < t_dec0]
    post = [x for x in fr if x >= t_dec0]
    alt = (L.get("paths_alt") or {}).get("end")
    lpath = alt if (sett["shipped_display"] == "DISP_END" and alt) else L["path"]
    drawn = {}
    for x in pre:
        drawn[round(float(x), 4)] = CENTRE
    a_, _b = st.slice_of[L["lock_line"]]
    line_entry = xy_of(st, a_)
    switches = []
    if lpath:
        x0 = next((x for x in frames if x >= t_dec0 - 1e-9), None)
        if x0 is None and frames:
            x0 = float(frames[-1]) + np.ceil((t_dec0 - float(frames[-1])) * FPS - 1e-9) / FPS
        s0 = simulate_walk(lpath, st, t_dec0, t_dec0 + 1.0, line_entry, L["lock_line"], STRIDE, 0, FPS, None,
                           lambda q: None, frames=[x0], lead=False, shift_w=shift_w) if x0 is not None else None
        seam0 = s0["red"][0] if (s0 and s0["red"]) else line_entry
        g0 = float(anch[0]) if anch else float(park_until)
        span0 = float(t_dec0) - g0
        for x in anch:
            f_ = 0.0 if span0 <= 0 else float(np.clip((x - g0) / span0, 0.0, 1.0))
            drawn[round(float(x), 4)] = (line_entry[0] + (seam0[0] - line_entry[0]) * f_,
                                         line_entry[1] + (seam0[1] - line_entry[1]) * f_)
    if not (post and lpath):
        return drawn, switches, {"line_entry": line_entry, "t_dec0": t_dec0, "park_until": park_until}
    t_eff = t_dec0
    end_arg = (float(press_end) if press_end is not None else float(post[-1])) + LATENCY_S
    sim = simulate_walk(lpath, st, t_eff, end_arg, line_entry, L["lock_line"], STRIDE, 0, FPS, None,
                        lambda q: None, frames=post, lead=False, shift_w=shift_w)
    drawn.update({round(f, 4): p for f, p in zip(sim["frames"], sim["red"])})
    margins = []
    try:
        ev_end = [float(t[int(q["evidence_window"])]) + WINDOW_S for q in lpath]
        for x in post:
            i_ = int(min(max(np.floor((x - t_dec0) / STRIDE + shift_w), 0), len(lpath) - 1))
            margins.append(float(x) - ev_end[i_])
        margins += [float(x) - ev_end[0] for x in anch if x > park_until + 1e-9]
    except Exception:
        margins = []
    sw = sett["switch"]
    if sw:
        assert sett["shipped_display"] == "DISP_END", "switch paths exist for DISP_END only"
        end_ = float(press_end) if press_end is not None else float(post[-1]) + 1.0
        dfr = [x for x in decision_frames(press_start, end_) if x <= post[-1] + TOL]
        decs = scorer.decisions(E_sw, t, lo, scorer.start(E_sw, lo), dfr)
        dots = [(float(x), drawn[round(float(x), 4)]) for x in anch + post]

        # Function newsim.
        def newsim(line, frames_):
            na, _nb = st.slice_of[line]
            return simulate_walk(L["switch_paths"]["end"][line], st, t_eff, end_arg, xy_of(st, na), line,
                                 STRIDE, 0, FPS, None, lambda q: None, frames=frames_, lead=False,
                                 shift_w=shift_w)

        # Function dots for.
        def dots_for(line, x_from):
            s_ = newsim(line, [x for x in post if x >= x_from - 1e-9])
            return list(zip(s_["frames"], s_["red"]))

        res = decide_walk(L["lock_line"], decs, adj, float(sw["theta"]), st, dots, dots_for,
                             radius=sw["radius_m"], max_switches=int(sw["max_switches"]),
                             final_m=float(sw["final_m"]))
        order = sorted(float(x) for x in anch + post)
        for s_ in res["switches"]:
            xs, new = float(s_["x"]), s_["new"]
            bef = [x_ for x_ in order if x_ < xs - 1e-9]
            p_old = drawn[round(bef[-1], 4)] if bef else line_entry
            q_new = newsim(new, [xs + SLIDE_S])["red"][0]
            for x_, p_, _off in slide(p_old, q_new, xs, post):
                drawn[round(float(x_), 4)] = p_
            after = [x for x in post if x >= xs + SLIDE_S - 1e-9]
            nsim = newsim(new, after)
            drawn.update({round(f, 4): p_ for f, p_ in zip(nsim["frames"], nsim["red"])})
            switches.append({"x": xs, "old": s_["old"], "new": new})
    return drawn, switches, {"line_entry": line_entry, "t_dec0": t_dec0, "park_until": park_until,
                             "min_margin_s": (min(margins) if margins else None)}



SWITCH_CAP_M_S = 2.0


CENTRE = (2.5, 2.5)


# Function xy of.
def xy_of(st, state_idx):
    q = decoded_xy(np.array([int(state_idx)]), st)
    return (float(q[0][0]), float(q[0][1]))


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



PERSIST_STEPS = 2


MAX_SWITCHES = 1
FINAL_M = 1.0
SLIDE_S = 0.5
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
    def __init__(self, st, cfg, transit, max_advance: float = None):
        self.st = st
        self.sp = Space(st, cfg)
        self.lT_chains = transition_matrix(st, "tight", with_null=False, max_advance=max_advance)
        names = np.asarray(decoded_paths(np.arange(self.sp.N), st)).astype(str)
        self.on_chain = names != ""
        self.first_state = np.zeros(self.sp.N, bool)
        for nm in st.names:
            self.first_state[st.slice_of[nm][0]] = True

    # Function stack.
    def stack(self, e_path, ge, ne):
        return stack2(e_path, ge, ne, self.sp)

    # Function start.
    def start(self, E, lo):
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
