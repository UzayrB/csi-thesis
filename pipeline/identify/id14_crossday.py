"""id14. Cross-day identification on all nine pairings, with the R6 speed diagnostics.

THE QUESTION THIS STAGE EXISTS TO ANSWER. Not "how accurate is identification", which the frozen
record already answers at 25.8 percent with the true line and 22.2 without. The question is whether
ANY of that accuracy is gait rather than pace. On this data the speed-only control beats every gait
arm at a single pass, 28.33 against 23.33, so an arm that merely beats chance has shown nothing.

R6 IS THEREFORE THE POINT OF THE STAGE, not a robustness check appended to it. An arm counts as
gait identification only if its speed-residualised version still beats the permutation null on at
least 5 of 9 pairings. Every arm also reports how often it AGREES WITH S0, the oracle speed-only
control: an arm that mostly predicts what a speed classifier predicts is pace in disguise however
high its accuracy, and that number is harder to argue with than an ablation.

THE ARMS ARE FIXED A PRIORI, in the pre-registration, and no ladder is grown by looking at
accuracy. A0 is the bar for R3, and note what A0 IS: the 19b reference with speed and step_length
removed, leaving exactly one gait feature, cadence, recomputed here WITHOUT the oracle-speed stride
test the frozen code used. A0-brief keeps the oracle-resolved cadence and is reported beside it as
ORACLE-CONTAMINATED, so the gap between them measures how much of the frozen result rested on a
harmonic resolved with the answer in hand.
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
from pipeline.identify.id_heads import (cluster_bootstrap, fit_score,              # noqa: E402
                                        permutation_null, ships_r3)

STAGE = "id14_crossday"
SMOKE = os.environ.get("ID14_SMOKE") == "1"
N_PERM = 20 if SMOKE else 100

#: feature-name prefixes per arm, matched against the id13 feature dict
ENV_KEYS = ("cadence_hz_", "cadence_cv_", "cycle_s_", "autocorr_peak_", "symmetry_ratio_",
            "step_stride_ratio_", "band_ratio_", "estimator_spread_hz_")
SPEC_KEYS = ("spec_gait_cycle_s_", "spec_leg_to_torso_ratio_", "spec_cycle_cv_",
             "spec_left_right_symmetry_", "spec_contour_periodicity_", "spec_leg_contour_cv_")


def _matrix(rows, prefixes) -> np.ndarray:
    keys = sorted({k for r in rows for k in r["features"]
                   if any(k.startswith(p) for p in prefixes)})
    if not keys:
        return np.zeros((len(rows), 0))
    X = np.array([[_num(r["features"].get(k)) for k in keys] for r in rows], float)
    med = np.nanmedian(X, axis=0)
    med = np.where(np.isfinite(med), med, 0.0)
    return np.where(np.isfinite(X), X, med[None, :])


def _num(v):
    try:
        f = float(v)
        return f if np.isfinite(f) else np.nan
    except (TypeError, ValueError):
        return np.nan


def _per_line_z(tr_rows, te_rows, Xtr, Xte, te_lines=None):
    """Z-score each pass by its own LINE's statistics, computed on the TRAIN rows only."""
    lines_tr = np.array([r["line"] for r in tr_rows])
    lines_te = np.array(te_lines if te_lines is not None else [r["line"] for r in te_rows])
    gm, gs = Xtr.mean(0), np.maximum(Xtr.std(0), 1e-6)
    stats = {}
    for ln in np.unique(lines_tr):
        m = lines_tr == ln
        if m.sum() >= 2:
            stats[ln] = (Xtr[m].mean(0), np.maximum(Xtr[m].std(0), 1e-6))
    def z(X, lines):
        out = np.empty_like(X)
        for i, ln in enumerate(lines):
            mu, sd = stats.get(ln, (gm, gs))
            out[i] = (X[i] - mu) / sd
        return out
    return z(Xtr, lines_tr), z(Xte, lines_te)


