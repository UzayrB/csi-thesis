"""iwg_screen. The window and gait brief's scoring (`runs/identify/engine/PLAN.md`, the note of 2026-10-01 20:15): every row
against engine v3 on the natural, slow and fast identification walks, with S_wifi on the row's own windows.

    cnn --arm T4.0 --device mps     v3's CNN weights (three seeds) on the arm's maps, AdaBN on same-layout pools (cached)
    partA                            every Part A arm (needs the CNN caches); the T 3.0 anchor
    partB --arm T4.0                 Part B's gait columns on the carried arm (B1, B2, with and without the speed column)
    table                            every row so far

Each walks fold uses its own bank (the end detector's alpha is fitted per fold on its training sessions). Development
evaluation, all data seen; the engine does not change.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import pickle
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idv2_core as C
from pipeline.identify import idw_eval as EV
from pipeline.identify import idx_loso as L
from pipeline.identify import ils_common as IL
from pipeline.identify import iwg_bank as WB

OUT = WB.OUT
ROWS = os.path.join(OUT, "rows")
TAGS = ("cnn3", "cnn_link0", "cnn_link1", "cnn_link2")
BLOCKS = ("natural", "slow", "fast")
GAIN, GUARD = 4.45, -4.45


# ------------------------------------------------------------------ data

def alpha_of(fold: str) -> float:
    if fold.startswith("A"):                       # the Room A folds (the lean-in brief): fitted on both Room B days
        return json.load(open(os.path.join("runs", "identify", "lean_in", "alpha_A.json")))["alpha"]
    return json.load(open(os.path.join(OUT, "alpha.json")))["folds"][f"to{fold}"]["alpha"]


_BANK = {}


def bank(a: float) -> dict:
    """Every arm's per-row data over the 1,019 bank rows, merged from the five sessions' pickles for one alpha."""
    if a not in _BANK:
        parts = [pickle.load(open(os.path.join(OUT, "bank", f"a{a}", f"{s}.pkl"), "rb")) for s in ("A1", "A2", "A3", "B1", "B2")]
        out = {}
        for arm in WB.ARMS:
            rows = np.concatenate([p[arm]["rows"] for p in parts])
            o = np.argsort(rows)
            assert np.array_equal(rows[o], np.arange(len(rows)))
            g = {"features": np.concatenate([p[arm]["features"] for p in parts])[o],
                 "maps": [m for p in parts for m in p[arm]["maps"]],
                 "spec": [m for p in parts for m in p[arm]["spec"]], "spec_f": parts[0][arm]["spec_f"]}
            g["maps"] = [g["maps"][i] for i in o]
            g["spec"] = [g["spec"][i] for i in o]
            for k in ("wifi_speed", "end_s", "dec_s", "walk_end_s"):
                g[k] = np.concatenate([p[arm][k] for p in parts])[o]
            out[arm] = g
        more = [os.path.join(OUT, "bank", f"a{a}", f"{s}_more.pkl") for s in ("A1", "A2", "A3", "B1", "B2")]
        if all(os.path.exists(p) for p in more):          # the lean-in brief's additions (T 3.75, 4.25 s; RX1 series)
            mparts = [pickle.load(open(p, "rb")) for p in more]
            for arm in WB.MORE:
                rows = np.concatenate([p[arm]["rows"] for p in mparts])
                o = np.argsort(rows)
                assert np.array_equal(rows[o], np.arange(len(rows)))
                g = {"features": np.concatenate([p[arm]["features"] for p in mparts])[o],
                     "maps": [m for p in mparts for m in p[arm]["maps"]], "spec": [m for p in mparts for m in p[arm]["spec"]],
                     "spec_f": mparts[0][arm]["spec_f"]}
                g["maps"] = [g["maps"][i] for i in o]
                g["spec"] = [g["spec"][i] for i in o]
                for k in ("wifi_speed", "end_s", "dec_s", "walk_end_s"):
                    g[k] = np.concatenate([p[arm][k] for p in mparts])[o]
                out[arm] = g
            rows = np.concatenate([p["rx1"]["rows"] for p in mparts])
            o = np.argsort(rows)
            out["rx1"] = {arm: [[x for p in mparts for x in p["rx1"][arm]][i] for i in o] for arm in WB.RX1_ARMS}
        _BANK[a] = out
    return _BANK[a]


def arm(arm_name: str, fold: str) -> dict:
    return bank(alpha_of(fold))[arm_name]


_V3 = {}


def v3() -> dict:
    """Engine v3's replays (the reference) and the bank labels."""
    if not _V3:
        d = IL.data()
        meta = json.load(open(os.path.join(os.path.join(EN.ENG, "bank_T3.0_v3"), "meta.json")))["passes"]
        rep = {}
        for s in IL.SESS:
            z = np.load(os.path.join(EN.ENG, "replays", f"loso_{s}_v3_{s}_T3.0.npz"))
            rep[s] = {k: z[k] for k in z.files}
            assert np.array_equal(rep[s]["te"], d["rep"][s]["te"])
        _V3.update({"rep": rep, "dur": np.array([m["t_end"] - m["t_start"] for m in meta]),
                    "Xv3": np.load(os.path.join(os.path.join(EN.ENG, "bank_T3.0_v3"), "features.npy")),
                    "wifi_v3": np.array([m["wifi_speed"] for m in meta], float)})
    return _V3


