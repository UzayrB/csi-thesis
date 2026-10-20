# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: ARM (d): CAUSAL PER-SESSION ADAPTATION.

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.constrained.night_common import set_half_roots
set_half_roots(REPO_ROOT)
from pipeline.constrained._guard import assert_isolated
assert_isolated("u1_adapt", os.path.join(REPO_ROOT, "runs", "artefacts_half"))

import time

import numpy as np

from pipeline.constrained.common import E_POST, pairings, status, tag_of
from pipeline.constrained.fh_common import check_contract, claim_fh, release, save
from pipeline.constrained.night_common import boot_ci
from pipeline.constrained.q1_diag import REGIONS, region_of
from pipeline.constrained.rebuild_common import WINDOW_S, findings, headline
from pipeline.constrained.t1_region import (BASELINE_PCT, SHIP_ACC_PCT,
                                            assert_grouped_by_pass, confusion, fit_predict,
                                            pct_ci, prepress_indices)
from pipeline.constrained.t2_embed import load_heads, tag_for_session

STAGE = "u1_adapt"
SELECTION_FOLDS = ("s01_to_s02", "s02_to_s01")
SESSION01_FOLDS = ("s02_to_s01", "s03_to_s01", "s0203_to_s01")
DEMO_TAG = "s0102_to_s03"
SEED = 0
CALIB_MODE = "idle"


# Windows before the first press whose mode is idle.
def calibration_indices(rec, fp) -> np.ndarray:
    if not fp:
        return np.zeros(0, int)
    first = float(min(fp.values()))
    t0 = np.asarray(rec.t0, float)
    sel = np.flatnonzero((t0 + WINDOW_S <= first + 1e-9)
                         & (np.asarray(rec.mode).astype(str) == CALIB_MODE))
    return sel


# Recompute every BatchNorm2d running statistic from this session's own calibration windows.
def adapt_batchnorm(heads, F, R):
    import copy

    import torch
    import torch.nn as nn
    from pipeline.constrained.nets import stack_link
    torch.set_num_threads(1)
    out = []
    for li, (m0, mu, sd) in enumerate(heads):
        m = copy.deepcopy(m0)
        bns = [q for q in m.modules() if isinstance(q, nn.BatchNorm2d)]
        if not bns:
            out.append((m, mu, sd))
            continue
        for q in bns:
            q.reset_running_stats()
            q.momentum = None
            q.train()
        Xb = stack_link(F[:, [li]], R[:, [li]])
        Xb = ((Xb - mu) / sd).astype(np.float32)
        with torch.no_grad():
            for i in range(0, len(Xb), 32):
                m(torch.from_numpy(Xb[i:i + 32]))
        m.eval()
        out.append((m, mu, sd))
        del Xb
    return out


# The comparator: replace the training mu and sd with this session's own statistics.
def adapt_input_norm(heads, F, R):
    from pipeline.constrained.nets import per_channel_stats, stack_link
    out = []
    for li, (m, mu, sd) in enumerate(heads):
        Xb = stack_link(F[:, [li]], R[:, [li]])
        mu2, sd2 = per_channel_stats(Xb)
        out.append((m, mu2, sd2))
        del Xb
    return out


# (n, 3 * EMBED) from whichever head set is handed in.
def embed_rows(heads, F, R, batch: int = 32) -> np.ndarray:
    import torch
    from pipeline.constrained.nets import stack_link
    torch.set_num_threads(1)
    parts = []
    for li, (m, mu, sd) in enumerate(heads):
        Xb = stack_link(F[:, [li]], R[:, [li]])
        Xb = ((Xb - mu) / sd).astype(np.float32)
        ch = []
        with torch.no_grad():
            for i in range(0, len(Xb), batch):
                ch.append(m.embed(torch.from_numpy(Xb[i:i + batch])).numpy())
        parts.append(np.concatenate(ch) if ch else np.zeros((0, 1), np.float32))
        del Xb
    return np.concatenate(parts, axis=1).astype(np.float32)


