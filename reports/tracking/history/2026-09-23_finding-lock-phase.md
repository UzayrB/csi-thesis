# The shipped lock is drawn up to 0.5 s before its last window has finished recording

> **CORRECTED 2026-09-23 (freeze 23d, `reports/CORRECTION_drawn_lock_2026-09-23.md`):** every lock figure below decoded the display at `sd_scale` 1.0. The render draws its lock at 4.5. As drawn: grid 55.83, ONE lattice 53.33 held-out, paired -3.10 [-4.88, -0.95]. The comparisons below are like with like and stand as measured.


> **FIXED 2026-09-23 (batch 23d), operator instruction 4 item 2:** the press-aligned lattice is now
> the ONE lattice for everything drawn and quoted. `reports/FIX_one_lattice_2026-09-23.md`. What
> follows is the finding as written.

2026-09-23, batch 23c, found while designing item 2 (the press-aligned lattice). **Nothing has been
changed as a result of this document.** It is a measured fault in the shipped render, `23a`, and
it bears on what "the causal horizon" means for items 2 and 4.

---

## The finding in one line

**Rule 6 and V3 as amended on 2026-09-23 draw the lock at exactly press + 2.0 s, but the lock line
is still read from window `lo + 2`, and on the shipped lattice that window finishes recording
AFTER press + 2.0 s on 360 of 360 passes: median +0.218 s, minimum +0.001 s, maximum +0.499 s.**

## The measurement

Shipped tree `runs/constrained/windows_half`, all 18 recordings, 360 passes; press times from the
sidecars (`data/`, read only), on the same clock as `t_start_abs`.

| quantity | median | min | max | n |
|---|---|---|---|---|
| first walk window `lo` start, relative to the press | -0.782 s | -0.999 s | -0.501 s | 360 |
| **window `lo + 2` end, relative to press + 2.0 s** | **+0.218 s** | +0.001 s | **+0.499 s** | 360 |
| passes where it is after the lock frame | **360 of 360** | | | |
| passes where it is more than 0.25 s after | 165 of 360 | | | |

## Why it happens, from the code

- `f3_render.py:541`: `park_until = t_press_start + LATENCY`, with `LATENCY = 2.0`. The commit
  frame is the press plus 2.0 s on the recording's own clock (V3, amended 23a).
- `night_arms.py`: the lock line is the fixed-lag path at step `li = round(2.0 / 0.5) - lw = 2`
  from `lo_disp = lo - DISPLAY_LEAD_IN_W = lo` (`f3_render.py:221`, lead-in 0), decoded with evidence
  horizon `ev_w = 0`. So it reads windows `lo .. lo + 2`, and window `lo + 2` ends at
  `t[lo] + 1.0 + 2.0`.
- `t[lo]` sits between 0.5 and 1.0 s before the press, because the lattice is one grid per
  recording and its phase against each press is arbitrary (rule 6 itself records the median
  0.202 s of that scatter).

**Before 23a the same lock was causal.** The commit frame was `scene_start + LATENCY` =
`t[lo] + 2.0 - 0.75 + 2.0` = `t[lo] + 3.25`, which is 0.25 s after window `lo + 2` ends. The
amendment moved the commit frame 0.45 s earlier, onto the press, without moving the windows the
lock reads.

## Why no check caught it

Rule 5's evidence causal bound is computed over the `post` frames only (`f3_render.py:651-664`):
the drawn path from the first decoded position on. **The lock DECISION is not a drawn window**,
and the anchor segment between the press and the first decoded position, which is drawn on the
locked line's entry, is not in `post` either. The index-based "causal horizon" in
`reports/FINDING_two_locks_2026-09-23.md`, `lo + step`, is causal in window arithmetic and
assumes `lo` is named at the press; it is not causal in wall-clock time by the lattice phase.

## What it means

- **The shipped 57.50 lock is not strictly causal at the frame it is drawn on.** It reads a
  median 0.22 s of radio that has not finished recording. This is smaller than the 1.0 s leak the
  two-locks finding removed from the diagnostics, and it is in the shipped render, not only in
  diagnostics.
- **It does not touch the committed answer or the 62.50 headline**, which are full-walk.
- **Item 2's press-aligned lattice removes it by construction.** With a window starting exactly
  on the press, `lo` starts at press - 1.0 s and `lo + 2` ends at exactly press + 2.0 s, the
  commit frame, on every pass. Item 2 therefore measures its lock at the WALL-CLOCK causal horizon
  and reports the shipped lock beside it with this leak stated.
- **Item 4 (mid-walk switching)** takes its decisions "using radio to t + 2.0 s only", which is a
  wall-clock horizon; it is measured in wall-clock terms for the same reason.

## What is NOT done here

No render change and no rule change: the render is frozen at `23a` and a fix is a change to what
ships. The two fixes available are (i) item 2's lattice, which keeps three windows of evidence and
makes them exactly causal, or (ii) on the shipped lattice, locking on the last window finished by
press + 2.0 s, which is `lo + 1` on every pass and costs half a second of evidence. **Which one, if
either, is the operator's decision**, and item 2's measurement is the evidence for it.

## THE TWO FIXES, PRICED (batch 23c, after this document was written)

Both measured over nine pairings, 1080 passes, against the shipped lock at 57.50.

| | held-out 7 | paired against shipped | E_col1 | E_col5 | E_row1 | E_row5 | late locks |
|---|---|---|---|---|---|---|---|
| **shipped** (reads `lo + 2`, +0.218 s median past its frame) | 57.50 | | 42.59 | 77.78 | 35.19 | 57.41 | **1080 of 1080** |
| **(i) press-aligned lattice**, `y4_pressalign` | 50.00 | **-4.52 [-6.90, -2.38]** | 37.04 | 66.67 | 27.78 | 50.00 | **0** |
| **(ii) lock on `lo + 1`**, shipped lattice, `y4b_lockstep1` | 50.00 | **-3.69 [-6.67, -0.95]** | 33.33 | 37.04 | **1.85** | 16.67 | 0 |

(ii) uses the lock proxy, which matches the render lock on the median and all four edge lines.

**Reading.** Exact causality costs about four points of held-out lock accuracy either way; the
shipped 57.50 is partly radio that has not finished recording when the lock is drawn. **(i) keeps
the edge lines; (ii) destroys them**, E_row1 to 1.85, because it throws away a whole window of
evidence where (i) re-phases the same three windows. **Neither ships under the rule as written**:
both fail (a) in the negative direction and (f). The third option, not measured and not proposed
by me because it changes an operator decision: move the lock frame from press + 2.0 to press +
2.5 s, which makes the shipped lattice's `lo + 2` causal on every pass (its worst case is +0.499 s)
but changes V1/V3. **Which of these, if any, is the operator's call.**

`tests/test_lock_phase.py` records the fault as a strict expected failure, so the suite goes red
the moment it is fixed and the marker has to be removed deliberately.
