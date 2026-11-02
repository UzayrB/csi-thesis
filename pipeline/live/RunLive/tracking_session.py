# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: One tracking session from start to finish: packets and key presses go in; 2 s windows, the networks'...

from __future__ import annotations

import time

import numpy as np


# The decoder's options.
def shipped_opts(st, train) -> dict:
    raise SystemExit("REFUSED: start tracking through main.py, which sets the frozen tracker's decoder options")


# Class Tracking Session.
class TrackingSession:
    # Pieces and components {"pool", "end_head", "terms"} come from the frozen tracker (main.py).
    def __init__(self, *, tag: str, train, test, reader_tag: str, baseline: dict, session: str, stem: str,
                 pieces=None, components: dict = None):
        from pipeline.live.RunLive.tracking_line_decision import LiveDecoder
        from pipeline.live.RunLive.tracking_display import CapSwitch, LiveDisplay, settings
        from pipeline.live.RunLive.tracking_windows import LiveStream
        c = components or {}
        if pieces is None or not all(c.get(k) for k in ("pool", "end_head", "terms")):
            raise SystemExit("REFUSED: a session needs the frozen tracker's pieces, pool, end head and start terms "
                             "(main.py builds them)")
        st, cfg, ne, transit, kind, alpha = pieces
        self.st = st
        opts = shipped_opts(st, tuple(train))
        opts["entry"], opts["entry_window_m"], opts["start_term"] = "soft", 1.0, None
        self.stream = LiveStream(baseline)
        self.pool, self.end_head, self.terms = c["pool"], c["end_head"], c["terms"]
        self.caps = CapSwitch()
        self.decoder = LiveDecoder(st, cfg, ne, transit, opts, session, stem)
        self.display = LiveDisplay(st, cfg, ne, transit, opts, session, stem, settings(), self.caps)
        self.session, self.stem = session, stem
        self.win = {}
        self.order = []
        self.passes = {}
        self.first_press = None
        self.adaptation = None
        self.decisions = []
        self.truth = None
        self.timing = {"window_s": [], "press_s": [], "cut_s": []}
        self.events = []

    # Function packet.
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
        from pipeline.live.RunLive.tracking_display import LATENCY_S
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
        return {"dot": dot, "line": line if xs else None, "switched": switched, "green": green,
                "verdict": verdict, "t_scene": now - LATENCY_S,
                "status": f"walk {pid}  windows {len(self.order)}  decided {len(self.decisions)}"}

    # Function press.
    def press(self, pid: int, t_press: float) -> None:
        t_ = time.perf_counter()
        res = self.stream.press(t_press)
        first = self.first_press is None
        if first:
            self.first_press = float(t_press)
        for k in res["dropped"] + res["withdrawn"]:
            self.win.pop(k, None)
        from pipeline.live.RunLive.tracking_windows import RECUT_BACK_S
        recent = [r for r in res["windows"] if float(r["t0"]) >= float(t_press) - RECUT_BACK_S - 0.5]
        older = [r for r in res["windows"] if float(r["t0"]) < float(t_press) - RECUT_BACK_S - 0.5]
        for r, w in zip(recent, self._rows_batch(recent, pool=True)):
            self.win[r["k"]] = w
        for r, w in zip(older, self._rows_batch(older, pool=False)):
            self.win[r["k"]] = w
        self._sync()
        if first:
            self._adapt(float(t_press))
            self.display.set_origin(float(self.win[self.order[0]]["t0"]))
        self.passes[int(pid)] = {"press": float(t_press), "end": None, "terms": None}
        self.decoder.press(float(t_press), int(pid))
        self.display.press(int(pid), float(t_press))
        self.timing["press_s"].append(time.perf_counter() - t_)
        self.events.append((float(t_press), self.timing["press_s"][-1], "press", None))

    # Function end press.
    def end_press(self, pid: int, t_end: float) -> None:
        self.stream.end_press(t_end)
        if int(pid) in self.passes:
            self.passes[int(pid)]["end"] = float(t_end)
        self.display.end_press(int(pid), float(t_end))

    # Function close.
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

    # Function rows.
    def _rows(self, r, pool: bool = True) -> dict:
        from pipeline.live.RunLive.tracking_networks import LivePool
        feats = LivePool.features(r["X"][None])
        rssi = np.asarray(r["rssi"], np.float32)[None]
        out = {"k": r["k"], "t0": r["t0"], "t0_epoch": r["t0_epoch"], "feats": feats[0], "rssi": rssi[0],
               "e": None, "ge": self.pool.gate_energy(r["X"]), "e_end": None,
               "provisional": bool(r.get("provisional"))}
        if pool:
            out["e"] = self.pool.emissions_from_probs(self.pool.head_probs(feats, rssi))[0]
            out["e_end"] = self.end_head.emission(feats, rssi)[0]
        return out

    # _rows for many windows (a press's re-cut).
    def _rows_batch(self, recs: list, pool: bool) -> list:
        from pipeline.live.RunLive.tracking_networks import LivePool
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

    # Function window.
    def _window(self, r) -> None:
        t_ = time.perf_counter()
        w = self._rows(r, pool=not r.get("provisional"))
        self.win[r["k"]] = w
        self.order.append(r["k"])
        self._terms_due(float(w["t0"]))
        self.display.push(w["t0"], w["t0_epoch"], w["e"], w["ge"], w["e_end"])
        for row in self.decoder.push(w["t0"], w["t0_epoch"], w["e"], w["ge"]):
            self._decided(row)
        self.timing["window_s"].append((time.perf_counter() - t_, bool(w["provisional"])))

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

    # AdaBN on the idle windows ending at or before the first press (u1_adapt.calibration_indices): idle means...
    def _adapt(self, first_press: float) -> None:
        from pipeline.io.RunLive.signal_windows import WALK_EDGE_S
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
        self.display.e_end = [w["e_end"] for w in rows]
        for p in self.decoder.passes + self.display.passes:
            if p.get("lo") is not None:
                p["lo"] = next(i for i, t in enumerate(self.decoder.t0) if t + 1.0 >= p["press"])

    # Function decided.
    def _decided(self, row, at_close: bool = False) -> None:
        self.decisions.append({"pass_id": int(row["pass_id"]), "final_line": row["final_line"],
                               "exit_window": int(row["live_exit_window"]),
                               "decided_at_window": int(row["live_decided_at_window"]),
                               "t0_decided": float(self.decoder.t0[row["live_decided_at_window"]]),
                               "press": float(row["live_press"]), "at_close": bool(at_close)})


