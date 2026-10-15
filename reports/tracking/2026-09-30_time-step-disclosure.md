# DT_MISMATCH: the 1 s time-step units inside the 0.5 s decoder, disclosed for the 15:39 model

Written 29 September 2026, 23:10 SAST (Uzayr's item 2). **This is a disclosure for the 15:39 model on the
development rotations only. Nothing is adopted from it, and no A3 or B2 decode was made.**

## The mismatch

The decoder rebuild of 17 September ran at a 1 s stride (`rebuild_common.STRIDE_S = 1.0`). The 0.5 s
decoder reads three of its quantities in 1 s units. The reason is that `decoder2.py` takes Dt = 1.0 from
`common.py`, while `night_common.shipped_pieces` sets 0.5 only in `decoder.py`.

| quantity | as shipped | in 0.5 s units |
|---|---|---|
| late-entry reach, per window of the transit clock | v x 1.0 s = 1.30 m | v x 0.5 s = 0.65 m |
| late-entry cost | 1 nat per 1.30 m of arc left unexplained | 1 nat per 0.65 m |
| minimum transit windows between lines (ceil of distance / 1.298 m/s, over the window length) | 0 to 6 windows | 0 to 11 windows |
| the transit clock's saturation | 8 windows (meant as 8 s) | 16 windows |

Movement along a line (`decoder.along_log_score`) uses the correct 0.5 s.

## The arms

Each arm is the 15:39 configuration (`rule/FINAL_CONFIG.md`):
- relgateU + abstain + A2 weight 0.25, display lock;
- the frozen A1+A2 pace, N(1.30341, 0.11255), in every arm;
- the clean reader map.

They were decoded on the three rotations' final-architecture cells (`d4c_fuse_*`) by
`pipeline/constrained/pd_dt.py`.

| arm | what changes |
|---|---|
| **0** | nothing: as shipped |
| **1** (Uzayr's arm) | late-entry reach and cost, and the minimum transit windows, in 0.5 s units: `decoder2.DT = 0.5`, and the new file `runs/dc2_results/v2/transit_geometry_s05.json`. The rb0 file is untouched |
| **1K** (a diagnostic beside it; V2_PREREG's base) | arm 1 with the clock at 16 windows. With the clock left at 8, 42 of the 144 line-to-line transits need 9 to 11 windows, which the clock can never reach |

**The change reached the decoder.** Its transition matrix changes in 14,610 entries. The allowed
transitions go from 19,396 (arm 0) to 9,252 (arm 1). Arm 1K has 522 states (the clock doubled) and
30,644 allowed transitions.

## The result: no decision moves

Paired on the same passes. The 95 percent intervals come from a bootstrap over passes within each
rotation, 1,000 draws, seed 0, weighted as pd_rule (B1 x2):

| arm | committed difference | display lock difference |
|---|---|---|
| 1 against 0 | **0.00 [0.00, 0.00]** | **0.00 [0.00, 0.00]** |
| 1K against 0 | **0.00 [0.00, 0.00]** | **0.00 [0.00, 0.00]** |

| rotation | passes | committed, arms 0 / 1 / 1K | lock, arms 0 / 1 / 1K | exit windows changed (arm 1, 1K) | committed lines changed | walks that reached the 20 s horizon, each arm |
|---|---|---|---|---|---|---|
| A1+A2 -> B1 | 120 | 56.67 / 56.67 / 56.67 | 39.17 / 39.17 / 39.17 | 0, 0 | 0, 0 | 5 |
| A1+B1 -> A2 | 120 | 94.17 / 94.17 / 94.17 | 72.50 / 72.50 / 72.50 | 0, 0 | 0, 0 | 6 |
| A2+B1 -> A1 | 120 | 75.00 / 75.00 / 75.00 | 51.67 / 51.67 / 51.67 | 0, 0 | 0, 0 | 6 |

The drawn dot's resolution is also identical in all three arms. For example, on A1+A2 -> B1 it is
0.50 / 1.13 m on walks whose lock is correct.

**Arm 0 against round 2's record.** Round 2 decoded the same configuration on these cells with the old
pace, N(1.298, 0.123) (`CR.relgateU+abstain+a2w0.25`). Arm 0 uses the frozen A1+A2 pace, and that is the
only difference between them. Arm 0 differs from that record on:
- 6 committed answers (3, 2 and 1 by rotation);
- 1 display lock;
- 4 scorer locks,

out of 360 passes. That is the pace's own effect on the rotations. Every arm here shares the frozen pace,
so the comparison above does not depend on it.

## Why nothing moves

The pass decode is semi-bounded:
1. **At the start press,** it starts on a line (in the first 1 m of every line).
2. **At the causal exit,** it ends the walk at the first window whose forward decode leaves every line.
3. **The committed line** is decided over that interval by per-line Viterbi totals, which read no
   transit state.
4. **The lock** is the display decode's line 1 s into the walk.

Late entry and the minimum transit windows govern only a path that leaves a line, crosses the transit
states and enters another line. No such path decides an exit, a committed line or a lock on these 360
passes.

## What this means

- **For the 15:39 model:** the mismatch is real in the code, and it is inert on every figure this
  disclosure can measure.
- **For V2:** its base carries the 0.5 s units, as pre-registered, whatever this showed. On this
  evidence it changes nothing on its own.

**Files:**
- `runs/dc2_results/cells/d4c_fuse_*/d3/DT{0,1,1K}.relgateU+abstain+a2w0.25/`: `decode.json`,
  `scorerlock.json`, `clean.json`, and `exits.json` (each committed pass's exit window);
- `runs/dc2_results/v2/DT_MISMATCH.json`;
- the transit file `runs/dc2_results/v2/transit_geometry_s05.json`.
