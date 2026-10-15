"""STEPS 1 TO 3: can the START REGION be read from the PRE-PRESS windows alone?
Brief: reports/PREREG_prepress_region_2026-09-21.md. Runs only because t0_oracle cleared its bar.

THE QUESTION. p2_prepress measured the LINE from these windows at chance, 9.17 percent with an
interval of [7.69, 12.31] against 8.33. It never measured the REGION, which is a coarser question
and one the geometry ought to make easy: the eight regions are up to 7 m apart.

STRICTLY CAUSAL. Only windows whose END is at or before the first press. AFTER_S is ZERO and is
asserted here and in tests/test_prepress_is_causal.py. At a 2 s window on a 0.5 s stride that is
four windows covering a 3.5 s span, and MEASURED over all 360 passes that span ENDS a median
0.282 s BEFORE the press, never later than the press itself and never earlier than 0.499 s before
it, because the window lattice does not align with the press. The earliest sample used is a median
3.782 s before the press. The span is 3.5 s wide; it does not reach the press and it does not
reach back a full 4 s.

GROUPED BY PASS, NEVER BY WINDOW. The four windows of a pass overlap by 1.5 s, so they are not four
observations. Every arm builds ONE feature row per pass and the disjointness is asserted, because
a split that let two windows of the same pass fall on opposite sides would be reporting an
interpolation as a generalisation.

THE ARMS.

  A    the existing A3 feature set, the position head's xy_hat and the three per-link xy_hat,
       re-fitted with AFTER_S = 0. Free, no training, and it settles whether the features already
       on record carry the region before the press.
  B    the 25-cell POSTERIOR over the same windows, fused and per link. Also free: the posterior
       artefacts already cover every window of every recording, pre-press ones included. Strictly
       richer than A, whose xy_hat is a two-number summary of this same posterior.
  B2   the frozen CNN embedding, LinkNet.embed with the encoder fixed. Needs the raw window npz
       files, about 285 MB a recording, so it runs last and only if A and B leave it open.

  DEVIATION FROM THE PRE-REGISTRATION, DISCLOSED: arm B as pre-registered was the CNN embedding.
  The posterior arm here is an ADDITION inserted before it, not a substitution, because it is
  nearly free and strictly richer than A. B2 is the pre-registered arm and still runs if the time
  box allows. Nothing is dropped.

WHAT t0_oracle ALREADY ESTABLISHED, and which decides what any of this is worth: a region term is
NET NEGATIVE below about 60 percent accuracy and only buys line accuracy above about 75 percent.
Beating the 20 percent baseline is the pre-registered kill rule but it is NOT sufficient to ship.
Both bars are reported.
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.constrained.night_common import set_half_roots                      # noqa: E402
set_half_roots(REPO_ROOT)
from pipeline.constrained._guard import assert_isolated                           # noqa: E402
assert_isolated("t1_region", os.path.join(REPO_ROOT, "runs", "artefacts_half"))

import time                                                                       # noqa: E402

import numpy as np                                                                # noqa: E402

from pipeline.constrained.common import E_POST, pairings, status, tag_of           # noqa: E402
from pipeline.constrained.fh_common import check_contract, claim_fh, release, save  # noqa: E402
from pipeline.constrained.night_common import boot_ci                             # noqa: E402
from pipeline.constrained.q1_diag import REGIONS, region_of                       # noqa: E402
from pipeline.constrained.rebuild_common import WINDOW_S, findings, headline       # noqa: E402
from pipeline.constrained.t0_oracle import line_regions                           # noqa: E402

STAGE = "t1_region"
#: STRICTLY CAUSAL. Windows whose END lies in [press - BEFORE_S, press - AFTER_S]. AFTER_S is zero
#: and must stay zero: a positive value reads radio recorded after the press.
BEFORE_S, AFTER_S = 2.0, 0.0
SEED = 0
#: the pre-registered kill rule, the best constant predictor over the eight regions
BASELINE_PCT = 20.0
#: THE BAR THAT ACTUALLY DECIDES, from t0_oracle: the region accuracy at which a region term stops
#: costing line accuracy and starts buying it. Beating BASELINE_PCT is necessary, not sufficient.
SHIP_ACC_PCT = 74.2
#: what t0_oracle measured a region term to be worth, for reading any accuracy against
BREAK_EVEN_NOTE = ("t0_oracle: a region term is net NEGATIVE at 37.5 percent accuracy (-10.00 "
                   "points, ci [-15.60, -1.90]) and at 56.7 percent (-4.17, ci [-6.67, 8.10]), "
                   "and buys line accuracy at 74.2 percent (+5.00, ci [1.31, 15.24]). Beating the "
                   "20 percent baseline is the kill rule and is NOT sufficient to ship")


def prepress_indices(t0: np.ndarray, press: float,
                     before_s: float = BEFORE_S, after_s: float = AFTER_S) -> np.ndarray:
    """Windows whose END is at or before the press, within before_s of it.

    THE END, not the start. A window spans [t0, t0 + WINDOW_S] and consists only of samples
    recorded before the press when t0 + WINDOW_S <= press. This is the same legality argument
    p1_runup made and test_prepress_is_causal.py asserts it.
    """
    assert after_s == 0.0, (
        f"AFTER_S is {after_s}, not zero. A positive value selects windows whose end is AFTER the "
        f"press, which reads radio recorded after the moment this head claims to predict from")
    end = np.asarray(t0, float) + WINDOW_S
    return np.flatnonzero((end <= press + 1e-9) & (end >= press - before_s - 1e-9))


def _agg(v: np.ndarray) -> np.ndarray:
    """One row from a pass's windows: the mean over them and the LAST one, which ends at the press."""
    a = np.asarray(v, float)
    return np.concatenate([np.nanmean(a, axis=0).ravel(), a[-1].ravel()])


