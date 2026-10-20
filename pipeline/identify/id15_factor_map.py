# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Projected bistatic factor map.

from __future__ import annotations

import os
from typing import Iterable, Optional, Sequence

import numpy as np

ROOM_A_TX = (2.5, -0.5)
ROOM_A_RX = {"RX1": (2.5, 5.5), "RX2": (-0.5, 2.5), "RX3": (5.5, 2.5)}
ROOM_A_EXTENT = (0.0, 5.0, 0.0, 5.0)

F_LOW = 0.3
F_BAD_FRACTION = 0.25

C_M_S = 299_792_458.0
DEFAULT_CHANNEL_HZ = 2.437e9


# Function wavelength m.
def wavelength_m(f_hz: float = DEFAULT_CHANNEL_HZ) -> float:
    return C_M_S / float(f_hz)


# F at each point for one link and one walking direction.
def bistatic_factor(points, direction, tx=ROOM_A_TX, rx=(2.5, 5.5)) -> np.ndarray:
    p = np.atleast_2d(np.asarray(points, float))
    tx = np.asarray(tx, float)
    rx = np.asarray(rx, float)
    v = np.asarray(direction, float)
    n = np.linalg.norm(v)
    if n < 1e-12:
        return np.zeros(len(p))
    v = v / n

    # Function unit from.
    def unit_from(node):
        d = p - node[None, :]
        return d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)

    s = unit_from(tx) + unit_from(rx)
    return np.abs(s @ v) / 2.0


# F = 2 F v / lambda.
def doppler_hz(F, speed_m_s: float, channel_hz: float = DEFAULT_CHANNEL_HZ) -> np.ndarray:
    return 2.0 * np.asarray(F, float) * float(speed_m_s) / wavelength_m(channel_hz)


# F over a grid, per link and minimum over links.
def factor_map(direction, extent=ROOM_A_EXTENT, step: float = 0.05,
               tx=ROOM_A_TX, rx: dict = None) -> dict:
    rx = dict(rx or ROOM_A_RX)
    x0, x1, y0, y1 = extent
    xs = np.arange(x0, x1 + 1e-9, step)
    ys = np.arange(y0, y1 + 1e-9, step)
    X, Y = np.meshgrid(xs, ys)
    pts = np.column_stack([X.ravel(), Y.ravel()])
    per = {k: bistatic_factor(pts, direction, tx, v).reshape(X.shape) for k, v in rx.items()}
    stack = np.stack([per[k] for k in sorted(per)], axis=0)
    return {"x": xs, "y": ys, "per_link": per, "min_over_links": stack.min(axis=0),
            "mean_over_links": stack.mean(axis=0), "direction": tuple(np.asarray(direction, float))}


# Score one straight directed segment.
def score_segment(start, end, n: int = 200, tx=ROOM_A_TX, rx: dict = None) -> dict:
    rx = dict(rx or ROOM_A_RX)
    a, b = np.asarray(start, float), np.asarray(end, float)
    d = b - a
    length = float(np.linalg.norm(d))
    if length < 1e-9:
        return {"length_m": 0.0, "struck_out": True, "why": "zero length"}
    t = np.linspace(0.0, 1.0, int(n))
    pts = a[None, :] + t[:, None] * d[None, :]
    per, bad = {}, {}
    for k in sorted(rx):
        F = bistatic_factor(pts, d, tx, rx[k])
        per[k] = {"mean_F": round(float(F.mean()), 4), "min_F": round(float(F.min()), 4),
                  "frac_below_0.3": round(float((F < F_LOW).mean()), 4)}
        bad[k] = float((F < F_LOW).mean())
    means = [per[k]["mean_F"] for k in per]
    worst = max(bad, key=bad.get)
    struck = bool(bad[worst] > F_BAD_FRACTION)
    return {"start": [round(float(x), 3) for x in a], "end": [round(float(x), 3) for x in b],
            "length_m": round(length, 3), "per_link": per,
            "mean_F_over_links": round(float(np.mean(means)), 4),
            "min_link_mean_F": round(float(np.min(means)), 4),
            "worst_link": worst, "worst_link_frac_below_0.3": round(bad[worst], 4),
            "struck_out": struck,
            "why": (f"{worst} spends {bad[worst]:.0%} of the path below F={F_LOW}, over the "
                    f"pre-registered {F_BAD_FRACTION:.0%} limit") if struck else "passes the F gate"}


