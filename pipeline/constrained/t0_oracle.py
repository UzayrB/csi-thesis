# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: STEP 0 of the pre-press region work: THE ORACLE CEILING.

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.constrained.night_common import set_half_roots
set_half_roots(REPO_ROOT)
from pipeline.constrained._guard import assert_isolated
assert_isolated("t0_oracle", os.path.join(REPO_ROOT, "runs", "artefacts_half"))

import time

import numpy as np

from pipeline.constrained.common import pairings, status, tag_of
from pipeline.constrained.fh_common import (both_readings, check_contract, claim_fh,
                                            release, save)
from pipeline.constrained.g3_final import shipped_pool_emissions
from pipeline.constrained.n2_arms import run, summarise
from pipeline.constrained.night_common import guard_verdict, shipped_pieces
from pipeline.constrained.q1_diag import REGIONS, region_of
from pipeline.constrained.q4_arms import start_terms
from pipeline.constrained.r1_oldcensus import shipped_opts
from pipeline.constrained.rebuild_common import findings, headline

STAGE = "t0_oracle"
SELECTION_FOLDS = ("s01_to_s02", "s02_to_s01")
COMBINED_FOLDS = ("s0102_to_s03", "s0103_to_s02", "s0203_to_s01")
ENTRY_WINDOW_M = 1.0
SHIPPED_START_W = 0.5
ORACLE_WEIGHTS = (0.5, 1.0, 2.0, 4.0)
SIM_ACCURACIES = (0.4, 0.6, 0.8)
CEILING_BAR_POINTS = 5.0
FORBID = -1.0e6
SEED = 0


# {line: the region its FIRST state sits in}.
def line_regions(st) -> dict:
    xy = np.asarray(st.xy, float)
    return {nm: region_of(xy[st.slice_of[nm][0]]) for nm in st.names}


# {session|stem|pass_id: the TRUE start region} over the test sessions of one pairing.
def true_regions(te_s, st) -> dict:
    from pipeline.constrained.recordings import load_meta, recordings
    lr = line_regions(st)
    out = {}
    for sess, stem in recordings():
        if sess not in te_s:
            continue
        try:
            rec = load_meta(sess, stem)
        except Exception:
            continue
        for pid, nm, _a, _b in rec.pass_spans():
            if nm in lr:
                out[f"{sess}|{stem}|{int(pid)}"] = lr[nm]
    return out


# A predicted region per pass, turned into the per-line log offset start_terms emits.
def term_from_prediction(pred: dict, st, weight: float, hard: bool = False) -> dict:
    lr = line_regions(st)
    regions = list(REGIONS)
    idx = {r: i for i, r in enumerate(regions)}
    out = {}
    for key, r_hat in pred.items():
        if hard:
            out[key] = {nm: (0.0 if r == r_hat else FORBID) for nm, r in lr.items()}
            continue
        P = np.full(len(regions), 1e-9)
        P[idx[r_hat]] = 1.0
        lp = np.log(np.clip(P, 1e-9, 1.0))
        base = float(np.mean(lp))
        out[key] = {nm: weight * float(lp[idx[r]] - base) for nm, r in lr.items() if r in idx}
    return out


# A classifier of exactly this accuracy: right with probability a, else a uniform wrong region.
def simulated_prediction(truth: dict, accuracy: float, seed: int = SEED) -> dict:
    rng = np.random.default_rng(seed)
    regions = list(REGIONS)
    out = {}
    for key in sorted(truth):
        r = truth[key]
        if rng.random() < accuracy:
            out[key] = r
        else:
            others = [x for x in regions if x != r]
            out[key] = others[int(rng.integers(len(others)))]
    return out


# Line accuracy broken out by the TRUE start region, counts kept.
def by_region(rows, lr) -> dict:
    d = {}
    for r in rows:
        reg = lr.get(r["true_line"])
        if reg is None:
            continue
        e = d.setdefault(reg, {"n": 0, "hit": 0})
        e["n"] += 1
        e["hit"] += int(r["found_final"])
    return {k: {"n": v["n"], "hit": v["hit"], "pct": 100.0 * v["hit"] / max(v["n"], 1)}
            for k, v in sorted(d.items())}


