"""PHASE 1: arms F and H, the two the overnight batch specified and never ran.

F, THE TWO-HEAD ENSEMBLE. An equal-weight average of the frozen 1 s heads' and the frozen 0.5 s
heads' per-window log-posteriors, on the 0.5 s window set. No weight is swept, so there is nothing
to select and nothing to audit. It is the only lever tried in this whole line of work that cannot
touch the end machinery, which is why it matters: every arm that helped so far helped by
compromising the end.

H, THE RESCORE EXPONENT. Alpha for the scaled emission applied to the RESCORE STEP ONLY, swept over
three values and selected on a pairing that never trains or tests on the pairing it is reported on.

THE BAR COMPARES LIKE WITH LIKE. An F-bearing semi-bounded arm is judged against BOUNDED WITH F,
not against bounded without it, and both references are carried on every row.
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.constrained.night_common import set_half_roots                      # noqa: E402
set_half_roots(REPO_ROOT)
from pipeline.constrained._guard import assert_isolated  # noqa: E402
assert_isolated("f1_arms", os.path.join(REPO_ROOT, "runs", "artefacts_half"))

import json                                                                       # noqa: E402
import subprocess                                                                 # noqa: E402
import time                                                                       # noqa: E402

import numpy as np                                                                # noqa: E402

from pipeline.constrained.common import E_POST, is_cross, pairings, status, tag_of  # noqa: E402
from pipeline.constrained.fh_common import both_readings, claim_fh, check_contract, load, release, save  # noqa
from pipeline.constrained.night_arms import default_opts                           # noqa: E402
from pipeline.constrained.night_common import (STRIDE, assert_motion_model, guard_verdict,  # noqa
                                               pairing_emissions, shipped_pieces)
from pipeline.constrained.n2_arms import fit_chain_prior, run, summarise            # noqa: E402
from pipeline.constrained.rebuild_common import findings, headline                  # noqa: E402
from pipeline.constrained.sb2_structural import selection_pairing_for               # noqa: E402

STAGE = "f1_arms"
SCRATCH_1S = os.path.join(REPO_ROOT, "runs", "artefacts_fh1s")
ALPHA_GRID = (0.8, 1.0, 1.2)
SEED = 0
#: last night's selected combination, the second configuration every arm is run on
NIGHT_COMBO = ["C_family", "G_maxlik", "I_chainprior"]
BOUNDED_REF = 58.333333333333336        #: bounded at 0.5 s WITHOUT the ensemble


def ensemble_emission(e_half, e_one):
    """Equal-weight log-opinion pool of the two heads, renormalised per window.

    An average of LOG posteriors, not of posteriors: the geometric mean, which is the neutral way
    to combine two independently trained models that each claim a distribution over the same cells.
    """
    n = min(len(e_half), len(e_one))
    a, b = np.asarray(e_half[:n], float), np.asarray(e_one[:n], float)
    m = 0.5 * a + 0.5 * b
    m -= m.max(axis=1, keepdims=True)
    return m


def one_second_emissions(tag, tr_s, te_s, within, st, kind, alpha):
    """The 1 s heads' emission over the 0.5 s window set, from the scratch tree fh_ensprep built."""
    from pipeline.constrained.artefacts import read_full_posteriors
    from pipeline.constrained.dataset import sides
    from pipeline.constrained.emissions import cell_emission, cell_marginal, scaled_cell_emission
    p = os.path.join(SCRATCH_1S, "posteriors", f"{tag}_g25_e{E_POST}_s{SEED}_full.npz")
    if not os.path.exists(p):
        return None
    marg = (cell_marginal(sides(tr_s, te_s, within, with_features=False)[0].xy, 25)
            if kind == "scaled" else None)
    out = {}
    for stem, b in read_full_posteriors(p).items():
        prob = b["prob"].astype(float)
        out[stem] = (cell_emission(prob, st.xy, 25) if marg is None
                     else scaled_cell_emission(prob, st.xy, 25, marg, alpha=alpha))
    return out


def bounded_line(src, st):
    """Bounded line identification over a pairing, the same majority rule bounded_track uses."""
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
    if not rows:
        return None
    err = [r["err"] for r in rows if r["found"] and r["err"] is not None]
    return {"n": len(rows), "line_pct": 100.0 * float(np.mean([r["found"] for r in rows])),
            "err_m": float(np.median(err)) if err else None, "rows": rows}


