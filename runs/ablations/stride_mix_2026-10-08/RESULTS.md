# Stride ablation: results (development evaluation, all data seen)

PLAN.md's rule. Committed and lock in percent, averaged over the complete seed sets, with a 95 % bootstrap interval over walks (1,000 draws, seed 0). Edge lines committed / lock. Rotations: A1+A2 to B1, A1+B1 to A2, A2+B1 to A1 (120 walks each, 360 pooled); A3 and B2 never read.

## Primary: committed-line error, arm minus MIX (points), paired by seed set

| arm | seed sets | per seed set | mean [95 % t-interval] | verdict | lock, arm minus MIX |
|---|---|---|---|---|---|
| ALL05 | [0, 1, 2] | -3.33, -0.28, -0.83 | -1.48 [-5.52, +2.56] | **no measurable difference** | +0.09 [-0.96, +1.15] |
| ALL1 | [0, 1, 2] | +1.39, -0.56, +3.06 | +1.30 [-3.19, +5.79] | **no measurable difference** | -0.19 [-1.92, +1.55] |

**Does the stride mix matter?** False

## Each arm, pooled and per rotation

| arm | split | committed [95 %] | lock [95 %] | E_col1 | E_col5 | E_row1 | E_row5 |
|---|---|---|---|---|---|---|---|
| MIX | pooled | 75.83 [71.94, 79.72] | 53.80 [48.98, 58.43] | 70 / 54 | 83 / 39 | 98 / 43 | 85 / 44 |
| MIX | B1 | 59.17 [50.83, 67.22] | 38.06 [30.83, 46.39] | 83 / 83 | 61 / 28 | 100 / 0 | 100 / 61 |
| MIX | A2 | 94.44 [91.11, 97.22] | 76.11 [70.00, 82.50] | 78 / 78 | 100 / 61 | 100 / 89 | 94 / 72 |
| MIX | A1 | 73.89 [66.94, 80.83] | 47.22 [39.17, 55.28] | 50 / 0 | 89 / 28 | 94 / 39 | 61 / 0 |
| ALL05 | pooled | 77.31 [73.42, 81.11] | 53.89 [49.07, 58.98] | 74 / 48 | 93 / 59 | 100 / 56 | 83 / 39 |
| ALL05 | B1 | 66.94 [59.17, 74.72] | 42.22 [33.89, 51.67] | 78 / 72 | 78 / 72 | 100 / 0 | 100 / 56 |
| ALL05 | A2 | 91.11 [86.39, 95.28] | 72.78 [65.83, 80.28] | 100 / 72 | 100 / 61 | 100 / 100 | 83 / 61 |
| ALL05 | A1 | 73.89 [65.83, 81.94] | 46.67 [38.33, 54.72] | 44 / 0 | 100 / 44 | 100 / 67 | 67 / 0 |
| ALL1 | pooled | 74.54 [70.65, 78.89] | 53.61 [48.98, 58.06] | 63 / 52 | 76 / 31 | 98 / 35 | 87 / 43 |
| ALL1 | B1 | 57.78 [49.72, 65.83] | 38.61 [31.11, 47.22] | 83 / 78 | 56 / 17 | 100 / 0 | 100 / 56 |
| ALL1 | A2 | 94.44 [90.56, 97.22] | 75.00 [68.06, 81.67] | 61 / 78 | 100 / 67 | 100 / 83 | 94 / 67 |
| ALL1 | A1 | 71.39 [63.88, 78.62] | 47.22 [39.44, 55.28] | 44 / 0 | 72 / 11 | 94 / 22 | 67 / 6 |

## Per seed set, pooled

| arm | seed set | committed | lock |
|---|---|---|---|
| MIX | 0 | 75.56 | 54.44 |
| MIX | 1 | 75.00 | 54.44 |
| MIX | 2 | 76.94 | 52.50 |
| ALL05 | 0 | 78.89 | 54.44 |
| ALL05 | 1 | 75.28 | 54.17 |
| ALL05 | 2 | 77.78 | 53.06 |
| ALL1 | 0 | 74.17 | 53.61 |
| ALL1 | 1 | 75.56 | 55.00 |
| ALL1 | 2 | 73.89 | 52.22 |

