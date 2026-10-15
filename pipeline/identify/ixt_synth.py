"""ixt_synth. The teaching-pack addendum's AC1 (`runs/identify/engine/PLAN.md`, the addendum note): the step-rate
estimator on a grid of simulated walks, pushed through the engine's own path (amplitude, causal clock, the 3 s window,
the 150 Hz grid, `pass_features`). The walker is `idz_synth`'s with its step rate and speed made parameters. CPU only.
Information for the write-up; the engine does not change. Development evaluation, all data seen.
From 1 Oct the engine is v2 (the cadence bug fix this grid found); the grid re-run on it writes `synth_grid_x.json`, and the
v1 run (`synth_grid.json`) is kept as the record of the bug.

    PYTHONPATH=. python3 -m pipeline.identify.ixt_synth
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idz_audit as Z
from pipeline.identify import idz_synth as ZS

OUT = os.path.join("runs", "identify", "teaching", "synth_grid")
STEPS = (1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2)
SPEEDS = (1.0, 1.2, 1.4)
DIRS = ("away", "towards")


def motion(t_rel: np.ndarray, step_hz: float, v0: float, direction: str) -> dict:
    """`idz_synth.motion` with the step rate, speed and direction as parameters (limbs at half the step rate)."""
    tg = np.arange(-1.0, max(float(t_rel.max()), 30.0) + 1.0, 1e-3)
    v = np.where(tg > 0, v0 * (1 - np.exp(-np.clip(tg, 0, None) / 0.3)) * (1 + 0.15 * np.sin(2 * np.pi * step_hz * tg)), 0.0)
    x = np.cumsum(v) * 1e-3
    stop = int(np.argmax(x >= ZS.PATH_M)) if np.any(x >= ZS.PATH_M) else len(x) - 1
    v[stop:] = 0.0
    x = np.minimum(np.cumsum(v) * 1e-3, ZS.PATH_M)
    xi = np.interp(t_rel, tg, x)
    out = {"t_end_rel": float(tg[stop]), "travel": xi,
           "from_tx": xi if direction == "away" else ZS.PATH_M - xi}
    for l, phi in ((1, 0.0), (2, np.pi)):
        vl = v * (2.5 + np.sin(2 * np.pi * (step_hz / 2) * tg + phi))
        xl = np.interp(t_rel, tg, np.cumsum(vl) * 1e-3)
        out[f"len{l}"] = xl if direction == "away" else 20.0 - xl
        out[f"m{l}"] = 1 + 0.8 * np.sin(2 * np.pi * (step_hz / 2) * t_rel + phi)
    out["bob"] = np.where(t_rel > 0, 1 + 0.2 * np.sin(2 * np.pi * step_hz * t_rel), 1.0)
    return out


def payload(t_rel: np.ndarray, F: float, step_hz: float, v0: float, direction: str, scale: float = 20.0) -> np.ndarray:
    """`idz_synth.csi` with the parametrised walker: (frames, 256) int8, interleaved (imag, real), nulls 0."""
    lay = Z.esp_layout()
    m = motion(t_rel, step_hz, v0, direction)
    att = 1.0 / (1.0 + m["from_tx"])
    torso_len = m["travel"] if direction == "away" else ZS.PATH_M - m["travel"]
    paths = [(np.full_like(t_rel, 1.0), np.full_like(t_rel, 0.5)),
             (0.30 * m["bob"] * att, 1.0 + 2 * F * torso_len),
             (0.05 * m["m1"] * att, 1.0 + 2 * F * m["len1"]),
             (0.05 * m["m2"] * att, 1.0 + 2 * F * m["len2"])]
    out = np.zeros((len(t_rel), 256), np.int8)
    for e in range(128):
        _field, sc, valid = lay[e]
        if not valid:
            continue
        fk = ZS.FC + sc * ZS.DF
        h = sum(a * np.exp(-2j * np.pi * fk * L / ZS.CL) for a, L in paths) * scale
        out[:, 2 * e] = np.clip(np.round(h.imag), -127, 127).astype(np.int8)
        out[:, 2 * e + 1] = np.clip(np.round(h.real), -127, 127).astype(np.int8)
    return out


def envelope_cadence(a_rx2: np.ndarray):
    """The cadence diagnostic's envelope method (`idz_cadence`)."""
    from pipeline.identify import idz_cadence as ZC
    from pipeline.identify import rehearsal_doppler_check as RD
    f, P = RD.conditioned_spectrogram(a_rx2)
    env = P[(f >= 10.0) & (f <= 70.0)].sum(axis=0)
    fs = 150.0 / 8.0
    pk, lag = ZC.acf_peak(env, fs, ZC.STEP)
    if lag is not None:
        return 1.0 / lag, "step"
    pk2, lag2 = ZC.acf_peak(env, fs, ZC.STRIDE)
    if lag2 is not None:
        return 2.0 / lag2, "stride"
    return float("nan"), "none"


