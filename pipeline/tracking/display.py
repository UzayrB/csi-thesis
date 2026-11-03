# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: T10, the dot: what the tracking window draws for each walk.

from __future__ import annotations

import dataclasses

import numpy as np

from pipeline.tracking.decoder import (LOOKBACK_W, Space, chain_transitions, decoded_xy, entry_start, night_track,
                                       stack2, viterbi)
from pipeline.tracking.settings import STRIDE_S, WINDOW_S

FPS = 10
LATENCY_S = 2.0
TOL = 1e-9
CENTRE = (2.5, 2.5)

DISPLAY_CAP_M_PER_WINDOW = 0.80
DISPLAY_SD_SCALE = 3.0
PRIOR_F = 0.5
PATH_LAG_EXTRA = 1
SHIFT_W = 1.0
HEAD_OFFSET_S = 1.0

SWITCH_THETA = 2.0
PERSIST_STEPS = 2
MAX_SWITCHES = 1
FINAL_M = 1.0
SLIDE_S = 0.5
ENTRY_WINDOW_M = 1.0
SWITCH_FAR = -1.0e9



# Frames for one recording, each computed from the windows that had ended by its time.
class LiveDisplay:

    # Sets up the object.
    def __init__(self, st, cfg, ne, transit, opts: dict):
        self.st, self.ne, self.transit = st, ne, transit
        self.cfg = dataclasses.replace(cfg, sd_scale=DISPLAY_SD_SCALE)
        self.opts = dict(opts)
        self.scorer = Scorer(st, dataclasses.replace(cfg, sd_scale=1.0), DISPLAY_CAP_M_PER_WINDOW)
        self.t0, self.t0_epoch, self.e, self.ge = [], [], [], []
        self.passes = []
        self.origin = None
        self.frames = None
        self.next_frame = 0
        self.out = {}
        self.meta = {}

    # The recording's first window start: the frame grid's origin.
    def set_origin(self, t0_first: float) -> None:
        self.origin = float(t0_first)
        self.frames = frame_times(self.origin, 200000)

    # Function press.
    def press(self, pid: int, t_press: float) -> None:
        self.passes.append({"pid": int(pid), "press": float(t_press), "end": None, "lo": None, "adj": None})

    # The walk's end (in semi mode its causal exit): no frame of the walk is drawn past it plus the latency.
    def end_press(self, pid: int, t_end: float) -> None:
        for p in self.passes:
            if p["pid"] == int(pid):
                p["end"] = float(t_end)

    # The walk's start terms, which the switch adds to each line's total.
    def set_terms(self, pid: int, committed_term: dict = None) -> None:
        for p in self.passes:
            if p["pid"] == int(pid):
                p["adj"] = committed_term

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
            self.meta[p["pid"]] = {"lock_line": facts.get("lock_line"), "switches": sw,
                                   "line_entry": facts.get("line_entry"), "t_dec0": facts.get("t_dec0"),
                                   "park_until": facts.get("park_until")}
        self.next_frame = j1

    # The walk's frames up to x_max, from the display's decode of the windows held now.
    def _compose(self, p, x_max: float):
        k = len(self.t0) - 1
        a = max(0, p["lo"] - LOOKBACK_W)
        if k < p["lo"] + 2:
            return {}, [], {}
        e = np.asarray(self.e[a:k + 1], float)
        ge = np.asarray(self.ge[a:k + 1], float)
        L = night_track(e, ge, p["lo"] - a, self.st, self.cfg, self.transit, self.ne, self.opts, draw=True,
                        max_advance=DISPLAY_CAP_M_PER_WINDOW, path_lag_extra=PATH_LAG_EXTRA, prior_f=PRIOR_F)
        E_sw = self.scorer.stack(e, ge, self.ne)
        if L is None:
            return {}, [], {}
        frames = [float(x) for x in self.frames[:int(np.searchsorted(self.frames, x_max, side="right"))]
                  if x >= p["press"]]
        drawn, sw, facts = compose_walk(self.st, L, p["lo"] - a, np.asarray(self.t0[a:k + 1]), p["press"],
                                        p["end"], frames, E_sw, self.scorer, p["adj"])
        facts["lock_line"] = L["lock_line"]
        return drawn, sw, facts


# The frame grid: from the recording's first window start, every 1 / FPS.
def frame_times(origin: float, n: int) -> np.ndarray:
    return np.arange(float(origin), float(origin) + (n + 0.5) / FPS, 1.0 / FPS)[:n]


