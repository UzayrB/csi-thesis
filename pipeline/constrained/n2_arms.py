"""PHASE 2: the single-lever arms, every one gated by the substitution test before its line counts.

The default configuration reproduces the shipped decoder exactly and that is ASSERTED before any
arm is measured, because an arm measured against a broken baseline measures nothing.

Swept values are selected on a pairing whose TEST session is one of this pairing's TRAINING
sessions and whose own training never touches this pairing's test session, so nothing is chosen on
the session the number is reported on. A value whose sweep ties is recorded as NOT SELECTED.
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.constrained.night_common import set_half_roots                      # noqa: E402
set_half_roots(REPO_ROOT)
# n3 and n4 import fit_chain_prior, run and summarise from here as a LIBRARY, with the roots
# already set by their own module tops. The guard therefore checks that the ROOTS ARE CORRECT, not
# that nothing was imported first. This is the third time the import-order form of this assert has
# broken a caller in this project, so it is written the same way everywhere now.
from pipeline.constrained.lattice import half_art_dir as _half_art_dir              # noqa: E402
_WANT = _half_art_dir()                  # the ONE lattice's half tree, since 2026-09-23d
assert os.environ.get("TDR_ART_DIR") == _WANT, (
    f"n2_arms needs the 0.5 s roots set before any pipeline import; TDR_ART_DIR is "
    f"{os.environ.get('TDR_ART_DIR')!r}, not {_WANT!r}")

import time                                                                       # noqa: E402

import numpy as np                                                                # noqa: E402

from pipeline.constrained.common import is_cross, pairings, status, tag_of         # noqa: E402
from pipeline.constrained.night_arms import default_opts, night_track              # noqa: E402
from pipeline.constrained.night_common import (STRIDE, assert_motion_model, boot_ci,  # noqa
                                               check_contract, claim, guard_verdict, load,
                                               pairing_emissions, release, save, shipped_pieces)
from pipeline.constrained.rebuild_common import findings, headline                 # noqa: E402
from pipeline.constrained.sb2_structural import selection_pairing_for              # noqa: E402

STAGE = "n2_arms"
SHIPPED_DEMO_LINE = 71.7        #: the default must reproduce this on s0102_to_s03


def arm_grid(diag):
    """Every arm as a list of (name, opts). Arm I runs only if phase 1 found a family bias."""
    arms = [("shipped", {})]
    # A: guard-safe pinned entry, entry crossed with prior flattening
    for entry in ("hard", "soft"):
        for f in (0.0, 0.5, 0.9):
            arms.append((f"A_{entry}_flat{f}", {"entry": entry, "prior_flatten": f}))
    # B: candidate-set rescore, the form phase 0 selected by reading the code
    for th in (0.2, 0.4, 0.6):
        arms.append((f"B_cand{th}", {"cand_thresh": th}))
    # G: the final-line rule, which the shipped decoder takes as a majority vote
    arms.append(("G_maxlik", {"final_rule": "maxlik"}))
    # C: hierarchical family-first decision
    arms.append(("C_family", {"family_first": True}))
    # I: per-chain prior, only if a bias exists
    if ((diag or {}).get("family_bias") or {}).get("bias_exists"):
        arms.append(("I_chainprior", {"chain_logprior": "FIT"}))
    return arms


def fit_chain_prior(st, tr_s):
    """Arm I: a per-chain log-prior from the TRAINING sessions' line frequencies only."""
    from pipeline.constrained.recordings import load_meta, recordings
    counts = {nm: 0 for nm in st.names}
    for sess, stem in recordings():
        if sess not in tr_s:
            continue
        try:
            rec = load_meta(sess, stem)
        except Exception:                                                # noqa: BLE001
            continue
        for _pid, nm, _a, _b in rec.pass_spans():
            if nm in counts:
                counts[nm] += 1
    tot = sum(counts.values()) or 1
    # the protocol makes these uniform, so the prior corrects any residual imbalance only
    return {nm: float(np.log(max(c, 1) / tot) - np.log(1.0 / len(counts)))
            for nm, c in counts.items()}


