"""Tracking mode: packets and presses in; windows, the committed decision and the drawn frames out.

The pieces, each proved against its offline counterpart on replay (`pipeline/live/gates.py`):

    LiveStream       packets -> the tree's windows, re-cut on each start press      (gate stream)
    LivePool         window  -> the five-head pooled emission and the gate energy    (gate 1)
    LiveEndHead      window  -> the display head's emission (DISP_END)               (gate e2e)
    LiveStartTerms   the pass's windows -> A2 and the veto; AdaBN at the first press (gate 2)
    LiveDecoder      the committed decision, the frozen decoder on each prefix       (gate 3)
    LiveDisplay      the dot, the lock, the switch, frame by frame                   (gate 4)

The order inside one window is fixed and is the causal order: the window's rows are computed; any
pass whose start terms read only windows that have now all ended gets them; the display draws every
frame that could not have read this window; then the decoder advances. A START press re-cuts the
windows it re-assigns, recomputes their rows, and re-synchronises the decoder's and the display's
window lists (a re-cut window keeps its place; the first press may drop the recording's first window
and a press may withdraw the newest ones, which then return as the radio arrives). The first press
also runs AdaBN on the idle windows before it, now on its phase.

Presses are RAW key times: the tree's lattice is phased on the raw press (see `stream.py`). The
END press moves the next segment's boundary and ends the walk's drawn frames; the decoder is never
told it.
"""

from __future__ import annotations

import time

import numpy as np


