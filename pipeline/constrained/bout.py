"""The bout decoder: one decision per walking bout, not per window.
Brief: reports/decoder_rebuild_prompt_2026-09-17.md, STAGE 4.

WHY THIS EXISTS. The motion gate separates walking from standing with 100 percent walking recall,
and a person who is walking is walking either a pass or a transit; there is nothing else. So the
gate delimits a BOUT, and the decoder's job inside a bout is a thirteen-way choice, twelve lines or
transit, rather than a fresh decision every second. Catch-up is free here: once the line is chosen
the arc length follows from the bout's own clock, so a decoder that commits three windows late
still knows exactly where along the line the person is now.

THE RISK IS THE GATE'S STANDING DETECTION, about 45 percent, which merges bouts: a pass, a pause
and a transit read as one. Stage 0 measured 65 merged bouts of 1110. So a bout may be split at up
to two internal points, chosen by likelihood, and a merged bout is decoded as line, transit, line
rather than forced into one hypothesis.

SCORING, AND WHY IT IS PRECOMPUTED. For a line L, a traversal starting at window ``o`` puts the
walker at arc length ``v (t - o)``, so its score is a fixed diagonal sum through the emission
matrix. Every start window's traversal score is computed once per recording, and a segment's score
for L is then a range maximum over those, plus the null level for the windows the traversal does
not cover. Without that the three-segment search rescanned the emissions for every candidate split
and took over two minutes on one recording; with it, a recording decodes in under a second.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from pipeline.constrained.common import DT, V_MEAN
from pipeline.constrained.decoder2 import MOTION_THETA

NEG = -1e18


@dataclass(frozen=True)
class BoutConfig:
    max_splits: int = 2
    min_cover: float = 0.6       #: a line hypothesis must traverse at least this fraction of it
    margin: float = 0.0          #: nats a line must hold over transit before the bout is committed
    geometry: bool = True        #: a line may not start before the transit from the last line ends
    min_bout: int = 2            #: bouts shorter than this are transit by definition


def bouts_of(gate_e: np.ndarray, theta: float = MOTION_THETA) -> list:
    """Contiguous runs of walking windows: ``(first, last)`` inclusive."""
    w = np.asarray(gate_e, float) >= theta
    out, i, n = [], 0, len(w)
    while i < n:
        if not w[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and w[j + 1]:
            j += 1
        out.append((int(i), int(j)))
        i = j + 1
    return out


def line_windows(st, name: str) -> int:
    """How many windows the model says a full traversal of this line takes."""
    i0, i1 = st.slice_of[name]
    return int(np.ceil((st.s_of[i1 - 1] - st.s_of[i0]) / (V_MEAN * DT) + 1e-9)) + 1


def traversal_states(st, name: str, n: int) -> np.ndarray:
    """The ``n`` states of a walker on ``name`` starting at its first state."""
    i0, i1 = st.slice_of[name]
    s_rel = st.s_of[i0:i1] - st.s_of[i0]
    want = np.clip(V_MEAN * DT * np.arange(n), 0, s_rel[-1])
    return i0 + np.clip(np.searchsorted(s_rel, want), 0, len(s_rel) - 1)


class BoutScorer:
    """Traversal scores for every line at every start window, computed once per recording."""

    def __init__(self, e_path: np.ndarray, null_level: np.ndarray, st, cfg: BoutConfig):
        self.st, self.cfg = st, cfg
        self.n = int(e_path.shape[0])
        self.e = e_path
        self.cumnull = np.concatenate([[0.0], np.cumsum(np.asarray(null_level, float))])
        self.need = {nm: line_windows(st, nm) for nm in st.names}
        self.states = {nm: traversal_states(st, nm, self.need[nm]) for nm in st.names}
        self.adj = {}      # adj[nm][o] = traversal score at o minus the null it displaces
        for nm in st.names:
            need, stt = self.need[nm], self.states[nm]
            if need > self.n:
                self.adj[nm] = np.full(0, NEG)
                continue
            m = self.n - need + 1
            per_k = np.empty((need, m))
            for k in range(need):
                per_k[k] = e_path[k:k + m, stt[k]]
            trav = per_k.sum(0)
            displaced = self.cumnull[need:need + m] - self.cumnull[0:m]
            self.adj[nm] = trav - displaced

    def null_range(self, a: int, b: int) -> float:
        return float(self.cumnull[b + 1] - self.cumnull[a])

    def score(self, a: int, b: int, nm: str):
        """(score, states, mask) for line ``nm`` over ``[a, b]``, or None if it cannot fit."""
        n_seg = b - a + 1
        need = self.need[nm]
        if n_seg >= need:
            lo, hi = a, b - need + 1
            if hi < lo or len(self.adj[nm]) == 0:
                return None
            band = self.adj[nm][lo:hi + 1]
            if not len(band):
                return None
            o = lo + int(np.argmax(band))
            sc = self.null_range(a, b) + float(band[o - lo])
            # states and mask are both SEGMENT aligned, so a caller can index them with one boolean
            mask = np.zeros(n_seg, bool)
            mask[o - a:o - a + need] = True
            stt = np.zeros(n_seg, dtype=np.int32)
            stt[o - a:o - a + need] = self.states[nm]
            return sc, stt, mask
        # the segment is shorter than a full traversal: allow it only if it covers enough
        if n_seg / need < self.cfg.min_cover:
            return None
        stt = np.asarray(self.states[nm][:n_seg], dtype=np.int32)
        sc = float(self.e[np.arange(a, b + 1), stt].sum())
        return sc, stt, np.ones(n_seg, bool)

    def best(self, a: int, b: int, allowed: Optional[set] = None):
        """The best hypothesis over ``[a, b]``: ``(name, score, states, mask)``; transit has None."""
        best = ("transit", self.null_range(a, b), None, None)
        for nm in self.st.names:
            if allowed is not None and nm not in allowed:
                continue
            r = self.score(a, b, nm)
            if r is not None and r[0] > best[1]:
                best = (nm, r[0], r[1], r[2])
        return best


def decode_bout(scorer: BoutScorer, a: int, b: int, cfg: BoutConfig,
                allowed: Optional[set] = None) -> dict:
    """Up to ``cfg.max_splits`` internal splits, by likelihood, over windows ``[a, b]``.

    A forward dynamic program: ``f[t][k]`` is the best score for windows ``[a, t)`` using ``k``
    segments, so the three-way case costs a few thousand range maxima rather than a rescan.
    """
    n = b - a + 1
    if n < cfg.min_bout:
        return {"segments": [(a, b, "transit", None, None)], "score": scorer.null_range(a, b),
                "n_segments": 1}
    K = max(1, int(cfg.max_splits) + 1)
    f = np.full((n + 1, K + 1), -np.inf)
    back = {}
    f[0, 0] = 0.0
    for t in range(1, n + 1):
        for k in range(1, K + 1):
            for s in range(0, t):
                if not np.isfinite(f[s, k - 1]):
                    continue
                nm, sc, stt, msk = scorer.best(a + s, a + t - 1, allowed)
                v = f[s, k - 1] + sc
                if v > f[t, k]:
                    f[t, k] = v
                    back[(t, k)] = (s, nm, stt, msk)
    k_best = int(np.argmax(f[n, 1:])) + 1
    segs, t, k = [], n, k_best
    while k > 0 and (t, k) in back:
        s, nm, stt, msk = back[(t, k)]
        segs.append((a + s, a + t - 1, nm, stt, msk))
        t, k = s, k - 1
    segs.reverse()
    return {"segments": segs, "score": float(f[n, k_best]), "n_segments": len(segs)}


def decode_recording_bouts(e_path: np.ndarray, gate_e: np.ndarray, null_level: np.ndarray, st,
                           cfg: BoutConfig, transit_min_windows: Optional[dict] = None,
                           lag: Optional[int] = None) -> dict:
    """Decode a whole recording bout by bout.

    ``lag`` None decodes each bout with its full evidence. An integer is the live form: the bout is
    re-decoded as it grows and window ``t`` is fixed once ``t + lag`` has arrived, so an early
    decision can still be corrected by the next ``lag`` windows but never after that.
    """
    n = len(e_path)
    seq = np.full(n, st.null, dtype=np.int32)
    names = np.empty(n, dtype="U10"); names[:] = ""
    scorer = BoutScorer(e_path, null_level, st, cfg)
    revisions, bout_rows = [], []
    last_line = None
    for (a, b) in bouts_of(gate_e):
        allowed = None
        if cfg.geometry and transit_min_windows and last_line:
            allowed = {nm for nm in st.names
                       if transit_min_windows.get(f"{last_line}->{nm}", {}).get("min_windows", 0) <= (b - a + 1)}
            if not allowed:
                allowed = set(st.names)
        if lag is None:
            dec = decode_bout(scorer, a, b, cfg, allowed)
            placed = dec["segments"]
        else:
            # LIVE. The bout is re-decoded as it grows and window t is written ONCE, when t + lag
            # has arrived. A revision is logged when the decode that commits a window disagrees with
            # what the previous decode would have shown there, which is the catch-up the viewer
            # sees. Writing every prefix decode's whole placement instead logged a revision on every
            # window of every bout, counting the decoder thinking rather than the display changing.
            from pipeline.constrained.decoder import decoded_xy as _dxy
            placed, shown = [], {}
            for t in range(a, b + 1):
                at = {}
                for (sa, _sb, nm, stt, msk) in decode_bout(scorer, a, t, cfg, allowed)["segments"]:
                    if nm == "transit" or stt is None or msk is None:
                        continue
                    for off in np.flatnonzero(msk):
                        at[sa + int(off)] = (nm, int(stt[off]))
                w = t - lag
                if w >= a:
                    cur, prev = at.get(w), shown.get(w)
                    if cur is not None:
                        nm, state = cur
                        placed.append((w, w, nm, np.array([state], np.int32), np.ones(1, bool), w))
                        if prev is not None and (prev[0] != nm or abs(prev[1] - state) > 1):
                            revisions.append({"window": int(w),
                                              "kind": "line" if prev[0] != nm else "arc",
                                              "distance_m": float(np.linalg.norm(
                                                  _dxy(np.array([state]), st)[0] - _dxy(np.array([prev[1]]), st)[0]))})
                        elif prev is None and state > st.slice_of[nm][0]:
                            revisions.append({"window": int(w), "kind": "entry",
                                              "distance_m": float(st.s_of[state] - st.s_of[st.slice_of[nm][0]])})
                shown.update(at)
            for w in range(max(a, b - lag + 1), b + 1):      # the tail, with what context it had
                cur = shown.get(w)
                if cur is not None:
                    placed.append((w, w, cur[0], np.array([cur[1]], np.int32), np.ones(1, bool), w))
        for row in placed:
            if len(row) == 6:
                sa, sb, nm, stt, msk, seg_start = row
            else:
                sa, sb, nm, stt, msk = row
                seg_start = sa
            if nm == "transit" or stt is None or msk is None:
                continue
            idx_all = np.arange(seg_start, seg_start + len(msk))
            sel = msk & (idx_all >= sa) & (idx_all <= sb)
            if not sel.any():
                continue
            idx = idx_all[sel]
            prev_names = names[idx].copy()
            seq[idx] = stt[sel]
            names[idx] = nm
            first = st.slice_of[nm][0]
            if lag is None and int(seq[idx[0]]) > first and (prev_names[0] == "" or prev_names[0] != nm):
                revisions.append({"window": int(idx[0]), "kind": "entry",
                                  "distance_m": float(st.s_of[int(seq[idx[0]])] - st.s_of[first])})
            last_line = nm
        n_seg = len({(r[0], r[1]) for r in placed}) or 1
        bout_rows.append({"bout": [a, b], "windows": b - a + 1, "n_segments": n_seg,
                          "hypotheses": sorted({str(r[2]) for r in placed}) or ["transit"]})
    from pipeline.constrained.decoder import decoded_xy
    return {"seq": seq, "names": names, "xy": decoded_xy(seq, st), "on_path": names != "",
            "revisions": revisions, "bouts": bout_rows, "n_bouts": len(bout_rows),
            "n_split": sum(1 for r in bout_rows if r["n_segments"] > 1)}
