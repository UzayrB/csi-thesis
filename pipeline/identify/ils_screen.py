"""ils_screen. The identification lever screen's driver (`reports/BRIEF_ID_LEVER_SCREEN_2026-10-01.md`; every rule in
`runs/identify/engine/PLAN.md`, the note of 2026-10-01 17:18). Each lever is a set of components per session (the
feature components from `ils_feat`, the CNN components from the replays or `ils_cnn`), a fusion rule and an
optional session bias correction, scored on the 180 natural walks paired against engine v2 (`ils_common.score`).

    PYTHONPATH=. python3 -m pipeline.identify.ils_screen tier0      # 0.1 (and fix L), 0.3, 0.4
    PYTHONPATH=. python3 -m pipeline.identify.ils_screen noise      # the noise floor (S)
    PYTHONPATH=. python3 -m pipeline.identify.ils_screen tier1
    PYTHONPATH=. python3 -m pipeline.identify.ils_screen tier2
    PYTHONPATH=. python3 -m pipeline.identify.ils_screen table
    PYTHONPATH=. python3 -m pipeline.identify.ils_screen combo <lever id> ...

Development evaluation, all data seen. A screen: the engine does not change.
"""

from __future__ import annotations

import glob
import json
import os
import sys
import time

import numpy as np

from pipeline.identify import idv2_core as C
from pipeline.identify import idx_loso as L
from pipeline.identify import ils_cnn as CN
from pipeline.identify import ils_common as IL
from pipeline.identify import ils_feat as FT

FEAT_LEVERS = {      # Tier 2 (and the noise floor's feature seeds), as `ils_feat` configurations
    "N.feat_seed1": {"seed": 1}, "N.feat_seed2": {"seed": 2},
    "T2.1.cols_rx2": {"cols": "rx2"}, "T2.1.cols_rx23": {"cols": "rx23"},
    "T2.2.lda_shrink0.7": {"lda": ("shrink", 0.7)}, "T2.2.lda_shrink0.9": {"lda": ("shrink", 0.9)},
    "T2.2.lda_to_logreg_C0.01": {"lda": ("logreg", 0.01)}, "T2.2.lda_removed": {"lda": "drop"},
    "T2.3.matched_x2": {"weight": 2}, "T2.3.matched_x4": {"weight": 4}, "T2.3.matched_only": {"rows": "matched"},
    "T2.4.no_rhy_tplacf": {"families": "no_rhy_tpl"}, "T2.4.dop_spec_wav_mod": {"families": "dop_spec_wav_mod"},
    "T2.5a.std_id_layout": {"std": "id_layout"}, "T2.5b.std_perpath_training": {"std": "perpath"},
    "T2.5c.std_none_global": {"std": "global"}, "T2.5d.std_session_no_path": {"std": "nopath"},
}
WHAT = {
    "N.feat_seed1": "noise floor: feature components with random_state 1",
    "N.feat_seed2": "noise floor: feature components with random_state 2",
    "T2.1.cols_rx2": "feature columns: RX2 only (209 + 3 step-rate)",
    "T2.1.cols_rx23": "feature columns: RX2 + RX3 (418 + 3)",
    "T2.2.lda_shrink0.7": "LDA with fixed shrinkage 0.7", "T2.2.lda_shrink0.9": "LDA with fixed shrinkage 0.9",
    "T2.2.lda_to_logreg_C0.01": "logistic regression (L2, C 0.01) in the LDA's place",
    "T2.2.lda_removed": "the LDA component removed (retrained set)",
    "T2.3.matched_x2": "matched rows (other Room B day's identification walks) weighted x2",
    "T2.3.matched_x4": "matched rows weighted x4", "T2.3.matched_only": "feature components trained on matched rows only",
    "T2.4.no_rhy_tplacf": "families without rhy and tplacf", "T2.4.dop_spec_wav_mod": "families dop, spec, wav, mod only",
    "T2.5a.std_id_layout": "standardisation by (session, layout); test pool same layout",
    "T2.5b.std_perpath_training": "standardisation per path from training statistics only",
    "T2.5c.std_none_global": "no session standardisation: global training statistics",
    "T2.5d.std_session_no_path": "session standardisation without the path split",
}


# ------------------------------------------------------------------ building blocks

