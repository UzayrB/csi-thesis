"""The shipped display, live: the dot, the lock at press + 2.0 s, the one switch, the end text.

The display is `f3_render`'s, composed per walk exactly as its main loop composes it (the park at the
room centre, the anchor segment from the committed line's entry, `simulate_walk` on the DISP_END
locked path, and the one mid-walk switch through `switching.decide_walk`). `f3_render` does all of it
once, after the recording, over every window. Here each FRAME is computed from the windows that had
ended by that frame's time and nothing later: the display decode and the switching scorer are run on
that prefix, the walk is composed, and only that frame is kept. Gate 4 compares every frame with the
one `f3_render` drew. A frame that differs would be a frame `f3_render` computed from radio recorded
after it, so the gate is the causality test as well as the equality test.

`f3_render` sets module state in a fixed order, and the live process must reproduce it:

  - the DISPLAY decode runs with `decoder.MAX_ADVANCE_M = 0.80` (the speed cap) and `sd_scale` 4.5;
    the DECISION decode runs with no cap and `sd_scale` 1.0;
  - the switching scorer (`switching.Scorer`) is BUILT while the cap is set, so its chain transitions
    carry it;
  - `decoder2._LT_CACHE` is keyed without the cap, so `f3_render` clears it at every change. Here the
    two settings keep one cache each and swap them (`CapSwitch`), which gives the same matrices.

The constants below are `f3_render.main`'s locals, which cannot be imported. Gate 4 checks each of
them against the values `f3_render` recorded in its results.
"""

from __future__ import annotations

import contextlib

import numpy as np

FPS = 10
LATENCY_S = 2.0                  #: V1: the whole display runs this far behind real time
DELAY_S = 2.0                    #: the lock reads the window ending at press + 2.0 s
LAG_S = 1.0                      #: WINDOW_S / 2, the strict causal lag
HEAD_OFFSET_S = 0.75             #: R1: how far behind its window's end the drawn head names
SHIFT_W = 0.50                   #: V5: the drawn dot's phase, in strides
DISPLAY_CAP_M_PER_WINDOW = 0.80  #: the display's speed cap
#: item 3 of 30 Sep: the dot leaves the entry with the walker. The candidates, each display-only: the drawn path's
#: look-ahead within the locked line (windows past each step; 0 is the pinned night_track's own), and the anchor
#: span held at the entry or glided to the first decoded frame. Chosen on the rotations only, by
#: rule/DOT_PREREG.md; the app's choice is final_model.DISPLAY_CANDIDATE
DISPLAY_CANDIDATES = {"K0": {"path_lag_extra": 0, "anchor": "hold"}, "K1": {"path_lag_extra": 1, "anchor": "hold"},
                      "K2": {"path_lag_extra": 2, "anchor": "hold"}, "K1g": {"path_lag_extra": 1, "anchor": "glide"},
                      "K2g": {"path_lag_extra": 2, "anchor": "glide"},
                      # K1g with the glide starting at the FIRST ANCHOR FRAME (10 Oct, the clean display's rule 2a fix):
                      # that frame is the locked line's entry exactly; only the anchor span's frames differ from K1g
                      "K1gf": {"path_lag_extra": 1, "anchor": "glide_first"}}
DISPLAY_SD_SCALE = 4.5
DECISION_SD_SCALE = 1.0
TOL = 1e-9                       #: a window has ended by frame x when t0 + WINDOW_S <= x + TOL


class CapSwitch:
    """`decoder.MAX_ADVANCE_M` set for a block, with one transition cache per setting."""

    def __init__(self):
        self.caches = {}

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


def settings() -> dict:
    """The display arms `f3_render` reads from the stage results, read the same way."""
    from pipeline.constrained.fh_common import load
    r3p = load("r3_prior") or {}
    prior_arm = r3p.get("SHIPPED_DISPLAY_PRIOR") or "flatten_0.00"
    prior_f = 0.0 if prior_arm == "DISP_RAW" else float(prior_arm.split("_")[-1])
    e2 = load("e2_switch") or {}
    switch = ((e2.get("evaluation") or {}).get("RENDER") if e2.get("VALID") else None)
    s2 = load("s2_display") or {}
    shipped = s2.get("SHIPPED_DISPLAY") or "centre_labelled"
    return {"prior_arm": prior_arm, "prior_f": prior_f, "switch": switch, "shipped_display": shipped}