# Rank every straight directed segment of the given length that fits inside the room.
def best_corridors(length_m: float = 7.0, extent=ROOM_A_EXTENT, n_angles: int = 36,
                   step: float = 0.25, tx=ROOM_A_TX, rx: dict = None, top: int = 10) -> list:
    rx = dict(rx or ROOM_A_RX)
    x0, x1, y0, y1 = extent
    out = []
    for ang in np.linspace(0.0, np.pi, n_angles, endpoint=False):
        u = np.array([np.cos(ang), np.sin(ang)])
        for sx in np.arange(x0, x1 + 1e-9, step):
            for sy in np.arange(y0, y1 + 1e-9, step):
                a = np.array([sx, sy])
                b = a + length_m * u
                if not (x0 - 1e-9 <= b[0] <= x1 + 1e-9 and y0 - 1e-9 <= b[1] <= y1 + 1e-9):
                    continue
                out.append(score_segment(a, b, tx=tx, rx=rx))
    out.sort(key=lambda r: (not r["struck_out"], r["min_link_mean_F"]), reverse=True)
    return out[:top]


# Every taped line in Room A, both directions, scored.
def score_named_lines(tx=ROOM_A_TX, rx: dict = None) -> dict:
    from pipeline.constrained import paths as P
    rx = dict(rx or ROOM_A_RX)
    out = {}
    for name, pts in P.load_paths().items():
        v = np.asarray(pts, float)
        out[name] = score_segment(v[0], v[-1], tx=tx, rx=rx)
    return out


# F17.
def plot_map(direction, path: str, extent=ROOM_A_EXTENT, tx=ROOM_A_TX, rx: dict = None,
             overlay_lines: bool = True, corridor: Optional[Sequence] = None,
             title: str = "") -> list:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rx = dict(rx or ROOM_A_RX)
    m = factor_map(direction, extent, 0.05, tx, rx)
    panels = [("min over links", m["min_over_links"])] + \
             [(k, m["per_link"][k]) for k in sorted(m["per_link"])]
    fig, axes = plt.subplots(1, len(panels), figsize=(4.0 * len(panels), 4.2), squeeze=False)
    for ax, (name, Z) in zip(axes[0], panels):
        im = ax.imshow(Z, origin="lower", extent=extent, vmin=0.0, vmax=1.0, cmap="viridis")
        ax.contour(m["x"], m["y"], Z, levels=[F_LOW], colors="w", linewidths=1.2)
        if overlay_lines:
            try:
                from pipeline.constrained import paths as P
                for ln, pts in P.load_paths().items():
                    v = np.asarray(pts, float)
                    ax.plot(v[:, 0], v[:, 1], color="w", lw=0.6, alpha=0.5)
            except Exception:
                pass
        if corridor is not None:
            c = np.asarray(corridor, float)
            ax.plot(c[:, 0], c[:, 1], color="red", lw=2.4)
        ax.plot(*tx, marker="^", color="orange", ms=11, mec="k")
        for k, v in rx.items():
            ax.plot(*v, marker="s", color="cyan", ms=9, mec="k")
            ax.annotate(k, v, color="w", fontsize=7, xytext=(3, 3), textcoords="offset points")
        ax.set_title(f"{name}", fontsize=9)
        ax.set_xlabel("x (m)")
    axes[0][0].set_ylabel("y (m)")
    fig.colorbar(im, ax=axes[0].tolist(), shrink=0.85, label="projected bistatic factor F")
    fig.suptitle(title or f"F for walking direction {np.round(m['direction'], 2)}; "
                          f"white contour is F = {F_LOW}", fontsize=10)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    wrote = []
    for ext in ("pdf", "png"):
        p = f"{path}.{ext}"
        fig.savefig(p, bbox_inches="tight", dpi=200)
        wrote.append(p)
    plt.close(fig)
    return wrote