def comps(feat_cfg=None, cnn_pool=None, links=(0, 1, 2), seeds=None) -> tuple:
    """Per session, the components over every replay window; and seconds. None means the replay's own."""
    d = IL.data()
    t = time.time()
    feats = None
    if feat_cfg is not None:
        _ens, feats, _s = FT.lever(feat_cfg)
    out = {}
    for s in IL.SESS:
        c = {k: v for k, v in IL.replay_comps(d, s).items()}
        if feats is not None:
            for k in IL.FEATC:
                c.pop(k, None)
            c.update(feats[s])
        if cnn_pool is not None or tuple(links) != (0, 1, 2) or seeds is not None:
            c.update(CN.components(CN.load(cnn_pool or "engine", s), seeds=seeds, links=links))
        out[s] = c
    return out, time.time() - t


def fuse_sum(c: dict, use=None) -> np.ndarray:
    return IL.ensemble(c, use=tuple(k for k in IL.COMPS if k in c and (use is None or k in use)))


def bias(c: dict, s: str, pool: str, use=None) -> np.ndarray:
    """Tier 1.5: each class's summed log-probability minus its mean over the session's earlier windows (>= 10)."""
    d = IL.data()
    S = sum(np.asarray(c[k]) for k in IL.COMPS if k in c and (use is None or k in use))
    lay = d["a"]["layout"][d["rep"][s]["te"]]
    out = S.copy()
    for k in range(len(S)):
        p = np.arange(k) if pool == "engine" else np.flatnonzero(lay[:k] == lay[k])
        if len(p) >= 10:
            out[k] = S[k] - S[p].mean(0)
    return C.normalise_logp(out)


def record(lid, tier, what, ens, seconds, extra=None, mark=True):
    r = IL.score(ens, IL.data())
    return IL.save(lid, tier, what, r, seconds, extra, mark), r


# ------------------------------------------------------------------ Tier 0

