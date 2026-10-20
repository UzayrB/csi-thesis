# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The shipped display, live: the dot, the lock at press + 2.0 s, the one switch, the end text.

from __future__ import annotations

import contextlib

import numpy as np

FPS = 10
LATENCY_S = 2.0
DELAY_S = 2.0
LAG_S = 1.0
HEAD_OFFSET_S = 0.75
SHIFT_W = 0.50
DISPLAY_CAP_M_PER_WINDOW = 0.80
DISPLAY_CANDIDATES = {"K0": {"path_lag_extra": 0, "anchor": "hold"}, "K1": {"path_lag_extra": 1, "anchor": "hold"},
                      "K2": {"path_lag_extra": 2, "anchor": "hold"}, "K1g": {"path_lag_extra": 1, "anchor": "glide"},
                      "K2g": {"path_lag_extra": 2, "anchor": "glide"},
                      "K1gf": {"path_lag_extra": 1, "anchor": "glide_first"}}
DISPLAY_SD_SCALE = 4.5
DECISION_SD_SCALE = 1.0
TOL = 1e-9


# Decoder.MAX_ADVANCE_M set for a block, with one transition cache per setting.
class CapSwitch:

    # Sets up the object.
    def __init__(self):
        self.caches = {}

    # Function cap.
    @contextlib.contextmanager
    def cap(self, value):
        import pipeline.constrained.decoder as D
        import pipeline.constrained.decoder2 as D2
        prev = D.MAX_ADVANCE_M
        if value == prev:
            yield
            return
        self.caches[prev] = dict(D2._LT_CACHE)
        D2._LT_CACHE.clear()
        D2._LT_CACHE.update(self.caches.get(value, {}))
        D.MAX_ADVANCE_M = value
        try:
            yield
        finally:
            self.caches[value] = dict(D2._LT_CACHE)
            D2._LT_CACHE.clear()
            D2._LT_CACHE.update(self.caches.get(prev, {}))
            D.MAX_ADVANCE_M = prev


# The display arms f3_render reads from the stage results, read the same way.
def settings() -> dict:
    from pipeline.constrained.fh_common import load
    r3p = load("r3_prior") or {}
    prior_arm = r3p.get("SHIPPED_DISPLAY_PRIOR") or "flatten_0.00"
    prior_f = 0.0 if prior_arm == "DISP_RAW" else float(prior_arm.split("_")[-1])
    e2 = load("e2_switch") or {}
    switch = ((e2.get("evaluation") or {}).get("RENDER") if e2.get("VALID") else None)
    s2 = load("s2_display") or {}
    shipped = s2.get("SHIPPED_DISPLAY") or "centre_labelled"
    return {"prior_arm": prior_arm, "prior_f": prior_f, "switch": switch, "shipped_display": shipped}


# F3_render's frame grid, np.arange from the recording's first window start at 1 / FPS.
def frame_times(origin: float, n: int) -> np.ndarray:
    return np.arange(float(origin), float(origin) + (n + 0.5) / FPS, 1.0 / FPS)[:n]


