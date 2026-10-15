"""The twelve taped lines, their arc-length state spaces, and the families they fall into.

Everything about a path comes from the recorded ground-truth sidecars, never from geometry inferred
after the fact. That rule exists because A_fwd and A_rev trace the SAME polyline in opposite
directions, as do the B, C and D pairs, so any matcher scoring distance to a polyline ties at
exactly zero on four pairs and the winner falls out of dictionary ordering. That silently mislabels
sixteen of every twenty passes.

THE FAMILIES matter for the second requirement. Errors inside a family are confusions between
parallel lines, which is a geometry question; errors between fwd and rev on the same line are
direction errors, which the motion model should fix almost for free; errors across families mean the
radio evidence is weak. Stage 3 reports the residual split those three ways, so "the gap to 100
percent" has a cause attached rather than a number alone.
"""

from __future__ import annotations

import glob
import json
import os
from typing import Optional

import numpy as np

from pipeline.constrained.common import SIX

# ---------------------------------------------------------------------------------------------
# THE COORDINATE CONVENTION, stated once and used everywhere downstream.
#
#   metres, x to the right, y upwards, origin at one corner of the room.
#   the room spans (0, 0) to (5, 5) and its centre is (2.5, 2.5).
#
# There is NO transform anywhere between this file, the emission grid, the decoder and the render:
# the render plots st.xy directly. If you are checking for an axis swap or a mirror, this is the
# only place a convention is set, and `python3 -m pipeline.constrained.paths` prints the twelve
# lines and re-runs the round-trip check so you can see it rather than trust it.
#
# THE NULL STATE'S COORDINATE IS NOT SET HERE. A state index equal to `PathStates.null` means "not
# on any line", and decoder.decoded_xy maps it to the room centre (2.5, 2.5) via its `null_xy`
# argument. That is why the demonstration parks the dot at the centre between walks: the centre is
# the null state's own decoded position, not a drawing convention.
# ---------------------------------------------------------------------------------------------

#: Arc-length discretisation along a path, metres. 0.25 m gives the 5 m straight lines 21 states
#: (20 intervals plus the endpoint) and the 7.071 m diagonals 30 (28 full intervals, then a short
#: final one so the chain ends exactly ON the last anchor rather than past it). 288 path states in
#: total, small enough that the whole decoder is one dense matrix operation. Verify with
#: `python3 -m pipeline.constrained.paths`, which prints the state count per line.
DS = 0.25

# THE THREE FAMILIES. A family is a set of PARALLEL lines, so a confusion inside a family is a
# geometry question and a confusion across families means the radio evidence was weak.
#
#   vertical   A_fwd/A_rev at x = 2.5, E_col1 at x = 0.5, E_col5 at x = 4.5
#   horizontal B_fwd/B_rev at y = 2.5, E_row1 at y = 0.5, E_row5 at y = 4.5
#   diagonal   C_fwd/C_rev corner to corner, D_fwd/D_rev the other diagonal
#
# So each of A_fwd and B_fwd has TWO parallel siblings and the diagonals have none: the E lines
# exist precisely to create the hard parallel case. Measured 2026-09-20: sibling confusions are 11
# percent of errors against an 18 percent chance share, so the siblings are NOT what limits the
# current decoder; direction reversal at twice chance is the structured error. See
# reports/GEOMETRY_AUDIT_2026-09-20.md.
VERTICAL = ("A_fwd", "A_rev", "E_col1", "E_col5")
HORIZONTAL = ("B_fwd", "B_rev", "E_row1", "E_row5")
DIAGONAL = ("C_fwd", "C_rev", "D_fwd", "D_rev")
FAMILY = {**{n: "vertical" for n in VERTICAL},
          **{n: "horizontal" for n in HORIZONTAL},
          **{n: "diagonal" for n in DIAGONAL}}

#: Paths that trace the same line in opposite directions. Used to classify a decode error as a
#: direction error rather than a line error.
REVERSE_OF = {"A_fwd": "A_rev", "A_rev": "A_fwd", "B_fwd": "B_rev", "B_rev": "B_fwd",
              "C_fwd": "C_rev", "C_rev": "C_fwd", "D_fwd": "D_rev", "D_rev": "D_fwd"}

_CACHE: dict = {}


def load_paths() -> dict:
    """The twelve named paths as ordered anchor coordinates, READ FROM THE GROUND TRUTH SIDECARS.

    The coordinates come from `anchor_coords` in `data/room_A/session_*/‹stem›.gt.json`, which is
    where the operator recorded the taped line's endpoints in room metres. `data/` is read only, so
    this is the single source of the room's geometry and nothing here is inferred or hard coded.

    Each line is taken from the FIRST sidecar that names it, and every later sidecar naming the
    same line is ignored: the tape does not move between sessions, so one reading is the
    definition. If the tape HAD moved, this would silently use the first session's geometry, which
    is a real assumption and is stated here rather than buried.

    A line is a polyline of two or more anchors. All twelve happen to be straight, two-anchor
    lines; the resampler below does not assume that.
    """
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


def pass_path_labels() -> dict:
    """``participant|session|pass_id`` to the path name the operator RECORDED.

    Never inferred from the truth coordinates: see the module docstring for why that cannot work.
    """
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


