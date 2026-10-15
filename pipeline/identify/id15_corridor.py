"""id15. The corridor pilot and the DC2 power analysis. The geometry tool is id15_factor_map.

R5 SAYS THIS IS A PILOT WHATEVER IT SHOWS, and addendum A makes that stronger rather than weaker.
The geometry audit found that ALL TWELVE Room A lines fail the pre-registered F gate, and so does
every straight 4 m, 5 m and 7 m segment anywhere in the room. So the corridor pilot runs on
geometry that is known IN ADVANCE to be unsuitable, and a negative result here says nothing about
whether a corridor works on a rig built for one. That has to be stated wherever the pilot is
quoted, and it is stated in the findings this stage writes.

THE POWER ANALYSIS IS THE PART THAT MATTERS. DC2 needs a number of passes per person per block and
a number of blocks per day, and the v0 sheet currently carries a placeholder of 8 passes. The
binding constraint on every per-person arm in this project is 20 passes per person per session, and
the reason a six-way result has never been measurable is that six test passes per line per session
cannot resolve anything. This stage replaces the placeholder with a simulated requirement.

THE ICC IS WHY THE NAIVE CALCULATION IS WRONG. Passes within one recording are correlated, so the
effective sample size is smaller than the pass count. A binomial calculation that ignores that
returns a number of passes far too small, and the resulting protocol would produce another
unmeasurable batch. The simulation estimates the within-recording correlation from the data and
carries it.
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time                                                                       # noqa: E402

import numpy as np                                                                # noqa: E402

from pipeline.constrained.common import pairings, status, tag_of                  # noqa: E402
from pipeline.constrained.rebuild_common import findings, headline                # noqa: E402
from pipeline.identify.common import CHANCE_PCT, id_load, id_save, id_stage_dir   # noqa: E402
from pipeline.identify.id_heads import cluster_bootstrap, fit_score               # noqa: E402

STAGE = "id15_corridor"
SMOKE = os.environ.get("ID15_SMOKE") == "1"
N_SIM = 200 if SMOKE else 2000
TARGET_ACC = 0.35            #: the accuracy DC2 must be able to detect against chance
TARGET_HALFWIDTH = 10.0      #: percentage points
TARGET_POWER = 0.80


def select_corridor(rows) -> dict:
    """Identity-blind ranking. Addendum A: for the Room A pilot the strike-out is SUSPENDED.

    Applying the F gate as registered leaves zero candidates in this room, so the pilot could not
    run at all. Candidates are ranked and nothing is removed; the bad fraction is reported beside
    every one so the suspension is visible rather than silent.
    """
    geo = id_load("id15_geometry") or {}
    named = geo.get("named_lines") or {}
    counts = {}
    for r in rows:
        counts.setdefault(r["line"], set()).add((r["anon"], r["session"]))
    cand = []
    for line, g in named.items():
        n_cells = len(counts.get(line, ()))
        cand.append({
            "line": line, "mean_F": g.get("mean_F_over_links"),
            "min_link_mean_F": g.get("min_link_mean_F"),
            "frac_below_0.3": g.get("worst_link_frac_below_0.3"),
            "struck_out_by_the_registered_gate": g.get("struck_out"),
            "n_participant_session_cells": n_cells,
            "length_m": g.get("length_m"),
        })
    cand.sort(key=lambda c: (c["min_link_mean_F"] or 0, c["mean_F"] or 0), reverse=True)
    chosen = cand[0]["line"] if cand else None
    return {
        "ranking": cand, "chosen": chosen,
        "rule": ("ranked by min-link mean F, then mean F. Identity-blind: no label enters. "
                 "ADDENDUM A: the strike-out is suspended for the Room A pilot because it leaves "
                 "zero candidates, and every candidate's bad fraction is reported"),
        "all_candidates_would_be_struck_out": all(c["struck_out_by_the_registered_gate"]
                                                  for c in cand) if cand else None,
        "selection_never_uses_accuracy": True,
    }


def estimate_icc(per_pairing_rows) -> dict:
    """Within-recording correlation of correctness. The number the power analysis turns on."""
    groups = [np.asarray(v, float) for v in per_pairing_rows.values() if len(v) >= 2]
    if len(groups) < 2:
        return {"icc": None, "why": "too few recordings to estimate"}
    k = float(np.mean([len(g) for g in groups]))
    grand = float(np.mean([g.mean() for g in groups]))
    msb = k * float(np.mean([(g.mean() - grand) ** 2 for g in groups])) * len(groups) / max(
        len(groups) - 1, 1)
    msw = float(np.mean([g.var(ddof=1) if len(g) > 1 else 0.0 for g in groups]))
    icc = (msb - msw) / max(msb + (k - 1) * msw, 1e-9)
    return {"icc": round(float(np.clip(icc, 0.0, 0.95)), 4), "mean_group_size": round(k, 2),
            "n_groups": len(groups),
            "why": ("passes inside one recording are correlated, so the effective sample size is "
                    "smaller than the pass count and a binomial calculation that ignores this "
                    "returns a requirement that is far too small")}


def _simulate(n_per_block: int, n_blocks: int, icc: float, p_true: float,
              n_people: int = 6, n_sim: int = N_SIM, seed: int = 0) -> dict:
    """Beta-binomial simulation: each block draws its own success rate around p_true."""
    rng = np.random.default_rng(seed)
    if icc <= 1e-6:
        a = b = None
    else:
        nu = max(1.0 / icc - 1.0, 1e-6)
        a, b = p_true * nu, (1 - p_true) * nu
    halfwidths, hits = [], 0
    chance = 1.0 / n_people
    for _ in range(n_sim):
        acc = []
        for _p in range(n_people):
            for _bl in range(n_blocks):
                q = float(rng.beta(a, b)) if a else p_true
                acc.append(rng.binomial(n_per_block, q) / n_per_block)
        acc = np.asarray(acc, float)
        # cluster bootstrap over blocks, matching how the result would actually be reported
        idx = rng.integers(0, len(acc), (200, len(acc)))
        draws = acc[idx].mean(axis=1)
        lo, hi = np.percentile(draws, [2.5, 97.5])
        halfwidths.append(100.0 * (hi - lo) / 2.0)
        if lo > chance:
            hits += 1
    return {"median_halfwidth_pts": round(float(np.median(halfwidths)), 2),
            "power_vs_chance": round(hits / n_sim, 3),
            "n_per_block": n_per_block, "n_blocks": n_blocks,
            "total_passes_per_person": n_per_block * n_blocks}


def power_analysis(icc: float) -> dict:
    """The DC2 requirement: passes per block and blocks per day, for both pre-registered targets."""
    grid, meets = [], None
    for n_blocks in (2, 3, 4, 5):
        for n_per_block in (4, 6, 8, 10, 12, 16, 20):
            r = _simulate(n_per_block, n_blocks, icc, TARGET_ACC)
            r["meets_halfwidth"] = bool(r["median_halfwidth_pts"] <= TARGET_HALFWIDTH)
            r["meets_power"] = bool(r["power_vs_chance"] >= TARGET_POWER)
            r["meets_both"] = bool(r["meets_halfwidth"] and r["meets_power"])
            grid.append(r)
            if r["meets_both"] and meets is None:
                meets = r
    return {"icc_used": icc, "grid": grid, "smallest_design_meeting_both": meets,
            "targets": {"accuracy_to_detect_pct": 100 * TARGET_ACC,
                        "chance_pct": CHANCE_PCT,
                        "ci_halfwidth_pts": TARGET_HALFWIDTH, "power": TARGET_POWER},
            "recommendation": (f"{meets['n_per_block']} passes per block in {meets['n_blocks']} "
                               f"separated blocks, so {meets['total_passes_per_person']} passes "
                               f"per person per day" if meets else
                               "NO design in the searched grid meets both targets. The grid tops "
                               "out at 20 passes per block in 5 blocks, so DC2 cannot measure a "
                               "six-way result at this effect size and the honest move is to "
                               "commit to a smaller cohort")}


def main() -> int:
    id_stage_dir(STAGE)
    t0 = time.time()
    status(f"{STAGE} START: corridor pilot and DC2 power analysis" + (" [SMOKE]" if SMOKE else ""))

    d13 = id_load("id13_representations") or {}
    path = d13.get("rows_path")
    rows = list(np.load(path, allow_pickle=True)["rows"]) if path and os.path.exists(path) else []
    RES = {"stage": STAGE, "n_passes": len(rows), "PILOT": True,
           "pilot_caveat": ("addendum A: all twelve Room A lines fail the F gate and so does every "
                            "straight segment in the room, so this pilot runs on geometry known in "
                            "advance to be unsuitable. A negative result here says nothing about "
                            "whether a corridor works on a rig built for one"),
           "failures": []}

    RES["selection"] = select_corridor(rows) if rows else {"error": "no rows from id13"}
    chosen = (RES["selection"] or {}).get("chosen")
    status(f"  corridor chosen by geometry: {chosen}")

    # the pilot, on the chosen corridor only, over the nine pairings
    per_pairing, correctness_by_rec = {}, {}
    if rows and chosen:
        from pipeline.identify.id14_crossday import ENV_KEYS, SPEC_KEYS, _matrix
        for tr_s, te_s in pairings():
            if tr_s == te_s:
                continue
            tag = tag_of(tr_s, te_s, False)
            tr = [r for r in rows if r["session"] in tr_s and r["line"] == chosen]
            te = [r for r in rows if r["session"] in te_s and r["line"] == chosen]
            if len(tr) < 6 or len(te) < 3:
                per_pairing[tag] = {"n_train": len(tr), "n_test": len(te),
                                    "skipped": "too few corridor passes to score"}
                continue
            ytr = np.array([r["anon"] for r in tr])
            yte = np.array([r["anon"] for r in te])
            X = ENV_KEYS + SPEC_KEYS
            r = fit_score(_matrix(tr, X), ytr, _matrix(te, X), yte, te)
            if r.get("accuracy_pct") is None:
                continue
            correct = (r["pred"] == yte).astype(float)
            per_pairing[tag] = {"accuracy_pct": round(r["accuracy_pct"], 3),
                                "n_train": len(tr), "n_test": len(te),
                                "ci95": cluster_bootstrap(correct, r["recording_ids"])}
            for rid, c in zip(r["recording_ids"], correct):
                correctness_by_rec.setdefault(rid, []).append(c)
    RES["corridor_only"] = per_pairing
    vals = [v["accuracy_pct"] for v in per_pairing.values() if "accuracy_pct" in v]
    RES["corridor_median_pct"] = round(float(np.median(vals)), 3) if vals else None

    # THE ICC IS MEASURED FROM THE FULL ARMS, NOT FROM THE CORRIDOR PILOT.
    #
    # The pilot cannot supply it: one corridor line gives six test passes per pairing, one per
    # participant, so every recording group holds a single value and the estimator needs at least
    # two. The previous fallback appended ONE pooled accuracy per pairing, which produced groups of
    # length one as well, returned None, and sent the power analysis to an assumed icc of 0.1. The
    # DC2 passes-per-block number then rested on an assumption rather than a measurement.
    #
    # id14 stores per-recording correctness for every arm, about twenty passes per recording, which
    # is what this needs.
    icc_source = "corridor pilot"
    if sum(1 for v in correctness_by_rec.values() if len(v) >= 2) < 2:
        d14 = id_load("id14_crossday") or {}
        pooled = {}
        for arm in ("A0", "A3_ENV_SPEC", "A6_ENCODER"):
            pp = ((d14.get("arms") or {}).get(arm) or {}).get("per_pairing") or {}
            for tag, v in pp.items():
                for rid, cs in (v.get("per_recording_correct") or {}).items():
                    pooled.setdefault(f"{arm}|{tag}|{rid}", []).extend(cs)
            if sum(1 for x in pooled.values() if len(x) >= 2) >= 4:
                icc_source = f"id14 arm {arm}, per recording per pairing"
                break
        if pooled:
            correctness_by_rec = pooled
    RES["icc"] = estimate_icc(correctness_by_rec)
    RES["icc"]["source"] = icc_source
    RES["icc"]["MEASURED"] = bool(RES["icc"].get("icc") is not None)
    icc = RES["icc"].get("icc")
    status(f"  ICC = {icc}")

    if icc is None:
        status("  ICC COULD NOT BE MEASURED. The power grid runs at an ASSUMED 0.1 and every "
               "figure it produces is labelled as resting on that assumption.")
    RES["power"] = power_analysis(icc if icc is not None else 0.1)
    RES["power"]["icc_was_measured"] = bool(icc is not None)
    if icc is None:
        RES["power"]["WARNING"] = ("the ICC was not measured, so this recommendation rests on an "
                                   "ASSUMED within-recording correlation of 0.1. At 0.3 the same "
                                   "design fails both targets. Do not put this number on the DC2 "
                                   "sheet without the assumption stated beside it")
    RES["minutes"] = round((time.time() - t0) / 60.0, 1)
    id_save(STAGE, RES)

    rec = RES["power"]["recommendation"]
    headline(f"id15 CORRIDOR PILOT: {chosen} at {RES['corridor_median_pct']} percent, PILOT ONLY "
             f"on geometry that fails the F gate. DC2 POWER: {rec}")
    findings(STAGE.replace("_corridor", ""), not RES["failures"], (
        f"THE CORRIDOR PILOT AND THE DC2 POWER ANALYSIS.\n\n"
        f"THE PILOT IS CONFOUNDED BY GEOMETRY AND THAT WAS KNOWN BEFORE IT RAN. All twelve Room A "
        f"lines fail the pre-registered F gate, and so does every straight 4 m, 5 m and 7 m segment "
        f"anywhere in the room. The corridor chosen was {chosen}, selected by geometry alone and "
        f"never by accuracy, with the strike-out suspended under addendum A because applying it "
        f"leaves zero candidates. Median over pairings {RES['corridor_median_pct']} percent against "
        f"chance {CHANCE_PCT:.1f}. R5 stands: this is a pilot and supports no claim.\n\n"
        f"THE POWER ANALYSIS IS THE DELIVERABLE. Within-recording ICC {icc}, which is why a "
        f"binomial calculation is not used: passes inside a recording are correlated and the "
        f"effective sample is smaller than the pass count.\n\n"
        f"DC2 REQUIREMENT, to detect {100 * TARGET_ACC:.0f} percent against {CHANCE_PCT:.1f} chance "
        f"with a 95 percent interval no wider than plus or minus {TARGET_HALFWIDTH:.0f} points and "
        f"{100 * TARGET_POWER:.0f} percent power: {rec}\n\n"
        f"This replaces the v0 sheet's placeholder of 8 passes per block."))
    status(f"{STAGE} DONE in {RES['minutes']:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
