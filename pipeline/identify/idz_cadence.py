"""idz_cadence. Identification audit, stage 5 (`runs/identify/audit/PLAN.md` section 5): is stride or step
rhythm visible, on signals that can show it, in the natural identification walks (n 180)?

- the envelope: RX2's conditioned spectrogram (`rehearsal_doppler_check.conditioned_spectrogram`) power
  summed over 10 to 70 Hz per frame (18.75 frames per second);
- the gait-band mean channel of RX2 (`idmax_features.reduce_link(a, "b08_35", "mean")`, 150 Hz).
For each: the normalised autocorrelation of the mean-removed signal; a peak is a local maximum of at least
0.30 in the step range (0.4 to 0.7 s) or the stride range (0.8 to 1.4 s). The envelope's cadence is
1 / step lag, else 2 / stride lag; the bank's resolver agrees within 10 %.
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

from pipeline.identify import id29_dc2_score as D
from pipeline.identify import idmax_common as IC
from pipeline.identify import idmax_features as F
from pipeline.identify import idx_bank as B
from pipeline.identify import rehearsal_doppler_check as RD
from pipeline.identify.id19_bank import _interp_cols
from pipeline.identify.id19_featbank import SC

OUT = os.path.join("runs", "identify", "audit", "stage5")
THR = 0.30
STEP, STRIDE = (0.4, 0.7), (0.8, 1.4)


def acf_peak(x, fs, rng):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)] - np.nanmean(x)
    den = float(np.dot(x, x))
    if len(x) < int(rng[1] * fs) + 3 or den <= 0:
        return None, None
    ac = np.array([np.dot(x[:len(x) - k], x[k:]) / den for k in range(int(rng[1] * fs) + 2)])
    lo, hi = int(np.ceil(rng[0] * fs)), int(np.floor(rng[1] * fs))
    best, lag = -1.0, None
    for k in range(max(lo, 1), min(hi, len(ac) - 2) + 1):
        if ac[k] >= ac[k - 1] and ac[k] >= ac[k + 1] and ac[k] > best:
            best, lag = float(ac[k]), k / fs
    return (best, lag) if best >= THR else (best if best > -1 else None, None)


def run(bank_dir: str) -> dict:
    from pipeline.identify import idx_loso as L
    from pipeline.identify import idz_bank as ZB
    bank = L.load(bank_dir)
    a, names = bank["a"], np.array(bank["names"])
    cols = ZB.columns_v2(bank)
    cad_cols = [j for j in cols if names[j].split("|")[0] in ("cad", "rhy", "tplacf")]
    j_cad = int(np.flatnonzero(names == "cad|all|-|-|cadence_hz")[0])
    meta = json.load(open(os.path.join(bank_dir, "meta.json")))["passes"]
    rows = {(m["session"], round(m["t_start"], 6)): i for i, m in enumerate(meta)}
    res = []
    for rec in B.recordings():
        if rec["kind"] != "idcap" or rec["block"] != "natural":
            continue
        t, amp, _r, _c = D._link(f"{rec['stem']}_RX2.bin")
        amp = np.asarray(amp, float)[:, SC]
        for q in json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))["passes"]:
            i = rows[(rec["session"], round(float(q["t_start"]), 6))]
            seg = _interp_cols(np.arange(q["t_start"], q["t_end"], 1 / 150.0), t, amp)
            f, P = RD.conditioned_spectrogram(seg)
            env = P[(f >= 10) & (f <= 70)].sum(axis=0)
            gb = F.reduce_link(seg, "b08_35", "mean")[0]
            e_step, e_step_lag = acf_peak(env, 150 / 8.0, STEP)
            e_str, e_str_lag = acf_peak(env, 150 / 8.0, STRIDE)
            g_step, g_step_lag = acf_peak(gb, 150.0, STEP)
            g_str, g_str_lag = acf_peak(gb, 150.0, STRIDE)
            env_cad = 1 / e_step_lag if e_step_lag else (2 / e_str_lag if e_str_lag else None)
            rc = float(bank["X"][i, j_cad])
            res.append({"row": i, "path": q["path_name"], "env_step": e_step_lag is not None, "env_stride": e_str_lag is not None,
                        "gb_step": g_step_lag is not None, "gb_stride": g_str_lag is not None, "env_cad": env_cad,
                        "resolver_cad": rc if np.isfinite(rc) else None,
                        "cad_nan_frac": float(np.mean(~np.isfinite(bank["X"][i, cad_cols])))})
    n = len(res)
    env_clear = [r for r in res if r["env_step"] or r["env_stride"]]
    agree = [r for r in env_clear if r["resolver_cad"] is not None and r["env_cad"] is not None
             and abs(r["resolver_cad"] - r["env_cad"]) <= 0.1 * r["env_cad"]]
    fail = [r for r in env_clear if r["resolver_cad"] is None]
    summ = {"n": n,
            "envelope": {"step_peak": round(np.mean([r["env_step"] for r in res]), 3), "stride_peak": round(np.mean([r["env_stride"] for r in res]), 3),
                         "either": round(len(env_clear) / n, 3)},
            "gait_band_mean": {"step_peak": round(np.mean([r["gb_step"] for r in res]), 3), "stride_peak": round(np.mean([r["gb_stride"] for r in res]), 3),
                               "either": round(np.mean([r["gb_step"] or r["gb_stride"] for r in res]), 3)},
            "resolver_vs_envelope_among_envelope_clear": {"n": len(env_clear), "agree": len(agree), "resolver_nan": len(fail),
                                                          "disagree_or_fail_frac": round(1 - len(agree) / max(len(env_clear), 1), 3)},
            "resolver_nan_frac_all": round(np.mean([r["resolver_cad"] is None for r in res]), 3),
            "cadence_feature_nan_frac": {"median": round(float(np.median([r["cad_nan_frac"] for r in res])), 3),
                                         "p90": round(float(np.percentile([r["cad_nan_frac"] for r in res], 90)), 3),
                                         "mean": round(float(np.mean([r["cad_nan_frac"] for r in res])), 3)}}
    summ["C1_GATE"] = bool(summ["envelope"]["either"] >= 0.5 and summ["resolver_vs_envelope_among_envelope_clear"]["disagree_or_fail_frac"] >= 0.25)
    doc = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "label": "development evaluation, all data seen", "summary": summ, "passes": res}
    os.makedirs(OUT, exist_ok=True)
    txt = json.dumps(doc, indent=1, default=float)
    assert IC.no_names(txt)
    open(os.path.join(OUT, "cadence.json"), "w").write(txt)
    print(json.dumps(summ, indent=1))
    return summ


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else os.path.join("runs", "identify", "audit", "bank_v2"))
    sys.exit(0)