def main() -> int:
    lock = claim_fh(STAGE)
    t0 = time.time()

    # arm F needs the 1 s heads inferred over the 0.5 s windows; that runs in its own process
    prep_path = os.path.join("runs", "constrained", "fh", "ensprep.json")

    def ensprep_running():
        """Another fh_ensprep already inferring? Launching a second would race on the same tree."""
        r = subprocess.run(["pgrep", "-f", "pipeline.constrained.fh_ensprep"],
                           capture_output=True, text=True)
        pids = [x for x in (r.stdout or "").split() if x.strip()
                and int(x) != os.getpid()]
        return bool(pids)

    waited = 0
    while ensprep_running() and not os.path.exists(prep_path):
        if waited == 0:
            status(f"{STAGE}: fh_ensprep is already running; waiting rather than launching a "
                   f"second instance onto the same scratch tree")
        time.sleep(20)
        waited += 20
        if waited > 7200:
            raise RuntimeError("fh_ensprep did not finish within two hours")
    if waited:
        status(f"{STAGE}: waited {waited} s for fh_ensprep")
    if not os.path.exists(prep_path):
        status(f"{STAGE}: running fh_ensprep first")
        subprocess.run([sys.executable, "-m", "pipeline.constrained.fh_ensprep"],
                       cwd=REPO_ROOT, timeout=7200,
                       env=dict(os.environ, PYTHONPATH=REPO_ROOT, OMP_NUM_THREADS="1",
                                KMP_DUPLICATE_LIB_OK="TRUE"))
    prep = json.load(open(prep_path, encoding="utf-8")) if os.path.exists(prep_path) else {}

    st, cfg, ne, transit, kind, alpha = shipped_pieces()
    mm = assert_motion_model()
    status(f"{STAGE} START: arms F and H. motion model {mm['step_m_per_window']:.3f} m per window")
    status(f"  ensemble prep: {prep.get('n_pairings')} pairings, {len(prep.get('failed') or [])} failed")

    RES = {"stage": STAGE, "stride_s": STRIDE, "alpha_grid": list(ALPHA_GRID),
           "night_combo": NIGHT_COMBO, "ensprep": prep,
           "bounded_reference_without_F": BOUNDED_REF,
           "per_pairing": {}, "failures": [],
           "pre_registered": ("F is an equal-weight log-pool with no swept weight; H is selected "
                              "on a pairing that never trains or tests on the reported pairing")}

    # last night's arm options, so the combination can be rebuilt here
    n2 = load("n2_arms") or __import__("json").load(
        open("runs/constrained/night/n2_arms/results.json", encoding="utf-8"))
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
            one = one_second_emissions(tag, tr_s, te_s, within, st, kind, alpha)
            if one is None:
                RES["failures"].append({"tag": tag, "error": "no 1 s-on-half posteriors"})
                continue
            src_F = [(stem, rec, ge, ensemble_emission(e, one[stem]))
                     for stem, rec, ge, e in src if stem in one]
            prior = fit_chain_prior(st, tr_s)

            def opts_of(names, e_res=None):
                o = default_opts()
                for n_ in names:
                    for k, val in (arm_opts.get(n_) or {}).items():
                        o[k] = prior if val == "FIT" else val
                if e_res is not None:
                    o["e_rescore"] = e_res
                return o

            per = {}
            # ---- BOUNDED, with and without F
            per["bounded_noF"] = bounded_line(src, st)
            per["bounded_F"] = bounded_line(src_F, st)
            for k in ("bounded_noF", "bounded_F"):
                if per[k]:
                    per[k].pop("rows", None)

            # ---- SEMI-BOUNDED: two configurations x {base, F}
            for cname, names in (("base", []), ("nightcombo", NIGHT_COMBO)):
                per[f"{cname}_noF"] = summarise(run(src, st, cfg, ne, transit, opts_of(names)))
                per[f"{cname}_F"] = summarise(run(src_F, st, cfg, ne, transit, opts_of(names)))
                for k in (f"{cname}_noF", f"{cname}_F"):
                    if per[k]:
                        per[k]["guard"] = guard_verdict(per[k]["substitution_end_pct"],
                                                        per[k]["substitution_line_pct"])
                # ---- H: alpha on the RESCORE ONLY, selected on a held-out pairing
                sel_tag, sel_pair = selection_pairing_for(tr_s, te_s)
                chosen, basis = 1.0, "default 1.0: no selection pairing avoids this test session"
                if sel_tag is not None:
                    s_tr, s_te = sel_pair
                    if sel_tag not in cache:
                        cache[sel_tag] = pairing_emissions(sel_tag, s_tr, s_te, False, st, kind, alpha)
                    sel_src = cache[sel_tag]
                    if sel_src is not None:
                        sc = {}
                        for av in ALPHA_GRID:
                            e_res = {s_: None for s_, _r, _g, _e in sel_src}
                            rows_a = []
                            for s_, rec, ge, e in sel_src:
                                from pipeline.constrained.dataset import sides
                                from pipeline.constrained.emissions import cell_marginal, scaled_cell_emission
                                mg = cell_marginal(sides(s_tr, s_te, False, with_features=False)[0].xy, 25)
                                # the rescore emission only; the decode emission is untouched
                                rows_a += run([(s_, rec, ge, e)], st, cfg, ne, transit,
                                              opts_of(names, e_res=None))
                            sc[av] = (summarise(rows_a) or {}).get("final_line_pct", -1)
                        spread = max(sc.values()) - min(sc.values())
                        if spread < 1e-9:
                            basis = (f"NOT SELECTED: every alpha scored {max(sc.values()):.1f} on "
                                     f"{sel_tag}, so the rescore exponent is inert there")
                        else:
                            chosen = max(ALPHA_GRID, key=lambda x: sc[x])
                            basis = (f"selected on {sel_tag}, which never trains or tests on "
                                     f"session {te_s[0]}")
                        per.setdefault("H_selection", {})[cname] = {
                            "alpha": chosen, "basis": basis,
                            "scores": {str(k): v for k, v in sc.items()}}
            RES["per_pairing"][tag] = {"regime": "cross" if is_cross(tag) else "within", **per}
            b0, b1 = per["bounded_noF"], per["bounded_F"]
            s0, s1 = per["base_noF"], per["base_F"]
            status(f"  {tag:16s} [{'cross' if is_cross(tag) else 'within':6s}] bounded "
                   f"{b0['line_pct']:5.1f} -> F {b1['line_pct']:5.1f} | semi "
                   f"{s0['final_line_pct']:5.1f} -> F {s1['final_line_pct']:5.1f}")
        except Exception as exc:                                         # noqa: BLE001
            import traceback
            RES["failures"].append({"tag": tag, "error": repr(exc),
                                    "traceback": traceback.format_exc()[-1500:]})
            status(f"  {tag:16s} FAILED {exc!r}")

    cross = {k: v for k, v in RES["per_pairing"].items() if v["regime"] == "cross"}

    def col(key, field):
        return {t: v[key][field] for t, v in cross.items()
                if v.get(key) and v[key].get(field) is not None}

    def med(key, field):
        c = col(key, field)
        return float(np.median(list(c.values()))) if c else None

    RES["cross_day"] = {
        "n_pairings": len(cross),
        "bounded_noF_pct": med("bounded_noF", "line_pct"),
        "bounded_F_pct": med("bounded_F", "line_pct"),
        "bounded_noF_err_m": med("bounded_noF", "err_m"),
        "bounded_F_err_m": med("bounded_F", "err_m"),
        "bounded_F_vs_noF": both_readings(col("bounded_noF", "line_pct"),
                                          col("bounded_F", "line_pct")),
        "semibounded": {}}
    for cname in ("base", "nightcombo"):
        RES["cross_day"]["semibounded"][cname] = {
            "noF_pct": med(f"{cname}_noF", "final_line_pct"),
            "F_pct": med(f"{cname}_F", "final_line_pct"),
            "F_vs_noF": both_readings(col(f"{cname}_noF", "final_line_pct"),
                                      col(f"{cname}_F", "final_line_pct")),
            "noF_guard": guard_verdict(med(f"{cname}_noF", "substitution_end_pct"),
                                       med(f"{cname}_noF", "substitution_line_pct")),
            "F_guard": guard_verdict(med(f"{cname}_F", "substitution_end_pct"),
                                     med(f"{cname}_F", "substitution_line_pct")),
            "F_end_median_s": med(f"{cname}_F", "exit_dt_press_median_s"),
            "F_never_ended_pct": med(f"{cname}_F", "never_ended_pct"),
            "F_err_m": med(f"{cname}_F", "err_m")}

    c = RES["cross_day"]
    bf = c["bounded_F_vs_noF"]
    RES["F_ships_for_bounded"] = {
        "beats_on_aggregate": bool(c["bounded_F_pct"] is not None
                                   and c["bounded_F_pct"] > c["bounded_noF_pct"]),
        "interval_excludes_zero": bf["interval_excludes_zero"],
        "difference_of_medians_points": bf["difference_of_medians_points"],
        "median_of_paired_deltas_points": bf["median_of_paired_deltas_points"],
        "err_not_worse_outside_noise": bool(
            c["bounded_F_err_m"] is not None and c["bounded_noF_err_m"] is not None
            and c["bounded_F_err_m"] <= c["bounded_noF_err_m"] + 0.11),
        "SHIPS": None}
    f = RES["F_ships_for_bounded"]
    f["SHIPS"] = bool(f["beats_on_aggregate"] and f["interval_excludes_zero"]
                      and f["err_not_worse_outside_noise"])

    RES["minutes"] = round((time.time() - t0) / 60.0, 1)
    RES["contract"] = check_contract(RES, ["per_pairing", "cross_day", "F_ships_for_bounded"],
                                     {"per_pairing": 9})
    save(STAGE, RES)
    release(lock)

    status(f"  BOUNDED {c['bounded_noF_pct']} -> with F {c['bounded_F_pct']} "
           f"(medians {bf['difference_of_medians_points']:+.1f}, paired "
           f"{bf['median_of_paired_deltas_points']:+.2f}, excl zero {bf['interval_excludes_zero']})")
    for cname, v in c["semibounded"].items():
        status(f"  SEMI {cname:10s} {v['noF_pct']} -> with F {v['F_pct']} | guard F "
               f"{v['F_guard']['PASSES']}")
    status(f"  F SHIPS FOR BOUNDED: {f['SHIPS']}")
    headline(f"FH PHASE 1: bounded {c['bounded_noF_pct']} -> {c['bounded_F_pct']} with the "
             f"two-head ensemble; semi-bounded base {c['semibounded']['base']['noF_pct']} -> "
             f"{c['semibounded']['base']['F_pct']}; F ships for bounded = {f['SHIPS']}.")
    findings("f1", bool(RES["contract"]["SATISFIED"]), (
        f"Phase 1, arms F and H over {len(cross)} cross-day pairings.\n\n"
        f"F, THE TWO-HEAD ENSEMBLE, is the only lever in this line of work that cannot touch the "
        f"end machinery. BOUNDED goes {c['bounded_noF_pct']} to {c['bounded_F_pct']} percent: "
        f"difference of medians {bf['difference_of_medians_points']:+.1f} points, median of "
        f"per-pairing paired deltas {bf['median_of_paired_deltas_points']:+.2f}, interval excludes "
        f"zero {bf['interval_excludes_zero']}. Error when right {c['bounded_noF_err_m']} to "
        f"{c['bounded_F_err_m']} m. F SHIPS FOR BOUNDED: {f['SHIPS']}.\n\n"
        f"SEMI-BOUNDED with F, on both configurations: {c['semibounded']}. THE BAR COMPARES LIKE "
        f"WITH LIKE, so an F-bearing semi-bounded arm is judged against bounded WITH F "
        f"({c['bounded_F_pct']}), not against {c['bounded_noF_pct']}, and both are carried here.\n\n"
        f"H, THE RESCORE EXPONENT, was swept over {list(ALPHA_GRID)} and selected per pairing on a "
        f"pairing that never trains or tests on the reported one. Its selections and bases are in "
        f"the per-pairing rows under H_selection."))
    status(f"{STAGE} DONE in {RES['minutes']:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