def frame_times(origin: float, n: int) -> np.ndarray:
    """`f3_render`'s frame grid, np.arange from the recording's first window start at 1 / FPS.
    np.arange fills start + i * ((start + step) - start), so the values do not depend on the stop."""
    return np.arange(float(origin), float(origin) + (n + 0.5) / FPS, 1.0 / FPS)[:n]


def compose_walk(st, L, lo, t, press_start, press_end, frames, E_sw, scorer, sett, adj):
    """ONE walk, composed exactly as `f3_render.main` composes it. Returns ({round(x, 4): xy}, switches).

    `lo` indexes `t` (the windows given); `frames` are the recording's frame times inside this walk;
    `press_end` is the end press, or None while the walk is still being drawn (the decision frames
    then run to the last frame given)."""
    from pipeline.constrained import switching as SW
    from pipeline.constrained.night_common import STRIDE
    from pipeline.constrained.render_display import CENTRE, simulate_walk, xy_of
    from pipeline.constrained.rebuild_common import WINDOW_S
    # a display profile (final_model.DISPLAY_PROFILES) may set the phase and the head offset in sett; without one, the
    # module's values, exactly as before
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
        # RULE 2a, the LIVE form (sett["anchor"] = "hold", the app's): the dot waits at the locked line's entry
        # until the first decoded position. `f3_render` slides it towards that position over the anchor span,
        # but that position reads radio that ends up to 0.6 s after the anchor frames, which a screen drawing
        # each frame at its own time does not have. Held, every anchor frame is known at the lock
        for x in anch:
            drawn[round(float(x), 4)] = line_entry
    glide = sett.get("anchor") in ("glide", "glide_first")
    if glide and lpath:
        # THE GLIDE (item 3 of 30 Sep): over the anchor span the dot glides from the locked line's entry to the
        # position the drawn path takes at its first decoded frame, as the display glides between decoded
        # positions. That position reads step 0 alone, whose radio ends at press + 1.0 s plus the path's
        # look-ahead: before every anchor frame for a look-ahead of at most 2 windows. The first anchor frame
        # (the lock frame) is the entry itself
        x0 = next((x for x in frames if x >= t_dec0 - 1e-9), None)
        if x0 is None and frames:
            x0 = float(frames[-1]) + np.ceil((t_dec0 - float(frames[-1])) * FPS - 1e-9) / FPS
        s0 = simulate_walk(lpath, st, t_dec0, t_dec0 + 1.0, line_entry, L["lock_line"], STRIDE, 0, FPS, None,
                           lambda q: None, frames=[x0], lead=False, shift_w=shift_w) if x0 is not None else None
        seam0 = s0["red"][0] if (s0 and s0["red"]) else line_entry
        # glide_first (K1gf): the glide starts at the first anchor frame, which is therefore the entry exactly (rule 2a
        # as written); glide (K1g): it starts at park_until, so the first frame (on the recording's 0.1 s grid, not the
        # press's) may already be part-way along
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
    # THE MARGIN (item 3 of 30 Sep): for every decoded frame, its time less the end of the latest radio it reads
    # (the step simulate_walk interpolates towards, and its evidence window); for the glide, step 0's
    margins = []
    try:                                              # a measurement: it must never stop a frame being drawn
        from pipeline.constrained.rebuild_common import WINDOW_S as _WS
        ev_end = [float(t[int(q["evidence_window"])]) + _WS for q in lpath]
        for x in post:
            i_ = int(min(max(np.floor((x - t_dec0) / STRIDE + shift_w), 0), len(lpath) - 1))
            margins.append(float(x) - ev_end[i_])
        if glide:
            margins += [float(x) - ev_end[0] for x in anch if x > park_until + 1e-9]
    except Exception:                                 # noqa: BLE001
        margins = []
    sw = sett["switch"]
    if sw:
        assert sett["shipped_display"] == "DISP_END", "switch paths exist for DISP_END only"
        # the decision frames up to the last frame drawn now; later ones are decided when their
        # windows exist (a decision at x reads only windows that ended by x)
        end_ = float(press_end) if press_end is not None else float(post[-1]) + 1.0
        dfr = [x for x in SW.decision_frames(press_start, end_) if x <= post[-1] + TOL]
        decs = scorer.decisions(E_sw, t, lo, scorer.start(E_sw, lo), dfr)
        dots = [(float(x), drawn[round(float(x), 4)]) for x in anch + post]

        def newsim(line, frames_):
            na, _nb = st.slice_of[line]
            return simulate_walk(L["switch_paths"]["end"][line], st, t_eff, end_arg, xy_of(st, na), line,
                                 STRIDE, 0, FPS, None, lambda q: None, frames=frames_, lead=False,
                                 shift_w=shift_w)

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


