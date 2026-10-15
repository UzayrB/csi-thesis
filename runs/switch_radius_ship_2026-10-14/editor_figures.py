"""The figures the Editor list needs after the ship: the dot error from the first decoded frame on A3 and B2 under the shipped
radius-free switch (the radius test's R0 replays, `runs/switch_radius_a3b2_2026-10-14/R0/`, which the ship's step 3 ties to
`clean_1s_r0`) against `clean_1s` (the 14 Oct CPU replays, `runs/head_offset_2026-10-14/step4_cpu/`, whose figures are the
thesis's current tab:tracking-dot values, so that side checks the method). The 1.0 s record's method exactly
(`runs/head_offset_2026-10-14/editor_figures.py`: app_score.score_recording, the walk-cluster bootstrap, 1,000 draws, seed 0).

    python3 runs/switch_radius_ship_2026-10-14/editor_figures.py      # writes EDITOR_FIGURES.json

Development evaluation, all data seen; inside A3's tenth and B2's eighth looks (no new decode).
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
sys.path.insert(0, J(REPO, "runs", "head_offset_2026-10-14"))
import editor_figures as EF  # noqa: E402  (boot_paired, the 10 Oct record's bootstrap exactly)

NEW = lambda m: J(REPO, "runs", "switch_radius_a3b2_2026-10-14", "R0", m, "semi_disp-K1gf_prof-clean_1s_r0_causal")  # noqa: E731
OLD = lambda m: J(REPO, "runs", "head_offset_2026-10-14", "step4_cpu", m, "semi_disp-K1gf_causal")                     # noqa: E731


def case(model: str, session: str) -> dict:
    import pipeline.live.app_score as S
    wn, wo = [], []
    for lp in sorted(glob.glob(J(OLD(model), f"{session}__*.jsonl"))):
        stem = os.path.basename(lp)[len(session) + 2:-len(".jsonl")]
        gt = J(S.DATA[session], f"{stem}.gt.json")
        nr = {r["pid"]: r for r in S.score_recording(J(NEW(model), f"{session}__{stem}.jsonl"), gt, "committed")}
        orr = {r["pid"]: r for r in S.score_recording(lp, gt, "committed")}
        assert sorted(nr) == sorted(orr)
        for pid in sorted(nr):
            assert nr[pid]["lock_correct"] == orr[pid]["lock_correct"]
            wn.append(nr[pid])
            wo.append(orr[pid])

    def frames(ws, correct_only):
        return [e for w in ws if (w["lock_correct"] or not correct_only) for e in w["err"]]
    out = {"n_walks": len(wn)}
    for which, co in (("all_walks", False), ("correct_lock_walks", True)):
        out[which] = {
            "median_m": EF.boot_paired(wn, wo, lambda ws, co=co: float(np.median(frames(ws, co)))),
            "p90_m": EF.boot_paired(wn, wo, lambda ws, co=co: float(np.percentile(frames(ws, co), 90))),
            "within_0_5m_pct": EF.boot_paired(wn, wo, lambda ws, co=co: 100.0 * float(np.mean(np.asarray(frames(ws, co)) <= 0.5)))}
    return out


if __name__ == "__main__":
    res = {"what": "Editor-list figures: dot error from the first decoded frame (app_score.score_recording), clean_1s_r0 (the "
                   "radius test's R0 replays) against clean_1s (step4_cpu); the 10 Oct record's walk-cluster bootstrap exactly",
           "label": "development evaluation, all data seen; inside A3's tenth and B2's eighth looks",
           "cases": {f"{m}|{s}": case(m, s) for m, s in (("final", "03"), ("final", "B2"), ("zeroshot", "B2"))}}
    p = J(HERE, "EDITOR_FIGURES.json")
    if os.path.exists(p):
        raise SystemExit(f"REFUSED: {p} exists")
    json.dump(res, open(p, "w", encoding="utf-8"), indent=1)
    for c, f in res["cases"].items():
        for which in ("all_walks", "correct_lock_walks"):
            for st in ("median_m", "p90_m", "within_0_5m_pct"):
                b = f[which][st]
                print(f"{c:12s} {which:18s} {st:16s} new {b['new']:.3f} {[round(x, 3) for x in b['new_ci95']]} | old "
                      f"{b['old']:.3f} {[round(x, 3) for x in b['old_ci95']]} | diff {b['new_minus_old']:+.3f} "
                      f"{[round(x, 3) for x in b['diff_ci95']]}")