def _residualise(Xtr, Xte, str_speed, ste_speed):
    """R6. Regress every feature on ORACLE pass speed, LINEAR, fitted on TRAIN, applied to both.

    LINEAR, EXACTLY AS PRE-REGISTERED. A quadratic version was written and MEASURED and then
    REJECTED, and the measurement is worth keeping because the result is counter-intuitive. On
    synthetic arms where the answer was known, over 12 seeds against a 16.7 percent chance line:

        residualise on [1, s]        non-linear PACE arm 18.0 +- 3.1    genuine GAIT arm 43.3
        residualise on [1, s, s^2]   non-linear PACE arm 26.4 +- 4.1    genuine GAIT arm 43.6

    Regressing out MORE speed structure made the pace arm score HIGHER, which is the opposite of
    the intent. The mechanism is that a harder residualisation does not remove the identity
    information carried by speed, it only shrinks the scale of what is left, and the classifier
    standardises its inputs and restores that scale. The registered linear rule is the better test
    and it stays. See addendum D.
    """
    s_tr = np.asarray(str_speed, float)
    s_te = np.asarray(ste_speed, float)
    ok = np.isfinite(s_tr)
    if ok.sum() < 5:
        return Xtr, Xte
    A = np.column_stack([np.ones(ok.sum()), s_tr[ok]])
    coef, *_ = np.linalg.lstsq(A, Xtr[ok], rcond=None)
    def resid(X, s):
        s = np.where(np.isfinite(s), s, np.nanmedian(s_tr[ok]))
        return X - np.column_stack([np.ones(len(s)), s]) @ coef
    return resid(Xtr, s_tr), resid(Xte, s_te)


def _speed_probe(Xtr, Xte, s_tr, s_te) -> float:
    """R6. A linear probe predicting pass speed, fitted on TRAIN, scored on TEST as R squared."""
    ok_tr = np.isfinite(s_tr)
    ok_te = np.isfinite(s_te)
    if ok_tr.sum() < 5 or ok_te.sum() < 3:
        return float("nan")
    A = np.column_stack([np.ones(ok_tr.sum()), Xtr[ok_tr]])
    coef, *_ = np.linalg.lstsq(A, s_tr[ok_tr], rcond=None)
    pred = np.column_stack([np.ones(ok_te.sum()), Xte[ok_te]]) @ coef
    y = s_te[ok_te]
    ss = np.sum((y - y.mean()) ** 2)
    return float(1.0 - np.sum((y - pred) ** 2) / max(ss, 1e-12))


def build_arms(tr, te, emb=None, rng=None) -> dict:
    """Every arm's (Xtr, Xte). Fixed a priori; nothing here is chosen by looking at accuracy."""
    out = {}
    env_tr, env_te = _matrix(tr, ENV_KEYS), _matrix(te, ENV_KEYS)
    spec_tr, spec_te = _matrix(tr, SPEC_KEYS), _matrix(te, SPEC_KEYS)
    out["A1_ENV"] = (env_tr, env_te)
    out["A2_SPEC"] = (spec_tr, spec_te)
    out["A3_ENV_SPEC"] = (np.hstack([env_tr, spec_tr]), np.hstack([env_te, spec_te]))

    cad_tr = _matrix(tr, ("cadence_hz_",))
    cad_te = _matrix(te, ("cadence_hz_",))
    if emb is not None:
        Etr, Ete = emb
        z_tr, z_te = _per_line_z(tr, te, Etr, Ete)
        out["A0"] = (np.hstack([z_tr, cad_tr]), np.hstack([z_te, cad_te]))
        out["A6_ENCODER"] = (z_tr, z_te)
    s_tr = np.array([[_num(r.get("speed_m_s"))] for r in tr])
    s_te = np.array([[_num(r.get("speed_m_s"))] for r in te])
    med = np.nanmedian(s_tr) if np.isfinite(s_tr).any() else 1.3
    out["S0_ORACLE_SPEED"] = (np.where(np.isfinite(s_tr), s_tr, med),
                              np.where(np.isfinite(s_te), s_te, med))
    return out


