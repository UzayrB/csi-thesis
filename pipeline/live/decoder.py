"""The shipped semi-bounded committed decision, live.

The frozen decoder (`night_arms.night_track`) is not re-implemented here: it is CALLED, at every new
window, on exactly the windows that exist at that moment. That makes the live answer the offline
answer by construction wherever the offline answer is causal, and gate 3 checks it pass by pass.
Three facts make the prefix call exact, each read from the frozen code on 2026-09-25:

  1  THE EXIT IS CAUSAL. `causal_end` declares a walk over at the first window whose forward decode
     ends in the null state, reading nothing later. On a prefix it returns the same exit once that
     window exists; before then it runs out of windows and says so (`timeout_fired` with the search
     stopping at the last window rather than at the walk horizon), and the pass stays open.
  2  THE NULL REFERENCE IS ZERO. `ne.calibrate` takes a quantile of each window's MAXIMUM emission over
     whatever it is given; the shipped pool renormalises every window so that maximum is exactly 0,
     so the reference is 0.000 on any prefix. Asserted, not assumed (`calibrate` is checked below).
  3  EVERYTHING ELSE IS BACKWARD-LOOKING: `stack2`'s gate veto uses earlier windows only, and the
     rescore reads the interval from the pass's start to its exit.

The ground truth `night_track` reads for SCORING (the last anchor press, the walk's true end) does not
exist live. Its cache (`sb2_structural._PRESS_CACHE`) is seeded with the start press, which moves only
the scoring fields of the row (`exit_dt_*`, `never_ended`), never a decision.
"""

from __future__ import annotations

import numpy as np

#: windows kept before a pass's first walk window when its prefix is decoded. MEASURED 2026-09-25:
#: gates 3 and 4 are 120 of 120 equal at 6 (the decode reads about 3 s before its first walk window:
#: the gate veto's look-back and the soft entry), and the frozen decoder refuses at 2. 8 keeps a
#: margin above the measured 6; the stream re-cuts at least this far back at every start press
LOOKBACK_W = 8


class LiveDecoder:
    def __init__(self, st, cfg, ne, transit, opts: dict, session: str, stem: str, participant: str = "live"):
        self.st, self.cfg, self.ne, self.transit = st, cfg, ne, transit
        self.opts = dict(opts)
        self.session, self.stem, self.participant = session, stem, participant
        self.t0, self.t0_epoch, self.e, self.ge = [], [], [], []
        self.passes = []          # {pid, press, lo, term, done, row}
        from pipeline.constrained import sb2_structural
        self._press_cache = sb2_structural._PRESS_CACHE
        self._scoring_press = {}

    # -- inputs ------------------------------------------------------------------------------
    def press(self, t_press: float, pid: int = None) -> int:
        """The operator's start press: the RAW key time, as the sidecar's `t_start` stores it (the tree's
        lattice is phased on it; see `stream.py`)."""
        pid = int(pid) if pid is not None else (max([p["pid"] for p in self.passes], default=0) + 1)
        self.passes.append({"pid": pid, "press": float(t_press), "lo": None, "term": None,
                            "done": False, "row": None})
        return pid

    def set_term(self, pid: int, term: dict) -> None:
        """The pass's start term (A2 + veto), available one second after its press."""
        for p in self.passes:
            if p["pid"] == int(pid):
                p["term"] = dict(term) if term is not None else None

    def push(self, t0: float, t0_epoch: float, e_row: np.ndarray, ge: float) -> list:
        """One completed window. Returns the rows of any pass whose end this window declares."""
        self.t0.append(float(t0))
        self.t0_epoch.append(float(t0_epoch))
        self.e.append(np.asarray(e_row, float))
        self.ge.append(float(ge))
        k = len(self.t0) - 1
        done = []
        for p in self.passes:
            if p["done"]:
                continue
            if p["lo"] is None and self.t0[k] + 1.0 >= p["press"]:
                p["lo"] = k                        # the first window whose MIDPOINT is at or after the press
            if p["lo"] is None or k < p["lo"] + 1:
                continue
            row = self._decode(p, k)
            if row is not None:
                p["done"], p["row"] = True, row
                done.append(row)
        return done

    def close(self) -> list:
        """The recording stopped: decide every open pass on the windows that exist.

        Offline, a pass still walking when the recording ends is decided on the truncated windows (the
        exit search times out at the last one). This is that decision, taken when the operator stops."""
        k = len(self.t0) - 1
        done = []
        for p in self.passes:
            if p["done"] or p["lo"] is None or k < p["lo"]:
                continue
            row = self._decode(p, k, final=True)
            if row is not None:
                p["done"], p["row"] = True, row
                done.append(row)
        return done

    # -- the frozen decoder on the prefix -----------------------------------------------------
    def _recording(self, a: int, b: int, p):
        from pipeline.constrained.recordings import Recording
        n = b - a + 1
        t0 = np.asarray(self.t0[a:b + 1], float)
        walk = np.zeros(n, bool)
        walk[p["lo"] - a:] = True
        mode = np.where(walk, "walk", "idle").astype("U10")
        pass_id = np.where(walk, p["pid"], -1)
        return Recording(session=self.session, stem=self.stem, participant=self.participant, t0=t0,
                         t0_epoch=np.asarray(self.t0_epoch[a:b + 1], float), mode=mode, pass_id=pass_id,
                         path_name=np.where(walk, "", "").astype("U10"),
                         xy=np.full((n, 2), np.nan), cell_id=np.full(n, "", dtype="U10"),
                         gap_flag=np.zeros(n, bool))

    def _decode(self, p, k: int, final: bool = False):
        from pipeline.constrained.night_arms import MAX_WALK_S, night_track
        from pipeline.constrained.night_common import STRIDE
        a = max(0, p["lo"] - LOOKBACK_W)
        rec = self._recording(a, k, p)
        e = np.asarray(self.e[a:k + 1], float)
        assert float(np.max(np.abs(e.max(axis=1)))) == 0.0, \
            "the pooled emission is not max-normalised: the null reference would not be 0 on a prefix"
        self._press_cache[(self.session, self.stem)] = {p["pid"]: p["press"]}
        o = dict(self.opts)
        o["start_term"] = {f"{self.session}|{self.stem}|{p['pid']}": p["term"]} if p["term"] is not None else None
        rows = night_track(e, rec, self.st, self.cfg, self.transit, self.ne, np.asarray(self.ge[a:k + 1]),
                           STRIDE, o, None)
        rows = [r for r in rows if r["pass_id"] == p["pid"]]
        if not rows:
            return None
        r = rows[0]
        horizon_w = int(round(MAX_WALK_S / STRIDE))
        lo_rel = p["lo"] - a
        ran_out = bool(r["timeout_fired"] and r["exit_search_hi"] == (k - a)
                       and (k - a) < lo_rel + horizon_w)
        if ran_out and not final:
            return None
        return {**r, "live_exit_window": int(a + r["own_end_i"]), "live_lo": int(p["lo"]),
                "live_decided_at_window": int(k), "live_press": p["press"],
                "live_scoring_fields_are_placeholders": True}
