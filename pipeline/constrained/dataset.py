# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The training and evaluation sets, built from the window cache directly.

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

from pipeline.constrained.common import SIX, status
from pipeline.constrained.recordings import (
    load_features, load_meta, load_rssi, session_recordings,
)


# A set of windows with everything a head needs to train and a metric needs to score.
@dataclass
class Windows:

    X: np.ndarray
    rssi: np.ndarray
    xy: np.ndarray
    keys: np.ndarray
    path_name: np.ndarray
    participant: np.ndarray
    session: np.ndarray
    pass_id: np.ndarray
    t0_epoch: np.ndarray
    stem: np.ndarray

    # The number of items.
    def __len__(self) -> int:
        return int(len(self.xy))

    # Function subset.
    def subset(self, m) -> "Windows":
        m = np.asarray(m)
        out = {}
        for f in ("X", "rssi", "xy", "keys", "path_name", "participant", "session", "pass_id",
                  "t0_epoch", "stem"):
            v = getattr(self, f)
            out[f] = v[m] if getattr(v, "shape", (0,))[0] == len(m) else v
        return Windows(**out)

    # Function describe.
    def describe(self) -> str:
        return (f"{len(self)} windows, {len(set(self.keys.tolist()))} passes, "
                f"sessions {sorted(set(self.session.tolist()))}, "
                f"{len(set(self.participant.tolist()))} people")


END_LABELS = os.environ.get("TDR_END_LABELS") == "1"
EDGE_WINDOWS = os.environ.get("TDR_EDGE_WINDOWS", "")
EDGE_FRACTION = float(os.environ.get("TDR_EDGE_FRACTION", "1.0"))
END_LABEL_BOUND_S = 1.0


# (extra indices, their xy labels) for the end windows the protocol rule can label.
def _end_label_mask(rec, sid: str, stem: str):
    import glob as _glob
    import json as _json
    from pipeline.constrained import paths as _P
    from pipeline.constrained.rebuild_common import WINDOW_S
    hits = _glob.glob(os.path.join("data", "room_*", f"session_{sid}", f"{stem}.gt.json"))
    if not hits:
        return np.zeros(0, dtype=int), np.zeros((0, 2))
    with open(hits[0], encoding="utf-8") as f:
        sc = _json.load(f)
    lines = _P.load_paths()
    centres = np.asarray(rec.t0, float) + WINDOW_S / 2.0
    idx, lab = [], []
    for pp in sc.get("passes", []):
        at = pp.get("anchor_times") or []
        nm = str(pp.get("path_name", ""))
        if len(at) < 2 or nm not in lines:
            continue
        pts = np.asarray(lines[nm], float)
        start_xy, end_xy = pts[0], pts[-1]
        first, last = float(at[0]), float(at[-1])
        w = np.flatnonzero(rec.pass_id == int(pp["pass_id"]))
        for i in w:
            c = centres[i]
            if first - END_LABEL_BOUND_S <= c < first:
                idx.append(int(i)); lab.append(start_xy)
            elif last < c <= last + END_LABEL_BOUND_S:
                idx.append(int(i)); lab.append(end_xy)
    if not idx:
        return np.zeros(0, dtype=int), np.zeros((0, 2))
    return np.asarray(idx, dtype=int), np.asarray(lab, float)


# (indices, labels) for the windows that STRADDLE the tape entry, labelled at their END.
def _edge_straddle_mask(rec, sid: str, stem: str):
    import glob as _glob
    import json as _json
    from pipeline.constrained.rebuild_common import WINDOW_S
    hits = _glob.glob(os.path.join("data", "room_*", f"session_{sid}", f"{stem}.gt.json"))
    if not hits:
        return np.zeros(0, dtype=int), np.zeros((0, 2))
    with open(hits[0], encoding="utf-8") as f:
        sc = _json.load(f)
    lab = {}
    for pp in sc.get("passes", []):
        at = pp.get("anchor_times") or []
        ac = pp.get("anchor_coords") or []
        if len(at) >= 2:
            lab[int(pp["pass_id"])] = (np.asarray(at, float),
                                       np.asarray([c[0] for c in ac], float),
                                       np.asarray([c[1] for c in ac], float))
    mode = np.asarray(rec.mode).astype(str)
    keep_pids = None
    if EDGE_FRACTION < 1.0:
        pids = sorted({int(p) for p in rec.pass_id if int(p) >= 0})
        rng = np.random.default_rng(abs(hash((sid, stem))) % (2 ** 32))
        n_keep = int(round(EDGE_FRACTION * len(pids)))
        keep_pids = set(rng.permutation(np.asarray(pids))[:n_keep].tolist())
    idx, out = [], []
    for i in np.flatnonzero(mode == "walk_edge"):
        pid = int(rec.pass_id[i])
        if pid not in lab or (keep_pids is not None and pid not in keep_pids):
            continue
        at, ax, ay = lab[pid]
        t_end = float(rec.t0[i]) + WINDOW_S
        if t_end < at[0] - 1e-9 or t_end > at[-1] + 1e-9:
            continue
        idx.append(int(i))
        out.append((float(np.interp(t_end, at, ax)), float(np.interp(t_end, at, ay))))
    if not idx:
        return np.zeros(0, dtype=int), np.zeros((0, 2))
    return np.asarray(idx, dtype=int), np.asarray(out, float)