def tier0() -> None:
    d = IL.data()
    t = time.time()
    # 0.1 the calibration pools of each natural walk
    rows = []
    for s in IL.SESS:
        r = d["rep"][s]
        te, pu = r["te"], r["path_used"].astype(str)
        lay, kind = d["a"]["layout"][te], d["a"]["kind"][te]
        for k in IL.walks(d)[s]:
            earlier = np.arange(k)
            same = earlier[pu[earlier] == pu[k]]
            std = (same if len(same) >= 3 else earlier) if k >= 10 else np.array([], int)
            rows.append({"session": s, "position": int(k), "who": IL.NAME[d["a"]["anon"][te[k]]], "path": pu[k],
                         "std_pool": {"n": int(len(std)), "home_layout": int((lay[std] == "home").sum()),
                                      "rows": [int(x) for x in te[std]]},
                         "adabn_pool": {"n": int(k), "home_layout": int((lay[earlier] == "home").sum()),
                                        "tracking": int((kind[earlier] == "track").sum())}})
    mixed_std = sum(x["std_pool"]["home_layout"] > 0 for x in rows)
    mixed_bn = sum(x["adabn_pool"]["home_layout"] > 0 for x in rows)
    yus = [x for x in rows if x["session"] == "B2" and x["position"] == 151]
    summ = {"label": IL.LABEL, "natural_walks": len(rows),
            "standardisation_pool": "earlier windows of the session with the same engine path (used once >= 10 earlier "
                                    "windows; all earlier windows if fewer than 3 share the path); line-A tracking "
                                    "passes (RX2 at home) carry the same path labels A_fwd/A_rev",
            "adabn_pool": "every earlier window of the session (all 4 networks x 3 seeds), not split by path or layout",
            "walks_whose_std_pool_holds_home_layout_windows": mixed_std,
            "walks_whose_adabn_pool_holds_home_layout_windows": mixed_bn,
            "std_pool_home_fraction_median": round(float(np.median([x["std_pool"]["home_layout"] / x["std_pool"]["n"]
                                                                      for x in rows if x["std_pool"]["n"]])), 3),
            "adabn_pool_home_fraction_median": round(float(np.median([x["adabn_pool"]["home_layout"] / x["adabn_pool"]["n"]
                                                                        for x in rows if x["adabn_pool"]["n"]])), 3),
            "worked_walk_B2_151": {k: v for k, v in yus[0].items() if k != "std_pool"} | {
                "std_pool": {kk: vv for kk, vv in yus[0]["std_pool"].items() if kk != "rows"}} if yus else None,
            "MIXES_LAYOUTS": bool(mixed_std or mixed_bn)}
    IL.dump(os.path.join(IL.OUT, "tier0", "pools.json"), {"summary": summ, "walks": rows})
    print(json.dumps(summ, indent=1), flush=True)
    # fix L (test side only): features and CNNs on same-layout pools, and each half alone (information)
    if summ["MIXES_LAYOUTS"]:
        c, sec = comps(feat_cfg={"pool": "layout"}, cnn_pool="layout")
        record("T0.1.fixL", "0.1", "fix L: calibrate only on earlier windows of the same layout (features and AdaBN)",
               {s: fuse_sum(c[s]) for s in IL.SESS}, sec)
        c, sec = comps(feat_cfg={"pool": "layout"})
        record("T0.1.fixL_features_only", "0.1", "fix L, the feature standardisation half only (information)",
               {s: fuse_sum(c[s]) for s in IL.SESS}, sec, mark=False)
        c, sec = comps(cnn_pool="layout")
        record("T0.1.fixL_adabn_only", "0.1", "fix L, the AdaBN half only (information)",
               {s: fuse_sum(c[s]) for s in IL.SESS}, sec, mark=False)
    # 0.3 each component alone (from the replays)
    diag = {}
    wk = IL.walks(d)
    for comp in IL.COMPS:
        ens = {s: IL.replay_comps(d, s)[comp] for s in IL.SESS}
        rec, r = record(f"T0.3.{comp}_alone", "0.3", f"component {comp} alone", ens, 0.0, mark=False)
        lp = np.vstack([ens[s][wk[s]] for s in IL.SESS])
        who = np.concatenate([d["a"]["anon"][d["rep"][s]["te"][wk[s]]] for s in IL.SESS])
        tru = np.array([L.CLASSES.index(p) for p in who])
        pred = lp.argmax(1)
        conf = [[int(np.sum((tru == i) & (pred == j))) for j in range(6)] for i in range(6)]
        diag[comp] = {"accuracy": r["natural"], "named_pa1": r["pa1"],
                      "mean_logp_spread": round(float((lp.max(1) - lp.min(1)).mean()), 3),
                      "mean_true_class_nll": round(float(-lp[np.arange(len(tru)), tru].mean()), 3),
                      "confusion_rows_true_cols_named": {IL.NAME[L.CLASSES[i]]: {IL.NAME[L.CLASSES[j]]: conf[i][j]
                                                                                for j in range(6)} for i in range(6)}}
    # 0.4 each receiver's per-link CNN alone (AdaBN on the engine's pool, mean over seeds)
    for l, rx in enumerate(("RX1", "RX2", "RX3")):
        ens = {s: CN.link_alone(CN.load("engine", s), l) for s in IL.SESS}
        rec, r = record(f"T0.4.perlink_{rx}_alone", "0.4", f"the per-link CNN, {rx} alone", ens, 0.0, mark=False)
        lp = np.vstack([ens[s][wk[s]] for s in IL.SESS])
        diag[f"perlink_{rx}"] = {"accuracy": r["natural"], "named_pa1": r["pa1"],
                                 "mean_logp_spread": round(float((lp.max(1) - lp.min(1)).mean()), 3)}
    IL.dump(os.path.join(IL.OUT, "tier0", "components.json"), {"label": IL.LABEL, "components": diag,
                                                                "seconds": round(time.time() - t, 1)})


# ------------------------------------------------------------------ the noise floor

def noise() -> dict:
    d = IL.data()
    accs_cnn = []
    for sd in (0, 1, 2):
        c, sec = comps(seeds=[sd])
        _rec, r = record(f"N.cnn_seed{sd}", "noise", f"noise floor: all three CNN components from seed {sd} only",
                         {s: fuse_sum(c[s]) for s in IL.SESS}, sec, mark=False)
        accs_cnn.append(r["natural"]["pct"])
    accs_feat = [IL.score({s: d["rep"][s]["ensemble"] for s in IL.SESS}, d)["natural"]["pct"]]
    for lid in ("N.feat_seed1", "N.feat_seed2"):
        c, sec = comps(feat_cfg=FEAT_LEVERS[lid])
        _rec, r = record(lid, "noise", WHAT[lid], {s: fuse_sum(c[s]) for s in IL.SESS}, sec, mark=False)
        accs_feat.append(r["natural"]["pct"])
    S = max(max(accs_cnn) - min(accs_cnn), max(accs_feat) - min(accs_feat))
    out = {"label": IL.LABEL, "cnn_single_seed_natural": accs_cnn, "feature_random_state_0_1_2_natural": accs_feat,
           "cnn_range": round(max(accs_cnn) - min(accs_cnn), 2), "feature_range": round(max(accs_feat) - min(accs_feat), 2),
           "S": round(S, 2)}
    IL.dump(os.path.join(IL.OUT, "noise.json"), out)
    print(out, flush=True)
    return out


