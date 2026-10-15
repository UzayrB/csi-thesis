"""Intervals for the rotation figures the report sentences quote (Mastermind's review of 04c56b38, item 3).

    python3 runs/a3_clean_2026-10-08/dot/sentence_intervals.py

Offline, from the existing stage replays only (no decode, no A3): stage 1's two arms (held-out DISP_END and the pooled
display, both at the shipped offset and phase, switching off) and the chosen configuration (stage 5, arm A). The method is
PREREG_DOT's: 95 % percentile bootstrap, 1,000 draws, seed 0, walks resampled within each rotation, rotation-weighted
(2 B1 + A2 + A1) / 4; differences are PAIRED (the same drawn walks for both arms). The statistics are arm_figures':
  - median dot error on correct-lock walks, frames from press + 2.0 s (per rotation, the median of the pooled frames);
  - mean signed along-line offset on correct-lock walks, frames from the first decoded frame (per rotation, the mean of
    the pooled frames);
  - jumps over 0.5 m per walk, all walks, frames from the first decoded frame (per rotation, the mean over walks).
Writes dot/SENTENCE_INTERVALS.json.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

J = os.path.join
DOT = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(DOT)
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)
import dot_harness as H  # noqa: E402
import measures as M  # noqa: E402
from pipeline.live.app_score import DATA  # noqa: E402

ROTS = ("B1", "A2", "A1")
STEMS = ["participant_PA5_walk", "participant_PA1_walk", "participant_PA2_walk", "participant_PA3_walk",
         "participant_PA4_walk", "participant_PA6_walk"]
W = M.WEIGHTS


def walks_of(stage: int, arm: str) -> dict:
    arms = json.load(open(J(DOT, f"stage{stage}", "ARMS.json"), encoding="utf-8"))["arms"]
    vn = H.variant_name(arms[arm])
    out = {}
    for rot in ROTS:
        s = H.ROTS[rot][0]
        out[rot] = {}
        for stem in STEMS:
            for pid, w in M.load(J(DOT, f"stage{stage}", "multi", vn, f"{s}__{stem}.jsonl"),
                                 J(DATA[s], f"{stem}.gt.json")).items():
                out[rot][f"{stem}|{pid}"] = w
    return out


def per_walk(ws: dict) -> dict:
    """{rot: {key: (errors from the press if lock-correct, signed offsets if lock-correct, jumps, lock-correct)}}."""
    out = {}
    for rot, d in ws.items():
        out[rot] = {}
        for k, w in d.items():
            ok = w["lock"] == w["true"]
            out[rot][k] = (M.errors(w, M.from_press_frames(w)) if ok else [],
                           M.signed_offsets(w, M.decoded_frames(w)) if ok else [],
                           M.jumps(M.decoded_frames(w)), ok)
    return out


def stat(pw: dict, keys: dict, which: str) -> float:
    """The rotation-weighted statistic over the given walks (keys[rot] a list, repeats allowed)."""
    tot = 0.0
    for rot in ROTS:
        rows = [pw[rot][k] for k in keys[rot]]
        if which == "median_err":
            v = float(np.median([e for r in rows if r[3] for e in r[0]]))
        elif which == "mean_offset":
            v = float(np.mean([e for r in rows if r[3] for e in r[1]]))
        else:
            v = float(np.mean([r[2] for r in rows]))
        tot += W[rot] * v
    return tot / sum(W.values())


def boot(pa: dict, pb: dict, which: str, n_boot: int = 1000, seed: int = 0) -> dict:
    """Point and 95 % interval of a, of b and of a minus b (paired, walks resampled within rotations)."""
    rng = np.random.default_rng(seed)
    universe = {rot: sorted(k for k in pa[rot] if (which == "jumps" or pa[rot][k][3])) for rot in ROTS}
    for rot in ROTS:
        assert sorted(pa[rot]) == sorted(pb[rot]) and all(pa[rot][k][3] == pb[rot][k][3] for k in pa[rot]), rot
    full = {rot: universe[rot] for rot in ROTS}
    pt_a, pt_b = stat(pa, full, which), stat(pb, full, which)
    da, db, dd = [], [], []
    for _ in range(n_boot):
        keys = {rot: [universe[rot][i] for i in rng.integers(0, len(universe[rot]), len(universe[rot]))] for rot in ROTS}
        a, b = stat(pa, keys, which), stat(pb, keys, which)
        da.append(a), db.append(b), dd.append(a - b)
    ci = lambda v: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]             # noqa: E731
    return {"a": pt_a, "a_ci95": ci(da), "b": pt_b, "b_ci95": ci(db), "a_minus_b": pt_a - pt_b, "diff_ci95": ci(dd),
            "n_walks": {rot: len(universe[rot]) for rot in ROTS}}


def main() -> int:
    end = per_walk(walks_of(1, "DISP_END"))
    pooled = per_walk(walks_of(1, "centre_labelled"))
    chosen = per_walk(walks_of(5, "A"))
    res = {"method": "PREREG_DOT: 95 % percentile bootstrap, 1,000 draws, seed 0, walks within rotations, (2 B1 + A2 + A1) / 4, paired",
           "label": "development evaluation, all data seen",
           "stage1_heldout_DISP_END_vs_pooled": {"median_err_from_press_ok_m": boot(end, pooled, "median_err"),
                                                 "mean_signed_offset_ok_m": boot(end, pooled, "mean_offset"),
                                                 "jumps_over_0_5m_per_walk": boot(end, pooled, "jumps")},
           "chosen_vs_stage1_pooled": {"median_err_from_press_ok_m": boot(chosen, pooled, "median_err"),
                                       "mean_signed_offset_ok_m": boot(chosen, pooled, "mean_offset")}}
    out = J(DOT, "SENTENCE_INTERVALS.json")
    if os.path.exists(out):
        raise SystemExit(f"REFUSED: {out} exists")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    for k, v in res.items():
        if isinstance(v, dict):
            for kk, b in v.items():
                print(k, kk, {x: (round(y, 3) if isinstance(y, float) else ([round(z, 3) for z in y] if isinstance(y, list) else y))
                              for x, y in b.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
