# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: T9, the line: after each SPACE press, which of the twelve lines (or none) the walker is on.

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

import numpy as np

from pipeline.tracking.settings import STRIDE, WINDOW_S, Recording

NEG = -1e18



V_MEAN, V_SD = 1.298, 0.123
DT = 1.0
SPACE_DT = 1.0


# The frozen tracker's walking-pace prior and time step (its meta.json), set before any decode.
def set_pace(v_mean: float, v_sd: float, dt: float) -> None:
    global V_MEAN, V_SD, DT
    V_MEAN, V_SD, DT = float(v_mean), float(v_sd), float(dt)
    _LT_CACHE.clear()



# The UNNORMALISED log score of every step along one chain; with max_advance (metres), a longer step is...
def along_log_score(s_vals: np.ndarray, kind: str = "tight", sd_scale: float = 1.0,
                    broad_sd: float = 1.5, max_advance: float = None) -> np.ndarray:
    s = np.asarray(s_vals, float)
    d = s[None, :] - s[:, None]
    if kind == "forward_uniform":
        out = np.where(d >= -1e-9, 0.0, NEG)
    elif kind == "broad":
        out = -0.5 * (d / max(broad_sd, 1e-6)) ** 2
    else:
        sd = max(V_SD * DT * sd_scale, 1e-3)
        out = -0.5 * ((d - V_MEAN * DT) / sd) ** 2
        out = np.where(d < -1e-9, NEG, out)
        if max_advance is not None:
            out = np.where(d > float(max_advance) + 1e-9, NEG, out)
    return out


# Row-stochastic transition over one chain's arc-length states.
def along_transition(s_vals: np.ndarray, kind: str = "tight", sd_scale: float = 1.0,
                     broad_sd: float = 1.5) -> np.ndarray:
    s = np.asarray(s_vals, float)
    d = s[None, :] - s[:, None]
    if kind == "forward_uniform":
        W = (d >= -1e-9).astype(float)
    elif kind == "broad":
        W = np.exp(-0.5 * (d / max(broad_sd, 1e-6)) ** 2)
    else:
        sd = max(V_SD * DT * sd_scale, 1e-3)
        W = np.exp(-0.5 * ((d - V_MEAN * DT) / sd) ** 2)
        W[d < -1e-9] = 0.0
    rs = W.sum(1, keepdims=True)
    dead = (rs[:, 0] <= 1e-300)
    if dead.any():
        W[dead] = 0.0
        W[dead, np.flatnonzero(dead)] = 1.0
        rs = W.sum(1, keepdims=True)
    return W / rs


# The whole transition matrix, path chains plus the null state, in LOG space.
def transition_matrix(states, kind: str = "tight", sd_scale: float = 1.0, broad_sd: float = 1.5,
                      null_self: float = 0.9, exit_p: float = 0.5,
                      exit_from_last_k: int = 1, entry_prior: Optional[np.ndarray] = None,
                      with_null: bool = True, normalise_along: bool = False, max_advance: float = None) -> np.ndarray:
    S = states.n_states
    N = S + 1 if with_null else S
    out = np.full((N, N), NEG, dtype=float)
    for nm in states.names:
        i0, i1 = states.slice_of[nm]
        if normalise_along:
            T = along_transition(states.s_of[i0:i1], kind, sd_scale, broad_sd)
            blk = np.full_like(T, NEG)
            np.log(T, out=blk, where=T > 0)
        else:
            blk = along_log_score(states.s_of[i0:i1], kind, sd_scale, broad_sd, max_advance)
        out[i0:i1, i0:i1] = blk
    if with_null:
        null = S
        k = max(1, int(exit_from_last_k))
        log_exit = float(np.log(max(exit_p, 1e-12)))
        for nm in states.names:
            i0, i1 = states.slice_of[nm]
            for i in range(max(i0, i1 - k), i1):
                out[i, null] = log_exit
        p = (np.full(len(states.names), 1.0 / len(states.names)) if entry_prior is None
             else np.asarray(entry_prior, float) / max(float(np.sum(entry_prior)), 1e-12))
        out[null, :] = NEG
        out[null, null] = float(np.log(max(null_self, 1e-12)))
        for j, nm in enumerate(states.names):
            w = (1.0 - null_self) * p[j]
            out[null, states.slice_of[nm][0]] = float(np.log(w)) if w > 0 else NEG
    return out



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


