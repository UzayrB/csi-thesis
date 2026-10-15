"""The decoder: twelve path chains, one null state, and the motion model along a path.

THE STATE SPACE. State ``i`` for ``i < n_states`` is a point on one of the twelve taped lines,
sampled every 0.25 m. State ``n_states`` is NULL, meaning the person is not on a line. A pass is
entered only at a chain's first state and left only near its last, so the decoder cannot appear in
the middle of a line or vanish from it.

THE MOTION MODEL ALONG A PATH IS UNDER SUSPICION and that is why it is a parameter here rather than
a constant. The frozen prior is a Gaussian on the step in arc length with mean 1.298 m and standard
deviation 0.123 m per one-second window. That standard deviation is the between-pass spread of MEAN
walking speed, not the within-pass variation of a single step, so used as a per-window transition it
demands almost exactly 1.298 m every second: once the line and the starting offset are fixed the
whole trajectory is determined to within about a quarter of a metre without the radio contributing
anything. Stage 1 measures that, stage 2 widens it, and the rung the batch quotes is the WEAKEST
prior that still beats dead reckoning.

    tight             the frozen prior, N(1.298, 0.123), forward only
    wide k            N(1.298, k x 0.123), forward only, for k in 3, 5, 10
    broad             N(0, 1.5), forward AND backward: the mean advance removed entirely
    forward_uniform   any forward step, uniformly: no speed assumption at all
    none              no motion model; handled at decode time as a per-window argmax

EXIT FROM A PATH. The brief's rule is that a path is left only at its end, and that is the default.
It has a failure mode worth measuring rather than assuming away: under a weak prior the decoder may
not reach the last state before the person leaves, and would then be stuck on the line for ever. So
the exit zone is the last ``exit_from_last_k`` states, with k = 1 being the brief's rule, and stage 4
sweeps it.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from pipeline.constrained.common import DT, V_MEAN, V_SD

#: optional hard ceiling on one window's advance, in metres of arc. None = the shipped kernel.
MAX_ADVANCE_M = None

NEG = -1e18


# --------------------------------------------------------------------------- along a path


def along_log_score(s_vals: np.ndarray, kind: str = "tight", sd_scale: float = 1.0,
                    broad_sd: float = 1.5) -> np.ndarray:
    """The UNNORMALISED log score of every step along one chain. The pass-level decoder's transition.

    WHY UNNORMALISED, measured rather than assumed. Making each row sum to one is the textbook
    thing to do and it costs nineteen points of path accuracy here: 31.0 percent against 50.0 over
    the same seven cross-day pairings, where the figure on record is 56.3. Normalising divides each
    row by its own sum, and a state near the end of a line has fewer forward steps available, so its
    sum is smaller and its surviving transitions are inflated. That rewards being near the end of a
    line for a reason that has nothing to do with the radio, and it makes a 5 m line and a 7.071 m
    line score on different scales, which is fatal when the whole decision is which of the twelve a
    person walked.

    The raw score is the log likelihood of the DISPLACEMENT under the speed model, which is the
    quantity that is actually comparable across lines of different lengths.
    """
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
        # MAX_ADVANCE_M is an optional HARD ceiling on how far the chain may advance in one
        # window, in metres of arc. None leaves the kernel bit-identical to the shipped model. It
        # exists so a physical ceiling on walking speed can be stated as a ceiling rather than
        # implied by how narrow the spread happens to be: at the shipped spread a 1.5 m step
        # scores -95.7 and is impossible, which is a cap nobody chose.
        if MAX_ADVANCE_M is not None:
            out = np.where(d > float(MAX_ADVANCE_M) + 1e-9, NEG, out)
    return out


def along_transition(s_vals: np.ndarray, kind: str = "tight", sd_scale: float = 1.0,
                     broad_sd: float = 1.5) -> np.ndarray:
    """Row-stochastic transition over one chain's arc-length states.

    Returns ``(n, n)`` where entry (i, j) is P(the person is at s_j next, given s_i now). Used by
    the UNIFIED decoder, where the null state has to compete with the twelve chains and that
    comparison is only well posed between probabilities. The pass-level decoder uses
    :func:`along_log_score` instead, for the reason given there.
    """
    s = np.asarray(s_vals, float)
    d = s[None, :] - s[:, None]                      # (n, n) step in arc length, forward positive
    if kind == "forward_uniform":
        W = (d >= -1e-9).astype(float)
    elif kind == "broad":
        W = np.exp(-0.5 * (d / max(broad_sd, 1e-6)) ** 2)
    else:
        sd = max(V_SD * DT * sd_scale, 1e-3)
        W = np.exp(-0.5 * ((d - V_MEAN * DT) / sd) ** 2)
        W[d < -1e-9] = 0.0                            # no going backwards along a line
    rs = W.sum(1, keepdims=True)
    # A row that underflows to zero happens on the last states under a tight prior, where every
    # forward step of 1.298 m is off the end of the line. Staying put is the only thing left.
    dead = (rs[:, 0] <= 1e-300)
    if dead.any():
        W[dead] = 0.0
        W[dead, np.flatnonzero(dead)] = 1.0
        rs = W.sum(1, keepdims=True)
    return W / rs


def transition_matrix(states, kind: str = "tight", sd_scale: float = 1.0, broad_sd: float = 1.5,
                      null_self: float = 0.9, exit_p: float = 0.5,
                      exit_from_last_k: int = 1, entry_prior: Optional[np.ndarray] = None,
                      with_null: bool = True, normalise_along: bool = False) -> np.ndarray:
    """The whole transition matrix, path chains plus the null state, in LOG space.

    ``normalise_along`` defaults to False for the same reason the pass-level decoder does not
    normalise: making each chain's rows sum to one inflates transitions out of states near a line's
    end and puts lines of different lengths on different scales, and it costs nineteen points of
    path accuracy. Measured with the unified decoder too: normalised, it found the passes but picked
    the right line on 15 percent of them.

    WHY MIXING RAW SCORES WITH REAL PROBABILITIES IS STILL WELL POSED. The along-path entries are
    log likelihoods of a displacement; the entry, exit and null-self entries are log probabilities.
    They are on different scales, but every one of the latter is a CONSTANT: entering any chain costs
    the same, leaving any chain costs the same, and staying in null costs the same per window. A
    constant offset between the null branch and the path branch is exactly what the fitted null level
    absorbs, and that level is fitted through the decoder itself on the training side. So the only
    quantity that has to be comparable across lines is the along-path score, and raw is what makes it
    comparable.

    ``entry_prior`` is an optional distribution over the twelve paths for the null-to-path
    transition, which is where a pass classifier's posterior enters. Uniform when omitted.
    """
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


# --------------------------------------------------------------------------- decoding


def viterbi(log_emis: np.ndarray, log_T: np.ndarray,
            log_start: Optional[np.ndarray] = None) -> np.ndarray:
    """Offline Viterbi over the whole sequence. Uses every window, so it cannot run live."""
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


def fixed_lag_viterbi(log_emis: np.ndarray, log_T: np.ndarray, lag: int,
                      log_start: Optional[np.ndarray] = None) -> np.ndarray:
    """Causal forward recursion that commits window ``t - lag`` once window ``t`` has arrived.

    Forward messages only, no backward sweep. The state for a window is fixed using that window and
    the ``lag`` windows after it, and nothing later ever revises it, which is exactly what a live
    system can do at the cost of ``lag`` seconds of delay. With ``lag = 0`` it is the greedy filter;
    with ``lag >= T`` it reduces to :func:`viterbi`, and the unit tests assert both.

    A COMMITMENT IS BINDING, AND THAT IS NOT A DETAIL. The obvious implementation takes the best
    path at ``t``, walks back ``lag`` steps and emits that state, then does the same again at
    ``t + 1``. Those two emissions come from DIFFERENT paths, so the sequence it prints is a run of
    independent decisions and not a trajectory at all: measured on this data it emitted 139 to 237
    steps per recording that the transition matrix itself scores as impossible, jumped between
    parallel lines 21 to 64 times, entered a line partway down it about half the time, and finished
    only three to ten of the ninety-odd lines it started. The state space forbids every one of
    those moves; nothing was enforcing it at the point where states are actually emitted.

    So once a state is committed the belief is collapsed onto it and the forward messages are
    recomputed from there. Every later path must pass through what was already emitted, which makes
    the output a connected walk through the state space by construction. The cost is that a bad
    commitment can no longer be escaped, which is the honest meaning of having committed: with a
    lag of three the decoder gets three windows to change its mind and not one window more.
    """
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
            for u in range(t, commit, -1):           # walk back exactly lag steps
                j = int(back[u, j])
            out[commit] = j
            # bind it: everything after this window must come from this state
            keep = dp[commit, j]
            dp[commit, :] = NEG
            dp[commit, j] = keep
            for u in range(commit + 1, t + 1):
                m = dp[u - 1][:, None] + log_T
                back[u] = m.argmax(0)
                dp[u] = m.max(0) + log_emis[u]
    # the tail: the last ``lag`` windows never got their full context, so they are committed with
    # whatever context they did get rather than left undecided
    if lag:
        j = int(dp[-1].argmax())
        for u in range(Tn - 1, max(-1, Tn - 1 - lag), -1):
            if out[u] < 0:
                out[u] = j
            j = int(back[u, j]) if u > 0 else j
    return out


def argmax_decode(log_emis: np.ndarray) -> np.ndarray:
    """No motion model at all: the best state for each window independently."""
    return log_emis.argmax(1).astype(np.int32)


# --------------------------------------------------------------------------- pass-level decoding


def decode_pass_on_path(log_emis_path: np.ndarray, s_vals: np.ndarray, kind: str = "tight",
                        sd_scale: float = 1.0, broad_sd: float = 1.5,
                        normalise: bool = False) -> tuple:
    """Decode one pass along ONE path. Returns the state indices and the total log score.

    This is the pass-level decoder stages 1 to 3 use, where the pass boundaries are given and the
    only question is which line and where along it. ``normalise`` defaults to False because making
    the rows stochastic costs nineteen points of path accuracy; see :func:`along_log_score`.
    """
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


def decode_pass_free(log_emis: np.ndarray, states, kind: str = "tight", sd_scale: float = 1.0,
                     broad_sd: float = 1.5, path_log_prior: Optional[dict] = None,
                     normalise: bool = False) -> tuple:
    """Decode one pass with the path identity FREE: score all twelve and keep the best.

    ``path_log_prior`` optionally adds a per-path log prior, which is how a pass classifier's
    posterior enters. Returns (path_name, xy per window, total score, per-path scores).
    """
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


def decode_pass_forced(log_emis: np.ndarray, states, path_name: str, kind: str = "tight",
                       sd_scale: float = 1.0, broad_sd: float = 1.5,
                       normalise: bool = False) -> np.ndarray:
    """ORACLE. Decode along the TRUE path, which the decoder is told. Never an accuracy claim."""
    i0, i1 = states.slice_of[path_name]
    seq, _sc = decode_pass_on_path(log_emis[:, i0:i1], states.s_of[i0:i1], kind, sd_scale,
                                   broad_sd, normalise)
    return states.xy[i0 + seq]


# --------------------------------------------------------------------------- dead reckoning


def dead_reckon(n_windows: int, states, path_name: str, v: float = V_MEAN, dt: float = DT,
                start_s: float = 0.0) -> np.ndarray:
    """THE CONTROL FOR REQUIREMENT ONE. Walk the path at a constant speed, reading no radio at all.

    The person is placed at arc length ``s = start_s + v t`` on the given path. If a decoder that
    reads the CSI cannot beat this, then along-path position is coming from the pace prior and not
    from the radio, and the tracker is a path classifier with a motion model attached.
    """
    i0, i1 = states.slice_of[path_name]
    s = states.s_of[i0:i1]
    want = start_s + v * dt * np.arange(n_windows)
    idx = np.abs(s[None, :] - np.clip(want, s[0], s[-1])[:, None]).argmin(1)
    return states.xy[i0 + idx]


# --------------------------------------------------------------------------- reading a decode


def decoded_paths(seq: np.ndarray, states) -> np.ndarray:
    """The path name for each decoded state, or '' where the decoder was in the null state."""
    out = np.empty(len(seq), dtype="U10")
    out[:] = ""
    on = seq < states.n_states
    out[on] = states.path_of[seq[on]]
    return out


def decoded_xy(seq: np.ndarray, states, null_xy=(2.5, 2.5)) -> np.ndarray:
    """The coordinate for each decoded state. The null state sits at the room centre.

    Resting at the centre is a deliberate display choice, not an estimate: the decoder is saying it
    does not know where the person is, and the centre is the point that claims least.
    """
    out = np.tile(np.asarray(null_xy, float), (len(seq), 1))
    on = seq < states.n_states
    out[on] = states.xy[seq[on]]
    return out


def segments(seq: np.ndarray, states) -> list:
    """Contiguous runs of the decode as (kind, path_name, first, last).

    ``kind`` is 'path' or 'null'. This is what the segmentation metrics and the render's state label
    are both built from.
    """
    names = decoded_paths(seq, states)
    out, i = [], 0
    while i < len(seq):
        j = i
        while j + 1 < len(seq) and names[j + 1] == names[i]:
            j += 1
        out.append(("null" if names[i] == "" else "path", str(names[i]), i, j))
        i = j + 1
    return out
