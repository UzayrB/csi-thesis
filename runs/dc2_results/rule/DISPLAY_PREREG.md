# DISPLAY_PREREG: where the display's settings come from. Pre-registered 30 September 2026, 09:15 SAST

**Status.** Written before any Part D run on data. Its SHA-256 is in `DISPLAY_PREREG.md.sha256`, and
it is never edited afterwards.

**What it covers.** Uzayr's Part D: the cap, the spread and the other display settings of the 15:39
model's display. **Nothing is adopted in either outcome.** `rule/FINAL_CONFIG.md` and its hash are
untouched, and so is every file of the 15:39 model.

## 1. The cap rule

**The training-derived cap** is (pace mean + 3 SD) x 0.5 s, using the A1+A2 pace N(1.30341, 0.11255)
m/s:

    (1.3034113357347858 + 3 x 0.11254567809955889) x 0.5 = 0.8205242 m per window, written 0.8205

**The shipped cap** is 0.80 m per window, swept on A3's walks (git 8590d47).

## 2. Cap equivalence

**(a) From the code.**
- **Where the cap is read:** the app reads it in one place, `pipeline.constrained.decoder.MAX_ADVANCE_M`.
  That is read by `decoder.along_log_score`, which builds the along-line steps of:
  - `decoder2.transition_matrix2` (the display decode);
  - `decoder.transition_matrix` (the locked-line path and the chain totals);
  - the switching scorer's matrices, built while the cap is set (`pipeline/live/display.CapSwitch`).
- **What it does not touch:** off-line moves (entry, exit, abort, late entry, transit).
- **The step lengths:** 0.25 k on a 5 m line. On a 7.071 m diagonal, 0.25 k or 0.25 k + 0.0711, because
  of the short last step.
- **The identical range:** any cap in [0.75, 0.8211) allows the same steps. Computed at 09:14: the three
  kinds of matrix are bit-identical at 0.80 and 0.8205, and they differ at 0.7499 and 0.8212. Both caps
  are inside the range.

**(b) On the rotations.** Two runs, cap 0.80 and cap 0.8205, on the three rotations:
- the offline decoder: every lock and every drawn path, on A1+A2 -> B1, A1+B1 -> A2 and A2+B1 -> A1;
- the app: every drawn dot, on A1+A2 -> B1.

The test is whether they are bit-identical.

**The outcome.**
- **If (a) and (b) both hold,** the cap is equivalent to a training-derived value, and its A3 label is
  cleared.
- **If not, stop and report,** without sweeping the cap.

## 3. The spread sweep

**The grid:** the display decode's spread (sd_scale) in {2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0}, with
the cap at 0.80.

**What it is run on.** The frozen model's rotation form: the `d4c_fuse_*` cells under the 15:39
configuration, relgateU + abstain + A2 weight 0.25. It uses the frozen A1+A2 pace and the clean reader
map, and is decoded as `pd_clean.decode` with the variant `relgateU+abstain+a2w0.25+sd<x>`.

**When the offline decoder may be used.** Only after a replay gate shows the app and the offline decoder
agree on that rotation: every committed line and display lock equal at spread 4.5, with start and end
presses and the whole-file clock (the offline tree's inputs). On a rotation where the gate fails, the
sweep is run by app replays instead.

**The objective:** rotation-weighted display-lock accuracy, A1+A2 -> B1 x2, A1+B1 -> A2 x1 and
A2+B1 -> A1 x1.

**Selection:** the argmax. Exact ties go to the smallest spread.

**The outcomes:**
- **If the argmax is 4.5:** the spread counts as re-derived on training data, and its A3 label is
  cleared.
- **Otherwise:** the A3 label stays. The report gives the whole curve, and the paired display-lock
  difference of 4.5 against the argmax: per pass, weighted over the rotations as pd_rule, with a 95
  percent bootstrap interval (1,000 draws, seed 0, passes resampled within each rotation).

**Nothing is adopted either way.**

## 4. The other display settings

**Each setting the app's display uses is traced to the data it was set on:**
- the draw phase (head offset 0.375 s, and SHIFT_W 0.50 strides);
- the lock delay and the latency (2.0 s);
- the frame rate;
- the switch's theta, radius, final zone and maximum switches;
- the display prior;
- the display head (DISP_END and its training);
- anything else found in `pipeline/live/display.py` and `final_model.py`.

**The rule.** A setting chosen on A3's walks, or on data that included A3, keeps the A3 display figures
(the lock and the dot error) labelled OPTIMISTIC. The exception is a check of the same kind as sections 2
or 3 that clears it.
- **Operator decisions, not tuned on data:** V1's 2.0 s, V3's 2.0 s and the frame rate are recorded as
  such.
- **A setting not traceable to its data** is treated as set on A3.

## 5. The report

`reports/DISPLAY_PROVENANCE_2026-09-30.md` gives:
- (a) and (b);
- the spread curve;
- the trace table;
- the exact label wording for the A3 lock and the A3 dot error.
