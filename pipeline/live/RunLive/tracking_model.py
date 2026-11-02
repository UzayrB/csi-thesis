# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The shipped tracker: the five networks run on each window (FinalPool), the start-of-walk terms...

from __future__ import annotations

import json
import os
import time

import numpy as np

from pipeline.live.RunLive.tracking_session import TrackingSession

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
J = os.path.join
OUT = J(REPO_ROOT, "runs", "live", "final")
MODEL_CELLS = {"final": {"03": "f05_A3", "B2": "f05_B2"}, "zeroshot": {"B2": "z05_B2"}}
MIN_IDLE_WINDOWS = 10
DISPLAY_PROFILES = {
    "clean_1s_r0": {"candidate": "K1gf", "end_head": False, "sd_scale": 3.0,
                    "sett": {"prior_arm": "flatten_0.50", "prior_f": 0.5, "shift_w": 1.0, "head_offset_s": 1.0,
                             "switch": {"arm": "A", "theta": 2.0, "max_switches": 1, "final_m": 1.0, "radius_m": None}},
                    "gate_ref": "FCC.relgateU+abstain+a2w0.25+sd3.0",
                    "source": "runs/switch_radius_ship_2026-10-14/SHIP_PLAN.md (Uzayr, 14 Oct): clean_1s with the switch "
                              "radius removed"}}
DISPLAY_PROFILE = "clean_1s_r0"
FRAME_EPS_S = 1e-6


# The final model's five shared-encoder heads, applied to single windows.
class FinalPool:

    # Features.tracking_features_links on each window as stored (LivePool's, unchanged).
    @staticmethod
    def features(windows: np.ndarray) -> np.ndarray:
        from pipeline.live.RunLive.tracking_networks import LivePool
        return LivePool.features(windows)

    # The unscaled band energy, as LivePool computes it; the session applies the relative gate.
    @staticmethod
    def gate_energy(window: np.ndarray) -> float:
        from pipeline.constrained.RunLive.walking_gate import band_energy
        from pipeline.constrained.RunLive.shared_settings import FS
        from pipeline.live.RunLive.tracking_networks import LivePool
        return float(band_energy(LivePool.as_stored(window), FS))

    # Install_rrel's operation: float32 RSSI minus each link's idle mean (a Python float).
    @staticmethod
    def relative(rssi: np.ndarray, means) -> np.ndarray:
        R = np.array(rssi, dtype=np.float32)
        for li in range(R.shape[1]):
            R[:, li] = R[:, li] - float(means[li])
        return R

    # {head: (n, cells) float32 fused posterior}, on the RELATIVE RSSI.
    def head_probs(self, feats: np.ndarray, rssi: np.ndarray, means) -> dict:
        from pipeline.constrained.RunLive.network_shared import infer_shared
        R = self.relative(rssi, means)
        out = {}
        for name, _cells, (m, mu, sd), _p in self.heads:
            p, _pl = infer_shared(m, mu, sd, np.asarray(feats, np.float32), R, 128)
            out[name] = p.astype(np.float32)
        return out

    # Function emissions from probs.
    def emissions_from_probs(self, probs: dict) -> np.ndarray:
        from pipeline.constrained.RunLive.decoder_emissions import cell_emission, scaled_cell_emission
        from pipeline.constrained.RunLive.decoder_emissions import pool
        from pipeline.constrained.RunLive.decoder_emissions import g100_to_25
        parts = []
        for name, cells, _m, _p in self.heads:
            prob = probs[name].astype(float)
            if cells == 100:
                prob = g100_to_25(prob)
                prob = prob / np.maximum(prob.sum(axis=1, keepdims=True), 1e-300)
            parts.append(cell_emission(prob, self.st.xy, 25) if self.marg is None
                         else scaled_cell_emission(prob, self.st.xy, 25, self.marg, alpha=self.alpha))
        return pool(parts)


# The display head the profile draws with: DISP_END (final or zeroshot) for pre_clean, none (the pooled...
def end_head_for(st, alpha: float, which: str = "final", profile: str = None):
    if not DISPLAY_PROFILES[profile or DISPLAY_PROFILE]["end_head"]:
        return None
    raise SystemExit("REFUSED: the DISP_END display head is development code (support/final_model.py); the app's "
                     "display profile does not use it")