def main() -> int:
    id_stage_dir(STAGE)
    t0 = time.time()
    status(f"{STAGE} START: cross-day identification, chance {CHANCE_PCT:.1f}"
           + (" [SMOKE]" if SMOKE else ""))

    d13 = id_load("id13_representations") or {}
    path = d13.get("rows_path")
    if not path or not os.path.exists(path):
        status(f"{STAGE}: id13 has not produced rows; nothing to score")
        return 1
    rows = list(np.load(path, allow_pickle=True)["rows"])
    status(f"  {len(rows)} passes from id13")

    # embeddings for A0 and A6, from the FROZEN encoder
    emb_by_key = {}
    try:
        from pipeline.identify.id3_embeddings import pass_embeddings
        for r in pass_embeddings():
            emb_by_key[(r["session"], r["stem"], int(r["pass_id"]))] = np.asarray(r["emb"], float)
    except Exception as e:                                                 # noqa: BLE001
        status(f"  embeddings unavailable ({e}); A0 and A6 will not run")

    RES = {"stage": STAGE, "chance_pct": CHANCE_PCT, "n_passes": len(rows),
           "arms": {}, "R6": {}, "failures": [],
           "heads": "FIXED shrinkage LDA primary; secondaries reported, never selected between"}

    per_arm = {}
    for tr_s, te_s in pairings():
        if tr_s == te_s:
            continue
        tag = tag_of(tr_s, te_s, False)
        tr = [r for r in rows if r["session"] in tr_s]
        te = [r for r in rows if r["session"] in te_s]
        if not tr or not te:
            continue
        ytr = np.array([r["anon"] for r in tr])
        yte = np.array([r["anon"] for r in te])
        rng = np.random.default_rng(0)

        emb = None
        ktr = [(r["session"], r["stem"], int(r["pass_id"])) for r in tr]
        kte = [(r["session"], r["stem"], int(r["pass_id"])) for r in te]
        if emb_by_key and all(k in emb_by_key for k in ktr + kte):
            emb = (np.vstack([emb_by_key[k] for k in ktr]),
                   np.vstack([emb_by_key[k] for k in kte]))

        arms = build_arms(tr, te, emb, rng)
        s_tr = np.array([_num(r.get("speed_m_s")) for r in tr])
        s_te = np.array([_num(r.get("speed_m_s")) for r in te])

        s0 = arms.get("S0_ORACLE_SPEED")
        s0_pred = None
        if s0 is not None:
            r0 = fit_score(s0[0], ytr, s0[1], yte, te)
            s0_pred = r0.get("pred")

        for name, (Xtr, Xte) in arms.items():
            if Xtr.shape[1] == 0:
                continue
            r = fit_score(Xtr, ytr, Xte, yte, te)
            acc = r.get("accuracy_pct")
            if acc is None:
                continue
            node = per_arm.setdefault(name, {})
            correct = (r["pred"] == yte).astype(float)
            # PER-RECORDING CORRECTNESS, kept so id15 can MEASURE the within-recording ICC.
            # The corridor pilot cannot: one line gives six test passes per pairing, one per
            # participant, so every recording group holds a single value and the ICC is
            # unestimable. id15 then fell back to an ASSUMED icc of 0.1 and the DC2 power
            # recommendation, which is the hard deliverable of this run, rested on that assumption
            # rather than on a measurement. The full arms have about twenty passes per recording.
            by_rec = {}
            for rid, c in zip(r["recording_ids"], correct):
                by_rec.setdefault(str(rid), []).append(float(c))
            node[tag] = {
                "accuracy_pct": round(acc, 3),
                "ci95": cluster_bootstrap(correct, r["recording_ids"]),
                "per_recording_correct": by_rec,
                "per_line_recall_pct": r.get("per_line_recall_pct"),
                "secondary": r.get("secondary"),
                "n_test": int(len(yte)),
            }
            if s0_pred is not None and name != "S0_ORACLE_SPEED":
                node[tag]["agreement_with_S0_pct"] = round(
                    float(100.0 * (r["pred"] == s0_pred).mean()), 2)

            # R6, on the gait arms only
            if name.startswith(("A1", "A2", "A3", "A6", "A0")):
                Rtr, Rte = _residualise(Xtr, Xte, s_tr, s_te)
                rr = fit_score(Rtr, ytr, Rte, yte, te)
                null = permutation_null(
                    lambda ysh, a=Rtr, b=Rte, c=yte: (fit_score(a, ysh, b, c) or {}
                                                      ).get("accuracy_pct"),
                    ytr, n=N_PERM)
                node[tag]["R6"] = {
                    "residualised_accuracy_pct": (round(rr["accuracy_pct"], 3)
                                                  if rr.get("accuracy_pct") else None),
                    "drop_pts": (round(acc - rr["accuracy_pct"], 3)
                                 if rr.get("accuracy_pct") else None),
                    "permutation_null_p95": null.get("p95"),
                    "beats_null": bool(rr.get("accuracy_pct") is not None
                                       and null.get("p95") is not None
                                       and rr["accuracy_pct"] > null["p95"]),
                    "speed_probe_r2": round(_speed_probe(Xtr, Xte, s_tr, s_te), 4),
                }
        status(f"  {tag} done ({(time.time() - t0) / 60:.1f} min)")

    # aggregate, R3 against A0, R6 verdicts
    acc_of = {a: {t: v["accuracy_pct"] for t, v in node.items()} for a, node in per_arm.items()}
    for a, node in per_arm.items():
        vals = [v["accuracy_pct"] for v in node.values()]
        edges = [v["per_line_recall_pct"].get("_EDGE_MEAN") for v in node.values()
                 if v.get("per_line_recall_pct")]
        edges = [e for e in edges if e is not None]
        r6 = [v["R6"] for v in node.values() if v.get("R6")]
        beats = sum(1 for x in r6 if x["beats_null"])
        RES["arms"][a] = {
            "per_pairing": node,
            "median_pct": round(float(np.median(vals)), 3) if vals else None,
            "mean_pct": round(float(np.mean(vals)), 3) if vals else None,
            "n_pairings": len(vals),
            "edge_line_mean_recall_pct": round(float(np.mean(edges)), 2) if edges else None,
            "mean_agreement_with_S0_pct": (
                round(float(np.mean([v["agreement_with_S0_pct"] for v in node.values()
                                     if "agreement_with_S0_pct" in v])), 2)
                if any("agreement_with_S0_pct" in v for v in node.values()) else None),
        }
        if r6:
            RES["R6"][a] = {
                "n_pairings_beating_null": beats,
                "R6_PASSES": bool(beats >= 5),
                "mean_residualisation_drop_pts": round(
                    float(np.mean([x["drop_pts"] for x in r6 if x["drop_pts"] is not None])), 3),
                "mean_speed_probe_r2": round(
                    float(np.mean([x["speed_probe_r2"] for x in r6
                                   if np.isfinite(x["speed_probe_r2"])])), 4),
                "rule": ("R6: an arm counts as gait only if its speed-residualised version beats "
                         "the 95th percentile of the permutation null on at least 5 of 9 pairings"),
            }
    if "A0" in acc_of:
        RES["R3"] = {a: ships_r3(acc_of["A0"], acc_of[a]) for a in acc_of if a != "A0"}

    RES["minutes"] = round((time.time() - t0) / 60.0, 1)
    id_save(STAGE, RES)

    gait_pass = [a for a, v in RES["R6"].items() if v["R6_PASSES"]]
    best = max((a for a in gait_pass), key=lambda a: RES["arms"][a]["median_pct"] or 0,
               default=None)
    s0m = (RES["arms"].get("S0_ORACLE_SPEED") or {}).get("median_pct")
    for a, v in sorted(RES["arms"].items()):
        status(f"  {a:16s} median {v['median_pct']}  edge-line {v['edge_line_mean_recall_pct']}  "
               f"agree-with-S0 {v['mean_agreement_with_S0_pct']}  "
               f"R6 {'PASS' if a in gait_pass else 'fail' if a in RES['R6'] else '-'}")
    headline(f"id14 CROSS-DAY: arms passing R6 (gait, not pace) = {gait_pass or 'NONE'}; "
             f"best gait arm {best or 'none'} at "
             f"{RES['arms'][best]['median_pct'] if best else 'n/a'} against chance "
             f"{CHANCE_PCT:.1f} and the oracle speed control at {s0m}")
    findings(STAGE.replace("_crossday", ""), not RES["failures"], (
        f"CROSS-DAY IDENTIFICATION over nine pairings, {len(rows)} passes, chance "
        f"{CHANCE_PCT:.1f} percent. Heads FIXED before the run.\n\n"
        f"R6 IS THE VERDICT, not a robustness check. Arms passing R6: {gait_pass or 'NONE'}.\n\n"
        + "\n".join(f"  {a:16s} median {v['median_pct']}  edge lines "
                    f"{v['edge_line_mean_recall_pct']}  agrees with the oracle speed control on "
                    f"{v['mean_agreement_with_S0_pct']} percent of passes"
                    for a, v in sorted(RES["arms"].items()))
        + f"\n\nTHE ORACLE SPEED CONTROL S0 sits at {s0m}. An arm that does not clear it has not "
          f"shown gait identification, and an arm that AGREES with it on most passes is pace in "
          f"disguise however high its accuracy.\n\n"
          f"A0 is the 19b reference with speed and step_length removed and cadence recomputed "
          f"WITHOUT the oracle-speed stride test. R3 is judged against it."))
    status(f"{STAGE} DONE in {RES['minutes']:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