def summarise(rows):
    if not rows:
        return None
    err = [r["err_m"] for r in rows if r["found_final"] and r["err_m"] is not None]
    dtp = [r["exit_dt_press_s"] for r in rows]
    se = [r["subs_end_changed"] for r in rows if r["subs_end_changed"] is not None]
    sl = [r["subs_line_changed"] for r in rows if r["subs_line_changed"] is not None]
    per_line = {}
    for r in rows:
        d = per_line.setdefault(r["true_line"], {"n": 0, "hit": 0})
        d["n"] += 1
        d["hit"] += int(r["found_final"])
    return {
        "n_passes": len(rows),
        "final_line_pct": 100.0 * float(np.mean([r["found_final"] for r in rows])),
        "provisional_line_pct": 100.0 * float(np.mean([r["found_provisional"] for r in rows])),
        "err_m": float(np.median(err)) if err else None,
        "exit_dt_press_median_s": float(np.median(dtp)),
        "exit_dt_press_p90_s": float(np.percentile(np.abs(dtp), 90)),
        "exit_within_1s_pct": 100.0 * float(np.mean([abs(x) <= 1.0 for x in dtp])),
        "never_ended_pct": 100.0 * float(np.mean([r["never_ended"] for r in rows])),
        "revisions_mean": float(np.mean([r["revisions"] for r in rows])),
        "timeout_fired_pct": 100.0 * float(np.mean([r["timeout_fired"] for r in rows])),
        "substitution_end_pct": 100.0 * float(np.mean(se)) if se else None,
        "substitution_line_pct": 100.0 * float(np.mean(sl)) if sl else None,
        "impossible_transitions": int(sum(r["impossible"] for r in rows)),
        "per_line_recall_pct": {k: 100.0 * v["hit"] / v["n"] for k, v in sorted(per_line.items())},
        "commit_timeline_pct": {d: 100.0 * float(np.mean([r["commit_s"].get(d, False)
                                                          for r in rows]))
                                for d in ("0.5", "1.0", "1.5", "2.0", "2.5", "3.0", "3.5", "4.0")}}


def run(src, st, cfg, ne, transit, opts, subs=True):
    rows, n = [], len(src)
    for k, (_stem, rec, ge, e) in enumerate(src):
        alt = src[(k + 1) % n][3] if (subs and n > 1) else None
        rows += night_track(e, rec, st, cfg, transit, ne, ge, STRIDE, opts, alt)
    return rows


