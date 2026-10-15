"""The figures the Editor list needs (step 7 of DECISION_1p0.md), from the corrected step 4 logs (1.0 s, CPU) and, as a check
of the method, from the shipped 0.75 s logs (which must reproduce the thesis's current tab:tracking-dot values). The dot is
scored from the first decoded frame against the truth 2.0 s earlier (app_score's frames; measures.decoded_frames); intervals
are 95 % percentile bootstraps over walks, 1,000 draws, seed 0.

    python3 runs/head_offset_2026-10-14/editor_figures.py      # writes EDITOR_FIGURES.json

Development evaluation, all data seen.
"""

from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
sys.path.insert(0, J(REPO, "runs", "a3_clean_2026-10-08"))
DIRS = {"1.0 s": lambda m: J(HERE, "step4_cpu", m, "semi_disp-K1gf_causal"),
        "0.75 s shipped": lambda m: J(REPO, "runs", "live", "replay", m, "semi_disp-K1gf_causal")}


def boot_paired(new_w: list, old_w: list, stat, n_boot: int = 1000, seed: int = 0) -> dict:
    """runs/clean_display_2026-10-10/run.py's boot_paired exactly: walks resampled, the same drawn walks for both."""
    a, b = stat(new_w), stat(old_w)
    idx = np.random.default_rng(seed).integers(0, len(new_w), size=(n_boot, len(new_w)))
    da, db = [], []
    for row in idx:
        da.append(stat([new_w[i] for i in row]))
        db.append(stat([old_w[i] for i in row]))
    da, db = np.asarray(da, float), np.asarray(db, float)
    ci = lambda v: [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))]        # noqa: E731
    return {"new": a, "new_ci95": ci(da), "old": b, "old_ci95": ci(db), "new_minus_old": a - b, "diff_ci95": ci(da - db)}


def case(model: str, session: str) -> dict:
    """The 10 Oct record's look_figures, new (1.0 s, step4_cpu) against old (the shipped 0.75 s), on app_score's walks."""
    import pipeline.live.app_score as S
    new_d, old_d = DIRS["1.0 s"](model), DIRS["0.75 s shipped"](model)
    wn, wo = [], []
    for lp in sorted(glob.glob(J(old_d, f"{session}__*.jsonl"))):
        stem = os.path.basename(lp)[len(session) + 2:-len(".jsonl")]
        gt = J(S.DATA[session], f"{stem}.gt.json")
        nr = {r["pid"]: r for r in S.score_recording(J(new_d, f"{session}__{stem}.jsonl"), gt, "committed")}
        orr = {r["pid"]: r for r in S.score_recording(lp, gt, "committed")}
        assert sorted(nr) == sorted(orr)
        for pid in sorted(nr):
            wn.append(nr[pid])
            wo.append(orr[pid])

    def frames(ws, correct_only):
        return [e for w in ws if (w["lock_correct"] or not correct_only) for e in w["err"]]
    out = {"n_walks": len(wn)}
    for which, co in (("all_walks", False), ("correct_lock_walks", True)):
        out[which] = {
            "median_m": boot_paired(wn, wo, lambda ws, co=co: float(np.median(frames(ws, co)))),
            "p90_m": boot_paired(wn, wo, lambda ws, co=co: float(np.percentile(frames(ws, co), 90))),
            "within_0_5m_pct": boot_paired(wn, wo, lambda ws, co=co: 100.0 * float(np.mean(np.asarray(frames(ws, co)) <= 0.5)))}
    return out


if __name__ == "__main__":
    res = {"what": "Editor-list figures: dot error from the first decoded frame (app_score.score_recording), 1.0 s (step4_cpu) "
                   "against the shipped 0.75 s; the 10 Oct record's walk-cluster bootstrap exactly (1,000 draws, seed 0)",
           "label": "development evaluation, all data seen",
           "cases": {f"{m}|{s}": case(m, s) for m, s in (("final", "03"), ("final", "B2"), ("zeroshot", "B2"))}}
    json.dump(res, open(J(HERE, "EDITOR_FIGURES.json"), "w", encoding="utf-8"), indent=1)
    for c, f in res["cases"].items():
        for which in ("all_walks", "correct_lock_walks"):
            for st in ("median_m", "p90_m", "within_0_5m_pct"):
                b = f[which][st]
                print(f"{c:12s} {which:18s} {st:16s} new {b['new']:.3f} {[round(x, 3) for x in b['new_ci95']]} | old "
                      f"{b['old']:.3f} {[round(x, 3) for x in b['old_ci95']]} | diff {b['new_minus_old']:+.3f} "
                      f"{[round(x, 3) for x in b['diff_ci95']]}")
