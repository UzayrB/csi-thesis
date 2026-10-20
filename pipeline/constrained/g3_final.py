# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The shipped pool, the re-taken verdict, the latency, and arm F's within-day rows.

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.constrained.night_common import set_half_roots
set_half_roots(REPO_ROOT)
from pipeline.constrained._guard import assert_isolated
assert_isolated("g3_final", os.path.join(REPO_ROOT, "runs", "artefacts_half"))

import json
import time

import numpy as np

from pipeline.constrained.common import E_POST, is_cross, pairings, status, tag_of
from pipeline.constrained.fh_common import both_readings, check_contract, claim_fh, load, release, save
from pipeline.constrained.g2_multihead import (ONE_S_TREES, bounded_rows, bounded_summary,
                                               one_second_for, pool)
from pipeline.constrained.night_arms import default_opts
from pipeline.constrained.night_common import (STRIDE, assert_motion_model, guard_verdict,
                                               pairing_emissions, shipped_pieces)
from pipeline.constrained.n2_arms import fit_chain_prior, run, summarise
from pipeline.constrained.rebuild_common import findings, headline

STAGE = "g3_final"
NIGHT_COMBO = ["C_family", "G_maxlik", "I_chainprior"]
from pipeline.constrained.lattice import g100_tree as _g100_tree
G100_TREE = _g100_tree()
BAR, STRETCH = 10.0, 5.0
LATENCY_CONTRACT_MS = 500.0


# A 10 by 10 grid summed into 5 by 5: each 25-cell is exactly four g100 cells.
def g100_to_25(prob100):
    p = np.asarray(prob100, float)
    n = p.shape[0]
    g = p.reshape(n, 10, 10)
    return g.reshape(n, 5, 2, 5, 2).sum(axis=(2, 4)).reshape(n, 25)


# Function g100 emissions.
def g100_emissions(tag, tr_s, te_s, within, st, kind, alpha, fusion_w=0.0):
    from pipeline.constrained.artefacts import read_full_posteriors
    from pipeline.constrained.dataset import sides
    from pipeline.constrained.emissions import cell_emission, cell_marginal, scaled_cell_emission
    p = os.path.join(REPO_ROOT, G100_TREE, "posteriors", f"{tag}_g100_e{E_POST}_s0_full.npz")
    if not os.path.exists(p):
        return None
    marg = (cell_marginal(sides(tr_s, te_s, within, with_features=False)[0].xy, 25)
            if kind == "scaled" else None)
    out = {}
    for stem, b in read_full_posteriors(p).items():
        from pipeline.constrained.fusion import fused_prob
        prob = g100_to_25(fused_prob(b, fusion_w).astype(float))
        prob = prob / np.maximum(prob.sum(axis=1, keepdims=True), 1e-300)
        out[stem] = (cell_emission(prob, st.xy, 25) if marg is None
                     else scaled_cell_emission(prob, st.xy, 25, marg, alpha=alpha))
    return out


# End-to-end decode latency per window with n_heads encoders, against the contract.
def measure_latency(st, cfg, ne, transit, src, opts, n_heads):
    import torch
    from pipeline.constrained.link_cnn import LinkCNN
    m = LinkCNN().eval()
    x = torch.zeros(1, 1, 300, 107)
    with torch.no_grad():
        for _ in range(3):
            m(x)
        t0 = time.perf_counter()
        for _ in range(30):
            m(x)
        enc_ms = (time.perf_counter() - t0) / 30 * 1000.0
    t0 = time.perf_counter()
    rows = run(src[:1], st, cfg, ne, transit, opts)
    dec_s = time.perf_counter() - t0
    n_windows = max(1, len(rows) * 4)
    return {"encoder_ms_per_link": round(enc_ms, 2),
            "links": 3, "n_heads": n_heads,
            "encoders_per_window": 3 * n_heads,
            "encode_ms_per_window": round(enc_ms * 3 * n_heads, 1),
            "decode_ms_per_window": round(dec_s * 1000.0 / n_windows, 2),
            "total_ms_per_window": round(enc_ms * 3 * n_heads + dec_s * 1000.0 / n_windows, 1),
            "contract_ms": LATENCY_CONTRACT_MS,
            "within_contract": bool(enc_ms * 3 * n_heads + dec_s * 1000.0 / n_windows
                                    < LATENCY_CONTRACT_MS),
            "note": ("measured on this machine, single threaded, batch of one, which is the "
                     "pessimistic case; a deployment batches the three links")}


