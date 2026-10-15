"""ilb_p1. The best-model run's P1, a learned path-walk speed (`runs/identify/best/POA_B.md`, section 2): per walk, from the
link-weighting cache (`ilw_cache`, the walking span of the model's alpha), each link's median contour, its 25th and 75th
percentiles, the median of contour / F at the nominal 1.2 m/s position, the fraction of usable frames, each link's mean
F and the route; a HistGradientBoostingRegressor (max_iter 200, learning_rate 0.05, max_depth 3, random_state 0) onto
the press speed, trained on path walks of the given sessions only.

    PYTHONPATH=. python3 -m pipeline.identify.ilb_p1 quality      # the correlation with the stopwatch per held-out session

Exploratory development, all data seen; selection on A3 and B2.
"""

from __future__ import annotations

import json
import os
import sys
import time
import warnings

import numpy as np

from pipeline.identify import engine as EN

BD = os.path.join("runs", "identify", "best")
PATHS = ("A_fwd", "A_rev", "B_fwd", "B_rev", "C_fwd", "C_rev", "D_fwd", "D_rev", "E_col1", "E_col5", "E_row1", "E_row5")
_X = {}


def features(alpha: float = 0.5) -> np.ndarray:
    """(1019, d) per-walk inputs for P1, from the cache's walking span at `alpha`."""
    if alpha in _X:
        return _X[alpha]
    from pipeline.identify import ilw_cache as LC
    from pipeline.identify import ilw_gate as G
    from pipeline.identify.idgp_contract import path_length
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    meta = json.load(open(os.path.join(EN.bank_dir(4.0), "meta.json")))["passes"]
    rows = []
    for r in LC.load_all():
        m = meta[r["row"]]
        sp = r["spans"][alpha]
        ep = m["engine_path"]
        f = []
        if any(sp["links"][L] is None for L in EN.LINKS):
            f = [np.nan] * (5 * 3)
        else:
            t = sp["links"]["RX1"]["t"]
            Fk = G.F_along(ep, r["layout"], 1.2 * t / path_length(ep))
            for j, L in enumerate(EN.LINKS):
                c = sp["links"][L]["c"]
                ok = np.isfinite(c)
                okF = ok & (Fk[j] >= 0.3)
                f += [np.nanmedian(c) if ok.any() else np.nan, np.nanpercentile(c, 25) if ok.any() else np.nan,
                      np.nanpercentile(c, 75) if ok.any() else np.nan,
                      np.median(c[okF] / Fk[j][okF]) if okF.any() else np.nan, float(ok.mean())]
        f += [EN.mean_F(L, ep, r["layout"]) for L in EN.LINKS]
        f += [1.0 if ep == p else 0.0 for p in PATHS]
        rows.append(f)
    _X[alpha] = np.asarray(rows, float)
    return _X[alpha]


def regressor():
    from sklearn.ensemble import HistGradientBoostingRegressor
    return HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_depth=3, random_state=0)


def labels():
    meta = json.load(open(os.path.join(EN.bank_dir(4.0), "meta.json")))["passes"]
    return {k: np.array([m[k] for m in meta]) for k in ("session", "kind", "press_speed_m_s", "wifi_speed", "wifi_speed_a0.2")}


def pace_column(train_sessions, alpha: float) -> tuple:
    """The pace column under P1 for a model trained on `train_sessions` at `alpha`: path walks of the training sessions
    get cross-fitted predictions (a regressor trained on the other training sessions' path walks), every other path walk a
    regressor trained on all of them; identification walks keep the Wi-Fi speed. (None, reason) with one training session."""
    a = labels()
    X = features(alpha)
    wifi = a["wifi_speed" if alpha == 0.5 else f"wifi_speed_a{alpha}"].astype(float)
    ts = sorted(set(train_sessions))
    if len(ts) < 2:
        return None, "one training session: P1 cannot be cross-fitted by session; the Wi-Fi speed is kept"
    path = a["kind"] == "track"
    y = a["press_speed_m_s"].astype(float)
    v = wifi.copy()
    full = regressor().fit(X[path & np.isin(a["session"], ts)], y[path & np.isin(a["session"], ts)])
    other = path & ~np.isin(a["session"], ts)
    v[other] = full.predict(X[other])
    for s in ts:
        tr = path & np.isin(a["session"], [x for x in ts if x != s])
        te = path & (a["session"] == s)
        v[te] = regressor().fit(X[tr], y[tr]).predict(X[te])
    return v, None


def quality() -> dict:
    """Each session held out: P1 trained on the other four sessions' path walks; Pearson r with the stopwatch on the held-
    out session's path walks, beside the Wi-Fi speed's (alpha 0.5)."""
    from scipy import stats
    a = labels()
    X = features(0.5)
    y = a["press_speed_m_s"].astype(float)
    path = a["kind"] == "track"
    res = {"label": "exploratory development, all data seen; selection on A3 and B2", "sessions": {}}
    for s in ("A1", "A2", "A3", "B1", "B2"):
        tr = path & (a["session"] != s)
        te = path & (a["session"] == s)
        p = regressor().fit(X[tr], y[tr]).predict(X[te])
        w = a["wifi_speed"][te].astype(float)
        w = np.where(np.isfinite(w), w, np.nanmedian(w))
        res["sessions"][s] = {"n": int(te.sum()), "P1_pearson": round(float(stats.pearsonr(p, y[te])[0]), 3),
                              "wifi_pearson": round(float(stats.pearsonr(w, y[te])[0]), 3),
                              "P1_median_abs_error": round(float(np.median(np.abs(p - y[te]))), 3),
                              "wifi_median_abs_error": round(float(np.median(np.abs(w - y[te]))), 3)}
        print(s, res["sessions"][s], flush=True)
    res["built"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    os.makedirs(BD, exist_ok=True)
    json.dump(res, open(os.path.join(BD, "p1_quality.json"), "w"), indent=1)
    return res


if __name__ == "__main__":
    if sys.argv[1] == "quality":
        quality()
    sys.exit(0)