# Wraps the session so that every output is logged the moment it exists (stream time).
class Logger:

    # Sets up the object.
    def __init__(self, s):
        self.s, self.rows, self.now = s, [], None
        self.locks = {}
        self.n_frames = 0
        disp = s.display
        orig_draw = disp._draw_until

        # Function draw until.
        def draw_until(x_stop):
            before = {pid: set(v) for pid, v in disp.out.items()}
            orig_draw(x_stop)
            for pid, v in disp.out.items():
                for x in sorted(set(v) - before.get(pid, set())):
                    xy = v[x]
                    self.rows.append({"kind": "dot", "pid": int(pid), "x": float(x), "xy": [float(xy[0]), float(xy[1])],
                                      "computed_at": self.now})
                    self.n_frames += 1
            for pid, ln in s.first_lock.items():
                m = disp.meta[pid]
                if pid not in self.locks:
                    self.locks[pid] = ln
                    self.rows.append({"kind": "lock", "pid": int(pid), "line": ln, "at": self.now,
                                      "line_entry": [float(v) for v in m["line_entry"]] if m.get("line_entry") else None,
                                      "t_dec0": m.get("t_dec0"), "park_until": m.get("park_until")})
        disp._draw_until = draw_until
        orig_park = s._park_drawn_ahead

        # Function park.
        def park(pid, t_press):
            before = set(disp.out.get(int(pid), {}))
            orig_park(pid, t_press)
            for x in sorted(set(disp.out.get(int(pid), {})) - before):
                xy = disp.out[int(pid)][x]
                self.rows.append({"kind": "dot", "pid": int(pid), "x": float(x), "xy": [float(xy[0]), float(xy[1])],
                                  "computed_at": self.now})
                self.n_frames += 1
        s._park_drawn_ahead = park
        orig_dec = s._decided

        # Function decided.
        def decided(row, at_close=False):
            orig_dec(row, at_close)
            d = s.decisions[-1]
            self.rows.append({"kind": "committed", "pid": d["pass_id"], "line": d["final_line"], "at": self.now,
                              "exit_window_centre": float(s.decoder.t0[d["exit_window"]]) + 1.0,
                              "decided_window_end": float(s.decoder.t0[d["decided_at_window"]]) + 2.0,
                              "at_close": bool(at_close)})
        s._decided = decided

    # Function event.
    def event(self, t):
        self.now = float(t)

    # Function finish.
    def finish(self):
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