# ------------------------------------------------------------------ Tier 1

def _nll(lp, y):
    return float(-lp[np.arange(len(y)), y].mean())


def _idcap_rows(d, s):
    te = d["rep"][s]["te"]
    k = np.flatnonzero(d["a"]["kind"][te] == "idcap")
    return k, np.array([L.CLASSES.index(p) for p in d["a"]["anon"][te[k]]])


def temperatures(c: dict) -> dict:
    """Per scored session, one temperature per component, fitted on the OTHER session's identification walks."""
    from scipy.optimize import minimize_scalar
    d = IL.data()
    out = {}
    for s in IL.SESS:
        o = "B1" if s == "B2" else "B2"
        k, y = _idcap_rows(d, o)
        T = {}
        for comp in IL.COMPS:
            lp = np.asarray(c[o][comp])[k]
            f = lambda lt: _nll(C.normalise_logp(lp / np.exp(lt)), y)      # noqa: E731
            T[comp] = float(np.exp(minimize_scalar(f, bounds=(-4, 4), method="bounded").x))
        out[s] = T
    return out


def joint_weights(c: dict) -> dict:
    from scipy.optimize import minimize
    d = IL.data()
    out = {}
    for s in IL.SESS:
        o = "B1" if s == "B2" else "B2"
        k, y = _idcap_rows(d, o)
        Ls = np.stack([np.asarray(c[o][comp])[k] for comp in IL.COMPS])
        f = lambda w: _nll(C.normalise_logp(np.tensordot(w, Ls, 1)), y)   # noqa: E731
        res = minimize(f, np.ones(len(IL.COMPS)), method="L-BFGS-B", bounds=[(0, 5)] * len(IL.COMPS))
        out[s] = dict(zip(IL.COMPS, [float(x) for x in res.x]))
    return out


def tier1() -> None:
    d = IL.data()
    c = {s: IL.replay_comps(d, s) for s in IL.SESS}
    for comp in IL.COMPS:
        t = time.time()
        record(f"T1.1.without_{comp}", "1.1", f"leave out {comp}",
               {s: fuse_sum(c[s], use=[k for k in IL.COMPS if k != comp]) for s in IL.SESS}, time.time() - t)
    t = time.time()
    T = temperatures(c)
    record("T1.2.temperature", "1.2", "one temperature per component (cross-fitted), then the sum",
           {s: C.normalise_logp(sum(C.normalise_logp(c[s][k] / T[s][k]) for k in IL.COMPS)) for s in IL.SESS},
           time.time() - t, extra={"temperatures": T})
    t = time.time()
    Wt = joint_weights(c)
    record("T1.2b.joint_weights", "1.2", "beyond the brief: eight weights fitted jointly (cross-fitted)",
           {s: C.normalise_logp(sum(Wt[s][k] * c[s][k] for k in IL.COMPS)) for s in IL.SESS}, time.time() - t,
           extra={"weights": Wt})
    t = time.time()
    record("T1.3.mean_of_probabilities", "1.3", "the mean of probabilities",
           {s: C.normalise_logp(np.log(np.mean([np.exp(c[s][k]) for k in IL.COMPS], axis=0))) for s in IL.SESS},
           time.time() - t)
    t = time.time()
    record("T1.3.two_families", "1.3", "features and CNNs each summed and normalised, then added",
           {s: C.normalise_logp(fuse_sum(c[s], IL.FEATC) + fuse_sum(c[s], IL.CNNC)) for s in IL.SESS}, time.time() - t)
    t = time.time()
    rank = lambda x: np.argsort(np.argsort(x, axis=1), axis=1).astype(float)          # noqa: E731
    ens = {}
    for s in IL.SESS:
        R = sum(rank(np.asarray(c[s][k])) for k in IL.COMPS)
        ens[s] = np.log(R + 1e-6 * np.exp(d["rep"][s]["ensemble"]) + 1e-12)        # ties: the engine's ensemble
    record("T1.3.rank_sum", "1.3", "the sum of ranks (ties broken by the engine's ensemble)", ens, time.time() - t)
    t = time.time()
    z = lambda x: (x - x.mean(1, keepdims=True)) / np.maximum(x.std(1, keepdims=True), 1e-12)   # noqa: E731
    record("T1.3.zscore_sum", "1.3", "the sum of per-walk z-scored log-probabilities",
           {s: C.normalise_logp(sum(z(np.asarray(c[s][k])) for k in IL.COMPS)) for s in IL.SESS}, time.time() - t)
    for name, links in (("RX2", (1,)), ("RX2_RX3", (1, 2))):
        cc, sec = comps(links=links)
        record(f"T1.4.perlink_{name}", "1.4", f"the per-link component from {name.replace('_', ' + ')} only",
               {s: fuse_sum(cc[s]) for s in IL.SESS}, sec)
    for pool in ("engine", "layout"):
        t = time.time()
        record(f"T1.5.bias_{pool}_pool", "1.5",
               f"session bias correction over earlier windows ({'every one' if pool == 'engine' else 'same layout'}); "
               "assumes everyone walks equally often", {s: bias(c[s], s, pool) for s in IL.SESS}, time.time() - t)