# LiveStartTerms with the decode variant's start terms: the A2 term at the variant's weight, and abstain...
class FinalStartTerms:

    # Creates the object.
    def __new__(cls, train_sessions, reader_tag, st, variant: str):
        from pipeline.constrained.RunLive.start_veto import variant_spec
        from pipeline.constrained.RunLive.start_veto import A2_WEIGHT
        from pipeline.live.RunLive.tracking_start_of_walk import LiveStartTerms

        # Class T.
        class _T(LiveStartTerms):
            # Function terms.
            def terms(self, a2_row, veto_row):
                import pipeline.constrained.RunLive.start_veto as R
                from pipeline.constrained.RunLive.start_veto import line_regions
                from pipeline.constrained.RunLive.start_veto import VETO_NATS
                from pipeline.constrained.RunLive.start_veto import VETO_THR, VETO_W
                lr = line_regions(self.st)
                out = {}
                if a2_row is not None:
                    P = self.a2.predict_proba(self.a2_sc.transform(a2_row[None]))[0]
                    classes = list(self.a2.classes_)
                    lp = np.log(np.clip(P, 1e-9, 1.0))
                    base = float(np.mean(lp))
                    out = {nm: self.a2w * float(lp[classes.index(r)] - base) for nm, r in lr.items() if r in classes}
                if veto_row is not None:
                    p = self.reader.predict_proba(self.v_sc.transform(veto_row[None]))[0]
                    ci = {c: i for i, c in enumerate(self.reader.classes_)}
                    if self.abstain:
                        if float(np.asarray(p, float).max()) >= R.ABSTAIN_THR:
                            lp = np.log(np.clip(np.asarray(p, float), 1e-9, 1.0))
                            base = float(np.mean(lp))
                            for nm, r in lr.items():
                                if r in ci:
                                    out[nm] = out.get(nm, 0.0) + R.ABSTAIN_W * float(lp[ci[r]] - base)
                    else:
                        for nm, r in lr.items():
                            v = -VETO_W * VETO_NATS if (r in ci and p[ci[r]] < VETO_THR) else 0.0
                            out[nm] = out.get(nm, 0.0) + v
                return out
        t = _T(train_sessions, reader_tag, st)
        spec = variant_spec(variant)
        t.a2w = spec["a2w"] if spec["a2w"] is not None else A2_WEIGHT
        t.abstain = bool(spec["abstain"])
        t.variant = variant
        return t