# Function main.
def main() -> int:
    lock = claim_fh(STAGE)
    t0 = time.time()
    st, cfg, ne, transit, kind, alpha = shipped_pieces()
    import pipeline.constrained.decoder as D
    import pipeline.constrained.decoder2 as D2
    D.MAX_ADVANCE_M = None
    D2._LT_CACHE.clear()
    lr = line_regions(st)
    status(f"{STAGE} START: the oracle ceiling on the start region, ceiling OFF for the decision")
    status(f"  region map: " + ", ".join(f"{r}={sum(1 for v in lr.values() if v == r)}"
                                         for r in REGIONS))

    ARMS = {"A1_A2_0.5": {"real": SHIPPED_START_W}}
    for w in ORACLE_WEIGHTS:
        ARMS[f"oracle_w{w}"] = {"oracle": w}
    ARMS["oracle_hard"] = {"oracle_hard": True}
    for a in SIM_ACCURACIES:
        ARMS[f"sim_a{a}"] = {"sim": a}

    RES = {"stage": STAGE,
           "brief": "reports/PREREG_prepress_region_2026-09-21.md",
           "what_it_measures": ("what a PERFECT start-region reader would be worth, and how "
                                "accurate a real one must be before it buys anything. No training "
                                "and no decoder change: the A2 term takes the region straight"),
           "ceiling_on_decision": False, "entry_window_m": ENTRY_WINDOW_M,
           "shipped_start_weight": SHIPPED_START_W,
           "oracle_weights": list(ORACLE_WEIGHTS), "sim_accuracies": list(SIM_ACCURACIES),
           "ceiling_bar_points": CEILING_BAR_POINTS,
           "selection_folds": list(SELECTION_FOLDS), "combined_folds": list(COMBINED_FOLDS),
           "baseline_arm": "A1_A2_0.5",
           "region_line_counts": {r: sorted(nm for nm, v in lr.items() if v == r) for r in REGIONS},
           "per_arm": {}, "failures": []}

    cache = {}
    for tr_s, te_s in pairings():
        if tr_s == te_s:
            continue
        tag = tag_of(tr_s, te_s, False)
        src, _i = shipped_pool_emissions(tag, tr_s, te_s, False, st, kind, alpha)
        if src is None:
            continue
        truth = true_regions(te_s, st)
        cache[tag] = {"tr_s": tr_s, "te_s": te_s, "src": src, "truth": truth,
                      "real": start_terms(tr_s, te_s, st, SHIPPED_START_W)}
    status(f"  {len(cache)} pairings cached, "
           f"{sum(len(v['truth']) for v in cache.values())} passes with a true region")

    for name, A in ARMS.items():
        node = {}
        for tag, C in cache.items():
            try:
                o = shipped_opts(st, C["tr_s"])
                o["entry"] = "soft"
                o["entry_window_m"] = ENTRY_WINDOW_M
                if "real" in A:
                    o["start_term"] = C["real"]
                elif "oracle" in A:
                    o["start_term"] = term_from_prediction(C["truth"], st, float(A["oracle"]))
                elif "oracle_hard" in A:
                    o["start_term"] = term_from_prediction(C["truth"], st, 0.0, hard=True)
                elif "sim" in A:
                    pred = simulated_prediction(C["truth"], float(A["sim"]))
                    o["start_term"] = term_from_prediction(pred, st, SHIPPED_START_W)
                    node_acc = 100.0 * np.mean([pred[k] == C["truth"][k] for k in C["truth"]])
                rows = run(C["src"], st, cfg, ne, transit, o, subs=True)
                s = summarise(rows)
                if s is None:
                    continue
                s["by_region"] = by_region(rows, lr)
                if "sim" in A:
                    s["simulated_region_accuracy_pct"] = float(node_acc)
                node[tag] = s
            except Exception as exc:
                import traceback
                RES["failures"].append({"arm": name, "tag": tag, "error": repr(exc),
                                        "traceback": traceback.format_exc()[-900:]})
        RES["per_arm"][name] = node
        v = [x["final_line_pct"] for x in node.values() if x]
        if v:
            status(f"  {name:14s} line all9 {np.median(v):5.2f}  "
                   f"endsub {np.median([x['substitution_end_pct'] for x in node.values() if x]):5.1f}")

    # Function col.
    def col(name, field="final_line_pct", which="heldout"):
        node = RES["per_arm"].get(name) or {}
        # Function keep.
        def keep(t):
            if which == "heldout":
                return t not in SELECTION_FOLDS
            if which == "combined":
                return t in COMBINED_FOLDS
            return True
        return {t: v[field] for t, v in node.items()
                if v and keep(t) and v.get(field) is not None}

    base = col("A1_A2_0.5")
    RES["aggregate"] = {}
    for name in ARMS:
        node = RES["per_arm"][name]
        if not node:
            continue
        agg = {
            "line_pct_heldout7": float(np.median(list(col(name).values()))) if col(name) else None,
            "line_pct_all9": float(np.median(list(col(name, which="all").values()))),
            "line_pct_combined3": (float(np.median(list(col(name, which="combined").values())))
                                   if col(name, which="combined") else None),
            "guard": guard_verdict(
                float(np.median([x["substitution_end_pct"] for x in node.values()
                                 if x and x["substitution_end_pct"] is not None])),
                float(np.median([x["substitution_line_pct"] for x in node.values()
                                 if x and x["substitution_line_pct"] is not None]))),
            "vs_baseline_heldout": (both_readings(base, col(name))
                                    if name != "A1_A2_0.5" else None)}
        reg = {}
        for tag, v in node.items():
            if tag in SELECTION_FOLDS or not v:
                continue
            for r, d in (v.get("by_region") or {}).items():
                e = reg.setdefault(r, {"n": 0, "hit": 0})
                e["n"] += d["n"]
                e["hit"] += d["hit"]
        agg["by_region_heldout"] = {r: {"n": e["n"], "hit": e["hit"],
                                        "pct": 100.0 * e["hit"] / max(e["n"], 1)}
                                    for r, e in sorted(reg.items())}
        if "sim" in ARMS[name]:
            acc = [x["simulated_region_accuracy_pct"] for x in node.values()
                   if x and x.get("simulated_region_accuracy_pct") is not None]
            agg["simulated_region_accuracy_pct"] = float(np.mean(acc)) if acc else None
        RES["aggregate"][name] = agg

    base_reg = RES["aggregate"]["A1_A2_0.5"]["by_region_heldout"]
    oracles = [k for k in ARMS if k.startswith("oracle")]
    gains = {k: RES["aggregate"][k]["vs_baseline_heldout"] for k in oracles
             if k in RES["aggregate"] and RES["aggregate"][k]["vs_baseline_heldout"]}
    best = max(gains, key=lambda k: gains[k]["median_of_paired_deltas_points"]) if gains else None
    best_gain = gains[best]["median_of_paired_deltas_points"] if best else None
    RES["ceiling"] = {
        "baseline_arm": "A1_A2_0.5",
        "baseline_line_pct_heldout7": RES["aggregate"]["A1_A2_0.5"]["line_pct_heldout7"],
        "best_oracle_arm": best,
        "best_oracle_gain_points_heldout": best_gain,
        "basis": ("median of the per-pairing paired deltas over the seven held-out pairings, the "
                  "two selection folds excluded. The difference of medians is reported beside it "
                  "in vs_baseline_heldout and neither is quoted alone"),
        "bar_points": CEILING_BAR_POINTS,
        "CLEARS_THE_BAR": bool(best_gain is not None and best_gain >= CEILING_BAR_POINTS),
        "STEPS_1_TO_3_MAY_RUN": bool(best_gain is not None and best_gain >= CEILING_BAR_POINTS),
        "per_region_gain_points": ({r: round(RES["aggregate"][best]["by_region_heldout"][r]["pct"]
                                             - base_reg[r]["pct"], 2)
                                    for r in base_reg
                                    if r in RES["aggregate"][best]["by_region_heldout"]}
                                   if best else None),
        "why_per_region": ("a ceiling carried by SW alone, which is 20 percent of passes, is not a "
                           "ceiling worth chasing, so the gain is broken out by true start region"),
        "break_even_note": ("the sim_a arms say how accurate a real classifier must be before it "
                            "buys anything; read them, not the oracle, when deciding whether to "
                            "build one")}

    RES["minutes"] = round((time.time() - t0) / 60.0, 1)
    RES["contract"] = check_contract(RES, ["per_arm", "aggregate", "ceiling"])
    save(STAGE, RES)
    release(lock)

    C = RES["ceiling"]
    status(f"  BASELINE A1_A2_0.5 held-out7 line {C['baseline_line_pct_heldout7']}")
    for k in oracles + [f"sim_a{a}" for a in SIM_ACCURACIES]:
        a = RES["aggregate"].get(k)
        if not a or not a["vs_baseline_heldout"]:
            continue
        r = a["vs_baseline_heldout"]
        status(f"  {k:14s} held-out7 {a['line_pct_heldout7']:5.2f}  paired "
               f"{r['median_of_paired_deltas_points']:+6.2f}  diff-of-medians "
               f"{r['difference_of_medians_points']:+6.2f}  ci {r['paired_ci']}")
    status(f"  CEILING: best {C['best_oracle_arm']} buys {C['best_oracle_gain_points_heldout']} "
           f"points against a {CEILING_BAR_POINTS} point bar -> "
           f"{'STEPS 1 TO 3 MAY RUN' if C['STEPS_1_TO_3_MAY_RUN'] else 'STOP, THE CEILING IS THE FINDING'}")
    g = C["best_oracle_gain_points_heldout"]
    headline(f"T0 ORACLE CEILING: a perfect start-region reader buys "
             f"{g if g is None else round(g, 2)} points of line accuracy on the seven held-out "
             f"pairings against a {CEILING_BAR_POINTS} point bar, so steps 1 to 3 "
             f"{'PROCEED' if C['STEPS_1_TO_3_MAY_RUN'] else 'DO NOT RUN'}")
    findings("t0oracle", bool(RES["contract"]["SATISFIED"]), (
        f"THE ORACLE CEILING ON THE START REGION.\n\n"
        f"Baseline, the current ship A1_A2_0.5, over the seven held-out pairings: "
        f"{C['baseline_line_pct_heldout7']} percent line accuracy.\n"
        f"Best oracle arm: {C['best_oracle_arm']}, buying "
        f"{g if g is None else round(g, 2)} points as the median of the per-pairing paired "
        f"deltas. The difference of medians is reported beside it and neither is quoted alone.\n\n"
        f"Per region: {C['per_region_gain_points']}\n\n"
        f"The simulated-classifier arms say what a REAL reader would be worth:\n" +
        "\n".join(
            f"  accuracy {RES['aggregate'][k].get('simulated_region_accuracy_pct')} -> "
            f"{(RES['aggregate'][k]['vs_baseline_heldout'] or {}).get('median_of_paired_deltas_points')} points"
            for k in (f"sim_a{a}" for a in SIM_ACCURACIES) if k in RES["aggregate"]) +
        f"\n\nPre-registered bar {CEILING_BAR_POINTS} points. Steps 1 to 3 "
        f"{'may run' if C['STEPS_1_TO_3_MAY_RUN'] else 'do not run; the ceiling is the finding'}.\n"
        f"Brief: reports/PREREG_prepress_region_2026-09-21.md"))
    return 0 if RES["contract"]["SATISFIED"] else 1


if __name__ == "__main__":
    sys.exit(main())