# ONE walk's frames: the park at the centre, the glide from the line's start to the drawn path, the path...
def compose_walk(st, L, lo, t, press_start, press_end, frames, E_sw, scorer, adj):
    lock = L["lock_line"]
    lpath = L["paths"][lock]
    t_dec0 = float(t[lo]) + WINDOW_S - HEAD_OFFSET_S + LATENCY_S
    park_until = float(press_start) + LATENCY_S
    fr = [x for x in frames if float(press_start) <= x
          and (press_end is None or x < float(press_end) + LATENCY_S)]
    pre = [x for x in fr if x < park_until]
    anch = [x for x in fr if park_until <= x < t_dec0]
    post = [x for x in fr if x >= t_dec0]
    drawn = {round(float(x), 4): CENTRE for x in pre}
    line_entry = xy_of(st, st.slice_of[lock][0])
    facts = {"line_entry": line_entry, "t_dec0": t_dec0, "park_until": park_until}
    x0 = next((x for x in frames if x >= t_dec0 - 1e-9), None)
    if x0 is None and frames:
        x0 = float(frames[-1]) + np.ceil((t_dec0 - float(frames[-1])) * FPS - 1e-9) / FPS
    seam0 = walk_positions(lpath, st, t_dec0, line_entry, [x0])[0] if x0 is not None else line_entry
    g0 = float(anch[0]) if anch else float(park_until)
    span0 = float(t_dec0) - g0
    for x in anch:
        f_ = 0.0 if span0 <= 0 else float(np.clip((x - g0) / span0, 0.0, 1.0))
        drawn[round(float(x), 4)] = (line_entry[0] + (seam0[0] - line_entry[0]) * f_,
                                     line_entry[1] + (seam0[1] - line_entry[1]) * f_)
    if not post:
        return drawn, [], facts
    drawn.update({round(f, 4): p for f, p in zip(post, walk_positions(lpath, st, t_dec0, line_entry, post))})

    end_ = float(press_end) if press_end is not None else float(post[-1]) + 1.0
    dfr = [x for x in decision_frames(press_start, end_) if x <= post[-1] + TOL]
    decs = scorer.decisions(E_sw, t, lo, scorer.start(E_sw, lo), dfr)
    dots = [(float(x), drawn[round(float(x), 4)]) for x in anch + post]

    # Function along.
    def along(line, frames_):
        return list(zip(frames_, walk_positions(L["paths"][line], st, t_dec0, xy_of(st, st.slice_of[line][0]), frames_)))

    switches = []
    order = sorted(float(x) for x in anch + post)
    for s_ in decide_walk(lock, decs, adj, st, dots, lambda line, x_from: along(line, [x for x in post if x >= x_from - 1e-9])):
        xs, new = float(s_["x"]), s_["new"]
        bef = [x_ for x_ in order if x_ < xs - 1e-9]
        p_old = drawn[round(bef[-1], 4)] if bef else line_entry
        q_new = along(new, [xs + SLIDE_S])[0][1]
        for x_, p_ in slide(p_old, q_new, xs, post):
            drawn[round(float(x_), 4)] = p_
        drawn.update({round(f, 4): p_ for f, p_ in along(new, [x for x in post if x >= xs + SLIDE_S - 1e-9])})
        switches.append({"x": xs, "old": s_["old"], "new": new})
    return drawn, switches, facts


# The dot at each frame along one drawn path (a list of states, one a window): from the frame's time, the...
def walk_positions(path: list, st, t_start: float, entry_xy, frames) -> list:
    pts = [xy_of(st, s) for s in path]
    out = []
    for tq in frames:
        raw = (tq - t_start) / STRIDE_S + SHIFT_W
        i = int(np.floor(raw))
        if i < 0:
            out.append(tuple(entry_xy))
            continue
        i = min(i, len(pts) - 1)
        a, b = (pts[i - 1] if i > 0 else entry_xy), pts[i]
        f = float(np.clip(raw - i, 0.0, 1.0))
        out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
    return out


# Function xy of.
def xy_of(st, state_idx):
    q = decoded_xy(np.array([int(state_idx)]), st)
    return (float(q[0][0]), float(q[0][1]))



