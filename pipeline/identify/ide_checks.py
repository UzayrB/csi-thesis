"""ide_checks. The engine's identity-blind checks (`runs/identify/engine/PLAN.md`, sections 2.2, 2.4 and 2.5), from
the engine bank's own extraction records (`ide_bank`): the clock check, the direction detector's accuracy on
every identification walk, and the Wi-Fi speed against press speed. No model, no identity.

    PYTHONPATH=. python3 -m pipeline.identify.ide_checks
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idmax_common as IC

OUT = os.path.join(EN.ENG, "checks")


def meta(T: float = 3.0) -> list:
    return json.load(open(os.path.join(EN.ENG, f"bank_T{T:.1f}", "meta.json")))["passes"]


def direction(rows: list) -> dict:
    idc = [r for r in rows if r["kind"] == "idcap"]
    ok = np.array([r["dir_detected"] == r["path"] for r in idc], float)

    def acc(sel):
        s = [i for i, r in enumerate(idc) if sel(r)]
        return {"accuracy_pct": round(100 * float(ok[s].mean()), 2), "n": len(s), "wrong": int(len(s) - ok[s].sum())}
    out = {"all": acc(lambda r: True)}
    for d in ("B1", "B2"):
        out[d] = acc(lambda r, d=d: r["session"] == d)
    for b in ("natural", "slow", "fast"):
        out[b] = acc(lambda r, b=b: r["block"] == b)
    for p in ("A_fwd", "A_rev"):
        out[p] = acc(lambda r, p=p: r["path"] == p)
    out["RULE_detected_used"] = bool(out["all"]["accuracy_pct"] >= 95.0)
    return out


def speed(rows: list) -> dict:
    from scipy.stats import pearsonr, spearmanr
    out = {}
    for tag, sel in (("identification_all", lambda r: r["kind"] == "idcap"),
                     ("identification_natural", lambda r: r["kind"] == "idcap" and r["block"] == "natural"),
                     ("identification_slow", lambda r: r["kind"] == "idcap" and r["block"] == "slow"),
                     ("identification_fast", lambda r: r["kind"] == "idcap" and r["block"] == "fast"),
                     ("tracking_all_information", lambda r: r["kind"] == "track")):
        s = [r for r in rows if sel(r)]
        v = np.array([r["wifi_speed"] for r in s], float)
        p = np.array([r["press_speed_m_s"] for r in s], float)
        ok = np.isfinite(v)
        d = {"n": len(s), "nan": int((~ok).sum())}
        if ok.sum() > 2:
            d.update({"pearson": round(float(pearsonr(v[ok], p[ok])[0]), 3),
                      "spearman": round(float(spearmanr(v[ok], p[ok])[0]), 3),
                      "median_abs_error_m_s": round(float(np.median(np.abs(v[ok] - p[ok]))), 3),
                      "median_ratio_wifi_over_press": round(float(np.median(v[ok] / p[ok])), 3),
                      "wifi_median_m_s": round(float(np.median(v[ok])), 3), "press_median_m_s": round(float(np.median(p[ok])), 3),
                      "distinct_wifi_values": int(len(np.unique(np.round(v[ok], 6))))})
        out[tag] = d
    return out


def run() -> dict:
    rows = meta(3.0)
    clock = json.load(open(os.path.join(OUT, "clock.json")))
    res = {"label": EN.LABEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "T": 3.0,
           "clock": {k: clock[k] for k in ("engine_windows_T3.0_at_decision", "every_frame_at_arrival_0.5s",
                                           "wraps_total", "reboots_total")},
           "direction": direction(rows), "wifi_speed": speed(rows),
           "wait_after_window_s": {"median": round(float(np.median([r["wait_s"] for r in rows])), 4),
                                   "p90": round(float(np.percentile([r["wait_s"] for r in rows], 90)), 4),
                                   "max": round(float(np.max([r["wait_s"] for r in rows])), 4),
                                   "at_cap": int(sum(r["wait_s"] >= EN.CAP_S - 1e-9 for r in rows))},
           "extract_s": {"median": round(float(np.median([r["extract_s"] for r in rows])), 3),
                         "p95": round(float(np.percentile([r["extract_s"] for r in rows], 95)), 3)},
           "information_other_T": {f"T{T}": {"direction": direction(meta(T))["all"]} for T in (2.5, 3.5)}}
    txt = json.dumps(res, indent=1)
    assert IC.no_names(txt)
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "checks.json"), "w").write(txt)
    print(txt)
    return res


if __name__ == "__main__":
    run()
    sys.exit(0)
