# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The twelve taped lines: where they are (taken from the recordings), the points along each line the decoder...

from __future__ import annotations

import glob
import json

import numpy as np

from pipeline.constrained.RunLive.shared_settings import SIX


DS = 0.25

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
