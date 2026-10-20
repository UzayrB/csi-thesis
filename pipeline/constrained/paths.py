# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The twelve taped lines, their arc-length state spaces, and the families they fall into.

from __future__ import annotations

import glob
import json
import os
from typing import Optional

import numpy as np

from pipeline.constrained.common import SIX


DS = 0.25

VERTICAL = ("A_fwd", "A_rev", "E_col1", "E_col5")
HORIZONTAL = ("B_fwd", "B_rev", "E_row1", "E_row5")
DIAGONAL = ("C_fwd", "C_rev", "D_fwd", "D_rev")
FAMILY = {**{n: "vertical" for n in VERTICAL},
          **{n: "horizontal" for n in HORIZONTAL},
          **{n: "diagonal" for n in DIAGONAL}}

REVERSE_OF = {"A_fwd": "A_rev", "A_rev": "A_fwd", "B_fwd": "B_rev", "B_rev": "B_fwd",
              "C_fwd": "C_rev", "C_rev": "C_fwd", "D_fwd": "D_rev", "D_rev": "D_fwd"}

_CACHE: dict = {}


# The twelve named paths as ordered anchor coordinates, READ FROM THE GROUND TRUTH SIDECARS.
def load_paths() -> dict:
    if "paths" in _CACHE:
        return _CACHE["paths"]
    paths: dict = {}
    for p in sorted(glob.glob("data/room_A/session_*/participant_*_walk.gt.json")):
        if "_DEMO_" in p:
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if (d.get("participant_code") or "") not in SIX:
            continue
        for ps in d.get("passes", []):
            nm, c = ps.get("path_name") or "", ps.get("anchor_coords") or []
            if nm and len(c) >= 2 and nm not in paths:
                paths[nm] = np.asarray(c, dtype=float)
    _CACHE["paths"] = paths
    return paths


# Participant|session|pass_id to the path name the operator RECORDED.
def pass_path_labels() -> dict:
    if "labels" in _CACHE:
        return _CACHE["labels"]
    out: dict = {}
    for p in sorted(glob.glob("data/room_A/session_*/participant_*_walk.gt.json")):
        if "_DEMO_" in p:
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        who = d.get("participant_code") or ""
        if who not in SIX:
            continue
        sid = p.split("session_")[1][:2]
        for ps in d.get("passes", []):
            nm, pid = ps.get("path_name"), ps.get("pass_id")
            if nm and pid is not None:
                out[f"{who}|{sid}|{pid}"] = nm
    _CACHE["labels"] = out
    return out


# Resample a polyline at fixed arc length.
def arclength_points(coords: np.ndarray, ds: float = DS):
    coords = np.asarray(coords, dtype=float)
    seg = np.linalg.norm(np.diff(coords, axis=0), axis=1)
    total = float(seg.sum())
    if total <= 0:
        return coords[:1], np.array([0.0])
    s = np.arange(0.0, total + 1e-9, ds)
    if s[-1] < total - 1e-9:
        s = np.append(s, total)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    pts = np.stack([np.interp(s, cum, coords[:, 0]), np.interp(s, cum, coords[:, 1])], axis=1)
    return pts, s


# The twelve chains as one flat state space, plus the bookkeeping the decoder needs.
class PathStates:

    # Sets up the object.
    def __init__(self, ds: float = DS):
        paths = load_paths()
        names = sorted(paths)
        xy, s_of, path_of, dir_of = [], [], [], []
        self.slice_of, self.names, self.ds = {}, names, ds
        i0 = 0
        for nm in names:
            pts, s = arclength_points(paths[nm], ds)
            xy.append(pts)
            s_of.append(s)
            path_of += [nm] * len(s)
            v = paths[nm][-1] - paths[nm][0]
            chord = float(np.linalg.norm(v))
            assert abs(chord - float(s[-1])) < 1e-6 * max(1.0, chord), (
                f"{nm} is not straight: its chord is {chord:.4f} m but its arc length is "
                f"{float(s[-1]):.4f} m, so a single chord direction does not describe it")
            u = v / max(chord, 1e-12)
            dir_of.append(np.repeat(u[None, :], len(s), axis=0))
            self.slice_of[nm] = (i0, i0 + len(s))
            i0 += len(s)
        self.xy = np.concatenate(xy, axis=0)
        self.s_of = np.concatenate(s_of, axis=0)
        self.dir_of = np.concatenate(dir_of, axis=0)
        self.path_of = np.asarray(path_of)
        self.n_states = len(self.xy)
        self.start_index = np.array([self.slice_of[nm][0] for nm in names])
        self.end_index = np.array([self.slice_of[nm][1] - 1 for nm in names])
        self.path_index = {nm: i for i, nm in enumerate(names)}
        self.null = self.n_states

    # Function direction of.
    def direction_of(self, path_name: str) -> np.ndarray:
        i0, _i1 = self.slice_of[path_name]
        return self.dir_of[i0]

    # Function points.
    def points(self, path_name: str) -> np.ndarray:
        i0, i1 = self.slice_of[path_name]
        return self.xy[i0:i1]

    # Function s values.
    def s_values(self, path_name: str) -> np.ndarray:
        i0, i1 = self.slice_of[path_name]
        return self.s_of[i0:i1]

    # Function describe.
    def describe(self) -> str:
        parts = [f"{nm}({self.slice_of[nm][1] - self.slice_of[nm][0]})" for nm in self.names]
        return f"{len(self.names)} paths, {self.n_states} path states at {self.ds} m: " + " ".join(parts)


