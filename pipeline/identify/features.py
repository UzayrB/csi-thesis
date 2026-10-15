"""Per-PASS gait and geometry features. Brief phase D1.

Every feature here is a per-pass scalar or short vector, computed ONLY because the walk boundaries
and the line are known, which the tracker supplies. One decision per pass, never per window.

THE SPECTRAL PICTURE. A walking body modulates the channel at two related rates: the STEP rate,
about 2 Hz, and the STRIDE rate, about 1 Hz, which is one full gait cycle of two steps. Which of the
two dominates depends on gait SYMMETRY, because a symmetric gait makes consecutive steps look alike
and concentrates energy at the step rate, while an asymmetric one makes the two-step cycle the true
period. Phase C measured 115 of 360 passes dominated by the stride rate, so that flag is carried
here as a feature in its own right rather than being normalised away.
"""

from __future__ import annotations

import numpy as np

from pipeline.identify.common import (CADENCE_HI, CADENCE_LO, FS, GAIT_HI, GAIT_LO, STRIDE_HI,
                                      STRIDE_LO, bandpass, cadence_of, envelopes, gait_windows,
                                      pass_stream)

#: closest approach of each line to any node, in metres, computed from the geometry. A and B pass
#: 0.50 m from a node and the edge lines 1.12 m, so the deepest shadow, and the best chance of
#: reading body cross-section, is on the CENTRAL lines rather than the edges.
NEAR_NODE_M = {"A_fwd": 0.50, "A_rev": 0.50, "B_fwd": 0.50, "B_rev": 0.50,
               "E_row1": 1.12, "E_row5": 1.12, "E_col1": 1.12, "E_col5": 1.12,
               "C_fwd": 2.12, "C_rev": 2.12, "D_fwd": 2.12, "D_rev": 2.12}
NEAR_NODE_LINES = tuple(k for k, v in NEAR_NODE_M.items() if v <= 0.60)


def spectral_shape(env: np.ndarray, fs: float = FS) -> dict:
    """Welch shape over the gait band: how concentrated the rhythm is, and where it sits."""
    from scipy.signal import welch
    f, pxx = welch(np.asarray(env, float), fs=fs, nperseg=min(512, np.asarray(env).shape[-1]))
    band = (f >= GAIT_LO) & (f <= GAIT_HI)
    p = np.atleast_2d(pxx)[:, band]
    fb = f[band]
    tot = np.maximum(p.sum(axis=1, keepdims=True), 1e-20)
    pn = p / tot
    centroid = (pn * fb[None, :]).sum(axis=1)
    entropy = -(pn * np.log(pn + 1e-20)).sum(axis=1) / np.log(max(len(fb), 2))
    lo = (f >= 0.5) & (f <= 1.4)                 # torso sway
    hi = (f > 1.4) & (f <= 3.0)                  # leg swing
    a = np.atleast_2d(pxx)[:, lo].sum(axis=1)
    b = np.atleast_2d(pxx)[:, hi].sum(axis=1)
    return {"centroid_hz": centroid, "entropy": entropy,
            "band_ratio": a / np.maximum(b, 1e-20)}


def cadence_variability(env: np.ndarray, cad: float, fs: float = FS) -> float:
    """Coefficient of variation of inter-step intervals, from peaks of the envelope."""
    from scipy.signal import find_peaks
    if not cad or cad <= 0:
        return float("nan")
    x = np.asarray(env, float)
    x = x.mean(0) if x.ndim > 1 else x
    dist = max(int(fs / (cad * 1.6)), 2)
    pk, _ = find_peaks(x, distance=dist)
    if len(pk) < 4:
        return float("nan")
    iv = np.diff(pk) / fs
    return float(np.std(iv) / max(np.mean(iv), 1e-9))