# The whole log transition matrix for cfg (cached; the speed cap is part of the key).
def transition_matrix2(st, cfg: Config, transit_min_windows: Optional[dict] = None,
                       max_advance: float = None) -> np.ndarray:
    key = (id(st), asdict(cfg).__repr__(), id(transit_min_windows) if cfg.geometry else 0, max_advance)
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
            blk = along_log_score(st.s_of[i0:i1], cfg.kind, cfg.sd_scale, max_advance=max_advance)
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
    v_step = V_MEAN * SPACE_DT
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



# A null level anchored to the CURRENT recording's own emission scale, not to the training days.
class AdaptiveNullEmission:

    # Sets up the object.
    def __init__(self, quantile: float = 0.5, offset: float = 0.0, gate_weight: float = 0.0,
                 motion_theta: float = 0.431):
        self.quantile = float(np.clip(quantile, 0.01, 0.999))
        self.offset = float(offset)
        self.gate_weight = float(gate_weight)
        self.motion_theta = float(motion_theta)
        self._ref = None

    # Set the reference from this recording's own peaks.
    def calibrate(self, path_emission: np.ndarray) -> "AdaptiveNullEmission":
        self._ref = float(np.quantile(np.asarray(path_emission).max(1), self.quantile))
        return self

    # Calls the object.
    def __call__(self, gate_energy: np.ndarray) -> np.ndarray:
        if self._ref is None:
            raise RuntimeError("calibrate() must be called on the recording before decoding it")
        still = (np.asarray(gate_energy, float) < self.motion_theta).astype(float)
        return self._ref + self.offset + self.gate_weight * still

    # Function to dict.
    def to_dict(self) -> dict:
        return {"kind": "adaptive", "quantile": self.quantile, "offset": self.offset,
                "gate_weight": self.gate_weight, "motion_theta": self.motion_theta,
                "reference_of_last_recording": self._ref}

    # Choose the quantile, offset and gate weight on the TRAINING recordings, by F1.
    @classmethod
    def fit(cls, path_emissions, gate_energies, on_path_masks, grace_masks, states, log_T,
            quantiles=(0.25, 0.5, 0.75), offsets=None, gate_weights=(0.0, 2.0, 4.0)) -> tuple:
        if offsets is None:
            offsets = np.linspace(-8.0, 2.0, 21)
        best = (None, -1.0, None)
        for q in quantiles:
            refs = [float(np.quantile(np.asarray(e).max(1), q)) for e in path_emissions]
            for off in offsets:
                for gw in gate_weights:
                    tp = fp = fn = 0
                    for e, g, on, grace, ref in zip(path_emissions, gate_energies, on_path_masks,
                                                    grace_masks, refs):
                        ne = cls(quantile=q, offset=float(off), gate_weight=gw)
                        ne._ref = ref
                        pred = decoded_paths(viterbi(stack_with_null(e, ne(g)), log_T), states) != ""
                        sc = ~np.asarray(grace, bool)
                        on_ = np.asarray(on, bool)
                        tp += int((pred & on_ & sc).sum())
                        fp += int((pred & ~on_ & sc).sum())
                        fn += int((~pred & on_ & sc).sum())
                    prec, rec = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
                    f1 = 2 * prec * rec / max(prec + rec, 1e-9)
                    if f1 > best[1]:
                        best = (cls(quantile=q, offset=float(off), gate_weight=gw), f1,
                                {"precision_pct": round(100 * prec, 1),
                                 "recall_pct": round(100 * rec, 1)})
        if best[0] is None:
            return cls(), {"fitted": False, "reason": "no candidate scored"}
        return best[0], {"fitted": True, "f1": round(best[1], 4), "counts": best[2],
                         "selected_on": "F1 over the on-path class on the training recordings, each "
                                        "calibrated per recording as it would be at test time",
                         **best[0].to_dict()}