def positions(s: str) -> dict:
    """Replay positions of the identification walks of session s, by block."""
    d = IL.data()
    te = d["rep"][s]["te"]
    return {b: np.flatnonzero((d["a"]["kind"][te] == "idcap") & (d["a"]["block"][te] == b)) for b in BLOCKS}


# ------------------------------------------------------------------ CNN components on an arm's maps

def cnn_outputs(fold: str, maps: list, device: str, nets: dict = None, seeds=(0, 1, 2)) -> dict:
    """v3's CNN networks (or `nets` {(tag, seed): net}) on `maps`, in replay order, AdaBN on same-layout pools."""
    d = IL.data()
    model = EN.Model(os.path.join(EN.ENG, "models", f"loso_{fold}_v3"), device)
    if nets:
        for key, net in nets.items():
            model.nets[key] = net.to(device)
    model.meta = dict(model.meta, seeds=list(seeds))
    r = d["rep"][fold]
    te, paths = r["te"], r["path_used"]
    plain = np.zeros((len(te), len(seeds), 6))
    adapt = np.zeros((len(te), len(TAGS), len(seeds), 6))
    pools = {}
    for k, (i, path) in enumerate(zip(te, paths)):
        sess = pools.setdefault(d["a"]["layout"][i], EN.Session(model))
        Wn = C.windows(maps[i])
        for ti, tag in enumerate(TAGS):
            Xw, dw, pw = sess._cnn_input(tag, [Wn], [str(path)])
            for si, sd in enumerate(seeds):
                if tag == "cnn3":
                    plain[k, si] = C.normalise_logp(C.pass_logp(model.nets[(tag, sd)], Xw, dw, pw, 1, 6, device))[0]
                net = sess.adapted.get((tag, sd), model.nets[(tag, sd)])
                adapt[k, ti, si] = C.normalise_logp(C.pass_logp(net, Xw, dw, pw, 1, 6, device))[0]
        sess.add({"features": d["X"][i], "wifi_speed": 0.0, "path": str(path), "maps": maps[i]})
        if device == "mps":
            import torch
            torch.mps.empty_cache()                   # release varying-size blocks (the 1 Oct out-of-memory lesson)
    return {"te": te, "plain": plain, "adapt": adapt}


def cnn_cache(arm_name: str, fold: str) -> str:
    return os.path.join(OUT, "cnn", f"{arm_name}_to{fold}.npz")


