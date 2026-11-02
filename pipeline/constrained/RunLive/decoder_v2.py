# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The rebuilt decoder's states and transitions, used by the semi-bounded decoder.

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

import numpy as np

from pipeline.constrained.RunLive.shared_settings import DT, V_MEAN
from pipeline.constrained.RunLive.decoder_lines import NEG, along_log_score, along_transition

MOTION_THETA = 0.431


# Class Config.
@dataclass(frozen=True)
class Config:
    veto: bool = False
    veto_hysteresis: int = 1
    split: bool = False
    geometry: bool = False
    late_entry: bool = False
    margin: float = 0.0
    sibling_margin: float = 0.0
    sd_scale: float = 1.0
    lam: float = 1.0
    normalise: bool = False
    null_self: float = 0.9
    exit_k: int = 1
    exit_p: float = 0.5
    clock_max: int = 8
    kind: str = "tight"
    bout_log_odds: float = 0.0
    abort_cost: float = 60.0

    # Function label.
    def label(self) -> str:
        on = [k for k in ("veto", "split", "geometry", "late_entry", "normalise") if getattr(self, k)]
        if self.bout_log_odds:
            on.append("bout_prior")
        return ("+".join(on) or "frozen") + f" ns{self.null_self} k{self.exit_k}" + \
            (f" m{self.margin:g}" if self.late_entry else "") + \
            (f" b{self.bout_log_odds:+.2f}" if self.bout_log_odds else "")


# Index bookkeeping for the extended state space.
class Space:

    # Sets up the object.
    def __init__(self, st, cfg: Config):
        self.st, self.cfg = st, cfg
        S = st.n_states
        self.S = S
        self.n_lines = len(st.names)
        if not cfg.split:
            self.P = 1
            self.still0 = S
            self.transit0 = None
            self.N = S + 1
        else:
            self.P = self.n_lines + 1
            self.still0 = S
            self.transit0 = S + self.P
            self.N = S + self.P + self.P * (cfg.clock_max + 1)

    # Function still.
    def still(self, p: int = 0) -> int:
        return self.still0 + (p if self.cfg.split else 0)

    # Function transit.
    def transit(self, p: int, k: int) -> int:
        assert self.cfg.split
        return self.transit0 + p * (self.cfg.clock_max + 1) + min(k, self.cfg.clock_max)

    # Function kind.
    def kind(self, state: int) -> str:
        if state < self.S:
            return "path"
        if not self.cfg.split or state < self.transit0:
            return "still"
        return "transit"

_LT_CACHE: dict = {}


