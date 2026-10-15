"""ixt_pack. The identification teaching pack (`reports/identification/briefs/2026-10-01_teaching.md`, sections 2.2 and 2.3): the two worked
walks opened up, the model, the results tables, provenance and the timeline, as one JSON (split if over 3 MB).
Every app-level number comes from the verification run of the live app's rig path; every other number from the
engine's own code on the same frames, or from a committed result file named in the entry. Names, not codes.
From 1 Oct every engine figure is engine v2's (the cadence bug fix, `_x` models, bank and result files); the v1 figures
appear only in the timeline, as superseded.

    PYTHONPATH=. python3 -m pipeline.identify.ixt_pack [--device mps]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pickle
import subprocess
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idv2_core as C
from pipeline.identify import idw_core as W
from pipeline.identify import ixt_walk as XW
from pipeline.identify.common import SIX, anon

OUT_DIR = os.path.join("reports", "identification", "teaching")
T_DIR = os.path.join("runs", "identify", "teaching")
CODES = ("P1", "P2", "P3", "P4", "P5", "P6")
NAME = {anon(n): n for n in SIX}
NAMES = [NAME[c] for c in CODES]
LABEL = "development evaluation, all data seen"
SUF = EN.SUFFIX
MB2 = EN.model_name("loso_B2")
BANK = EN.bank_dir(EN.T_S)
V4 = EN.ENGINE_VERSION >= 4                  # engine v4 (2 Oct): the 4.0 s window, the end detector, the speed on the walking span
ALPHA_B2 = json.load(open(os.path.join(EN.ENG, "models", MB2, "manifest.json"))).get("alpha") if V4 else None
PACK_NAME = "2026-10-02_teaching-pack.json" if V4 else "2026-10-01_teaching-pack.json"
EV_FILE = os.path.join(EN.ENG, "eval", f"eval{SUF}.json")
MS_FILE = os.path.join("runs", "identify", "final_extras", "measures", f"measures{SUF}.json")
OP_FILE = os.path.join(EN.ENG, "eval", f"one_press_cost_tracking_information{SUF}.json")


# ------------------------------------------------------------------ small helpers

ABS_TIME_KEYS = ("press_time_mono_s", "t_start", "t_end")      # absolute clock times: kept to the microsecond


def sig(x, n=4):
    """Round to n significant figures, recursively; numpy to plain lists; NaN to None. Absolute clock times
    (`ABS_TIME_KEYS`) are rounded to 1e-6 s instead, since 4 figures would destroy them."""
    if isinstance(x, dict):
        return {k: (round(float(v), 6) if k in ABS_TIME_KEYS and isinstance(v, (float, np.floating)) else sig(v, n))
                for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [sig(v, n) for v in x]
    if isinstance(x, np.ndarray):
        return sig(x.tolist(), n)
    if isinstance(x, (np.floating, float)):
        x = float(x)
        if not math.isfinite(x):
            return None
        return 0.0 if x == 0 else float(f"{x:.{n}g}")
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def commit_of(path: str) -> str:
    #: --follow and the A/M filter: the commit that last wrote the text, not the move of 1 October 2026
    out = subprocess.run(["git", "log", "-1", "--format=%h", "--follow", "--diff-filter=AM", "--", path],
                         capture_output=True, text=True).stdout.strip()
    return out or "uncommitted"


def head() -> str:
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()


def entry(value, ci=None, n=None, train=None, test=None, calibration="causal", scored=None, src=None, src_commit=None, **extra):
    e = {"value": value, "ci_low": ci[0] if ci else None, "ci_high": ci[1] if ci else None, "n": n,
         "train_sessions": train, "test_session": test, "calibration": calibration, "scored_set": scored,
         "source_file": src, "source_commit": src_commit or (commit_of(src) if src else None)}
    e.update(extra)
    return e


def boot(d, **kw):
    return entry(d["pct"], d.get("ci95"), d.get("n"), **kw)


def names_not_codes(x):
    """Dictionary keys that are codes (P1 to P6) replaced by names, recursively: the pack never carries codes."""
    if isinstance(x, dict):
        return {(NAME[k] if k in NAME else k): names_not_codes(v) for k, v in x.items()}
    if isinstance(x, list):
        return [names_not_codes(v) for v in x]
    return x


# ------------------------------------------------------------------ the two walks

def walk_section(role: str, sel: dict, device: str) -> dict:
    from pipeline.identify import idx_loso as L
    from pipeline.identify import ixa_data as XD
    from pipeline.identify import rehearsal_doppler_check as RD
    bdir = BANK
    meta = json.load(open(os.path.join(bdir, "meta.json")))["passes"]
    X = np.load(os.path.join(bdir, "features.npy"))
    maps = pickle.load(open(os.path.join(bdir, "maps.pkl"), "rb"))
    z = np.load(os.path.join(EN.ENG, "replays", f"{MB2}_B2_T{EN.T_S:.1f}.npz"))
    v = np.load(os.path.join(T_DIR, f"verify_B2{SUF}_rig_path.npz"))
    w = sel[role]
    k, row = int(w["k"]), int(w["row"])
    m = meta[row]
    stem = os.path.join("runs", "identify", "dc2_src_relabelled", "identification", "session_02", w["recording"])
    t0 = float(m["t_start"])
    assert abs(float(v["t0"][k]) - t0) < 1e-9 and abs(float(z["t0"][k]) - t0) < 1e-9
    ext = XW.extract(stem, t0, row, m, X, maps, alpha=ALPHA_B2)
    q = ext["q"]
    gt = json.load(open(stem + ".gt.json", encoding="utf-8"))
    order = sorted(gt["passes"], key=lambda p: p["t_start"])
    pass_index = [i for i, p in enumerate(order) if abs(float(p["t_start"]) - t0) < 1e-9][0]
    # ---- app-level numbers: the live app's own logged values (verification run), full precision
    ens = v["ensemble"][k]
    conf = v["confidence"][k]
    top, run_up = int(np.argmax(ens)), int(np.argsort(-ens)[1])
    t_decision = float(v["t_dec"][k]) + float(v["latency_s"][k]) - float(v["wait_s"][k])
    app = {"top": NAMES[top], "runner_up": NAMES[run_up], "truth": NAME[m["anon"]], "correct": NAMES[top] == NAME[m["anon"]],
           "ensemble_probability": dict(zip(NAMES, np.exp(ens).tolist())), "displayed_confidence": dict(zip(NAMES, conf.tolist())),
           "wifi_speed_m_s": float(v["wifi_speed"][k]), "direction_detected": str(v["path"][k]),
           "calibration_walks_seen": int(v["calib_n"][k]), "t_decision_data_s": float(v["t_dec"][k]) - t0,
           "t_decision_s_after_press": t_decision - t0, "latency_after_window_s": float(v["latency_s"][k]),
           "packet_wait_after_window_s": float(v["wait_s"][k]),
           "note": "these are the live app's logged values from the rig-path verification run, unrounded; the latency's compute part is measured and varies run to run"}
    # ---- the engine's own internals for this walk
    model = EN.Model(os.path.join(EN.ENG, "models", MB2), device)
    sess = EN.Session(model)
    te = z["te"]
    lay = lambda i: "id_spot" if meta[int(i)]["kind"] == "idcap" else "home"          # noqa: E731  engine v3's fix L
    pool = [{"features": X[int(i)], "maps": maps[int(i)], "wifi_speed": meta[int(i)]["wifi_speed"], "path": str(z["path_used"][j]),
             "layout": lay(i)} for j, i in enumerate(te[:k]) if lay(i) == lay(row)]
    sess.set_pool(pool)
    me = {"features": X[row], "maps": maps[row], "wifi_speed": m["wifi_speed"], "path": str(z["path_used"][k]), "layout": lay(row)}
    cls = sess.classify(me)
    assert np.allclose(cls["ensemble"], ens, atol=1e-6), "the engine's re-run differs from the app's logged ensemble"
    evo = XW.cnn_evolution(model, sess, me)
    for c in ("cnn", "cnn_prior", "cnn_perlink_prior"):
        assert np.allclose(evo[c]["running_logp"][-1], cls["components"][c], atol=1e-6)
    A, R = ext["A"], ext["R"]
    # ---- timeline of arrivals (20 Hz bins)
    lo, hi = t0 - 1.0, t_decision + 0.5
    edges = np.arange(lo, hi + 1e-9, 0.05)
    timeline = {"bin_start_s_after_press": (edges[:-1] - t0), "bin_s": 0.05,
                "arrivals_per_bin": {L: np.histogram(ext["arrivals"][L], edges)[0] for L in EN.LINKS},
                "press_s": 0.0, "window_end_s": EN.T_S, "decision_data_complete_s": float(v["t_dec"][k]) - t0,
                "decision_s": t_decision - t0}
    # ---- raw signal and conditioning, per link
    links = {}
    for li, L in enumerate(EN.LINKS):
        t_hat = ext["timed"][li][0]
        inw = t_hat[(t_hat >= t0) & (t_hat <= t0 + EN.T_S)]
        gaps = np.diff(inw) * 1e3
        cd = XW.conditioning(A[li])
        F_link = EN.mean_F(L, "A_fwd" if m["path"] == "A_fwd" else "A_rev", "id_spot")
        mean_ch = __import__("pipeline.identify.idmax_features", fromlist=["x"]).reduce_link(A[li], "b08_35", "mean")[0]
        links[L] = {
            "raw_amplitude_heatmap_25hz": XW.ds_mean(A[li], 6, 0).T, "subcarrier_mean_50hz": XW.ds_mean(A[li].mean(axis=1), 3),
            "rssi_50hz_dbm": XW.ds_mean(R[li], 3), "packets_in_window": int(len(inw)),
            "inter_packet_gap_median_ms": float(np.median(gaps)), "inter_packet_gap_max_ms": float(np.max(gaps)),
            "conditioning": {
                "step1_resampled_amplitude": "raw_amplitude_heatmap_25hz (150 Hz grid, averaged to 25 Hz for display)",
                "step2_bandpass_4_70hz_rms_heatmap_25hz": XW.ds_rms(cd["band"], 6, 0).T,
                "step3_pca_explained_variance_pc1_to_pc4": cd["explained"],
                "step3_pc1_trace_50hz_discarded": cd["pcs"][0][::3], "step3_pc2_to_pc4_traces_50hz": cd["pcs"][1:4, ::3],
                "step3_note": "PC traces are 4 to 70 Hz signals shown at 50 Hz (every third sample): a display only, aliased above 25 Hz",
                "step4_stft_magnitude_per_pc": cd["stft_per_pc"], "step5_log_map_minus_mean_cnn_input": cd["log_map"]},
            "gait_channel_mean_b08_35_50hz": mean_ch[::3],
            "gait_channel_autocorrelation_50hz_lags_0_to_2s": XW.acf(mean_ch[::3], 100),
            "bistatic_factor_F": F_link,
            "predicted_torso_hz_press_speed": 2 * F_link * m["press_speed_m_s"] / EN.LAMBDA,
            "predicted_torso_hz_wifi_speed": 2 * F_link * m["wifi_speed"] / EN.LAMBDA if np.isfinite(m["wifi_speed"]) else None}
    # ---- direction and speed
    f, P = RD.conditioned_spectrogram(ext["A3"][1] if V4 else A[1])     # v4: the direction is read on the first 3 s
    band = (f >= 10.0) & (f < 35.0)
    e = np.log10(P[band].sum(axis=0) + 1e-12)
    slope, icpt = np.polyfit(np.arange(len(e), dtype=float), e, 1)
    li_s, F2 = EN.best_link(m["engine_path"], "id_spot")
    nw = int(np.searchsorted(np.arange(t0, t0 + EN.T_S, 1.0 / EN.FS), t0 + m["walk_end_s"], side="left")) if V4 else A.shape[1]
    contour = XD.torso_contour(A[li_s][:nw])                            # v4: the walking span only
    ftorso = float(np.nanmedian(contour))
    assert abs(ftorso * EN.LAMBDA / (2 * F2) - m["wifi_speed"]) < 1e-9
    direction = {"rx2_log10_energy_10_35hz_per_frame": e, "fit_slope_per_frame": slope, "fit_intercept": icpt,
                 "sign": "falling: away (A_fwd)" if slope < 0 else "rising: towards (A_rev)",
                 "detected": m["dir_detected"], "true": m["path"], "frame_times_s": (16 + 8 * np.arange(len(e))) / XW.FS}
    speed = {"torso_contour_hz_per_frame_rx2": contour, "f_torso_hz_median": ftorso, "F_rx2": F2, "lambda_m": EN.LAMBDA,
             "v_wifi_m_s": m["wifi_speed"], "speed_trace_m_s": contour * EN.LAMBDA / (2 * F2),
             "formula": "v = f_torso x lambda / (2 F)", "press_speed_m_s_not_used": m["press_speed_m_s"],
             "contour_frame_times_s": (np.arange(len(contour)) * 8) / XW.FS, "speed_link": EN.LINKS[li_s]}
    if V4:
        x4 = ext["x"]
        assert abs(x4["walk_end_s"] - m["walk_end_s"]) < 1e-9 and abs(x4["wifi_speed"] - m["wifi_speed"]) < 1e-9
        speed["end_detector"] = {
            "alpha": ALPHA_B2, "checkpoints_s": [c for c, _e in ext["series"]],
            "rx2_energy_10_35hz_per_frame_at_last_checkpoint": ext["series"][-1][1],
            "frame_times_s": EN.DET_C0_S + EN.DET_HOP_S * np.arange(len(ext["series"][-1][1])),
            "reference_rule": f"median over frames centred up to {EN.DET_REF_S} s",
            "end_rule": f"first run of {EN.DET_RUN} frames below alpha x reference starting at or after {EN.DET_MIN_S} s",
            "walk_end_s": m["walk_end_s"], "speed_span_s": [0.0, m["walk_end_s"]],
            "note": "the speed is measured on the walking span only; features and maps use the whole window"}
    # ---- gait features: raw, standardised as the calibration in force did
    cols = model.cols
    names = json.load(open(EN.DEV_NAMES))
    gnames = [names[j] for j in cols]
    g = X[row].astype(float)[cols]
    pr = model.feat["rf_prior"]["state"]
    pool_g = np.asarray([p["features"].astype(float)[cols] for p in pool])
    Xall = np.vstack([pool_g, g[None, :]])
    paths = np.array([p["path"] for p in pool] + [me["path"]])
    std_session = pr.apply(Xall, paths, np.array([len(Xall) - 1]), np.arange(len(pool)) if len(pool) else None)[0]
    kept_session = np.flatnonzero(pr.ok)[pr.keep]
    pp = model.feat["rf"]["state"]
    std_path = pp.transform(g[None, :], np.array([me["path"]]))[0]
    kept_path = np.flatnonzero(pp.ok)[pp.keep]
    zs = np.full(len(cols), np.nan)
    zs[kept_session] = std_session
    zp = np.full(len(cols), np.nan)
    zp[kept_path] = std_path
    feats = {"names": gnames, "family": [n.split("|")[0] for n in gnames], "raw": g, "standardised_by_session_calibration": zs,
             "standardised_per_path_training": zp,
             "calibration_in_force": f"{len(pool)} earlier B2 windows (>= 10, so session statistics)" if len(pool) >= 10 else
             f"{len(pool)} earlier windows (< 10: training statistics)",
             "resolved_cadence_hz": ext["feats"].get("cad|all|-|-|cadence_hz"),
             "cycle_template_rx2": [ext["feats"].get(f"tplacf|mean@b08_35|RX2|0|tpl_{i:02d}") for i in range(32)]}
    from pipeline.identify import idz_cadence as ZC
    envp = RD.conditioned_spectrogram(A[1])
    env = envp[1][(envp[0] >= 10.0) & (envp[0] <= 70.0)].sum(axis=0)
    pk = ZC.acf_peak(env - env.mean(), 150.0 / 8.0, ZC.STEP)
    pk2 = ZC.acf_peak(env - env.mean(), 150.0 / 8.0, ZC.STRIDE)
    feats["envelope_cadence_hz"] = (1.0 / pk[1] if pk and pk[0] is not None and pk[0] >= ZC.THR else
                                    2.0 / pk2[1] if pk2 and pk2[0] is not None and pk2[0] >= ZC.THR else None)
    # ---- evidence to identity
    comps = {c: {"logp": v[f"c_{c}"][k], "p": np.exp(v[f"c_{c}"][k])} for c in model.components}
    s = sum(v[f"c_{c}"][k] for c in model.components)
    evidence = {"components": comps, "sum_logp": s, "ensemble_logp": ens, "ensemble_probability": np.exp(ens),
                "displayed_confidence": conf, "argmax": NAMES[top], "runner_up": NAMES[run_up],
                "margin_log_units": float(ens[top] - ens[run_up]),
                "cnn_evolution": evo, "classes_order": NAMES,
                "note": "the CNN components score each 34-frame window (about 2 s of signal, hop 0.21 s) and average them; the five "
                        f"feature components decide once, on the whole {EN.T_S:g} s window"}
    # ---- what drove it (diagnostics, not causes)
    drivers = {}
    for c in ("rf", "rf_prior", "rf_pace_prior", "et_pace_prior"):
        st = model.feat[c]["state"]
        inp = gnames + (["pace: wifi_speed_m_s"] if c.endswith("pace_prior") else [])
        kept = np.flatnonzero(st.ok)[st.keep]
        imp = model.feat[c]["clf"].feature_importances_
        order_ = np.argsort(-imp)[:20]
        raw = np.r_[g, m["wifi_speed"]] if c.endswith("pace_prior") else g
        drivers[c] = [{"feature": inp[kept[j]], "importance": float(imp[j]), "this_walk_raw": float(raw[kept[j]])} for j in order_]
    lda = model.feat["lda_pace_prior"]
    st = lda["state"]
    raw = np.r_[g, m["wifi_speed"]]
    Xl = np.vstack([np.c_[pool_g, np.array([p["wifi_speed"] for p in pool])], raw[None, :]])
    zl = st.apply(Xl, paths, np.array([len(Xl) - 1]), np.arange(len(pool)))[0]
    kept = np.flatnonzero(st.ok)[st.keep]
    inp = gnames + ["pace: wifi_speed_m_s"]
    cls_names = [NAME[c] for c in lda["classes"]]
    lda_out = {}
    for who in (NAMES[top], NAMES[run_up]):
        ci = cls_names.index(who)
        contrib = lda["clf"].coef_[ci] * zl
        idx = np.argsort(-np.abs(contrib))[:15]
        lda_out[who] = [{"feature": inp[kept[j]], "contribution": float(contrib[j]), "z": float(zl[j]),
                         "coef": float(lda["clf"].coef_[ci][j])} for j in idx]
    drivers["lda_pace_prior_contributions"] = lda_out
    drivers["note"] = "diagnostics, not causes: impurity importances are global to each forest; LDA contributions are coef x z for this walk"
    return {"role": role, "name": NAME[m["anon"]], "session": "B2", "recording": w["recording"], "pass_index_in_recording": pass_index,
            "pace_block": m["block"], "direction_true": m["path"], "direction_detected": m["dir_detected"],
            "press_time_mono_s": t0,
            "truth_for_teaching_only_never_seen_by_the_model": {
                "metre_anchor_press_times_s_after_press": [float(x) - t0 for x in q.get("anchor_times", [])],
                "anchor_coords_m": q.get("anchor_coords"), "end_press_s_after_press": float(q["t_end"]) - t0},
            "app": app, "event_timeline": timeline, "links": links, "map_frequency_axis_hz": C.F_BINS,
            "map_frame_times_s": (16 + 8 * np.arange(cd["log_map"].shape[1])) / XW.FS,
            "direction": direction, "speed": speed, "gait_features": feats, "evidence": evidence, "drivers": drivers}


# ------------------------------------------------------------------ the model

def cnn_layers(c_in: int) -> dict:
    net = C.make_net(c_in, 6)
    c1, c2, c3 = C.HP["channels"]
    rows = [("conv1 3x3, padding 1", f"{c1} x 28 x 34", c_in * c1 * 9 + c1, f"{c_in}·{c1}·9 + {c1}"),
            ("batchnorm1", f"{c1} x 28 x 34", 2 * c1, f"2·{c1} (scale, shift)"),
            ("ReLU, max-pool over time (1 x 2)", f"{c1} x 28 x 17", 0, "0"),
            ("conv2 3x3", f"{c2} x 28 x 17", c1 * c2 * 9 + c2, f"{c1}·{c2}·9 + {c2}"),
            ("batchnorm2", f"{c2} x 28 x 17", 2 * c2, f"2·{c2}"),
            ("ReLU, max-pool over time (1 x 2)", f"{c2} x 28 x 8", 0, "0"),
            ("conv3 3x3", f"{c3} x 28 x 8", c2 * c3 * 9 + c3, f"{c2}·{c3}·9 + {c3}"),
            ("batchnorm3, ReLU", f"{c3} x 28 x 8", 2 * c3, f"2·{c3}"),
            ("mean over time (frequency kept)", f"{c3} x 28 = {c3 * 28}", 0, "0"),
            ("append the direction one-hot", f"{c3 * 28 + 2}", 0, "0"),
            ("dropout 0.3 (training only)", f"{c3 * 28 + 2}", 0, "0"),
            ("linear head", "6", (c3 * 28 + 2) * 6 + 6, f"{c3 * 28 + 2}·6 + 6")]
    total = sum(r[2] for r in rows)
    return {"input": f"{c_in} x 28 frequencies x 34 frames, plus a 2-value direction flag",
            "layers": [{"layer": a, "output_shape": b, "parameters": n, "how_the_count_arises": h} for a, b, n, h in rows],
            "total_from_table": total, "total_from_the_network": C.n_params(net)}


def check_saved_totals() -> dict:
    import torch
    md = os.path.join(EN.ENG, "models", MB2)
    out = {}
    for tag, c_in in (("cnn3", 3), ("cnn_link0", 1)):
        sd = torch.load(os.path.join(md, f"{tag}_seed0.pt"), map_location="cpu")
        net = C.make_net(c_in, 6)
        names = {n for n, _ in net.named_parameters()}
        out[tag] = int(sum(v.numel() for k, v in sd.items() if k in names))
    return out


def training_stats(model_name: str) -> dict:
    bdir = BANK
    meta = json.load(open(os.path.join(bdir, "meta.json")))["passes"]
    maps = pickle.load(open(os.path.join(bdir, "maps.pkl"), "rb"))
    md = os.path.join(EN.ENG, "models", model_name)
    rows = np.load(os.path.join(md, "train_rows.npy"))
    mt = json.load(open(os.path.join(md, "meta_feat_cnn.json")))
    tab = {}
    for i in rows:
        mm = meta[int(i)]
        key = (mm["session"], NAME[mm["anon"]])
        p, wn = tab.get(key, (0, 0))
        tab[key] = (p + 1, wn + len(C.windows(maps[int(i)])))
    sessions = sorted({k[0] for k in tab})
    return {"model": model_name, "passes_total": int(len(rows)),
            "passes_per_session_per_person": {s: {n: tab.get((s, n), (0, 0))[0] for n in NAMES} for s in sessions},
            "cnn_windows_per_session_per_person": {s: {n: tab.get((s, n), (0, 0))[1] for n in NAMES} for s in sessions},
            "class_balance_passes": {n: int(sum(tab.get((s, n), (0, 0))[0] for s in sessions)) for n in NAMES},
            "training_seconds": mt["seconds"], "seeds": mt["seeds"], "cnn_steps": mt["steps"], "device": mt["device"],
            "built": mt["built"], "feature_retraining_seconds_v2": mt.get("seconds_feature_retraining"),
            "feature_components": mt.get("feature_components"), "cnn_components": mt.get("cnn_components")}


def lda_shrinkage() -> dict:
    """The LDA's fitted Ledoit-Wolf shrinkage per class for `loso_B2` (sklearn's 'auto' rule, recomputed on its own
    training matrix)."""
    from sklearn.covariance import ledoit_wolf
    from sklearn.preprocessing import StandardScaler
    from pipeline.identify import ixa_score as S
    B = S.base(SUF)
    a, G = B["a"], B["G"]
    tr = np.flatnonzero(a["session"] != "B2")
    M = S.matrix(G, None, a["wifi_speed"].astype(float), True)[tr]
    A = W.Prior().fit(M, a["path"][tr], a["session"][tr])
    y = a["anon"][tr]
    out = {}
    for c in CODES:
        Xc = A[y == c]
        out[NAME[c]] = float(ledoit_wolf(StandardScaler().fit_transform(Xc))[1])
    return out


def model_section() -> dict:
    from pipeline.identify import idmax_eval as E
    names = json.load(open(EN.DEV_NAMES))
    cols = EN.v2_columns(names)
    fam = {}
    for j in cols:
        f_ = names[j].split("|")[0]
        fam[f_] = fam.get(f_, 0) + 1
    rig = EN._rigs()
    F_line_a = {L: {"away": EN.mean_F(L, "A_fwd", "id_spot"), "towards": EN.mean_F(L, "A_rev", "id_spot")} for L in EN.LINKS}
    settings = {
        "window_T_s": EN.T_S, "decision_cap_s": EN.CAP_S,
        "causal_clock": {"trailing_s": EN.CLOCK_WIN_S, "min_frames": EN.CLOCK_MIN, "percentile": EN.CLOCK_PCT,
                         "wrap": "a backwards jump > 1 s from within 5 s of 2^32 us to under 5 s", "reboot": "any other backwards jump > 1 s: restart"},
        "grid_hz": 150.0, "csi_entries": 103, "unique_subcarriers": 54,
        "bands_hz": {"map_bandpass": [4.0, 70.0], "gait_b08_35": [0.8, 3.5], "b03_2": [0.3, 2.0], "full": [0.3, 70.0],
                     "direction_energy": [10.0, 35.0]},
        "pca_rule": "per-window PCA of the band-passed 103 entries, mean-centred, sign set so skewness is positive; PCs 2 to 4 kept, PC1 discarded",
        "stft": {"window_samples": 32, "overlap": 24, "hop_samples": 8, "nfft": 64, "bin_hz": 150.0 / 64, "frames_per_s": 150.0 / 8},
        "map_bins": {"count": 28, "from_hz": float(C.F_BINS[0]), "to_hz": float(C.F_BINS[-1])},
        "log_rule": "log(magnitude + 1e-6 x the map's median magnitude), minus the map's mean",
        "cnn_window": {"frames": C.HP["win_frames"], "hop_frames": C.HP["hop_frames"], "seconds": C.HP["win_frames"] * 8 / 150.0},
        "calibration_thresholds": {"feature_standardisation_min_windows": EN.MIN_FEAT_CALIB, "adabn_min_windows": 1},
        "fusion": "the equal-weight sum of the eight components' log-probabilities, normalised; the decision is its argmax",
        "displayed_confidence": "softmax(sum / 8): the geometric mean of the eight; it never changes the decision",
        "lambda_m": EN.LAMBDA, "F_min_for_speed": EN.F_MIN,
        "node_positions_m": {"identification_layout": rig["id_spot"], "tracking_layout_rx2_home": rig["home"]},
        "F_along_line_a_identification_layout": F_line_a}
    if V4:
        settings["engine_v4"] = {
            "window": f"[t0, t0 + {EN.T_S} s], decided at its end by the causal clock; it stops at the next start press if that press is already pending",
            "direction": f"RX2's 10 to 35 Hz energy slope on the first {EN.DIR_T_S} s, at that 3 s window's own decision time (as engine v3)",
            "end_detector": {"checkpoints_s": f"{EN.DIR_T_S} to {EN.T_S} every {EN.DET_STEP_S}", "reference": f"median energy over frames centred up to {EN.DET_REF_S} s",
                             "end": f"first run of {EN.DET_RUN} frames below alpha x reference, starting at or after {EN.DET_MIN_S} s",
                             "alpha_per_model": {b_: json.load(open(os.path.join(EN.ENG, "models", EN.model_name(b_), "manifest.json"))).get("alpha")
                                                 for b_ in ("loso_B2", "loso_B1", "loso_A1", "loso_A2", "loso_A3", "deploy_all5")},
                             "alpha_rule": "fitted on each fold's training sessions only (window and gait brief, 1 Oct)"},
            "wifi_speed": "the torso contour median on the best link for the direction's path, on [t0, the detected end] (the whole window without one), x lambda / (2F)",
            "features_and_maps": f"on the whole {EN.T_S} s window",
            "fixes_carried": "engine v3's fix L (per-layout calibration pools) and fix F (no rhythm, no step rate)"}
    comps = {"rf": "random forest, 300 trees, max_features sqrt, random_state 0; 630 gait columns; per-path z (training statistics)",
             "rf_prior": "the same forest; session standardisation (calibration)",
             "rf_pace_prior": "the same forest; 630 gait + Wi-Fi speed; session standardisation",
             "et_pace_prior": "extra trees, 300 trees, sqrt, random_state 0; 630 + Wi-Fi speed; session standardisation",
             "lda_pace_prior": "LDA, solver lsqr, shrinkage auto (Ledoit-Wolf); 630 + Wi-Fi speed; session standardisation",
             "cnn": "CNN-v2 on the 3-link maps, seeds 0 to 2, plain", "cnn_prior": "the same nets with AdaBN on the calibration windows",
             "cnn_perlink_prior": "one 1-link CNN-v2 per receiver (3 seeds each), AdaBN, the three links' log-probabilities summed"}
    return {"settings": settings, "cnn_3link": cnn_layers(3), "cnn_1link": cnn_layers(1), "saved_state_dict_totals": check_saved_totals(),
            "cnn_training": {"optimiser": "Adam, lr 1e-3, weight decay 1e-4, cosine to 0", "steps": 6000, "batch": 64,
                             "sampling": "class-balanced", "augmentation": C.HP["aug"], "seeds": [0, 1, 2]},
            "components": comps, "lda_fitted_shrinkage_per_class_loso_B2": lda_shrinkage(),
            "features_630_by_family": fam,
            "training": {"loso_B2": training_stats(MB2), "deploy_all5": training_stats(EN.model_name("deploy_all5"))},
            "chance_pct": {"single_walk": 16.67, "top_2": 33.33, "household_2": 50.0, "household_3": 33.33, "household_4": 25.0,
                           "household_5": 20.0, "household_6": 16.67}}


# ------------------------------------------------------------------ results tables

WALK_TRAIN = {"to B2": ["A1", "A2", "A3", "B1"], "to B1": ["A1", "A2", "A3", "B2"]}
WALK_TEST = "B2 and B1, pooled (each walk scored by the fold that never saw its day)"
NAT = "natural identification walks (180)"


def confusion(z, meta, nat_only=True) -> dict:
    te = z["te"]
    M = np.zeros((6, 6), int)
    for kk, i in enumerate(te):
        mm = meta[int(i)]
        if mm["kind"] != "idcap" or (nat_only and mm["block"] != "natural"):
            continue
        M[CODES.index(mm["anon"]), int(z["ensemble"][kk].argmax())] += 1
    return {"rows_true_cols_predicted": NAMES, "matrix": M.tolist()}


def results() -> dict:
    ev = json.load(open(EV_FILE))
    ms = json.load(open(MS_FILE))
    op = json.load(open(OP_FILE))
    ck = json.load(open(os.path.join(EN.ENG, "checks", "checks.json")))
    st = json.load(open(os.path.join("runs", "identify", "final_extras", "state.json")))
    a4 = json.load(open(os.path.join("runs", "identify", "final_extras", "a4", "a4_walks.json")))
    gs = json.load(open(os.path.join(EN.ENG, "stage1", "result.json")))
    au = json.load(open(os.path.join("runs", "identify", "audit", "final.json")))
    ph = json.load(open(os.path.join("runs", "identify", "idwalks", "physics", "physics.json")))
    cad = json.load(open(os.path.join(EN.ENG, "cadence", "cadence_ratio.json")))
    rh = json.load(open(os.path.join("runs", "identify", "audit", "stage5", "cadence.json")))["summary"]
    CFP = os.path.join(T_DIR, "synth_grid", "cadence_fix_check.json")
    cf = json.load(open(CFP))
    meta = json.load(open(os.path.join(BANK, "meta.json")))["passes"]
    E = EV_FILE
    MS = MS_FILE
    kw = {"train": WALK_TRAIN, "test": WALK_TEST}
    head = {b: boot(v, scored=b.replace("_", " ") + " identification walks", src=E, **kw) | {"to_B2_pct": v["toB2"], "to_B1_pct": v["toB1"]}
            for b, v in ev["walks"]["engine"].items()}
    zb2 = np.load(os.path.join(EN.ENG, "replays", f"{MB2}_B2_T{EN.T_S:.1f}.npz"))
    zb1 = np.load(os.path.join(EN.ENG, "replays", f"{EN.model_name('loso_B1')}_B1_T{EN.T_S:.1f}.npz"))
    cb2, cb1 = confusion(zb2, meta), confusion(zb1, meta)
    pooled = {"rows_true_cols_predicted": NAMES, "matrix": (np.array(cb2["matrix"]) + np.array(cb1["matrix"])).tolist()}
    loso = {s: boot(v, train=[x for x in ("A1", "A2", "A3", "B1", "B2") if x != s] if len(s) == 2 else "the other four sessions per fold",
                    test=s, scored="tracking walks (route known)", src=E) for s, v in ev["loso_tracking_known_route"].items()}
    pace = {
        "S0_press_speed": {b: boot(v, scored=b, src=E, calibration="none (one-number LDA)", **kw) for b, v in ev["walks"]["S0"].items()},
        "S_wifi": {b: boot(v, scored=b, src=MS, calibration="none (one-number LDA)", **kw) for b, v in ms["S_wifi"].items()},
        "engine_without_pace": {b: boot(v, scored=b, src=MS, **kw) for b, v in ms["engine_without_pace"].items()},
        "engine_minus_S0": {b: boot(v, scored=b, src=E, **kw) for b, v in ev["walks"]["engine_minus_S0"].items()},
        "engine_minus_S_wifi": {b: boot(v, scored=b, src=MS, **kw) for b, v in ms["engine_minus_S_wifi"].items()},
        "engine_without_pace_minus_S_wifi": {b: boot(v, scored=b, src=MS, **kw) for b, v in ms["engine_without_pace_minus_S_wifi"].items()},
        "note": "S0 times the walk from two presses, a stopwatch the engine never has; S_wifi uses the engine's own Wi-Fi speed"}
    caln = {"walks": {b: boot(v, scored=b, src=MS, calibration="none", **kw) for b, v in ms["cal_none"]["walks"].items()},
            "engine_minus_cal_none": {b: boot(v, scored=b, src=MS, **kw) for b, v in ms["cal_none"]["engine_minus_cal_none"].items()},
            "loso": {k_: boot(v, scored="tracking walks", src=MS, train="the other four sessions per fold", test=k_)
                     for k_, v in ms["cal_none"]["loso"].items()}}
    dep = {k_: boot(v, scored="natural identification walks", src=E, **kw) | {"chance_pct": v.get("chance")}
           for k_, v in ev["walks"]["deployment"].items()}
    cov = {"levels": {lv: entry(v["pct"], v["ci95"], v["walks"], scored="natural identification walks, most confident first",
                                src=MS, **kw) | {"walks_per_person": v["walks_per_person"], "correct_per_person": v["correct_per_person"],
                                                 "lowest_confidence": v["min_confidence"]}
                      for lv, v in ms["coverage"]["levels"].items()},
           "auroc": entry(ms["coverage"]["auroc"], None, 180, scored="natural identification walks", src=MS, **kw)}
    opc = ev["one_press_cost"]
    one = {"natural_walks": boot(opc["engine_minus_two_press"]["natural_both"], scored="natural identification walks", src=E, **kw),
           "by_block": {b: boot(v, scored=b, src=E, **kw) for b, v in opc["engine_minus_two_press"].items()},
           "two_press_natural": boot(opc["two_press"]["natural_both"], scored="natural (two presses, B1 configuration)", src=E, **kw),
           "tracking_pooled": boot(op["pooled"], scored="600 tracking passes", src=OP_FILE,
                                   train="the other four sessions per fold", test="all five"),
           "tracking_room_A": boot(op["room_A"], scored="Room A tracking passes", src=OP_FILE,
                                   train="the other four sessions per fold", test="A1, A2, A3"),
           "tracking_room_B": boot(op["room_B"], scored="Room B tracking passes", src=OP_FILE,
                                   train="the other four sessions per fold", test="B1, B2"),
           "room_A_without_pace": boot(op["room_A_without_pace"], scored="Room A tracking passes, no pace components",
                                       src=OP_FILE, train="the other four", test="A1, A2, A3")}
    tsens = {T: {b: boot(v, scored=b, src=E, **kw) for b, v in d.items()} for T, d in ev["T_sensitivity_information"].items()}
    lat = ev["latency"]
    two = {"identification_walks_natural": boot(au["walks"]["natural_both"], scored="natural identification walks", calibration="others",
                                                 src=os.path.join("runs", "identify", "audit", "final.json"), **kw),
           "fast_lead_over_S0": entry(21.85, [5.00, 35.59], 119, scored="fast identification walks", calibration="others",
                                      src="reports/identification/2026-09-30_audit.md", train=WALK_TRAIN, test=WALK_TEST, section="2, the headline"),
           "loso_room_A": boot(au["loso_tracking_causal"]["room_A"], scored="Room A tracking walks", train="the other four sessions per fold",
                               test="A1, A2, A3", src=os.path.join("runs", "identify", "audit", "final.json")),
           "loso_room_B": boot(au["loso_tracking_causal"]["room_B"], scored="Room B tracking walks", train="the other four sessions per fold",
                               test="B1, B2", src=os.path.join("runs", "identify", "audit", "final.json")),
           "note": "the two-press configuration is a frozen reference (30 Sept); its bank was built with the v1 cadence resolver"}
    a1g = [h for h in st["history"] if h["item"] == "A1"][0]["physics_gate"]
    CK = os.path.join(EN.ENG, "checks", "checks.json")
    physics = {
        "torso_hz_rx2": {d: entry(v["torso_hz_median"], None, v["n"], scored=f"natural identification walks, {d}", calibration="none",
                                  src=os.path.join("runs", "identify", "idwalks", "physics", "physics.json"), train="identity-blind",
                                  test="B1 and B2") | {"predicted_hz": v["predicted_hz_median"], "spearman": v["spearman_measured_vs_predicted"]}
                         for d, v in ph["direction_RX2"].items()},
        "direction_detector": entry(ck["direction"]["all"]["accuracy_pct"], None, 419, scored="all identification walks", calibration="none",
                                    src=CK, train="identity-blind (a rule)", test="B1 and B2") | {"by_group": ck["direction"]},
        "wifi_speed_current": {k_: v for k_, v in ck["wifi_speed"].items()} | {"source_file": CK},
        "wifi_speed_a1_estimator": a1g | {"source_file": os.path.join("runs", "identify", "final_extras", "state.json")},
        "limb_bands_rx2_over_empty_room": ph["links"]["RX2|both"] | {"source_file": os.path.join("runs", "identify", "idwalks", "physics", "physics.json")},
        "rhythm_visibility_natural_rx2": {"energy_envelope": rh["envelope"], "gait_band_channel": rh["gait_band_mean"],
                                          "source_file": os.path.join("runs", "identify", "audit", "stage5", "cadence.json")},
        "cadence_resolver_bias": {k_: cad[k_] for k_ in ("n_clear", "fractions_within_10pct", "ratio_percentiles_10_25_50_75_90", "sentence")}
                                 | {"source_file": os.path.join(EN.ENG, "cadence", "cadence_ratio.json"),
                                    "note": "measured 30 Sept with the v1 resolver on the two-press bank's windows; the cadence bug (AC1) explains its low median"},
        "cadence_resolver_engine_windows_v1_and_v2": {k_: cf["real_natural_walks"][k_] for k_ in cf["real_natural_walks"] if k_ != "walks"}
                                 | {"source_file": CFP, "what": "the 180 natural identification walks, the engine's own 3 s windows: the resolved "
                                    "cadence before (now) and after (fixed) the cadence bug fix, and agreement with the energy envelope where it shows a clear rhythm"},
        "clock_causal_vs_whole_file": ck["clock"] | {"source_file": CK}}
    rejected = {"GS": entry(gs["paired_pooled"]["pct"], gs["paired_pooled"]["ci95"], 600, scored="600 tracking passes (paired)",
                            train="the other four sessions per fold", test="all five", src=os.path.join(EN.ENG, "stage1", "result.json"),
                            decision="not adopted"),
                **{h["item"]: (entry(h["paired_natural"]["pct"], h["paired_natural"]["ci95"], 180, scored="natural (paired)",
                                     src=os.path.join("runs", "identify", "final_extras", "state.json"), **kw) | {"decision": "not adopted"}
                               if "paired_natural" in h else {"physics_gate": h.get("physics_gate"), "decision": "not tested (gate)"})
                   for h in st["history"] if h["item"] in ("A1", "A2", "A3")},
                "A4": entry(a4["paired_natural"]["pct"], a4["paired_natural"]["ci95"], 180, scored="natural (paired)",
                            src=os.path.join("runs", "identify", "final_extras", "a4", "a4_walks.json"), **kw) | {"decision": "not adopted"}}
    # the two families of components on their own (sums of their log-probabilities from the same replays; information)
    from pipeline.identify import idw_eval as EV
    groups = {"cnn_only": ("cnn", "cnn_prior", "cnn_perlink_prior"),
              "features_only": ("rf", "rf_prior", "rf_pace_prior", "et_pace_prior", "lda_pace_prior")}
    comp = {}
    for g, cs in list(groups.items()) + [("all_eight", None)]:
        oks, whos = [], []
        for z in (zb2, zb1):
            k = np.array([meta[int(i)]["kind"] == "idcap" and meta[int(i)]["block"] == "natural" for i in z["te"]])
            who = np.array([meta[int(i)]["anon"] for i in z["te"]])[k]
            e = z["ensemble"][k] if cs is None else sum(z[f"c_{c}"][k] for c in cs)
            oks.append((np.array(CODES)[e.argmax(1)] == who).astype(float))
            whos.append(who)
        d = EV._boot(np.concatenate(oks), np.concatenate(whos))
        comp[g] = boot(d, scored="natural identification walks", src=os.path.join(EN.ENG, "replays"), **kw) | {
            "to_B2_pct": round(100 * float(oks[0].mean()), 2), "to_B1_pct": round(100 * float(oks[1].mean()), 2),
            "components": list(cs) if cs else "all eight"}
    comp["note"] = "information: the sum of each family's log-probabilities from the engine's own replays; the engine always uses all eight"
    return {"headline": head, "component_families": comp, "confusion_B2": cb2, "confusion_B1": cb1, "confusion_pooled": pooled,
            "per_person_natural_pct": ms["per_participant_natural"], "loso_tracking": loso, "pace_confound": pace,
            "no_same_day_adaptation": caln, "deployment": dep, "confidence_coverage": cov, "one_press_cost": one,
            "T_sensitivity_information": tsens, "latency_s": lat, "two_press_reference": two, "physics": physics,
            "rejected_candidates": rejected, "label": LABEL}


# ------------------------------------------------------------------ provenance and the timeline

def provenance() -> list:
    P = "runs/identify/engine/PLAN.md"
    rows = [
        ("the five feature components' weights", "each fold's four training sessions (loso_B2_x: A1, A2, A3, B1; deploy_all5_x: all five)",
         "1 Oct 2026 (retrained on the engine v2 bank; first trained 30 Sept)", "idz_core.train with the same rows, heads and seeds (ixt_rebank)",
         "runs/identify/engine/models/<model>_x/feat_*.pkl", "80cbf0c", False),
        ("the CNN weights (3-link and per-link, 3 seeds)", "the same training sessions", "30 Sept 2026",
         "ide_train; copied unchanged into the v2 models (the fix leaves the maps untouched, asserted for every window)", "<model>/cnn*_seed*.pt", "a972c4c", False),
        ("the CNN input statistics", "the training windows of the fold", "30 Sept 2026", "per link and direction", "<model>/cnn*_norm.pkl", "a972c4c", False),
        ("per-path z statistics (rf)", "the training passes of the fold", "30 Sept 2026", "W.PerPath", "<model>/feat_rf.pkl", "a972c4c", False),
        ("per-session standardisation statistics (training side)", "each training session on itself", "30 Sept 2026", "W.Prior", "<model>/feat_*_prior.pkl", "a972c4c", False),
        ("test-time standardisation and AdaBN statistics", "the test session's EARLIER windows, unlabelled (causal); nothing else of the test day", "at run time",
         "engine.Session (>= 10 windows; >= 1 for AdaBN)", "pipeline/identify/engine.py", "d5c99f1", False),
        ("the component list (8 components)", "development batches with test results in view (A1 to B2 leave one session out)", "29 Sept 2026",
         "dev batch 2; disclosed in ID_DEV_FINAL section 7", "reports/identification/2026-09-29_development-batch-2.md", commit_of("reports/identification/2026-09-29_development-batch-2.md"), True),
        ("the fusion rule (equal-weight sum)", "development batches; every selection rule lost to averaging", "29 Sept 2026",
         "ID_DEV_FINAL section 4", "reports/identification/2026-09-29_development-batch-2.md", commit_of("reports/identification/2026-09-29_development-batch-2.md"), True),
        ("the direction rule (RX2 10 to 35 Hz energy slope)", "physics, from the identification walks' energy by thirds (B1 and B2, identity-blind)",
         "30 Sept 2026", "fixed in PLAN 2.4 before training; 95 % gate on all 419 walks", P, "0ef1e58", True),
        ("the Wi-Fi speed formula and its F values", "physics: f = 2 F v / lambda; F from the node geometry (id15_factor_map)", "30 Sept 2026",
         "PLAN 2.5", P, "0ef1e58", False),
        ("T = 3.0 s and the 1 s cap", "Uzayr's brief (no data)", "30 Sept 2026", "brief section 4.1; T sensitivity only reported afterwards"
         + ("; superseded by T = 4.0 s (engine v4)" if V4 else ""), "reports/identification/briefs/2026-09-30_engine.md", "ca0408f", False),
        ("the bands (4 to 70 Hz map; 0.8 to 3.5 Hz gait)", "the frozen feature bank, designed on Room A data (A1 to A3)", "23 Sept 2026",
         "id19_featbank, freeze-hashed", "pipeline/identify/id19_featbank.py", commit_of("pipeline/identify/id19_featbank.py"), True),
        ("the subcarrier list (103 entries, 54 subcarriers)", "measured nulls on all three links (Room A, identity-blind)", "23 Sept 2026",
         "id19_bank.KEEP, id19_featbank.SC", "pipeline/identify/id19_bank.py", commit_of("pipeline/identify/id19_bank.py"), False),
        ("the causal clock settings (20 s, 5th percentile, 20 frames)", "modelled on the frozen 10 s-bin map; fixed before training", "30 Sept 2026",
         "PLAN 2.2", P, "0ef1e58", False),
        ("the CNN architecture and training hyperparameters", "registered with DC2 v2 before its first run", "28 Sept 2026",
         "idv2_core.HP (freeze 2026-09-28b)", "pipeline/identify/idv2_core.py", commit_of("pipeline/identify/idv2_core.py"), False),
        ("the bug fixes B-1 (dwt_6 removed) and B-2 (relative log constant)", "found by the synthetic walker (identity-blind)", "30 Sept 2026",
         "the audit: bugs adopted whatever their effect", "reports/identification/2026-09-30_audit.md", commit_of("reports/identification/2026-09-30_audit.md"), False),
        ("the cadence bug fix (engine v2): only estimate sets with an autocorrelation peak >= 0.30 vote on the step rate",
         "found by the simulated walks of the addendum's AC1 (identity-blind); the threshold is the resolver's own existing confidence cut",
         "1 Oct 2026", "Uzayr adopted it as a bug fix whatever its effect (Option 1), after seeing its measured effect (information)",
         "pipeline/identify/engine.py", "80cbf0c", True)]
    if V4:
        rows += [
            ("engine v3's fix L (calibration pools per layout) and fix F (no rhythm, no step rate)", "found by the lever screen's checks (identity-blind bugs)",
             "1 Oct 2026", "adopted as bug fixes by Uzayr's v3 brief", "pipeline/identify/engine.py", "7b032fe", True),
            ("T = 4.0 s (engine v4)", "the lean-in screen's window plateau on all five sessions (3.75 s 36.11, 4.0 s 37.78, 4.25 s 36.67), with test results in view",
             "1 to 2 Oct 2026", "the lean-in brief's base-window rule, then its final rule; development evaluation", "runs/identify/lean_in/final_final.json", "71f823d", True),
            ("the end detector's alpha (0.5; 0.2 for loso_B1)", "each fold's training sessions only (the window and gait brief's rule)", "1 Oct 2026",
             "the median end error on the training sessions' identification walks", "runs/identify/window_gait/alpha.json", "33656c9", False),
            ("the feature components' weights (engine v4)", "each fold's training sessions, on the v4 bank", "2 Oct 2026",
             "iv4_build: the same rows, heads and seeds as v3", "runs/identify/engine/models/<model>_v4/feat_*.pkl", "b13808d", False),
            ("the CNN weights (engine v4)", "copied unchanged from the v3 models (trained on 3 s maps, 30 Sept); scored on 4 s maps", "2 Oct 2026",
             "the lean-in stack kept v3's weights", "runs/identify/engine/models/<model>_v4/cnn*_seed*.pt", "b13808d", False)]
    return [{"element": a, "fitted_or_chosen_on": b, "date": c, "rule": d, "file": e, "commit": f, "chosen_with_test_results_in_view": g}
            for a, b, c, d, e, f, g in rows]


def timeline() -> list:
    ev = json.load(open(EV_FILE))
    T = []
    def add(date, value, ci, what, part, calib, status, why=None, by=None, src=None):
        T.append({"date": date, "value_pct": value, "ci": ci, "measured": what, "train_test": part, "calibration": calib,
                  "status": status, "superseded_why": why, "superseded_by": by, "source": src})
    S = "reports/identification/thesis-summary.md"
    add("2026-09-12", 15.7, None, "eight-class CNN (two since-retired participants); speed alone 28.6", "Room A, across days", "none",
        "archived", "not comparable: eight classes", None, S + " section 2.1")
    add("2026-09-18", 25.83, None, "per-pass gait features, cross-day (the ladder)", "Room A, day pairs", "per-line z", "superseded",
        "test-set head selection and oracle cadence", "the nested 15.83", S + " sections 2.2 and 4")
    add("2026-09-23", 15.83, [10.28, 21.67], "the nested cross-day headline (p 0.71); speed alone 32.50", "Room A, leave one session out, nested",
        "per-line z", "superseded", "the direction change: a new model family and more data", "the development ensemble", S + " section 5")
    add("2026-09-28", 26.67, [13.33, 36.67], "DC2 pre-registered analysis P1 (S0 40.00; analysis P2: RX2 = RX3 = 23.33)",
        "Room A trained, B1 to B2", "per-line z", "superseded (the frozen record stands as the 'before')", "a pre-registered test of the old model",
        "the development ensemble", S + " DC2 section")
    add("2026-09-29", 39.72, [27.50, 46.94], "the development ensemble, Room A (Room B 30.00 [19.58, 39.17])", "leave one session out, tracking walks",
        "causal", "superseded", "two presses; bug B-1 found later", "the audit's 39.44 / 30.00, then the engine's 30.83 / 29.17",
        "reports/identification/2026-09-29_development-batch-2.md")
    add("2026-09-29", 46.67, [29.44, 66.11], "identification walks, natural, TR-AB", "Room A + the other Room B day -> B1/B2", "others",
        "superseded", "bug B-1 (a hidden pace proxy)", "43.33", "reports/identification/2026-09-29_identification-walks.md")
    add("2026-09-30", 43.33, [26.11, 62.78], "identification walks after the audit's bug fixes (two presses)", "the same", "others",
        "superseded (kept as the two-press reference)", "Uzayr: one model, the live app, one press", "36.11", "reports/identification/2026-09-30_audit.md")
    v2 = json.load(open(os.path.join(EN.ENG, "eval", "eval_x.json")))["walks"]["engine"]["natural_both"]
    add("2026-09-30", 36.11, [24.44, 52.22], "the one-press engine, identification walks, natural (the live app)", "the four other sessions -> B2/B1",
        "causal", "superseded", "the cadence bug (found by AC1's simulated walks, 1 Oct); fixed as engine v2", f"{v2['pct']:.2f}",
        "reports/identification/2026-09-30_final.md")
    add("2026-10-01", -0.56, [-3.89, 2.78], "the cadence fix measured before adoption by feature re-scoring (engine unchanged; natural "
        "35.56; Room B tracking -5.42 [-8.75, -1.67]) (paired change)", "the four other sessions -> B2/B1", "causal", "information",
        None, None, os.path.join(T_DIR, "cadence_fix", "impact.json"))
    if V4:
        v3 = json.load(open(os.path.join(EN.ENG, "eval", "eval_v3.json")))["walks"]["engine"]["natural_both"]
        v4 = ev["walks"]["engine"]["natural_both"]
        add("2026-10-01", v2["pct"], v2["ci95"], "engine v2 (the cadence bug fix), identification walks, natural (the live app)",
            "the four other sessions -> B2/B1", "causal", "superseded", "two bugs (fix L, fix F) found by the lever screen", "engine v3",
            os.path.join(EN.ENG, "eval", "eval_x.json"))
        add("2026-10-01", v3["pct"], v3["ci95"], "engine v3 (fix L and fix F), identification walks, natural (the live app)",
            "the four other sessions -> B2/B1", "causal", "superseded", "the lean-in brief: the 4.0 s window", "engine v4",
            os.path.join(EN.ENG, "eval", "eval_v3.json"))
        add("2026-10-02", v4["pct"], v4["ci95"], f"engine v{EN.ENGINE_VERSION} (the 4.0 s window, the end detector), identification walks, natural (the live app)",
            "the four other sessions -> B2/B1", "causal", "CURRENT", None, None, EV_FILE)
    else:
        add("2026-10-01", v2["pct"], v2["ci95"], "engine v2 (the cadence bug fix), identification walks, natural (the live app)",
            "the four other sessions -> B2/B1", "causal", "CURRENT", None, None, EV_FILE)
    for name, v, ci, src in (("audit L1", 1.11, [-1.11, 3.89], "reports/identification/2026-09-30_audit.md"), ("audit L2", 2.78, [-4.44, 7.78], "reports/identification/2026-09-30_audit.md"),
                             ("audit CF", -1.11, [-15.00, 10.00], "reports/identification/2026-09-30_audit.md"), ("audit FN", -0.56, [-3.33, 1.67], "reports/identification/2026-09-30_audit.md"),
                             ("audit GS (identification walks)", 10.00, [-5.00, 23.33], "reports/identification/2026-09-30_audit.md"),
                             ("GS on 600 tracking passes", -2.00, [-4.00, 0.50], "reports/identification/2026-09-30_final.md"),
                             ("A2 speed profile", 0.00, [-3.33, 3.33], "reports/identification/2026-09-30_extras.md"), ("A3 offset windows", -3.33, [-5.56, -1.11], "reports/identification/2026-09-30_extras.md"),
                             ("A4 lean correction", -0.56, [-1.67, 0.00], "reports/identification/2026-09-30_extras.md"),
                             ("start press only (two-press era)", -14.44, [-26.67, -2.78], "reports/identification/2026-09-29_identification-walks.md")):
        add("2026-09-30" if "audit" in name or "GS" in name or name.startswith("A") else "2026-09-29", v, ci, f"rejected candidate: {name} (paired change)",
            "as its test", "as its test", "rejected", None, None, src)
    add("2026-09-30", None, None, "rejected candidate: A1 precise Wi-Fi speed (physics gate r 0.697 < 0.70; not tested)", "identity-blind", "none", "rejected",
        None, None, "reports/identification/2026-09-30_extras.md")
    return T


def addendum() -> dict:
    """The addendum's AC1 to AC3 (information only), when their outputs exist."""
    out = {"status": "pending"}
    p0 = os.path.join(T_DIR, "synth_grid", "synth_grid.json")
    p1 = os.path.join(T_DIR, "synth_grid", f"synth_grid{SUF}.json")
    if V4 and not os.path.exists(p1):                 # AC1 was measured on engine v2's 3 s window and is not re-run on v4
        p1 = os.path.join(T_DIR, "synth_grid", "synth_grid_x.json")
        out["measured_on"] = "engine v2 (3 s window); AC1 to AC3 are information and were not re-run on engine v4"
    pf = os.path.join(T_DIR, "synth_grid", "cadence_fix_check.json")
    pi = os.path.join(T_DIR, "cadence_fix", "impact.json")
    p2 = os.path.join(T_DIR, "extra", "extra.json")
    if os.path.exists(p1):
        g, g0, f, im = json.load(open(p1)), json.load(open(p0)), json.load(open(pf)), json.load(open(pi))
        out["AC1_step_rate_simulated"] = {
            "summary": g["summary"], "walks": g["walks"], "grid": g["grid"], "source_file": p1, "engine_version": g.get("engine_version"),
            "train_test": "identity-blind: no model; simulated walks through the engine's extraction",
            "before_the_fix": {"summary": g0["summary"], "walks": g0["walks"], "source_file": p0,
                               "note": "the same grid through engine v1: the run that found the cadence bug"},
            "the_bug": {"fault": f["fault"], "fix": f["candidate_fix"], "worked_walks": f["worked_walks"],
                        "real_natural_walks": {k_: v for k_, v in f["real_natural_walks"].items() if k_ != "walks"}, "source_file": pf},
            "effect_measured_before_adoption": {"paired_natural": im["paired_natural"], "paired_by_block": im["paired_by_block"],
                                                "tracking_pooled_change": im["tracking_pooled_change"], "loso_by_room": im["loso_by_room"],
                                                "features_changed_windows": im["features_changed_windows"], "source_file": pi,
                                                "how": "feature re-scoring with the engine unchanged (information for Uzayr's decision)"},
            "decision": "adopted as a bug fix (engine v2), Uzayr, 1 Oct 2026 (Option 1)" + ("" if V4 else "; every engine figure in this pack is engine v2's")}
    if os.path.exists(p2):
        e = json.load(open(p2))
        out["AC2_same_day_confounded_by_recording"] = e["AC2_same_day"] | {"source_file": p2}
        out["AC3_training_without_slow_and_fast_walks"] = e["AC3_without_paced_training"] | {"source_file": p2}
    if os.path.exists(p1) and os.path.exists(p2):
        out["status"] = "complete"
    return out