def run_cnn(arm_name: str, device: str) -> None:
    for fold in IL.SESS:
        p = cnn_cache(arm_name, fold)
        if os.path.exists(p):
            continue
        t = time.time()
        z = cnn_outputs(fold, arm(arm_name, fold)["maps"], device)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        np.savez(p, **z)
        print(f"{time.strftime('%H:%M:%S')} cnn {arm_name} to{fold}: {time.time() - t:.0f} s", flush=True)


def cnn_components(arm_name: str, fold: str) -> dict:
    from pipeline.identify import ils_cnn as CN
    z = np.load(cnn_cache(arm_name, fold))
    return CN.components({k: z[k] for k in z.files})


# ------------------------------------------------------------------ scoring

def s_wifi(wifi: np.ndarray, fold: str) -> np.ndarray:
    """S_wifi's log-probabilities on fold's replay windows: an LDA on the Wi-Fi speed alone, trained on the other Room B
    day's identification walks (`ixa_measures.lda_one`'s arithmetic)."""
    d = IL.data()
    a = d["a"]
    other = "B1" if fold == "B2" else "B2"
    tr = np.flatnonzero((a["session"] == other) & (a["kind"] == "idcap") & np.isfinite(wifi))
    te = d["rep"][fold]["te"]
    x = np.where(np.isfinite(wifi[te]), wifi[te], np.nanmedian(wifi[tr]))
    P, cl = C.lda_proba(wifi[tr][:, None], x[:, None], a["anon"][tr])
    return L._order(C.logp_from_proba(P), cl)


def _ok(lp: np.ndarray, s: str, b: str) -> np.ndarray:
    d = IL.data()
    k = positions(s)[b]
    te = d["rep"][s]["te"][k]
    return (IL.CL[np.asarray(lp)[k].argmax(1)] == d["a"]["anon"][te]).astype(float)


