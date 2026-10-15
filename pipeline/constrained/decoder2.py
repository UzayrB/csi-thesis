"""The rebuilt decoder. Brief: reports/decoder_rebuild_prompt_2026-09-17.md, STAGE 2.

Four changes to the frozen decoder, each switchable so it can be measured alone and then combined:

  veto        2.1  when the motion gate reads stationary, every path state is forbidden
  split       2.2  the null state becomes STILL and TRANSIT; TRANSIT carries a walking clock and,
                   with ``geometry``, the minimum transit time from the line just left to each line
  late_entry  2.3  a chain may be entered at any arc length the walking clock allows, at a cost per
                   window left unexplained; the entry is the catch-up and is logged as a revision
  normalise   2.4  the along-path score row-normalised, the control the old metric rejected

With every flag off the state space and transition matrix reduce to the frozen decoder's, which the
tests assert, so the stage 1 baseline is a configuration of this module rather than a different one.

STATES. Path states are 0 .. S-1 as before. Without ``split`` there is one null state at index S.
With it, STILL(p) for p in 0..12 (0 = no line left yet, i = line i just left) and TRANSIT(p, k) for
the same p and a clock k in 0..K windows walked since the last stationary reading. The line just
left persists through STILL, because someone who finishes a line, stops, and walks on still has to
cover the distance to the next line's start. The clock is what makes late entry well posed: from
TRANSIT(p, k) a line may be entered at any arc length s with s <= v (k + 1), and with ``geometry``
only if k also covers the transit from end(p).

The committed track is a connected walk through THIS state space by construction, and every entry
mid-chain is a transition this matrix contains, so the impossible-transition audit is run against
the matrix actually used.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

import numpy as np

from pipeline.constrained.common import DT, V_MEAN
from pipeline.constrained.decoder import (
    NEG, along_log_score, along_transition, decoded_paths, decoded_xy, fixed_lag_viterbi, viterbi,
)

MOTION_THETA = 0.431


@dataclass(frozen=True)
class Config:
    veto: bool = False
    veto_hysteresis: int = 1        #: consecutive stationary windows before path states are forbidden
    split: bool = False
    geometry: bool = False          #: needs split
    late_entry: bool = False        #: needs split
    margin: float = 0.0             #: commitment margin in nats, charged on every entry
    #: I3: an ADDITIONAL entry cost in nats applied only to lines that have parallel siblings, the
    #: six members of {A_fwd, E_col1, E_col5} and {B_fwd, E_row1, E_row5}. Diagonals, A_rev and
    #: B_rev have no sibling and are never affected. Default 0.0 leaves the decoder bit-identical.
    #: MAY BE NEGATIVE, and that is deliberate. The brief assumed the failure was committing to the
    #: WRONG sibling too early, which a positive margin would fix by waiting. Phase 1 measured the
    #: opposite: wrong-parallel commitments are only 10 of 216 and happen no earlier than correct
    #: ones, while the sibling lines LEAD the hypothesis on 44.9 percent of cross-day passes and
    #: commit on 19.4. The failure is under-commitment, so the sweep must be free to lower the
    #: barrier as well as raise it.
    sibling_margin: float = 0.0
    #: Scales the spread of the chain step model. along_log_score uses sd = V_SD * DT * sd_scale, so
    #: 1.0 is the shipped 0.123 m tolerance around a 1.298 m per window advance. It does NOT move the
    #: implied mean speed, only how hard the model insists on it. Exposed for the phase 3 sweep: the
    #: mean was measured correct (1.298 implied against 1.302 over 360 labelled passes, 0.04 sd), so
    #: the spread is the part of the duration model that could still be wrong.
    sd_scale: float = 1.0
    lam: float = 1.0                #: nats per walking window left unexplained by a late entry
    normalise: bool = False
    null_self: float = 0.9
    exit_k: int = 1
    exit_p: float = 0.5
    clock_max: int = 8              #: K, windows; the clock saturates here
    kind: str = "tight"
    #: Amendment C3. Log-odds of P(this walking bout contains a pass), fitted on the TRAINING side
    #: and charged on every entry into a chain from a walking state. Stage 0 found 866 of 1110
    #: walking bouts contain no pass, so about 78 percent of all walking is transit and the decoder
    #: carried no notion of it. PROTOCOL DEPENDENT: the ratio is a property of this capture
    #: protocol, not of the room, and the freeze says so.
    bout_log_odds: float = 0.0
    abort_cost: float = 60.0        #: nats to abandon a chain mid-line; only ever cheaper than NEG

    def label(self) -> str:
        on = [k for k in ("veto", "split", "geometry", "late_entry", "normalise") if getattr(self, k)]
        if self.bout_log_odds:
            on.append("bout_prior")
        return ("+".join(on) or "frozen") + f" ns{self.null_self} k{self.exit_k}" + \
            (f" m{self.margin:g}" if self.late_entry else "") + \
            (f" b{self.bout_log_odds:+.2f}" if self.bout_log_odds else "")


FROZEN = Config()


class Space:
    """Index bookkeeping for the extended state space."""

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

    def still(self, p: int = 0) -> int:
        return self.still0 + (p if self.cfg.split else 0)

    def transit(self, p: int, k: int) -> int:
        assert self.cfg.split
        return self.transit0 + p * (self.cfg.clock_max + 1) + min(k, self.cfg.clock_max)

    def kind(self, state: int) -> str:
        if state < self.S:
            return "path"
        if not self.cfg.split or state < self.transit0:
            return "still"
        return "transit"

    def kinds(self, seq: np.ndarray) -> np.ndarray:
        seq = np.asarray(seq, int)
        out = np.full(len(seq), "path", dtype="U7")
        out[seq >= self.S] = "still"
        if self.cfg.split:
            out[seq >= self.transit0] = "transit"
        return out


_LT_CACHE: dict = {}


def transition_matrix2(st, cfg: Config, transit_min_windows: Optional[dict] = None) -> np.ndarray:
    """The whole log transition matrix for ``cfg``. Cached per configuration."""
    key = (id(st), asdict(cfg).__repr__(), id(transit_min_windows) if cfg.geometry else 0)
    if key in _LT_CACHE:
        return _LT_CACHE[key]
    sp = Space(st, cfg)
    S, N = sp.S, sp.N
    out = np.full((N, N), NEG, dtype=float)

    # along each chain
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
    #: I3: per-line entry cost. Only the six lines with a parallel sibling see the adjustment.
    SIBLING_LINES = frozenset(("A_fwd", "E_col1", "E_col5", "B_fwd", "E_row1", "E_row5"))
    def entry_for(nm: str) -> float:
        return log_entry - (float(cfg.sibling_margin) if nm in SIBLING_LINES else 0.0)
    log_entry_walking = log_entry + float(cfg.bout_log_odds)
    k_exit = max(1, int(cfg.exit_k))
    v_step = V_MEAN * DT
    # THE ABORT, needed by the veto. With binding commitments the decoder can be on a chain when the
    # gate turns stationary; the veto then makes every path emission NEG and, mid-chain, no exit
    # exists, so the argmax among impossible options emitted an illegal move (16 of them on a random
    # test sequence at lag 0). So every path state may fall to STILL at a cost of abort_cost nats,
    # which is worse than the worst legal on-chain step (standing still on the line scores about
    # -55.7), so it never wins in ordinary decoding and always wins over NEG. It is in the matrix,
    # so the audit sees it as what it is: the gate forbidding the chain, not the decoder wandering.
    log_abort = -float(cfg.abort_cost) if cfg.veto else None

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
        # leaving a line: to STILL(line) or TRANSIT(line, 0)
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
            out[s_, sp.transit(p, 0)] = log_leave                 # walking onset
            # direct entry from standing, at the line's first state, if no transit is owed
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
                    # late entry: any arc length the clock allows, penalised per window unexplained
                    s_rel = st.s_of[i0:i1] - st.s_of[i0]
                    for j in range(i1 - i0):
                        unexplained = s_rel[j] / v_step
                        if s_rel[j] <= v_step * (k + 1) + 1e-9 and k >= owed + int(np.floor(unexplained)):
                            out[t_, i0 + j] = entry_nm - cfg.lam * unexplained
    _LT_CACHE[key] = out
    return out


def stack2(e_path: np.ndarray, gate_e: np.ndarray, ne, sp: Space) -> np.ndarray:
    """``(T, N)`` emissions: path columns, then STILL and TRANSIT columns, with the gate veto."""
    T = e_path.shape[0]
    cfg = sp.cfg
    g = np.asarray(gate_e, float)
    theta = float(getattr(ne, "motion_theta", MOTION_THETA))
    still = (g < theta).astype(float)
    walking = 1.0 - still
    gw = float(getattr(ne, "gate_weight", 0.0))
    level = np.asarray(ne(g), float)                     # the fitted null level, still bonus included
    base = level - gw * still                             # the level with the still bonus removed
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


def decode2(e_path: np.ndarray, gate_e: np.ndarray, ne, st, cfg: Config,
            transit_min_windows: Optional[dict] = None, lag: Optional[int] = None) -> dict:
    """Decode one recording under ``cfg``: offline (``lag`` None) or fixed-lag with binding
    commitments. Returns the committed track, its kinds, its revisions and the matrix used."""
    sp = Space(st, cfg)
    lT = transition_matrix2(st, cfg, transit_min_windows)
    e = stack2(e_path, gate_e, ne, sp)
    seq = viterbi(e, lT) if lag is None else fixed_lag_viterbi(e, lT, int(lag))
    names = decoded_paths(seq, st)
    revisions = []
    for i in range(1, len(seq)):
        if names[i] and names[i] != names[i - 1]:
            first = st.slice_of[str(names[i])][0]
            if int(seq[i]) > first:
                revisions.append({"window": int(i), "kind": "entry",
                                  "distance_m": float(st.s_of[int(seq[i])] - st.s_of[first])})
    return {"seq": seq, "names": names, "xy": decoded_xy(seq, st), "on_path": names != "",
            "kinds": sp.kinds(seq), "revisions": revisions, "log_T": lT, "config": cfg.label()}


def provisional_track(e_path: np.ndarray, gate_e: np.ndarray, ne, st, cfg: Config,
                      transit_min_windows: Optional[dict] = None) -> np.ndarray:
    """Stage 3's provisional track: the fixed-lag-1 argmax of the UN-collapsed forward belief.
    Shown immediately, allowed to be wrong, and audited so the cost of showing it is a number."""
    sp = Space(st, cfg)
    lT = transition_matrix2(st, cfg, transit_min_windows)
    e = stack2(e_path, gate_e, ne, sp)
    Tn, N = e.shape
    dp = e[0].copy()
    back = np.zeros((Tn, N), dtype=np.int32)
    out = np.full(Tn, -1, dtype=np.int32)
    prev = None
    for t in range(1, Tn):
        m = dp[:, None] + lT
        back[t] = m.argmax(0)
        dp = m.max(0) + e[t]
        dp -= dp.max()
        j = int(dp.argmax())
        out[t - 1] = int(back[t, j])          # the state for t-1 on the best path ending at t
        prev = j
    out[Tn - 1] = int(prev) if prev is not None else int(dp.argmax())
    return out


def fit_adaptive_null2(blocks, st, cfg: Config, transit_min_windows: Optional[dict] = None,
                       grid: str = "full", lag: Optional[int] = None) -> tuple:
    """The adaptive null rule (quantile, offset, still weight) selected THROUGH THIS decoder on the
    training blocks, by F1 on the on-path class, exactly as stage 4 fitted it through the old one.
    ``grid`` 'full' is stage 4's 189 candidates; 'coarse' is 42 and is used only where the full grid
    is stated as unaffordable. ``lag`` fits THROUGH the fixed-lag decoder at that display lag rather
    than offline: a level that best separates on-path windows for a global Viterbi is the wrong level
    for a decoder that must commit within two windows, and measured on the hardest pairing the
    offline-fitted level found 18 percent of passes offline and none live."""
    from pipeline.constrained.emissions import AdaptiveNullEmission
    quantiles = (0.25, 0.5, 0.75)
    offsets = np.linspace(-8.0, 2.0, 21 if grid == "full" else 7)
    gws = (0.0, 2.0, 4.0) if grid == "full" else (0.0, 4.0)
    sp = Space(st, cfg)
    lT = transition_matrix2(st, cfg, transit_min_windows)
    best = (None, -1.0, None)
    for q in quantiles:
        refs = [float(np.quantile(np.asarray(e).max(1), q)) for e, _g, _on, _gr in blocks]
        for off in offsets:
            for gw in gws:
                tp = fp = fn = 0
                for (e, g, on, grace), ref in zip(blocks, refs):
                    ne = AdaptiveNullEmission(quantile=q, offset=float(off), gate_weight=gw)
                    ne._ref = ref
                    ee = stack2(e, g, ne, sp)
                    seq = viterbi(ee, lT) if lag is None else fixed_lag_viterbi(ee, lT, int(lag))
                    pred = decoded_paths(seq, st) != ""
                    sc = ~np.asarray(grace, bool)
                    on_ = np.asarray(on, bool)
                    tp += int((pred & on_ & sc).sum()); fp += int((pred & ~on_ & sc).sum())
                    fn += int((~pred & on_ & sc).sum())
                prec, rec = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
                f1 = 2 * prec * rec / max(prec + rec, 1e-9)
                if f1 > best[1]:
                    best = (AdaptiveNullEmission(quantile=q, offset=float(off), gate_weight=gw), f1,
                            {"precision_pct": round(100 * prec, 1), "recall_pct": round(100 * rec, 1)})
    if best[0] is None:
        return None, {"fitted": False}
    return best[0], {"fitted": True, "f1": round(best[1], 4), "counts": best[2], "grid": grid,
                     "fitted_at_lag": lag, **best[0].to_dict()}


def fit_bout_prior(train_rows, st) -> tuple:
    """Amendment C3. P(a walking bout contains a pass), on the TRAINING side of one pairing only.

    ``train_rows`` are ``(stem, rec, gate_energy)``. Returns (log_odds, info). Never pooled across
    pairings, and reported in the freeze as PROTOCOL DEPENDENT: it is the ratio of pass-walking to
    transit-walking under this capture protocol, not a property of the room.
    """
    from pipeline.constrained.bout import bouts_of
    n_bout = n_pass = 0
    for _stem, rec, ge in train_rows:
        modes = np.asarray(rec.mode, dtype=object)
        for a, b in bouts_of(ge):
            n_bout += 1
            n_pass += int((modes[a:b + 1] == "walk").any())
    if n_bout == 0:
        return 0.0, {"fitted": False, "reason": "no walking bouts on the training side"}
    # add-one smoothing so a pairing with no pass-bearing bout does not give an infinite penalty
    p = (n_pass + 1.0) / (n_bout + 2.0)
    lo = float(np.log(p / (1.0 - p)))
    return lo, {"fitted": True, "bouts": n_bout, "bouts_with_a_pass": n_pass,
                "p_bout_contains_a_pass": round(p, 4), "log_odds": round(lo, 4),
                "protocol_dependent": True,
                "note": "fitted on the training side of this pairing alone, never pooled"}
