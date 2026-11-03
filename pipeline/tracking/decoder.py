# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: T9, the line: after each SPACE press, which of the twelve lines the walker is on.

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from pipeline.tracking.settings import STRIDE_S

NEG = -1e18
NEG_BIG = -1e30
MAX_WALK_S = 20.0
LOOKBACK_W = 8
FAMILY_OF = {"A": "vert", "B": "horz", "C": "diagC", "D": "diagD", "E": "edge"}
LOCK_STEP = 2
ENTRY_WINDOW_M = 1.0
MOTION_THETA = 0.431


V_MEAN, V_SD = 1.298, 0.123
DT = 1.0
SPACE_DT = 1.0


# The frozen tracker's walking-pace prior and time step (its meta.json), set before any decode.
def set_pace(v_mean: float, v_sd: float, dt: float) -> None:
    global V_MEAN, V_SD, DT
    V_MEAN, V_SD, DT = float(v_mean), float(v_sd), float(dt)
    _LT_CACHE.clear()



# Class Live Decoder.
class LiveDecoder:
    # Sets up the object.
    def __init__(self, st, cfg, ne, transit, opts: dict):
        self.st, self.cfg, self.ne, self.transit = st, cfg, ne, transit
        self.opts = dict(opts)
        self.t0, self.t0_epoch, self.e, self.ge = [], [], [], []
        self.passes = []

    # The operator's start press, at the raw key time.
    def press(self, t_press: float, pid: int) -> None:
        self.passes.append({"pid": int(pid), "press": float(t_press), "lo": None, "term": None, "done": False})

    # The pass's start term (A2 and the veto reader), available one second after its press.
    def set_term(self, pid: int, term: dict) -> None:
        for p in self.passes:
            if p["pid"] == int(pid):
                p["term"] = dict(term) if term is not None else None

    # One completed window; every walk it decides.
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
                p["done"] = True
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
                p["done"] = True
                done.append(row)
        return done

    # The walk decoded on the windows from LOOKBACK_W before its start to window k; None while it has not ended...
    def _decode(self, p, k: int, final: bool = False):
        a = max(0, p["lo"] - LOOKBACK_W)
        e = np.asarray(self.e[a:k + 1], float)
        assert float(np.max(np.abs(e.max(axis=1)))) == 0.0, \
            "the pooled emission is not max-normalised: the null reference would not be 0 on a prefix"
        r = night_track(e, np.asarray(self.ge[a:k + 1]), p["lo"] - a, self.st, self.cfg, self.transit, self.ne,
                        self.opts, p["term"])
        if r is None:
            return None
        horizon_w = int(round(MAX_WALK_S / STRIDE_S))
        ran_out = bool(r["timeout"] and r["hi"] == (k - a) and (k - a) < (p["lo"] - a) + horizon_w)
        if ran_out and not final:
            return None
        return {"pass_id": p["pid"], "final_line": r["final_line"], "live_exit_window": int(a + r["end_i"]),
                "live_decided_at_window": int(k), "live_press": p["press"]}



# One walk, starting at window lo of the emissions e (and the walking-gate energies ge): where it ends and...
def night_track(e, ge, lo: int, st, cfg, transit, ne, opts: dict, term: dict = None, draw: bool = False,
                max_advance: float = None, path_lag_extra: int = 0, prior_f: float = 0.0):
    n = len(e)
    if n - lo < 2:
        return None
    sp = Space(st, cfg)
    lT = flatten_chain_prior(transition_matrix2(st, cfg, transit, max_advance), st, float(opts["prior_flatten"]))
    lT_chains = chain_transitions(st, max_advance)
    ne.calibrate(e)
    e_stacked = stack2(e, ge, ne, sp)
    hi_lim = int(min(n - 1, len(e_stacked) - 1, lo + int(round(MAX_WALK_S / STRIDE_S))))
    if hi_lim <= lo:
        return None
    st_lo = entry_start(e_stacked, st, sp, lo)
    s_arr = np.asarray(st.s_of, float)
    for nm in st.names:
        aa, bb = st.slice_of[nm]
        far = aa + np.flatnonzero((s_arr[aa:bb] - s_arr[aa]) > ENTRY_WINDOW_M + 1e-9)
        if len(far):
            st_lo[far] = NEG_BIG

    d = np.asarray(e_stacked[lo], float) + np.asarray(st_lo, float)
    end_i, timeout = hi_lim, True
    for k in range(1, hi_lim - lo + 1):
        d = np.asarray(e_stacked[lo + k], float) + (d[:, None] + lT).max(axis=0)
        if int(np.nanargmax(np.where(np.isfinite(d), d, -np.inf))) >= st.n_states:
            end_i, timeout = lo + k, False
            break

    tot = chain_totals(e, st, slice(lo, end_i + 1), lT_chains, opts["chain_logprior"])
    if term:
        tot = {k: v + term.get(k, 0.0) for k, v in tot.items()}
    out = {"final_line": pick_line(tot, st), "timeout": bool(timeout), "end_i": int(end_i), "hi": int(hi_lim)}
    if draw:
        out["lock_line"] = lock_line(e_stacked, lT, st_lo, st, lo, hi_lim)
        lT_draw = flatten_chain_prior(lT_chains, st, prior_f)
        out["paths"] = {nm: locked_chain_path(e, lT_draw, st, lo, hi_lim, path_lag_extra, nm, st_lo) for nm in st.names}
    return out


