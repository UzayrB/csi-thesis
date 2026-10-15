"""ilb_p2. The best-model run's P2, the tracker's speed (`runs/identify/best/POA_B.md`, dated notes): for each path walk,
from the tracker's existing replay logs (no new decode), the least-squares slope of the dot's distance along the locked
line against frame time, over the dot frames after the anchor ends (the lock's t_dec0) and computed by the
identification decision time (the bank's t_dec). Fewer than 5 such frames, no lock by t_dec, or a slope outside 0.5 to 2.5
m/s: the Wi-Fi speed is kept (counted). Identification walks keep the Wi-Fi speed.

Sources (each walk's tracker never trained on that walk's session):
- A1, A2, B1: `runs/a3_clean_2026-10-08/dot/stage1/multi/h-heldout_.../` (the rotation, trackers on the other two);
- A3: `runs/live/replay/final/semi_disp-K1g_causal_realtime_screen/03__*` (f05_A3: A1+A2+B1);
- B2: the same directory's `B2__*` (f05_B2: A1+A2+B1; identical dots to the non-screen run), and for xr_A, the zero-shot
  tracker `runs/live/replay/zeroshot/semi_disp-K1g_causal/B2__*` (z05_B2: A1+A2).

    PYTHONPATH=. python3 -m pipeline.identify.ilb_p2 quality     # the speed error against the stopwatch first

Exploratory development, all data seen; selection on A3 and B2.
"""

from __future__ import annotations

import glob
import json
import os
import sys
import time

import numpy as np

from pipeline.identify import engine as EN

BD = os.path.join("runs", "identify", "best")
STAGE1 = os.path.join("runs", "a3_clean_2026-10-08", "dot", "stage1", "multi", "h-heldout_f0.5_o0.375_s0.5_sw-off_sd3_soft1")
FINAL = os.path.join("runs", "live", "replay", "final", "semi_disp-K1g_causal_realtime_screen")
ZERO = os.path.join("runs", "live", "replay", "zeroshot", "semi_disp-K1g_causal")
SOURCES = {"A1": (STAGE1, "01", ("A2", "B1")), "A2": (STAGE1, "02", ("A1", "B1")), "B1": (STAGE1, "B1", ("A1", "A2")),
           "A3": (FINAL, "03", ("A1", "A2", "B1")), "B2": (FINAL, "B2", ("A1", "A2", "B1")),
           "B2z": (ZERO, "B2", ("A1", "A2"))}
MIN_FRAMES = 5
LO, HI = 0.5, 2.5
_S = {}


def _logs(src: str) -> dict:
    """{press time: (pid, dots [(x, computed_at, xy)], locks [(at, line, t_dec0)])} for one source."""
    d, pre, _tr = SOURCES[src]
    out = {}
    for f in sorted(glob.glob(os.path.join(d, f"{pre}__participant_*.jsonl"))):
        rows = [json.loads(l) for l in open(f)]
        press = {r["pid"]: r["t"] for r in rows if r["kind"] == "press"}
        for pid, t in press.items():
            out[round(t, 6)] = {"pid": pid, "file": os.path.basename(f),
                                "dots": [(r["x"], r.get("computed_at", r["x"]), r["xy"]) for r in rows
                                         if r["kind"] == "dot" and r["pid"] == pid],
                                "locks": [(r["at"], r["line"], r["t_dec0"]) for r in rows
                                          if r["kind"] == "lock" and r["pid"] == pid]}
    return out


def speeds(src: str) -> dict:
    """{bank row: (speed or nan, reason)} for the path walks of the source's session."""
    if src in _S:
        return _S[src]
    from pipeline.identify.idgp_contract import PATHS
    meta = json.load(open(os.path.join(EN.bank_dir(4.0), "meta.json")))["passes"]
    sess = "B2" if src == "B2z" else src
    logs = _logs(src)
    out = {}
    for k, m in enumerate(meta):
        if m["session"] != sess or m["kind"] != "track":
            continue
        L = logs.get(round(m["t_start"], 6))
        if L is None:
            out[k] = (np.nan, "no press in the log")
            continue
        td = m["t_dec"]
        locks = [x for x in L["locks"] if x[0] <= td]
        if not locks:
            out[k] = (np.nan, "no lock by t_dec")
            continue
        _at, line, t0 = locks[-1]
        a, b = (np.asarray(p, float) for p in PATHS[line])
        u = (b - a) / np.linalg.norm(b - a)
        fr = [(x, float(np.dot(np.asarray(xy, float) - a, u))) for x, ca, xy in L["dots"] if x > t0 and ca <= td]
        if len(fr) < MIN_FRAMES:
            out[k] = (np.nan, f"{len(fr)} frames")
            continue
        x, s = np.array(fr).T
        v = float(np.polyfit(x - x[0], s, 1)[0])
        out[k] = (v, "ok") if LO <= v <= HI else (np.nan, f"slope {v:.2f} outside {LO} to {HI}")
    _S[src] = out
    return out