class TrackingSession:
    def __init__(self, *, tag: str, train, test, reader_tag: str, baseline: dict, session: str, stem: str,
                 end_tag: str = None, pieces=None, components: dict = None):
        """components: prebuilt {"pool", "end_head", "terms"} to share across recordings (they hold no
        per-recording state except AdaBN, which `_adapt` resets at each first press)."""
        from pipeline.constrained.night_common import shipped_pieces
        from pipeline.constrained.r1_oldcensus import shipped_opts
        from pipeline.live.decoder import LiveDecoder
        from pipeline.live.display import CapSwitch, LiveDisplay, settings
        from pipeline.live.pool import LiveEndHead, LivePool
        from pipeline.live.start_terms import LiveStartTerms
        from pipeline.live.stream import LiveStream
        st, cfg, ne, transit, kind, alpha = pieces or shipped_pieces()
        self.st = st
        opts = shipped_opts(st, tuple(train))
        opts["entry"], opts["entry_window_m"], opts["start_term"] = "soft", 1.0, None
        self.stream = LiveStream(baseline)
        c = components or {}
        self.pool = c.get("pool") or LivePool(tag, tuple(train), tuple(test), st, kind, alpha)
        self.end_head = c.get("end_head") or LiveEndHead(end_tag or tag, tuple(train), st, alpha)
        self.terms = c.get("terms") or LiveStartTerms(tuple(train), reader_tag, st)
        self.caps = CapSwitch()
        self.decoder = LiveDecoder(st, cfg, ne, transit, opts, session, stem)
        self.display = LiveDisplay(st, cfg, ne, transit, opts, session, stem, settings(), self.caps)
        self.session, self.stem = session, stem
        self.win = {}                  # base index -> rows
        self.order = []                # base indices in lattice order, as the decoder and display hold them
        self.passes = {}               # pid -> {"press", "end", "terms"}
        self.first_press = None
        self.adaptation = None
        self.decisions = []
        self.truth = None
        self.identities = []           # identification's decision lines, for the SCREEN only (`identity`)
        self.timing = {"window_s": [], "press_s": [], "cut_s": []}
        #: (arrival on the stream clock, service seconds, kind, window t0): the queue gate 6 replays
        self.events = []

    # -- inputs --------------------------------------------------------------------------------
    def packet(self, node, t, amplitude, t_host, t_mono, rssi) -> None:
        self.stream.push_rssi(node, t_host, rssi)
        t_ = time.perf_counter()
        recs = self.stream.push_packet(node, t, amplitude, t_host=t_host, t_mono=t_mono)
        if recs:
            cut = (time.perf_counter() - t_) / len(recs)
            self.timing["cut_s"].append(cut)
        for r in recs:
            t1 = time.perf_counter()
            self._window(r)
            self.events.append((float(t_mono), cut + time.perf_counter() - t1, "window", float(r["t0"])))

    def rssi(self, node, t_host, rssi) -> None:
        self.stream.push_rssi(node, t_host, rssi)

    def csi(self, node, t, amplitude, t_host, t_mono) -> None:
        """A packet whose RSSI was already pushed at arrival (the rig's path: CSI waits for its clock fit)."""
        t_ = time.perf_counter()
        recs = self.stream.push_packet(node, t, amplitude, t_host=t_host, t_mono=t_mono)
        cut = (time.perf_counter() - t_) / len(recs) if recs else 0.0
        for r in recs:
            t1 = time.perf_counter()
            self._window(r)
            self.events.append((float(t_mono), cut + time.perf_counter() - t1, "window", float(r["t0"])))

    def set_truth(self, sidecar: dict) -> None:
        """A recording's ground truth, for the SCREEN only (the green marker and the verdict's colour).
        Nothing that decides or draws the dot reads it. Live on the rig there is none unless one is given."""
        # keyed session|stem|pass_id, the standing pairing key (tests/test_pass_pairing_key.py)
        self.truth = {f"{self.session}|{self.stem}|{int(p['pass_id'])}": p for p in (sidecar or {}).get("passes", [])}

    def _truth_at(self, pid: int, t: float):
        """Where the walker was at t, from the pass's anchor presses, as `rb7_demo.truth_at` gives it."""
        p = (getattr(self, "truth", None) or {}).get(f"{self.session}|{self.stem}|{int(pid)}")
        if p is None:
            return None
        at, ac = p["anchor_times"], p["anchor_coords"]
        if not at[0] <= t <= at[-1]:
            return None
        return (float(np.interp(t, at, [c[0] for c in ac])), float(np.interp(t, at, [c[1] for c in ac])))

    def identity(self, line: dict) -> None:
        """One identification decision (`reports/identification/live-interface.md`, schema id_engine_decision_v1), as the
        identification mode writes it: who is walking. For the SCREEN only, beside the walk it names. Nothing
        that decides or draws reads it (tests/test_live_truth_isolation.py)."""
        self.identities.append(dict(line))

    def _identity_for(self, press: float, now: float):
        """The decision whose press is this walk's (within 1.0 s) and which had been made by `now`."""
        best = None
        for ln in (getattr(self, "identities", None) or []):
            dt = abs(float(ln.get("t_press_mono", float("inf"))) - float(press))
            if dt <= 1.0 and float(ln.get("t_decision_mono", float("inf"))) <= now and (best is None or dt < best[0]):
                best = (dt, ln)
        return None if best is None else {"top": best[1].get("top"), "probability": best[1].get("probability"),
                                          "direction": best[1].get("direction")}

    def screen_state(self, now: float) -> dict:
        """What the screen shows at wall time `now`: the latest frame drawn at or before it, the line the
        display names there (the lock, or the switch from its frame on), the green marker where the walker
        was LATENCY_S ago (from the press + LATENCY_S on, as `f3_render` shows it, and only with a ground
        truth), and the verdict once the walk's drawn frames are over AND the committed decision exists."""
        from pipeline.live.display import LATENCY_S
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
        # RULE 6 by construction: a pass's truth spans its first to its last anchor press, which are its
        # start and end presses, so the marker for the moment now - LATENCY_S appears on the frame the dot
        # leaves the park (press + LATENCY_S) and goes when the walk's frames end (end press + LATENCY_S)
        green = self._truth_at(pid, now - LATENCY_S)
        # V2 on the screen: the marker appears on the video frame on which the dot leaves the park. The frame at
        # press + 2.0 s is ready only once the window ending then has been cut (about 0.1 s later), so a marker
        # shown from press + 2.0 s itself would lead the dot by a frame or two
        if not (xs and max(xs) >= self.passes[pid]["press"] + LATENCY_S - 1e-6):
            green = None
        d = next((q for q in self.decisions if q["pass_id"] == pid), None)
        verdict = None
        if end is not None and now >= end + LATENCY_S:
            if d is None:
                # the walk's frames are over but the decoder has not declared its end yet: say so
                verdict = {"pending": True, "drawn": line}
            else:
                t = (getattr(self, "truth", None) or {}).get(f"{self.session}|{self.stem}|{int(pid)}")
                verdict = {"committed": d["final_line"], "drawn": line,
                           "true": str(t.get("path_name", "")) if t else None}
        return {"dot": dot, "line": line if xs else None, "switched": switched, "green": green,
                "verdict": verdict, "t_scene": now - LATENCY_S,
                "identity": self._identity_for(self.passes[pid]["press"], now),
                "status": f"walk {pid}  windows {len(self.order)}  decided {len(self.decisions)}"}

    def press(self, pid: int, t_press: float) -> None:
        t_ = time.perf_counter()
        res = self.stream.press(t_press)
        first = self.first_press is None
        if first:
            self.first_press = float(t_press)
        for k in res["dropped"] + res["withdrawn"]:
            self.win.pop(k, None)
        from pipeline.live.stream import RECUT_BACK_S
        recent = [r for r in res["windows"] if float(r["t0"]) >= float(t_press) - RECUT_BACK_S - 0.5]
        older = [r for r in res["windows"] if float(r["t0"]) < float(t_press) - RECUT_BACK_S - 0.5]
        for r, w in zip(recent, self._rows_batch(recent, pool=True)):
            self.win[r["k"]] = w
        for r, w in zip(older, self._rows_batch(older, pool=False)):
            self.win[r["k"]] = w
        self._sync()
        if first:
            self._adapt(float(t_press))
            # the frame grid starts at the recording's first window, now on the first press's phase
            self.display.set_origin(float(self.win[self.order[0]]["t0"]))
        self.passes[int(pid)] = {"press": float(t_press), "end": None, "terms": None}
        self.decoder.press(float(t_press), int(pid))
        self.display.press(int(pid), float(t_press))
        self.timing["press_s"].append(time.perf_counter() - t_)
        self.events.append((float(t_press), self.timing["press_s"][-1], "press", None))

    def end_press(self, pid: int, t_end: float) -> None:
        self.stream.end_press(t_end)
        if int(pid) in self.passes:
            self.passes[int(pid)]["end"] = float(t_end)
        self.display.end_press(int(pid), float(t_end))

    def close(self) -> None:
        res = self.stream.close()
        for k in res["withdrawn"]:
            self.win.pop(k, None)
        if res["withdrawn"]:
            self._sync()
        for r in res["windows"]:
            self._window(r)
        self.display.close()
        for row in self.decoder.close():
            self._decided(row, at_close=True)

    # -- one window ----------------------------------------------------------------------------
    def _rows(self, r, pool: bool = True) -> dict:
        from pipeline.live.pool import LivePool
        feats = LivePool.features(r["X"][None])
        rssi = np.asarray(r["rssi"], np.float32)[None]
        out = {"k": r["k"], "t0": r["t0"], "t0_epoch": r["t0_epoch"], "feats": feats[0], "rssi": rssi[0],
               "e": None, "ge": self.pool.gate_energy(r["X"]), "e_end": None,
               "provisional": bool(r.get("provisional"))}
        if pool:
            out["e"] = self.pool.emissions_from_probs(self.pool.head_probs(feats, rssi))[0]
            out["e_end"] = self.end_head.emission(feats, rssi)[0]
        return out

    def _rows_batch(self, recs: list, pool: bool) -> list:
        """`_rows` for many windows (a press's re-cut). The heads run window by window: on the Apple GPU a
        batch of twelve cost 45 ms per head and link against 2.4 ms for one (measured 2026-09-25), and
        one at a time is the path gate 1 proved. Only the features of windows the heads skip are batched."""
        from pipeline.live.pool import LivePool
        if not recs:
            return []
        if pool:
            return [self._rows(r, pool=True) for r in recs]
        feats = LivePool.features(np.stack([r["X"] for r in recs]))
        rssi = np.stack([np.asarray(r["rssi"], np.float32) for r in recs])
        e = self.pool.emissions_from_probs(self.pool.head_probs(feats, rssi)) if pool else None
        ee = self.end_head.emission(feats, rssi) if pool else None
        return [{"k": r["k"], "t0": r["t0"], "t0_epoch": r["t0_epoch"], "feats": feats[i], "rssi": rssi[i],
                 "e": None if e is None else e[i], "ge": self.pool.gate_energy(r["X"]),
                 "e_end": None if ee is None else ee[i], "provisional": bool(r.get("provisional"))}
                for i, r in enumerate(recs)]

    def _window(self, r) -> None:
        t_ = time.perf_counter()
        # before the first press every window is provisional (that press re-cuts them all), so the
        # heads wait; the gate energy is kept for a presence read-out
        w = self._rows(r, pool=not r.get("provisional"))
        self.win[r["k"]] = w
        self.order.append(r["k"])
        self._terms_due(float(w["t0"]))
        self.display.push(w["t0"], w["t0_epoch"], w["e"], w["ge"], w["e_end"])
        for row in self.decoder.push(w["t0"], w["t0_epoch"], w["e"], w["ge"]):
            self._decided(row)
        self.timing["window_s"].append((time.perf_counter() - t_, bool(w["provisional"])))

    def _terms_due(self, t0_new: float) -> None:
        """A pass's start terms read the windows ending in [press - 2, press + 1]. They are all in once
        a window ending after press + 1 arrives, and they are set before that window is decoded."""
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

    def _adapt(self, first_press: float) -> None:
        """AdaBN on the idle windows ending at or before the first press (`u1_adapt.calibration_indices`):
        idle means the window's midpoint is more than WALK_EDGE_S from the press, as `label_window` says."""
        from pipeline.io.windows import WALK_EDGE_S
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

    def _sync(self) -> None:
        """The decoder's and the display's window lists, rebuilt from the session's (after a re-cut)."""
        self.order = sorted(self.win)
        rows = [self.win[k] for k in self.order]
        for obj in (self.decoder, self.display):
            obj.t0 = [float(w["t0"]) for w in rows]
            obj.t0_epoch = [float(w["t0_epoch"]) for w in rows]
            obj.e = [w["e"] for w in rows]
            obj.ge = [w["ge"] for w in rows]
        self.display.e_end = [w["e_end"] for w in rows]
        for p in self.decoder.passes + self.display.passes:
            if p.get("lo") is not None:
                p["lo"] = next(i for i, t in enumerate(self.decoder.t0) if t + 1.0 >= p["press"])

    def _decided(self, row, at_close: bool = False) -> None:
        self.decisions.append({"pass_id": int(row["pass_id"]), "final_line": row["final_line"],
                               "exit_window": int(row["live_exit_window"]),
                               "decided_at_window": int(row["live_decided_at_window"]),
                               "t0_decided": float(self.decoder.t0[row["live_decided_at_window"]]),
                               "press": float(row["live_press"]), "at_close": bool(at_close)})
