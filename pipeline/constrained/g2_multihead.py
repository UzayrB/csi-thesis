"""IMPROVEMENT 1, step two: multi-head ensembles of the frozen heads.

WHY THIS IS THE LEAD. Pooling ONE 1 s head set with the 0.5 s set added 7.5 points to semi-bounded
and 5.0 to bounded, and it is the only lever in this line of work that improved the number without
compromising the end. Every other gain came from making the end partly a clock, which the guard
refuses. This asks the obvious next question: if two heads bought that, what do three and four buy?

THE POOL IS A LOG-OPINION POOL, an equal-weight average of log posteriors, renormalised per window.
That is the geometric mean, the neutral way to combine independently trained models that each claim
a distribution over the same cells. Equal weight means there is NOTHING TO SELECT, so the headline
arms carry no selection to audit. A weighted pool is reported separately because it does.

SEPARATING MORE HEADS FROM MORE DIVERSITY. A 1 s-only pool of the three 1 s seeds is run beside the
mixed pools. If the mixed pool wins, the lever is stride diversity; if the 1 s-only pool matches it,
the lever is simply more heads. That distinction decides where the next effort goes, so it is
measured here rather than argued later.
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.constrained.night_common import set_half_roots                      # noqa: E402
set_half_roots(REPO_ROOT)
from pipeline.constrained._guard import assert_isolated                           # noqa: E402
assert_isolated("g2_multihead", os.path.join(REPO_ROOT, "runs", "artefacts_half"))

import json                                                                       # noqa: E402
import time                                                                       # noqa: E402

import numpy as np                                                                # noqa: E402

from pipeline.constrained.common import E_POST, is_cross, pairings, status, tag_of  # noqa: E402
from pipeline.constrained.fh_common import both_readings, check_contract, claim_fh, load, release, save  # noqa
from pipeline.constrained.night_arms import default_opts                           # noqa: E402
from pipeline.constrained.night_common import (STRIDE, assert_motion_model, guard_verdict,  # noqa
                                               pairing_emissions, shipped_pieces)
from pipeline.constrained.n2_arms import fit_chain_prior, run, summarise            # noqa: E402
from pipeline.constrained.rebuild_common import findings, headline                  # noqa: E402
from pipeline.constrained.sb2_structural import selection_pairing_for               # noqa: E402

STAGE = "g2_multihead"
SEED = 0
NIGHT_COMBO = ["C_family", "G_maxlik", "I_chainprior"]
#: where each 1 s seed's posteriors over the 0.5 s windows live
from pipeline.constrained.lattice import one_s_trees as _one_s_trees                # noqa: E402
ONE_S_TREES = _one_s_trees()             # the ONE lattice's 1 s trees, since 2026-09-23d
WEIGHT_GRID = (0.3, 0.5, 0.7)      #: weight on the 0.5 s head in the weighted pool


def pool(emissions):
    """Equal-weight log-opinion pool of N emissions, renormalised per window."""
    n = min(len(e) for e in emissions)
    m = np.mean([np.asarray(e[:n], float) for e in emissions], axis=0)
    return m - m.max(axis=1, keepdims=True)


def weighted_pool(e_half, e_others, w_half):
    """w_half on the 0.5 s head, the remainder shared equally among the 1 s heads."""
    n = min([len(e_half)] + [len(e) for e in e_others])
    rest = (1.0 - w_half) / max(1, len(e_others))
    m = w_half * np.asarray(e_half[:n], float)
    for e in e_others:
        m = m + rest * np.asarray(e[:n], float)
    return m - m.max(axis=1, keepdims=True)


def one_second_for(tree, tag, tr_s, te_s, within, st, kind, alpha, seed, fusion_w=0.0):
    from pipeline.constrained.artefacts import read_full_posteriors
    from pipeline.constrained.dataset import sides
    from pipeline.constrained.emissions import cell_emission, cell_marginal, scaled_cell_emission
    p = os.path.join(REPO_ROOT, tree, "posteriors", f"{tag}_g25_e{E_POST}_s{seed}_full.npz")
    if not os.path.exists(p):
        return None
    marg = (cell_marginal(sides(tr_s, te_s, within, with_features=False)[0].xy, 25)
            if kind == "scaled" else None)
    out = {}
    for stem, b in read_full_posteriors(p).items():
        from pipeline.constrained.fusion import fused_prob
        prob = fused_prob(b, fusion_w).astype(float)
        out[stem] = (cell_emission(prob, st.xy, 25) if marg is None
                     else scaled_cell_emission(prob, st.xy, 25, marg, alpha=alpha))
    return out


def bounded_rows(src, st):
    from pipeline.constrained.rb10_bounded_demo import bounded_track
    rows = []
    for _stem, rec, _ge, e in src:
        bt = bounded_track(e, rec, st, None)
        v = {q["pass_id"]: q for q in bt["passes"]}
        for pid, nm, _a, _b in rec.pass_spans():
            if pid in v:
                rows.append({"key": f"{rec.session}|{rec.stem}|{int(pid)}",
                             "found": bool(v[pid]["found"]),
                             "err": v[pid]["median_error_m"]})
    return rows


def bounded_summary(rows):
    if not rows:
        return None
    err = [r["err"] for r in rows if r["found"] and r["err"] is not None]
    return {"n": len(rows), "line_pct": 100.0 * float(np.mean([r["found"] for r in rows])),
            "err_m": float(np.median(err)) if err else None}


def main() -> int:
    lock = claim_fh(STAGE)
    t0 = time.time()
    st, cfg, ne, transit, kind, alpha = shipped_pieces()
    mm = assert_motion_model()
    have = {s: t for s, t in ONE_S_TREES.items()
            if os.path.isdir(os.path.join(REPO_ROOT, t, "posteriors"))}
    status(f"{STAGE} START: multi-head pools. 1 s seeds available: {sorted(have)}")
    status(f"  motion model {mm['step_m_per_window']:.3f} m per window")

    RES = {"stage": STAGE, "stride_s": STRIDE, "seeds_available": sorted(have),
           "weight_grid": list(WEIGHT_GRID), "night_combo": NIGHT_COMBO,
           "pool_rule": ("equal-weight log-opinion pool, renormalised per window; no weight is "
                         "swept in the headline arms so there is nothing to select"),
           "per_pairing": {}, "failures": []}

    n2 = json.load(open(os.path.join(REPO_ROOT, "runs", "constrained", "night", "n2_arms",
                                     "results.json"), encoding="utf-8"))
    arm_opts = {}
    for _t, v in (n2.get("per_pairing") or {}).items():
        for n_, row in (v.get("arms") or {}).items():
            if row and row.get("opts") is not None:
                arm_opts[n_] = {k: ("FIT" if val == "fitted" else val)
                                for k, val in row["opts"].items()}
        break

    cache = {}
    for tr_s, te_s in pairings():
        within = tr_s == te_s
        tag = tag_of(tr_s, te_s, within)
        try:
            src = pairing_emissions(tag, tr_s, te_s, within, st, kind, alpha)
            if src is None:
                RES["failures"].append({"tag": tag, "error": "no 0.5 s posteriors"})
                continue
            ones = {}
            for s_, tree in have.items():
                o = one_second_for(tree, tag, tr_s, te_s, within, st, kind, alpha, s_)
                if o is not None:
                    ones[s_] = o
            if not ones:
                RES["failures"].append({"tag": tag, "error": "no 1 s posteriors for any seed"})
                continue

            prior = fit_chain_prior(st, tr_s)
            opts = default_opts()
            for n_ in NIGHT_COMBO:
                for k, val in (arm_opts.get(n_) or {}).items():
                    opts[k] = prior if val == "FIT" else val

            def build(stem_list, seeds, include_half=True, w_half=None):
                out = []
                for stem, rec, ge, e in src:
                    parts = [ones[s_][stem] for s_ in seeds if stem in ones.get(s_, {})]
                    if len(parts) != len(seeds):
                        return None
                    if w_half is not None:
                        em = weighted_pool(e, parts, w_half)
                    else:
                        em = pool(([e] if include_half else []) + parts)
                    out.append((stem, rec, ge, em))
                return out

            arms = {}
            seeds = sorted(ones)
            # the headline family: the 0.5 s head pooled with 1, 2 or 3 of the 1 s seeds
            for k_ in range(1, len(seeds) + 1):
                name = f"mixed_{k_ + 1}head"
                s2 = build(src, seeds[:k_])
                if s2 is None:
                    continue
                arms[name] = {"semib": summarise(run(s2, st, cfg, ne, transit, opts)),
                              "bounded": bounded_summary(bounded_rows(s2, st)),
                              "n_heads": k_ + 1, "kind": "mixed stride"}
            # the control: 1 s seeds ONLY, which separates more heads from more diversity
            if len(seeds) >= 2:
                s_only = build(src, seeds, include_half=False)
                if s_only is not None:
                    arms[f"oneS_only_{len(seeds)}head"] = {
                        "semib": summarise(run(s_only, st, cfg, ne, transit, opts)),
                        "bounded": bounded_summary(bounded_rows(s_only, st)),
                        "n_heads": len(seeds), "kind": "single stride, 1 s only"}
            # the baseline, no pooling at all
            arms["half_only_1head"] = {
                "semib": summarise(run(src, st, cfg, ne, transit, opts)),
                "bounded": bounded_summary(bounded_rows(src, st)),
                "n_heads": 1, "kind": "single stride, 0.5 s only"}
            for a in arms.values():
                if a["semib"]:
                    a["guard"] = guard_verdict(a["semib"]["substitution_end_pct"],
                                               a["semib"]["substitution_line_pct"])

            # the weighted pool, selected on a pairing that never touches this test session
            sel_tag, sel_pair = selection_pairing_for(tr_s, te_s)
            chosen, basis = 0.5, "default 0.5: no selection pairing avoids this test session"
            if sel_tag is not None and len(seeds) >= 1:
                s_tr, s_te = sel_pair
                if sel_tag not in cache:
                    cache[sel_tag] = (pairing_emissions(sel_tag, s_tr, s_te, False, st, kind, alpha),
                                      {s_: one_second_for(ONE_S_TREES[s_], sel_tag, s_tr, s_te,
                                                          False, st, kind, alpha, s_)
                                       for s_ in seeds})
                ssrc, sones = cache[sel_tag]
                if ssrc is not None and all(sones.get(s_) for s_ in seeds):
                    sc = {}
                    for w in WEIGHT_GRID:
                        built = [(stm, rc, g, weighted_pool(e, [sones[s_][stm] for s_ in seeds], w))
                                 for stm, rc, g, e in ssrc if all(stm in sones[s_] for s_ in seeds)]
                        sc[w] = (summarise(run(built, st, cfg, ne, transit, opts)) or {}
                                 ).get("final_line_pct", -1)
                    spread = max(sc.values()) - min(sc.values())
                    if spread < 1e-9:
                        basis = f"NOT SELECTED: every weight scored the same on {sel_tag}"
                    else:
                        chosen = max(WEIGHT_GRID, key=lambda w: sc[w])
                        basis = (f"selected on {sel_tag}, which never trains or tests on session "
                                 f"{te_s[0]}")
                    RES.setdefault("weight_selection", {})[tag] = {
                        "w_half": chosen, "basis": basis,
                        "scores": {str(k): v for k, v in sc.items()}}
            wsrc = build(src, seeds, w_half=chosen)
            if wsrc is not None:
                arms["weighted"] = {"semib": summarise(run(wsrc, st, cfg, ne, transit, opts)),
                                    "bounded": bounded_summary(bounded_rows(wsrc, st)),
                                    "n_heads": len(seeds) + 1, "kind": "mixed, weighted",
                                    "w_half": chosen, "selection_basis": basis}
                if arms["weighted"]["semib"]:
                    arms["weighted"]["guard"] = guard_verdict(
                        arms["weighted"]["semib"]["substitution_end_pct"],
                        arms["weighted"]["semib"]["substitution_line_pct"])

            RES["per_pairing"][tag] = {"regime": "cross" if is_cross(tag) else "within",
                                       "arms": arms}
            base = arms["half_only_1head"]["semib"]["final_line_pct"]
            best = max((a for a in arms.values() if a.get("semib")),
                       key=lambda a: a["semib"]["final_line_pct"])
            status(f"  {tag:16s} [{'cross' if is_cross(tag) else 'within':6s}] base {base:5.1f} -> "
                   f"best {best['semib']['final_line_pct']:5.1f} ({best['kind']}, "
                   f"{best['n_heads']} heads)")
        except Exception as exc:                                         # noqa: BLE001
            import traceback
            RES["failures"].append({"tag": tag, "error": repr(exc),
                                    "traceback": traceback.format_exc()[-1500:]})
            status(f"  {tag:16s} FAILED {exc!r}")

    cross = {k: v for k, v in RES["per_pairing"].items() if v["regime"] == "cross"}
    names = sorted({k for p in cross.values() for k in p["arms"]})

    def col(arm, which, field):
        return {t: p["arms"][arm][which][field] for t, p in cross.items()
                if p["arms"].get(arm) and p["arms"][arm].get(which)
                and p["arms"][arm][which].get(field) is not None}

    def med(arm, which, field):
        c = col(arm, which, field)
        return float(np.median(list(c.values()))) if c else None

    by = {}
    for a in names:
        by[a] = {
            "n_heads": next((p["arms"][a]["n_heads"] for p in cross.values()
                             if p["arms"].get(a)), None),
            "kind": next((p["arms"][a]["kind"] for p in cross.values() if p["arms"].get(a)), None),
            "semibounded_pct": med(a, "semib", "final_line_pct"),
            "semibounded_err_m": med(a, "semib", "err_m"),
            "bounded_pct": med(a, "bounded", "line_pct"),
            "bounded_err_m": med(a, "bounded", "err_m"),
            "end_substitution_pct": med(a, "semib", "substitution_end_pct"),
            "line_substitution_pct": med(a, "semib", "substitution_line_pct"),
            "exit_dt_press_median_s": med(a, "semib", "exit_dt_press_median_s"),
            "never_ended_pct": med(a, "semib", "never_ended_pct")}
        by[a]["guard"] = guard_verdict(by[a]["end_substitution_pct"],
                                       by[a]["line_substitution_pct"])
        if a != "half_only_1head":
            by[a]["vs_baseline"] = both_readings(col("half_only_1head", "semib", "final_line_pct"),
                                                 col(a, "semib", "final_line_pct"))
    RES["cross_day"] = {"n_pairings": len(cross), "by_arm": by}

    scored = [a for a in names if by[a]["semibounded_pct"] is not None]
    passing = [a for a in scored if by[a]["guard"]["PASSES"]]
    best_overall = max(scored, key=lambda a: by[a]["semibounded_pct"]) if scored else None
    best_pass = max(passing, key=lambda a: by[a]["semibounded_pct"]) if passing else None
    RES["gate"] = {
        "n_scored": len(scored), "n_passing": len(passing),
        "best_overall_arm": best_overall,
        "best_overall_pct": by[best_overall]["semibounded_pct"] if best_overall else None,
        "best_overall_passes_guard": by[best_overall]["guard"]["PASSES"] if best_overall else None,
        "best_guard_passing_arm": best_pass,
        "best_guard_passing_pct": by[best_pass]["semibounded_pct"] if best_pass else None,
        "baseline_pct": by.get("half_only_1head", {}).get("semibounded_pct")}

    # MORE HEADS OR MORE DIVERSITY, the question this stage exists to answer
    mixed = [a for a in names if by[a]["kind"] == "mixed stride"]
    only = [a for a in names if by[a]["kind"] == "single stride, 1 s only"]
    best_mixed = max(mixed, key=lambda a: by[a]["semibounded_pct"] or -1) if mixed else None
    RES["heads_or_diversity"] = {
        "best_mixed_arm": best_mixed,
        "best_mixed_pct": by[best_mixed]["semibounded_pct"] if best_mixed else None,
        "one_second_only_arm": only[0] if only else None,
        "one_second_only_pct": by[only[0]]["semibounded_pct"] if only else None,
        "reading": None}
    h = RES["heads_or_diversity"]
    if h["best_mixed_pct"] is not None and h["one_second_only_pct"] is not None:
        h["mixed_minus_singlestride_points"] = h["best_mixed_pct"] - h["one_second_only_pct"]
        h["reading"] = (
            "STRIDE DIVERSITY is doing the work: a pool that mixes strides beats a pool of the "
            "same number of single-stride heads, so the next effort belongs on different windows "
            "or gates rather than more seeds."
            if h["mixed_minus_singlestride_points"] > 1.0 else
            "MORE HEADS is doing the work: a single-stride pool matches the mixed one, so extra "
            "seeds at one stride are as good as stride diversity and are the cheaper path.")

    RES["minutes"] = round((time.time() - t0) / 60.0, 1)
    RES["contract"] = check_contract(RES, ["per_pairing", "cross_day", "gate",
                                           "heads_or_diversity"], {"per_pairing": 9})
    save(STAGE, RES)
    release(lock)

    g = RES["gate"]
    status(f"  CROSS-DAY over {len(cross)} pairings:")
    for a in sorted(names, key=lambda a: -(by[a]["semibounded_pct"] or 0)):
        status(f"    {a:24s} {by[a]['n_heads']}h semi {by[a]['semibounded_pct']} bounded "
               f"{by[a]['bounded_pct']} guard {by[a]['guard']['PASSES']}")
    status(f"  BEST GUARD-PASSING {g['best_guard_passing_arm']} {g['best_guard_passing_pct']} "
           f"against a baseline {g['baseline_pct']}")
    status(f"  {h.get('reading')}")
    headline(f"G2 MULTI-HEAD: best guard-passing {g['best_guard_passing_arm']} at "
             f"{g['best_guard_passing_pct']} percent semi-bounded against a one-head baseline of "
             f"{g['baseline_pct']}; bounded {by.get(g['best_guard_passing_arm'], {}).get('bounded_pct')}.")
    findings("g2", bool(RES["contract"]["SATISFIED"]), (
        f"Improvement 1, multi-head ensembles, over {len(cross)} cross-day pairings with "
        f"{len(have)} of three 1 s seeds available.\n\n"
        f"THE POOLS. {RES['pool_rule']} Best guard-passing arm is {g['best_guard_passing_arm']} at "
        f"{g['best_guard_passing_pct']} percent semi-bounded, against a one-head baseline of "
        f"{g['baseline_pct']}. Best overall is {g['best_overall_arm']} at {g['best_overall_pct']} "
        f"and it {'PASSES' if g['best_overall_passes_guard'] else 'FAILS'} the guard.\n\n"
        f"MORE HEADS OR MORE DIVERSITY: {h.get('reading')} The best mixed-stride pool scores "
        f"{h.get('best_mixed_pct')} and the 1 s-only pool of the same size scores "
        f"{h.get('one_second_only_pct')}, a difference of "
        f"{h.get('mixed_minus_singlestride_points')} points.\n\n"
        f"Every comparison against the baseline carries BOTH readings, the difference of medians "
        f"and the median of per-pairing paired deltas, in the results file. A weighted pool is "
        f"reported separately because it introduces a selection the equal-weight arms do not."))
    status(f"{STAGE} DONE in {RES['minutes']:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