## Reading (written 23:08 SAST, 8 October 2026)

**The stride mix does not measurably matter.** Under PLAN.md's fixed rule, neither alternative differs from the shipped
mix on pooled committed-line error over three seed sets: all-0.5 s heads -1.48 points [-5.52, +2.56], all-1 s heads
+1.30 [-3.19, +5.79]; both intervals contain zero. The display lock does not move either (+0.09 and -0.19 points).
Development evaluation, all data seen.

**One pattern, reported and not tested by the rule:** on the cross-room rotation (A1+A2 to B1, trained on Room A
only) the all-0.5 s pool commits 66.94 % against MIX's 59.17 %, while on the two within-room rotations it is level or
slightly lower (A2 91.11 against 94.44; A1 73.89 against 73.89). Its advantage shrank from seed set 0 to seeds 1 and 2
(-3.33, then -0.28 and -0.83 points of pooled error). A hint for a cross-room study, not a finding.

**The edge lines** (committed / lock, pooled over three rotations and three seed sets, 54 decisions each) are in the
table above. The per-rotation edges rest on 6 walks a seed set; B1's E_row1 lock is 0 % and A1's E_col1 lock 0 % in every
arm, so those zeros belong to the rotations, not to the stride.

## Disclosures

- **Two early looks** at Uzayr's request: 15:39 (B1, seed set 0) and 21:56 (seed sets 0 and 1, all rotations). The run,
  the arms and the rule were not changed after either.
- **Inputs rebuilt, byte-checked:** B1's 1 s and 0.5 s window arrays had been deleted (6 Oct and 1 Oct cleanups) and
  were re-cut from `data/` with the original cutters; every `meta.json` byte-identical to the surviving one.
- **Pace:** every decode used the rotation records' setting, the modules' default N(1.298, 0.123), which was measured
  on A1+A2+A3 anchors. The same for every arm, and A3 is never scored here, so the paired comparison does not depend
  on it; it does mean these rotation figures are not A3-free in that one statistic.
- **Plumbing:** MIX seed set 0 (the recorded `d4c_fuse` heads) reproduced each rotation's recorded decode exactly
  (0 of 120 committed, display-lock and scorer-lock changes, on all three rotations).
- **Compute changes only** (PLAN addenda): driver restarts at 14:26, 14:49, 19:31 and 22:33; the arm-independent
  readers step cached per rotation after a byte-identity check; a memory guard from 19:40 (it never paused anything);
  the last four decodes rerun at nice 0 (zsh's BG_NICE had niced every earlier one).
- **No shipped file changed:** at 23:00 the final (454 files) and zero-shot (218) model sets and the current hash lists
  (`TRACE_HASHES_fin_A3`, `_fin_B2`, `_zsf_B2`, `FINAL_CORRECTED_HASHES` and its supplement) re-hashed with 0
  mismatches, and FINAL_CONFIG.md matched its hash.

## Reproducing

From the repository root with `/opt/anaconda3/bin/python3`: `run.py` trains every network (one GPU job at a time,
memory watchdog, caffeinate) and decodes every arm, skipping anything finished; `eval_one.py --rot <B1|A2|A1> --arm
<MIX|ALL05|ALL1> --k <0|1|2>` decodes one; `score.py` writes `results.json` and this file. B1's window arrays must
exist at both strides (`recut_b1_05.py`; `pipeline.io.windows --stride 1.0 --sessions B1` for 1 s). Start long jobs
from zsh with `setopt NO_BG_NICE`. The networks are in `runs/<rotation>/<network>_k<k>/art/models/`; the per-walk
answers of every decode are in `runs/<rotation>/eval_<arm>_k<k>.json`.