def score(rid: str, part: str, what: str, ens: dict, wifi: dict, dec: dict = None, end: dict = None,
          ref: dict = None, ref_sw: float = None, extra: dict = None, mark: bool = True) -> dict:
    """One row: natural, slow and fast paired against the reference (v3 unless `ref` gives ensembles per fold)."""
    d = IL.data()
    V = v3()
    refe = ref or {s: V["rep"][s]["ensemble"] for s in IL.SESS}
    rec = {"id": rid, "part": part, "row": what, "label": IL.LABEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "reference": "engine v3" if ref is None else "the same-seed baseline", "blocks": {}}
    for b in BLOCKS:
        ok = np.concatenate([_ok(ens[s], s, b) for s in IL.SESS])
        rk = np.concatenate([_ok(refe[s], s, b) for s in IL.SESS])
        who = np.concatenate([d["a"]["anon"][d["rep"][s]["te"][positions(s)[b]]] for s in IL.SESS])
        sw = np.concatenate([_ok(s_wifi(wifi[s], s), s, b) for s in IL.SESS])
        rec["blocks"][b] = {"acc": EV._boot(ok, who), "paired": EV.paired(ok, rk, who), "S_wifi": EV._boot(sw, who),
                            "minus_S_wifi": EV.paired(ok, sw, who)}
    nat = {s: _ok(ens[s], s, "natural") for s in IL.SESS}
    natr = {s: _ok(refe[s], s, "natural") for s in IL.SESS}
    for s in IL.SESS:
        rec[f"to{s}"] = round(100 * float(nat[s].mean()), 2)
        rec[f"paired_to{s}"] = round(100 * float(nat[s].mean() - natr[s].mean()), 2)
    pred = np.concatenate([IL.CL[np.asarray(ens[s])[positions(s)["natural"]].argmax(1)] for s in IL.SESS])
    who = np.concatenate([d["a"]["anon"][d["rep"][s]["te"][positions(s)["natural"]]] for s in IL.SESS])
    rec["pa1"] = int((pred == "P2").sum())
    j = who == "P3"
    rec["pa2"] = f"{int(np.concatenate(list(nat.values()))[j].sum())} of {int(j.sum())}"
    rec["per_person"] = {IL.NAME[p]: round(100 * float(np.concatenate(list(nat.values()))[who == p].mean()), 2)
                         for p in L.CLASSES}
    if dec is not None:
        rec["decision_s_median_natural"] = round(float(np.median(np.concatenate(
            [dec[s][d["rep"][s]["te"][positions(s)["natural"]]] for s in IL.SESS]))), 3)
        rec["ran_past_end_press"] = {}
        for b in BLOCKS:
            rr = np.concatenate([d["rep"][s]["te"][positions(s)[b]] for s in IL.SESS])
            e = np.concatenate([end[s][d["rep"][s]["te"][positions(s)[b]]] for s in IL.SESS])
            rec["ran_past_end_press"][b] = round(100 * float(np.mean(e > V["dur"][rr] + 1e-9)), 1)
    g = rec["blocks"]["natural"]["paired"]["pct"]
    sl, fa = rec["blocks"]["slow"]["paired"]["pct"], rec["blocks"]["fast"]["paired"]["pct"]
    msw = rec["blocks"]["natural"]["minus_S_wifi"]["pct"]
    rec["rule_ref_minus_S_wifi"] = ref_sw
    if mark:
        ok4 = ref_sw is None or msw >= ref_sw - 1e-9
        if g >= GAIN and rec["paired_toB1"] > 0 and rec["paired_toB2"] > 0 and sl >= GUARD and fa >= GUARD and ok4:
            rec["verdict"] = "PROMISING"
        elif g <= GUARD:
            rec["verdict"] = "WORSE"
        else:
            rec["verdict"] = "FLAT"
    else:
        rec["verdict"] = "information"
    if extra:
        rec["extra"] = extra
    rec["named"] = [IL.NAME[p] for p in pred]
    IL.dump(os.path.join(ROWS, f"{rid}.json"), rec)
    B = rec["blocks"]
    print(f"{time.strftime('%H:%M:%S')} {rid:<26} nat {B['natural']['acc']['pct']:6.2f} ({g:+6.2f} "
          f"[{B['natural']['paired']['ci95'][0]:+.2f}, {B['natural']['paired']['ci95'][1]:+.2f}])  slow {sl:+6.2f}  "
          f"fast {fa:+6.2f}  B1 {rec['paired_toB1']:+.2f} B2 {rec['paired_toB2']:+.2f}  PA1 {rec['pa1']:3d}  "
          f"PA2 {rec['pa2']}  -Swifi {msw:+.2f}  dec {rec.get('decision_s_median_natural', float('nan')):.2f}  {rec['verdict']}",
          flush=True)
    return rec


def feat_comps(arm_name: str, cfg_extra: dict = None) -> tuple:
    """The five feature components per fold, retrained on the arm's windows (its own bank per fold), same-layout pools."""
    from pipeline.identify import ils_feat as FT
    d = IL.data()
    out, wifi = {}, {}
    for s in IL.SESS:
        g = arm(arm_name, s)
        cfg = {"G": g["features"].astype(np.float64)[:, EN.v2_columns(d["names"])], "pace": g["wifi_speed"], "pool": "layout",
               **(cfg_extra(s) if callable(cfg_extra) else (cfg_extra or {}))}
        out[s] = FT.rescore(FT.train(d, s, cfg), d, s, cfg)
        wifi[s] = g["wifi_speed"]
    return out, wifi


REF_SW = {}


def reference_minus_s_wifi() -> float:
    """Engine v3's own natural engine minus S_wifi in this pipeline (rule point 4's floor)."""
    if not REF_SW:
        V = v3()
        r = score("v3_reference", "A", "engine v3 (its replays; the reference)", {s: V["rep"][s]["ensemble"] for s in IL.SESS},
                  {s: V["wifi_v3"] for s in IL.SESS}, mark=False)
        REF_SW["v"] = r["blocks"]["natural"]["minus_S_wifi"]["pct"]
    return REF_SW["v"]


