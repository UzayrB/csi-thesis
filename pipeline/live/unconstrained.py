"""The UNCONSTRAINED mode (rule/APP_PREREG.md section 6, hashed 09:26): no press at all.

    python3 -m pipeline.live.unconstrained stat_s        # (a) S, from the training recordings only
    python3 -m pipeline.live.unconstrained choose_m      # (b) the m grid on the three rotations, through the app
    python3 -m pipeline.live.unconstrained decide_m      # (b) the chosen m: runs/live/unconstrained/M.json
    python3 -m pipeline.live replay --session B2 --presses none      # the app, no press, the chosen m
    python3 -m pipeline.live.unconstrained score --model final --session B2      # (c)

(a) The recording's statistics without a press. The relative RSSI means, g_rec and AdaBN come from the
    windows lying wholly in the first S seconds of the recording. S is the 10th percentile, over the
    training sessions' walk recordings (A1, A2 and B1; calibration recordings excluded), of
    (the first start press - the recording's first window start - 3.0 s). At least 10 windows, or refused.
(b) A walk start, (c) the matching and (d) the report follow the pre-registration; they are built after
    (a), last in the order.

This file reads the training recordings' first press only to fix S; the app in this mode is never given a
press.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = os.path.join
OUT = J(REPO_ROOT, "runs", "live", "unconstrained")
#: the start detector's spread, PINNED under every display profile (the Mastermind's ruling, 10 Oct): it decides when a
#: walk starts, so it does not follow the display's spread (the clean profile draws at 3.0). The no-press figures
#: (unconstrained_m4_disp-K1g) were made at 4.5
DETECTOR_SD_SCALE = 4.5
TRAIN = ("01", "02", "B1")
#: a cell whose environment binds every training session's raw data (A1+A2 -> B1; B1 is read as a session)
ENV_CELL = "d4c_fuse_0102_to_B1"


NEG = -1e18
M_GRID = (1, 2, 3, 4)
ROTS = {"B1": ("rotB1", "B1", 2.0), "A2": ("rotA2", "02", 1.0), "A1": ("rotA1", "01", 1.0)}
MATCH_S = 1.5
#: a content-addressed cache of window rows (heads, relative RSSI, gate), keyed by the window's raw radio and the
#: recording's statistics: the m grid replays one recording four times, and a window cut from the same radio
#: with the same statistics has the same rows. None: off (every figure run computes afresh)
ROWS_CACHE = None
#: the m grid only: the display draws no frame. It feeds neither the detector nor the decoder, and the objective
#: reads neither a dot nor a lock, so the choice of m is the same; the replays run several times faster where
#: false starts are many (Room A's standing block). Checked on B1: identical detections and committed lines
NO_DISPLAY = os.environ.get("UNC_NO_DISPLAY") == "1"


class StartDetector:
    """(b) The display decoder, run continuously: the full-state decode (paths, still and transit states) with
    the frozen display settings (the display's configuration at sd_scale 4.5, its transition matrix built with
    the 0.80 m per window cap, the pooled emission, the scaled gate, the gate veto), as `decoder2.
    provisional_track` runs it: the lag-1 argmax of the UN-collapsed forward belief (Stage 3's live track), one
    window at a time. When window t arrives, window t - 1's state is the one on the best path ending at t.
    The null level's reference is the 0.75 quantile of the path peaks of every window so far (the display
    calibrates on the windows it holds). It consumes each window once, as it arrives, and is never re-decoded
    when a start re-cuts the lattice.

    (A first version committed each window at lag 0 with binding commitments, as `fixed_lag_viterbi`, like the
    display's free path. On one development recording, B1 P4, it never left the transit states in 712 windows:
    the display's path starts each walk ON a line through its start prior at the press, and a continuous decode
    has no press, so entering a line's first state never won a single greedy step. Recorded in
    rule/APP_PREREG_ADDENDUM_2.md; no test session was replayed in this mode before the change.)"""

    def __init__(self, st, cfg_disp, ne, transit, caps, m: int):
        import copy
        import dataclasses as dc

        from pipeline.constrained.decoder2 import Space, transition_matrix2
        from pipeline.live.display import DISPLAY_CAP_M_PER_WINDOW
        assert int(getattr(cfg_disp, "veto_hysteresis", 1)) <= 1, "per-window stacking needs a veto hysteresis of 1"
        cfg_disp = dc.replace(cfg_disp, sd_scale=DETECTOR_SD_SCALE)      # pinned, whatever the display's profile
        self.sd_scale = float(cfg_disp.sd_scale)
        self.sp = Space(st, cfg_disp)
        with caps.cap(DISPLAY_CAP_M_PER_WINDOW):
            self.lT = transition_matrix2(st, cfg_disp, transit)
        self.ne = copy.deepcopy(ne)
        self.m = int(m)
        self.peaks, self.dp, self.t_prev = [], None, None
        self.run, self.run_start = 0, None
        self.rows = []

    def push(self, t0: float, e_row, ge: float) -> None:
        from pipeline.constrained.decoder2 import stack2
        e_row = np.asarray(e_row, float)
        self.peaks.append(float(e_row.max()))
        self.ne.calibrate(np.asarray(self.peaks)[:, None])
        e = stack2(e_row[None], np.array([float(ge)]), self.ne, self.sp)[0]
        if self.dp is None:                              # the first window: nothing to decide yet
            self.dp, self.t_prev = e - e.max(), float(t0)
            return
        mm = self.dp[:, None] + self.lT
        back = mm.argmax(0)
        dp = mm.max(0) + e
        dp -= dp.max()
        j_prev = int(back[int(dp.argmax())])            # the previous window's state on the best path ending now
        self.dp = dp
        on = j_prev < self.sp.S
        if on:
            self.run += 1
            if self.run == 1:
                self.run_start = self.t_prev + 1.0      # the centre of the first on-line window
        else:
            self.run, self.run_start = 0, None
        self.rows.append({"t0": self.t_prev, "state": j_prev, "on_line": bool(on), "run": self.run})
        self.t_prev = float(t0)


def first_window_t0(sdir: str, stem: str, clock: str = "causal") -> float:
    """The app's own first window start on a recording: the radio pushed into the live stream until it
    cuts its first window (the base lattice, no press)."""
    from pipeline.live.replay import recording_events
    from pipeline.live.stream import LiveStream
    import pipeline.io.windows as W
    ev, _info = recording_events(sdir, stem, end_presses=False, causal_anchor=(clock == "causal"))
    st = LiveStream(W.session_baseline(W.baseline_dir_for(sdir, stem)))
    for e_ in ev:
        if e_[2] != "frame":
            continue
        _t, _o, _k, n, ts, amp, t_host, rssi, t_mono = e_
        st.push_rssi(n, t_host, rssi)
        if ts is None:
            continue
        recs = st.push_packet(n, ts, amp, t_host=t_host, t_mono=t_mono)
        if recs:
            return float(recs[0]["t0"])
    raise SystemExit(f"{stem}: no window cut")


def load_S() -> float:
    with open(J(OUT, "S.json"), encoding="utf-8") as f:
        d = json.load(f)
    if d["refused"]:
        raise SystemExit("REFUSED: fewer than 10 windows lie in S")
    return float(d["S_s"])


def load_m() -> int:
    """(b)'s m, chosen on the rotations (runs/live/unconstrained/M.json, written by `decide_m`)."""
    with open(J(OUT, "M.json"), encoding="utf-8") as f:
        return int(json.load(f)["chosen_m"])


