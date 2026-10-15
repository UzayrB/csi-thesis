"""ils_extract. The lever screen's Tier 0.2 and 0.5 (PLAN note 2026-10-01 17:18): the identification walks re-extracted
with the engine's own Extractor (as `ixt_cadfix.real_walks`), to find how often the v2 cadence resolver's fallback
fires and what it resolves to, and how often the 3 s window holds a 50 ms bin with no packet. Also fix F's bank
(only if the fallback is confirmed to reproduce the bug): every window's features re-extracted with "no qualifying
channel means no rhythm", into a bank beside the old one.

    PYTHONPATH=. python3 -m pipeline.identify.ils_extract walks      # Tier 0.2 and 0.5
    PYTHONPATH=. python3 -m pipeline.identify.ils_extract fixF       # fix F's bank (bug confirmed only)

Development evaluation, all data seen. Report only; the engine does not change.
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idmax_features as F
from pipeline.identify import ils_common as IL

EDGE = (0.80, 0.88)          # an estimate at the 0.8 Hz band-pass edge; doubled, 1.60 to 1.76 Hz
BIN_S = 0.05


class TapT(EN.Extractor):
    """The engine's Extractor, keeping each decided window's raw amplitude and its timed frames."""

    def poll(self, now, closing=False):
        from pipeline.identify.ixa_data import window_raw
        for r in self.rx.values():
            r.consolidate(trim_before=self.newest - EN.KEEP_S)
        out = []
        while self.pending:
            w = self.pending[0]
            td = self._t_dec(w, np.inf if closing else now)
            if td is None:
                break
            A = window_raw(self, w, td)
            timed = [self.rx[L].timed(td) for L in EN.LINKS]
            x = EN.extract_window(timed, w["t0"], self.T, self.amp_norm, w["path"], w["layout"], self.names) \
                if w["info"].get("features") else None
            self.pending.pop(0)
            out.append((w, td, A, timed, x))
        return out


def _windows(only_idcap: bool, features: bool):
    """Every pass in bank order (`idx_bank.recordings()`), re-extracted; yields (bank row, A, timed, features)."""
    from pipeline.identify import idx_bank as B
    from pipeline.io.capture_logger import read_capture_file
    d = IL.data()
    k = 0
    for rec in B.recordings():
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        qs = sorted(gt["passes"], key=lambda q: q["t_start"])
        if only_idcap and rec["kind"] != "idcap":
            k += len(qs)
            continue
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        ex = TapT(T=3.0, layout="id_spot" if rec["kind"] == "idcap" else "home", names=d["names"])
        pos = {L: 0 for L in EN.LINKS}
        for q in qs:
            t0 = float(q["t_start"])
            assert abs(d["meta"][k]["t_start"] - t0) < 1e-6
            lim = t0 + 3.0 + EN.CAP_S
            for L in EN.LINKS:
                n = int(np.searchsorted(fr[L]["t_mono"], lim, side="right"))
                ex.push(L, fr[L][pos[L]:n])
                pos[L] = n
            ex.press(t0, path=d["meta"][k]["engine_path"], info={"features": features})
            (_w, td, A, timed, x), = ex.poll(lim)
            assert abs(td - d["meta"][k]["t_dec"]) < 1e-9
            yield k, t0, A, timed, x
            k += 1


def _edge_doubled(sets: list, rate) -> bool:
    if rate is None:
        return False
    raw = [v for e in sets for kk in ("welch", "acf_cycle", "peaks") for v in [e.get(kk)]
           if v is not None and EDGE[0] <= v <= EDGE[1]]
    return any(abs(rate - 2 * v) <= 0.1 for v in raw)


def walks() -> dict:
    """Tier 0.2 on the 180 natural walks and Tier 0.5 on every identification walk."""
    from pipeline.identify import ixt_synth as S
    from pipeline.identify.id19_featbank import CADENCE_CH
    d = IL.data()
    ci = d["names"].index("cad|all|-|-|cadence_hz")
    rows, gaps, t = [], [], time.time()
    for k, t0, A, timed, _x in _windows(only_idcap=True, features=False):
        edges = t0 + BIN_S * np.arange(61)
        empty = np.array([np.histogram(tt[(tt >= t0) & (tt < t0 + 3.0)], bins=edges)[0] == 0 for tt, _a, _r in timed])
        gaps.append({"row": k, "block": d["meta"][k]["block"], "session": d["meta"][k]["session"],
                     "empty_all3": int(empty.all(0).sum()), "empty_per_rx": [int(e.sum()) for e in empty],
                     "longest_gap_s_per_rx": [round(float(np.diff(np.r_[t0, np.sort(tt[(tt >= t0) & (tt < t0 + 3.0)]),
                                                                         t0 + 3.0]).max()), 4) for tt, _a, _r in timed]})
        if d["meta"][k]["block"] != "natural":
            continue
        sets = [F.cadence_estimates(F.reduce_link(A[li], band, red)[0]) for li in range(3) for red, band in CADENCE_CH]
        strong = [e for e in sets if e.get("acf_peak") is not None and e["acf_peak"] >= EN.CADENCE_VOTE_MIN_ACF]
        v2 = EN.resolve_cadence_v2(sets)["cadence_hz"]
        per = []
        for li in range(3):
            s3 = sets[3 * li:3 * li + 3]
            st3 = [e for e in s3 if e.get("acf_peak") is not None and e["acf_peak"] >= EN.CADENCE_VOTE_MIN_ACF]
            r3 = EN.resolve_cadence_v2(s3)["cadence_hz"]
            per.append({"strong": len(st3), "fallback": not st3, "rate": r3, "edge_doubled": (not st3) and _edge_doubled(s3, r3)})
        env, how = S.envelope_cadence(A[1])
        rows.append({"row": k, "session": d["meta"][k]["session"], "who": IL.NAME[d["meta"][k]["anon"]],
                     "strong": len(strong), "fallback": not strong, "rate_v2": v2,
                     "bank_rate": float(d["X"][k, ci]) if np.isfinite(d["X"][k, ci]) else None,
                     "rate_all_vote": EN._RESOLVE_V1(sets)["cadence_hz"],
                     "edge_doubled": (not strong) and _edge_doubled(sets, v2),
                     "acf_peaks": [None if e.get("acf_peak") is None else round(e["acf_peak"], 3) for e in sets],
                     "envelope": env, "envelope_clear": how != "none", "per_link": per})
    print(f"{time.strftime('%H:%M:%S')} re-extracted {len(gaps)} identification windows ({time.time() - t:.0f} s)", flush=True)
    anchor = sum(1 for r in rows if r["bank_rate"] is not None and r["rate_v2"] is not None     # the bank is float32
                 and abs(r["bank_rate"] / r["rate_v2"] - 1) < 1e-6)
    fb = [r for r in rows if r["fallback"]]
    clear = [r for r in fb if r["envelope_clear"]]
    nat = [g for g in gaps if g["block"] == "natural"]
    summ = {
        "label": IL.LABEL,
        "anchor_rate_equals_bank": f"{anchor} of {len(rows)}",
        "natural_walks": len(rows),
        "fallback_fires": len(fb), "fallback_pct": round(100 * len(fb) / len(rows), 2),
        "fallback_rate_at_doubled_edge": sum(r["edge_doubled"] for r in fb),
        "fallback_by_session": {s: sum(r["fallback"] for r in rows if r["session"] == s) for s in IL.SESS},
        "fallback_by_person": {n: sum(r["fallback"] for r in rows if r["who"] == n) for n in IL.NAME.values()},
        "fallback_rates_hz": sorted(round(r["rate_v2"], 3) for r in fb if r["rate_v2"] is not None),
        "fallback_envelope_clear": len(clear),
        "fallback_ratio_to_envelope_median": (round(float(np.median([r["rate_v2"] / r["envelope"] for r in clear])), 3)
                                              if clear else None),
        "strong_channels_distribution": {int(v): sum(r["strong"] == v for r in rows) for v in range(10)},
        "per_link_fallback": {L: sum(r["per_link"][i]["fallback"] for r in rows) for i, L in enumerate(EN.LINKS)},
        "per_link_fallback_at_doubled_edge": {L: sum(r["per_link"][i]["edge_doubled"] for r in rows)
                                              for i, L in enumerate(EN.LINKS)},
        "BUG_CONFIRMED": bool(fb) and sum(r["edge_doubled"] for r in fb) > len(fb) / 2,
        "gaps": {
            "resampler": "id19_bank._interp_cols: linear interpolation between the neighbouring frames (by causal-clock "
                         "time), clamped at the window's ends; a gap is a straight line, never zeros",
            "natural_windows": len(nat),
            "natural_windows_with_an_all3_empty_bin": sum(g["empty_all3"] > 0 for g in nat),
            "natural_all3_empty_bins_total": sum(g["empty_all3"] for g in nat),
            "natural_windows_with_an_empty_bin_per_rx": [sum(g["empty_per_rx"][i] > 0 for g in nat) for i in range(3)],
            "natural_empty_bins_per_rx_median": [float(np.median([g["empty_per_rx"][i] for g in nat])) for i in range(3)],
            "natural_longest_gap_s_per_rx_median": [float(np.median([g["longest_gap_s_per_rx"][i] for g in nat])) for i in range(3)],
            "natural_longest_gap_s_per_rx_max": [float(np.max([g["longest_gap_s_per_rx"][i] for g in nat])) for i in range(3)],
            "all_identification_windows": len(gaps),
            "all_windows_with_an_all3_empty_bin": sum(g["empty_all3"] > 0 for g in gaps),
        },
        "seconds": round(time.time() - t, 1),
    }
    IL.dump(os.path.join(IL.OUT, "tier0", "cadence_gaps.json"), {"summary": summ, "walks": rows, "gaps": gaps})
    print(json.dumps(summ, indent=1, default=float), flush=True)
    return summ


def resolve_fixF(estimate_sets: list) -> dict:
    """Fix F: only rhythm-bearing channels vote (as v2); if none qualifies there is no rhythm (no fallback)."""
    strong = [e for e in estimate_sets if e.get("acf_peak") is not None and e["acf_peak"] >= EN.CADENCE_VOTE_MIN_ACF]
    if not strong:
        return {"cadence_hz": None, "agree_frac": 0.0, "n_estimates": 0}
    return EN._RESOLVE_V1(strong)


def fixF() -> dict:
    """Every window's features with fix F, beside the old bank (`runs/identify/lever_screen/bank_T3.0_cadF`)."""
    out = os.path.join(IL.OUT, "bank_T3.0_cadF")
    p = os.path.join(out, "features.npy")
    assert not os.path.exists(p), f"{p} exists: never overwritten"
    saved = EN.resolve_cadence_v2
    EN.resolve_cadence_v2 = resolve_fixF            # `_cadence_v2` installs this name at each extraction
    t, feats = time.time(), []
    try:
        for k, _t0, _A, _timed, x in _windows(only_idcap=False, features=True):
            feats.append(x["features"])
            if k % 100 == 0:
                print(f"{time.strftime('%H:%M:%S')} fixF {k} ({time.time() - t:.0f} s)", flush=True)
    finally:
        EN.resolve_cadence_v2 = saved
    X = np.asarray(feats, np.float32)
    os.makedirs(out, exist_ok=True)
    np.save(p, X)
    old = np.load(os.path.join(IL.data()["bank"], "features.npy"))
    changed = int((~np.all(np.isclose(X, old, equal_nan=True), axis=1)).sum())
    rec = {"label": IL.LABEL, "fix": "no qualifying channel (acf peak >= 0.30) means no rhythm: cadence None",
           "n": int(len(X)), "windows_changed": changed, "seconds": round(time.time() - t, 1)}
    IL.dump(os.path.join(out, "build.json"), rec)
    print(rec, flush=True)
    return rec


if __name__ == "__main__":
    sys.exit(0 if {"walks": walks, "fixF": fixF}[sys.argv[1]]() else 1)