# Each line's Viterbi total within the line over the windows that have ended, from the walk's start: the...
class Scorer:

    # Sets up the object.
    def __init__(self, st, cfg, max_advance: float = None):
        self.st = st
        self.sp = Space(st, cfg)
        self.lT_chains = chain_transitions(st, max_advance)

    # Function stack.
    def stack(self, e_path, ge, ne):
        return stack2(e_path, ge, ne, self.sp)

    # Function start.
    def start(self, E, lo):
        sl = np.asarray(entry_start(E, self.st, self.sp, lo), float).copy()
        s_arr = np.asarray(self.st.s_of, float)
        for nm in self.st.names:
            a, b = self.st.slice_of[nm]
            far = a + np.flatnonzero((s_arr[a:b] - s_arr[a]) > ENTRY_WINDOW_M + 1e-9)
            if len(far):
                sl[far] = SWITCH_FAR
        return sl

    # Function totals.
    def totals(self, E, lo, hi, sl) -> dict:
        tot = {}
        for nm in self.st.names:
            a, b = self.st.slice_of[nm]
            sub = np.asarray(E[lo:hi + 1, a:b], float)
            ls = np.asarray(sl[a:b], float)
            s = viterbi(sub, self.lT_chains[a:b, a:b], log_start=ls)
            tot[nm] = float(sub[np.arange(len(s)), s].sum()) + float(ls[int(s[0])])
        return tot

    # One entry per decision frame, reading ONLY windows with t_start + WINDOW_S <= x.
    def decisions(self, E, t, lo, sl, frames) -> list:
        t = np.asarray(t, float)
        out = []
        for x in frames:
            ok = np.flatnonzero(t + WINDOW_S <= x + 1e-9)
            w = int(ok[-1]) if len(ok) else -1
            if w <= lo:
                continue
            out.append({"x": float(x), "raw": self.totals(E, lo, w, sl)})
        return out


# The switch's decision times: x_k = press + 2.0 + k * 0.5 s, k >= 1, while x_k < end + 2.0.
def decision_frames(press_start: float, press_end: float) -> list:
    out, k = [], 1
    while True:
        x = float(press_start) + LATENCY_S + k * STRIDE_S
        if x >= float(press_end) + LATENCY_S - 1e-9:
            return out
        out.append(x)
        k += 1


# The switches in one walk (at most MAX_SWITCHES): a line not yet drawn that leads the drawn line by more...
def decide_walk(lock_line: str, decs: list, adj, st, dots_lock, dots_for_line) -> list:

    # Function segment.
    def segment(dots):
        fr = [(float(x), p) for x, p in dots if p is not None]
        return fr, np.asarray([x for x, _p in fr], float)

    line, drawn_lines = lock_line, {lock_line}
    L = line_length(st, line)
    fr, fx = segment(dots_lock)
    arcs = None
    hist = []
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
        if float(arcs[n_up - 1]) >= L - FINAL_M:
            break
        tot = {nm: d["raw"][nm] + float((adj or {}).get(nm, 0.0)) for nm in d["raw"]}
        best = max(tot, key=tot.get)
        if best not in drawn_lines and float(tot[best] - tot[line]) > SWITCH_THETA:
            streak = streak + 1 if best == streak_line else 1
            streak_line = best
        else:
            streak_line, streak = None, 0
        if streak >= PERSIST_STEPS:
            hist.append({"x": x, "old": line, "new": best})
            if len(hist) >= MAX_SWITCHES:
                break
            line = best
            drawn_lines.add(best)
            L = line_length(st, line)
            fr, fx = segment(dots_for_line(best, x + SLIDE_S))
            arcs = None
            streak_line, streak = None, 0
    return hist


# The dot on [x_s, x_s + SLIDE_S): the straight segment from p_old to q_new, by the fraction of the time gone.
def slide(p_old, q_new, x_s: float, frames) -> list:
    out = []
    p0, q1 = np.asarray(p_old, float), np.asarray(q_new, float)
    for x in frames:
        if not (x_s - 1e-9 <= x < x_s + SLIDE_S - 1e-9):
            continue
        f = float(np.clip((x - x_s) / SLIDE_S, 0.0, 1.0))
        p = p0 + (q1 - p0) * f
        out.append((float(x), (float(p[0]), float(p[1]))))
    return out


# Metres of arc from the line's start to the point's projection on the line.
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


# Function line arcs.
def line_arcs(st, line: str):
    a, b = st.slice_of[line]
    return np.asarray(st.xy, float)[a:b], np.asarray(st.s_of, float)[a:b]