def make_session(m: int, S: float = None, **kw):
    """The unconstrained session: FinalTrackingSession's semi-constrained walk machinery, with no press given;
    its statistics fixed at S and its starts detected (section 6)."""
    from pipeline.live.final_model import FinalTrackingSession, MIN_IDLE_WINDOWS

    class UnconstrainedSession(FinalTrackingSession):
        def __init__(self, **k):
            super().__init__(mode="semi", **k)
            self.m, self.S = int(m), float(S if S is not None else load_S())
            self._fixed, self.w0, self._internal = False, None, False
            self.detector = StartDetector(self.st, self.display.cfg_disp, self.display.ne, self.display.transit,
                                          self.caps, self.m)
            self.detections, self._used_run = [], None

        # -- no press is ever given --------------------------------------------------------------
        def press(self, pid, t_press):
            if not self._internal:
                raise AssertionError("the unconstrained mode takes no press")
            super().press(pid, t_press)

        def end_press(self, pid, t_end):
            raise AssertionError("the unconstrained mode takes no press")

        # -- (a) the statistics, at S ------------------------------------------------------------
        def _final_stats(self, windows, first_press):
            assert self._fixed, "a start before the statistics were fixed"

        def _adapt(self, first_press):
            assert self._fixed, "a start before the statistics were fixed"

        def _rows(self, r, pool=True):
            pool = bool(pool or self._fixed)
            if ROWS_CACHE is None or not pool:
                return super()._rows(r, pool=pool)
            import hashlib
            key = (hashlib.blake2b(np.ascontiguousarray(r["X"]).tobytes()
                                   + np.ascontiguousarray(np.asarray(r["rssi"], np.float32)).tobytes(),
                                   digest_size=16).hexdigest(), tuple(self.rrel), float(self.gate_scale))
            hit = ROWS_CACHE.get(key)
            if hit is None:
                hit = super()._rows(r, pool=True)
                ROWS_CACHE[key] = hit
            return {**hit, "k": r["k"], "t0": r["t0"], "t0_epoch": r["t0_epoch"], "provisional": bool(r.get("provisional"))}

        def _fix_stats(self):
            from pipeline.io.windows import WALK_EDGE_S          # noqa: F401  (the idle rule is S itself here)
            cal = [r for r in self.stream.windows.values()
                   if float(r["t0"]) >= self.w0 - 1e-9 and float(r["t0"]) + 2.0 <= self.w0 + self.S + 1e-9]
            if len(cal) < MIN_IDLE_WINDOWS:
                raise SystemExit(f"REFUSED: {len(cal)} windows in the first S = {self.S} s, below {MIN_IDLE_WINDOWS}")
            R = np.stack([np.asarray(r["rssi"], np.float32) for r in cal])
            self.rrel = [float(R[:, li].mean(dtype=np.float64)) for li in range(R.shape[1])]
            g = float(np.median([self.pool.gate_energy(r["X"]) for r in cal]))
            self.gate_scale = max(1.0, self.G0 / g)
            self.stats = {"n_idle_windows": len(cal), "rssi_idle_mean": self.rrel, "g_rec": g, "G0": self.G0,
                          "gate_scale": self.gate_scale, "S_s": self.S, "w0": self.w0}
            self._fixed = True
            # AdaBN on the same windows (as `_adapt` runs it on the idle windows before a first press)
            rows = {r["k"]: self._rows(r, pool=True) for r in cal}
            F = np.stack([rows[k]["feats"] for k in rows]).astype(np.float32)
            Rr = np.stack([rows[k]["rssi"] for k in rows]).astype(np.float32)
            self.adaptation = self.terms.adapt(F, Rr)
            # every held window's rows again, with the heads, the relative RSSI and the gate; lists re-synced
            for k in list(self.win):
                rec = self.stream.windows.get(k)
                if rec is not None:
                    self.win[k] = self._rows(rec, pool=True)
            self._sync()

        # -- (b) the starts --------------------------------------------------------------------------
        def _window(self, r):
            if self.w0 is None:
                self.w0 = float(r["t0"])
            super()._window(r)
            if not self._fixed:
                if float(r["t0"]) + 2.0 > self.w0 + self.S + 1e-9:
                    self._fix_stats()
                    # the detector runs from the recording's first window: every window held now, in order (the
                    # idle ones inside S included); a start is looked for only from the next window on
                    for k in self.order:
                        w = self.win[k]
                        self.detector.push(float(w["t0"]), w["e"], w["ge"])
                return
            w = self.win[r["k"]]
            self.detector.push(float(w["t0"]), w["e"], w["ge"])
            self._maybe_start()

        def _maybe_start(self):
            d = self.detector
            if d.run < d.m or d.run_start is None or self._used_run == d.run_start:
                return
            decided = {int(x["pass_id"]) for x in self.decisions}
            if any(int(p) not in decided for p in self.passes):
                return                                  # a walk is open: its causal exit has not been declared
            if self.decisions:
                last = self.decisions[-1]
                if d.run_start <= float(self.decoder.t0[last["exit_window"]]) + 1.0 + 1e-9:
                    return                              # the run began at or before the last walk's exit
            self._used_run = d.run_start
            pid = len(self.passes) + 1
            # detected when the window after the run's m-th arrived (lag 1): that window's end
            self.detections.append({"pid": pid, "t_start": d.run_start, "detected_at_t0": d.t_prev,
                                    "at": d.t_prev + 2.0, "m": d.m})
            self._internal = True
            try:
                self.press(pid, d.run_start)
            finally:
                self._internal = False
            # the start is in the past: the walk's first window is the first centred at or after it, as it is for a
            # press in real time (push sets it only from the windows arriving after the press)
            lo = next((i for i, t in enumerate(self.decoder.t0) if t + 1.0 >= d.run_start), None)
            for p in self.decoder.passes + self.display.passes:
                if p["pid"] == pid and p.get("lo") is None and lo is not None:
                    p["lo"] = lo
            self._late_frames(pid, d.run_start)

        def _park_drawn_ahead(self, pid, t_press):
            """Replaced by `_late_frames`: a detected start may lie past frames already drawn, park and beyond."""

        def _late_frames(self, pid, t_start):
            """The new walk's frames between its start and the frames already drawn: its park and, when the
            start is detected after start + 2.0 s, its first decoded frames. Drawn now, at detection (their draw
            lag shows it); no other walk's frame is redrawn."""
            dsp = self.display
            if dsp.frames is None:
                return
            j0 = int(np.searchsorted(dsp.frames, float(t_start), side="left"))
            j1 = dsp.next_frame
            if j1 <= j0:
                return
            keep_passes, keep_next = dsp.passes, dsp.next_frame
            try:
                dsp.passes = [p for p in keep_passes if p["pid"] == int(pid)]
                dsp.next_frame = j0
                dsp._draw_until(float(dsp.frames[j1]) - 1e-9)
            finally:
                dsp.passes, dsp.next_frame = keep_passes, keep_next

    s = UnconstrainedSession(**kw)
    if NO_DISPLAY:
        s.display._draw_until = lambda x_stop: None
    return s


