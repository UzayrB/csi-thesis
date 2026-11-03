# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: One tracking session, from the first packet to the last: packets and SPACE presses go in (T5); 2 s windows...

from __future__ import annotations

import copy
import dataclasses
import time

import numpy as np

from pipeline.io.signals import WALK_EDGE_S
from pipeline.tracking.decoder import LiveDecoder, chain_totals, pick_line, transition_matrix
from pipeline.tracking.display import CENTRE, DISPLAY_CANDIDATES, LATENCY_S, LiveDisplay
from pipeline.tracking.settings import WINDOW_S
from pipeline.tracking.tracker import DISPLAY_PROFILE, DISPLAY_PROFILES
from pipeline.tracking.windows import RECUT_BACK_S, LiveStream

MIN_IDLE_WINDOWS = 10
FRAME_EPS_S = 1e-6


# The frozen tracker on one stream of packets: semi mode (the shipped one) takes one SPACE per walk, at its...
class Session:

    MODES = ("semi", "full")

    # Tracker: tracker.load()'s Tracker.
    def __init__(self, tracker, *, session: str, stem: str, baseline: dict, mode: str = "semi",
                 display_profile: str = None):
        assert mode in self.MODES, mode
        self.tracker, self.mode = tracker, mode
        self.st = tracker.st
        self.pool, self.terms, self.G0 = tracker.networks, tracker.start_terms, float(tracker.G0)
        self.tag = tracker.networks.tag
        self.train, self.test, self.reader_tag = tuple(tracker.meta["train"]), (tracker.meta["test"],), tracker.meta["reader_tag"]
        opts = copy.deepcopy(tracker.opts)
        opts["entry"], opts["entry_window_m"], opts["start_term"] = "soft", 1.0, None
        self.display_profile = display_profile or DISPLAY_PROFILE
        prof = DISPLAY_PROFILES[self.display_profile]
        self.display_candidate = prof["candidate"]
        sett = copy.deepcopy(tracker.display_settings)
        sett.update(DISPLAY_CANDIDATES[self.display_candidate])
        sett.update(prof["sett"])
        self.stream = LiveStream(baseline)
        self.decoder = LiveDecoder(self.st, tracker.cfg, tracker.ne, tracker.transit, opts, session, stem)
        self.display = LiveDisplay(self.st, tracker.cfg, tracker.ne, tracker.transit, opts, session, stem, sett)
        if prof["sd_scale"] is not None:
            self.display.cfg_disp = dataclasses.replace(self.display.cfg_disp, sd_scale=float(prof["sd_scale"]))
        self.session, self.stem = session, stem
        self.win = {}
        self.order = []
        self.passes = {}
        self.first_press = None
        self.adaptation = None
        self.decisions, self.decisions_full = [], []
        self._full_pending = {}
        self.truth = None
        self.rrel, self.gate_scale, self.stats = None, None, {}
        self.first_lock, self.lock_changes = {}, []
        self.timing = {"window_s": [], "press_s": [], "cut_s": []}
        self.events = []
        self.log = None


    # Function rssi.
    def rssi(self, node, t_host, rssi) -> None:
        self.stream.push_rssi(node, t_host, rssi)

    # A packet whose RSSI was already pushed at arrival (the rig's path: CSI waits for its clock fit).
    def csi(self, node, t, amplitude, t_host, t_mono) -> None:
        t_ = time.perf_counter()
        recs = self.stream.push_packet(node, t, amplitude, t_host=t_host, t_mono=t_mono)
        cut = (time.perf_counter() - t_) / len(recs) if recs else 0.0
        for r in recs:
            t1 = time.perf_counter()
            self._window(r)
            self.events.append((float(t_mono), cut + time.perf_counter() - t1, "window", float(r["t0"])))

    # A start press: the windows re-cut on it, the idle statistics fixed at the first one, then the walk opens...
    def press(self, pid: int, t_press: float) -> None:
        t_ = time.perf_counter()
        res = self.stream.press(t_press)
        first = self.first_press is None
        if first:
            self.first_press = float(t_press)
            self._idle_stats(res["windows"], float(t_press))
        for k in res["dropped"] + res["withdrawn"]:
            self.win.pop(k, None)
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

    # Full mode's end press.
    def end_press(self, pid: int, t_end: float) -> None:
        if self.mode == "semi":
            raise AssertionError("semi-constrained mode takes no end press")
        self.stream.end_press(t_end)
        if int(pid) in self.passes:
            self.passes[int(pid)]["end"] = float(t_end)
        self.display.end_press(int(pid), float(t_end))
        self._full_pending[int(pid)] = float(t_end)
        self._full_due()

    # The stream stopped: the last windows, the last frames, and every open walk decided.
    def close(self) -> None:
        res = self.stream.close()
        for k in res["withdrawn"]:
            self.win.pop(k, None)
        if res["withdrawn"]:
            self._sync()
        for r in res["windows"]:
            self._window(r)
        self.draw_until(np.inf)
        for row in self.decoder.close():
            self._decided(row, at_close=True)
        if self._full_pending:
            self._full_due(final=True)


    # Function window.
    def _window(self, r) -> None:
        t_ = time.perf_counter()
        w = self._rows(r, pool=not r.get("provisional"))
        self.win[r["k"]] = w
        self.order.append(r["k"])
        self._terms_due(float(w["t0"]))
        self.display.push(w["t0"], w["t0_epoch"], w["e"], w["ge"])
        for row in self.decoder.push(w["t0"], w["t0_epoch"], w["e"], w["ge"]):
            self._decided(row)
        self.timing["window_s"].append((time.perf_counter() - t_, bool(w["provisional"])))
        if self._full_pending:
            self._full_due()
        self._draw_ahead()

    # A window's features, RSSI and relative gate energy and, with pool, the five networks' pooled emission (on...
    def _rows(self, r, pool: bool = True) -> dict:
        feats = self.pool.features(r["X"][None])
        rssi = np.asarray(r["rssi"], np.float32)[None]
        ge = self.pool.gate_energy(r["X"]) * (self.gate_scale if self.gate_scale is not None else 1.0)
        out = {"k": r["k"], "t0": r["t0"], "t0_epoch": r["t0_epoch"], "feats": feats[0], "rssi": rssi[0],
               "e": None, "ge": ge, "provisional": bool(r.get("provisional"))}
        if pool:
            assert self.rrel is not None, "the heads ran before the first press fixed the idle statistics"
            out["e"] = self.pool.emissions_from_probs(self.pool.head_probs(feats, rssi, self.rrel))[0]
        return out

    # A pass's start terms read the windows ending in [press - 2, press + 1].
    def _terms_due(self, t0_new: float) -> None:
        for pid, p in self.passes.items():
            if p["terms"] is not None or t0_new + 2.0 <= p["press"] + 1.0 + 1e-6:
                continue
            ks = [k for k in self.order if k in self.win]
            t0 = np.asarray([self.win[k]["t0"] for k in ks], float)
            idx = np.flatnonzero((t0 + 2.0 >= p["press"] - 2.0 - 1e-6) & (t0 + 2.0 <= p["press"] + 1.0 + 1e-6))
            if len(idx) < 2:
                p["terms"] = {"a2": None, "committed": None}
            else:
                F = np.stack([self.win[ks[i]]["feats"] for i in idx]).astype(np.float32)
                R = np.stack([self.win[ks[i]]["rssi"] for i in idx]).astype(np.float32)
                a2_row = self.terms.a2_row(t0[idx], F, R, p["press"])
                veto_row = self.terms.veto_row(t0[idx], F, R, p["press"])
                p["terms"] = {"a2": self.terms.terms(a2_row, None),
                              "committed": self.terms.terms(a2_row, veto_row)}
            self.decoder.set_term(pid, p["terms"]["committed"])
            self.display.set_terms(pid, p["terms"]["a2"], p["terms"]["committed"])

    # The decoder committed a walk's line; in semi mode the walk's end is its causal exit.
    def _decided(self, row, at_close: bool = False) -> None:
        self.decisions.append({"pass_id": int(row["pass_id"]), "final_line": row["final_line"],
                               "exit_window": int(row["live_exit_window"]),
                               "decided_at_window": int(row["live_decided_at_window"]),
                               "t0_decided": float(self.decoder.t0[row["live_decided_at_window"]]),
                               "press": float(row["live_press"]), "at_close": bool(at_close)})
        if self.mode == "semi":
            pid = int(row["pass_id"])
            t_exit = float(self.decoder.t0[int(row["live_exit_window"])]) + 1.0
            pp = self.passes.get(pid)
            if pp is not None and (pp.get("end") is None or t_exit < pp["end"]):
                pp["end"] = t_exit
                self.display.end_press(pid, t_exit)
        if self.log is not None:
            self.log.committed(at_close)

    # Full mode: the committed line with the walk ending at the end press, once the last window whose centre is...
    def _full_due(self, final: bool = False) -> None:
        d = self.decoder
        for pid, t_end in list(self._full_pending.items()):
            p = next((q for q in d.passes if q["pid"] == pid), None)
            if p is None or p["lo"] is None:
                continue
            cen = np.asarray(d.t0, float) + 1.0
            hi = int(np.searchsorted(cen, t_end + 1e-9, side="right")) - 1
            arrived = hi < len(d.t0) - 1 or final
            if not arrived or hi < p["lo"]:
                continue
            e = np.asarray(d.e[p["lo"]:hi + 1], float)
            tot = chain_totals(e, self.st, slice(0, hi + 1 - p["lo"]), transition_matrix(self.st, "tight", with_null=False),
                               d.opts.get("chain_logprior"))
            if p["term"]:
                tot = {k: v + float(p["term"].get(k, 0.0)) for k, v in tot.items()}
            line = pick_line(tot, self.st, bool(d.opts.get("family_first")))
            self.decisions_full.append({"pass_id": pid, "final_line": line, "hi_end": hi, "t_end": t_end,
                                        "decided_at_window": len(d.t0) - 1})
            del self._full_pending[pid]


    # The display's frames before x_stop, then the lock bookkeeping (the line first drawn for each walk is THE...
    def draw_until(self, x_stop: float) -> None:
        before = self.log.snapshot() if self.log is not None else None
        self.display.draw_until(x_stop)
        for pid, m in self.display.meta.items():
            ln = m.get("lock_line")
            if ln and pid not in self.first_lock:
                self.first_lock[pid] = ln
            elif ln and ln != self.first_lock.get(pid):
                self.lock_changes.append({"pid": int(pid), "first": self.first_lock[pid], "now": ln})
        if self.log is not None:
            self.log.drawn(before)

    # V1 on the screen: every frame is ready by its own time.
    def _draw_ahead(self) -> None:
        d = self.display
        if d.frames is None or not d.t0:
            return
        self.draw_until(float(d.t0[-1]) + WINDOW_S + float(self.stream.stride_s) - FRAME_EPS_S)

    # A start press inside frames already drawn ahead: those frames of the new walk are its park, the room...
    def _park_drawn_ahead(self, pid: int, t_press: float) -> None:
        d = self.display
        if d.frames is None:
            return
        before = set(d.out.get(int(pid), {}))
        j0 = int(np.searchsorted(d.frames, float(t_press), side="left"))
        out = d.out.setdefault(int(pid), {})
        for x in d.frames[j0:d.next_frame]:
            assert x < float(t_press) + LATENCY_S, "a frame drawn ahead lies past the new walk's park"
            out[round(float(x), 4)] = CENTRE
        if self.log is not None:
            self.log.parked(int(pid), before)


    # A recording's ground truth, for the SCREEN only (the green marker and the verdict's colour).
    def set_truth(self, sidecar: dict) -> None:
        self.truth = {f"{self.session}|{self.stem}|{int(p['pass_id'])}": p for p in (sidecar or {}).get("passes", [])}

    # Where the walker was at t, from the pass's anchor presses, as rb7_demo.truth_at gives it.
    def _truth_at(self, pid: int, t: float):
        p = (getattr(self, "truth", None) or {}).get(f"{self.session}|{self.stem}|{int(pid)}")
        if p is None:
            return None
        at, ac = p["anchor_times"], p["anchor_coords"]
        if not at[0] <= t <= at[-1]:
            return None
        return (float(np.interp(t, at, [c[0] for c in ac])), float(np.interp(t, at, [c[1] for c in ac])))

    # What the screen shows at wall time now: the latest frame drawn at or before it, the line the display names...
    def screen_state(self, now: float) -> dict:
        if not self.passes:
            return {"status": f"windows {len(self.order)}; waiting for the first press"}
        pid = max(self.passes, key=lambda q: self.passes[q]["press"])
        out = self.display.out.get(pid, {})
        xs = [x for x in out if x <= now]
        dot = out[max(xs)] if xs else None
        meta = self.display.meta.get(pid, {})
        line, switched = meta.get("lock_line"), False
        for sw in meta.get("switches", []):
            if xs and max(xs) >= sw["x"] - 1e-9:
                line, switched = sw["new"], True
        end = self.passes[pid]["end"]
        green = self._truth_at(pid, now - LATENCY_S)
        if not (xs and max(xs) >= self.passes[pid]["press"] + LATENCY_S - 1e-6):
            green = None
        d = next((q for q in self.decisions if q["pass_id"] == pid), None)
        verdict = None
        if end is not None and now >= end + LATENCY_S:
            if d is None:
                verdict = {"pending": True, "drawn": line}
            else:
                t = (getattr(self, "truth", None) or {}).get(f"{self.session}|{self.stem}|{int(pid)}")
                verdict = {"committed": d["final_line"], "drawn": line,
                           "true": str(t.get("path_name", "")) if t else None}
        if verdict and not verdict.get("pending"):
            if self.mode == "full":
                dq = next((q for q in self.decisions_full if q["pass_id"] == pid), None)
                verdict["committed"] = dq["final_line"] if dq else None
                verdict["label"] = "committed at the end press (upper bound)"
            else:
                verdict["label"] = "committed line (the walk has ended)"
        return {"dot": dot, "line": line if xs else None, "switched": switched, "green": green,
                "verdict": verdict, "t_scene": now - LATENCY_S,
                "status": f"walk {pid}  windows {len(self.order)}  decided {len(self.decisions)}"}


    # The idle windows ended by the first press: their per-link RSSI mean (the relative RSSI) and their median...
    def _idle_stats(self, windows: list, first_press: float) -> None:
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

    # AdaBN on the idle windows ending at or before the first press: idle means the window's midpoint is more...
    def _adapt(self, first_press: float) -> None:
        ks = [k for k in self.order if k in self.win]
        cal = []
        for k in ks:
            t0 = float(self.win[k]["t0"])
            t_mid = 0.5 * (t0 + (t0 + 2.0))
            if t0 + 2.0 <= first_press + 1e-9 and abs(t_mid - first_press) > WALK_EDGE_S:
                cal.append(k)
        F = np.stack([self.win[k]["feats"] for k in cal]).astype(np.float32) if cal else np.zeros((0,))
        R = np.stack([self.win[k]["rssi"] for k in cal]).astype(np.float32) if cal else np.zeros((0,))
        self.adaptation = self.terms.adapt(F, R)

    # The decoder's and the display's window lists, rebuilt from the session's (after a re-cut).
    def _sync(self) -> None:
        self.order = sorted(self.win)
        rows = [self.win[k] for k in self.order]
        for obj in (self.decoder, self.display):
            obj.t0 = [float(w["t0"]) for w in rows]
            obj.t0_epoch = [float(w["t0_epoch"]) for w in rows]
            obj.e = [w["e"] for w in rows]
            obj.ge = [w["ge"] for w in rows]
        for p in self.decoder.passes + self.display.passes:
            if p.get("lo") is not None:
                p["lo"] = next(i for i, t in enumerate(self.decoder.t0) if t + 1.0 >= p["press"])


