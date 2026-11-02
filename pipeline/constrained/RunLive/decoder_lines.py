# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The decoder: one chain per line plus a not-on-a-line state, a model of how fast people walk along a line...

from __future__ import annotations

from typing import Optional

import numpy as np

from pipeline.constrained.RunLive.shared_settings import DT, V_MEAN, V_SD

MAX_ADVANCE_M = None

NEG = -1e18




# The UNNORMALISED log score of every step along one chain.
def along_log_score(s_vals: np.ndarray, kind: str = "tight", sd_scale: float = 1.0,
                    broad_sd: float = 1.5) -> np.ndarray:
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
        if MAX_ADVANCE_M is not None:
            out = np.where(d > float(MAX_ADVANCE_M) + 1e-9, NEG, out)
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
                      with_null: bool = True, normalise_along: bool = False) -> np.ndarray:
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
            blk = along_log_score(states.s_of[i0:i1], kind, sd_scale, broad_sd)
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