# One feature row per pass, under a named adaptation mode, plus the calibration audit.
def session_rows(sessions, st, mode: str, cache: dict):
    from pipeline.constrained.p1_runup import first_presses
    from pipeline.constrained.recordings import load_features, load_meta, load_rssi, recordings
    xy = np.asarray(st.xy)
    starts = {nm: xy[st.slice_of[nm][0]] for nm in st.names}
    X, y, keys, who, used = [], [], [], [], {}
    audit = {}
    for sess, stem in recordings():
        if sess not in sessions:
            continue
        ck = f"{mode}|{sess}|{stem}"
        if ck not in cache:
            tag = tag_for_session(sess)
            base = load_heads(tag) if tag else None
            if base is None:
                continue
            rec = load_meta(sess, stem)
            fp = first_presses(sess, stem)
            t0 = np.asarray(rec.t0, float)
            cal = calibration_indices(rec, fp)
            idx, order = [], []
            for pid, nm, _a, _b in rec.pass_spans():
                press = fp.get(int(pid))
                if press is None or nm not in starts:
                    continue
                sel = prepress_indices(t0, press)
                if len(sel) < 2:
                    continue
                order.append((int(pid), nm, list(map(int, sel))))
                idx += list(map(int, sel))
            if not idx:
                continue
            t_s = time.time()
            heads = base
            if mode != "none" and len(cal) >= 20:
                Fc = load_features(sess, stem, list(map(int, cal))).astype(np.float32)
                Rc = load_rssi(sess, stem, rec.t0_epoch)[cal].astype(np.float32)
                heads = (adapt_batchnorm(base, Fc, Rc) if mode == "adabn"
                         else adapt_input_norm(base, Fc, Rc))
                del Fc, Rc
            F = load_features(sess, stem, idx).astype(np.float32)
            R = load_rssi(sess, stem, rec.t0_epoch)[np.asarray(idx, int)].astype(np.float32)
            E = embed_rows(heads, F, R)
            del F, R
            pos, k = {}, 0
            for pid, nm, sel in order:
                pos[pid] = E[k:k + len(sel)]
                k += len(sel)
            cache[ck] = {"emb": pos, "order": order}
            audit[f"{sess}|{stem}"] = {
                "n_calibration_windows": int(len(cal)),
                "adapted": bool(mode != "none" and len(cal) >= 20),
                "latest_calibration_window_end_minus_first_press_s": (
                    None if not len(cal) else
                    float((t0[cal].max() + WINDOW_S) - float(min(fp.values())))),
                "all_calibration_windows_are_idle": bool(
                    len(cal) == 0 or set(np.asarray(rec.mode)[cal].astype(str)) == {CALIB_MODE}),
                "seconds": round(time.time() - t_s, 1)}
        rec = load_meta(sess, stem)
        for pid, nm, sel in cache[ck]["order"]:
            if nm not in starts:
                continue
            e = cache[ck]["emb"][pid]
            f = np.concatenate([np.nanmean(e, axis=0).ravel(), e[-1].ravel()])
            key = f"{sess}|{stem}|{int(pid)}"
            X.append(np.where(np.isfinite(f), f, 0.0))
            y.append(region_of(starts[nm]))
            keys.append(key)
            who.append(stem)
            used[key] = list(sel)
    return (np.vstack(X) if X else np.zeros((0, 1))), np.asarray(y), keys, np.asarray(who), used, audit