# TrackingSession with the final model: the pool above, relative RSSI and the relative gate fixed at the...
class FinalTrackingSession(TrackingSession):

    MODES = ("semi", "full")

    # Sets up the object.
    def __init__(self, *, pool: FinalPool, terms, G0: float, baseline: dict, session: str, stem: str, train,
                 test, reader_tag: str, pieces=None, end_head=None, mode: str = "semi",
                 display_profile: str = None):
        assert mode in self.MODES, mode
        self.mode = mode
        self.decisions_full = []
        self._full_pending = {}
        self.G0 = float(G0)
        self.rrel = None
        self.gate_scale = None
        self.stats = {}
        self._end = end_head
        super().__init__(tag=pool.tag, train=train, test=test, reader_tag=reader_tag, baseline=baseline,
                         session=session, stem=stem, pieces=pieces,
                         components={"pool": pool, "end_head": end_head or "pooled", "terms": terms})
        import dataclasses as _dc

        import pipeline.live.RunLive.tracking_display as LD
        self.display_profile = display_profile or DISPLAY_PROFILE
        prof = DISPLAY_PROFILES[self.display_profile]
        self.display_candidate = prof["candidate"]
        self.display.sett.update(LD.DISPLAY_CANDIDATES[self.display_candidate])
        self.display.sett.update(prof["sett"])
        if prof["sd_scale"] is not None:
            self.display.cfg_disp = _dc.replace(self.display.cfg_disp, sd_scale=float(prof["sd_scale"]))
        self.first_lock, self.lock_changes = {}, []
        d = self.display
        orig_draw, orig_push = d._draw_until, d.push
        self._in_push = False

        # Function push.
        def push(*a, **k):
            self._in_push = True
            try:
                orig_push(*a, **k)
            finally:
                self._in_push = False
        d.push = push

        # Function draw until.
        def draw_until(x_stop):
            if self._in_push:
                return
            orig_draw(x_stop)
            for pid, m in d.meta.items():
                ln = m.get("lock_line")
                if ln and pid not in self.first_lock:
                    self.first_lock[pid] = ln
                elif ln and ln != self.first_lock.get(pid):
                    self.lock_changes.append({"pid": int(pid), "first": self.first_lock[pid], "now": ln})
        d._draw_until = draw_until

    # Calibration_indices' windows (ended by the first press, idle) from the re-cut lattice: their per-link RSSI...
    def _final_stats(self, windows: list, first_press: float) -> None:
        from pipeline.io.RunLive.signal_windows import WALK_EDGE_S
        cal = [r for r in windows if float(r["t0"]) + 2.0 <= first_press + 1e-9
               and abs(float(r["t0"]) + 1.0 - first_press) > WALK_EDGE_S]
        if len(cal) < MIN_IDLE_WINDOWS:
            raise SystemExit(f"REFUSED: {len(cal)} idle windows before the first press, below {MIN_IDLE_WINDOWS}; "
                             f"record at least 10 s of stillness before the first walk")
        R = np.stack([np.asarray(r["rssi"], np.float32) for r in cal])
        self.rrel = [float(R[:, li].mean(dtype=np.float64)) for li in range(R.shape[1])]
        g = float(np.median([self.pool.gate_energy(r["X"]) for r in cal]))
        self.gate_scale = max(1.0, self.G0 / g)
        self.stats = {"n_idle_windows": len(cal), "rssi_idle_mean": self.rrel, "g_rec": g, "G0": self.G0,
                      "gate_scale": self.gate_scale}

    # Function rows.
    def _rows(self, r, pool: bool = True) -> dict:
        feats = FinalPool.features(r["X"][None])
        rssi = np.asarray(r["rssi"], np.float32)[None]
        ge = self.pool.gate_energy(r["X"]) * (self.gate_scale if self.gate_scale is not None else 1.0)
        out = {"k": r["k"], "t0": r["t0"], "t0_epoch": r["t0_epoch"], "feats": feats[0], "rssi": rssi[0],
               "e": None, "ge": ge, "e_end": None, "provisional": bool(r.get("provisional"))}
        if pool:
            assert self.rrel is not None, "the heads ran before the first press fixed the idle statistics"
            e = self.pool.emissions_from_probs(self.pool.head_probs(feats, rssi, self.rrel))[0]
            out["e"] = e
            out["e_end"] = self._end.emission(feats, rssi, self.rrel)[0] if self._end is not None else e
        return out

    # Function rows batch.
    def _rows_batch(self, recs: list, pool: bool) -> list:
        return [self._rows(r, pool=pool) for r in recs]

    # TrackingSession.press, with the idle statistics fixed between the re-cut and the rows.
    def press(self, pid: int, t_press: float) -> None:
        t_ = time.perf_counter()
        res = self.stream.press(t_press)
        first = self.first_press is None
        if first:
            self.first_press = float(t_press)
            self._final_stats(res["windows"], float(t_press))
        for k in res["dropped"] + res["withdrawn"]:
            self.win.pop(k, None)
        from pipeline.live.RunLive.tracking_windows import RECUT_BACK_S
        recent = [r for r in res["windows"] if float(r["t0"]) >= float(t_press) - RECUT_BACK_S - 0.5]
        older = [r for r in res["windows"] if float(r["t0"]) < float(t_press) - RECUT_BACK_S - 0.5]
        for r in recent:
            self.win[r["k"]] = self._rows(r, pool=True)
        for r in older:
            self.win[r["k"]] = self._rows(r, pool=False)
        self._sync()
        if first:
            self._adapt(float(t_press))
            self.display.set_origin(float(self.win[self.order[0]]["t0"]))
        if self.mode == "semi":
            for q, pp in self.passes.items():
                if pp.get("end") is None:
                    pp["end"] = float(t_press)
                    self.display.end_press(q, float(t_press))
        self.passes[int(pid)] = {"press": float(t_press), "end": None, "terms": None}
        self.decoder.press(float(t_press), int(pid))
        self.display.press(int(pid), float(t_press))
        if not first:
            self._park_drawn_ahead(int(pid), float(t_press))
        self.timing["press_s"].append(time.perf_counter() - t_)
        self.events.append((float(t_press), self.timing["press_s"][-1], "press", None))

    # Semi mode is never given an end press: it is REFUSED rather than ignored, so a caller cannot pass one by...
    def end_press(self, pid: int, t_end: float) -> None:
        if self.mode == "semi":
            raise AssertionError("semi-constrained mode takes no end press")
        super().end_press(pid, t_end)
        if self.mode == "full":
            self._full_pending[int(pid)] = float(t_end)
            self._full_due()

    # Function window.
    def _window(self, r) -> None:
        super()._window(r)
        if self._full_pending:
            self._full_due()
        self._draw_ahead()

    # TrackingSession.screen_state, with the verdict naming the mode's answer: semi, the line announced at the...
    def screen_state(self, now: float) -> dict:
        out = super().screen_state(now)
        v = out.get("verdict")
        if v and not v.get("pending"):
            if self.mode == "full":
                pid = max(self.passes, key=lambda q: self.passes[q]["press"])
                d = next((q for q in self.decisions_full if q["pass_id"] == pid), None)
                v["committed"] = d["final_line"] if d else None
                v["label"] = "committed at the end press (upper bound)"
            else:
                v["label"] = "committed line (the walk has ended)"
        return out

    # V1 on the screen: every frame is ready by its own time.
    def _draw_ahead(self) -> None:
        d = self.display
        if d.frames is None or not d.t0:
            return
        from pipeline.constrained.RunLive.shared_settings import WINDOW_S
        d._draw_until(float(d.t0[-1]) + WINDOW_S + float(self.stream.stride_s) - FRAME_EPS_S)

    # A start press inside frames already drawn ahead: those frames of the new walk are its park, the room...
    def _park_drawn_ahead(self, pid: int, t_press: float) -> None:
        from pipeline.constrained.RunLive.display_rule import CENTRE
        from pipeline.live.RunLive.tracking_display import LATENCY_S
        d = self.display
        if d.frames is None:
            return
        j0 = int(np.searchsorted(d.frames, float(t_press), side="left"))
        out = d.out.setdefault(int(pid), {})
        for x in d.frames[j0:d.next_frame]:
            assert x < float(t_press) + LATENCY_S, "a frame drawn ahead lies past the new walk's park"
            out[round(float(x), 4)] = CENTRE

    # Function decided.
    def _decided(self, row, at_close: bool = False) -> None:
        super()._decided(row, at_close)
        if self.mode == "semi":
            pid = int(row["pass_id"])
            t_exit = float(self.decoder.t0[int(row["live_exit_window"])]) + 1.0
            pp = self.passes.get(pid)
            if pp is not None and (pp.get("end") is None or t_exit < pp["end"]):
                pp["end"] = t_exit
                self.display.end_press(pid, t_exit)

    # Full mode: the committed line with the walk ending at the end press, once the last window whose centre is...
    def _full_due(self, final: bool = False) -> None:
        import numpy as _np
        from pipeline.constrained.RunLive.decoder_lines import transition_matrix
        from pipeline.constrained.RunLive.decoder_semi_bounded import chain_totals, pick_line
        d = self.decoder
        for pid, t_end in list(self._full_pending.items()):
            p = next((q for q in d.passes if q["pid"] == pid), None)
            if p is None or p["lo"] is None:
                continue
            cen = _np.asarray(d.t0, float) + 1.0
            hi = int(_np.searchsorted(cen, t_end + 1e-9, side="right")) - 1
            arrived = hi < len(d.t0) - 1 or final
            if not arrived or hi < p["lo"]:
                continue
            e = _np.asarray(d.e[p["lo"]:hi + 1], float)
            tot = chain_totals(e, self.st, slice(0, hi + 1 - p["lo"]), transition_matrix(self.st, "tight", with_null=False),
                               d.opts.get("chain_logprior"))
            if p["term"]:
                tot = {k: v + float(p["term"].get(k, 0.0)) for k, v in tot.items()}
            line = pick_line(tot, self.st, bool(d.opts.get("family_first")))
            self.decisions_full.append({"pass_id": pid, "final_line": line, "hi_end": hi, "t_end": t_end,
                                        "decided_at_window": len(d.t0) - 1})
            del self._full_pending[pid]

    # Function close.
    def close(self) -> None:
        super().close()
        if self._full_pending:
            self._full_due(final=True)