# The start distribution at the press: each line point's emission at the walk's first window, relative to...
def entry_start(e_stacked, st, sp, lo: int) -> np.ndarray:
    v = np.full(sp.N, NEG_BIG)
    v[:st.n_states] = e_stacked[lo, :st.n_states]
    m = float(np.max(v[:st.n_states]))
    if np.isfinite(m):
        v[:st.n_states] -= m
    return v


# Each line's total log-likelihood over the windows, by Viterbi within the line, plus its prior.
def chain_totals(e_chain, st, seq_range, lT_chains, chain_logprior=None) -> dict:
    out = {}
    for nm in st.names:
        a, b = st.slice_of[nm]
        sub_e = e_chain[seq_range, a:b]
        s = viterbi(sub_e, lT_chains[a:b, a:b])
        tot = float(sub_e[np.arange(len(s)), s].sum())
        if chain_logprior:
            tot += float(chain_logprior.get(nm, 0.0))
        out[nm] = tot
    return out


# The committed line: the best family of lines first (the log-sum of its lines), then its best line.
def pick_line(totals: dict, st) -> str:
    if not totals:
        return ""
    fam = {}
    for nm, v in totals.items():
        fam.setdefault(FAMILY_OF.get(nm.split("_")[0], "other"), []).append(v)

    # Function lse.
    def lse(xs):
        m = max(xs)
        return m + float(np.log(sum(np.exp(x - m) for x in xs)))
    best_fam = max(fam, key=lambda f: lse(fam[f]))
    members = {nm: v for nm, v in totals.items() if FAMILY_OF.get(nm.split("_")[0], "other") == best_fam}
    return max(members, key=members.get)


# Each line's step prior mixed towards uniform (over the steps it allows) by a fraction f.
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



# The line the display locks to: the line of the decoded state LOCK_STEP windows into the walk (a decode...
def lock_line(e_stacked, lT, st_lo, st, lo: int, hi: int) -> str:
    last_on, k = None, None
    for i in range(min(LOCK_STEP, hi - lo) + 1):
        k = int(viterbi(e_stacked[lo:lo + i + 1], lT, log_start=st_lo)[i])
        if k < st.n_states:
            last_on = k
        elif last_on is not None:
            k = last_on
    if k < st.n_states:
        return chain_of(st, k)
    v = np.asarray(st_lo, float)[:st.n_states] + np.asarray(e_stacked[lo], float)[:st.n_states]
    if np.isfinite(v).any():
        return chain_of(st, int(np.nanargmax(np.where(np.isfinite(v), v, -np.inf))))
    return st.names[0]


# The drawn path along ONE line, as states: at each step, the state a Viterbi restricted to the line gives...
def locked_chain_path(e, lT_chains, st, lo: int, hi: int, lag_w: int, chain: str, log_start) -> list:
    a, b = st.slice_of[chain]
    sub_T = lT_chains[a:b, a:b]
    e_sub = np.asarray(e)[:, a:b]
    ls = np.asarray(log_start, float)[a:b].copy()
    ls = ls - (float(np.max(ls[np.isfinite(ls)])) if np.isfinite(ls).any() else 0.0)
    out = []
    for i in range(hi - lo + 1):
        s_ = viterbi(e_sub[lo:min(hi, lo + i + lag_w) + 1], sub_T, log_start=ls)
        out.append(int(a + s_[i]))
    return out


# Function chain of.
def chain_of(st, state_idx: int) -> str:
    for nm in st.names:
        a, b = st.slice_of[nm]
        if a <= state_idx < b:
            return nm
    return ""



# The decoder's settings (pieces.pkl holds the shipped one).
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


# The states' indices: the line points, then one STILL state per place (off the lines, or the end of each...
class Space:

    # Sets up the object.
    def __init__(self, st, cfg: Config):
        self.st, self.cfg = st, cfg
        self.S = st.n_states
        self.n_lines = len(st.names)
        self.P = self.n_lines + 1
        self.still0 = self.S
        self.transit0 = self.S + self.P
        self.N = self.S + self.P + self.P * (cfg.clock_max + 1)

    # Function still.
    def still(self, p: int = 0) -> int:
        return self.still0 + p

    # Function transit.
    def transit(self, p: int, k: int) -> int:
        return self.transit0 + p * (self.cfg.clock_max + 1) + min(k, self.cfg.clock_max)