# The whole log transition matrix for cfg.
def transition_matrix2(st, cfg: Config, transit_min_windows: Optional[dict] = None) -> np.ndarray:
    key = (id(st), asdict(cfg).__repr__(), id(transit_min_windows) if cfg.geometry else 0)
    if key in _LT_CACHE:
        return _LT_CACHE[key]
    sp = Space(st, cfg)
    N = sp.N
    out = np.full((N, N), NEG, dtype=float)

    for nm in st.names:
        i0, i1 = st.slice_of[nm]
        if cfg.normalise:
            T = along_transition(st.s_of[i0:i1], cfg.kind)
            blk = np.full_like(T, NEG)
            np.log(T, out=blk, where=T > 0)
        else:
            blk = along_log_score(st.s_of[i0:i1], cfg.kind, cfg.sd_scale)
        out[i0:i1, i0:i1] = blk

    log_exit = float(np.log(max(cfg.exit_p, 1e-12)))
    log_stay = float(np.log(max(cfg.null_self, 1e-12)))
    log_leave = float(np.log(max(1.0 - cfg.null_self, 1e-12)))
    log_entry = log_leave - float(np.log(sp.n_lines)) - float(cfg.margin)
    SIBLING_LINES = frozenset(("A_fwd", "E_col1", "E_col5", "B_fwd", "E_row1", "E_row5"))
    # Function entry for.
    def entry_for(nm: str) -> float:
        return log_entry - (float(cfg.sibling_margin) if nm in SIBLING_LINES else 0.0)
    k_exit = max(1, int(cfg.exit_k))
    v_step = V_MEAN * DT
    log_abort = -float(cfg.abort_cost) if cfg.veto else None

    # Function min w.
    def min_w(p: int, q_name: str) -> int:
        if not cfg.geometry or p == 0 or not transit_min_windows:
            return 0
        return int(transit_min_windows.get(f"{st.names[p - 1]}->{q_name}", {}).get("min_windows", 0))

    if not cfg.split:
        null = sp.still(0)
        for nm in st.names:
            i0, i1 = st.slice_of[nm]
            for i in range(max(i0, i1 - k_exit), i1):
                out[i, null] = log_exit
            if log_abort is not None:
                for i in range(i0, i1 - k_exit):
                    out[i, null] = log_abort
            out[null, i0] = entry_for(nm) + float(cfg.bout_log_odds)
        out[null, null] = log_stay
    else:
        K = cfg.clock_max
        for qi, nm in enumerate(st.names):
            i0, i1 = st.slice_of[nm]
            p = qi + 1
            for i in range(max(i0, i1 - k_exit), i1):
                out[i, sp.still(p)] = log_exit
                out[i, sp.transit(p, 0)] = log_exit
            if log_abort is not None:
                for i in range(i0, max(i0, i1 - k_exit)):
                    out[i, sp.still(p)] = log_abort
        for p in range(sp.P):
            s_ = sp.still(p)
            out[s_, s_] = log_stay
            out[s_, sp.transit(p, 0)] = log_leave
            for nm in st.names:
                if min_w(p, nm) == 0:
                    out[s_, st.slice_of[nm][0]] = log_entry
            for k in range(K + 1):
                t_ = sp.transit(p, k)
                out[t_, sp.transit(p, min(k + 1, K))] = log_stay
                out[t_, s_] = log_leave
                for nm in st.names:
                    i0, i1 = st.slice_of[nm]
                    owed = min_w(p, nm)
                    entry_nm = entry_for(nm) + float(cfg.bout_log_odds)
                    if not cfg.late_entry:
                        if k >= owed:
                            out[t_, i0] = entry_nm
                        continue
                    s_rel = st.s_of[i0:i1] - st.s_of[i0]
                    for j in range(i1 - i0):
                        unexplained = s_rel[j] / v_step
                        if s_rel[j] <= v_step * (k + 1) + 1e-9 and k >= owed + int(np.floor(unexplained)):
                            out[t_, i0 + j] = entry_nm - cfg.lam * unexplained
    _LT_CACHE[key] = out
    return out


# (T, N) emissions: path columns, then STILL and TRANSIT columns, with the gate veto.
def stack2(e_path: np.ndarray, gate_e: np.ndarray, ne, sp: Space) -> np.ndarray:
    T = e_path.shape[0]
    cfg = sp.cfg
    g = np.asarray(gate_e, float)
    theta = float(getattr(ne, "motion_theta", MOTION_THETA))
    still = (g < theta).astype(float)
    walking = 1.0 - still
    gw = float(getattr(ne, "gate_weight", 0.0))
    level = np.asarray(ne(g), float)
    base = level - gw * still
    out = np.full((T, sp.N), NEG, dtype=float)
    out[:, :sp.S] = e_path
    if cfg.veto:
        h = max(1, int(cfg.veto_hysteresis))
        stat = g < theta
        forbid = stat.copy()
        for d in range(1, h):
            shifted = np.zeros_like(stat)
            shifted[d:] = stat[:-d]
            forbid &= shifted
        out[forbid, :sp.S] = NEG
    if not cfg.split:
        out[:, sp.still(0)] = level
    else:
        still_level = base + gw * (still - walking)
        transit_level = base + gw * (walking - still)
        for p in range(sp.P):
            out[:, sp.still(p)] = still_level
            for k in range(cfg.clock_max + 1):
                out[:, sp.transit(p, k)] = transit_level
    return out