def trackers(model: str) -> dict:
    """The sessions each tracker behind a model's P2 column trained on: its training rows' and each test session's."""
    from pipeline.identify import ilc_outer as CO
    from pipeline.identify import ilp_cand as PC
    tr = np.load(os.path.join(CO.mdir(model), "train_rows.npy"))
    ts = sorted(str(x) for x in set(PC.bank()["a"]["session"][tr]))
    m = [k for k, (mm, _s) in CO.MODELS.items() if mm == model][0]
    tests = CO.MODELS[m][1]
    src = lambda s: "B2z" if (s == "B2" and model == "xr_A_v4") else s
    return {"training": {s: list(SOURCES[src(s)][2]) for s in ts},
            "test": {s: {"source": src(s), "tracker_trained_on": list(SOURCES[src(s)][2])} for s in tests}}


def pace_column(model: str, v: np.ndarray, flags: list) -> np.ndarray:
    """The pace column under P2 for one model: every path walk's tracker speed (B2 from the zero-shot tracker for xr_A),
    the Wi-Fi speed `v` kept where P2 has none. Appends the trackers' sessions, and for xr_A and xr_B1 the label "not
    zero-shot: the tracker saw <sessions>", to `flags`."""
    out = v.copy()
    n_fb = 0
    for s in ("A1", "A2", "A3", "B1", "B2"):
        src = "B2z" if (s == "B2" and model == "xr_A_v4") else s
        for k, (sp, _why) in speeds(src).items():
            if np.isfinite(sp):
                out[k] = sp
            else:
                n_fb += 1
    tk = trackers(model)
    flags.append(f"{model}: P2 trackers: training rows {tk['training']}; test {tk['test']}; {n_fb} path walks keep the "
                 f"Wi-Fi speed")
    if model in ("xr_A_v4", "xr_B1_v4"):
        saw = sorted(set(x for v_ in tk["training"].values() for x in v_) |
                     set(x for t in tk["test"].values() for x in t["tracker_trained_on"]))
        flags.append(f"{model}: P2 cells not zero-shot: the tracker saw {', '.join(saw)}")
    return out


def quality() -> dict:
    """Each source: P2 against the stopwatch (press speed) on its path walks, beside the Wi-Fi speed; the fallbacks."""
    from scipy import stats
    meta = json.load(open(os.path.join(EN.bank_dir(4.0), "meta.json")))["passes"]
    res = {"label": "exploratory development, all data seen; selection on A3 and B2", "built": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "rule": {"frames": f"x > t_dec0 and computed_at <= t_dec, at least {MIN_FRAMES}", "range_m_s": [LO, HI]},
           "sources": {}}
    for src in SOURCES:
        sp = speeds(src)
        rows = np.array(sorted(sp))
        p2 = np.array([sp[k][0] for k in rows])
        why = [sp[k][1] for k in rows]
        y = np.array([meta[k]["press_speed_m_s"] for k in rows], float)
        w = np.array([meta[k]["wifi_speed"] for k in rows], float)
        ok = np.isfinite(p2)
        wf = np.where(np.isfinite(w), w, np.nanmedian(w))
        p2f = np.where(ok, p2, wf)
        res["sources"][src] = {
            "dir": SOURCES[src][0], "tracker_trained_on": list(SOURCES[src][2]), "n": int(len(rows)), "n_p2": int(ok.sum()),
            "fallbacks": {r: why.count(r) for r in sorted(set(why)) if r != "ok"},
            "P2_pearson_on_own": round(float(stats.pearsonr(p2[ok], y[ok])[0]), 3) if ok.sum() > 2 else None,
            "wifi_pearson_same_walks": round(float(stats.pearsonr(wf[ok], y[ok])[0]), 3) if ok.sum() > 2 else None,
            "P2_with_fallback_pearson": round(float(stats.pearsonr(p2f, y)[0]), 3),
            "wifi_pearson": round(float(stats.pearsonr(wf, y)[0]), 3),
            "P2_median_abs_error": round(float(np.median(np.abs(p2[ok] - y[ok]))), 3) if ok.any() else None,
            "wifi_median_abs_error_same_walks": round(float(np.median(np.abs(wf[ok] - y[ok]))), 3) if ok.any() else None,
            "P2_median": round(float(np.median(p2[ok])), 3) if ok.any() else None, "press_median": round(float(np.median(y)), 3)}
        print(src, res["sources"][src], flush=True)
    os.makedirs(BD, exist_ok=True)
    json.dump(res, open(os.path.join(BD, "p2_quality.json"), "w"), indent=1)
    return res


if __name__ == "__main__":
    if sys.argv[1] == "quality":
        quality()
    sys.exit(0)