# ------------------------------------------------------------------ Tier 2

def tier2() -> None:
    for lid, cfg in FEAT_LEVERS.items():
        if lid.startswith("N."):
            continue
        cc, sec = comps(feat_cfg=cfg)
        record(lid, lid.split(".")[0][1:] + "." + lid.split(".")[1], WHAT[lid],
               {s: fuse_sum(cc[s]) for s in IL.SESS}, sec)


# ------------------------------------------------------------------ the table

def table() -> dict:
    S = json.load(open(os.path.join(IL.OUT, "noise.json")))["S"]
    recs = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(IL.LEVERS, "*.json")))]
    rows = []
    for r in recs:
        v = IL.verdict(r, S) if r["marked"] else "diagnostic"
        rows.append({"id": r["id"], "tier": r["tier"], "lever": r["lever"], "natural": r["natural"]["pct"],
                     "natural_ci95": r["natural"]["ci95"], "paired": r["paired"]["pct"], "paired_ci95": r["paired"]["ci95"],
                     "toB1": r["toB1"], "toB2": r["toB2"], "paired_toB1": r["paired_toB1"], "paired_toB2": r["paired_toB2"],
                     "pa1": r["pa1"], "pa2": r["pa2"], "verdict": v, "seconds": r["seconds"]})
    rows.sort(key=lambda x: (-x["paired"], x["id"]))
    lines = ["| tier | lever | natural | paired [95 %] | to B1 | to B2 | PA1 | PA2 | verdict | runtime |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for x in rows:
        lines.append(f"| {x['tier']} | {x['lever']} | {x['natural']:.2f} | {x['paired']:+.2f} [{x['paired_ci95'][0]:+.2f}, "
                     f"{x['paired_ci95'][1]:+.2f}] | {x['toB1']:.2f} ({x['paired_toB1']:+.2f}) | {x['toB2']:.2f} "
                     f"({x['paired_toB2']:+.2f}) | {x['pa1']} | {x['pa2']} | {x['verdict']} | {x['seconds']:.0f} s |")
    out = {"label": IL.LABEL, "S": S, "rows": rows}
    IL.dump(os.path.join(IL.OUT, "table.json"), out)
    open(os.path.join(IL.OUT, "table.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)
    return out


# ------------------------------------------------------------------ the additions (PLAN note 2026-10-01 17:33)

def extra() -> None:
    d = IL.data()
    c = {s: IL.replay_comps(d, s) for s in IL.SESS}
    t = time.time()
    record("T1.3.two_families_mean", "1.3", "the two families at equal weight: feature mean + CNN mean (addition 1)",
           {s: C.normalise_logp(sum(c[s][k] for k in IL.FEATC) / len(IL.FEATC) + sum(c[s][k] for k in IL.CNNC) / len(IL.CNNC))
            for s in IL.SESS}, time.time() - t)
    for pool, cnn in (("engine", None), ("layout", "layout")):
        t = time.time()
        cc, _sec = comps(feat_cfg={"lda": ("shrink", 0.7)} | ({"pool": "layout"} if pool == "layout" else {}), cnn_pool=cnn)
        T = temperatures(cc)
        cal = {s: {k: C.normalise_logp(cc[s][k] / T[s][k]) for k in IL.COMPS} for s in IL.SESS}
        record(f"X.combo_positive{'_fixL' if pool == 'layout' else ''}", "addition 3",
               "information, chosen with results in view: temperature + LDA shrinkage 0.7 + bias correction (same-layout "
               f"pools){' + fix L' if pool == 'layout' else ''}", {s: bias(cal[s], s, "layout") for s in IL.SESS},
               time.time() - t, extra={"temperatures": T}, mark=False)


def main(argv) -> int:
    {"tier0": tier0, "noise": noise, "tier1": tier1, "tier2": tier2, "extra": extra, "table": table}[argv[0]]()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