# (T, n_states) plus (T,) to (T, n_states + 1), the null state last.
def stack_with_null(path_emis: np.ndarray, null_emis: np.ndarray) -> np.ndarray:
    return np.concatenate([path_emis, np.asarray(null_emis, float)[:, None]], axis=1)



# Offline Viterbi over the whole sequence.
def viterbi(log_emis: np.ndarray, log_T: np.ndarray,
            log_start: Optional[np.ndarray] = None) -> np.ndarray:
    Tn, S = log_emis.shape
    dp = np.full((Tn, S), NEG)
    back = np.zeros((Tn, S), dtype=np.int32)
    dp[0] = log_emis[0] + (0.0 if log_start is None else log_start)
    for t in range(1, Tn):
        m = dp[t - 1][:, None] + log_T
        back[t] = m.argmax(0)
        dp[t] = m.max(0) + log_emis[t]
    out = np.zeros(Tn, dtype=np.int32)
    out[-1] = int(dp[-1].argmax())
    for t in range(Tn - 1, 0, -1):
        out[t - 1] = back[t, out[t]]
    return out


# The path name for each decoded state, or '' where the decoder was in the null state.
def decoded_paths(seq: np.ndarray, states) -> np.ndarray:
    out = np.empty(len(seq), dtype="U10")
    out[:] = ""
    on = seq < states.n_states
    out[on] = states.path_of[seq[on]]
    return out


# The coordinate for each decoded state.
def decoded_xy(seq: np.ndarray, states, null_xy=(2.5, 2.5)) -> np.ndarray:
    out = np.tile(np.asarray(null_xy, float), (len(seq), 1))
    on = seq < states.n_states
    out[on] = states.xy[seq[on]]
    return out



# The decoded position at each display step, from a fixed-lag Viterbi backtrace.
def fixed_lag_path(e_stacked, lT, st_lo, st, lo, hi, lag_w):
    n = hi - lo + 1
    out, held = [], 0
    last_on = None
    for i in range(n):
        end = min(hi, lo + i + lag_w)
        s = viterbi(e_stacked[lo:end + 1], lT, log_start=st_lo)
        k = int(s[i]) if i < len(s) else int(s[-1])
        on_chain = k < st.n_states
        if on_chain:
            last_on = k
        elif last_on is not None:
            held += 1
            k = last_on
        else:
            held += 1
        name = chain_of(st, k) if k < st.n_states else ""
        out.append({"step": i, "window": lo + i, "evidence_window": int(end), "state": int(k),
                    "line": name, "on_chain": bool(on_chain)})
    return out, held


# The drawn path AFTER the lock: a fixed-lag Viterbi restricted to ONE chain.
def locked_chain_path(e_res, lT_chains, st, lo, hi, lag_w, chain, log_start=None):
    a, b = st.slice_of[chain]
    sub_T = lT_chains[a:b, a:b]
    e_sub = np.asarray(e_res)[:, a:b]
    ls = None
    if log_start is not None:
        ls = np.asarray(log_start, float)[a:b].copy()
        m = float(np.max(ls[np.isfinite(ls)])) if np.isfinite(ls).any() else 0.0
        ls = ls - m
    out = []
    n = hi - lo + 1
    for i in range(n):
        end = min(hi, lo + i + lag_w)
        s_ = viterbi(e_sub[lo:end + 1], sub_T, log_start=ls)
        k = int(s_[i]) if i < len(s_) else int(s_[-1])
        out.append({"step": i, "window": lo + i, "evidence_window": int(end), "state": int(a + k),
                    "line": chain, "on_chain": True})
    return out


# Function chain of.
def chain_of(st, state_idx):
    for nm in st.names:
        a, b = st.slice_of[nm]
        if a <= state_idx < b:
            return nm
    return ""