KEYS_TITLE_TRACKING = "tracking: press SPACE in the Terminal window, not here"


# Function preflight.
def preflight(baseline: str = None, at: float = None) -> dict:
    raise SystemExit("REFUSED: start tracking through main.py, which sets the frozen tracker's pre-flight")


# Function components.
def _components(cell: str, variant: str):
    raise SystemExit("REFUSED: start tracking through main.py, which loads the frozen tracker")


# Function final variant.
def final_variant() -> str:
    raise SystemExit("REFUSED: start tracking through main.py, which sets the frozen tracker's variant")


# The board rigs' READY banner in the Terminal: where the keys go, what to press.
def rig_banner(lines: list) -> None:
    w = max(len(x) for x in lines) + 4
    print("\n" + "=" * w, flush=True)
    for x in lines:
        print(f"  {x}", flush=True)
    print("=" * w + "\n", flush=True)


# The board rigs' start-up status in the Terminal: numbered steps with their time.
class RigSteps:

    # Sets up the object.
    def __init__(self, n: int):
        self.n, self.i, self.t0, self.t = n, 0, time.time(), None

    # Function step.
    def step(self, what: str) -> None:
        self.done()
        self.i += 1
        self.t = time.time()
        print(f"[{self.i}/{self.n}] {what} ...", flush=True)

    # Function done.
    def done(self, note: str = "") -> None:
        if self.t is not None:
            print(f"      done in {time.time() - self.t:.0f} s{(': ' + note) if note else ''}", flush=True)
            self.t = None


