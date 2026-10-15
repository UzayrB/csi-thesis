"""ili_stack. The lean-in brief (`reports/identification/briefs/2026-10-01_lean-in.md`; every rule in
`runs/identify/engine/PLAN.md`, the note of 2026-10-01 22:48): the base window (Part 0), the cheap levers (Part 1), the
stack (Part 3) and the diagnostics (Part 4), scored against engine v3 and against the base or the stack so far.

    cnn --arm T3.75 --folds A1 A2 A3 --device mps   v3's CNN weights on an arm's maps for any folds (cached; GPU,
                                                     one job at a time under runs/identify/lean_in/queue/guard.sh)
    part0                                            plateau, direction, multi-window, the base

Windows come from the window and gait banks (`iwg_bank`, with the T 3.75 and 4.25 s additions). Development
evaluation, all data seen; the engine does not change.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idv2_core as C
from pipeline.identify import idw_eval as EV
from pipeline.identify import ils_common as IL
from pipeline.identify import iwg_bank as WB
from pipeline.identify import iwg_screen as S

OUT = os.path.join("runs", "identify", "lean_in")
ROWS = os.path.join(OUT, "rows")
ENS = os.path.join(OUT, "ens")
ALL = ("A1", "A2", "A3", "B1", "B2")
WINDOWS = ("T3.0", "T3.5", "T3.75", "T4.0", "T4.25", "T4.5", "T5.0", "T6.0")
PLATEAU = ("T3.5", "T3.75", "T4.0", "T4.25", "T4.5")
MULTI = ("T3.0", "T3.5", "T4.0", "T4.5")
ALPHA_A = 0.5            # Room A folds: fitted on both Room B days' identification walks (PLAN; 1.079 s median error)
BLOCKS = ("natural", "slow", "fast")


# ------------------------------------------------------------------ data for every fold

def data() -> dict:
    """`ils_common.data()` extended with the Room A folds (engine v3's replays and training rows)."""
    d = IL.data()
    for s in ALL:
        if s not in d["rep"]:
            z = np.load(os.path.join(EN.ENG, "replays", f"loso_{s}_v3_{s}_T3.0.npz"))
            d["rep"][s] = {k: z[k] for k in z.files}
            d["tr"][s] = np.load(os.path.join(EN.ENG, "models", f"loso_{s}_v3", "train_rows.npy"))
    return d


def arm(name: str, fold: str) -> dict:
    return S.bank(ALPHA_A if fold.startswith("A") else S.alpha_of(fold))[name]


def feat_comps(name: str, folds=IL.SESS, cfg_fn=None) -> tuple:
    """The five feature components retrained on an arm's windows, per fold (its own bank), same-layout pools."""
    from pipeline.identify import ils_feat as FT
    d = data()
    out, wifi = {}, {}
    for s in folds:
        g = arm(name, s)
        cfg = {"G": g["features"].astype(np.float64)[:, EN.v2_columns(d["names"])], "pace": g["wifi_speed"], "pool": "layout",
               **(cfg_fn(s) if cfg_fn else {})}
        out[s] = FT.rescore(FT.train(d, s, cfg), d, s, cfg)
        wifi[s] = g["wifi_speed"]
    return out, wifi


def cnn_cache(name: str, fold: str) -> str:
    return S.cnn_cache(name, fold)


def run_cnn(name: str, folds, device: str) -> None:
    data()
    for s in folds:
        p = cnn_cache(name, s)
        if os.path.exists(p):
            continue
        t = time.time()
        z = S.cnn_outputs(s, arm(name, s)["maps"], device)
        tmp = p[:-4] + ".tmp.npz"
        np.savez(tmp, **z)
        os.replace(tmp, p)
        print(f"{time.strftime('%H:%M:%S')} cnn {name} to{s}: {time.time() - t:.0f} s", flush=True)


def cnn_comps(name: str, fold: str) -> dict:
    return S.cnn_components(name, fold)


def ensemble_of(name: str, folds=IL.SESS) -> dict:
    """An arm's full ensemble (its feature components and v3's CNN weights on its maps), per fold; cached."""
    out = {}
    todo = [s for s in folds if not os.path.exists(os.path.join(ENS, f"{name}_{s}.npz"))]
    if todo:
        feats, _w = feat_comps(name, todo)
        for s in todo:
            os.makedirs(ENS, exist_ok=True)
            comps = {**feats[s], **cnn_comps(name, s)}
            np.savez(os.path.join(ENS, f"{name}_{s}.npz"), ensemble=IL.ensemble(comps),
                     **{f"c_{k}": v for k, v in comps.items()})
    for s in folds:
        z = np.load(os.path.join(ENS, f"{name}_{s}.npz"))
        out[s] = {k: z[k] for k in z.files}
    return out


# ------------------------------------------------------------------ scoring

def _cmp(ens: dict, ref: dict) -> dict:
    d = IL.data()
    out = {}
    for b in BLOCKS:
        ok = np.concatenate([S._ok(ens[s], s, b) for s in IL.SESS])
        rk = np.concatenate([S._ok(ref[s], s, b) for s in IL.SESS])
        who = np.concatenate([d["a"]["anon"][d["rep"][s]["te"][S.positions(s)[b]]] for s in IL.SESS])
        out[b] = EV.paired(ok, rk, who)
    for s in IL.SESS:
        out[f"to{s}"] = round(100 * float(S._ok(ens[s], s, "natural").mean() - S._ok(ref[s], s, "natural").mean()), 2)
    return out


def pa1(ens: dict) -> int:
    return int(sum((IL.CL[np.asarray(ens[s])[S.positions(s)["natural"]].argmax(1)] == "P2").sum() for s in IL.SESS))


def step_rule(vs: dict, ish: int, ref_ish: int) -> dict:
    """The brief's step rule against the stack so far."""
    c = {"natural_gain_ge_2.22": vs["natural"]["pct"] >= 2.22 - 1e-9,
         "no_fold_falls_more_than_3.4": min(vs["toB1"], vs["toB2"]) >= -3.4 - 1e-9,
         "slow_fast_fall_no_more_than_2.5": min(vs["slow"]["pct"], vs["fast"]["pct"]) >= -2.5 - 1e-9,
         "pa1_rise_le_5": ish - ref_ish <= 5}
    c["PASS"] = all(c.values())
    return c


def record(rid: str, part: str, what: str, ens: dict, wifi: dict = None, dec: dict = None, ref: dict = None,
           ref_name: str = None, extra: dict = None) -> dict:
    """One row: against engine v3 and against the reference (the base or the stack so far), with the step rule."""
    d = IL.data()
    V = S.v3()
    v3e = {s: V["rep"][s]["ensemble"] for s in IL.SESS}
    rec = {"id": rid, "part": part, "row": what, "label": IL.LABEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "blocks": {}}
    for b in BLOCKS:
        ok = np.concatenate([S._ok(ens[s], s, b) for s in IL.SESS])
        who = np.concatenate([d["a"]["anon"][d["rep"][s]["te"][S.positions(s)[b]]] for s in IL.SESS])
        rec["blocks"][b] = EV._boot(ok, who)
    for s in IL.SESS:
        rec[f"to{s}"] = round(100 * float(S._ok(ens[s], s, "natural").mean()), 2)
    rec["vs_v3"] = _cmp(ens, v3e)
    rec["pa1"] = pa1(ens)
    nat = np.concatenate([S._ok(ens[s], s, "natural") for s in IL.SESS])
    who = np.concatenate([d["a"]["anon"][d["rep"][s]["te"][S.positions(s)["natural"]]] for s in IL.SESS])
    rec["pa2"] = f"{int(nat[who == 'P3'].sum())} of {int((who == 'P3').sum())}"
    rec["per_person"] = {IL.NAME[p]: round(100 * float(nat[who == p].mean()), 2) for p in IL.L.CLASSES} \
        if hasattr(IL, "L") else None
    if wifi is not None:
        sw = {}
        for b in BLOCKS:
            ok = np.concatenate([S._ok(ens[s], s, b) for s in IL.SESS])
            sk = np.concatenate([S._ok(S.s_wifi(wifi[s], s), s, b) for s in IL.SESS])
            whob = np.concatenate([d["a"]["anon"][d["rep"][s]["te"][S.positions(s)[b]]] for s in IL.SESS])
            sw[b] = {"S_wifi": EV._boot(sk, whob)["pct"], "engine_minus_S_wifi": EV.paired(ok, sk, whob)}
        rec["s_wifi"] = sw
    if dec is not None:
        rec["decision_s_median_natural"] = round(float(np.median(np.concatenate(
            [np.asarray(dec[s])[d["rep"][s]["te"][S.positions(s)["natural"]]] for s in IL.SESS]))), 3)
    if ref is not None:
        rec["reference"] = ref_name
        rec["vs_ref"] = _cmp(ens, ref)
        rec["step_rule"] = step_rule(rec["vs_ref"], rec["pa1"], pa1(ref))
    if extra:
        rec["extra"] = extra
    rec["named"] = [IL.NAME[p] for p in np.concatenate([IL.CL[np.asarray(ens[s])[S.positions(s)["natural"]].argmax(1)]
                                                        for s in IL.SESS])]
    IL.dump(os.path.join(ROWS, f"{rid}.json"), rec)
    v = rec["vs_v3"]
    r = rec.get("vs_ref")
    print(f"{time.strftime('%H:%M:%S')} {rid:<30} nat {rec['blocks']['natural']['pct']:6.2f}  vs v3 {v['natural']['pct']:+6.2f} "
          f"[{v['natural']['ci95'][0]:+.2f}, {v['natural']['ci95'][1]:+.2f}] slow {v['slow']['pct']:+.2f} fast {v['fast']['pct']:+.2f} "
          f"B1 {v['toB1']:+.2f} B2 {v['toB2']:+.2f}  PA1 {rec['pa1']}  PA2 {rec['pa2']}"
          + (f"  | vs {ref_name} {r['natural']['pct']:+.2f} slow {r['slow']['pct']:+.2f} fast {r['fast']['pct']:+.2f} "
             f"B1 {r['toB1']:+.2f} B2 {r['toB2']:+.2f} step {'PASS' if rec['step_rule']['PASS'] else 'fail'}" if r else ""),
          flush=True)
    return rec


# ------------------------------------------------------------------ Part 0: the base window

def by_direction(ens: dict) -> dict:
    """Natural accuracy by the engine's detected direction (away A_fwd, towards A_rev)."""
    d = IL.data()
    out = {}
    for dirn, lab in (("A_fwd", "away"), ("A_rev", "towards")):
        ok, who = [], []
        for s in IL.SESS:
            k = S.positions(s)["natural"]
            m = d["rep"][s]["path_used"][k].astype(str) == dirn
            ok.append(S._ok(ens[s], s, "natural")[m])
            who.append(d["a"]["anon"][d["rep"][s]["te"][k]][m])
        out[lab] = EV._boot(np.concatenate(ok), np.concatenate(who))
    return out


def part0() -> dict:
    d = IL.data()
    V = S.v3()
    v3e = {s: V["rep"][s]["ensemble"] for s in IL.SESS}
    ens, wifi, dec = {}, {}, {}
    for w in WINDOWS:
        e = ensemble_of(w)
        ens[w] = {s: e[s]["ensemble"] for s in IL.SESS}
        wifi[w] = {s: arm(w, s)["wifi_speed"] for s in IL.SESS}
        dec[w] = {s: arm(w, s)["dec_s"] for s in IL.SESS}
    info = {"by_direction": {w: by_direction(ens[w]) for w in WINDOWS}}
    rows = {}
    for w in WINDOWS:
        rows[w] = record(f"P0.{w}", "0", f"fixed {w[1:]} s", ens[w], wifi[w], dec[w],
                         extra={"by_direction": info["by_direction"][w]})
    nat = {w: rows[w]["blocks"]["natural"]["pct"] for w in WINDOWS}
    info["plateau"] = {"T3.75_minus_T4.0": round(nat["T3.75"] - nat["T4.0"], 2), "T4.25_minus_T4.0": round(nat["T4.25"] - nat["T4.0"], 2)}
    info["plateau"]["PASS"] = abs(info["plateau"]["T3.75_minus_T4.0"]) <= 2.5 + 1e-9 and abs(info["plateau"]["T4.25_minus_T4.0"]) <= 2.5 + 1e-9
    # the direction rule, cross-fitted: each fold takes, per direction, the window best on the OTHER fold's walks
    choice, dens, ddec = {}, {}, {}
    for s in IL.SESS:
        o = "B1" if s == "B2" else "B2"
        te_o = d["rep"][o]["te"]
        k_o = np.flatnonzero(d["a"]["kind"][te_o] == "idcap")
        choice[s] = {}
        for dirn in ("A_fwd", "A_rev"):
            m = k_o[d["rep"][o]["path_used"][k_o].astype(str) == dirn]
            acc = {w: float((IL.CL[ens[w][o][m].argmax(1)] == d["a"]["anon"][te_o[m]]).mean()) for w in WINDOWS}
            choice[s][dirn] = sorted(WINDOWS, key=lambda w: (-acc[w], float(w[1:])))[0]
        pu = d["rep"][s]["path_used"].astype(str)
        dens[s] = np.array([ens[choice[s]["A_rev" if p.endswith("_rev") else "A_fwd"]][s][k] for k, p in enumerate(pu)])
        dd = np.zeros(len(d["a"]["kind"]))
        te = d["rep"][s]["te"]
        for k, (i, p) in enumerate(zip(te, pu)):
            dd[i] = dec[choice[s]["A_rev" if p.endswith("_rev") else "A_fwd"]][s][i]
        ddec[s] = dd
    info["direction_rule_choice"] = choice
    info_in_view = {}
    for dirn, lab in (("A_fwd", "away"), ("A_rev", "towards")):
        info_in_view[lab] = max(WINDOWS, key=lambda w: info["by_direction"][w][lab]["pct"])
    info["direction_choice_in_view_information"] = info_in_view
    dwifi = {s: wifi["T4.0"][s] for s in IL.SESS}
    rows["direction"] = record("P0.direction_rule", "0", "per direction, the window best on the other fold (cross-fitted)",
                               dens, dwifi, ddec, extra={"choice": choice})
    # the multi-window ensemble, decided at 4.5 s
    mens = {s: C.normalise_logp(sum(ens[w][s] for w in MULTI)) for s in IL.SESS}
    rows["multi"] = record("P0.multi_window", "0", "the equal sum of 3.0, 3.5, 4.0 and 4.5 s, decided at 4.5 s", mens,
                           wifi["T4.5"], dec["T4.5"])
    # the base: the best candidate passing the step rule against v3 and the plateau check; else 4.0 s
    cands = {"T4.0": rows["T4.0"], "direction_rule": rows["direction"], "multi_window": rows["multi"]}
    passing = {}
    for c, r in cands.items():
        sr = step_rule(r["vs_v3"], r["pa1"], pa1(v3e))
        passing[c] = {"step_rule_vs_v3": sr, "plateau": info["plateau"]["PASS"], "natural": r["blocks"]["natural"]["pct"]}
    ok = [c for c in cands if passing[c]["step_rule_vs_v3"]["PASS"] and passing[c]["plateau"]]
    base = max(ok, key=lambda c: passing[c]["natural"]) if ok else "T4.0"
    info["candidates"] = passing
    info["BASE"] = base
    IL.dump(os.path.join(OUT, "part0.json"), info)
    print(json.dumps({k: v for k, v in info.items() if k != "by_direction"}, indent=1, default=str), flush=True)
    for w in WINDOWS:
        print(w, {k: v["pct"] for k, v in info["by_direction"][w].items()}, flush=True)
    return info


# ------------------------------------------------------------------ Part 1: cheap levers; Part 3: the stack

NETS = os.environ.get("IWG_PARTC_OUT", os.path.join(OUT, "networks"))


def rx2_mod_idx(gnames: list) -> list:
    """The four RX2 amplitude-level columns (family `mod`), as indices into the 630."""
    return [j for j, n in enumerate(gnames) if n.startswith("mod|") and "|RX2|" in n]


def icc_order(G: np.ndarray, rows: np.ndarray) -> np.ndarray:
    """The 630 columns ordered by stability (PLAN 1.2): variance over people of their mean session means, over the mean
    over people of the variance of their session means; each column standardised over the training rows first."""
    a = IL.data()["a"]
    X = G[rows].astype(float)
    mu, sd = np.nanmean(X, 0), np.nanstd(X, 0)
    Z = (X - mu) / np.where(sd > 1e-12, sd, 1.0)
    who, ses = a["anon"][rows], a["session"][rows]
    ratio = np.zeros(G.shape[1])
    people = np.unique(who)
    for j in range(G.shape[1]):
        pm, pv = [], []
        for p in people:
            means = [np.nanmean(Z[(who == p) & (ses == s), j]) for s in np.unique(ses[who == p])]
            means = np.array([m for m in means if np.isfinite(m)])
            if len(means) >= 2:
                pm.append(means.mean())
                pv.append(means.var())
        ratio[j] = (np.var(pm) / max(np.mean(pv), 1e-12)) if len(pm) >= 2 else 0.0
    return np.argsort(-ratio), ratio


def rx1_columns(name: str, fold: str) -> np.ndarray:
    """PLAN 1.4: RX1's shadowing (depth, width, asymmetry over distance) and sway (power at the step rate), per row."""
    from scipy import signal as sg
    d = data()
    g = arm(name, fold)
    series = S.bank(ALPHA_A if fold.startswith("A") else S.alpha_of(fold))["rx1"][name]
    ci = d["names"].index("cad|all|-|-|cadence_hz")
    out = np.full((len(series), 4), np.nan)
    grid = np.arange(0.0, 5.0 + 1e-9, 0.1)
    for i, a1 in enumerate(series):
        a1 = np.asarray(a1, float)
        if len(a1) < 64 or not np.all(np.isfinite(a1)):
            continue
        att = 20.0 * np.log10(np.maximum(a1, 1e-9) / max(np.percentile(a1, 95), 1e-9))
        v = g["wifi_speed"][i]
        if np.isfinite(v) and v > 0:
            dist = v * np.arange(len(att)) / EN.FS
            ok = grid <= dist[-1]
            prof = np.interp(grid[ok], dist, att)
            if len(prof) >= 5:
                k = int(np.argmin(prof))
                depth = float(prof[k])
                below = np.flatnonzero(prof <= depth / 2.0)
                lo, hi = grid[ok][below[0]], grid[ok][below[-1]]
                width = float(hi - lo)
                out[i, 0], out[i, 1] = depth, width
                out[i, 2] = float((grid[ok][k] - (lo + hi) / 2.0) / width) if width > 0 else 0.0
        f = float(g["features"][i, ci])
        if np.isfinite(f) and f > 0:
            fr, P = sg.welch(sg.detrend(a1), fs=EN.FS, nperseg=min(len(a1), 512), nfft=4096)
            band = (fr >= 0.8) & (fr <= 3.5)
            at = np.abs(fr - f) <= 0.1
            out[i, 3] = float(P[at].sum() / max(P[band].sum(), 1e-20))
    return out


def cnn_source(name: str, fold: str, source: str) -> dict:
    """The CNN components: "v3w" (v3's weights on the arm's maps) or a list of network variants (seeds averaged)."""
    from pipeline.identify import iwg_cnn as CC
    if source == "v3w":
        return cnn_comps(name, fold)
    zs = [np.load(os.path.join(NETS, name, f"to{fold}", v, "components.npz")) for v in source.split("+")]
    mean = lambda k: np.mean([z[k] for z in zs], axis=0)                     # noqa: E731
    per = [C.normalise_logp(mean(f"alone_cnn_link{l}")) for l in range(3)]
    return {"cnn": C.normalise_logp(mean("cnn")), "cnn_prior": C.normalise_logp(mean("cnn_prior")),
            "cnn_perlink_prior": C.normalise_logp(sum(per))}


def stack_ensemble(name: str, st: dict, folds=IL.SESS) -> tuple:
    """A stack state -> (ensembles per fold, Wi-Fi speeds per fold). st keys: colidx (None or indices into the 630),
    rx1 (bool), cnn (a cnn_source), temps (bool), bias (bool)."""
    from pipeline.identify import ils_screen as LS
    def cfg(s):
        c = {}
        if st.get("colidx") is not None:
            c["colidx"] = st["colidx"][s] if isinstance(st["colidx"], dict) else st["colidx"]
        if st.get("rx1"):
            c["extra"] = rx1_columns(name, s)
        return c
    feats, wifi = feat_comps(name, folds, cfg)
    comps = {s: {**feats[s], **cnn_source(name, s, st.get("cnn", "v3w"))} for s in folds}
    if st.get("temps"):
        T = LS.temperatures(comps)
        comps = {s: {k: C.normalise_logp(comps[s][k] / T[s][k]) for k in IL.COMPS} for s in folds}
    if st.get("bias"):
        ens = {s: LS.bias(comps[s], s, "layout") for s in folds}
    else:
        ens = {s: IL.ensemble(comps[s]) for s in folds}
    return ens, wifi


BASE = "T4.0"


def part1() -> dict:
    """Each cheap lever on the base (feature components retrained; v3's CNN weights on the base maps), against the base."""
    from pipeline.identify import ils_feat as FT
    d = data()
    base_ens, base_w = stack_ensemble(BASE, {})
    dec = {s: arm(BASE, s)["dec_s"] for s in IL.SESS}
    record("lever1.base", "1", f"the base ({BASE[1:]} s; v3's CNN weights)", base_ens, base_w, dec)
    info = {"base": BASE}
    gn = d["gnames"]
    # 1.2 stable features: the ICC order per fold, from the fold's training rows only
    order = {}
    for s in IL.SESS:
        G = arm(BASE, s)["features"].astype(float)[:, EN.v2_columns(d["names"])]
        order[s], ratio = icc_order(G, d["tr"][s])
        info[f"icc_top10_to{s}"] = [(gn[j], round(float(ratio[j]), 3)) for j in order[s][:10]]
        info[f"icc_rank_of_rx2_mod_to{s}"] = {gn[j]: int(np.flatnonzero(order[s] == j)[0]) for j in rx2_mod_idx(gn)}
    mod = rx2_mod_idx(gn)
    info["rx2_amplitude_level_columns"] = [gn[j] for j in mod]
    # information: the forest's most important columns and the LDA's pulls towards PA1 (base, to B2)
    G = arm(BASE, "B2")["features"].astype(float)[:, EN.v2_columns(d["names"])]
    m = FT.train(d, "B2", {"G": G, "pace": arm(BASE, "B2")["wifi_speed"], "pool": "layout"})
    names_p = gn + ["wifi_speed"]
    keep = lambda st: np.flatnonzero(st.ok)[st.keep] if hasattr(st, "keep") else None   # noqa: E731
    imp = m["rf_prior"]["clf"].feature_importances_
    cols = keep(m["rf_prior"]["state"])
    info["rf_prior_top15_importance_toB2"] = [(gn[cols[j]] if cols[j] < len(gn) else "wifi_speed", round(float(imp[j]), 4))
                                              for j in np.argsort(-imp)[:15]]
    lda = m["lda_pace_prior"]["clf"]
    cl = list(m["lda_pace_prior"]["classes"])
    cols = keep(m["lda_pace_prior"]["state"])
    coef = lda.coef_[cl.index("P2")]
    info["lda_top15_pull_towards_PA1_toB2"] = [(names_p[cols[j]] if cols[j] < len(names_p) else "?", round(float(coef[j]), 3))
                                                  for j in np.argsort(-coef)[:15]]
    rows = {}
    levers = [("lever1.1_temperature", "one temperature per component (cross-fitted)", {"temps": True}),
              *[(f"lever1.2_stable_k{k}", f"the {k} most stable columns (ICC on the training rows)",
                 {"colidx": {s: np.sort(order[s][:k]) for s in IL.SESS}}) for k in (150, 300, 450)],
              ("lever1.3_rx2_placement_robust", "RX2's four amplitude-level (mod) columns dropped",
               {"colidx": np.array([j for j in range(len(gn)) if j not in mod])}),
              ("lever1.4_rx1_shadow_sway", "RX1's shadowing (depth, width, asymmetry) and sway columns", {"rx1": True}),
              ("lever1.5_bias_correction", "session bias correction, same-layout pool (assumes everyone walks equally often)",
               {"bias": True})]
    for rid, what, st in levers:
        ens, w = stack_ensemble(BASE, st)
        rows[rid] = record(rid, "1", what, ens, w, dec, ref=base_ens, ref_name="the base")
    IL.dump(os.path.join(OUT, "part1_info.json"), info)
    print(json.dumps({k: v for k, v in info.items() if "top" in k or "rx2" in k}, indent=1, default=str), flush=True)
    return rows


def loso(rid: str, what: str, st: dict) -> dict:
    """Leave one session out on the tracking walks (route known; all five folds), against engine v3's replays."""
    d = data()
    a = d["a"]
    ens, _w = stack_ensemble(BASE if "arm" not in st else st["arm"], st, folds=ALL)
    out = {"id": rid, "row": what, "label": IL.LABEL, "sessions": {}}
    for room in ("A", "B"):
        ok, okv, who = [], [], []
        for s in ALL:
            if s[0] != room:
                continue
            v3 = np.load(os.path.join(EN.ENG, "replays", f"loso_{s}_v3_{s}_T3.0.npz"))
            te = d["rep"][s]["te"]
            assert np.array_equal(v3["te"], te)
            k = np.flatnonzero(a["kind"][te] == "track")
            o1 = (IL.CL[ens[s][k].argmax(1)] == a["anon"][te[k]]).astype(float)
            o0 = (IL.CL[v3["ensemble"][k].argmax(1)] == a["anon"][te[k]]).astype(float)
            out["sessions"][s] = {"acc": round(100 * float(o1.mean()), 2), "v3": round(100 * float(o0.mean()), 2)}
            ok.append(o1)
            okv.append(o0)
            who.append(a["anon"][te[k]])
        ok, okv, who = np.concatenate(ok), np.concatenate(okv), np.concatenate(who)
        out[f"room_{room}"] = EV._boot(ok, who)
        out[f"room_{room}_v3"] = EV._boot(okv, who)
        out[f"room_{room}_paired"] = EV.paired(ok, okv, who)
        out[f"room_{room}_within_4.45_of_v3"] = bool(out[f"room_{room}"]["pct"] >= out[f"room_{room}_v3"]["pct"] - 4.45 - 1e-9)
    IL.dump(os.path.join(ROWS, f"{rid}.json"), out)
    print(f"{time.strftime('%H:%M:%S')} {rid}: Room A {out['room_A']['pct']} (v3 {out['room_A_v3']['pct']}; "
          f"{out['room_A_paired']['pct']:+.2f} {out['room_A_paired']['ci95']}), Room B {out['room_B']['pct']} "
          f"(v3 {out['room_B_v3']['pct']}; {out['room_B_paired']['pct']:+.2f} {out['room_B_paired']['ci95']})", flush=True)
    return out


# ------------------------------------------------------------------ Part 3: the stack, in the PLAN's fixed order

def have(variants: str, folds=IL.SESS) -> bool:
    return all(os.path.exists(os.path.join(NETS, BASE, f"to{s}", v, "components.npz")) for s in folds for v in variants.split("+"))


def stack() -> dict:
    """Part 3: each step against the stack so far, kept only if the step rule holds. Network steps compare at seed 0
    against the same-seed baseline; a kept network variant continues with three seeds."""
    d = data()
    dec = {s: arm(BASE, s)["dec_s"] for s in IL.SESS}
    path = []

    def run(rid, what, st):
        e, w = stack_ensemble(BASE, st)
        return e, w

    cur = {}
    cur_ens, cur_w = run("stack.0_base", "the base", cur)
    record("stack.0_base", "3", "1. the base (4.0 s; v3's CNN weights)", cur_ens, cur_w, dec)
    path.append({"step": "1. base", "kept": True})

    def try_step(rid, what, st, ref_ens=None, ref_name="the stack so far"):
        nonlocal cur, cur_ens, cur_w
        e, w = run(rid, what, st)
        r = record(rid, "3", what, e, w, dec, ref=ref_ens if ref_ens is not None else cur_ens, ref_name=ref_name)
        kept = r["step_rule"]["PASS"]
        path.append({"step": what, "vs_ref_natural": r["vs_ref"]["natural"]["pct"], "kept": kept,
                     "rule": r["step_rule"]})
        return kept, e, w, r

    # 2. the retrained CNNs, three seeds
    if not have("base+base_s1+base_s2"):
        raise SystemExit("step 2 needs the retrained networks (base, base_s1, base_s2) on both folds")
    st = {**cur, "cnn": "base+base_s1+base_s2"}
    kept, e, w, _r = try_step("stack.2_retrained_cnns", "2. the CNNs retrained on the base maps (3 seeds)", st)
    if kept:
        cur, cur_ens, cur_w = st, e, w
    # 3. temperatures
    st = {**cur, "temps": True}
    kept, e, w, _r = try_step("stack.3_temperature", "3. one temperature per component (cross-fitted)", st)
    if kept:
        cur, cur_ens, cur_w = st, e, w
    # 4. the better of the stable features (its best k) and the placement-robust RX2, then the other
    gn = d["gnames"]
    order = {}
    for s in IL.SESS:
        G = arm(BASE, s)["features"].astype(float)[:, EN.v2_columns(d["names"])]
        order[s], _r = icc_order(G, d["tr"][s])
    mod = set(rx2_mod_idx(gn))
    cands = {}
    for k in (150, 300, 450):
        st = {**cur, "colidx": {s: np.sort(order[s][:k]) for s in IL.SESS}}
        e, w = run(f"k{k}", "", st)
        cands[f"stable_k{k}"] = (st, e, w, float(np.mean(np.concatenate([S._ok(e[s], s, "natural") for s in IL.SESS]))))
    best_k = max((c for c in cands if c.startswith("stable")), key=lambda c: cands[c][3])
    st_rx2 = {**cur, "colidx": np.array([j for j in range(len(gn)) if j not in mod])}
    e2, w2 = run("rx2", "", st_rx2)
    acc_rx2 = float(np.mean(np.concatenate([S._ok(e2[s], s, "natural") for s in IL.SESS])))
    first, second = (("stable", "rx2") if cands[best_k][3] >= acc_rx2 else ("rx2", "stable"))
    for which in (first, second):
        if which == "stable":
            sel = {s: np.sort(order[s][:int(best_k.split("k")[1])]) for s in IL.SESS}
            if isinstance(cur.get("colidx"), np.ndarray):          # RX2 already dropped: intersect
                sel = {s: np.array([j for j in sel[s] if j not in mod]) for s in IL.SESS}
            st = {**cur, "colidx": sel}
            what = f"4. the {best_k.split('k')[1]} most stable columns"
        else:
            if isinstance(cur.get("colidx"), dict):                 # stable already kept: drop RX2's from it
                st = {**cur, "colidx": {s: np.array([j for j in cur["colidx"][s] if j not in mod]) for s in IL.SESS}}
            else:
                st = {**cur, "colidx": np.array([j for j in range(len(gn)) if j not in mod])}
            what = "4. RX2's amplitude-level columns dropped"
        kept, e, w, _r = try_step(f"stack.4_{which}", what, st)
        if kept:
            cur, cur_ens, cur_w = st, e, w
    # 5. RX1's shadowing and sway
    st = {**cur, "rx1": True}
    kept, e, w, _r = try_step("stack.5_rx1", "5. RX1's shadowing and sway", st)
    if kept:
        cur, cur_ens, cur_w = st, e, w
    # 6. the better of the whole-window CNN and pace augmentation (seed 0 against the same-seed baseline), then the other
    if not have("whole") or not have("paceaug"):
        raise SystemExit("step 6 needs the whole-window and pace-augmentation networks (seed 0) on both folds")
    same0 = {**cur, "cnn": "base"}
    ref0, _w0 = run("same0", "", same0)
    e_wh, w_wh = run("whole", "", {**cur, "cnn": "whole"})
    e_pa, w_pa = run("paceaug", "", {**cur, "cnn": "paceaug"})
    acc = lambda e: float(np.mean(np.concatenate([S._ok(e[s], s, "natural") for s in IL.SESS])))   # noqa: E731
    order6 = ("whole", "paceaug") if acc(e_wh) >= acc(e_pa) else ("paceaug", "whole")
    kept6 = []
    r6 = {}
    for v in order6:
        cand = v if not kept6 else "wholepace"
        if not have(cand):
            path.append({"step": f"6. {cand} (seed 0)", "kept": None, "note": f"needs the {cand} networks (seed 0)"})
            break
        ref_v = "base" if not kept6 else kept6[-1]
        refe, _ = run("ref6", "", {**cur, "cnn": ref_v})
        kept, e, w, r = try_step(f"stack.6_{cand}_seed0", f"6. {cand} networks (seed 0, against the same seed)",
                                 {**cur, "cnn": cand}, ref_ens=refe, ref_name=f"the same stack with {ref_v} (seed 0)")
        r6[cand] = kept
        if kept:
            kept6.append(cand)
        else:
            break
    if kept6:
        v = kept6[-1]
        if not have(f"{v}+{v}_s1+{v}_s2"):
            path.append({"step": f"6. {v} with three seeds", "kept": None, "note": f"needs {v}_s1 and {v}_s2"})
            IL.dump(os.path.join(OUT, "stack_path.json"), {"path": path, "state": _state(cur), "pending": f"{v}_s1, {v}_s2"})
            raise SystemExit(f"step 6 kept {v}: train {v}_s1 and {v}_s2, then run the stack again")
        st = {**cur, "cnn": f"{v}+{v}_s1+{v}_s2"}
        e, w = run("v3s", "", st)
        cur, cur_ens, cur_w = st, e, w
        record("stack.6_three_seeds", "3", f"6. {v} networks with three seeds (kept at seed 0)", e, w, dec, ref=None)
    # 7. bias correction, last and flagged
    st = {**cur, "bias": True}
    kept, e, w, _r = try_step("stack.7_bias", "7. session bias correction (assumes everyone walks equally often)", st)
    if kept:
        cur, cur_ens, cur_w = st, e, w
    final = record("stack.final", "3", "the final stack", cur_ens, cur_w, dec, extra={"state": _state(cur)})
    IL.dump(os.path.join(OUT, "stack_path.json"), {"path": path, "state": _state(cur)})
    print(json.dumps({"path": [(p["step"], p.get("vs_ref_natural"), p["kept"]) for p in path], "state": _state(cur)},
                     indent=1, default=str), flush=True)
    return {"state": cur, "final": final}


def final_checks(st: dict, rid: str = "final") -> dict:
    """The final stack: three seeds, leave one session out, slow and fast, S0 and S_wifi on every block, per person,
    PA1, PA2, the decision time; and the final rule."""
    d = data()
    meta = json.load(open(os.path.join(os.path.join(EN.ENG, "bank_T3.0_v3"), "meta.json")))["passes"]
    press = np.array([m["press_speed_m_s"] for m in meta], float)
    ens, wifi = stack_ensemble(BASE, st)
    dec = {s: arm(BASE, s)["dec_s"] for s in IL.SESS}
    r = record(f"stack.{rid}", "3", f"the final stack ({rid})", ens, wifi, dec, extra={"state": _state(st)})
    s0 = {}
    for b in BLOCKS:
        ok = np.concatenate([S._ok(ens[s], s, b) for s in IL.SESS])
        sk = np.concatenate([S._ok(S.s_wifi(press, s), s, b) for s in IL.SESS])
        who = np.concatenate([d["a"]["anon"][d["rep"][s]["te"][S.positions(s)[b]]] for s in IL.SESS])
        s0[b] = {"S0": EV._boot(sk, who)["pct"], "engine_minus_S0": EV.paired(ok, sk, who)}
    lo = loso(f"loso.{rid}", f"the final stack ({rid}) on the tracking walks", st)
    v3 = {"slow": 25.83, "fast": 23.53}
    rule = {"natural_interval_excludes_zero": r["vs_v3"]["natural"]["ci95"][0] > 0,
            "slow_at_least_v3": r["blocks"]["slow"]["pct"] >= v3["slow"] - 1e-9,
            "fast_at_least_v3": r["blocks"]["fast"]["pct"] >= v3["fast"] - 1e-9,
            "loso_room_A_within_4.45": lo["room_A_within_4.45_of_v3"], "loso_room_B_within_4.45": lo["room_B_within_4.45_of_v3"],
            "three_seeds": ("+" in str(st.get("cnn", ""))) or st.get("cnn", "v3w") == "v3w"}
    rule["ADOPT"] = all(rule.values())
    out = {"label": IL.LABEL, "state": _state(st), "natural": r["blocks"]["natural"], "vs_v3": r["vs_v3"], "slow": r["blocks"]["slow"],
           "fast": r["blocks"]["fast"], "S0": s0, "S_wifi": r.get("s_wifi"), "per_person": r["per_person"], "pa1": r["pa1"],
           "pa2": r["pa2"], "decision_s_median_natural": r.get("decision_s_median_natural"), "loso": lo, "final_rule": rule}
    IL.dump(os.path.join(OUT, f"final_{rid}.json"), out)
    print(json.dumps({"final_rule": rule, "natural": r["blocks"]["natural"], "vs_v3_natural": r["vs_v3"]["natural"]},
                     indent=1, default=str), flush=True)
    return out


def _state(st: dict) -> dict:
    return {k: (("per fold, " + str({s: len(v) for s, v in st[k].items()}) + " columns") if isinstance(st[k], dict) else
                (f"{len(st[k])} columns" if isinstance(st[k], np.ndarray) else st[k])) for k in st}


# ------------------------------------------------------------------ Part 4: diagnostics (information only)

def systematic(ens: dict) -> dict:
    """4.1: per person and test day, the share of their wrong natural walks that get their most frequent wrong name."""
    d = IL.data()
    out, shares = {}, []
    for s in IL.SESS:
        k = S.positions(s)["natural"]
        who = d["a"]["anon"][d["rep"][s]["te"][k]]
        pred = IL.CL[np.asarray(ens[s])[k].argmax(1)]
        for p in IL.L.CLASSES:
            wrong = pred[(who == p) & (pred != who)]
            if len(wrong):
                vals, cnt = np.unique(wrong, return_counts=True)
                out[f"{IL.NAME[p]} on {s}"] = {"wrong": int(len(wrong)), "most_frequent_wrong_name": IL.NAME[vals[np.argmax(cnt)]],
                                               "share": round(float(cnt.max() / len(wrong)), 3)}
                shares.append((cnt.max(), len(wrong)))
    tot = sum(x for x, _ in shares) / max(sum(n for _, n in shares), 1)
    out["_pooled_share"] = round(float(tot), 3)
    out["_by_chance_if_spread_over_five_names"] = 0.2
    return out


def link_cols(gnames: list, link: str) -> np.ndarray:
    import re
    return np.array([j for j, n in enumerate(gnames) if (set(re.findall(r"RX[123]", n)) == {link}) or
                     not re.findall(r"RX[123]", n)])


def part4() -> dict:
    """4.1 on engine v3; 4.2 same day against across days, feature components only, link by link (AC2's recipe, v3's
    3 s features)."""
    from pipeline.identify import ils_feat as FT
    from pipeline.identify import ixt_extra as XE
    d = data()
    V = S.v3()
    res = {"label": IL.LABEL, "4.1_engine_v3": systematic({s: V["rep"][s]["ensemble"] for s in IL.SESS})}
    m = json.load(open(os.path.join(os.path.join(EN.ENG, "bank_T3.0_v3"), "meta.json")))["passes"]
    trm = XE.cycle_train_mask(m)
    G = V["Xv3"].astype(float)[:, EN.v2_columns(d["names"])]
    pace = V["wifi_v3"]
    res["4.2_same_vs_cross_by_link"] = {}
    for link in ("RX1", "RX2", "RX3", "all"):
        cols = np.arange(G.shape[1]) if link == "all" else link_cols(d["gnames"], link)
        cfg = {"G": G, "pace": pace, "pool": "layout", "colidx": cols}
        ok_s, ok_c, whos = [], [], []
        for day in IL.SESS:
            te = d["rep"][day]["te"]
            d["tr"][f"same_{day}"] = np.flatnonzero((d["a"]["session"] == day) & trm)
            fs = FT.rescore(FT.train(d, f"same_{day}", cfg), d, day, cfg)
            fc = FT.rescore(FT.train(d, day, cfg), d, day, cfg)
            es = IL.ensemble(fs, use=IL.FEATC)
            ec = IL.ensemble(fc, use=IL.FEATC)
            k = np.flatnonzero((d["a"]["kind"][te] == "idcap") & (d["a"]["block"][te] == "natural") & ~trm[te])
            who = d["a"]["anon"][te[k]]
            ok_s.append((IL.CL[es[k].argmax(1)] == who).astype(float))
            ok_c.append((IL.CL[ec[k].argmax(1)] == who).astype(float))
            whos.append(who)
        ok_s, ok_c, whos = np.concatenate(ok_s), np.concatenate(ok_c), np.concatenate(whos)
        res["4.2_same_vs_cross_by_link"][link] = {"columns": int(len(cols)), "test_walks": int(len(whos)),
                                                  "same_day": EV._boot(ok_s, whos), "cross_day": EV._boot(ok_c, whos),
                                                  "same_minus_cross": EV.paired(ok_s, ok_c, whos)}
        r = res["4.2_same_vs_cross_by_link"][link]
        print(f"{time.strftime('%H:%M:%S')} {link}: same {r['same_day']['pct']} cross {r['cross_day']['pct']} "
              f"same-cross {r['same_minus_cross']['pct']:+.2f} {r['same_minus_cross']['ci95']} (n {len(whos)})", flush=True)
    IL.dump(os.path.join(OUT, "part4.json"), res)
    print(json.dumps(res["4.1_engine_v3"], indent=1), flush=True)
    return res


def table() -> str:
    """Every row: natural, slow and fast against v3 and against its reference, folds, PA1, PA2, decision time, the
    engine minus S_wifi, and the step rule (kept or not)."""
    import glob
    lines = ["| part | row | natural [95 %] | vs v3: natural [95 %] / slow / fast | vs reference: natural / slow / fast | to B1 / to B2 (vs v3) | PA1 | PA2 | decision (s) | engine minus S_wifi, natural | step rule |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for pth in sorted(glob.glob(os.path.join(ROWS, "*.json"))):
        r = json.load(open(pth))
        if "blocks" not in r:
            continue
        v = r["vs_v3"]
        ref = r.get("vs_ref")
        refs = (f"{ref['natural']['pct']:+.2f} / {ref['slow']['pct']:+.2f} / {ref['fast']['pct']:+.2f}" if ref else "")
        sw = r.get("s_wifi", {}).get("natural", {}).get("engine_minus_S_wifi", {})
        step = ("kept" if r["step_rule"]["PASS"] else "not kept") if "step_rule" in r else ""
        lines.append(f"| {r['part']} | {r['row']} | {r['blocks']['natural']['pct']:.2f} [{r['blocks']['natural']['ci95'][0]:.2f}, "
                     f"{r['blocks']['natural']['ci95'][1]:.2f}] | {v['natural']['pct']:+.2f} [{v['natural']['ci95'][0]:+.2f}, "
                     f"{v['natural']['ci95'][1]:+.2f}] / {v['slow']['pct']:+.2f} / {v['fast']['pct']:+.2f} | {refs} | "
                     f"{v['toB1']:+.2f} / {v['toB2']:+.2f} | {r['pa1']} | {r['pa2'].replace(' of 30', '')} | "
                     f"{r.get('decision_s_median_natural', float('nan')):.2f} | "
                     f"{(str(round(sw['pct'], 2)) if sw else '')} | {step} |")
    txt = "\n".join(lines) + "\n"
    open(os.path.join(OUT, "table.md"), "w").write(txt)
    return txt


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("what", choices=("cnn", "part0", "part1", "base_loso", "part4", "stack", "table"))
    ap.add_argument("--arm")
    ap.add_argument("--folds", nargs="+", default=list(IL.SESS))
    ap.add_argument("--device", default="mps", choices=("cpu", "mps"))
    x = ap.parse_args(argv)
    if x.what == "cnn":
        run_cnn(x.arm, x.folds, x.device)
    elif x.what == "part0":
        part0()
    elif x.what == "part1":
        part1()
    elif x.what == "part4":
        part4()
    elif x.what == "stack":
        stack()
    elif x.what == "table":
        print(table())
    else:
        loso("loso.base_T4.0", "the base (4.0 s; v3's CNN weights) on the tracking walks", {})
    return 0


if __name__ == "__main__":
    sys.exit(main())
