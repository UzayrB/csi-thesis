"""PART 2: A1 and A2, each singly then combined, against the shipped decoder.

THE CEILING IS OFF FOR THE DECISION. Extra 1 measured the 3 m/s ceiling costing 7.50 points of
line accuracy with a paired interval of [-11.48, -3.15] that excludes zero, and taking the
semi-bounded against bounded gap from 7.5 to 15.8 points, which loses the verdict. The operator's
own instruction keeps the ceiling on the DISPLAY either way, so it is off here and on there.

A1  entry restricted to the first 1.0 m of each chain, not pinned, emissions choosing within it
A2  a start-consistency term on the chain totals, fed by the A3 classifier, targeting the 89 passes
    where the start region was read correctly and the decoder still chose a line starting elsewhere

Every arm reports the generalised substitution, both readings with the paired interval, and the
clock checks. An arm ships only if its paired improvement interval is entirely above zero.
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.constrained.night_common import set_half_roots                      # noqa: E402
set_half_roots(REPO_ROOT)
from pipeline.constrained._guard import assert_isolated                           # noqa: E402
assert_isolated("q4_arms", os.path.join(REPO_ROOT, "runs", "artefacts_half"))

import json                                                                       # noqa: E402
import time                                                                       # noqa: E402

import numpy as np                                                                # noqa: E402

from pipeline.constrained.common import E_POST, pairings, status, tag_of           # noqa: E402
from pipeline.constrained.fh_common import both_readings, check_contract, claim_fh, release, save  # noqa
from pipeline.constrained.g3_final import shipped_pool_emissions                   # noqa: E402
from pipeline.constrained.night_common import guard_verdict, shipped_pieces        # noqa: E402
from pipeline.constrained.n2_arms import run, summarise                            # noqa: E402
from pipeline.constrained.paths import REVERSE_OF                                  # noqa: E402
from pipeline.constrained.q1_diag import REGIONS, region_of                        # noqa: E402
from pipeline.constrained.q3_startclf import collect                               # noqa: E402
from pipeline.constrained.r1_oldcensus import shipped_opts                         # noqa: E402
from pipeline.constrained.rebuild_common import findings, headline                 # noqa: E402

STAGE = "q4_arms"
SELECTION_FOLDS = ("s01_to_s02", "s02_to_s01")
WEIGHTS = (0.25, 0.5, 1.0)
ENTRY_WINDOW_M = 1.0


def start_terms(tr_s, te_s, st, weight):
    """A3 trained on tr_s, applied to te_s, turned into a per-pass per-line log term."""
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    from sklearn.preprocessing import StandardScaler
    Xtr, ytr, _k, _w = collect(tr_s, st)
    Xte, yte, kte, _w2 = collect(te_s, st)
    if not len(Xtr) or not len(Xte):
        return {}
    sc = StandardScaler().fit(Xtr)
    clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
    clf.fit(sc.transform(Xtr), ytr)
    P = clf.predict_proba(sc.transform(Xte))
    classes = list(clf.classes_)
    xy = np.asarray(st.xy)
    line_region = {nm: region_of(xy[st.slice_of[nm][0]]) for nm in st.names}
    out = {}
    for i, key in enumerate(kte):
        lp = np.log(np.clip(P[i], 1e-9, 1.0))
        base = float(np.mean(lp))            # centre it so no line is favoured overall
        out[key] = {nm: weight * float(lp[classes.index(r)] - base)
                    for nm, r in line_region.items() if r in classes}
    return out


def arm_summary(src, st, cfg, ne, transit, o):
    rows = []
    n = len(src)
    from pipeline.constrained.night_arms import night_track
    from pipeline.constrained.night_common import STRIDE
    for k, (_s, rec, ge, e) in enumerate(src):
        alt = src[(k + 1) % n][3] if n > 1 else None
        rows += night_track(e, rec, st, cfg, transit, ne, ge, STRIDE, o, alt)
    s = summarise(rows)
    if s is None:
        return None
    xy = np.asarray(st.xy)
    lr = {nm: region_of(xy[st.slice_of[nm][0]]) for nm in st.names}
    wrong = [r for r in rows if not r["found_final"]]
    s["n_wrong"] = len(wrong)
    s["reversed"] = sum(1 for r in wrong if r["final_line"] == REVERSE_OF.get(r["true_line"]))
    s["not_starting_there"] = sum(1 for r in wrong if r["final_line"] in lr
                                  and lr[r["final_line"]] != lr.get(r["true_line"]))
    s["per_pass"] = {r["key"]: bool(r["found_final"]) for r in rows}
    return s


def main() -> int:
    lock = claim_fh(STAGE)
    t0 = time.time()
    st, cfg, ne, transit, kind, alpha = shipped_pieces()
    import pipeline.constrained.decoder as D
    import pipeline.constrained.decoder2 as D2
    D.MAX_ADVANCE_M = None                 # THE DECISION SIDE: ceiling off, per extra 1
    D2._LT_CACHE.clear()
    status(f"{STAGE} START: A1 and A2, ceiling OFF for the decision, ON for the display")

    ARMS = {"shipped": {}, "A1": {"entry_window_m": ENTRY_WINDOW_M}}
    for w in WEIGHTS:
        ARMS[f"A2_{w}"] = {"_start_w": w}
    for w in WEIGHTS:
        ARMS[f"A1_A2_{w}"] = {"entry_window_m": ENTRY_WINDOW_M, "_start_w": w}

    RES = {"stage": STAGE, "ceiling_on_decision": False, "ceiling_on_display": True,
           "entry_window_m": ENTRY_WINDOW_M, "weights": list(WEIGHTS),
           "selection_folds": list(SELECTION_FOLDS), "per_arm": {}, "failures": []}

    cache, terms = {}, {}
    for tr_s, te_s in pairings():
        if tr_s == te_s:
            continue
        tag = tag_of(tr_s, te_s, False)
        src, _i = shipped_pool_emissions(tag, tr_s, te_s, False, st, kind, alpha)
        if src is None:
            continue
        cache[tag] = (tr_s, te_s, src)
        for w in WEIGHTS:
            terms[(tag, w)] = start_terms(tr_s, te_s, st, w)
    status(f"  {len(cache)} pairings; start terms built for {len(WEIGHTS)} weights")

    for name, A in ARMS.items():
        node = {}
        for tag, (tr_s, te_s, src) in cache.items():
            try:
                o = shipped_opts(st, tr_s)
                o["entry"] = "soft"
                if "entry_window_m" in A:
                    o["entry_window_m"] = A["entry_window_m"]
                if "_start_w" in A:
                    o["start_term"] = terms.get((tag, A["_start_w"]), {})
                node[tag] = arm_summary(src, st, cfg, ne, transit, o)
            except Exception as exc:                                     # noqa: BLE001
                import traceback
                RES["failures"].append({"arm": name, "tag": tag, "error": repr(exc),
                                        "traceback": traceback.format_exc()[-800:]})
        RES["per_arm"][name] = node
        v = [x["final_line_pct"] for x in node.values() if x]
        if v:
            status(f"  {name:14s} line {np.median(v):5.2f}  endsub "
                   f"{np.median([x['substitution_end_pct'] for x in node.values() if x]):5.1f}  "
                   f"not-starting-there {sum(x['not_starting_there'] for x in node.values() if x):3d}"
                   f"  reversed {sum(x['reversed'] for x in node.values() if x):3d}")

    def col(name, field="final_line_pct", decision=True):
        return {t: v[field] for t, v in RES["per_arm"][name].items()
                if v and (not decision or t not in SELECTION_FOLDS) and v.get(field) is not None}

    base = col("shipped")
    RES["aggregate"], ship = {}, {}
    for name in ARMS:
        node = RES["per_arm"][name]
        if not node:
            continue
        g = guard_verdict(float(np.median([x["substitution_end_pct"] for x in node.values() if x])),
                          float(np.median([x["substitution_line_pct"] for x in node.values() if x])))
        RES["aggregate"][name] = {
            "line_pct_decision7": float(np.median(list(col(name).values()))),
            "line_pct_all9": float(np.median(list(col(name, decision=False).values()))),
            "err_m": float(np.median([x["err_m"] for x in node.values()
                                      if x and x["err_m"] is not None])),
            "guard": g,
            "end_substitution_pct": float(np.median([x["substitution_end_pct"]
                                                     for x in node.values() if x])),
            "not_starting_there": int(sum(x["not_starting_there"] for x in node.values() if x)),
            "reversed": int(sum(x["reversed"] for x in node.values() if x)),
            "n_wrong": int(sum(x["n_wrong"] for x in node.values() if x)),
            "vs_shipped": both_readings(base, col(name)) if name != "shipped" else None}
        if name != "shipped":
            r = RES["aggregate"][name]["vs_shipped"]
            above = bool(r["interval_excludes_zero"] and r["median_of_paired_deltas_points"] > 0)
            ship[name] = {"paired_delta": r["median_of_paired_deltas_points"],
                          "paired_ci": r["paired_ci"],
                          "difference_of_medians": r["difference_of_medians_points"],
                          "interval_above_zero": above,
                          "guard_passes": bool(g["PASSES"]),
                          "end_substitution_pct": RES["aggregate"][name]["end_substitution_pct"],
                          "SHIPS": bool(above and g["PASSES"])}
    RES["ship_rule"] = ship
    winners = [k for k, v in ship.items() if v["SHIPS"]]
    RES["shipped_arm"] = (max(winners, key=lambda k: RES["aggregate"][k]["line_pct_decision7"])
                          if winners else None)
    RES["ships_nothing"] = not winners

    RES["minutes"] = round((time.time() - t0) / 60.0, 1)
    RES["contract"] = check_contract(RES, ["per_arm", "aggregate", "ship_rule"])
    save(STAGE, RES)
    release(lock)

    S = RES["aggregate"]["shipped"]
    status(f"  shipped: line {S['line_pct_decision7']:.2f}, not-starting-there "
           f"{S['not_starting_there']}, reversed {S['reversed']}, endsub "
           f"{S['end_substitution_pct']:.1f}")
    for k, v in ship.items():
        status(f"    {k:14s} {v['paired_delta']:+.2f} {[round(x,2) for x in v['paired_ci']]} "
               f"above zero {v['interval_above_zero']}  guard {v['guard_passes']} (endsub "
               f"{v['end_substitution_pct']:.1f})  SHIPS {v['SHIPS']}")
    status(f"  SHIPPED ARM = {RES['shipped_arm']}  ships nothing = {RES['ships_nothing']}")
    headline(f"Q4 ARMS: shipped arm = {RES['shipped_arm']}; baseline line "
             f"{S['line_pct_decision7']:.1f} percent with the ceiling off for the decision.")
    findings("q4", bool(RES["contract"]["SATISFIED"]), (
        f"PART 2 ARMS, ceiling OFF for the decision and ON for the display.\n\n"
        f"SHIPPED BASELINE: line {S['line_pct_decision7']:.2f} percent on the seven decision "
        f"pairings, {S['line_pct_all9']:.2f} on all nine; {S['not_starting_there']} commitments to "
        f"a line that does not start there and {S['reversed']} same-line reversals out of "
        f"{S['n_wrong']} errors; end substitution {S['end_substitution_pct']:.1f} percent.\n\n"
        + "\n".join(
            f"  {k:14s} line {RES['aggregate'][k]['line_pct_decision7']:.2f}, paired "
            f"{v['paired_delta']:+.2f} {v['paired_ci']}, difference of medians "
            f"{v['difference_of_medians']:+.2f}, not-starting-there "
            f"{RES['aggregate'][k]['not_starting_there']}, reversed "
            f"{RES['aggregate'][k]['reversed']}, end substitution "
            f"{v['end_substitution_pct']:.1f}, guard {v['guard_passes']}, SHIPS {v['SHIPS']}"
            for k, v in ship.items())
        + f"\n\nSHIPPED ARM = {RES['shipped_arm']}. Ships nothing = {RES['ships_nothing']}."))
    status(f"{STAGE} DONE in {RES['minutes']:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