def part_a() -> None:
    d = IL.data()
    V = v3()
    sw0 = reference_minus_s_wifi()
    anchor = {}
    for arm_name in WB.ARMS:
        t = time.time()
        feats, wifi = feat_comps(arm_name)
        ens = {s: IL.ensemble({**feats[s], **cnn_components(arm_name, s)}) for s in IL.SESS}
        dec = {s: arm(arm_name, s)["dec_s"] for s in IL.SESS}
        end = {s: arm(arm_name, s)["end_s"] for s in IL.SESS}
        info = arm_name == "Woracle"
        r = score(f"A.{arm_name}", "A", {"T3.0": "fixed 3.0 s (this pipeline's anchor of v3)"}.get(arm_name, arm_name),
                  ens, wifi, dec, end, ref_sw=sw0, mark=not info and arm_name != "T3.0",
                  extra={"alpha": {f"to{s}": alpha_of(s) for s in IL.SESS}, "seconds": round(time.time() - t, 1)})
        if arm_name == "T3.0":
            for s in IL.SESS:
                te = d["rep"][s]["te"]
                g = arm("T3.0", s)
                feq = int(np.sum(np.all(np.isclose(g["features"][te], V["Xv3"][te], equal_nan=True, rtol=0, atol=0), axis=1)))
                same = int(np.sum(ens[s].argmax(1) == V["rep"][s]["ensemble"].argmax(1)))
                anchor[f"to{s}"] = {"features_equal_v3_bank": f"{feq} of {len(te)}", "decisions_equal_v3": f"{same} of {len(te)}",
                                    "truncated_by_next_press": int(np.sum(g["end_s"][te] < 3.0 - 1e-9)),
                                    "ensemble_max_abs_diff": float(np.abs(ens[s] - V["rep"][s]["ensemble"]).max())}
    IL.dump(os.path.join(OUT, "anchor_T3.0.json"), anchor)
    print(json.dumps(anchor, indent=1), flush=True)
    # the detected end (W-radio) against the true end press, by block (information)
    det = {}
    for s in IL.SESS:
        g = arm("Wradio", s)
        for b in BLOCKS:
            rr = d["rep"][s]["te"][positions(s)[b]]
            e = g["end_s"][rr] - V["dur"][rr]
            det.setdefault(b, []).append(e)
    det = {b: {"median_signed_s": round(float(np.median(np.concatenate(v))), 3),
               "median_abs_s": round(float(np.median(np.abs(np.concatenate(v)))), 3),
               "p90_abs_s": round(float(np.percentile(np.abs(np.concatenate(v)), 90)), 3)} for b, v in det.items()}
    IL.dump(os.path.join(OUT, "wradio_end_error.json"), det)
    print(json.dumps(det, indent=1), flush=True)


# ------------------------------------------------------------------ Part B: gait parameters on the carried window

def contour(g: dict, i: int, E: np.ndarray, path: str, layout: str) -> np.ndarray:
    """The per-frame speed on the walking span (PLAN B2): A1's estimator on identification-spot windows, else the best
    link's power-weighted centroid in the torso band scaled by F / 0.98; NaN where a frame is not kept."""
    P, f = np.asarray(g["spec"][i], float), np.asarray(g["spec_f"], float)
    if layout == "id_spot":
        F, lo, hi = 0.98, 10.0, 35.0
    else:
        _li, F = EN.best_link(path, layout)
        if F < EN.F_MIN:
            return np.full(P.shape[1], np.nan)
        lo, hi = 10.0 * F / 0.98, 35.0 * F / 0.98
    m = (f >= lo) & (f < hi)
    Pb = P[m]
    if layout == "id_spot":
        Pb = np.maximum(Pb - E[:, None], 0.0)
    e = Pb.sum(axis=0)
    out = np.full(P.shape[1], np.nan)
    if not P.shape[1] or not np.any(e > 0):
        return out
    keep = (e > np.percentile(e, 25)) & (e > 0)
    c = (f[m][:, None] * Pb).sum(axis=0) / np.where(e > 0, e, 1.0)
    out[keep] = c[keep] * EN.LAMBDA / (2.0 * F)
    return out


