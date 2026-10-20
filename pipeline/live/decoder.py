# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The shipped semi-bounded committed decision, live.

from __future__ import annotations

import numpy as np

LOOKBACK_W = 8


# Class Live Decoder.
class LiveDecoder:
    # Sets up the object.
    def __init__(self, st, cfg, ne, transit, opts: dict, session: str, stem: str, participant: str = "live"):
        self.st, self.cfg, self.ne, self.transit = st, cfg, ne, transit
        self.opts = dict(opts)
        self.session, self.stem, self.participant = session, stem, participant
        self.t0, self.t0_epoch, self.e, self.ge = [], [], [], []
        self.passes = []
        from pipeline.constrained import sb2_structural
        self._press_cache = sb2_structural._PRESS_CACHE
        self._scoring_press = {}

    # The operator's start press: the RAW key time, as the sidecar's t_start stores it (the tree's lattice is...
    def press(self, t_press: float, pid: int = None) -> int:
        pid = int(pid) if pid is not None else (max([p["pid"] for p in self.passes], default=0) + 1)
        self.passes.append({"pid": pid, "press": float(t_press), "lo": None, "term": None,
                            "done": False, "row": None})
        return pid

    # The pass's start term (A2 + veto), available one second after its press.
    def set_term(self, pid: int, term: dict) -> None:
        for p in self.passes:
            if p["pid"] == int(pid):
                p["term"] = dict(term) if term is not None else None

    # One completed window.
    def push(self, t0: float, t0_epoch: float, e_row: np.ndarray, ge: float) -> list:
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
                p["lo"] = k
            if p["lo"] is None or k < p["lo"] + 1:
                continue
            row = self._decode(p, k)
            if row is not None:
                p["done"], p["row"] = True, row
                done.append(row)
        return done

    # The recording stopped: decide every open pass on the windows that exist.
    def close(self) -> list:
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

    # Function recording.
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

    # Function decode.
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
