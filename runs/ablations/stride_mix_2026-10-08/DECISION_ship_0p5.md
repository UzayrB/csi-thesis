# Decision: ship the all-0.5 s heads. Written 2026-10-08 23:28 SAST (clock read), committed before any training

**Decision (Uzayr, 8 October 2026, after the stride ablation's result):** the deployed tracker and the zero-shot model
ship the all-0.5 s arm, so every one of the five pool heads is trained on one stride.

**The reason is simplicity, not performance.** The stride ablation (`RESULTS.md`, 65e22a80) found no measurable
difference: ALL05 minus MIX -1.48 [-5.52, +2.56] points of pooled committed-line error, lock +0.09 [-0.96, +1.15],
three seed sets on the three training rotations, development evaluation, all data seen. The report will say exactly
that.

## Fixed now, before any test decode

- **The recipe:** the ablation's ALL05 arm. Five heads, each one shared LinkCNN encoder with the fusion head
  (`arch` fuse), augmentation on, relative RSSI, 24 epochs, Adam 1e-3, weight decay 1e-4, batch 64, every head trained
  on the press-aligned **0.5 s** walking windows.
- **The seeds: the ablation's ALL05 seed set 0, not chosen among seed sets.**

  | pool slot | shipped (MIX) | now (ALL05) |
  |---|---|---|
  | `half` | 0.5 s, 25 cells, seed 0 | unchanged: the same trained file |
  | `fh1s` | 1 s, 25 cells, seed 0 | 0.5 s, 25 cells, **seed 3** |
  | `g1s1` | 1 s, 25 cells, seed 1 | 0.5 s, 25 cells, seed 1 |
  | `g1s2` | 1 s, 25 cells, seed 2 | 0.5 s, 25 cells, seed 2 |
  | `g100` | 1 s, 100 cells, seed 0 | 0.5 s, 100 cells, seed 0 |

  The brief asks for the shipped seeds. At 0.5 s the `fh1s` slot's seed 0 would train a byte-identical copy of `half`
  (same data, same seed, deterministic training), leaving four distinct heads with one counted twice. The ablation's
  ALL05 arm used seed 3 in that slot for this reason, and that arm is the recipe being shipped; the other four seeds
  are the shipped ones. Uzayr was told before training started.
- **Models:** the deployed model (`fin`, trained on A1+A2+B1) and the zero-shot model (`zsf`, A1+A2). Four new heads
  each; `half` is reused byte for byte.
- **Unchanged:** the display head DISP_END, the start-of-walk readers (their own per-link networks and rows), the
  motion gate and every decode setting (variant `relgateU+abstain+a2w0.25`, frozen A1+A2 pace, display K1g at spread
  4.5). None depends on the pool heads' training stride; if a check shows otherwise, work stops and Uzayr is told.
- **It ships whatever A3 and B2 show.** No reverting, and no further selection, on test results.

## The cross-room hint, disclosed

On the cross-room rotation (A1+A2 to B1, trained on Room A only) the ALL05 pool committed 66.94 % against MIX's 59.17 %,
averaged over three seed sets; the gap shrank from seed set 0 to seeds 1 and 2 (pooled error differences -3.33, then
-0.28 and -0.83 points), and on the two within-room rotations ALL05 was level or slightly lower. This is not why the
all-0.5 s heads ship, and it was not tested by the ablation's rule.

## Test looks

One decode of each test session in the live app (semi mode, as-it-arrives clock, `app_score`): B2 deployed, B2
zero-shot, and A3 on the shipped display (spread 4.5), plus the fully constrained and unconstrained modes reported in
the results. Uzayr's brief calls this **A3's fifth look and B2's second**. By the counting the records use for A3
(midpoint, FINAL, the corrected test, A3-clean lock on 8 October), it is A3's fifth and **B2's fourth** (midpoint,
FINAL, the corrected test, this). Both are recorded.

## Kept on record

The old (MIX) figures stay in every record and report as they are. The old heads, model sets (`runs/live/models/
final.json`, `zeroshot.json`), hash lists and FINAL_CONFIG are archived beside the new ones under dated names, never
deleted or overwritten. The A3-clean lock selection of 8 October (spread 2.5) was made on the old mix and is not re-run;
its cost on the new heads is estimated for Uzayr.
