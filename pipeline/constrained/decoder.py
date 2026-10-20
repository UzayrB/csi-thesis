# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The decoder: twelve path chains, one null state, and the motion model along a path.

from __future__ import annotations

from typing import Optional

import numpy as np

from pipeline.constrained.common import DT, V_MEAN, V_SD

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


# Causal forward recursion that commits window t - lag once window t has arrived.
def fixed_lag_viterbi(log_emis: np.ndarray, log_T: np.ndarray, lag: int,
                      log_start: Optional[np.ndarray] = None) -> np.ndarray:
    Tn, S = log_emis.shape
    lag = max(0, int(lag))
    dp = np.full((Tn, S), NEG)
    back = np.zeros((Tn, S), dtype=np.int32)
    dp[0] = log_emis[0] + (0.0 if log_start is None else log_start)
    out = np.full(Tn, -1, dtype=np.int32)
    for t in range(Tn):
        if t > 0:
            m = dp[t - 1][:, None] + log_T
            back[t] = m.argmax(0)
            dp[t] = m.max(0) + log_emis[t]
        commit = t - lag
        if commit >= 0:
            j = int(dp[t].argmax())
            for u in range(t, commit, -1):
                j = int(back[u, j])
            out[commit] = j
            keep = dp[commit, j]
            dp[commit, :] = NEG
            dp[commit, j] = keep
            for u in range(commit + 1, t + 1):
                m = dp[u - 1][:, None] + log_T
                back[u] = m.argmax(0)
                dp[u] = m.max(0) + log_emis[u]
    if lag:
        j = int(dp[-1].argmax())
        for u in range(Tn - 1, max(-1, Tn - 1 - lag), -1):
            if out[u] < 0:
                out[u] = j
            j = int(back[u, j]) if u > 0 else j
    return out


# No motion model at all: the best state for each window independently.
def argmax_decode(log_emis: np.ndarray) -> np.ndarray:
    return log_emis.argmax(1).astype(np.int32)




# Decode one pass along ONE path.
def decode_pass_on_path(log_emis_path: np.ndarray, s_vals: np.ndarray, kind: str = "tight",
                        sd_scale: float = 1.0, broad_sd: float = 1.5,
                        normalise: bool = False) -> tuple:
    Tt = len(log_emis_path)
    logT = (np.log(np.clip(along_transition(s_vals, kind, sd_scale, broad_sd), 1e-300, None))
            if normalise else along_log_score(s_vals, kind, sd_scale, broad_sd))
    dp = np.full((Tt, len(s_vals)), NEG)
    back = np.zeros((Tt, len(s_vals)), dtype=np.int32)
    dp[0] = log_emis_path[0]
    for t in range(1, Tt):
        m = dp[t - 1][:, None] + logT
        back[t] = m.argmax(0)
        dp[t] = m.max(0) + log_emis_path[t]
    end = int(dp[-1].argmax())
    seq = np.zeros(Tt, dtype=np.int32)
    seq[-1] = end
    for t in range(Tt - 1, 0, -1):
        seq[t - 1] = back[t, seq[t]]
    return seq, float(dp[-1, end])


# Decode one pass with the path identity FREE: score all twelve and keep the best.
def decode_pass_free(log_emis: np.ndarray, states, kind: str = "tight", sd_scale: float = 1.0,
                     broad_sd: float = 1.5, path_log_prior: Optional[dict] = None,
                     normalise: bool = False) -> tuple:
    best = (None, -np.inf, None)
    scores = {}
    for nm in states.names:
        i0, i1 = states.slice_of[nm]
        seq, sc = decode_pass_on_path(log_emis[:, i0:i1], states.s_of[i0:i1], kind, sd_scale,
                                      broad_sd, normalise)
        if path_log_prior:
            sc += float(path_log_prior.get(nm, 0.0))
        scores[nm] = sc
        if sc > best[1]:
            best = (nm, sc, seq)
    nm, sc, seq = best
    i0, _i1 = states.slice_of[nm]
    return nm, states.xy[i0 + seq], sc, scores


# ORACLE.
def decode_pass_forced(log_emis: np.ndarray, states, path_name: str, kind: str = "tight",
                       sd_scale: float = 1.0, broad_sd: float = 1.5,
                       normalise: bool = False) -> np.ndarray:
    i0, i1 = states.slice_of[path_name]
    seq, _sc = decode_pass_on_path(log_emis[:, i0:i1], states.s_of[i0:i1], kind, sd_scale,
                                   broad_sd, normalise)
    return states.xy[i0 + seq]




# THE CONTROL FOR REQUIREMENT ONE.
def dead_reckon(n_windows: int, states, path_name: str, v: float = V_MEAN, dt: float = DT,
                start_s: float = 0.0) -> np.ndarray:
    i0, i1 = states.slice_of[path_name]
    s = states.s_of[i0:i1]
    want = start_s + v * dt * np.arange(n_windows)
    idx = np.abs(s[None, :] - np.clip(want, s[0], s[-1])[:, None]).argmin(1)
    return states.xy[i0 + idx]




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


# Contiguous runs of the decode as (kind, path_name, first, last).
def segments(seq: np.ndarray, states) -> list:
    names = decoded_paths(seq, states)
    out, i = [], 0
    while i < len(seq):
        j = i
        while j + 1 < len(seq) and names[j + 1] == names[i]:
            j += 1
        out.append(("null" if names[i] == "" else "path", str(names[i]), i, j))
        i = j + 1
    return out