# Function main.
def main() -> int:
    lock = claim_fh(STAGE)
    t0 = time.time()
    from pipeline.constrained import paths as P
    st = P.states()
    status(f"{STAGE} START: arm (d), causal per-session adaptation. A PILOT in Room A")

    RES = {"stage": STAGE, "brief": "reports/PREREG_prepress_v2_2026-09-22.md",
           "arm": "(d) causal per-session adaptation",
           "IS_A_PILOT": ("Room A's only per-session anchor varies 2.3x across three days and that "
                          "alone produced 3.33 points of scatter in t8_calib. A NULL HERE IS "
                          "'untestable with Room A's anchor', NEVER 'adaptation does not work'"),
           "calibration_windows": ("mode == 'idle' AND ending at or before the first press. The 24 "
                                   "walk_edge windows in that period are the first evaluated "
                                   "pass's own run-up and are EXCLUDED, which refines t8_calib"),
           "adabn_available": "checked: pipeline/constrained/link_cnn.py:67 has nn.BatchNorm2d",
           "baseline_pct": BASELINE_PCT, "ship_accuracy_pct": SHIP_ACC_PCT,
           "modes": ["none", "adabn", "input_norm"],
           "per_mode": {}, "calibration_audit": {}, "failures": []}

    cache = {}
    for mode in ("none", "adabn", "input_norm"):
        per_tag, allp, allt, allk = {}, [], [], []
        line = {"hit": {}, "n": {}}
        try:
            for tr_s, te_s in pairings():
                if tr_s == te_s or len(te_s) != 1:
                    continue
                tag = tag_of(tr_s, te_s, False)
                Xtr, ytr, ktr, _w1, utr, a1 = session_rows(tr_s, st, mode, cache)
                Xte, yte, kte, _w2, ute, a2 = session_rows(te_s, st, mode, cache)
                if not len(Xtr) or not len(Xte):
                    continue
                assert_grouped_by_pass(ktr, utr)
                assert_grouped_by_pass(kte, ute)
                assert not (set(ktr) & set(kte)), "leakage: a pass on both sides"
                RES["calibration_audit"].update(a1)
                RES["calibration_audit"].update(a2)
                pred, _pr, _cl = fit_predict(Xtr, ytr, Xte)
                hit = [bool(a == b) for a, b in zip(yte, pred)]
                per_tag[tag] = 100.0 * float(np.mean(hit))
                allp += list(pred)
                allt += list(yte)
                allk += list(kte)
                status(f"  {mode:11s} {tag:16s} {per_tag[tag]:5.2f} percent")
            if not per_tag:
                continue
            hits = [bool(a == b) for a, b in zip(allt, allp)]
            for r in REGIONS:
                f = [hits[i] for i in range(len(allt)) if allt[i] == r]
                line["hit"][r] = pct_ci(f)
            v = list(per_tag.values())
            m_, lo_, hi_ = boot_ci(v)
            RES["per_mode"][mode] = {
                "per_pairing": {k: round(x, 3) for k, x in per_tag.items()},
                "median_over_pairings_pct": float(np.median(v)),
                "ci95": [lo_, hi_], "boot_mean": m_,
                "per_pairing_scatter_min_max": [round(min(v), 2), round(max(v), 2)],
                "per_pairing_spread_points": round(max(v) - min(v), 2),
                "session01_folds": {k: round(per_tag.get(k, float("nan")), 3)
                                    for k in SESSION01_FOLDS},
                "session01_median": float(np.median([per_tag[k] for k in SESSION01_FOLDS
                                                     if k in per_tag])),
                "others_median": float(np.median([x for k, x in per_tag.items()
                                                  if k not in SESSION01_FOLDS])),
                "per_region_recall": {r: line["hit"][r] for r in REGIONS},
                "confusion": confusion(allt, allp),
                "n_unique_passes": len(set(allk))}
        except Exception as exc:
            import traceback
            RES["failures"].append({"mode": mode, "error": repr(exc),
                                    "traceback": traceback.format_exc()[-1500:]})
            status(f"  {mode} FAILED: {exc!r}")

    base = RES["per_mode"].get("none")
    for mode in ("adabn", "input_norm"):
        m = RES["per_mode"].get(mode)
        if not m or not base:
            continue
        common = sorted(set(m["per_pairing"]) & set(base["per_pairing"]))
        d = [m["per_pairing"][k] - base["per_pairing"][k] for k in common]
        dm, dlo, dhi = boot_ci(d) if d else (None, None, None)
        d01 = [m["per_pairing"][k] - base["per_pairing"][k]
               for k in SESSION01_FOLDS if k in common]
        m["vs_unadapted"] = {
            "median_paired_delta_points": float(np.median(d)) if d else None,
            "paired_ci": [dlo, dhi], "mean_paired_delta": dm,
            "interval_excludes_zero": bool(dlo is not None and (dlo > 0 or dhi < 0)),
            "session01_deltas": {k: round(m["per_pairing"][k] - base["per_pairing"][k], 3)
                                 for k in SESSION01_FOLDS if k in common},
            "session01_median_delta": float(np.median(d01)) if d01 else None}

    ad = (RES["per_mode"].get("adabn") or {}).get("vs_unadapted") or {}
    lifted = bool(ad.get("interval_excludes_zero")
                  and (ad.get("median_paired_delta_points") or 0) > 0
                  and (ad.get("session01_median_delta") or 0) > 0)
    RES["verdict"] = {
        "adabn_lifts_region_reading": lifted,
        "session01_median_delta_points": ad.get("session01_median_delta"),
        "EXTENSION_TO_THE_TRACKER_RUNS": lifted,
        "if_not": ("recorded as UNTESTABLE WITH ROOM A'S ANCHOR, not as adaptation failing. The "
                   "extension does not run, per the pre-registration"),
        "reading_the_scatter": ("the per-pairing spread is reported beside the median because "
                                "t8_calib showed this anchor produces scatter that a median hides")}

    RES["minutes"] = round((time.time() - t0) / 60.0, 1)
    RES["contract"] = check_contract(RES, ["per_mode", "calibration_audit", "verdict"])
    save(STAGE, RES)
    release(lock)

    for mode, m in RES["per_mode"].items():
        status(f"  {mode:11s} median {m['median_over_pairings_pct']:5.2f}  spread "
               f"{m['per_pairing_spread_points']:5.2f}  session01 {m['session01_median']:5.2f}  "
               f"others {m['others_median']:5.2f}")
    status(f"  AdaBN lifts session-01 region reading: {lifted}")
    headline(f"U1 ADAPT: arm (d) pilot. AdaBN median "
             f"{(RES['per_mode'].get('adabn') or {}).get('median_over_pairings_pct')} against "
             f"unadapted {(base or {}).get('median_over_pairings_pct')}; session-01 delta "
             f"{ad.get('session01_median_delta')}; extension runs = {lifted}")
    findings("u1adapt", bool(RES["contract"]["SATISFIED"]), (
        f"ARM (d), CAUSAL PER-SESSION ADAPTATION. A PILOT IN ROOM A.\n\n" +
        "\n".join(f"  {k:11s} median {v['median_over_pairings_pct']:5.2f}  spread "
                  f"{v['per_pairing_spread_points']:5.2f}  session01 {v['session01_median']:5.2f}"
                  f"  others {v['others_median']:5.2f}"
                  for k, v in RES["per_mode"].items()) +
        f"\n\nAdaBN against unadapted: paired {ad.get('median_paired_delta_points')} points, "
        f"ci {ad.get('paired_ci')}, session-01 delta {ad.get('session01_median_delta')}.\n"
        f"Lifts session-01 region reading: {lifted}.\n"
        f"If not lifted this is UNTESTABLE WITH ROOM A'S ANCHOR, not adaptation failing.\n"
        f"Brief: reports/PREREG_prepress_v2_2026-09-22.md"))
    return 0 if RES["contract"]["SATISFIED"] else 1


if __name__ == "__main__":
    sys.exit(main())