# Where the dot jumps to at the start press: the best ON-CHAIN state under the entry prior.
def entry_position(e_stacked, st_lo, st, lo):
    v = np.asarray(st_lo, float)[:st.n_states] + np.asarray(e_stacked[lo], float)[:st.n_states]
    if not np.isfinite(v).any():
        return None, ""
    k = int(np.nanargmax(np.where(np.isfinite(v), v, -np.inf)))
    return k, chain_of(st, k)



NEG_BIG = -1e30


MAX_WALK_S = 20.0
LOCK_DELAYS_S = (0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0)
FAMILY_OF = {"A": "vert", "B": "horz", "C": "diagC", "D": "diagD", "E": "edge"}


# Function default opts.
def default_opts() -> dict:
    return {"entry": "free", "prior_flatten": 0.0, "cand_thresh": None,
            "chain_logprior": None, "family_first": False, "e_rescore": None,
            "final_rule": "majority"}


# Arm A: mix each chain's within-chain step model towards uniform by a fraction f.
def flatten_chain_prior(lT, st, f: float):
    if f <= 0:
        return lT
    lT2 = lT.copy()
    for nm in st.names:
        lo, hi = st.slice_of[nm]
        blk = np.exp(lT2[lo:hi, lo:hi])
        reach = blk > 0
        n_reach = reach.sum(axis=1, keepdims=True)
        uni = np.where(reach, 1.0 / np.maximum(n_reach, 1), 0.0)
        mix = (1.0 - f) * blk + f * uni
        s = mix.sum(axis=1, keepdims=True)
        mix = np.where(s > 0, mix / np.maximum(s, 1e-300), 0.0)
        with np.errstate(divide="ignore"):
            lT2[lo:hi, lo:hi] = np.where(mix > 0, np.log(np.maximum(mix, 1e-300)), NEG_BIG)
    return lT2


# The initial distribution over states at the start press.
def entry_start(kind, e_stacked, st, sp, lo, on_chain, first_state):
    start = np.full(sp.N, NEG_BIG)
    if kind == "hard":
        start[first_state] = 0.0
    elif kind == "soft":
        v = np.full(sp.N, NEG_BIG)
        v[:st.n_states] = e_stacked[lo, :st.n_states]
        m = float(np.max(v[:st.n_states]))
        if np.isfinite(m):
            v[:st.n_states] -= m
        start = v
    else:
        start[on_chain] = 0.0
    return start


# Total log-likelihood of every chain over one window range, by Viterbi within the chain.
def chain_totals(e_chain, st, seq_range, lT_chains, chain_logprior=None):
    out = {}
    for nm in st.names:
        a, b = st.slice_of[nm]
        sub_e = e_chain[seq_range, a:b]
        sub_T = lT_chains[a:b, a:b]
        s = viterbi(sub_e, sub_T)
        tot = float(sub_e[np.arange(len(s)), s].sum())
        if chain_logprior:
            tot += float(chain_logprior.get(nm, 0.0))
        out[nm] = tot
    return out


# The final line from per-chain totals, flat or family-first (arm C).
def pick_line(totals, st, family_first=False):
    if not totals:
        return ""
    if not family_first:
        return max(totals, key=totals.get)
    fam = {}
    for nm, v in totals.items():
        f = FAMILY_OF.get(nm.split("_")[0], "other")
        fam.setdefault(f, []).append(v)
    # Function lse.
    def lse(xs):
        m = max(xs)
        return m + float(np.log(sum(np.exp(x - m) for x in xs)))
    best_fam = max(fam, key=lambda f: lse(fam[f]))
    members = {nm: v for nm, v in totals.items()
               if FAMILY_OF.get(nm.split("_")[0], "other") == best_fam}
    return max(members, key=members.get)