def arclength_points(coords: np.ndarray, ds: float = DS):
    """Resample a polyline at fixed arc length. Returns the points and the cumulative distance."""
    coords = np.asarray(coords, dtype=float)
    seg = np.linalg.norm(np.diff(coords, axis=0), axis=1)
    total = float(seg.sum())
    if total <= 0:
        return coords[:1], np.array([0.0])
    # stop AT the end rather than past it: arange(0, total + ds, ds) overshoots whenever the length
    # is not a multiple of ds, and np.interp then clamps, leaving a final state a few centimetres
    # from its neighbour. The diagonals are 7.071 m, so this bit every one of them.
    s = np.arange(0.0, total + 1e-9, ds)
    if s[-1] < total - 1e-9:
        s = np.append(s, total)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    pts = np.stack([np.interp(s, cum, coords[:, 0]), np.interp(s, cum, coords[:, 1])], axis=1)
    return pts, s


class PathStates:
    """The twelve chains as one flat state space, plus the bookkeeping the decoder needs.

    State ``i`` in ``0 .. n_states - 1`` is a point on one path. ``path_of[i]`` names it,
    ``s_of[i]`` is the arc length, ``xy[i]`` the coordinate and ``dir_of[i]`` the unit direction of
    travel there. ``start_index`` and ``end_index`` give each chain's first and last state, which is
    where the null state may be entered and left.

    THE CHAINS ARE LAID OUT END TO END IN ONE FLAT ARRAY, in sorted name order, and
    ``slice_of[name]`` gives each one's half-open range. Nothing outside this class should assume
    an ordering: always go through ``slice_of``.

    ARC LENGTH RESTARTS AT ZERO ON EVERY CHAIN. ``s_of`` is distance along that chain, not a
    position in the flat array, so comparing ``s_of`` between two different chains is meaningless
    and comparing it within one is how progress along a line is measured.

    A_fwd AND A_rev ARE SEPARATE CHAINS over the same tape, with opposite ``dir_of`` and with arc
    length running the opposite way. That is deliberate: direction is part of what the decoder has
    to decide, and the transition matrix forbids going backwards along a chain, so a person walking
    A_rev is not describable as A_fwd at all.
    """

    def __init__(self, ds: float = DS):
        paths = load_paths()
        names = sorted(paths)
        xy, s_of, path_of, dir_of = [], [], [], []
        self.slice_of, self.names, self.ds = {}, names, ds
        i0 = 0                       # running STATE offset, not the number of paths appended
        for nm in names:
            pts, s = arclength_points(paths[nm], ds)
            xy.append(pts)
            s_of.append(s)
            path_of += [nm] * len(s)
            # DIRECTION is the CHORD from first anchor to last, not a local tangent, and it is
            # repeated for every state on the chain. That is exact for a straight line and would be
            # wrong for a bent one; all twelve lines are straight, and the assertion below fails
            # loudly if that ever stops being true rather than quietly giving every state on a bend
            # the same direction.
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
        #: index of the NULL state in the unified space, appended after every path state
        self.null = self.n_states

    def direction_of(self, path_name: str) -> np.ndarray:
        i0, _i1 = self.slice_of[path_name]
        return self.dir_of[i0]

    def points(self, path_name: str) -> np.ndarray:
        i0, i1 = self.slice_of[path_name]
        return self.xy[i0:i1]

    def s_values(self, path_name: str) -> np.ndarray:
        i0, i1 = self.slice_of[path_name]
        return self.s_of[i0:i1]

    def describe(self) -> str:
        parts = [f"{nm}({self.slice_of[nm][1] - self.slice_of[nm][0]})" for nm in self.names]
        return f"{len(self.names)} paths, {self.n_states} path states at {self.ds} m: " + " ".join(parts)


def states(ds: float = DS) -> PathStates:
    """The cached state space. Every stage in the project calls this, so there is exactly one."""
    key = f"states_{ds}"
    if key not in _CACHE:
        _CACHE[key] = PathStates(ds)
    return _CACHE[key]


def error_kind(true_path: Optional[str], decoded_path: Optional[str]) -> str:
    """Classify one path decision: correct, direction, parallel (same family), or cross-family."""
    if true_path is None or decoded_path is None:
        return "unlabelled"
    if true_path == decoded_path:
        return "correct"
    if REVERSE_OF.get(true_path) == decoded_path:
        return "direction"
    if FAMILY.get(true_path) == FAMILY.get(decoded_path):
        return "parallel"
    return "cross_family"


def confusion(true_paths, decoded_paths, names=None) -> tuple:
    """The 12 x 12 confusion matrix, rows true and columns decoded."""
    names = list(names or sorted(load_paths()))
    idx = {n: i for i, n in enumerate(names)}
    M = np.zeros((len(names), len(names)), dtype=int)
    for t, d in zip(true_paths, decoded_paths):
        if t in idx and d in idx:
            M[idx[t], idx[d]] += 1
    return M, names


def write_confusion(M: np.ndarray, names, csv_path: str, fig_path: Optional[str] = None,
                    title: str = "") -> None:
    """Save the confusion matrix as CSV and, if matplotlib is available, as a figure."""
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


# ---------------------------------------------------------------------------------------------
# A READABLE SELF-CHECK. Run it with:
#
#     PYTHONPATH=. python3 -m pipeline.constrained.paths
#
# It prints the twelve lines as the decoder actually holds them and re-runs the round trip: every
# labelled ground-truth position must lie on its own chain to within half a state spacing. If an
# axis were swapped, a line mirrored or a direction reversed anywhere between the sidecars, the
# chains and the rendered coordinates, that check is what would catch it.
# ---------------------------------------------------------------------------------------------

def audit(ds: float = DS) -> dict:
    """Print the geometry and verify it against the labelled truth. Returns the numbers."""
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

    # THE ROUND TRIP. Every labelled truth position must sit on its own chain.
    from pipeline.constrained.recordings import load_meta, recordings
    worst, n, worst_where = 0.0, 0, None
    for sess, stem in recordings():
        try:
            rec = load_meta(sess, stem)
        except Exception:                                                # noqa: BLE001
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