def one(step_hz: float, v0: float, direction: str, src: dict) -> dict:
    from pipeline.identify import ixa_data as XD
    names = json.load(open(EN.DEV_NAMES))
    ci = names.index("cad|all|-|-|cadence_hz")
    t0 = src["t0"]
    t_end = t0 + motion(np.array([0.0]), step_hz, v0, direction)["t_end_rel"]
    res = {"step_hz": step_hz, "v0_m_s": v0, "direction": direction, "walk_s": round(t_end - t0, 3)}
    for tag, T in (("engine_3s_window", 3.0), ("whole_walk", t_end - t0)):
        ex = XD.Tap(T=T, layout="id_spot", names=names)
        lim = t0 + T + EN.CAP_S
        for L in EN.LINKS:
            fr = src["frames"][L]
            fr = fr[fr["t_mono"] <= lim]
            ex.push(L, fr)
        ex.press(t0, path=None, info={"features": True})
        (_w, _td, A, x), = ex.poll(lim)
        cad = float(x["features"][ci])
        env, how = envelope_cadence(A[1])
        res[tag] = {"resolver_hz": cad, "resolver_over_true": cad / step_hz if np.isfinite(cad) else None,
                    "envelope_hz": env, "envelope_over_true": env / step_hz if np.isfinite(env) else None, "envelope_lag_range": how}
    return res


def run() -> dict:
    from pipeline.io.capture_logger import read_capture_file
    t_all = time.time()
    rec = ZS.source_recording()
    gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
    t0 = float(sorted(gt["passes"], key=lambda q: q["t_start"])[0]["t_start"])
    base = {}
    for L in EN.LINKS:
        _h, fr = read_capture_file(f"{rec['stem']}_{L}.bin")
        keep = (fr["t_mono"] >= t0 - 25.0) & (fr["t_mono"] <= t0 + 12.0)
        t_hat, _lt = Z.corrected_time(fr)
        base[L] = (fr[keep].copy(), t_hat[keep] - t0)
    rows = []
    for step in STEPS:
        for v0 in SPEEDS:
            for d in DIRS:
                frames = {}
                for L in EN.LINKS:
                    fr, t_rel = base[L]
                    fr = fr.copy()
                    fr["data"] = payload(t_rel, ZS.F_LINK[L], step, v0, d)
                    frames[L] = fr
                rows.append(one(step, v0, d, {"t0": t0, "frames": frames}))
                print(f"{time.strftime('%H:%M:%S')} step {step} v {v0} {d}: resolver {rows[-1]['engine_3s_window']['resolver_over_true']}, "
                      f"envelope {rows[-1]['engine_3s_window']['envelope_over_true']}", flush=True)
    summ = {}
    for tag in ("engine_3s_window", "whole_walk"):
        r = np.array([x[tag]["resolver_over_true"] if x[tag]["resolver_over_true"] is not None else np.nan for x in rows])
        e = np.array([x[tag]["envelope_over_true"] if x[tag]["envelope_over_true"] is not None else np.nan for x in rows])
        summ[tag] = {"resolver_within_5pct": int(np.sum(np.abs(r - 1) <= 0.05)), "resolver_nan": int(np.sum(~np.isfinite(r))),
                     "resolver_ratio_median": float(np.nanmedian(r)), "resolver_ratio_min": float(np.nanmin(r)), "resolver_ratio_max": float(np.nanmax(r)),
                     "envelope_within_5pct": int(np.sum(np.abs(e - 1) <= 0.05)), "envelope_nan": int(np.sum(~np.isfinite(e))),
                     "envelope_ratio_median": float(np.nanmedian(e)) if np.isfinite(e).any() else None, "n": len(rows)}
    res = {"built": time.strftime("%Y-%m-%dT%H:%M:%S"), "source_timing": os.path.basename(rec["stem"]), "t0_press": t0,
           "grid": {"steps_hz": STEPS, "speeds_m_s": SPEEDS, "directions": DIRS}, "summary": summ, "walks": rows,
           "train_test": "identity-blind: no model; simulated walks through the engine's extraction", "seconds": round(time.time() - t_all, 1)}
    os.makedirs(OUT, exist_ok=True)
    res["engine_version"] = EN.ENGINE_VERSION
    json.dump(res, open(os.path.join(OUT, f"synth_grid{EN.SUFFIX}.json"), "w"), indent=1)
    print(json.dumps(summ, indent=1), flush=True)
    return res


if __name__ == "__main__":
    run()
    sys.exit(0)