# The cached state space.
def states(ds: float = DS) -> PathStates:
    key = f"states_{ds}"
    if key not in _CACHE:
        _CACHE[key] = PathStates(ds)
    return _CACHE[key]


# Classify one path decision: correct, direction, parallel (same family), or cross-family.
def error_kind(true_path: Optional[str], decoded_path: Optional[str]) -> str:
    if true_path is None or decoded_path is None:
        return "unlabelled"
    if true_path == decoded_path:
        return "correct"
    if REVERSE_OF.get(true_path) == decoded_path:
        return "direction"
    if FAMILY.get(true_path) == FAMILY.get(decoded_path):
        return "parallel"
    return "cross_family"


# The 12 x 12 confusion matrix, rows true and columns decoded.
def confusion(true_paths, decoded_paths, names=None) -> tuple:
    names = list(names or sorted(load_paths()))
    idx = {n: i for i, n in enumerate(names)}
    M = np.zeros((len(names), len(names)), dtype=int)
    for t, d in zip(true_paths, decoded_paths):
        if t in idx and d in idx:
            M[idx[t], idx[d]] += 1
    return M, names


# Save the confusion matrix as CSV and, if matplotlib is available, as a figure.
def write_confusion(M: np.ndarray, names, csv_path: str, fig_path: Optional[str] = None,
                    title: str = "") -> None:
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("true\\decoded," + ",".join(names) + "\n")
        for i, n in enumerate(names):
            f.write(n + "," + ",".join(str(int(v)) for v in M[i]) + "\n")
    if not fig_path:
        return
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        os.makedirs(os.path.dirname(fig_path) or ".", exist_ok=True)
        tot = M.sum(1, keepdims=True)
        frac = np.divide(M, np.maximum(tot, 1), where=tot > 0)
        fig, ax = plt.subplots(figsize=(7.2, 6.4))
        im = ax.imshow(frac, cmap="magma", vmin=0, vmax=1)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(names, rotation=90, fontsize=8)
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=8)
        for i in range(len(names)):
            for j in range(len(names)):
                if M[i, j]:
                    ax.text(j, i, str(int(M[i, j])), ha="center", va="center", fontsize=7,
                            color="white" if frac[i, j] > 0.5 else "black")
        ax.set_xlabel("decoded path")
        ax.set_ylabel("true path")
        ax.set_title(title or "path confusion", fontsize=10)
        fig.colorbar(im, ax=ax, shrink=0.8, label="fraction of true row")
        fig.tight_layout()
        fig.savefig(fig_path, dpi=120)
        plt.close(fig)
    except Exception:
        pass



# Print the geometry and verify it against the labelled truth.
def audit(ds: float = DS) -> dict:
    st = states(ds)
    xy, s_of = np.asarray(st.xy), np.asarray(st.s_of, dtype=float)
    print(f"coordinate convention: metres, x right, y up, room (0,0) to (5,5), centre (2.5,2.5)")
    print(f"state spacing {ds} m; null state index {st.null} draws at the room centre\n")
    print(f"{'line':9} {'family':11} {'start':>14} {'end':>14} {'length':>8} {'states':>7} {'direction':>10}")
    for nm in st.names:
        a, b = st.slice_of[nm]
        p0, p1 = xy[a], xy[b - 1]
        u = st.dir_of[a]
        d = ("+x" if u[0] > 0.1 else "-x" if u[0] < -0.1 else "") + \
            ("+y" if u[1] > 0.1 else "-y" if u[1] < -0.1 else "")
        print(f"{nm:9} {FAMILY.get(nm, '?'):11} ({p0[0]:5.2f},{p0[1]:5.2f}) "
              f"({p1[0]:5.2f},{p1[1]:5.2f}) {float(s_of[b - 1]):8.2f} {b - a:7d} {d:>10}")

    from pipeline.constrained.recordings import load_meta, recordings
    worst, n, worst_where = 0.0, 0, None
    for sess, stem in recordings():
        try:
            rec = load_meta(sess, stem)
        except Exception:
            continue
        txy = np.asarray(rec.xy, dtype=float)
        for pid, nm, _a, _b in rec.pass_spans():
            if nm not in st.slice_of:
                continue
            a, b = st.slice_of[nm]
            w = np.flatnonzero((np.asarray(rec.pass_id) == pid)
                               & (np.asarray(rec.mode).astype(str) == "walk"))
            for i in w:
                if not np.isfinite(txy[i]).all():
                    continue
                dmin = float(np.min(np.linalg.norm(xy[a:b] - txy[i], axis=1)))
                n += 1
                if dmin > worst:
                    worst, worst_where = dmin, (sess, stem, int(pid), nm)
    half = ds / 2.0
    ok = worst <= half + 1e-9
    print(f"\nround trip: {n} labelled truth points checked against their own chain")
    print(f"  worst distance {worst:.4f} m, half a state spacing is {half:.4f} m -> "
          f"{'PASS, quantisation only' if ok else 'FAIL'}")
    if worst_where:
        print(f"  worst case was {worst_where}")
    if not ok:
        print("  a failure here means an axis swap, a mirror or a reversed direction somewhere "
              "between the sidecars, the chains and the render")
    return {"n_points": n, "worst_m": worst, "half_spacing_m": half, "passes": bool(ok)}


if __name__ == "__main__":
    audit()