class LiveDisplay:
    """Frames for one recording, each computed from the windows that had ended by its time."""

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
        self.out = {}                 # pid -> {round(x, 4): xy}
        self.meta = {}                # pid -> lock line, switches, anchor facts
        self.n_decodes = 0

    # -- inputs --------------------------------------------------------------------------------
    def set_origin(self, t0_first: float) -> None:
        """The recording's first window start: the frame grid's origin, as `f3_render` sets it."""
        self.origin = float(t0_first)
        self.frames = frame_times(self.origin, 200000)

    def press(self, pid: int, t_press: float, a2_term: dict = None, committed_term: dict = None) -> None:
        self.passes.append({"pid": int(pid), "press": float(t_press), "end": None, "lo": None,
                            "a2": a2_term, "adj": committed_term})

    def end_press(self, pid: int, t_end: float) -> None:
        for p in self.passes:
            if p["pid"] == int(pid):
                p["end"] = float(t_end)

    def set_terms(self, pid: int, a2_term: dict = None, committed_term: dict = None) -> None:
        for p in self.passes:
            if p["pid"] == int(pid):
                p["a2"], p["adj"] = a2_term, committed_term

    def push(self, t0: float, t0_epoch: float, e_row, ge: float, e_end_row) -> None:
        """One completed window. First every frame that could not read it is drawn, from the
        windows before it; then it is added."""
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

    def close(self) -> None:
        self._draw_until(np.inf)

    # -- frames --------------------------------------------------------------------------------
    def _draw_until(self, x_stop: float) -> None:
        """Draw every frame before x_stop from the windows held now (all of which ended by then)."""
        if self.frames is None or not self.t0:
            return
        j0 = self.next_frame
        j1 = int(np.searchsorted(self.frames, x_stop, side="left"))
        if np.isinf(x_stop):
            # the recording stopped: `f3_render`'s grid is np.arange(t[0], t[-1] + WINDOW_S, 1 / FPS),
            # so the last frame is the last one before the last window's end
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
                    out[round(x, 4)] = CENTRE          # THE PARK: nothing to say yet, nothing read
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

    def _compose(self, p, x_max: float):
        from pipeline.constrained.night_arms import night_track
        from pipeline.constrained.night_common import STRIDE
        from pipeline.live.decoder import LOOKBACK_W
        k = len(self.t0) - 1
        a = max(0, p["lo"] - LOOKBACK_W)
        lo_rel = p["lo"] - a
        if k < p["lo"] + 2:
            return {}, [], {}                    # the lock's window has not ended: nothing is drawn
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
                # THE LOOK-AHEAD (item 3 of 30 Sep): the drawn path after the lock reads `extra` more windows
                # past each step within the locked line. night_track imports locked_chain_path at call time,
                # so this wrapper reaches the drawn paths of THIS composition only; the lock (the free path)
                # and every decision are untouched. Up to 2 windows keep every frame causal (the margin is
                # measured per frame: `margin_s`)
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