def contour_columns(v: np.ndarray, f_step: float) -> np.ndarray:
    """mean, fluctuation at the step rate / mean, steady speed, t90, start ratio (PLAN B2)."""
    tk = WB.C0_S + WB.HOP_S * np.arange(len(v))
    ok = np.isfinite(v)
    out = np.full(5, np.nan)
    if ok.sum() < 3:
        return out
    mean = float(np.mean(v[ok]))
    out[0] = mean
    if f_step and np.isfinite(f_step) and ok.sum() >= 8 and mean > 0:
        X = np.c_[np.ones(ok.sum()), np.cos(2 * np.pi * f_step * tk[ok]), np.sin(2 * np.pi * f_step * tk[ok])]
        coef = np.linalg.lstsq(X, v[ok], rcond=None)[0]
        out[1] = float(np.hypot(coef[1], coef[2]) / mean)
    half = tk >= tk[-1] / 2.0
    steady = float(np.median(v[ok & half])) if np.any(ok & half) else float(np.median(v[ok]))
    out[2] = steady
    hit = np.flatnonzero(ok & (v >= 0.9 * steady))
    out[3] = float(tk[hit[0]]) if len(hit) else np.nan
    early = ok & (tk <= 0.5)
    out[4] = float(np.median(v[early]) / steady) if np.any(early) and steady > 0 else np.nan
    return out


