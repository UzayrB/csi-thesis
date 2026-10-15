"""A3, as a STANDALONE start-reading test. The bar was fixed before this was written.

THE BAR, from the amended preregistration: the LOWER confidence bound must be at least twice the
12.5 percent chance, so 25 percent, reported separately for the four edge midpoints and the four
corners, with substitution per group under the generalised rule. If only one group clears it, A2 is
fed only by that group's regions.

THE REFERENCE IT MUST BEAT: the position head alone reads the start region at 18.5 percent, from
D2.

WHAT IT SEES. Windows whose END falls between 2.0 s before the first press and 1.0 s after it.
Pre-press windows are allowed because they had already finished recording. Windows ending just
after the press are allowed because this feeds the COMMITTED line, which is decided at the end and
is not a live display; the causal rule constrains what is DRAWN, not what is decided afterwards.

Nothing is re-inferred: the position head's estimate and the three per-link estimates already exist
in the posterior files.
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.constrained.night_common import set_half_roots                      # noqa: E402
set_half_roots(REPO_ROOT)
from pipeline.constrained._guard import assert_isolated                           # noqa: E402
assert_isolated("q3_startclf", os.path.join(REPO_ROOT, "runs", "artefacts_half"))

import json                                                                       # noqa: E402
import time                                                                       # noqa: E402

import numpy as np                                                                # noqa: E402

from pipeline.constrained.common import E_POST, pairings, status, tag_of           # noqa: E402
from pipeline.constrained.fh_common import check_contract, claim_fh, release, save  # noqa: E402
from pipeline.constrained.night_common import boot_ci, shipped_pieces              # noqa: E402
from pipeline.constrained.p1_runup import first_presses                            # noqa: E402
from pipeline.constrained.q1_diag import REGIONS, region_of                        # noqa: E402
from pipeline.constrained.rebuild_common import WINDOW_S, findings, headline        # noqa: E402

STAGE = "q3_startclf"
PREREG = os.path.join(REPO_ROOT, "runs", "PREREGISTRATION_part2_arms_2026-09-20.json")
BEFORE_S, AFTER_S = 2.0, 1.0
EDGE = ("S_mid", "N_mid", "W_mid", "E_mid")
CORNER = ("SW", "NE", "NW", "SE")
CHANCE = 100.0 / len(REGIONS)
SEED = 0


def features(blk, t, press):
    """The position head and the three per-link heads over the windows straddling the press."""
    end = np.asarray(t, float) + WINDOW_S
    sel = np.flatnonzero((end >= press - BEFORE_S - 1e-9) & (end <= press + AFTER_S + 1e-9))
    xh = np.asarray(blk.get("xy_hat"))
    xl = np.asarray(blk.get("xy_hat_link"))
    sel = sel[sel < len(xh)]
    if len(sel) < 2:
        return None
    v = [np.nanmean(xh[sel], axis=0), np.nanstd(xh[sel], axis=0), xh[sel[0]], xh[sel[-1]]]
    for li in range(xl.shape[0]):
        v += [np.nanmean(xl[li][sel], axis=0), xl[li][sel[0]], xl[li][sel[-1]]]
    f = np.concatenate([np.asarray(x, float).ravel() for x in v])
    return np.where(np.isfinite(f), f, 0.0)


def collect(sessions, st):
    from pipeline.constrained.artefacts import posterior_path, read_full_posteriors
    from pipeline.constrained.recordings import load_meta, recordings
    xy = np.asarray(st.xy)
    starts = {nm: xy[st.slice_of[nm][0]] for nm in st.names}
    X, y, keys, who = [], [], [], []
    for sess, stem in recordings():
        if sess not in sessions:
            continue
        try:
            rec = load_meta(sess, stem)
        except Exception:                                                # noqa: BLE001
            continue
        from pipeline.constrained.t2_embed import tag_for_session
        tag = tag_for_session(sess)              # ONE rule, shared with u1_adapt (and DC2's map)
        if tag is None:
            continue
        try:
            blocks = read_full_posteriors(posterior_path(tag, 25, E_POST, 0))
        except Exception:                                                # noqa: BLE001
            continue
        blk = blocks.get(stem)
        if blk is None:
            continue
        t = np.asarray(rec.t0, float)
        fp = first_presses(sess, stem)
        for pid, nm, _a, _b in rec.pass_spans():
            press = fp.get(int(pid))
            if press is None or nm not in starts:
                continue
            f = features(blk, t, press)
            if f is None:
                continue
            X.append(f)
            y.append(region_of(starts[nm]))
            keys.append(f"{sess}|{stem}|{int(pid)}")
            who.append(stem)
    return (np.vstack(X) if X else np.zeros((0, 1))), np.asarray(y), keys, who


def main() -> int:
    lock = claim_fh(STAGE)
    t0 = time.time()
    st, cfg, ne, transit, kind, alpha = shipped_pieces()
    prereg = json.load(open(PREREG, encoding="utf-8"))
    bar = prereg["A3_start_region_classifier"]["THE_BAR_fixed_before_training"]
    status(f"{STAGE} START: the bar is a lower bound of {bar['bar_pct']} percent, fixed before "
           f"training, chance {CHANCE:.1f}")

    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    from sklearn.preprocessing import StandardScaler

    RES = {"stage": STAGE, "bar": bar, "chance_pct": CHANCE,
           "windows": f"END between {BEFORE_S} s before the first press and {AFTER_S} s after it",
           "reference_position_head_pct": 18.5, "per_fold": {}, "failures": []}

    folds = [(("01", "02"), ("03",)), (("01", "03"), ("02",)), (("02", "03"), ("01",))]
    ok_all, grp = [], {"edge": [], "corner": []}
    sub_all, sub_ceil = {"edge": [], "corner": []}, {"edge": [], "corner": []}
    for tr_s, te_s in folds:
        try:
            Xtr, ytr, _k, _w = collect(tr_s, st)
            Xte, yte, kte, wte = collect(te_s, st)
            if not len(Xtr) or not len(Xte):
                continue
            sc = StandardScaler().fit(Xtr)
            clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
            clf.fit(sc.transform(Xtr), ytr)
            pred = clf.predict(sc.transform(Xte))
            ok = (pred == yte)
            ok_all += list(ok)
            for i, r in enumerate(yte):
                g = "edge" if r in EDGE else "corner"
                grp[g].append(bool(ok[i]))
            # SUBSTITUTION per group: another participant's features over the same pass slot
            order = np.argsort(np.asarray(wte))
            shifted = np.roll(order, 1)
            pred2 = clf.predict(sc.transform(Xte[shifted]))
            for i in range(len(yte)):
                g = "edge" if yte[i] in EDGE else "corner"
                sub_all[g].append(bool(pred2[i] != pred[i]))
                sub_ceil[g].append(bool(yte[shifted[i]] != yte[i]))
            RES["per_fold"][f"{'_'.join(tr_s)}_to_{te_s[0]}"] = {
                "n_train": int(len(Xtr)), "n_test": int(len(Xte)),
                "accuracy_pct": float(100.0 * ok.mean())}
            status(f"  train {tr_s} test {te_s}: {100.0 * ok.mean():.1f}% over {len(Xte)} passes")
        except Exception as exc:                                         # noqa: BLE001
            import traceback
            RES["failures"].append({"fold": str(te_s), "error": repr(exc),
                                    "traceback": traceback.format_exc()[-800:]})
            status(f"  fold {te_s} FAILED {exc!r}")

    def grp_stat(name):
        v = grp[name]
        if not v:
            return None
        ci = boot_ci([100.0 * x for x in v])
        obs = 100.0 * float(np.mean(sub_all[name])) if sub_all[name] else None
        ceil = 100.0 * float(np.mean(sub_ceil[name])) if sub_ceil[name] else None
        ratio = (obs / ceil) if (obs is not None and ceil) else None
        return {"n": len(v), "accuracy_pct": 100.0 * float(np.mean(v)),
                "ci95": ci[-2:], "lower_bound_pct": ci[-2],
                "chance_pct": CHANCE, "bar_pct": bar["bar_pct"],
                "CLEARS_THE_BAR": bool(ci[-2] is not None and ci[-2] >= bar["bar_pct"]),
                "substitution": {"observed_pct": obs, "ceiling_pct": ceil, "ratio": ratio,
                                 "PASSES": bool(ratio is not None and ratio >= 0.5)}}

    RES["groups"] = {"edge_midpoints": grp_stat("edge"), "corners": grp_stat("corner")}
    RES["overall_accuracy_pct"] = 100.0 * float(np.mean(ok_all)) if ok_all else None
    g_e, g_c = RES["groups"]["edge_midpoints"], RES["groups"]["corners"]
    passed = [k for k, g in (("edge_midpoints", g_e), ("corners", g_c))
              if g and g["CLEARS_THE_BAR"] and g["substitution"]["PASSES"]]
    RES["A3_PASSES"] = bool(passed)
    RES["groups_that_passed"] = passed
    RES["A2_may_run"] = bool(passed)
    RES["A2_fed_only_by"] = ([r for r in REGIONS
                              if (r in EDGE and "edge_midpoints" in passed)
                              or (r in CORNER and "corners" in passed)] if passed else [])

    RES["minutes"] = round((time.time() - t0) / 60.0, 1)
    RES["contract"] = check_contract(RES, ["groups", "per_fold"], {"per_fold": 3})
    save(STAGE, RES)
    release(lock)

    for k, g in RES["groups"].items():
        status(f"  {k:16s} {g['accuracy_pct']:5.1f}% ci {[round(x,1) for x in g['ci95']]} "
               f"lower {g['lower_bound_pct']:.1f} against a bar of {g['bar_pct']} -> clears "
               f"{g['CLEARS_THE_BAR']}; substitution {g['substitution']['observed_pct']:.1f}/"
               f"{g['substitution']['ceiling_pct']:.1f} ratio "
               f"{g['substitution']['ratio']:.2f} passes {g['substitution']['PASSES']}")
    status(f"  overall {RES['overall_accuracy_pct']:.1f}% against the position head's 18.5 and a "
           f"chance of {CHANCE:.1f}")
    status(f"  A3 PASSES = {RES['A3_PASSES']}; A2 may run = {RES['A2_may_run']}")
    headline(f"A3 START CLASSIFIER: edge midpoints {g_e['accuracy_pct']:.1f} percent, corners "
             f"{g_c['accuracy_pct']:.1f}, against a {CHANCE:.1f} chance and a lower-bound bar of "
             f"{bar['bar_pct']}; passes = {RES['A3_PASSES']}.")
    findings("q3", bool(RES["contract"]["SATISFIED"]), (
        f"A3 AS A STANDALONE START-READING TEST. {RES['windows']}. The bar was fixed before "
        f"training: a lower confidence bound of at least {bar['bar_pct']} percent, twice the "
        f"{CHANCE:.1f} percent chance, within each group.\n\n"
        + "\n".join(
            f"  {k}: {g['accuracy_pct']:.2f} percent, interval {[round(x, 1) for x in g['ci95']]}, "
            f"lower bound {g['lower_bound_pct']:.2f} against the {g['bar_pct']} bar, clears = "
            f"{g['CLEARS_THE_BAR']}; substitution {g['substitution']['observed_pct']:.1f} observed "
            f"over a ceiling of {g['substitution']['ceiling_pct']:.1f}, ratio "
            f"{g['substitution']['ratio']:.2f}, passes = {g['substitution']['PASSES']}"
            for k, g in RES["groups"].items())
        + f"\n\nOVERALL {RES['overall_accuracy_pct']:.2f} percent against the position head's 18.5 "
          f"from D2 and a chance of {CHANCE:.1f}.\n\n"
          f"A3 PASSES = {RES['A3_PASSES']}. Groups that passed: {passed}. A2 may run = "
          f"{RES['A2_may_run']}, fed only by {RES['A2_fed_only_by']}."))
    status(f"{STAGE} DONE in {RES['minutes']:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
