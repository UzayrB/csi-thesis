"""idz_synth. Identification audit, stage 2 (`runs/identify/audit/PLAN.md` section 2): a synthetic walker on
line A, written in the capture format and run through the REAL code path:
`read_capture_file` -> `raw_access.amplitude_from_frames` -> the id29 clock map (`id29_dc2_score._link`) ->
`KEEP` and `SC` -> the 150 Hz grid (`id19_bank._interp_cols`) -> `id19_featbank.pass_features` and
`idv2_core.conditioned_map`.

Timestamps and every non-CSI field come from a real Room B day 1 natural identification recording (the
first participant in capture order); only the CSI payload is synthetic. Identity never enters.

The CSI: on each valid subcarrier k (LLTF +-1..26, HT-LTF +-1..28) at f_k = 2,462 MHz + k 312.5 kHz, the
sum over four paths of a exp(-j 2 pi f_k L / c): a static path, the torso (length 1 + 2 F x(t), amplitude
bobbing at the step rate, falling with distance) and two limbs (speed 1.5 to 3.5 v at the stride rate, in
antiphase). v(t) = 1.2 (1 - exp(-t / 0.3)) (1 + 0.15 sin(2 pi 1.8 t)) from the start press until x = 5 m.

    PYTHONPATH=. python3 -m pipeline.identify.idz_synth
"""

from __future__ import annotations

import json
import os
import struct
import sys
import time

import numpy as np

from pipeline.identify import id29_dc2_score as D
from pipeline.identify import idmax_common as IC
from pipeline.identify import idv2_core as C
from pipeline.identify import idx_bank as B
from pipeline.identify import idz_audit as Z
from pipeline.identify.common import anon

OUT = os.path.join("runs", "identify", "audit", "synth")
LINKS = ("RX1", "RX2", "RX3")
F_LINK = {"RX1": 0.0, "RX2": 0.98, "RX3": 0.5}
FC, DF, CL = 2462e6, 312.5e3, 299792458.0
LAMBDA = CL / FC
STEP_HZ, STRIDE_HZ, V0 = 1.8, 0.9, 1.2
PATH_M = 5.0


def source_recording() -> dict:
    recs = [r for r in B.recordings() if r["session"] == "B1" and r["kind"] == "idcap" and r["block"] == "natural"]
    return sorted(recs, key=lambda r: anon(r["name"]))[0]           # participant P1: first in day 1's order


def motion(t_rel: np.ndarray) -> dict:
    """Walker kinematics at the given times (s since the start press), integrated on a 1 kHz grid."""
    tg = np.arange(-1.0, max(float(t_rel.max()), 30.0) + 1.0, 1e-3)    # long enough for the walk to finish
    v = np.where(tg > 0, V0 * (1 - np.exp(-np.clip(tg, 0, None) / 0.3)) * (1 + 0.15 * np.sin(2 * np.pi * STEP_HZ * tg)), 0.0)
    x = np.cumsum(v) * 1e-3
    stop = np.argmax(x >= PATH_M) if np.any(x >= PATH_M) else len(x) - 1
    v[stop:] = 0.0
    x = np.minimum(np.cumsum(v) * 1e-3, PATH_M)
    out = {"t_end_rel": float(tg[stop]), "x": np.interp(t_rel, tg, x)}
    for l, phi in ((1, 0.0), (2, np.pi)):
        vl = v * (2.5 + np.sin(2 * np.pi * STRIDE_HZ * tg + phi))
        out[f"x{l}"] = np.interp(t_rel, tg, np.cumsum(vl) * 1e-3)
        out[f"m{l}"] = 1 + 0.8 * np.sin(2 * np.pi * STRIDE_HZ * t_rel + phi)
    out["bob"] = np.where(t_rel > 0, 1 + 0.2 * np.sin(2 * np.pi * STEP_HZ * t_rel), 1.0)
    return out