# Every walking window with a position label, across the given sessions, in recording order.
def walking_windows(sessions: Sequence[str], with_features: bool = True) -> Windows:
    Xs, rs, xys, keys, paths, who, sess, pids, t0s, stems = [], [], [], [], [], [], [], [], [], []
    for sid in sessions:
        for _s, stem in session_recordings(sid):
            rec = load_meta(sid, stem)
            m = np.flatnonzero((rec.mode == "walk") & np.isfinite(rec.xy).all(1))
            xy_m = rec.xy[m]
            if EDGE_WINDOWS == "end":
                e_idx, e_xy = _edge_straddle_mask(rec, sid, stem)
                if len(e_idx):
                    order = np.argsort(np.concatenate([m, e_idx]))
                    m = np.concatenate([m, e_idx])[order]
                    xy_m = np.concatenate([xy_m, e_xy])[order]
            if END_LABELS:
                extra, extra_xy = _end_label_mask(rec, sid, stem)
                extra = np.asarray([i for i in extra if i not in set(m.tolist())], dtype=int)
                if len(extra):
                    keep = np.isin(_end_label_mask(rec, sid, stem)[0], extra)
                    extra_xy = _end_label_mask(rec, sid, stem)[1][keep]
                    order = np.argsort(np.concatenate([m, extra]))
                    m = np.concatenate([m, extra])[order]
                    xy_m = np.concatenate([xy_m, extra_xy])[order]
            if not len(m):
                continue
            if with_features:
                Xs.append(load_features(sid, stem, m))
            rs.append(load_rssi(sid, stem, rec.t0_epoch)[m])
            xys.append(xy_m)
            keys += [f"{rec.participant}|{sid}|{int(p)}" for p in rec.pass_id[m]]
            paths += [str(v) for v in rec.path_name[m]]
            who += [rec.participant] * len(m)
            sess += [sid] * len(m)
            pids += [int(p) for p in rec.pass_id[m]]
            t0s.append(rec.t0_epoch[m])
            stems += [stem] * len(m)
    if not xys:
        raise ValueError(f"no walking windows found for sessions {sessions}")
    return Windows(
        X=np.concatenate(Xs) if with_features else np.zeros(0),
        rssi=np.concatenate(rs), xy=np.concatenate(xys),
        keys=np.array(keys), path_name=np.array(paths), participant=np.array(who),
        session=np.array(sess), pass_id=np.array(pids), t0_epoch=np.concatenate(t0s),
        stem=np.array(stems))


# One session split by WHOLE PASSES, one pass in held_fraction held out per person.
def within_day_split(session: str, held_fraction: int = 5, seed: int = 0,
                     with_features: bool = True) -> tuple:
    w = walking_windows([session], with_features=with_features)
    rng = np.random.default_rng(seed)
    hold = np.zeros(len(w), dtype=bool)
    for p in sorted(set(w.participant.tolist())):
        mp = w.participant == p
        groups = sorted({int(g) for g in w.pass_id[mp]})
        if len(groups) < 2:
            continue
        n = max(1, len(groups) // held_fraction)
        held = set(rng.choice(groups, size=n, replace=False).tolist())
        hold |= mp & np.isin(w.pass_id, list(held))
    tr, te = w.subset(~hold), w.subset(hold)
    if len(tr) == 0 or len(te) == 0:
        raise ValueError(f"within-day split of session {session} produced an empty side")
    return tr, te


# The two sides of one pairing, with the no-overlap guard that still matters.
def sides(tr_s: Sequence[str], te_s: Sequence[str], within: bool,
          with_features: bool = True) -> tuple:
    if within:
        tr, te = within_day_split(tr_s[0], with_features=with_features)
    else:
        tr = walking_windows(tr_s, with_features=with_features)
        te = walking_windows(te_s, with_features=with_features)
        shared = set(zip(tr.session.tolist(), tr.stem.tolist())) & \
            set(zip(te.session.tolist(), te.stem.tolist()))
        if shared:
            raise AssertionError(f"leakage: {len(shared)} recording(s) on both sides")
    overlap = set(tr.keys.tolist()) & set(te.keys.tolist())
    if overlap:
        raise AssertionError(f"leakage: {len(overlap)} pass(es) on both sides, "
                             f"e.g. {sorted(overlap)[:3]}")
    return tr, te


# Which pass keys the numbers are scored on.
def held_out_passes(tr_s: Sequence[str], te_s: Sequence[str], within: bool) -> Optional[set]:
    if not within:
        return None
    _tr, te = within_day_split(tr_s[0], with_features=False)
    return set(te.keys.tolist())
