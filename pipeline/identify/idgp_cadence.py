"""idgp_cadence. IDGP items 2 and 3: S_csi validation, cadence reliability, the geometry sanity check.

S_csi (section 2). Its correlation with S_se and its timing error, pooled and on the training side of
each LOSO fold. GPu runs only if r >= 0.8 on every fold's training side (the queue's fixed rule).

CADENCE (section 3), per margin (0 and 0.5 s):
  person ICC over passes    one-way ICC(1) of per-pass cadence grouped by person, all sessions pooled;
                            the definition behind the earlier 0.018 (id19_audit part 3)
  person ICC across days    the same on per-(person, session) medians: does a person's day repeat?
  recording ICC             grouped by person-session, for reference: the recording's own share
  link disagreement         per pass, the range of the per-link cadences, median over passes
  r with S_se               pace from walk start and end
  strides per segment       duration x cadence / 2, median
The margin is chosen per LOSO fold by the TRAINING-side person ICC, never by accuracy.

GEOMETRY SANITY CHECK (section 4). On A_fwd, the slope of each link's torso contour against walk
progress, RAW and CORRECTED. The correction is doing its job only if it flattens the trend.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

from pipeline.identify import idmax_common as IC

STAGE = "idgp_cadence"
BANK = os.path.join("runs", "identify", "idgp")
OUT = os.path.join(BANK, STAGE)
LOSO = {"s0102_to_s03": ("01", "02"), "s0103_to_s02": ("01", "03"), "s0203_to_s01": ("02", "03")}


def load_bank(margin: float) -> dict:
    d = np.load(os.path.join(BANK, f"bank_m{margin}.npz"), allow_pickle=False)
    names = [str(x) for x in d["names"]]
    return {"X": d["X"], "names": names, "col": {n: j for j, n in enumerate(names)},
            "keys": [str(k) for k in d["keys"]]}


def icc1(values: np.ndarray, groups: np.ndarray) -> float:
    ok = np.isfinite(values)
    v, g = values[ok], groups[ok]
    u = np.unique(g)
    if len(u) < 2:
        return np.nan
    n_i = np.array([np.sum(g == x) for x in u], float)
    means = np.array([v[g == x].mean() for x in u])
    grand = v.mean()
    msb = np.sum(n_i * (means - grand) ** 2) / (len(u) - 1)
    msw = np.sum([np.sum((v[g == x] - v[g == x].mean()) ** 2) for x in u]) / (len(v) - len(u))
    k = (len(v) - np.sum(n_i ** 2) / len(v)) / (len(u) - 1)
    return float((msb - msw) / (msb + (k - 1) * msw))


def reliability(B: dict, M: dict, rows: np.ndarray) -> dict:
    X, c = B["X"], B["col"]
    cad = X[rows, c["P|rhy|-|fu|cadence_hz"]]
    y, sess = M["y"][rows], M["session"][rows]
    rec = np.array([f"{a}|{b}" for a, b in zip(y, sess)])
    links = np.column_stack([X[rows, c[f"{L}|diag|-|-|cad_link_hz"]] for L in ("RX1", "RX2", "RX3")])
    rng = np.array([np.ptp(r[np.isfinite(r)]) if np.isfinite(r).sum() >= 2 else np.nan for r in links])
    day = {}
    for p in np.unique(y):
        for s in np.unique(sess):
            m = (y == p) & (sess == s) & np.isfinite(cad)
            if m.any():
                day[(p, s)] = float(np.median(cad[m]))
    dv = np.array(list(day.values()))
    dg = np.array([k[0] for k in day])
    sp = M["S_se"][rows]
    ok = np.isfinite(cad)
    out = {"n": int(len(rows)), "n_resolved": int(ok.sum()),
           "person_icc_passes": round(icc1(cad, y), 3),
           "person_icc_days": round(icc1(dv, dg), 3),
           "recording_icc": round(icc1(cad, rec), 3),
           "link_disagreement_median_hz": round(float(np.nanmedian(rng)), 3),
           "r_with_S_se": round(float(np.corrcoef(cad[ok], sp[ok])[0, 1]), 3),
           "strides_per_segment_median": round(float(np.nanmedian(
               X[rows, c["P|diag|-|-|n_strides"]])), 2),
           "cadence_p10_p50_p90_hz": np.round(np.nanpercentile(cad, [10, 50, 90]), 3).tolist(),
           "sources_kept_median": float(np.nanmedian(X[rows, c["P|diag|-|-|n_kept"]])),
           "per_link_person_icc": {L: round(icc1(links[:, i], y), 3)
                                   for i, L in enumerate(("RX1", "RX2", "RX3"))}}
    return out


def meta() -> dict:
    from pipeline.identify.idgp_contract import path_length
    inv = IC.pass_inventory()
    return {"inv": inv, "y": np.array([r["anon"] for r in inv]),
            "session": np.array([r["session"] for r in inv]),
            "line": np.array([r["line"] for r in inv]),
            "S_se": np.array([path_length(r["line"]) / (r["t_end_press"] - r["t_start_press"])
                              for r in inv])}


def main() -> int:
    IC.job_start(STAGE)
    M = meta()
    out = {"stage": STAGE, "LABEL": "EXPLORATORY (Room A reopened, decision 11)"}
    # ---- S_csi
    sc = json.load(open(os.path.join(BANK, "scsi.json")))
    keys = [IC.pass_key(r) for r in M["inv"]]
    s_csi = np.array([sc[k]["S_csi"] if sc[k]["S_csi"] is not None else np.nan for k in keys])
    e_on = np.array([sc[k].get("err_onset_s", np.nan) for k in keys], float)
    e_off = np.array([sc[k].get("err_offset_s", np.nan) for k in keys], float)
    ok = np.isfinite(s_csi)
    folds = {}
    for tag, tr in LOSO.items():
        m = ok & np.isin(M["session"], tr)
        folds[tag] = round(float(np.corrcoef(s_csi[m], M["S_se"][m])[0, 1]), 3)
    valid = all(v >= 0.8 for v in folds.values())
    out["S_csi"] = {"r_with_S_se_training_side": folds,
                    "r_with_S_se_all": round(float(np.corrcoef(s_csi[ok], M["S_se"][ok])[0, 1]), 3),
                    "r_with_S_se_A_fwd": round(float(np.corrcoef(
                        s_csi[ok & (M["line"] == "A_fwd")], M["S_se"][ok & (M["line"] == "A_fwd")])[0, 1]), 3),
                    "onset_error_s_p25_p50_p75": np.round(np.nanpercentile(e_on, [25, 50, 75]), 2).tolist(),
                    "offset_error_s_p25_p50_p75": np.round(np.nanpercentile(e_off, [25, 50, 75]), 2).tolist(),
                    "abs_duration_error_s_median": round(float(np.nanmedian(np.abs(e_off - e_on))), 2),
                    "n_detected": int(ok.sum()),
                    "VALIDATED": bool(valid),
                    "verdict": ("validated: GPu runs as a secondary row" if valid else
                                "FAILED the r >= 0.8 rule on the training side: GPu is dropped")}
    # ---- cadence reliability
    out["cadence"] = {}
    out["margin_choice"] = {}
    for m in (0.0, 0.5):
        B = load_bank(m)
        allr = np.arange(len(M["y"]))
        out["cadence"][f"m{m}"] = {"all_lines": reliability(B, M, allr),
                                   "A_fwd": reliability(B, M, allr[M["line"] == "A_fwd"])}
    for tag, tr in LOSO.items():
        rows = np.flatnonzero(np.isin(M["session"], tr))
        icc = {m: icc1(load_bank(m)["X"][rows, load_bank(m)["col"]["P|rhy|-|fu|cadence_hz"]],
                       M["y"][rows]) for m in (0.0, 0.5)}
        out["margin_choice"][tag] = {"training_person_icc": {f"m{k}": round(v, 3) for k, v in icc.items()},
                                     "margin_s": 0.0 if icc[0.0] >= icc[0.5] else 0.5}
    out["cadence"]["earlier_id19_csi_only"] = {"person_icc_passes": 0.018, "link_disagreement_median_hz": 0.60,
                                               "source": "runs/identify/idmax/id19_audit/results.json"}
    best = max(out["cadence"][f"m{m}"]["all_lines"]["person_icc_passes"] for m in (0.0, 0.5))
    out["cadence"]["BELOW_0.2"] = bool(best < 0.2)
    out["cadence"]["statement"] = (
        "cadence ICC stays below 0.2: every cadence-derived parameter inherits that weakness"
        if best < 0.2 else "cadence ICC reaches 0.2 or more")
    # ---- geometry sanity check
    B = load_bank(0.0)
    X, c = B["X"], B["col"]
    geo = {}
    for line in ("A_fwd", "all"):
        rows = np.arange(len(M["y"])) if line == "all" else np.flatnonzero(M["line"] == line)
        g = {}
        for L in ("RX1", "RX2", "RX3"):
            tr_raw = X[rows, c[f"{L}|diag|raw|-|trend"]]
            tr_cor = X[rows, c[f"{L}|diag|cor|-|trend"]]
            g[L] = {"median_trend_raw": round(float(np.nanmedian(tr_raw)), 3) if np.isfinite(tr_raw).any() else None,
                    "median_trend_cor": round(float(np.nanmedian(tr_cor)), 3) if np.isfinite(tr_cor).any() else None,
                    "median_abs_trend_raw": round(float(np.nanmedian(np.abs(tr_raw))), 3) if np.isfinite(tr_raw).any() else None,
                    "median_abs_trend_cor": round(float(np.nanmedian(np.abs(tr_cor))), 3) if np.isfinite(tr_cor).any() else None,
                    "mean_F": round(float(np.nanmean(X[rows, c[f"{L}|diag|-|-|mean_F"]])), 3),
                    "frac_frames_masked": round(float(np.nanmean(X[rows, c[f"{L}|diag|-|-|frac_masked"]])), 3)}
            if g[L]["median_abs_trend_cor"] is not None:
                g[L]["FLATTENED"] = bool(g[L]["median_abs_trend_cor"] < g[L]["median_abs_trend_raw"])
        geo[line] = g
    # the prediction: on A_fwd, F on RX2 and RX3 runs 0.18 to 0.82, so the raw contour should rise
    from pipeline.identify.idgp_contract import RIG_ROOM_A
    from pipeline.identify.idgp_signal import frame_F
    from pipeline.identify.idgp_contract import ContractPass
    cp = ContractPass(amp=np.zeros((3, 10, 1), np.float32), fs=150.0, t_start=0.0, t_end=1.0, t_amp0=0.0,
                      path_id="A_fwd", path_length_m=5.0, rig=tuple(sorted(RIG_ROOM_A.items())))
    u = np.linspace(0, 1, 101)
    Fp = frame_F(cp, "RX3", u)
    geo["A_fwd_predicted_raw_trend_RX3"] = round(float(np.polyfit(u, Fp / Fp.mean(), 1)[0]), 3)
    geo["verdict"] = ("the correction flattens the along-walk trend" if all(
        geo["A_fwd"][L].get("FLATTENED") for L in ("RX2", "RX3")) else
        "the correction does NOT flatten the trend on A_fwd: the geometry model does not describe "
        "the torso contour on this rig")
    out["geometry_sanity"] = geo
    IC.save_json(os.path.join(OUT, "results.json"), out)
    IC.status(STAGE, json.dumps({"S_csi": out["S_csi"]["verdict"], "margin": out["margin_choice"],
                                 "icc": {k: v["all_lines"]["person_icc_passes"] for k, v in out["cadence"].items()
                                         if k.startswith("m")}, "geo": geo["verdict"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