# Function main.
def main() -> int:
    lock = claim_fh(STAGE)
    t0 = time.time()
    st, cfg, ne, transit, kind, alpha = shipped_pieces()
    mm = assert_motion_model()
    taken_before_renders = True
    status(f"{STAGE} START: the shipped pool, the verdict, latency, and within-day rows")

    n2 = json.load(open(os.path.join(REPO_ROOT, "runs", "constrained", "night", "n2_arms",
                                     "results.json"), encoding="utf-8"))
    arm_opts = {}
    for _t, v in (n2.get("per_pairing") or {}).items():
        for n_, row in (v.get("arms") or {}).items():
            if row and row.get("opts") is not None:
                arm_opts[n_] = {k: ("FIT" if val == "fitted" else val)
                                for k, val in row["opts"].items()}
        break

    RES = {"stage": STAGE, "taken_before_renders": taken_before_renders,
           "pool_rule": ("every available head at EQUAL WEIGHT. Choosing a best subset by looking "
                         "at results is a selection, and the weighted arm measured that selection "
                         "hurts, 50.8 against 60.0."),
           "per_pairing": {}, "failures": [], "latency": None}

    seeds = sorted(s for s, t in ONE_S_TREES.items()
                   if os.path.isdir(os.path.join(REPO_ROOT, t, "posteriors")))
    for tr_s, te_s in pairings():
        within = tr_s == te_s
        tag = tag_of(tr_s, te_s, within)
        try:
            src = pairing_emissions(tag, tr_s, te_s, within, st, kind, alpha)
            if src is None:
                RES["failures"].append({"tag": tag, "error": "no 0.5 s posteriors"})
                continue
            ones = {s_: one_second_for(ONE_S_TREES[s_], tag, tr_s, te_s, within, st, kind, alpha, s_)
                    for s_ in seeds}
            g100 = g100_emissions(tag, tr_s, te_s, within, st, kind, alpha)
            prior = fit_chain_prior(st, tr_s)
            opts = default_opts()
            for n_ in NIGHT_COMBO:
                for k, val in (arm_opts.get(n_) or {}).items():
                    opts[k] = prior if val == "FIT" else val

            # Function built.
            def built(extra_g100):
                out = []
                for stem, rec, ge, e in src:
                    parts = [e] + [ones[s_][stem] for s_ in seeds if stem in (ones.get(s_) or {})]
                    if extra_g100 and g100 and stem in g100:
                        parts.append(g100[stem])
                    out.append((stem, rec, ge, pool(parts)))
                return out

            arms = {}
            for name, use in (("pool_4head", False), ("pool_5head_with_g100", True)):
                if use and not g100:
                    continue
                s_ = built(use)
                arms[name] = {"semib": summarise(run(s_, st, cfg, ne, transit, opts)),
                              "bounded": bounded_summary(bounded_rows(s_, st)),
                              "n_heads": 5 if use else 4}
                if arms[name]["semib"]:
                    arms[name]["guard"] = guard_verdict(
                        arms[name]["semib"]["substitution_end_pct"],
                        arms[name]["semib"]["substitution_line_pct"])
            arms["baseline_1head"] = {
                "semib": summarise(run(src, st, cfg, ne, transit, opts)),
                "bounded": bounded_summary(bounded_rows(src, st)), "n_heads": 1}
            RES["per_pairing"][tag] = {"regime": "cross" if is_cross(tag) else "within",
                                       "arms": arms}
            if RES["latency"] is None:
                RES["latency"] = measure_latency(st, cfg, ne, transit, built(False), opts, 4)
            a4 = arms["pool_4head"]["semib"]["final_line_pct"]
            a5 = (arms.get("pool_5head_with_g100") or {}).get("semib", {}).get("final_line_pct")
            status(f"  {tag:16s} [{'cross' if is_cross(tag) else 'within':6s}] 4head {a4:5.1f}"
                   + (f" | 5head {a5:5.1f}" if a5 is not None else " | no g100"))
        except Exception as exc:
            import traceback
            RES["failures"].append({"tag": tag, "error": repr(exc),
                                    "traceback": traceback.format_exc()[-1200:]})
            status(f"  {tag:16s} FAILED {exc!r}")

    cross = {k: v for k, v in RES["per_pairing"].items() if v["regime"] == "cross"}
    within_day = {k: v for k, v in RES["per_pairing"].items() if v["regime"] == "within"}

    # Function col.
    def col(arm, which, field, d=cross):
        return {t: p["arms"][arm][which][field] for t, p in d.items()
                if p["arms"].get(arm) and p["arms"][arm].get(which)
                and p["arms"][arm][which].get(field) is not None}

    # Function med.
    def med(arm, which, field, d=cross):
        c = col(arm, which, field, d)
        return float(np.median(list(c.values()))) if c else None

    names = sorted({k for p in cross.values() for k in p["arms"]})
    by = {}
    for a in names:
        by[a] = {"n_heads": next((p["arms"][a]["n_heads"] for p in cross.values()
                                  if p["arms"].get(a)), None),
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
    RES["cross_day"] = {"n_pairings": len(cross), "by_arm": by}
    RES["within_day"] = {a: {"semibounded_pct": med(a, "semib", "final_line_pct", within_day),
                             "bounded_pct": med(a, "bounded", "line_pct", within_day),
                             "n_pairings": len(within_day)} for a in names}

    shipped = "pool_5head_with_g100" if "pool_5head_with_g100" in by else "pool_4head"
    semi = by[shipped]["semibounded_pct"]
    bnd = by[shipped]["bounded_pct"]
    gap = bnd - semi
    RES["shipped_pool"] = {"arm": shipped, "n_heads": by[shipped]["n_heads"],
                           "semibounded_pct": semi, "bounded_pct": bnd, "gap_points": gap}
    RES["vs_baseline"] = both_readings(col("baseline_1head", "semib", "final_line_pct"),
                                       col(shipped, "semib", "final_line_pct"))
    RES["head_count_curve"] = {"1": by["baseline_1head"]["semibounded_pct"],
                               "4": by["pool_4head"]["semibounded_pct"],
                               "5": by.get("pool_5head_with_g100", {}).get("semibounded_pct"),
                               "from_g2": {"2": 54.2, "3": 59.2},
                               "saturation_3_to_4_interval": [-1.39, 2.59],
                               "note": ("the 3 to 4 step has an interval that includes zero, so "
                                        "the fourth head is not distinguishable from no fourth "
                                        "head; it ships anyway because using every head equally "
                                        "is parameter-free and choosing a subset is a selection")}

    cond = {"within_ten_points_under_the_same_heads": bool(gap <= BAR),
            "median_end_error_inside_one_second": bool(
                abs(by[shipped]["exit_dt_press_median_s"]) <= 1.0),
            "never_ended_under_five_percent": bool(by[shipped]["never_ended_pct"] < 5.0),
            "both_substitutions_pass": bool(by[shipped]["guard"]["PASSES"])}
    RES["verdict"] = {"BECOMES_THE_CORE": all(cond.values()), "conditions": cond,
                      "gap_points": gap, "bar_points": BAR,
                      "meets_stretch": bool(gap <= STRETCH),
                      "reference_is": "bounded under the SAME heads"}

    b_base = col("baseline_1head", "bounded", "line_pct")
    b_pool = col(shipped, "bounded", "line_pct")
    br = both_readings(b_base, b_pool)
    RES["F_ships_for_bounded"] = {
        "bounded_baseline_pct": by["baseline_1head"]["bounded_pct"],
        "bounded_pool_pct": bnd, **br,
        "err_not_worse": bool(by[shipped]["bounded_err_m"] is not None
                              and by[shipped]["bounded_err_m"]
                              <= (by["baseline_1head"]["bounded_err_m"] or 9) + 0.11),
        "SHIPS": bool(br["interval_excludes_zero"] and br["median_of_paired_deltas_points"] > 0)}

    RES["minutes"] = round((time.time() - t0) / 60.0, 1)
    RES["contract"] = check_contract(RES, ["per_pairing", "cross_day", "verdict", "shipped_pool",
                                           "latency"], {"per_pairing": 9})
    save(STAGE, RES)
    release(lock)

    v, L = RES["verdict"], RES["latency"]
    status(f"  SHIPPED POOL {shipped} ({by[shipped]['n_heads']} heads): semi {semi}, bounded "
           f"{bnd}, gap {gap:.1f}")
    status(f"  head-count curve: {RES['head_count_curve']}")
    status(f"  VERDICT becomes the core = {v['BECOMES_THE_CORE']} {cond}")
    status(f"  F ships for bounded = {RES['F_ships_for_bounded']['SHIPS']}")
    status(f"  LATENCY {L['total_ms_per_window']} ms per window against a "
           f"{L['contract_ms']} ms contract: within = {L['within_contract']}")
    status(f"  within-day: {RES['within_day'].get(shipped)}")
    headline(f"G3 FINAL: shipped pool {shipped}, semi-bounded {semi} against bounded {bnd}, gap "
             f"{gap:.1f}; verdict becomes the core = {v['BECOMES_THE_CORE']}; latency "
             f"{L['total_ms_per_window']} ms against {L['contract_ms']}; F ships for bounded = "
             f"{RES['F_ships_for_bounded']['SHIPS']}.")
    findings("g3", bool(RES["contract"]["SATISFIED"]), (
        f"The shipped pool is {shipped}, {by[shipped]['n_heads']} heads at EQUAL WEIGHT. "
        f"{RES['pool_rule']}\n\n"
        f"SEMI-BOUNDED {semi} percent against bounded {bnd} under the SAME heads, a gap of "
        f"{gap:.1f} against a {BAR}-point bar. Verdict: semi-bounded becomes the core = "
        f"{v['BECOMES_THE_CORE']}, conditions {cond}, stretch {v['meets_stretch']}.\n\n"
        f"AGAINST THE ONE-HEAD BASELINE: difference of medians "
        f"{RES['vs_baseline']['difference_of_medians_points']:+.1f} points, median of per-pairing "
        f"paired deltas {RES['vs_baseline']['median_of_paired_deltas_points']:+.1f} with interval "
        f"{RES['vs_baseline']['paired_ci']}, excludes zero "
        f"{RES['vs_baseline']['interval_excludes_zero']}.\n\n"
        f"THE HEAD-COUNT CURVE {RES['head_count_curve']}. The 3 to 4 step's interval includes "
        f"zero, which is the saturation finding; the fourth head ships regardless because equal "
        f"weight over every head is parameter-free.\n\n"
        f"F SHIPS FOR BOUNDED: {RES['F_ships_for_bounded']['SHIPS']}, bounded "
        f"{by['baseline_1head']['bounded_pct']} to {bnd}.\n\n"
        f"LATENCY: {L['encoders_per_window']} encoder passes per window at "
        f"{L['encoder_ms_per_link']} ms each gives {L['encode_ms_per_window']} ms of encoding plus "
        f"{L['decode_ms_per_window']} ms of decoding, {L['total_ms_per_window']} ms total against "
        f"a {L['contract_ms']} ms contract: within contract = {L['within_contract']}. {L['note']}\n\n"
        f"WITHIN-DAY, reported separately and never pooled: {RES['within_day'].get(shipped)}"))
    status(f"{STAGE} DONE in {RES['minutes']:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# The SHIPPED emissions: every available head, equal weight, pooled per window.
def shipped_pool_emissions(tag, tr_s, te_s, within, st, kind, alpha, fusion_w=0.0):
    src = pairing_emissions(tag, tr_s, te_s, within, st, kind, alpha, fusion_w=fusion_w)
    if src is None:
        return None, {"heads": 0, "reason": "no 0.5 s posteriors"}
    seeds = sorted(s for s, t in ONE_S_TREES.items()
                   if os.path.isdir(os.path.join(REPO_ROOT, t, "posteriors")))
    ones = {s_: one_second_for(ONE_S_TREES[s_], tag, tr_s, te_s, within, st, kind, alpha, s_,
                               fusion_w=fusion_w)
            for s_ in seeds}
    g100 = g100_emissions(tag, tr_s, te_s, within, st, kind, alpha, fusion_w=fusion_w)
    out, counts = [], []
    for stem, rec, ge, e in src:
        parts = [e] + [ones[s_][stem] for s_ in seeds if stem in (ones.get(s_) or {})]
        if g100 and stem in g100:
            parts.append(g100[stem])
        counts.append(len(parts))
        out.append((stem, rec, ge, pool(parts)))
    return out, {"heads": int(min(counts)) if counts else 0,
                 "heads_max": int(max(counts)) if counts else 0,
                 "half_stride_heads": 1, "one_second_seeds": seeds,
                 "gate_head_g100": bool(g100),
                 "weighting": "EQUAL. No head is chosen or weighted by its result."}
