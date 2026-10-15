"""The rebuilt decoder as a stream: one window in, a committed state and a provisional state out.
Brief: reports/decoder_rebuild_prompt_2026-09-17.md, STAGE 3.

TWO TRACKS FROM ONE DECODER. The COMMITTED track is the fixed-lag decoder with binding commitments
at display lag L: window t is fixed once window t + L has arrived, the belief is collapsed onto it,
and it is never revised, so the committed track is a connected walk. The PROVISIONAL track is the
argmax of the UN-collapsed forward belief at the current window, shown to the viewer immediately
and allowed to be wrong. When the committed decision for a window differs from what was
provisionally shown, the display catches up, and that is counted as a revision with its distance.

:class:`LiveDecoder2` reproduces :func:`pipeline.constrained.decoder.fixed_lag_viterbi` exactly,
window by window, which the tests assert, so the numbers measured in batch are the numbers the
stream produces.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from pipeline.constrained.decoder import NEG, decoded_paths, decoded_xy
from pipeline.constrained.decoder2 import Config, Space, stack2, transition_matrix2


def provisional_greedy(e: np.ndarray, log_T: np.ndarray) -> np.ndarray:
    """The provisional track in batch: argmax of the un-collapsed forward belief at each window."""
    Tn, N = e.shape
    out = np.zeros(Tn, dtype=np.int32)
    dp = e[0].copy()
    out[0] = int(dp.argmax())
    for t in range(1, Tn):
        dp = (dp[:, None] + log_T).max(0) + e[t]
        dp -= dp.max()
        out[t] = int(dp.argmax())
    return out


def revisions_between(committed: np.ndarray, provisional: np.ndarray, st,
                     hysteresis_m: float = 0.0) -> list:
    """Windows where the committed decision disagrees with what was provisionally displayed.

    DEFINITION, stated because the figure was mislabelled once. A revision is counted when the
    committed LINE differs from the displayed line, or when both are on the same line and the
    committed state is more than one state (0.25 m) further along than the one displayed. It is
    counted PER WINDOW; the per-pass figure that metrics.py reports sums these over the pass span
    plus eight windows either side, about twenty windows, NOT over the four walk windows of the
    pass itself.

    ``hysteresis_m`` is the display guard of amendment D4(a): the dot is not redrawn unless the
    committed position differs from the displayed one by more than this. Measured without it, the
    median displacement was 2.30 m on a 5 x 5 m room, 8.75 times per pass, which is the dot jumping
    across the room rather than catching up, and requirement V4 is not met however good the
    accuracy is.
    """
    c = np.asarray(committed, int); p = np.asarray(provisional, int)
    cn, pn = decoded_paths(c, st), decoded_paths(p, st)
    cxy, pxy = decoded_xy(c, st), decoded_xy(p, st)
    out = []
    for t in range(len(c)):
        d = float(np.linalg.norm(cxy[t] - pxy[t]))
        if d <= hysteresis_m:
            continue
        if cn[t] != pn[t]:
            kind = "line"
        elif cn[t] and abs(int(c[t]) - int(p[t])) > 1:
            kind = "arc"
        else:
            continue
        out.append({"window": int(t), "kind": kind, "distance_m": d})
    return out


class LiveDecoder2:
    """Streaming fixed-lag decoder with binding commitments, plus the provisional belief.

    ``step(e_row, g)`` takes one window's path emissions and gate energy and returns
    ``(committed_state_for_window_t_minus_lag or None, provisional_state_for_window_t)``.
    """

    def __init__(self, st, cfg: Config, ne, lag: int, transit_min_windows: Optional[dict] = None):
        self.st, self.cfg, self.ne, self.lag = st, cfg, ne, int(lag)
        self.sp = Space(st, cfg)
        self.lT = transition_matrix2(st, cfg, transit_min_windows)
        self.reset()

    def reset(self):
        self.t = -1
        # buffer of forward messages from the last COMMITTED window (collapsed onto its state, kept
        # because the next window transitions from it) through the newest window
        self.E = []
        self.dp = []
        self.back = []
        self.head_committed = False
        self.dp_free = None      # un-collapsed forward belief for the provisional track
        self.committed = []
        self.provisional = []

    def _emission(self, e_row: np.ndarray, g: float) -> np.ndarray:
        return stack2(np.asarray(e_row, float)[None, :], np.array([g], float), self.ne, self.sp)[0]

    def step(self, e_row: np.ndarray, g: float):
        """Returns ``(committed state for window t - lag or None, provisional state for t)``."""
        self.t += 1
        e = self._emission(e_row, g)
        # provisional: un-collapsed forward belief
        if self.dp_free is None:
            self.dp_free = e.copy()
        else:
            self.dp_free = (self.dp_free[:, None] + self.lT).max(0) + e
            self.dp_free -= self.dp_free.max()
        prov = int(self.dp_free.argmax())
        self.provisional.append(prov)
        # committed: exactly the batch fixed-lag recursion, one window at a time
        self.E.append(e)
        if not self.dp:
            self.dp.append(e.copy()); self.back.append(None)
        else:
            m = self.dp[-1][:, None] + self.lT
            self.back.append(m.argmax(0).astype(np.int32))
            self.dp.append(m.max(0) + e)
        commit = None
        c = 1 if self.head_committed else 0          # index of the window to commit next
        if len(self.dp) - 1 - c >= self.lag:
            j = int(self.dp[-1].argmax())
            for u in range(len(self.dp) - 1, c, -1):
                j = int(self.back[u][j])
            keep = self.dp[c][j]
            self.dp[c][:] = NEG
            self.dp[c][j] = keep
            for u in range(c + 1, len(self.dp)):
                m = self.dp[u - 1][:, None] + self.lT
                self.back[u] = m.argmax(0).astype(np.int32)
                self.dp[u] = m.max(0) + self.E[u]
            commit = j
            self.committed.append(j)
            if self.head_committed:
                self.dp.pop(0); self.back.pop(0); self.E.pop(0)
                self.back[0] = None
            self.head_committed = True
        return commit, prov

    def flush(self) -> list:
        """Commit the tail (the last ``lag`` windows) with whatever context they have."""
        c = 1 if self.head_committed else 0
        if len(self.dp) - 1 < c:
            return []
        j = int(self.dp[-1].argmax())
        chain = [j]
        for u in range(len(self.dp) - 1, c, -1):
            j = int(self.back[u][j])
            chain.append(j)
        out = list(reversed(chain))
        self.committed.extend(out)
        self.dp, self.back, self.E = [], [], []
        self.head_committed = False
        return out

    def committed_xy(self, state: int):
        return tuple(float(v) for v in decoded_xy(np.array([state]), self.st)[0])