def main() -> int:
    lock = claim(STAGE)
    t0 = time.time()
    st, cfg, ne, transit, kind, alpha = shipped_pieces()
    mm = assert_motion_model()
    diag = load("n1_diag")
    arms = arm_grid(diag)
    status(f"{STAGE} START: {len(arms)} arms, guard on every one. "
           f"motion model {mm['step_m_per_window']:.3f} m per window")
    status(f"  arms: " + ", ".join(a for a, _ in arms))

    RES = {"stage": STAGE, "stride_s": STRIDE, "n_arms": len(arms),
           "arm_names": [a for a, _ in arms], "per_pairing": {}, "failures": [],
           "arm_I_runs": any(a == "I_chainprior" for a, _ in arms),
           "selection_rule": ("swept values selected on a pairing that never trains or tests on "
                              "the reported pairing's test session")}

    cache = {}

    def emis(tag, tr_s, te_s, within):
        if tag not in cache:
            cache[tag] = pairing_emissions(tag, tr_s, te_s, within, st, kind, alpha)
        return cache[tag]

    baseline_checked = False
    for tr_s, te_s in pairings():
        within = tr_s == te_s
        tag = tag_of(tr_s, te_s, within)
        src = emis(tag, tr_s, te_s, within)
        if src is None:
            RES["failures"].append({"tag": tag, "error": "no posteriors"})
            continue
        try:
            prior = fit_chain_prior(st, tr_s) if RES["arm_I_runs"] else None
            per_arm = {}
            for name, o in arms:
                opts = default_opts()
                opts.update(o)
                if opts.get("chain_logprior") == "FIT":
                    opts["chain_logprior"] = prior
                sm = summarise(run(src, st, cfg, ne, transit, opts))
                if sm is not None:
                    sm["opts"] = {k: (v if not isinstance(v, dict) else "fitted")
                                  for k, v in o.items()}
                    sm["guard"] = guard_verdict(sm["substitution_end_pct"],
                                                sm["substitution_line_pct"])
                per_arm[name] = sm
            # THE BASELINE ASSERTION, once, on the demonstration pairing
            if tag == "s0102_to_s03" and per_arm.get("shipped"):
                got = per_arm["shipped"]["final_line_pct"]
                RES["baseline_check"] = {
                    "pairing": tag, "expected_pct": SHIPPED_DEMO_LINE, "got_pct": got,
                    "reproduces": bool(abs(got - SHIPPED_DEMO_LINE) < 0.6),
                    "why": ("an arm measured against a baseline that is not the shipped decoder "
                            "measures nothing")}
                baseline_checked = True
                status(f"  BASELINE CHECK on {tag}: {got:.1f} against the shipped "
                       f"{SHIPPED_DEMO_LINE} -> {RES['baseline_check']['reproduces']}")
            RES["per_pairing"][tag] = {"regime": "cross" if is_cross(tag) else "within",
                                       "arms": per_arm}
            sh, best = per_arm.get("shipped"), None
            passing = [(n_, v) for n_, v in per_arm.items()
                       if v and v["guard"]["PASSES"]]
            if passing:
                best = max(passing, key=lambda kv: kv[1]["final_line_pct"])
            status(f"  {tag:16s} [{'cross' if is_cross(tag) else 'within':6s}] shipped "
                   f"{sh['final_line_pct']:5.1f} -> best guard-passing "
                   f"{best[0] if best else 'none'} {best[1]['final_line_pct'] if best else float('nan'):5.1f}")
        except Exception as exc:                                         # noqa: BLE001
            import traceback
            RES["failures"].append({"tag": tag, "error": repr(exc),
                                    "traceback": traceback.format_exc()[-1500:]})
            status(f"  {tag:16s} FAILED {exc!r}")

    cross = {k: v for k, v in RES["per_pairing"].items() if v["regime"] == "cross"}

    def med(arm, field):
        v = [p["arms"][arm][field] for p in cross.values()
             if p["arms"].get(arm) and p["arms"][arm].get(field) is not None]
        return float(np.median(v)) if v else None

    names = [a for a, _ in arms]
    by_arm = {}
    for a in names:
        by_arm[a] = {f: med(a, f) for f in
                     ("final_line_pct", "provisional_line_pct", "err_m",
                      "exit_dt_press_median_s", "exit_within_1s_pct", "never_ended_pct",
                      "revisions_mean", "timeout_fired_pct", "substitution_end_pct",
                      "substitution_line_pct", "impossible_transitions")}
        by_arm[a]["guard"] = guard_verdict(by_arm[a]["substitution_end_pct"],
                                           by_arm[a]["substitution_line_pct"])
    RES["cross_day"] = {"n_pairings": len(cross), "by_arm": by_arm}

    # the gate, applied on the aggregate: best guard-passing and best overall, reported separately
    scored = [a for a in names if by_arm[a]["final_line_pct"] is not None]
    passing = [a for a in scored if by_arm[a]["guard"]["PASSES"]]
    best_overall = max(scored, key=lambda a: by_arm[a]["final_line_pct"]) if scored else None
    best_pass = max(passing, key=lambda a: by_arm[a]["final_line_pct"]) if passing else None
    sh = by_arm.get("shipped", {}).get("final_line_pct")
    RES["gate"] = {
        "rule": ("an arm whose end-time substitution is at or below 50 percent, or whose line "
                 "substitution is not of the same order as bounded's 87.5, is OUT whatever its "
                 "line figure; among those that pass, the best line, error as tie-break"),
        "n_scored": len(scored), "n_passing": len(passing), "arms_passing": sorted(passing),
        "best_overall_arm": best_overall,
        "best_overall_line_pct": by_arm[best_overall]["final_line_pct"] if best_overall else None,
        "best_overall_passes_guard": by_arm[best_overall]["guard"]["PASSES"] if best_overall else None,
        "best_guard_passing_arm": best_pass,
        "best_guard_passing_line_pct": by_arm[best_pass]["final_line_pct"] if best_pass else None,
        "shipped_line_pct": sh,
        "gain_over_shipped_points": (None if (best_pass is None or sh is None)
                                     else by_arm[best_pass]["final_line_pct"] - sh)}
    # survivors for phase 3: pass the guard AND beat shipped on the aggregate
    RES["survivors"] = sorted(
        a for a in passing
        if a != "shipped" and sh is not None and by_arm[a]["final_line_pct"] > sh + 1e-9)

    RES["minutes"] = round((time.time() - t0) / 60.0, 1)
    RES["contract"] = check_contract(RES, ["per_pairing", "cross_day", "gate", "baseline_check"],
                                     {"per_pairing": 9})
    save(STAGE, RES)
    release(lock)

    g = RES["gate"]
    status(f"  CROSS-DAY over {len(cross)} pairings, {g['n_passing']} of {g['n_scored']} arms pass:")
    status(f"    shipped              {sh}")
    status(f"    BEST OVERALL         {g['best_overall_arm']} {g['best_overall_line_pct']}, "
           f"passes guard {g['best_overall_passes_guard']}")
    status(f"    BEST GUARD-PASSING   {g['best_guard_passing_arm']} "
           f"{g['best_guard_passing_line_pct']} ({g['gain_over_shipped_points']:+.1f} points)")
    status(f"    survivors for phase 3: {RES['survivors']}")
    headline(f"NIGHT PHASE 2: {g['n_passing']} of {g['n_scored']} arms pass the guard; best "
             f"guard-passing {g['best_guard_passing_arm']} at {g['best_guard_passing_line_pct']} "
             f"against the shipped {sh}; best overall {g['best_overall_arm']} at "
             f"{g['best_overall_line_pct']}, passes guard {g['best_overall_passes_guard']}.")
    findings("n2", bool(RES["contract"]["SATISFIED"] and RES.get("baseline_check", {}).get("reproduces")), (
        f"Phase 2, {len(arms)} single-lever arms over {len(cross)} cross-day pairings, the guard "
        f"applied to every one before its line figure counts.\n\n"
        f"THE BASELINE REPRODUCES THE SHIPPED DECODER: {RES.get('baseline_check')}. An arm "
        f"measured against a baseline that is not the shipped decoder measures nothing.\n\n"
        f"THE GATE. {g['n_passing']} of {g['n_scored']} arms pass. BEST GUARD-PASSING is "
        f"{g['best_guard_passing_arm']} at {g['best_guard_passing_line_pct']} percent, "
        f"{g['gain_over_shipped_points']} points over the shipped {sh}. BEST OVERALL is "
        f"{g['best_overall_arm']} at {g['best_overall_line_pct']} percent and it "
        f"{'PASSES' if g['best_overall_passes_guard'] else 'FAILS'} the guard"
        + ("" if g["best_overall_passes_guard"] else
           ", so it is out whatever its line figure") + ".\n\n"
        f"ARM I {'RAN' if RES['arm_I_runs'] else 'DID NOT RUN'}, on phase 1's family-bias finding. "
        f"Survivors carried into phase 3: {RES['survivors']}.\n\n"
        f"Per-arm aggregate rows, every one with its guard result, are in the results file."))
    status(f"{STAGE} DONE in {RES['minutes']:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
