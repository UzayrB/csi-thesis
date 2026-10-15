"""ARMS (a), (b), (c) and (e): use a WEAK reader in a way that cannot harm.
Brief: reports/PREREG_prepress_v2_2026-09-22.md, written before any of this ran.

THE QUESTION IS NOT ACCURACY. The break-even measured on 2026-09-21 is about 74 percent and the
best reader available is AdaBN at 42.50 percent (u1_adapt), so no arm here can reach the point
where a region term starts BUYING line accuracy. What these arms test is whether a reader far
below break-even can be used so that it does not COST any either. A clean neutral is the realistic
best outcome and is worth having: it is the difference between unusable and safe to carry to
Room B.

  (a) VETO, NOT VOTE   the reader may only REMOVE regions it rules out confidently, never boost
                       one. The threshold is set on the SELECTION FOLDS so the true region is
                       vetoed on at most 2 percent of passes there, and the true-region veto rate
                       is then reported on the held-out folds where it is NOT controlled.
  (b) ABSTAIN          the term applies only where the reader's confidence clears a threshold set
                       on the selection folds. Coverage AND accuracy on covered passes, both,
                       because either alone is meaningless.
  (c) COARSE FIRST     midpoint against corner, then which midpoint when midpoint. Corners are
                       never forced, because corners read at chance.
  (e) CLASS-BALANCED   uniform class priors on the reader, with PER-REGION RECALL reported, so
                       arm C's collapse to W_mid at 0.9 percent cannot recur unnoticed.

Every arm goes through the DECODER and is judged on the committed line under the full rule,
conditions (a) to (f), on nine pairings with the three session-01 folds explicit. The demonstration
pairing is never the basis of a conclusion.
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.constrained.night_common import set_half_roots                      # noqa: E402
set_half_roots(REPO_ROOT)
from pipeline.constrained._guard import assert_isolated                           # noqa: E402
assert_isolated("u2_useit", os.path.join(REPO_ROOT, "runs", "artefacts_half"))

import time                                                                       # noqa: E402

import numpy as np                                                                # noqa: E402

from pipeline.constrained.common import pairings, status, tag_of                   # noqa: E402
from pipeline.constrained.fh_common import (both_readings, check_contract, claim_fh,  # noqa: E402
                                            release, save)
from pipeline.constrained.g3_final import shipped_pool_emissions                   # noqa: E402
from pipeline.constrained.n2_arms import run, summarise                            # noqa: E402
from pipeline.constrained.night_common import guard_verdict, shipped_pieces        # noqa: E402
from pipeline.constrained.q1_diag import REGIONS                                   # noqa: E402
from pipeline.constrained.q4_arms import start_terms                               # noqa: E402
from pipeline.constrained.r1_oldcensus import shipped_opts                         # noqa: E402
from pipeline.constrained.rebuild_common import findings, headline                 # noqa: E402
from pipeline.constrained.t0_oracle import by_region, line_regions                 # noqa: E402
from pipeline.constrained.t1_region import assert_grouped_by_pass                  # noqa: E402
from pipeline.constrained.u1_adapt import session_rows                             # noqa: E402

STAGE = "u2_useit"
SELECTION_FOLDS = ("s01_to_s02", "s02_to_s01")
SESSION01_FOLDS = ("s02_to_s01", "s03_to_s01", "s0203_to_s01")
DEMO_TAG = "s0102_to_s03"
EDGE_LINES = ("E_col1", "E_col5", "E_row1", "E_row5")
ENTRY_WINDOW_M = 1.0
SHIPPED_START_W = 0.5
ADAPT_MODE = "adabn"
WEIGHTS = (0.0, 0.25, 0.5, 1.0)
#: (a) the true region may be vetoed on at most this share of SELECTION-fold passes
VETO_TRUE_BUDGET = 0.02
#: a vetoed line is pushed down by this much rather than forbidden outright, so the decoder can
#: still choose it when the radio insists. A veto that cannot be overridden is a hard constraint
#: fitted to a 42 percent reader, which is exactly what this batch refuses elsewhere.
VETO_NATS = 3.0
CORNERS = ("SW", "NE", "NW", "SE")


def fit_reader(Xtr, ytr, Xte, balanced: bool):
    """The reader. balanced=True is arm (e): uniform class priors, nothing else changed."""
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    from sklearn.preprocessing import StandardScaler
    sc = StandardScaler().fit(Xtr)
    classes = sorted(set(ytr))
    pri = (np.ones(len(classes)) / len(classes)) if balanced else None
    clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto", priors=pri)
    clf.fit(sc.transform(Xtr), ytr)
    Z = sc.transform(Xte)
    return clf.predict(Z), clf.predict_proba(Z), list(clf.classes_)


def term_veto(keys, proba, classes, st, thr, weight):
    """(a) Only ever pushes a region DOWN, and only when its posterior is below thr."""
    lr = line_regions(st)
    ci = {c: i for i, c in enumerate(classes)}
    out = {}
    for row, key in enumerate(keys):
        p = np.asarray(proba[row], float)
        out[key] = {nm: (-weight * VETO_NATS if (r in ci and p[ci[r]] < thr) else 0.0)
                    for nm, r in lr.items()}
    return out


def term_abstain(keys, proba, classes, st, thr, weight):
    """(b) The ordinary centred term, but only on passes the reader is confident about."""
    lr = line_regions(st)
    ci = {c: i for i, c in enumerate(classes)}
    out, covered = {}, 0
    for row, key in enumerate(keys):
        p = np.asarray(proba[row], float)
        if float(p.max()) < thr:
            out[key] = {nm: 0.0 for nm in lr}
            continue
        covered += 1
        lp = np.log(np.clip(p, 1e-9, 1.0))
        base = float(np.mean(lp))
        out[key] = {nm: weight * float(lp[ci[r]] - base) for nm, r in lr.items() if r in ci}
    return out, covered


def term_coarse(keys, proba, classes, st, weight):
    """(c) Midpoint against corner, then which midpoint. Corners are never forced."""
    lr = line_regions(st)
    ci = {c: i for i, c in enumerate(classes)}
    mids = [c for c in classes if c not in CORNERS]
    out = {}
    for row, key in enumerate(keys):
        p = np.asarray(proba[row], float)
        p_mid = float(sum(p[ci[c]] for c in mids))
        d = {}
        for nm, r in lr.items():
            if r not in ci:
                d[nm] = 0.0
                continue
            if r in CORNERS:
                # the corner side carries ONE bit: how much mass is off the midpoints. No
                # preference between corners, because corners read at chance.
                d[nm] = weight * float(np.log(max(1.0 - p_mid, 1e-9)) - np.log(0.5))
            else:
                share = p[ci[r]] / max(p_mid, 1e-9)
                d[nm] = weight * (float(np.log(max(p_mid, 1e-9)) - np.log(0.5))
                                  + float(np.log(max(share, 1e-9))
                                          - np.log(1.0 / max(len(mids), 1))))
        out[key] = d
    return out


def merged(a, b):
    out = {}
    for k in set(a) | set(b):
        d = dict(a.get(k) or {})
        for nm, v in (b.get(k) or {}).items():
            d[nm] = d.get(nm, 0.0) + v
        out[k] = d
    return out


def main() -> int:
    lock = claim_fh(STAGE)
    t0 = time.time()
    st, cfg, ne, transit, kind, alpha = shipped_pieces()
    import pipeline.constrained.decoder as D
    import pipeline.constrained.decoder2 as D2
    D.MAX_ADVANCE_M = None
    D2._LT_CACHE.clear()
    lr = line_regions(st)
    status(f"{STAGE} START: arms (a) veto, (b) abstain, (c) coarse, (e) balanced, on the "
           f"{ADAPT_MODE} reader")

    RES = {"stage": STAGE, "brief": "reports/PREREG_prepress_v2_2026-09-22.md",
           "reader": f"u1_adapt {ADAPT_MODE}, 42.50 percent median region accuracy",
           "the_question": ("NOT whether a 42 percent reader can reach the 74 percent break-even, "
                            "which it cannot, but whether it can be used so it does not COST line "
                            "accuracy. A clean neutral is the realistic best outcome"),
           "veto_true_budget": VETO_TRUE_BUDGET, "veto_nats": VETO_NATS,
           "weights": list(WEIGHTS),
           "selection_folds": list(SELECTION_FOLDS), "session01_folds": list(SESSION01_FOLDS),
           "demo_tag_never_the_basis": DEMO_TAG,
           "per_arm": {}, "reader_quality": {}, "thresholds": {}, "failures": []}

    cache, prep = {}, {}
    for tr_s, te_s in pairings():
        if tr_s == te_s or len(te_s) != 1:
            continue
        tag = tag_of(tr_s, te_s, False)
        try:
            src, _i = shipped_pool_emissions(tag, tr_s, te_s, False, st, kind, alpha)
            if src is None:
                continue
            Xtr, ytr, ktr, _w1, utr, _a1 = session_rows(tr_s, st, ADAPT_MODE, cache)
            Xte, yte, kte, _w2, ute, _a2 = session_rows(te_s, st, ADAPT_MODE, cache)
            if not len(Xtr) or not len(Xte):
                continue
            assert_grouped_by_pass(ktr, utr)
            assert_grouped_by_pass(kte, ute)
            assert not (set(ktr) & set(kte)), "leakage: a pass on both sides"
            node = {}
            for bal in (False, True):
                pred, proba, classes = fit_reader(Xtr, ytr, Xte, bal)
                node["balanced" if bal else "plain"] = {
                    "pred": pred, "proba": proba, "classes": classes,
                    "acc": 100.0 * float(np.mean([a == b for a, b in zip(yte, pred)]))}
            prep[tag] = {"tr_s": tr_s, "te_s": te_s, "src": src, "keys": kte, "truth": yte,
                         "a3": start_terms(tr_s, te_s, st, SHIPPED_START_W), **node}
            RES["reader_quality"][tag] = {
                "plain_pct": round(node["plain"]["acc"], 3),
                "balanced_pct": round(node["balanced"]["acc"], 3)}
        except Exception as exc:                                         # noqa: BLE001
            import traceback
            RES["failures"].append({"tag": tag, "stage": "prep", "error": repr(exc),
                                    "traceback": traceback.format_exc()[-900:]})
    status(f"  {len(prep)} pairings prepared; reader median "
           f"{np.median([v['plain_pct'] for v in RES['reader_quality'].values()]):.2f} plain, "
           f"{np.median([v['balanced_pct'] for v in RES['reader_quality'].values()]):.2f} balanced")

    # ---- thresholds, chosen on the SELECTION FOLDS ONLY
    sel = [t for t in prep if t in SELECTION_FOLDS]
    def choose_veto_thr(key):
        cand = np.arange(0.01, 0.51, 0.01)
        for thr in cand:
            bad = n = 0
            for t in sel:
                P = prep[t][key]
                ci = {c: i for i, c in enumerate(P["classes"])}
                for row, tr_ in enumerate(prep[t]["truth"]):
                    n += 1
                    if tr_ in ci and float(P["proba"][row][ci[tr_]]) < thr:
                        bad += 1
            if n and bad / n > VETO_TRUE_BUDGET:
                return float(max(0.01, thr - 0.01))
        return float(cand[-1])

    def choose_abstain_thr(key):
        cand = np.arange(0.20, 0.91, 0.05)
        best = (None, -1.0)
        for thr in cand:
            hit = n = 0
            for t in sel:
                P = prep[t][key]
                for row, tr_ in enumerate(prep[t]["truth"]):
                    if float(np.max(P["proba"][row])) >= thr:
                        n += 1
                        hit += int(P["pred"][row] == tr_)
            if n >= 20:
                acc = hit / n
                if acc > best[1]:
                    best = (float(thr), acc)
        return best[0] if best[0] is not None else 0.5

    for key in ("plain", "balanced"):
        RES["thresholds"][key] = {"veto": choose_veto_thr(key),
                                  "abstain": choose_abstain_thr(key),
                                  "chosen_on": list(SELECTION_FOLDS)}
    status(f"  thresholds {RES['thresholds']}")

    ARMS = {"shipped": {}}
    for w in WEIGHTS:
        if w == 0.0:
            continue
        ARMS[f"a_veto_{w}"] = {"kind": "veto", "w": w, "reader": "plain"}
        ARMS[f"b_abstain_{w}"] = {"kind": "abstain", "w": w, "reader": "plain"}
        ARMS[f"c_coarse_{w}"] = {"kind": "coarse", "w": w, "reader": "plain"}
    ARMS["e_balanced_veto_0.5"] = {"kind": "veto", "w": 0.5, "reader": "balanced"}
    ARMS["e_balanced_abstain_0.5"] = {"kind": "abstain", "w": 0.5, "reader": "balanced"}

    cov_tally = {}
    for name, A in ARMS.items():
        node = {}
        for tag, C in prep.items():
            try:
                o = shipped_opts(st, C["tr_s"])
                o["entry"] = "soft"
                o["entry_window_m"] = ENTRY_WINDOW_M
                term = dict(C["a3"])
                if A:
                    P = C[A["reader"]]
                    thr = RES["thresholds"][A["reader"]]
                    if A["kind"] == "veto":
                        extra = term_veto(C["keys"], P["proba"], P["classes"], st,
                                          thr["veto"], A["w"])
                    elif A["kind"] == "abstain":
                        extra, cov = term_abstain(C["keys"], P["proba"], P["classes"], st,
                                                  thr["abstain"], A["w"])
                        cov_tally.setdefault(name, []).append(100.0 * cov / max(1, len(C["keys"])))
                    else:
                        extra = term_coarse(C["keys"], P["proba"], P["classes"], st, A["w"])
                    term = merged(term, extra)
                o["start_term"] = term
                rows = run(C["src"], st, cfg, ne, transit, o, subs=True)
                s = summarise(rows)
                if s is None:
                    continue
                s["by_region"] = by_region(rows, lr)
                s["not_starting_there"] = int(sum(
                    1 for r in rows if not r["found_final"]
                    and lr.get(r.get("final_line")) != lr.get(r.get("true_line"))))
                node[tag] = s
            except Exception as exc:                                     # noqa: BLE001
                import traceback
                RES["failures"].append({"arm": name, "tag": tag, "error": repr(exc),
                                        "traceback": traceback.format_exc()[-900:]})
        RES["per_arm"][name] = node
        v = [x["final_line_pct"] for x in node.values() if x]
        if v:
            status(f"  {name:24s} all9 {np.median(v):5.2f}")

    def col(name, held=True):
        node = RES["per_arm"].get(name) or {}
        return {t: v["final_line_pct"] for t, v in node.items()
                if v and (t not in SELECTION_FOLDS if held else True)}

    base = col("shipped")
    base_edge = {}
    bn = RES["per_arm"]["shipped"]
    for t, v in bn.items():
        if t in SELECTION_FOLDS or not v:
            continue
        for ln, d in (v.get("per_line_recall_pct") or {}).items():
            base_edge.setdefault(ln, []).append(d)
    base_edge = {k: float(np.mean(x)) for k, x in base_edge.items()}

    RES["aggregate"], ship = {}, {}
    for name in ARMS:
        node = RES["per_arm"][name]
        if not node:
            continue
        edge = {}
        for t, v in node.items():
            if t in SELECTION_FOLDS or not v:
                continue
            for ln, d in (v.get("per_line_recall_pct") or {}).items():
                edge.setdefault(ln, []).append(d)
        edge = {k: float(np.mean(x)) for k, x in edge.items()}
        g = guard_verdict(
            float(np.median([x["substitution_end_pct"] for x in node.values()
                             if x and x["substitution_end_pct"] is not None])),
            float(np.median([x["substitution_line_pct"] for x in node.values()
                             if x and x["substitution_line_pct"] is not None])))
        RES["aggregate"][name] = {
            "line_pct_heldout7": float(np.median(list(col(name).values()))) if col(name) else None,
            "line_pct_all9": float(np.median(list(col(name, held=False).values()))),
            "session01_folds": {t: round(col(name, held=False).get(t, float("nan")), 3)
                                for t in SESSION01_FOLDS},
            "edge_line_recall_pct": {k: round(edge.get(k, float("nan")), 2) for k in EDGE_LINES},
            "per_line_recall_pct": {k: round(v_, 2) for k, v_ in sorted(edge.items())},
            "guard": g,
            "coverage_pct": (round(float(np.mean(cov_tally[name])), 2)
                             if name in cov_tally else None),
            "vs_shipped_heldout": both_readings(base, col(name)) if name != "shipped" else None}
        if name != "shipped":
            r = RES["aggregate"][name]["vs_shipped_heldout"]
            # UNROUNDED ON BOTH SIDES. The payload rounds edge_line_recall_pct to 2 dp for
            # readability; comparing that rounded value against the unrounded baseline made an
            # EXACT TIE fail by up to 0.005, so every arm read edge_ok False including ones whose
            # edge lines were strictly better. Caught 2026-09-22 by reading the per-line table
            # rather than the flag.
            edge_ok = all(edge.get(ln, 0.0) >= base_edge.get(ln, 0.0) - 1e-9 for ln in EDGE_LINES)
            e = RES["aggregate"][name]["edge_line_recall_pct"]
            cond = {
                "a_interval_above_zero": bool(r["interval_excludes_zero"]
                                              and (r["median_of_paired_deltas_points"] or 0) > 0),
                # IN PASSES, NOT IN POINTS. The delta is inherently a multiple of one pass,
                # 100/120 = 0.8333 points, so comparing two floats that both represent exactly two
                # passes fails on the last bit: a_veto_1.0 measured 1.6666666666666665 against a
                # bar of 1.6666666666666667 and was rejected by floating-point noise rather than
                # by the rule. Convert to passes and compare integers.
                "b_at_least_two_passes": bool(
                    round((r["median_of_paired_deltas_points"] or 0.0) / (100.0 / 120.0)) >= 2),
                "b_passes_per_pairing": round((r["median_of_paired_deltas_points"] or 0.0)
                                              / (100.0 / 120.0), 2),
                "d_substitution": bool(g["PASSES"]),
                "f_edge_lines_not_degraded": edge_ok,
                "edge_deltas": {ln: round(edge.get(ln, 0.0) - base_edge.get(ln, 0.0), 3)
                                for ln in EDGE_LINES},
                "paired_delta": r["median_of_paired_deltas_points"],
                "paired_ci": r["paired_ci"],
                "difference_of_medians": r["difference_of_medians_points"]}
            cond["SHIPS"] = bool(cond["a_interval_above_zero"] and cond["b_at_least_two_passes"]
                                 and cond["d_substitution"] and cond["f_edge_lines_not_degraded"])
            cond["DOES_NO_HARM"] = bool(
                (r["paired_ci"][0] if r["paired_ci"][0] is not None else -99) >= -100.0 / 60.0
                and edge_ok)
            ship[name] = cond
    RES["ship_rule"] = ship
    # (c) monotonicity is read per family, since each family has its own weight sweep
    # CONDITION (c) IS READ ON THE PAIRED DELTA, the same quantity conditions (a) and (b) use.
    #
    # The first version read it on the median held-out figure, which is a DIFFERENT quantity and
    # is subject to the median-swap artefact this project has documented twice. On b_abstain the
    # two disagree completely: the median falls monotonically, 74.17, 71.67, 70.83, while the
    # paired delta RISES then FALLS, +2.50, +3.33, +0.83. Reading (c) on the median therefore
    # passed an arm that a consistent reading fails. Conditions of one rule must be read on one
    # quantity.
    #
    # w = 0 IS INCLUDED as the anchor: at zero weight the arm IS the baseline and its delta is
    # exactly zero by construction, so the shape of the response is visible rather than inferred
    # from the swept points alone.
    RES["weight_sweeps"] = {}
    for fam in ("a_veto", "b_abstain", "c_coarse"):
        pairs = [(0.0, 0.0)]
        for w in WEIGHTS:
            if w == 0.0:
                continue
            c_ = ship.get(f"{fam}_{w}")
            if c_ and c_.get("paired_delta") is not None:
                pairs.append((w, float(c_["paired_delta"])))
        d = [pairs[i + 1][1] - pairs[i][1] for i in range(len(pairs) - 1)]
        RES["weight_sweeps"][fam] = {
            "quantity": "median paired delta against the shipped baseline, held-out folds",
            "pairs": [(w, round(v, 3)) for w, v in pairs], "steps": [round(x, 3) for x in d],
            "monotone": bool(all(x >= -1e-9 for x in d) or all(x <= 1e-9 for x in d)),
            "also_the_median_curve": [(w, (RES["aggregate"].get(f"{fam}_{w}") or {}).get(
                "line_pct_heldout7")) for w in WEIGHTS if w != 0.0]}
    for name, c in ship.items():
        fam = name.rsplit("_", 1)[0].replace("e_balanced_", "")
        c["c_monotone_in_w"] = RES["weight_sweeps"].get(
            fam if fam in RES["weight_sweeps"] else "a_veto", {}).get("monotone")
        c["SHIPS"] = bool(c["SHIPS"] and c["c_monotone_in_w"])

    winners = [k for k, v in ship.items() if v["SHIPS"]]
    RES["shipped_arm"] = (max(winners, key=lambda k: RES["aggregate"][k]["line_pct_heldout7"])
                          if winners else None)
    RES["ships_nothing"] = not winners
    RES["harmless_arms"] = [k for k, v in ship.items() if v["DOES_NO_HARM"]]

    RES["minutes"] = round((time.time() - t0) / 60.0, 1)
    RES["contract"] = check_contract(RES, ["per_arm", "aggregate", "ship_rule", "thresholds"])
    save(STAGE, RES)
    release(lock)

    B = RES["aggregate"]["shipped"]
    status(f"  BASELINE held-out7 {B['line_pct_heldout7']:.2f}, edge {B['edge_line_recall_pct']}")
    for k, v in ship.items():
        a = RES["aggregate"][k]
        status(f"  {k:24s} {a['line_pct_heldout7']:5.2f}  paired {v['paired_delta']:+6.2f} "
               f"ci {[round(x, 2) for x in v['paired_ci']]}  edge_ok {v['f_edge_lines_not_degraded']}"
               f"  harmless {v['DOES_NO_HARM']}  SHIPS {v['SHIPS']}")
    status(f"  SHIPPED ARM: {RES['shipped_arm']}  harmless: {RES['harmless_arms']}")
    headline(f"U2 USE-IT: shipped arm = {RES['shipped_arm']}; arms that do no harm: "
             f"{len(RES['harmless_arms'])} of {len(ship)}; baseline held-out7 "
             f"{B['line_pct_heldout7']:.2f} percent")
    findings("u2useit", bool(RES["contract"]["SATISFIED"]), (
        f"USING A WEAK READER WITHOUT HARM. Arms (a), (b), (c), (e).\n\n"
        f"Reader: AdaBN, median {np.median([v['plain_pct'] for v in RES['reader_quality'].values()]):.2f} "
        f"percent. Break-even is about 74, so no arm can BUY accuracy; the test is whether any "
        f"COSTS it.\n\n" +
        "\n".join(f"  {k:24s} {RES['aggregate'][k]['line_pct_heldout7']:6.2f}  paired "
                  f"{v['paired_delta']:+6.2f} ci {[round(x, 2) for x in v['paired_ci']]}  "
                  f"harmless {v['DOES_NO_HARM']}  ships {v['SHIPS']}"
                  for k, v in ship.items()) +
        f"\n\nShipped arm: {RES['shipped_arm']}. Arms that do no harm: {RES['harmless_arms']}\n"
        f"Brief: reports/PREREG_prepress_v2_2026-09-22.md"))
    return 0 if RES["contract"]["SATISFIED"] else 1


if __name__ == "__main__":
    sys.exit(main())