def csi(t_rel: np.ndarray, F: float, scale: float = 20.0) -> np.ndarray:
    """(frames, 256) int8 payload: interleaved (imag, real) per entry, LLTF then HT-LTF, nulls 0."""
    lay = Z.esp_layout()
    m = motion(t_rel)
    att = 1.0 / (1.0 + m["x"])
    paths = [(np.full_like(t_rel, 1.0), np.full_like(t_rel, 0.5)),
             (0.30 * m["bob"] * att, 1.0 + 2 * F * m["x"]),
             (0.05 * m["m1"] * att, 1.0 + 2 * F * m["x1"]),
             (0.05 * m["m2"] * att, 1.0 + 2 * F * m["x2"])]
    out = np.zeros((len(t_rel), 256), np.int8)
    for e in range(128):
        field, sc, valid = lay[e]
        if not valid:
            continue
        fk = FC + sc * DF
        h = sum(a * np.exp(-2j * np.pi * fk * L / CL) for a, L in paths) * scale
        out[:, 2 * e] = np.clip(np.round(h.imag), -127, 127).astype(np.int8)
        out[:, 2 * e + 1] = np.clip(np.round(h.real), -127, 127).astype(np.int8)
    return out


def write_bin(path: str, hdr: dict, fr: np.ndarray) -> None:
    blob = json.dumps(hdr).encode("utf-8")
    with open(path, "wb") as f:
        f.write(b"CSIBIN01")
        f.write(struct.pack("<I", len(blob)))
        f.write(blob)
        f.write(fr.tobytes())


def simulate(out_dir: str = OUT, scale: float = 20.0, suspect_frac: float = 0.0, seed: int = 0, tag: str = "base") -> dict:
    from pipeline.io.capture_logger import read_capture_file
    rec = source_recording()
    gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
    t0 = float(sorted(gt["passes"], key=lambda q: q["t_start"])[0]["t_start"])
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.join(out_dir, f"synth_{tag}")
    rng = np.random.default_rng(seed)
    t_end = None
    for L in LINKS:
        hdr, fr = read_capture_file(f"{rec['stem']}_{L}.bin")
        fr = fr.copy()
        t_hat, _lt = Z.corrected_time(fr)
        t_rel = t_hat - t0
        t_end = t0 + motion(np.array([0.0]))["t_end_rel"]
        fr["data"] = csi(t_rel, F_LINK[L], scale)
        if suspect_frac > 0:
            inside = np.flatnonzero((t_hat >= t0) & (t_hat <= t_end))
            pick = rng.choice(inside, int(round(suspect_frac * len(inside))), replace=False)
            d = fr["data"]
            d[pick, 128:] = 0
            fr["data"] = d
        write_bin(f"{stem}_{L}.bin", hdr, fr)
    return {"stem": stem, "t0": t0, "t1": t_end}


def extract(stem: str, t0: float, t1: float, amp_scale: float = 1.0, context_s: float = None) -> dict:
    """The real path from the .bin files to features and maps. context_s: also return the RX2 grid over
    [t0 - context_s, t1 + context_s] (for the edge-transient measurement)."""
    from pipeline.identify import id19_featbank as FB
    from pipeline.identify.id19_bank import _interp_cols
    from pipeline.identify.id19_featbank import SC
    links = [D._link(f"{stem}_{L}.bin") for L in LINKS]
    grid = np.arange(t0, t1, 1.0 / C.HP["fs"])
    A = np.asarray([_interp_cols(grid, t, a) for t, a, _r, _c in links], np.float64)[:, :, SC] * amp_scale
    Rr = np.asarray([_interp_cols(grid, t, r) for t, _a, r, _c in links], np.float64)
    out = {"feats": FB.pass_features(A, Rr), "maps": np.stack([C.conditioned_map(A[li]) for li in range(3)]),
           "A": A, "torso_hz_rx2": D.torso_hz(A[1])}
    if context_s:
        t, a, _r, _c = links[1]
        n_pre = int(round(context_s * C.HP["fs"]))
        g2 = t0 + np.arange(-n_pre, len(grid) + n_pre) / C.HP["fs"]
        out["A_rx2_context"] = np.asarray(_interp_cols(g2, t, a), np.float64)[:, SC] * amp_scale
        out["context_offset"] = n_pre
    return out


