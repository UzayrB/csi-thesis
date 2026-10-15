"""iv6_common. Shared pieces of Uzayr's components-and-features TEST (15 Oct 2026, `runs/identify/engine/PLAN.md`,
note of that date): the engine v5 replays' stored component log-probabilities, engine v5's combination with a weight
per component, the scorecard stores in `ilc_outer`'s format and the cell definitions.

Nothing here changes a shipped file: the v5 replays, models and engine are read only. Outputs go under
`runs/identify/v6_test/`.

Development evaluation, all data seen; exploratory.
"""

from __future__ import annotations

import os

import numpy as np

from pipeline.identify import ilc_outer as CO
from pipeline.identify import ilp_cand as PC

LABEL = "development evaluation, all data seen; exploratory"
OUT = os.path.join("runs", "identify", "v6_test")
REP = os.path.join("runs", "identify", "engine", "replays")
FEATC = ("rf", "rf_prior", "rf_pace_prior", "et_pace_prior", "lda_pace_prior", "hgb_pace_prior")
CNNC = ("cnn", "cnn_prior", "cnn_perlink_prior")
COMPS = FEATC + CNNC                      # engine.Model.components for a v5 model, in the order combine sums them
WINDOWS = ("", "_0.15", "_0.30")          # the engine's keys (0.0,) + offsets, in that order
SESSIONS = ("A1", "A2", "A3", "B1", "B2")
MODELS = {k: (v[0][:-3] + "_v5", v[1]) for k, v in CO.MODELS.items()}     # loso_A1 -> (loso_A1_v5, [A1]), ...

# the cells (ilc_outer's (model, session or "*", kind); a pooled cell is a list of them)
ZERO, CROSS, GUARD_ID = CO.ZERO, CO.CROSS, CO.GUARD
ROOM_TRACK = {"Room A tracking": [("loso", s, "path") for s in ("A1", "A2", "A3")],
              "Room B tracking": [("loso", s, "path") for s in ("B1", "B2")]}
CORE = {"xr_ABtrk A3+B2 path": [("xr_ABtrk", "A3", "path"), ("xr_ABtrk", "B2", "path")],
        "xr_A all B2": [("xr_A", "B2", k) for k in ("path", "natural", "slow", "fast")]}
GUARDS = {"loso natural": [("loso", "*", "natural")], "loso slow": [("loso", "*", "slow")],
          "loso fast": [("loso", "*", "fast")]} | ROOM_TRACK
GUARD_MARGIN = 5.0                        # points (ilc_outer.summarise and ilr_core.figures: 5 points, 0.05)

_R = {}


def replay(model: str, session: str) -> dict:
    """One v5 replay: te, the weight a per walk, the stored ensemble, and each component's three windows (3, n, 6)."""
    key = (model, session)
    if key not in _R:
        z = np.load(os.path.join(REP, f"{model}_{session}_T4.0.npz"))
        _R[key] = {"te": z["te"], "a": z["weight_a"].astype(float), "ensemble": z["ensemble"],
                   "confidence": z["confidence"], "room": z["room"],
                   "c": {c: np.stack([z[f"c_{c}{w}"] for w in WINDOWS]) for c in COMPS}}
    return _R[key]


def normalise(L: np.ndarray) -> np.ndarray:
    """`idv2_core.normalise_logp`, row-wise."""
    m = L.max(-1, keepdims=True)
    return L - (m + np.log(np.exp(L - m).sum(-1, keepdims=True)))


def coef(w: dict, a: np.ndarray, rule: bool = True) -> dict:
    """Per component, per walk: w_c x a for a feature component (the installation rule), w_c for a CNN component.
    `rule=False` drops the installation rule (a = 1 everywhere)."""
    g = a if rule else np.ones_like(a)
    return {c: (float(w[c]) * g if c in FEATC else np.full_like(a, float(w[c]) * 1.0)) for c in COMPS}


def combine(r: dict, w: dict, rule: bool = True) -> dict:
    """`engine.Session.combine` with a weight per component: per window s_k = sum_c coef_c x c_k (summed in the
    components' order), normalised; the windows averaged and normalised; the confidence softmax(mean_k s_k / A) with
    A = sum_c coef_c. With every w_c = 1 and the rule on, this is engine v5's own formula term for term."""
    k = coef(w, r["a"], rule)
    ens, raw = [], []
    for i in range(len(WINDOWS)):
        s = 0
        for c in COMPS:
            s = s + k[c][:, None] * r["c"][c][i]
        raw.append(s)
        ens.append(normalise(s))
    E = normalise(np.mean(ens, axis=0))
    A = sum(k[c] for c in COMPS)
    z = np.mean(raw, axis=0) / A[:, None]
    conf = np.exp(z - z.max(1, keepdims=True))
    return {"ensemble": E, "confidence": conf / conf.sum(1, keepdims=True)}


def walk_mean(r: dict) -> dict:
    """Each component's walk-level evidence m_c = the mean of its three windows (n, 6). engine v5's ensemble equals
    log_softmax(sum_c coef_c m_c) exactly in algebra (the per-window normalisers are constant across classes)."""
    return {c: r["c"][c].mean(0) for c in COMPS}


def labels(te: np.ndarray) -> np.ndarray:
    """Class index (0 to 5) of each walk."""
    return np.searchsorted(np.array(PC.CLASSES), PC.bank()["a"]["anon"][te])


def store(lps: dict) -> dict:
    """{model|session: (te, correct, log-probabilities)} from {model|session: ensemble}, `ilc_outer`'s format."""
    out = {}
    for m, (model, sessions) in MODELS.items():
        for s in sessions:
            te = replay(model, s)["te"]
            lp = lps[f"{m}|{s}"]
            out[f"{m}|{s}"] = (te, PC.accuracy(lp, te), lp)
    return out


def cell(cells: list, st: dict) -> tuple:
    """(rows, correct, log-probabilities) of a pooled cell (`ilb_core.cell_rows_b` per part, concatenated)."""
    from pipeline.identify import ilb_core as B
    parts = [B.cell_rows_b(c, st) for c in cells]
    return tuple(np.concatenate([p[i] for p in parts]) for i in range(3))


def keys() -> list:
    return [f"{m}|{s}" for m, (_model, sessions) in MODELS.items() for s in sessions]