def shadow_depths(stream: np.ndarray, rec, windows: np.ndarray, line: str, speed: float,
                  st, fs: float = FS) -> dict:
    """Dip DEPTH at each transmitter-receiver sight-line crossing, where the tracker supplies WHEN.

    The crossing code failed at LOCATING dips and this is a different question: the tracker now puts
    the walker along the line to about 0.3 m, so the crossing time is known to about a quarter of a
    second and only the DEPTH has to be measured. Depth is a body cross-section proxy, which is why
    the near-node lines matter: on A and B the body passes 0.50 m from a node, where the shadow is
    deepest and build should show most strongly.
    """
    import numpy as _np
    from pipeline.constrained import paths as P
    nodes = {"RX1": (2.5, 5.5), "RX2": (-0.5, 2.5), "RX3": (5.5, 2.5)}
    tx = _np.array([2.5, -0.5])
    pts = _np.asarray(P.load_paths()[line], float)
    s = _np.concatenate([[0.0], _np.cumsum(_np.linalg.norm(_np.diff(pts, axis=0), axis=1))])
    amp = _np.asarray(stream, float).mean(axis=2)             # (3, n) per-link amplitude
    n = amp.shape[1]
    dur = n / fs
    out = {}
    for li, (name, rx) in enumerate(nodes.items()):
        rx = _np.asarray(rx, float)
        d = _np.abs(_np.cross(rx - tx, pts - tx)) / max(_np.linalg.norm(rx - tx), 1e-9)
        k = int(_np.argmin(d))
        if d[k] > 0.35:                                        # this line does not cross this link
            out[f"depth_{name}"] = _np.nan
            continue
        frac = s[k] / max(s[-1], 1e-9)
        c = int(_np.clip(frac * n, 0, n - 1))
        half = int(0.6 * fs)
        seg = amp[li, max(0, c - half):min(n, c + half)]
        med = _np.median(amp[li])
        out[f"depth_{name}"] = float((med - seg.min()) / max(abs(med), 1e-9)) if len(seg) else _np.nan
    d2, d3 = out.get("depth_RX2", _np.nan), out.get("depth_RX3", _np.nan)
    out["shadow_asymmetry"] = float(d2 - d3) if _np.isfinite(d2) and _np.isfinite(d3) else _np.nan
    out["n_crossings"] = int(sum(1 for k, v in out.items()
                                 if k.startswith("depth_") and _np.isfinite(v)))
    return out


def pass_features(rec, pass_row: dict, st) -> dict:
    """Everything for one pass. Reads the raw stream once."""
    w = gait_windows(rec, pass_row["pass_id"])
    if not len(w):
        return {}
    stream = pass_stream(pass_row["session"], pass_row["stem"], w)
    env = envelopes(stream)
    cad, frac = cadence_of(env)
    speed = pass_row.get("speed_m_s")
    step = (speed / cad) if (cad and speed) else None
    sym = 0
    if step is not None and step > STRIDE_HI and cad:
        doubled = speed / (2.0 * cad)
        if STRIDE_LO <= doubled <= STRIDE_HI:
            cad, step, sym = 2.0 * cad, doubled, 1     # the stride-rate reading: asymmetric gait
    sh = spectral_shape(env)
    f = {"speed": speed, "cadence": cad, "step_length": step,
         "spectral_symmetry": sym, "spectral_fraction": frac,
         "cadence_cv": cadence_variability(env, cad),
         "near_node_m": NEAR_NODE_M.get(pass_row["line"], np.nan),
         "is_near_node": int(pass_row["line"] in NEAR_NODE_LINES)}
    for i in range(3):
        f[f"centroid_L{i}"] = float(sh["centroid_hz"][i])
        f[f"entropy_L{i}"] = float(sh["entropy"][i])
        f[f"band_ratio_L{i}"] = float(sh["band_ratio"][i])
    f.update(shadow_depths(stream, rec, w, pass_row["line"], speed, st))
    return f


#: the ladder, in the order the brief fixes and no other
GROUPS = [
    ("speed only", ["speed"]),
    ("plus cadence", ["cadence"]),
    ("plus step length", ["step_length"]),
    ("plus spectral symmetry", ["spectral_symmetry"]),
    ("plus cadence variability", ["cadence_cv"]),
    ("plus band ratio", ["band_ratio_L0", "band_ratio_L1", "band_ratio_L2"]),
    ("plus spectral shape", ["centroid_L0", "centroid_L1", "centroid_L2",
                             "entropy_L0", "entropy_L1", "entropy_L2"]),
    ("plus shadow depth", ["depth_RX1", "depth_RX2", "depth_RX3"]),
    ("plus shadow asymmetry", ["shadow_asymmetry"]),
]