# Records every output of a session the moment it exists (stream time): each drawn dot, each lock, each...
class Logger:

    # Sets up the object.
    def __init__(self, s: Session):
        self.s, self.rows, self.now = s, [], None
        self.locks = {}
        self.n_frames = 0
        s.log = self

    # Function event.
    def event(self, t) -> None:
        self.now = float(t)

    # Function snapshot.
    def snapshot(self) -> dict:
        return {pid: set(v) for pid, v in self.s.display.out.items()}

    # After a draw: its new dots, and any walk's first lock.
    def drawn(self, before: dict) -> None:
        disp = self.s.display
        for pid, v in disp.out.items():
            for x in sorted(set(v) - before.get(pid, set())):
                xy = v[x]
                self.rows.append({"kind": "dot", "pid": int(pid), "x": float(x), "xy": [float(xy[0]), float(xy[1])],
                                  "computed_at": self.now})
                self.n_frames += 1
        for pid, ln in self.s.first_lock.items():
            m = disp.meta[pid]
            if pid not in self.locks:
                self.locks[pid] = ln
                self.rows.append({"kind": "lock", "pid": int(pid), "line": ln, "at": self.now,
                                  "line_entry": [float(v) for v in m["line_entry"]] if m.get("line_entry") else None,
                                  "t_dec0": m.get("t_dec0"), "park_until": m.get("park_until")})

    # After a press inside frames already drawn: the new walk's park dots.
    def parked(self, pid: int, before: set) -> None:
        disp = self.s.display
        for x in sorted(set(disp.out.get(pid, {})) - before):
            xy = disp.out[pid][x]
            self.rows.append({"kind": "dot", "pid": pid, "x": float(x), "xy": [float(xy[0]), float(xy[1])],
                              "computed_at": self.now})
            self.n_frames += 1

    # Function committed.
    def committed(self, at_close: bool) -> None:
        s = self.s
        d = s.decisions[-1]
        self.rows.append({"kind": "committed", "pid": d["pass_id"], "line": d["final_line"], "at": self.now,
                          "exit_window_centre": float(s.decoder.t0[d["exit_window"]]) + 1.0,
                          "decided_window_end": float(s.decoder.t0[d["decided_at_window"]]) + 2.0,
                          "at_close": bool(at_close)})

    # Function finish.
    def finish(self) -> None:
        s = self.s
        for d in s.decisions_full:
            self.rows.append({"kind": "committed_full", "pid": d["pass_id"], "line": d["final_line"], "t_end": d["t_end"],
                              "hi_end": d["hi_end"]})
        for ch in s.lock_changes:
            self.rows.append({"kind": "lock_change", **ch})
        for pid, m in s.display.meta.items():
            if m.get("min_margin_s") is not None:
                self.rows.append({"kind": "margin", "pid": int(pid), "min_margin_s": float(m["min_margin_s"])})
            for sw in m.get("switches", []):
                self.rows.append({"kind": "switch", "pid": int(pid), "x": float(sw["x"]), "old": sw["old"], "new": sw["new"]})