def gait_columns(arm_name: str, fold: str) -> dict:
    """B1 and B2 columns over the 1,019 rows, for one fold (its bank, its training rows, its empty-room spectrum)."""
    from pipeline.identify import ixa_speed as XS
    d = IL.data()
    meta = json.load(open(os.path.join(os.path.join(EN.ENG, "bank_T3.0_v3"), "meta.json")))["passes"]
    g = arm(arm_name, fold)
    _rows, emp = None, pickle.load(open(os.path.join("runs", "identify", "final_extras", "a_data", "empty_idspot.pkl"), "rb"))
    E = XS.empty_spectrum(emp, XS.room_b_training_days(fold))
    ci = d["names"].index("cad|all|-|-|cadence_hz")
    f = g["features"][:, ci].astype(float)
    v = g["wifi_speed"]
    tr = d["tr"][fold]
    ok = np.isfinite(f[tr]) & np.isfinite(v[tr])
    b, a0 = np.polyfit(v[tr][ok], f[tr][ok], 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        b1 = np.c_[v / f ** 2, v / f, f - (a0 + b * v)]
    b2, a1 = [], []
    for i, m in enumerate(meta):
        lay = "id_spot" if m["kind"] == "idcap" else "home"
        vk = contour(g, i, E, m["engine_path"], lay)
        b2.append(contour_columns(vk, f[i]))
        a1.append(float(np.nanmedian(vk)) if (lay == "id_spot" and np.isfinite(vk).any()) else np.nan)
    return {"B1": b1, "B2": np.asarray(b2), "A1_speed": np.asarray(a1), "line": (float(a0), float(b)), "f_step": f}


def part_b(arm_name: str) -> None:
    from scipy import stats
    d = IL.data()
    sw0 = reference_minus_s_wifi()
    cols = {s: gait_columns(arm_name, s) for s in IL.SESS}
    cnn = {s: cnn_components(arm_name, s) for s in IL.SESS}
    meta = json.load(open(os.path.join(os.path.join(EN.ENG, "bank_T3.0_v3"), "meta.json")))["passes"]
    info = {"carried_arm": arm_name, "speed_cadence_line": {f"to{s}": cols[s]["line"] for s in IL.SESS}}
    # identity-blind information: A1's speed on this window against press speed; the usable step-rate share
    x, y = [], []
    for s in IL.SESS:
        rr = d["rep"][s]["te"][positions(s)["natural"]]
        x.append(cols[s]["A1_speed"][rr])
        y.append(np.array([meta[i]["press_speed_m_s"] for i in rr], float))
    x, y = np.concatenate(x), np.concatenate(y)
    k = np.isfinite(x) & np.isfinite(y)
    info["A1_speed_pearson_natural"] = {"r": round(float(stats.pearsonr(x[k], y[k])[0]), 3), "n": int(k.sum())}
    ci = d["names"].index("cad|all|-|-|cadence_hz")
    for nm in (arm_name, "T3.0"):
        u = []
        for s in IL.SESS:
            rr = d["rep"][s]["te"][positions(s)["natural"]]
            u.append(np.isfinite(arm(nm, s)["features"][rr, ci].astype(float)))
        info[f"usable_step_rate_natural_{nm}"] = round(100 * float(np.mean(np.concatenate(u))), 1)
    IL.dump(os.path.join(OUT, "partB_info.json"), info)
    print(json.dumps(info, indent=1), flush=True)
    carried_ens = {}
    rows = [("B.window_nospeed", "the carried window, no speed column", None, True)]
    for tag, what in (("B1", "walk ratio, step length, speed-normalised cadence"), ("B2", "the contour's five columns"),
                      ("B12", "B1 and B2")):
        for nospeed in (False, True):
            rows.append((f"B.{tag}_{'nospeed' if nospeed else 'speed'}", f"{what}, {'without' if nospeed else 'with'} the raw speed column",
                         tag, nospeed))
    for rid, what, tag, nospeed in rows:
        t = time.time()

        def cfg(s, tag=tag, nospeed=nospeed):
            if tag is None:
                ex = None
            else:
                ex = np.c_[tuple(cols[s][p] for p in ("B1", "B2") if p in {"B1": ["B1"], "B2": ["B2"], "B12": ["B1", "B2"]}[tag])]
            return {"extra": ex, "nopace": nospeed}
        feats, wifi = feat_comps(arm_name, cfg)
        ens = {s: IL.ensemble({**feats[s], **cnn[s]}) for s in IL.SESS}
        score(rid, "B", f"{arm_name}: {what}", ens, wifi, {s: arm(arm_name, s)["dec_s"] for s in IL.SESS},
              {s: arm(arm_name, s)["end_s"] for s in IL.SESS}, ref_sw=sw0, extra={"seconds": round(time.time() - t, 1)})


def table() -> None:
    recs = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(ROWS, "*.json")))]
    lines = ["| part | row | natural (paired) | slow (paired) | fast (paired) | to B1 | to B2 | PA1 | PA2 | decision (s) | engine - S_wifi, natural | verdict |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(recs, key=lambda x: (x["part"], -x["blocks"]["natural"]["paired"]["pct"])):
        B = r["blocks"]
        f = lambda b: f"{B[b]['acc']['pct']:.2f} ({B[b]['paired']['pct']:+.2f} [{B[b]['paired']['ci95'][0]:+.2f}, {B[b]['paired']['ci95'][1]:+.2f}])"  # noqa: E731
        lines.append(f"| {r['part']} | {r['row']} | {f('natural')} | {f('slow')} | {f('fast')} | {r['toB1']:.2f} ({r['paired_toB1']:+.2f}) | "
                     f"{r['toB2']:.2f} ({r['paired_toB2']:+.2f}) | {r['pa1']} | {r['pa2'].replace(' of 30', '')} | "
                     f"{r.get('decision_s_median_natural', float('nan')):.2f} | {B['natural']['minus_S_wifi']['pct']:+.2f} "
                     f"[{B['natural']['minus_S_wifi']['ci95'][0]:+.2f}, {B['natural']['minus_S_wifi']['ci95'][1]:+.2f}] | {r['verdict']} |")
    open(os.path.join(OUT, "table.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("what", choices=("cnn", "partA", "partB", "table"))
    ap.add_argument("--arm")
    ap.add_argument("--device", default="mps", choices=("cpu", "mps"))
    x = ap.parse_args(argv)
    if x.what == "cnn":
        run_cnn(x.arm, x.device)
    elif x.what == "partA":
        part_a()
    elif x.what == "partB":
        part_b(x.arm)
    else:
        table()
    return 0


if __name__ == "__main__":
    sys.exit(main())