# The semi-bounded decoder: for each walk, where it ends (the causal exit), the committed line, and with...
def night_track(e_path, rec, st, cfg, transit, ne, ge, stride_s, opts=None, want_display=False, display_lags_w=(0, 1, 2),
                display_delays_s=LOCK_DELAYS_S, display_to_horizon=False, display_alt_e=None, display_alt_flatten=None,
                display_lead_in_w=0, display_switch_paths=False, max_advance=None, path_lag_extra=0):
    o = dict(default_opts())
    o.update(opts or {})
    sp = Space(st, cfg)
    lT = transition_matrix2(st, cfg, transit, max_advance=max_advance)
    lT = flatten_chain_prior(lT, st, float(o["prior_flatten"]))
    lT_chains = transition_matrix(st, "tight", with_null=False, max_advance=max_advance)
    ne.calibrate(e_path)
    e_stacked = stack2(e_path, ge, ne, sp)

    all_names = np.asarray(decoded_paths(np.arange(sp.N), st)).astype(str)
    on_chain = all_names != ""
    first_state = np.zeros(sp.N, bool)
    for nm in st.names:
        first_state[st.slice_of[nm][0]] = True
    horizon_w = int(round(MAX_WALK_S / stride_s))
    n = len(rec)
    out = []

    for pid, nm, _p_lo, _p_hi in rec.pass_spans():
        w = np.flatnonzero((rec.pass_id == pid) & (rec.mode == "walk"))
        if len(w) < 2:
            continue
        lo = int(w[0])
        hi_lim = int(min(n - 1, len(e_stacked) - 1, lo + horizon_w))
        if hi_lim <= lo:
            continue
        st_lo = entry_start(o["entry"], e_stacked, st, sp, lo, on_chain, first_state)
        if o.get("entry_window_m"):
            lim = float(o["entry_window_m"])
            st_lo = np.asarray(st_lo, float).copy()
            s_arr = np.asarray(st.s_of, float)
            for nm_x in st.names:
                aa, bb = st.slice_of[nm_x]
                far = aa + np.flatnonzero((s_arr[aa:bb] - s_arr[aa]) > lim + 1e-9)
                if len(far):
                    st_lo[far] = NEG_BIG
        start_adj = None
        if o.get("start_term") is not None:
            start_adj = (o["start_term"] or {}).get(f"{rec.session}|{rec.stem}|{int(pid)}")

        d = np.asarray(e_stacked[lo], float) + np.asarray(st_lo, float)
        end_i, timeout_fired = hi_lim, True
        for k in range(1, hi_lim - lo + 1):
            d = np.asarray(e_stacked[lo + k], float) + (d[:, None] + lT).max(axis=0)
            if int(np.nanargmax(np.where(np.isfinite(d), d, -np.inf))) >= st.n_states:
                end_i, timeout_fired = lo + k, False
                break
        sl = slice(lo, end_i + 1)

        disp_paths, entry_k, entry_nm, disp_locked = None, None, "", None
        if want_display:
            disp_paths = {}
            disp_hi = hi_lim if display_to_horizon else end_i
            lo_disp = max(0, lo - int(display_lead_in_w))
            lw0 = int(round((WINDOW_S / 2.0) / stride_s))
            for lw in display_lags_w:
                if int(lw) - lw0 < 0:
                    raise AssertionError(f"display lag {lw} windows is shorter than the {lw0} windows a {WINDOW_S:g} s window "
                                         "needs to finish recording; it cannot be drawn causally")
                disp_paths[str(int(lw))], _held = fixed_lag_path(e_stacked, lT, st_lo, st, lo_disp, disp_hi, int(lw) - lw0)
            entry_k, entry_nm = entry_position(e_stacked, st_lo, st, lo)
            disp_locked = {}
            for lw in display_lags_w:
                free = disp_paths[str(int(lw))]
                for delay in display_delays_s:
                    li = max(0, min(int(round(delay / stride_s)) - int(lw), len(free) - 1))
                    nm_lock = free[li]["line"] or entry_nm or st.names[0]
                    node = {"lock_step": li, "lock_line": nm_lock, "lo_disp": int(lo_disp),
                            "evidence_horizon_w": int(lw) - lw0,
                            "path": locked_chain_path(e_path, lT_chains, st, lo_disp, disp_hi,
                                                      int(lw) - lw0 + int(path_lag_extra), nm_lock,
                                                      log_start=st_lo)}
                    if display_alt_e:
                        node["paths_alt"] = {}
                        for key_, v in display_alt_e.items():
                            lTk = lT_chains
                            fk = (display_alt_flatten or {}).get(key_)
                            if fk:
                                lTk = flatten_chain_prior(lT_chains, st, float(fk))
                            alt = np.resize(v, (len(e_path), np.shape(v)[1]))
                            node["paths_alt"][key_] = locked_chain_path(alt, lTk, st, lo_disp, disp_hi,
                                                                        int(lw) - lw0 + int(path_lag_extra),
                                                                        nm_lock, log_start=st_lo)
                            if display_switch_paths:
                                node.setdefault("switch_paths", {})[key_] = {
                                    nm_z: (node["paths_alt"][key_] if nm_z == nm_lock else
                                           locked_chain_path(alt, lTk, st, lo_disp, disp_hi,
                                                             int(lw) - lw0 + int(path_lag_extra), nm_z,
                                                             log_start=st_lo))
                                    for nm_z in st.names}
                    disp_locked[f"{int(lw)}|{delay}"] = node

        tot = chain_totals(e_path, st, sl, lT_chains, o["chain_logprior"])
        if start_adj:
            tot = {k: v + start_adj.get(k, 0.0) for k, v in tot.items()}
        final = pick_line(tot, st, o["family_first"])
        out.append({"key": f"{rec.session}|{rec.stem}|{int(pid)}", "pass_id": int(pid), "true_line": nm,
                    "final_line": final, "timeout_fired": bool(timeout_fired), "lo": int(lo), "own_end_i": int(end_i),
                    "exit_search_hi": int(hi_lim), "display_paths": disp_paths, "display_locked": disp_locked,
                    "entry_state": (int(entry_k) if entry_k is not None else None), "entry_line": entry_nm})
    return out