def stat_s_inner() -> int:
    from pipeline.constrained import pd_cells as PC
    from pipeline.constrained.recordings import session_recordings
    rows = []
    for session in TRAIN:
        sdir = PC.raw_dir(session)
        cal = PC.cal_stems(session)
        for _s, stem in session_recordings(session):
            if stem in cal:
                continue
            with open(J(sdir, f"{stem}.gt.json"), encoding="utf-8") as f:
                p1 = min(float(p["t_start"]) for p in json.load(f)["passes"])
            w0 = first_window_t0(sdir, stem)
            rows.append({"session": session, "stem": stem, "first_press_minus_first_window_s": round(p1 - w0, 3),
                         "idle_span_s": round(p1 - w0 - 3.0, 3)})
            print(f"{session} {stem}: first press - first window = {p1 - w0:.3f} s", flush=True)
    span = np.array([r["idle_span_s"] for r in rows])
    S = float(np.percentile(span, 10))
    n_win = int(np.floor((S - 2.0) / 0.5 + 1e-9)) + 1 if S >= 2.0 else 0     # windows wholly inside [0, S]
    out = {"S_s": round(S, 3), "rule": "10th percentile of (first press - first window start - 3.0 s) over the "
                                         "training walk recordings (A1, A2, B1), calibration excluded",
           "n_recordings": len(rows), "windows_wholly_in_S": n_win, "MIN_IDLE_WINDOWS": 10,
           "refused": n_win < 10, "rows": rows, "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    os.makedirs(OUT, exist_ok=True)
    with open(J(OUT, "S.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: out[k] for k in ("S_s", "n_recordings", "windows_wholly_in_S", "refused")}), flush=True)
    return 0


def choose_m_inner(rot: str, ms=None) -> int:
    """One rotation: every recording through the app in the unconstrained mode at every m of the grid."""
    global ROWS_CACHE
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    from pipeline.constrained.recordings import session_recordings
    from pipeline.live.app_replay import VARIANT, cell_for, replay_inner
    from pipeline.live.final_model import _components
    model, session, _w = ROTS[rot]
    comp = _components(cell_for(model, session), VARIANT)
    cal = comp[0].cal_stems(session)
    for _s, stem in session_recordings(session):
        if stem in cal:
            continue
        ROWS_CACHE = {}
        for m in (ms or M_GRID):
            replay_inner(model, session, stem, "none", "causal", False, components=comp, m=m)
    ROWS_CACHE = None
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["choose_m"]:
        ms = [int(argv[argv.index("--m") + 1])] if "--m" in argv else None
        if "--inner" in argv:
            return choose_m_inner(argv[argv.index("--rot") + 1], ms)
        from pipeline.live.app_replay import cell_for
        from pipeline.live.final_model import _env
        rots = [argv[argv.index("--rot") + 1]] if "--rot" in argv else list(ROTS)
        for rot in rots:
            model, session, _w = ROTS[rot]
            code = subprocess.call([sys.executable, "-m", "pipeline.live.unconstrained", "choose_m", "--inner", "--rot", rot]
                                   + (["--m", str(ms[0])] if ms else []),
                                   cwd=REPO_ROOT, env=dict(_env(cell_for(model, session)), OMP_NUM_THREADS="1"))
            if code:
                return code
        return 0
    if argv[:1] == ["decide_m"]:
        from pipeline.live.app_score import choose_m               # the scorer: the one reader of labels
        choose_m()
        return 0
    if argv[:1] == ["score"]:
        from pipeline.live.app_score import score_unconstrained
        score_unconstrained(argv[argv.index("--model") + 1], argv[argv.index("--session") + 1])
        return 0
    if argv[:1] == ["stat_s"]:
        if "--inner" in argv:
            return stat_s_inner()
        from pipeline.live.final_model import _env
        return subprocess.call([sys.executable, "-m", "pipeline.live.unconstrained", "stat_s", "--inner"], cwd=REPO_ROOT,
                               env=dict(_env(ENV_CELL), OMP_NUM_THREADS="1"))
    raise SystemExit("usage: python3 -m pipeline.live.unconstrained stat_s | choose_m [--rot B1|A2|A1] | decide_m | "
                     "score --model <m> --session <s>")


if __name__ == "__main__":
    sys.exit(main())
