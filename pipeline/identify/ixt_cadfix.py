"""ixt_cadfix. The teaching-pack addendum's AC1 found the cadence resolver biased on simulated truth (fast walks walking away
read 0.73 to 0.91 of the true step rate). This measures a candidate fix WITHOUT changing the frozen engine: the patched
resolver is installed only inside this process (`idmax_features.resolve_cadence`, which `id19_featbank` calls at run
time). Information for Uzayr, who decides; nothing here is adopted.

The fault: links whose gait-band channel holds no rhythm (autocorrelation peak 0.07 to 0.10) give estimates at the
0.8 Hz lower edge of the band-pass; `_candidates` doubles them into the step band (1.6 to 1.76 Hz) and
`resolve_cadence`'s vote counts supporters regardless of quality, so a dozen weak estimates outvote the strong ones.
The candidate fix: only channels whose autocorrelation peak is at least 0.30 (the cadence diagnostic's threshold for
clear rhythm) vote; if none qualifies, every channel votes as today.

    PYTHONPATH=. python3 -m pipeline.identify.ixt_cadfix
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

from pipeline.identify import idmax_features as F

OUT = os.path.join("runs", "identify", "teaching", "synth_grid")
ORIGINAL = F.resolve_cadence
THR = 0.30


def resolve_fixed(estimate_sets: list) -> dict:
    strong = [e for e in estimate_sets if e.get("acf_peak") is not None and e["acf_peak"] >= THR]
    r = ORIGINAL(strong if strong else estimate_sets)
    r["voters"] = len(strong) if strong else len(estimate_sets)
    return r


def grid(patched: bool) -> list:
    from pipeline.identify import ixt_synth as S
    from pipeline.identify import idz_audit as Z
    from pipeline.identify import idz_synth as ZS
    from pipeline.identify import engine as EN
    from pipeline.io.capture_logger import read_capture_file
    F.resolve_cadence = resolve_fixed if patched else ORIGINAL
    rec = ZS.source_recording()
    gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
    t0 = float(sorted(gt["passes"], key=lambda q: q["t_start"])[0]["t_start"])
    base = {}
    for L in EN.LINKS:
        _h, fr = read_capture_file(f"{rec['stem']}_{L}.bin")
        keep = (fr["t_mono"] >= t0 - 25.0) & (fr["t_mono"] <= t0 + 12.0)
        th, _lt = Z.corrected_time(fr)
        base[L] = (fr[keep].copy(), th[keep] - t0)
    out = []
    for step in S.STEPS:
        for v0 in S.SPEEDS:
            for d in S.DIRS:
                frames = {}
                for L in EN.LINKS:
                    fr, tr = base[L]
                    fr = fr.copy()
                    fr["data"] = S.payload(tr, ZS.F_LINK[L], step, v0, d)
                    frames[L] = fr
                r = S.one(step, v0, d, {"t0": t0, "frames": frames})
                out.append(r["engine_3s_window"]["resolver_over_true"])
    F.resolve_cadence = ORIGINAL
    return out


def worked_walks() -> dict:
    from pipeline.identify import engine as EN
    from pipeline.identify import ixt_walk as XW
    from pipeline.identify import id19_featbank as FB
    import pickle
    sel = json.load(open(os.path.join("runs", "identify", "teaching", "selection.json")))
    bdir = os.path.join(EN.ENG, "bank_T3.0")
    meta = json.load(open(os.path.join(bdir, "meta.json")))["passes"]
    X = np.load(os.path.join(bdir, "features.npy"))
    maps = pickle.load(open(os.path.join(bdir, "maps.pkl"), "rb"))
    names = json.load(open(EN.DEV_NAMES))
    cols = EN.v2_columns(names)
    out = {}
    for role in ("wrong", "right"):
        w = sel[role]
        row = int(w["row"])
        stem = os.path.join("runs", "identify", "dc2_src_relabelled", "identification", "session_02", w["recording"])
        ext = XW.extract(stem, float(meta[row]["t_start"]), row, meta[row], X, maps)
        F.resolve_cadence = ORIGINAL
        f0 = FB.pass_features(ext["A"], ext["R"])
        F.resolve_cadence = resolve_fixed
        f1 = FB.pass_features(ext["A"], ext["R"])
        F.resolve_cadence = ORIGINAL
        v0 = np.array([f0.get(names[j], np.nan) if f0.get(names[j]) is not None else np.nan for j in cols], float)
        v1 = np.array([f1.get(names[j], np.nan) if f1.get(names[j]) is not None else np.nan for j in cols], float)
        same = (np.isclose(v0, v1, rtol=1e-9, atol=1e-12)) | (~np.isfinite(v0) & ~np.isfinite(v1))
        fam = {}
        for j in np.flatnonzero(~same):
            k = names[cols[j]].split("|")[0]
            fam[k] = fam.get(k, 0) + 1
        out[role] = {"name": w["true"], "cadence_now_hz": f0.get("cad|all|-|-|cadence_hz"), "cadence_with_fix_hz": f1.get("cad|all|-|-|cadence_hz"),
                     "features_changed_of_630": int((~same).sum()), "changed_by_family": fam}
    return out


def main() -> int:
    t = time.time()
    from pipeline.identify import ixt_synth as S
    now, fixed = grid(False), grid(True)
    a = np.array(now, float)
    b = np.array(fixed, float)
    res = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "information_only": True, "engine_unchanged": True,
           "fault": "estimates from rhythm-less channels sit at the 0.8 Hz band-pass edge; _candidates doubles them into the step band; "
                    "resolve_cadence's vote ignores quality (idmax_features.py, _candidates and resolve_cadence)",
           "candidate_fix": f"only channels with autocorrelation peak >= {THR} vote; if none, all vote",
           "grid_now": {"within_5pct": int(np.sum(np.abs(a - 1) <= 0.05)), "median": float(np.nanmedian(a)), "min": float(np.nanmin(a)), "max": float(np.nanmax(a))},
           "grid_with_fix": {"within_5pct": int(np.sum(np.abs(b - 1) <= 0.05)), "median": float(np.nanmedian(b)), "min": float(np.nanmin(b)), "max": float(np.nanmax(b))},
           "grid_points": [{"step_hz": s, "v0": v, "direction": d, "now": x, "with_fix": y}
                           for (s, v, d), x, y in zip([(s, v, d) for s in S.STEPS for v in S.SPEEDS for d in S.DIRS], now, fixed)],
           "worked_walks": worked_walks(), "seconds": round(time.time() - t, 1)}
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, "cadence_fix_check.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "grid_points"}, indent=1))
    return 0


if __name__ == "__main__" and len(sys.argv) == 1:
    sys.exit(main())


def real_walks() -> dict:
    """The 180 natural identification walks (the engine's own 3 s windows): the resolved cadence today and with the
    candidate fix, and agreement with the envelope cadence where the envelope shows a clear rhythm."""
    import pickle
    from pipeline.identify import engine as EN
    from pipeline.identify import ixa_data as XD
    from pipeline.identify import ixt_synth as S
    from pipeline.identify import idx_bank as B
    from pipeline.identify.id19_featbank import CADENCE_CH
    from pipeline.io.capture_logger import read_capture_file
    meta = json.load(open(os.path.join(EN.ENG, "bank_T3.0", "meta.json")))["passes"]
    names = json.load(open(EN.DEV_NAMES))
    rows = []
    k = 0
    for rec in B.recordings():
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        qs = sorted(gt["passes"], key=lambda q: q["t_start"])
        if not (rec["kind"] == "idcap" and rec["block"] == "natural"):
            k += len(qs)
            continue
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        ex = XD.Tap(T=3.0, layout="id_spot", names=names)
        pos = {L: 0 for L in EN.LINKS}
        for q in qs:
            t0 = float(q["t_start"])
            lim = t0 + 3.0 + EN.CAP_S
            for L in EN.LINKS:
                n = int(np.searchsorted(fr[L]["t_mono"], lim, side="right"))
                ex.push(L, fr[L][pos[L]:n])
                pos[L] = n
            ex.press(t0, path=None, info={"features": False})
            (_w, td, A, _x), = ex.poll(lim)
            assert abs(td - meta[k]["t_dec"]) < 1e-9
            sets = [F.cadence_estimates(F.reduce_link(A[li], band, red)[0]) for li in range(3) for red, band in CADENCE_CH]
            now = ORIGINAL(sets)["cadence_hz"]
            fixed = resolve_fixed(sets)["cadence_hz"]
            env, how = S.envelope_cadence(A[1])
            rows.append({"row": k, "now": now, "fixed": fixed, "envelope": env, "envelope_clear": how != "none"})
            k += 1
    now = np.array([r["now"] or np.nan for r in rows])
    fix = np.array([r["fixed"] or np.nan for r in rows])
    env = np.array([r["envelope"] for r in rows])
    clear = np.array([r["envelope_clear"] for r in rows])
    chg = np.abs(fix / now - 1) > 0.05
    agree_now = np.abs(now[clear] / env[clear] - 1) <= 0.10
    agree_fix = np.abs(fix[clear] / env[clear] - 1) <= 0.10
    return {"n": len(rows), "cadence_changes_over_5pct": int(chg.sum()), "frac_changed": round(float(chg.mean()), 3),
            "median_fixed_over_now": round(float(np.nanmedian(fix / now)), 3),
            "envelope_clear_walks": int(clear.sum()), "agree_with_envelope_within_10pct_now": int(agree_now.sum()),
            "agree_with_envelope_within_10pct_fixed": int(agree_fix.sum()),
            "ratio_to_envelope_median_now": round(float(np.nanmedian(now[clear] / env[clear])), 3),
            "ratio_to_envelope_median_fixed": round(float(np.nanmedian(fix[clear] / env[clear])), 3)}


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "real":
    r = real_walks()
    p = os.path.join(OUT, "cadence_fix_check.json")
    d = json.load(open(p))
    d["real_natural_walks"] = r
    json.dump(d, open(p, "w"), indent=1)
    print(json.dumps(r, indent=1))