# ONE walk, composed exactly as f3_render.main composes it.
def compose_walk(st, L, lo, t, press_start, press_end, frames, E_sw, scorer, sett, adj):
    from pipeline.constrained import switching as SW
    from pipeline.constrained.night_common import STRIDE
    from pipeline.constrained.render_display import CENTRE, simulate_walk, xy_of
    from pipeline.constrained.rebuild_common import WINDOW_S
    shift_w = float(sett["shift_w"]) if sett.get("shift_w") is not None else SHIFT_W
    head_offset = float(sett["head_offset_s"]) if sett.get("head_offset_s") is not None else HEAD_OFFSET_S
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
    hold = sett.get("anchor") == "hold"
    if hold:
        for x in anch:
            drawn[round(float(x), 4)] = line_entry
    glide = sett.get("anchor") in ("glide", "glide_first")
    if glide and lpath:
        x0 = next((x for x in frames if x >= t_dec0 - 1e-9), None)
        if x0 is None and frames:
            x0 = float(frames[-1]) + np.ceil((t_dec0 - float(frames[-1])) * FPS - 1e-9) / FPS
        s0 = simulate_walk(lpath, st, t_dec0, t_dec0 + 1.0, line_entry, L["lock_line"], STRIDE, 0, FPS, None,
                           lambda q: None, frames=[x0], lead=False, shift_w=shift_w) if x0 is not None else None
        seam0 = s0["red"][0] if (s0 and s0["red"]) else line_entry
        g0 = float(anch[0]) if (sett.get("anchor") == "glide_first" and anch) else float(park_until)
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
    seam = sim["red"][0] if sim["red"] else line_entry
    span = float(t_dec0) - float(park_until)
    for x in ([] if (hold or glide) else anch):
        f_ = 0.0 if span <= 0 else float(np.clip((x - park_until) / span, 0.0, 1.0))
        drawn[round(float(x), 4)] = (line_entry[0] + (seam[0] - line_entry[0]) * f_,
                                     line_entry[1] + (seam[1] - line_entry[1]) * f_)
    drawn.update({round(f, 4): p for f, p in zip(sim["frames"], sim["red"])})
    margins = []
    try:
        from pipeline.constrained.rebuild_common import WINDOW_S as _WS
        ev_end = [float(t[int(q["evidence_window"])]) + _WS for q in lpath]
        for x in post:
            i_ = int(min(max(np.floor((x - t_dec0) / STRIDE + shift_w), 0), len(lpath) - 1))
            margins.append(float(x) - ev_end[i_])
        if glide:
            margins += [float(x) - ev_end[0] for x in anch if x > park_until + 1e-9]
    except Exception:
        margins = []
    sw = sett["switch"]
    if sw:
        assert sett["shipped_display"] == "DISP_END", "switch paths exist for DISP_END only"
        end_ = float(press_end) if press_end is not None else float(post[-1]) + 1.0
        dfr = [x for x in SW.decision_frames(press_start, end_) if x <= post[-1] + TOL]
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

        res = SW.decide_walk(L["lock_line"], decs, adj, float(sw["theta"]), st, dots, dots_for,
                             radius=sw["radius_m"], max_switches=int(sw["max_switches"]),
                             final_m=float(sw["final_m"]))
        order = sorted(float(x) for x in anch + post)
        for s_ in res["switches"]:
            xs, new = float(s_["x"]), s_["new"]
            bef = [x_ for x_ in order if x_ < xs - 1e-9]
            p_old = drawn[round(bef[-1], 4)] if bef else line_entry
            q_new = newsim(new, [xs + SW.SLIDE_S])["red"][0]
            for x_, p_, _off in SW.slide(p_old, q_new, xs, post):
                drawn[round(float(x_), 4)] = p_
            after = [x for x in post if x >= xs + SW.SLIDE_S - 1e-9]
            nsim = newsim(new, after)
            drawn.update({round(f, 4): p_ for f, p_ in zip(nsim["frames"], nsim["red"])})
            switches.append({"x": xs, "old": s_["old"], "new": new})
    return drawn, switches, {"line_entry": line_entry, "t_dec0": t_dec0, "park_until": park_until,
                             "min_margin_s": (min(margins) if margins else None)}