def collect(sessions, st, kind: str):
    """One feature row PER PASS. kind is 'A' (xy_hat, the A3 set) or 'B' (the 25-cell posterior).

    Returns X, y, keys, who, used, where `used` is {key: the window indices that row was built
    from}, kept so the grouping assertion can be made on the actual indices rather than on trust.
    """
    from pipeline.constrained.artefacts import posterior_path, read_full_posteriors
    from pipeline.constrained.p1_runup import first_presses
    from pipeline.constrained.recordings import load_meta, recordings
    xy = np.asarray(st.xy)
    starts = {nm: xy[st.slice_of[nm][0]] for nm in st.names}
    X, y, keys, who, used = [], [], [], [], {}
    for sess, stem in recordings():
        if sess not in sessions:
            continue
        try:
            rec = load_meta(sess, stem)
        except Exception:                                                # noqa: BLE001
            continue
        tag = None
        for tr_s, te_s in pairings():
            if te_s == (sess,) and tr_s != te_s:
                tag = tag_of(tr_s, te_s, False)
                break
        if tag is None:
            continue
        try:
            blk = read_full_posteriors(posterior_path(tag, 25, E_POST, SEED)).get(stem)
        except Exception:                                                # noqa: BLE001
            continue
        if blk is None:
            continue
        t = np.asarray(rec.t0, float)
        fp = first_presses(sess, stem)
        prob = np.asarray(blk["prob"], float)
        per_link = np.asarray(blk["per_link"], float)
        xh = np.asarray(blk["xy_hat"], float)
        xl = np.asarray(blk["xy_hat_link"], float)
        # THE POSTERIOR LATTICE MUST BE THE RECORDING'S. A window index means nothing unless both
        # sides are on the same stride, and the 1 s tree has half as many rows as the 0.5 s one.
        # Caught on 2026-09-21: a smoke test that imported a pipeline module BEFORE set_half_roots
        # bound ART_DIR to the 1 s tree, and `sel[sel < len(prob)]` then silently dropped every
        # pass in the second half of every recording, ten of twenty, without raising. q3_startclf
        # carries the same truncation and would hide the same fault. Assert, never truncate.
        assert len(prob) == len(t), (
            f"{sess}|{stem} posterior has {len(prob)} windows against the recording's {len(t)}. "
            f"These are different strides, so a window index means different things on each. "
            f"Was set_half_roots called before the first pipeline import?")
        for pid, nm, _a, _b in rec.pass_spans():
            press = fp.get(int(pid))
            if press is None or nm not in starts:
                continue
            sel = prepress_indices(t, press)
            sel = sel[sel < len(prob)]
            if len(sel) < 2:
                continue
            if kind == "A":
                v = [np.nanmean(xh[sel], axis=0), np.nanstd(xh[sel], axis=0),
                     xh[sel[0]], xh[sel[-1]]]
                for li in range(xl.shape[0]):
                    v += [np.nanmean(xl[li][sel], axis=0), xl[li][sel[0]], xl[li][sel[-1]]]
                f = np.concatenate([np.asarray(x, float).ravel() for x in v])
            elif kind == "B":
                f = np.concatenate([_agg(prob[sel])] +
                                   [np.nanmean(per_link[li][sel], axis=0).ravel()
                                    for li in range(per_link.shape[0])])
            else:
                raise ValueError(f"unknown kind {kind}")
            k = f"{sess}|{stem}|{int(pid)}"
            X.append(np.where(np.isfinite(f), f, 0.0))
            y.append(region_of(starts[nm]))
            keys.append(k)
            who.append(stem)
            used[k] = sel.tolist()
    return (np.vstack(X) if X else np.zeros((0, 1))), np.asarray(y), keys, np.asarray(who), used