_LT_CACHE: dict = {}


# The whole log transition matrix (cached; the speed cap is part of the key): each line's step prior, the...
def transition_matrix2(st, cfg: Config, transit_min_windows: dict = None, max_advance: float = None) -> np.ndarray:
    key = (id(st), asdict(cfg).__repr__(), id(transit_min_windows), max_advance)
    if key in _LT_CACHE:
        return _LT_CACHE[key]
    sp = Space(st, cfg)
    out = np.full((sp.N, sp.N), NEG, dtype=float)
    for nm in st.names:
        i0, i1 = st.slice_of[nm]
        out[i0:i1, i0:i1] = along_log_score(st.s_of[i0:i1], cfg.sd_scale, max_advance)

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
    log_abort = -float(cfg.abort_cost)

    # Function min w.
    def min_w(p: int, q_name: str) -> int:
        if p == 0 or not transit_min_windows:
            return 0
        return int(transit_min_windows.get(f"{st.names[p - 1]}->{q_name}", {}).get("min_windows", 0))

    K = cfg.clock_max
    for qi, nm in enumerate(st.names):
        i0, i1 = st.slice_of[nm]
        p = qi + 1
        for i in range(max(i0, i1 - k_exit), i1):
            out[i, sp.still(p)] = log_exit
            out[i, sp.transit(p, 0)] = log_exit
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
                s_rel = st.s_of[i0:i1] - st.s_of[i0]
                for j in range(i1 - i0):
                    unexplained = s_rel[j] / v_step
                    if s_rel[j] <= v_step * (k + 1) + 1e-9 and k >= owed + int(np.floor(unexplained)):
                        out[t_, i0 + j] = entry_nm - cfg.lam * unexplained
    _LT_CACHE[key] = out
    return out


# Each line's step prior on its own (the committed line's and the drawn path's), NEG between lines.
def chain_transitions(st, max_advance: float = None) -> np.ndarray:
    out = np.full((st.n_states, st.n_states), NEG, dtype=float)
    for nm in st.names:
        i0, i1 = st.slice_of[nm]
        out[i0:i1, i0:i1] = along_log_score(st.s_of[i0:i1], 1.0, max_advance)
    return out


# The unnormalised log score of every step along one line: a normal on the step's length about V_MEAN * DT...
def along_log_score(s_vals: np.ndarray, sd_scale: float = 1.0, max_advance: float = None) -> np.ndarray:
    s = np.asarray(s_vals, float)
    d = s[None, :] - s[:, None]
    sd = max(V_SD * DT * sd_scale, 1e-3)
    out = -0.5 * ((d - V_MEAN * DT) / sd) ** 2
    out = np.where(d < -1e-9, NEG, out)
    if max_advance is not None:
        out = np.where(d > float(max_advance) + 1e-9, NEG, out)
    return out


# (T, N) emissions: the line points' columns, then the STILL and TRANSIT columns from the null level and the...
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
    h = max(1, int(cfg.veto_hysteresis))
    stat = g < theta
    forbid = stat.copy()
    for d in range(1, h):
        shifted = np.zeros_like(stat)
        shifted[d:] = stat[:-d]
        forbid &= shifted
    out[forbid, :sp.S] = NEG
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
                 motion_theta: float = MOTION_THETA):
        self.quantile = float(np.clip(quantile, 0.01, 0.999))
        self.offset = float(offset)
        self.gate_weight = float(gate_weight)
        self.motion_theta = float(motion_theta)
        self._ref = None

    # The reference: this recording's own peaks.
    def calibrate(self, path_emission: np.ndarray) -> "AdaptiveNullEmission":
        self._ref = float(np.quantile(np.asarray(path_emission).max(1), self.quantile))
        return self

    # Calls the object.
    def __call__(self, gate_energy: np.ndarray) -> np.ndarray:
        if self._ref is None:
            raise RuntimeError("calibrate() must be called on the recording before decoding it")
        still = (np.asarray(gate_energy, float) < self.motion_theta).astype(float)
        return self._ref + self.offset + self.gate_weight * still



# The best state sequence over the whole run of windows.
def viterbi(log_emis: np.ndarray, log_T: np.ndarray, log_start: np.ndarray = None) -> np.ndarray:
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


# The coordinate of each decoded state (the room centre off the lines).
def decoded_xy(seq: np.ndarray, states, null_xy=(2.5, 2.5)) -> np.ndarray:
    out = np.tile(np.asarray(null_xy, float), (len(seq), 1))
    on = seq < states.n_states
    out[on] = states.xy[seq[on]]
    return out