# Frames for one recording, each computed from the windows that had ended by its time.
class LiveDisplay:

    # Sets up the object.
    def __init__(self, st, cfg, ne, transit, opts_disp: dict, session: str, stem: str, sett=None,
                 caps: CapSwitch = None):
        import dataclasses as dc

        from pipeline.constrained import switching as SW
        self.st, self.ne, self.transit = st, ne, transit
        self.cfg_disp = dc.replace(cfg, sd_scale=DISPLAY_SD_SCALE)
        self.cfg_dec = dc.replace(cfg, sd_scale=DECISION_SD_SCALE)
        self.opts = dict(opts_disp)
        self.session, self.stem = session, stem
        self.sett = sett or settings()
        self.caps = caps or CapSwitch()
        with self.caps.cap(DISPLAY_CAP_M_PER_WINDOW):
            self.scorer = SW.Scorer(st, self.cfg_dec, transit) if self.sett["switch"] else None
        self.t0, self.t0_epoch, self.e, self.ge, self.e_end = [], [], [], [], []
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
    def push(self, t0: float, t0_epoch: float, e_row, ge: float, e_end_row) -> None:
        from pipeline.constrained.rebuild_common import WINDOW_S
        self._draw_until(float(t0) + WINDOW_S - TOL)
        self.t0.append(float(t0))
        self.t0_epoch.append(float(t0_epoch))
        self.e.append(np.asarray(e_row, float))
        self.ge.append(float(ge))
        self.e_end.append(np.asarray(e_end_row, float))
        k = len(self.t0) - 1
        for p in self.passes:
            if p["lo"] is None and self.t0[k] + 1.0 >= p["press"]:
                p["lo"] = k

    # Function close.
    def close(self) -> None:
        self._draw_until(np.inf)

    # Draw every frame before x_stop from the windows held now (all of which ended by then).
    def _draw_until(self, x_stop: float) -> None:
        if self.frames is None or not self.t0:
            return
        j0 = self.next_frame
        j1 = int(np.searchsorted(self.frames, x_stop, side="left"))
        if np.isinf(x_stop):
            from pipeline.constrained.rebuild_common import WINDOW_S
            j1 = len(np.arange(self.origin, self.t0[-1] + WINDOW_S, 1.0 / FPS))
        if j1 <= j0:
            return
        xs = [float(x) for x in self.frames[j0:j1]]
        from pipeline.constrained.render_display import CENTRE
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
        from pipeline.constrained.night_arms import night_track
        from pipeline.constrained.night_common import STRIDE
        from pipeline.live.decoder import LOOKBACK_W
        k = len(self.t0) - 1
        a = max(0, p["lo"] - LOOKBACK_W)
        lo_rel = p["lo"] - a
        if k < p["lo"] + 2:
            return {}, [], {}
        rec = _shim(self, a, k, p)
        e = np.asarray(self.e[a:k + 1], float)
        ge = np.asarray(self.ge[a:k + 1], float)
        e_end = np.asarray(self.e_end[a:k + 1], float)
        o = dict(self.opts)
        o["start_term"] = ({f"{self.session}|{self.stem}|{p['pid']}": p["a2"]} if p["a2"] is not None else None)
        lag_w = int(round(LAG_S / STRIDE))
        from pipeline.constrained import sb2_structural
        sb2_structural._PRESS_CACHE[(self.session, self.stem)] = {p["pid"]: p["end"] or p["press"]}
        with self.caps.cap(DISPLAY_CAP_M_PER_WINDOW):
            import pipeline.constrained.render_display as RD
            orig_lcp, extra = RD.locked_chain_path, int(self.sett.get("path_lag_extra") or 0)
            if extra:
                # Function lcp.
                def lcp(e_res, lT_, st_, lo_, hi_, lag_w_, chain_, log_start=None):
                    return orig_lcp(e_res, lT_, st_, lo_, hi_, int(lag_w_) + extra, chain_, log_start=log_start)
                RD.locked_chain_path = lcp
            try:
                rows = night_track(e, rec, self.st, self.cfg_disp, self.transit, self.ne, ge, STRIDE, o, None,
                               want_display=True, display_lags_w=(lag_w,), display_to_horizon=True,
                               display_alt_e={"end": e_end},
                               display_alt_flatten=({"end": self.sett["prior_f"]} if self.sett["prior_f"] else None),
                               display_lead_in_w=0, display_switch_paths=bool(self.sett["switch"]))
            finally:
                RD.locked_chain_path = orig_lcp
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
    from pipeline.constrained.recordings import Recording
    n = b - a + 1
    walk = np.zeros(n, bool)
    walk[p["lo"] - a:] = True
    return Recording(session=d.session, stem=d.stem, participant="live",
                     t0=np.asarray(d.t0[a:b + 1], float), t0_epoch=np.asarray(d.t0_epoch[a:b + 1], float),
                     mode=np.where(walk, "walk", "idle").astype("U10"), pass_id=np.where(walk, p["pid"], -1),
                     path_name=np.full(n, "", dtype="U10"), xy=np.full((n, 2), np.nan),
                     cell_id=np.full(n, "", dtype="U10"), gap_flag=np.zeros(n, bool))