def assert_grouped_by_pass(keys, used) -> dict:
    """ONE ROW PER PASS, and no window feeding two rows. Asserted, not assumed.

    The four windows of a pass overlap by 1.5 s. If a split ever let two of them fall on opposite
    sides, the reported accuracy would be an interpolation wearing a generalisation's label.
    """
    assert len(keys) == len(set(keys)), (
        f"{len(keys) - len(set(keys))} duplicate pass keys: a pass would appear as two rows")
    seen = {}
    for k in keys:
        stem = k.rsplit("|", 1)[0]
        for i in used[k]:
            prev = seen.get((stem, i))
            assert prev is None, (
                f"window {i} of {stem} feeds both {prev} and {k}, so the two passes are not "
                f"independent rows and any split over them is leaky")
            seen[(stem, i)] = k
    n = [len(used[k]) for k in keys]
    return {"n_rows": len(keys), "n_unique_passes": len(set(keys)),
            "windows_per_pass_median": float(np.median(n)) if n else None,
            "windows_per_pass_min": int(min(n)) if n else None,
            "windows_per_pass_max": int(max(n)) if n else None,
            "no_window_shared_between_passes": True,
            "one_row_per_pass": True}


def confusion(y_true, y_pred) -> dict:
    """The full 8 by 8 matrix, counts. Rows are the truth, columns the prediction."""
    R = list(REGIONS)
    M = {a: {b: 0 for b in R} for a in R}
    for a, b in zip(y_true, y_pred):
        if a in M and b in M[a]:
            M[a][b] += 1
    return M


def pct_ci(flags) -> dict:
    f = [100.0 * float(bool(x)) for x in flags]
    if not f:
        return {"pct": None, "ci95": [None, None], "n": 0}
    m, lo, hi = boot_ci(f)
    return {"pct": float(np.mean(f)), "ci95": [lo, hi], "n": len(f), "boot_mean": m}


def fit_predict(Xtr, ytr, Xte):
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    from sklearn.preprocessing import StandardScaler
    sc = StandardScaler().fit(Xtr)
    clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
    clf.fit(sc.transform(Xtr), ytr)
    Z = sc.transform(Xte)
    return clf.predict(Z), clf.predict_proba(Z), list(clf.classes_)


def previous_end_regions(sessions, st) -> dict:
    """{key: the region the PREVIOUS pass ENDED in}, for the confound split.

    The walker approaches from wherever the previous pass ended, so a head may be reading where
    they came from rather than where they are. Both are radio and neither is cheating, but the
    first is protocol dependent and a deployment without a fixed pass order would not have it.
    """
    import json
    from pipeline.constrained.recordings import load_meta, recordings
    out = {}
    for sess, stem in recordings():
        if sess not in sessions:
            continue
        try:
            rec = load_meta(sess, stem)
            gt = json.load(open(os.path.join("data", "room_A", f"session_{sess}",
                                             f"{stem}.gt.json"), encoding="utf-8"))
        except Exception:                                                # noqa: BLE001
            continue
        ends = {int(p["pass_id"]): region_of(np.asarray(p["anchor_coords"][-1], float))
                for p in gt.get("passes", [])}
        prev = None
        for pid, _nm, _a, _b in rec.pass_spans():
            out[f"{sess}|{stem}|{int(pid)}"] = prev
            prev = ends.get(int(pid), prev)
    return out