LOOKBACK_W = 8


# Class Live Decoder.
class LiveDecoder:
    # Sets up the object.
    def __init__(self, st, cfg, ne, transit, opts: dict, session: str, stem: str):
        self.st, self.cfg, self.ne, self.transit = st, cfg, ne, transit
        self.opts = dict(opts)
        self.session, self.stem = session, stem
        self.t0, self.t0_epoch, self.e, self.ge = [], [], [], []
        self.passes = []

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
        n = b - a + 1
        t0 = np.asarray(self.t0[a:b + 1], float)
        walk = np.zeros(n, bool)
        walk[p["lo"] - a:] = True
        mode = np.where(walk, "walk", "idle").astype("U10")
        pass_id = np.where(walk, p["pid"], -1)
        return Recording(session=self.session, stem=self.stem, participant="live", t0=t0,
                         t0_epoch=np.asarray(self.t0_epoch[a:b + 1], float), mode=mode, pass_id=pass_id,
                         path_name=np.where(walk, "", "").astype("U10"),
                         xy=np.full((n, 2), np.nan), cell_id=np.full(n, "", dtype="U10"),
                         gap_flag=np.zeros(n, bool))

    # Function decode.
    def _decode(self, p, k: int, final: bool = False):
        a = max(0, p["lo"] - LOOKBACK_W)
        rec = self._recording(a, k, p)
        e = np.asarray(self.e[a:k + 1], float)
        assert float(np.max(np.abs(e.max(axis=1)))) == 0.0, \
            "the pooled emission is not max-normalised: the null reference would not be 0 on a prefix"
        o = dict(self.opts)
        o["start_term"] = {f"{self.session}|{self.stem}|{p['pid']}": p["term"]} if p["term"] is not None else None
        rows = night_track(e, rec, self.st, self.cfg, self.transit, self.ne, np.asarray(self.ge[a:k + 1]),
                           STRIDE, o)
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