# ON THE BOARDS: opens the serial ports.
def rig_inner(baseline: str, minutes: float, mode: str = "semi") -> int:
    from pipeline.constrained.RunLive.shared_settings import force_cpu
    force_cpu()
    steps = RigSteps(4)
    print("TRACKING, the live app on the boards: starting (about a minute)", flush=True)
    steps.step("Pre-flight: checking the shipped model's files and the baseline (about 25 s)")
    chk = preflight(baseline)
    for k, v in chk.items():
        print(f"  {'ok  ' if v else 'FAIL'} {k}")
    if not chk["ALL"]:
        raise SystemExit("REFUSED: the pre-flight failed; nothing was opened")
    steps.step("Loading the tracking model: five networks, the readers and the start terms (about 30 s)")
    PC, c, pieces, pool, terms, G0 = _components(MODEL_CELLS["final"]["03"], final_variant())
    from pipeline.constrained.RunLive.receiver_macs import room_a_macs
    from pipeline.live.RunLive.boards_run import TrackingConsumer, run
    from pipeline.live.RunLive.tracking_screen import Screen
    from pipeline.live.RunLive.boards_run import identify, mapping_by_mac
    from pipeline.io.RunLive.signal_windows import session_baseline
    steps.step("Naming the boards by their MAC addresses")
    nodes = mapping_by_mac(identify(), room_a_macs(J(REPO_ROOT, "data")))
    nodes = {k: v for k, v in nodes.items() if k in ("RX1", "RX2", "RX3")}
    steps.done(", ".join(f"{k} on {v}" for k, v in sorted(nodes.items())))
    st, _cfg, _ne, _tr, _kind, alpha = pieces
    s = FinalTrackingSession(pool=pool, terms=terms, G0=G0, session="live", stem=time.strftime("rig_final_%Y%m%d_%H%M%S"),
                             train=c["train"], test=(c["test"],), reader_tag=c["reader_tag"], pieces=pieces,
                             baseline=session_baseline(baseline), end_head=end_head_for(st, alpha), mode=mode)
    print(f"mode {mode}: " + ("SPACE once per walk, at the start tape" if mode == "semi" else "SPACE at the start and at the end"))
    from pipeline.live.RunLive.tracking_session import Logger
    log = Logger(s)

    # Class Logged Consumer.
    class LoggedConsumer(TrackingConsumer):
        ticks, redraws = 0, 0

        # Function handle.
        def handle(self, r):
            log.event(time.monotonic())
            super().handle(r)

        # Function tick.
        def tick(self, now):
            log.event(time.monotonic())
            super().tick(now)
            self.ticks += 1
            self.redraws += int(self.last_draw == now)

    steps.step("Opening the tracking window")
    con = LoggedConsumer(s, Screen(s.st, headless=False, title=KEYS_TITLE_TRACKING))
    steps.done()
    rig_banner(["READY.",
                "Click on THIS Terminal window: the keys are read here, not in the plot window.",
                "Stand still for 10 s, then press SPACE once as each walk starts (at the start tape)."
                if mode == "semi" else "Press SPACE at the start and again at the end of each walk.",
                "q quits."])
    try:
        rc = run(con, nodes, duration=minutes * 60.0 if minutes else None, mode="tracking", stem=s.stem,
                 run_config={"model": "final", "mode": mode, "cell": MODEL_CELLS["final"]["03"],
                             "display_profile": DISPLAY_PROFILE, "baseline": os.path.abspath(baseline)})
    finally:
        log.event(time.monotonic())
        close_error = None
        try:
            s.close()
        except Exception as e:
            close_error = f"{type(e).__name__}: {e}"
        log.finish()
        rec = getattr(con, "record_dir", None)
        if rec:
            with open(J(rec, f"{s.stem}.log.jsonl"), "w", encoding="utf-8") as f:
                for r_ in log.rows:
                    f.write(json.dumps(r_, default=float) + "\n")
            with open(J(rec, f"{s.stem}.gt.json"), "w", encoding="utf-8") as f:
                json.dump({"rig": True, "mode": mode, "baseline": os.path.abspath(baseline),
                           "baseline_capture": os.path.abspath(baseline), "session": "live",
                           "cell": MODEL_CELLS["final"]["03"], "display_profile": DISPLAY_PROFILE,
                           "passes": [{"pass_id": int(pid), "t_start": float(p["press"]),
                                       "t_end": (float(p["end"]) if mode == "full" and p.get("end") is not None else None)}
                                      for pid, p in sorted(s.passes.items())]}, f, indent=1)
            ws = [float(x) for x, prov in s.timing["window_s"] if not prov]
            dots = [r_ for r_ in log.rows if r_["kind"] == "dot" and r_.get("computed_at") is not None]
            lag = [max(0.0, float(r_["computed_at"]) - float(r_["x"])) for r_ in dots]
            lock_late = [float(r_["at"]) - (float(s.passes[r_["pid"]]["press"]) + 2.0)
                         for r_ in log.rows if r_["kind"] == "lock" and r_["pid"] in s.passes]
            q_ = lambda v, p_: float(np.percentile(v, p_)) if v else None
            from pipeline.constrained.RunLive import network_build as nets
            with open(J(rec, f"{s.stem}.summary.json"), "w", encoding="utf-8") as f:
                json.dump({"device": str(nets.device()), "display_profile": DISPLAY_PROFILE, "mode": mode,
                           "preflight": chk, "passes": len(s.passes), "committed": len(s.decisions),
                           "locks": len(log.locks), "frames": log.n_frames, "ticks": con.ticks, "redraws": con.redraws,
                           "window_service_s": {"median": q_(ws, 50), "p95": q_(ws, 95), "max": max(ws) if ws else None,
                                                "n": len(ws), "values": ws},
                           "press_service_s": {"median": q_(s.timing["press_s"], 50),
                                               "max": max(s.timing["press_s"]) if s.timing["press_s"] else None,
                                               "values": [float(x) for x in s.timing["press_s"]]},
                           "draw_lag_s": {"median": q_(lag, 50), "max": max(lag) if lag else None,
                                          "frames_late_over_0.1s": int(sum(x > 0.1 for x in lag)),
                                          "frames_late_over_0.5s": int(sum(x > 0.5 for x in lag)), "n": len(lag)},
                           "lock_late_s": {"median": q_(lock_late, 50), "max": max(lock_late) if lock_late else None},
                           "exit": rc if "rc" in locals() else None, "close_error": close_error,
                           "receiver_outages": con.outages,
                           "walks_overlapping_an_outage": sorted(int(pid) for pid, p in s.passes.items()
                                                                 for o in con.outages if p["press"] - 1.0 <= (o["to"] or np.inf)
                                                                 and p["press"] + 10.0 >= o["from"])}, f, indent=1, default=str)
    os.makedirs(J(REPO_ROOT, "runs", "live", "rig"), exist_ok=True)
    with open(J(REPO_ROOT, "runs", "live", "rig", f"{s.stem}.json"), "w", encoding="utf-8") as f:
        json.dump({**con.summary(), "model": "final", "mode": mode, "stats": s.stats,
                   "decisions_full": s.decisions_full, "first_lock": s.first_lock, "lock_changes": s.lock_changes},
                  f, indent=1, default=str)
    return rc