def substitution(Xte, yte, keys, who, clf_pred, Xtr, ytr) -> dict:
    """THE GENERALISED RULE, ceiling computed from the ACTUAL pairs used, never assumed.

    Each pass's feature row is replaced by ANOTHER PARTICIPANT'S row over the same window ordinal,
    the prediction recomputed, and the change rate compared with the rate at which a PERFECT
    classifier would change its answer on those same pairs, which is the share of pairs whose true
    regions differ. A component is signal driven only if swapping the CSI moves its answer.
    """
    order = np.argsort(who, kind="stable")
    n = len(keys)
    if n < 2:
        return {"PASSES": None, "reason": "too few passes"}
    # pair each pass with a pass from a DIFFERENT participant, by rotation within the sorted order
    part = np.asarray(who)
    alt = np.zeros(n, dtype=int)
    for i in range(n):
        j = (i + 1) % n
        tries = 0
        while part[order[j]] == part[order[i]] and tries < n:
            j = (j + 1) % n
            tries += 1
        alt[order[i]] = order[j]
    Xsub = Xte[alt]
    pred_sub, _p, _c = fit_predict(Xtr, ytr, Xsub)
    changed = [bool(a != b) for a, b in zip(clf_pred, pred_sub)]
    ceiling = [bool(yte[i] != yte[alt[i]]) for i in range(n)]
    obs = 100.0 * float(np.mean(changed))
    ceil = 100.0 * float(np.mean(ceiling))
    ratio = (obs / ceil) if ceil > 0 else None
    return {"observed_pct": obs, "ceiling_pct": ceil, "ratio": ratio,
            "PASSES": bool(ratio is not None and ratio >= 0.5),
            "rule": ("a decision passes substitution if its observed change rate is at least HALF "
                     "ITS CEILING, the ceiling computed from the actual pairs used: the rate at "
                     "which a perfect classifier would change its answer"),
            "n_pairs": n}


def run_arm(kind: str, st) -> dict:
    """One arm, over the cross-day pairings, train on the training sessions, test on the test one."""
    node = {"per_pairing": {}, "kind": kind}
    allp, allt, allk, allw = [], [], [], []
    for tr_s, te_s in pairings():
        if tr_s == te_s or len(te_s) != 1:
            continue
        tag = tag_of(tr_s, te_s, False)
        Xtr, ytr, ktr, _wtr, utr = collect(tr_s, st, kind)
        Xte, yte, kte, wte, ute = collect(te_s, st, kind)
        if not len(Xtr) or not len(Xte):
            continue
        grp_tr = assert_grouped_by_pass(ktr, utr)
        grp_te = assert_grouped_by_pass(kte, ute)
        assert not (set(ktr) & set(kte)), "leakage: a pass on both sides of the split"
        pred, _proba, _classes = fit_predict(Xtr, ytr, Xte)
        hit = [bool(a == b) for a, b in zip(yte, pred)]
        # the honest baseline: the best CONSTANT predictor, its class chosen on the TRAINING side
        vals, cnts = np.unique(ytr, return_counts=True)
        const = vals[int(np.argmax(cnts))]
        node["per_pairing"][tag] = {
            "n_train_passes": len(ktr), "n_test_passes": len(kte),
            "n_features": int(Xtr.shape[1]),
            "accuracy": pct_ci(hit),
            "constant_predictor": str(const),
            "constant_predictor_pct": 100.0 * float(np.mean([y == const for y in yte])),
            "grouping_train": grp_tr, "grouping_test": grp_te,
            "confusion": confusion(yte, pred),
            "substitution": substitution(Xte, yte, kte, wte, pred, Xtr, ytr)}
        allp += list(pred)
        allt += list(yte)
        allk += list(kte)
        allw += list(wte)
    if not allt:
        return node
    hit = [bool(a == b) for a, b in zip(allt, allp)]
    # EACH PASS IS PREDICTED THREE TIMES, once per pairing whose test side is its session, so the
    # 1080 rows are 360 passes over again. A bootstrap over rows would narrow the interval by a
    # factor it has not earned. The figure that decides is therefore the PER-PAIRING one,
    # bootstrapped over the nine pairings, which is the convention every other figure here uses.
    per_tag = [v["accuracy"]["pct"] for v in node["per_pairing"].values()
               if v["accuracy"]["pct"] is not None]
    m_t, lo_t, hi_t = boot_ci(per_tag) if per_tag else (None, None, None)
    node["pooled"] = {
        "n_rows": len(allt),
        "n_unique_passes": len(set(allk)),
        "rows_per_pass": ("3: each pass is predicted once per pairing whose TEST side is its "
                          "session, so the row count is not a sample size"),
        "accuracy_over_rows": pct_ci(hit),
        "accuracy": {"pct": float(np.median(per_tag)) if per_tag else None,
                     "ci95": [lo_t, hi_t], "boot_mean": m_t, "n": len(per_tag),
                     "definition": ("median of the nine per-pairing accuracies, interval "
                                    "bootstrapped over pairings. THE FIGURE THAT DECIDES")},
        "per_pairing_pct": {t: v["accuracy"]["pct"] for t, v in node["per_pairing"].items()},
        "baseline_pct": BASELINE_PCT,
        "BEATS_BASELINE_LOWER_BOUND": bool(lo_t is not None and lo_t > BASELINE_PCT),
        "confusion": confusion(allt, allp),
        "per_region_recall": {}}
    for r in REGIONS:
        f = [hit[i] for i in range(len(allt)) if allt[i] == r]
        node["pooled"]["per_region_recall"][r] = pct_ci(f)
    # STEP 3, the previous-pass confound, reported as a split AND as its own share
    prev = {}
    for s in ("01", "02", "03"):
        prev.update(previous_end_regions((s,), st))
    same = [i for i in range(len(allk)) if prev.get(allk[i]) == allt[i] and prev.get(allk[i])]
    diff = [i for i in range(len(allk)) if prev.get(allk[i]) is not None
            and prev.get(allk[i]) != allt[i]]
    node["previous_pass_confound"] = {
        "share_of_passes_whose_previous_pass_ENDED_where_this_one_STARTS_pct":
            100.0 * len(same) / max(len(same) + len(diff), 1),
        "n_same": len(same), "n_different": len(diff),
        "accuracy_when_previous_END_matches_this_START": pct_ci([hit[i] for i in same]),
        "accuracy_when_it_does_not": pct_ci([hit[i] for i in diff]),
        "why": ("the walker approaches from wherever the previous pass ended, so a head may be "
                "reading where they came from rather than where they are. Both are radio and "
                "neither is cheating, but the first is protocol dependent: a deployment without a "
                "fixed pass order would not have it. Reported either way, not argued")}
    return node