def gait_cols() -> list:
    from pipeline.identify import idx_loso as L
    bank = L.load()
    return list(np.array(bank["names"])[L.columns("U_all_gait")])


def band_ratio_db(M: np.ndarray) -> float:
    lin = np.exp(M)
    hi = (C.F_BINS >= 35.0) & (C.F_BINS <= 70.0)
    lo = (C.F_BINS >= 10.0) & (C.F_BINS < 35.0)
    return float(10 * np.log10(lin[hi].mean() / lin[lo].mean()))


def run_checks(out_dir: str = OUT, names: list = None) -> dict:
    from pipeline.identify import idmax_features as F
    names = names if names is not None else gait_cols()
    base = simulate(out_dir, tag="base")
    t0, t1 = base["t0"], base["t1"]
    r = extract(base["stem"], t0, t1, context_s=20.0)
    v_bar = PATH_M / (t1 - t0)
    ref = 2 * F_LINK["RX2"] * v_bar / LAMBDA
    res = {"label": "development evaluation, all data seen", "pass_s": round(t1 - t0, 3), "v_bar": round(v_bar, 3)}
    # 1 torso frequency
    res["check1_torso"] = {"measured_hz": round(r["torso_hz_rx2"], 2), "predicted_hz": round(ref, 2),
                           "bin_hz": round(float(np.diff(C.F_BINS)[0]), 3),
                           "PASS": bool(abs(r["torso_hz_rx2"] - ref) <= float(np.diff(C.F_BINS)[0]))}
    # 2 cadence
    cad = r["feats"].get("cad|all|-|-|cadence_hz")
    res["check2_cadence"] = {"resolved_hz": cad, "true_step_hz": STEP_HZ,
                             "PASS": bool(cad is not None and np.isfinite(cad) and abs(cad - STEP_HZ) <= 0.05 * STEP_HZ)}
    # 3 completeness
    fv = np.array([r["feats"].get(n, np.nan) if r["feats"].get(n) is not None else np.nan for n in names], float)
    nan_names = [n for n, x in zip(names, fv) if not np.isfinite(x)]
    res["check3_complete"] = {"n_features": len(names), "n_nan": len(nan_names), "nan_names": nan_names[:40],
                              "PASS": len(nan_names) == 0}
    # 4a gain invariance on the float amplitudes
    r2 = extract(base["stem"], t0, t1, amp_scale=2.0)
    f2 = np.array([r2["feats"].get(n, np.nan) if r2["feats"].get(n) is not None else np.nan for n in names], float)
    ok = np.isfinite(fv) & np.isfinite(f2)
    rel = np.abs(f2[ok] - fv[ok]) / np.maximum(np.abs(fv[ok]), 1e-9)
    bad = [(n, float(a), float(b)) for n, a, b in zip(np.array(names)[ok], fv[ok], f2[ok])
           if not np.isclose(b, a, rtol=1e-6, atol=1e-9)]
    map_diff = float(np.abs(r2["maps"] - r["maps"]).max())
    res["check4a_gain_float"] = {"n_features_changed": len(bad), "changed": [(n, round(a, 6), round(b, 6)) for n, a, b in bad[:40]],
                                 "max_rel_change": float(rel.max()) if len(rel) else 0.0, "max_map_abs_change": map_diff,
                                 "nan_pattern_equal": bool(np.array_equal(np.isfinite(fv), np.isfinite(f2))),
                                 "PASS": len(bad) == 0 and map_diff <= 1e-5 and bool(np.array_equal(np.isfinite(fv), np.isfinite(f2)))}
    # 4b payload x 2 before int8 rounding (measurement)
    s2 = simulate(out_dir, scale=40.0, tag="scale2")
    r3 = extract(s2["stem"], t0, t1)
    f3 = np.array([r3["feats"].get(n, np.nan) if r3["feats"].get(n) is not None else np.nan for n in names], float)
    ok3 = np.isfinite(fv) & np.isfinite(f3)
    rel3 = np.abs(f3[ok3] - fv[ok3]) / np.maximum(np.abs(fv[ok3]), 1e-9)
    res["check4b_gain_payload"] = {"median_rel_change": float(np.median(rel3)), "p95_rel_change": float(np.percentile(rel3, 95)),
                                   "max_map_abs_change": float(np.abs(r3["maps"] - r["maps"]).max())}
    # 5 suspect frames (measurement)
    s5 = simulate(out_dir, suspect_frac=0.02, tag="suspect2pct")
    r5 = extract(s5["stem"], t0, t1)
    res["check5_suspect"] = {"rx2_35_70_over_10_35_db_clean": round(band_ratio_db(r["maps"][1]), 2),
                             "rx2_35_70_over_10_35_db_with_2pct_suspect": round(band_ratio_db(r5["maps"][1]), 2),
                             "change_db": round(band_ratio_db(r5["maps"][1]) - band_ratio_db(r["maps"][1]), 2)}
    # 6 edge transients (measurement)
    off = r["context_offset"]
    n = r["A"].shape[1]
    edge = {}
    for band in ("b08_35", "b03_2"):
        within = F.reduce_link(r["A"][1], band, "mean")[0]
        cont = F.reduce_link(r["A_rx2_context"], band, "mean")[0][off:off + n]
        rms = np.sqrt(np.mean(cont ** 2))
        seg = {"first_1s": slice(0, 150), "middle": slice(150, n - 150), "last_1s": slice(n - 150, n)}
        edge[band] = {k: round(float(np.sqrt(np.mean((within[s] - cont[s]) ** 2)) / rms), 3) for k, s in seg.items()}
    res["check6_edges_rel_rms_error"] = edge
    res["ALL_PASS_1_to_4"] = all(res[k]["PASS"] for k in ("check1_torso", "check2_cadence", "check3_complete", "check4a_gain_float"))
    # after the bug fixes (PLAN dated note): B-1 drops dwt_6 from the model's columns; B-2 is conditioned_map_v2
    from pipeline.identify import idz_bank as ZB
    fixed_names = [n for n in names if not n.endswith("|dwt_6")]
    nan_fixed = [n for n in fixed_names if not np.isfinite(r["feats"].get(n) if r["feats"].get(n) is not None else np.nan)]
    res["check3_complete_fixed"] = {"n_features": len(fixed_names), "n_nan": len(nan_fixed), "PASS": len(nan_fixed) == 0}
    m1 = np.stack([ZB.conditioned_map_v2(r["A"][li]) for li in range(3)])
    m2 = np.stack([ZB.conditioned_map_v2(r2["A"][li]) for li in range(3)])
    res["check4a_gain_float_fixed"] = {"max_map_abs_change": float(np.abs(m2 - m1).max()), "n_features_changed": len(bad),
                                       "PASS": len(bad) == 0 and float(np.abs(m2 - m1).max()) <= 1e-5}
    res["ALL_PASS_1_to_4_after_fixes"] = all(res[k]["PASS"] for k in ("check1_torso", "check2_cadence", "check3_complete_fixed",
                                                                       "check4a_gain_float_fixed"))
    return res


def main() -> int:
    res = run_checks()
    os.makedirs(OUT, exist_ok=True)
    txt = json.dumps(res, indent=1, default=float)
    assert IC.no_names(txt)
    open(os.path.join(OUT, "checks.json"), "w").write(txt)
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