# ------------------------------------------------------------------ build

def build(device: str = "mps", final: bool = False) -> dict:
    """final: refuse unless the ablation scoring and the addendum's AC1 to AC3 are all present; otherwise they are
    marked pending (a provisional build for drafting the notes)."""
    sel = json.load(open(os.path.join(T_DIR, f"selection{SUF}.json")))
    ver = json.load(open(os.path.join(T_DIR, f"verify_B2{SUF}.json")))
    walks = {r: walk_section(r, sel, device) for r in ("wrong", "right")}
    # check 2: the exported app-level numbers equal the app's logged values (the verification run's JSON lines)
    lines = [json.loads(l) for l in open(ver["jsonl"])]
    chk = {}
    for r, w in walks.items():
        ln = [l for l in lines if abs(l["t_press_mono"] - w["press_time_mono_s"]) < 1e-9][0]
        a = w["app"]
        diffs = [abs(a["ensemble_probability"][NAME[c]] - ln["ensemble_probability"][c]) for c in CODES]
        diffs += [abs(a["displayed_confidence"][NAME[c]] - ln["displayed_confidence"][c]) for c in CODES]
        diffs += [abs(a["wifi_speed_m_s"] - ln["wifi_speed_m_s"]), abs(a["latency_after_window_s"] - ln["latency_after_window_s"])]
        chk[r] = {"decision_equal": a["top"] == ln["top_name"], "runner_up_equal": a["runner_up"] == ln["runner_up_name"],
                  "direction_equal": a["direction_detected"] == ln["path"], "calibration_equal": a["calibration_walks_seen"] == ln["calibration_windows"],
                  "max_abs_diff_against_log": max(diffs),
                  "note": "the JSON log rounds probabilities to 4 to 6 decimals and latency to 3; the npz of the same run holds full precision, equal exactly"}
        chk[r]["PASSED"] = bool(all(v for k_, v in chk[r].items() if k_.endswith("_equal")) and chk[r]["max_abs_diff_against_log"] < 6e-4)
    sub = json.load(open(os.path.join(T_DIR, f"substitution{SUF}.json")))
    for r, w in walks.items():
        pr = [p for p in sub["pairs"] if p["host_k"] == int(sel[r]["k"])][0]
        w["substitution"] = {"donor": pr["donor"], "donor_own_decision": pr["donor_own_decision"], "swapped_decision": pr["A_decision"],
                             "swapped_confidence": pr["A_confidence"], "rebuilt_pool_decision": pr["B_decision"]}
    checks = {"verification": ver | {"worked_walk_values": chk}, "substitution": {k_: v for k_, v in sub.items() if k_ != "pairs"} | {"pairs": sub["pairs"]},
              "shuffled_full": names_not_codes(json.load(open(os.path.join(T_DIR, f"shuffled_full{SUF}.json")))),
              "shuffled_null": json.load(open(os.path.join(T_DIR, f"shuffled_null{SUF}.json"))),
              "conditioning_ablation": json.load(open(os.path.join(T_DIR, "ablation", f"ablation{SUF}.json")))
                                       if os.path.exists(os.path.join(T_DIR, "ablation", f"ablation{SUF}.json")) else {"status": "pending"},
              "conditioning_energy_identity_blind": json.load(open(os.path.join(T_DIR, "ablation", f"maps_T{EN.T_S:.1f}.json" if V4 else "maps.json")))["energy_over_empty_rx2_10_35hz"]}
    plan = "runs/identify/engine/PLAN.md"
    pack = {"schema_version": "id_teaching_pack_v1", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "git_commit": head(),
            "engine_version": EN.ENGINE_VERSION, "engine_version_note": ("engine v4: v3 (v2 plus fix L and fix F) with the 4.0 s window, the end detector and the speed on the "
            "walking span (2 Oct 2026); every engine figure here is v4's unless labelled; older engines appear only in the timeline "
            "as superseded, and the addendum (AC1 to AC3) is engine v2's, labelled") if V4 else ("engine v2: v1 plus the cadence bug fix "
            "(1 Oct 2026, AC1); every engine figure here is v2's, v1's appear only in the timeline as superseded"),
            "engine_plan_sha256": hashlib.sha256(open(plan, "rb").read()).hexdigest(), "label": LABEL,
            "names_note": "participants are named; codes are never used here, because tracking numbers them differently (its P5 is PA2)",
            "models": {m_: {"training_sessions": json.load(open(os.path.join(EN.ENG, "models", m_, "manifest.json")))["training_sessions"]
                            if os.path.exists(os.path.join(EN.ENG, "models", m_, "manifest.json")) and "training_sessions" in
                            json.load(open(os.path.join(EN.ENG, "models", m_, "manifest.json"))) else
                            __import__("pipeline.live.identify_engine", fromlist=["x"]).training_sessions(os.path.join(EN.ENG, "models", m_))}
                       for m_ in [EN.model_name(b_) for b_ in ("loso_B2", "loso_B1", "loso_A1", "loso_A2", "loso_A3", "deploy_all5")]},
            "selection": sel, "walks": walks, "model": model_section(), "results": results(), "provenance": provenance(),
            "timeline": timeline(), "checks": checks, "addendum": addendum()}
    if final:
        assert pack["addendum"]["status"] == "complete" and "status" not in pack["checks"]["conditioning_ablation"], "not final yet"
    pack["provisional"] = not final
    apps = {r: w.pop("app") for r, w in pack["walks"].items()}
    out = sig(pack)
    for r in apps:                                     # the verified app-level numbers stay unrounded
        out["walks"][r]["app"] = apps[r]
    os.makedirs(OUT_DIR, exist_ok=True)
    txt = json.dumps(out, separators=(",", ":"))
    import re
    hit = re.search(r'"P[1-6]"', txt)
    assert hit is None, f"a code in the pack: ...{txt[max(0, hit.start() - 200):hit.end() + 50]}..."
    p = os.path.join(OUT_DIR, PACK_NAME)
    assert not os.path.exists(p), f"{p} exists: never overwritten"
    if len(txt) <= 3_000_000:
        open(p, "w").write(txt)
        files = {p: len(txt)}
    else:
        sigkeys = ("links", "event_timeline", "direction", "speed")
        signals = {r: {k_: out["walks"][r].pop(k_) for k_ in sigkeys} for r in out["walks"]}
        for r in signals:
            signals[r]["cnn_evolution"] = out["walks"][r]["evidence"].pop("cnn_evolution")
        core = json.dumps(out, separators=(",", ":"))
        sg = json.dumps({"schema_version": "id_teaching_pack_v1", "generated_at": out["generated_at"], "git_commit": out["git_commit"],
                         "walks": signals, "map_frequency_axis_hz": out["walks"]["wrong"]["map_frequency_axis_hz"]}, separators=(",", ":"))
        pc, ps = os.path.join(OUT_DIR, "id_teaching_pack_core.json"), os.path.join(OUT_DIR, "id_teaching_pack_signals.json")
        open(pc, "w").write(core)
        open(ps, "w").write(sg)
        files = {pc: len(core), ps: len(sg)}
    print(json.dumps({"files": files, "check2": chk}, indent=1, default=str), flush=True)
    return {"files": files, "check2": chk}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="mps", choices=("cpu", "mps"))
    ap.add_argument("--final", action="store_true")
    x = ap.parse_args()
    build(x.device, x.final)
    sys.exit(0)