def main() -> int:
    lock = claim_fh(STAGE)
    t0 = time.time()
    from pipeline.constrained import paths as P
    from pipeline.constrained.fh_common import load
    st = P.states()
    t0res = load("t0_oracle") or {}
    may_run = ((t0res.get("ceiling") or {}).get("STEPS_1_TO_3_MAY_RUN"))
    status(f"{STAGE} START: the start region from the pre-press windows, AFTER_S={AFTER_S}")
    status(f"  t0_oracle says steps 1 to 3 may run: {may_run}")

    RES = {"stage": STAGE, "brief": "reports/PREREG_prepress_region_2026-09-21.md",
           "before_s": BEFORE_S, "after_s": AFTER_S,
           "causality": ("only windows whose END is at or before the first press, so every sample "
                         "used was recorded before the moment predicted from. Asserted in "
                         "prepress_indices and in tests/test_prepress_is_causal.py"),
           "window_span_s": ("a 3.5 s span, MEASURED over all 360 passes as ending a median "
                             "0.282 s before the press (range 0.001 to 0.499 s before it) and "
                             "beginning a median 3.782 s before it (range 3.501 to 3.999). The "
                             "lattice does not align with the press, so the span neither reaches "
                             "the press nor reaches back a full 4 s"),
           "baseline_pct": BASELINE_PCT,
           "baseline_definition": ("the best CONSTANT predictor over the eight regions, which is "
                                   "always SW at 72 of 360 passes. NOT the 12.5 percent uniform "
                                   "chance q3_startclf reported, which is understated"),
           "break_even": BREAK_EVEN_NOTE,
           "t0_gate": {"STEPS_1_TO_3_MAY_RUN": may_run,
                       "ceiling_points": (t0res.get("ceiling") or {}).get(
                           "best_oracle_gain_points_heldout")},
           "deviation_disclosed": ("arm B as pre-registered was the CNN embedding. The 25-cell "
                                   "posterior arm is an ADDITION inserted before it, not a "
                                   "substitution: it is nearly free and strictly richer than A. "
                                   "The pre-registered embedding arm is B2 and runs if the time "
                                   "box allows"),
           "arms": {}, "failures": []}
    if not may_run:
        RES["stopped"] = "t0_oracle did not clear its bar; steps 1 to 3 do not run"
        RES["contract"] = check_contract(RES, ["arms"])
        save(STAGE, RES)
        release(lock)
        return 0

    for kind, name in (("A", "A_xyhat_features"), ("B", "B_cell_posterior")):
        try:
            RES["arms"][name] = run_arm(kind, st)
            p = RES["arms"][name].get("pooled")
            if p:
                status(f"  {name:20s} region accuracy {p['accuracy']['pct']:5.2f} "
                       f"ci {[round(x, 1) for x in p['accuracy']['ci95']]} "
                       f"against a {BASELINE_PCT} baseline -> "
                       f"{'BEATS' if p['BEATS_BASELINE_LOWER_BOUND'] else 'DOES NOT BEAT'}")
        except Exception as exc:                                         # noqa: BLE001
            import traceback
            RES["failures"].append({"arm": name, "error": repr(exc),
                                    "traceback": traceback.format_exc()[-1200:]})
            status(f"  {name} FAILED: {exc!r}")

    beats = {n: bool((v.get("pooled") or {}).get("BEATS_BASELINE_LOWER_BOUND"))
             for n, v in RES["arms"].items() if v.get("pooled")}
    best = max((n for n in beats), key=lambda n: RES["arms"][n]["pooled"]["accuracy"]["pct"],
               default=None)
    RES["kill_rule"] = {
        "arms_beating_the_baseline_lower_bound": [n for n, v in beats.items() if v],
        "KILL_BEFORE_ARM_C": not any(beats.values()),
        "rule": ("pre-registered: if arm A and arm B both fail to beat the 20.0 percent baseline "
                 "with a lower bound above it, stop before arm C and report the negative"),
        "best_arm": best,
        "best_accuracy_pct": (RES["arms"][best]["pooled"]["accuracy"]["pct"] if best else None),
        "ALSO_READ_THE_BREAK_EVEN": BREAK_EVEN_NOTE,
        "SUFFICIENT_TO_SHIP": bool(
            best is not None
            and RES["arms"][best]["pooled"]["accuracy"]["ci95"][0] is not None
            and RES["arms"][best]["pooled"]["accuracy"]["ci95"][0] >= SHIP_ACC_PCT),
        "why_that_second_bar": ("t0_oracle measured a region term net negative below about 60 "
                                "percent accuracy and positive at 74.2. An arm that beats the 20 "
                                "percent kill rule but sits below the break even would COST line "
                                "accuracy if shipped, which is what q4_arms already saw when A2 "
                                "at weight 1.0 made wrong-region errors worse")}

    RES["minutes"] = round((time.time() - t0) / 60.0, 1)
    RES["contract"] = check_contract(RES, ["arms", "kill_rule"])
    save(STAGE, RES)
    release(lock)

    K = RES["kill_rule"]
    status(f"  best arm {K['best_arm']} at {K['best_accuracy_pct']}, kill rule "
           f"{'FIRES' if K['KILL_BEFORE_ARM_C'] else 'does not fire'}, sufficient to ship "
           f"{K['SUFFICIENT_TO_SHIP']}")
    headline(f"T1 REGION: the start region from the pre-press windows alone reaches "
             f"{None if K['best_accuracy_pct'] is None else round(K['best_accuracy_pct'], 1)} "
             f"percent ({K['best_arm']}) against a {BASELINE_PCT} percent baseline and a "
             f"74.2 percent break even; "
             f"{'SHIPS' if K['SUFFICIENT_TO_SHIP'] else 'DOES NOT SHIP'}")
    findings("t1region", bool(RES["contract"]["SATISFIED"]), (
        f"THE START REGION FROM THE PRE-PRESS WINDOWS ALONE.\n\n"
        f"Strictly causal: windows whose END is at or before the first press, AFTER_S = 0. "
        f"MEASURED over all 360 passes, the four windows cover a 3.5 s span ending a median "
        f"0.282 s BEFORE the press and beginning a median 3.782 s before it; the lattice does not "
        f"align with the press, so the span neither reaches the press nor reaches back a full 4 s. "
        f"One feature row per pass, grouping asserted on the window indices themselves.\n\n" +
        "\n".join(
            f"  {n}: {v['pooled']['accuracy']['pct']:.2f} percent, ci "
            f"{[round(x, 1) for x in v['pooled']['accuracy']['ci95']]}, "
            f"n={v['pooled']['n_unique_passes']} passes"
            for n, v in RES["arms"].items() if v.get("pooled")) +
        f"\n\nBaseline {BASELINE_PCT} percent, the best constant predictor.\n"
        f"Break even {SHIP_ACC_PCT} percent, from t0_oracle.\n"
        f"Kill rule {'FIRES: report the negative' if K['KILL_BEFORE_ARM_C'] else 'does not fire'}.\n"
        f"Sufficient to ship: {K['SUFFICIENT_TO_SHIP']}.\n\n"
        f"Brief: reports/PREREG_prepress_region_2026-09-21.md"))
    return 0 if RES["contract"]["SATISFIED"] else 1


if __name__ == "__main__":
    sys.exit(main())
