# Addendum E: `idle` is not a valid null. `grid` is. This corrects addendum C

**Written 2026-09-23 09:30 SAST, after id12 ran and before any id12 figure is quoted in the report
or the freeze.** It corrects a null-choice made in addendum C, and it was found by the structural
auditor rather than by reading the headline.

---

## 1. How it was found

`pipeline/identify/audit_results.py` flags a discrimination AUC that sits systematically below
chance, because that means the classes are inverted: the null is carrying the signal it is supposed
to lack. On id12's completed run it raised exactly one flag:

    DISCRIMINATION_BELOW_CHANCE: M1_auc_vs_idle (43/45 below 0.5)

## 2. What the measurement says

Band-(a) motion envelope, standard deviation, on one recording:

| window class | envelope std | reading |
|---|---|---|
| **walk pass** | **1.2784** | the reference |
| **grid, a cell dwell** | **0.5711** | genuinely still, less than half the walk |
| idle, early in the recording | 0.6682 | quiet |
| idle, middle | 0.9872 | moving |
| **idle, late** | **1.3442** | **MORE motion than a walk pass** |

**`idle` is not stationary.** It is the room between passes, and between passes the participant
walks back to the start, the operator moves, and the next pass is set up. Late in a recording it
carries more motion energy than the walking it is supposed to be a null for.

And the AUC agrees across every chain:

| chain | AUC vs GRID | AUC vs IDLE |
|---|---|---|
| C0 raw | 0.5210 | 0.4673 |
| C0-C3 | 0.5579 | 0.4571 |
| C0-C6 | 0.5298 | 0.4325 |

The grid column sits above chance and the idle column below it, at every stage.

## 3. The correction

**Addendum C made M1 a two-null metric, `idle` and `grid`, reported separately and never pooled.
Reporting them separately is what made this visible, and the separation stands. What changes is
that `idle` is now declared INVALID as a stationary null and is excluded from every M1 claim.**

- **M1 is reported against `grid` alone**, the cell dwells, which are genuinely still: exactly five
  windows per cell, and a span never crosses a cell boundary.
- **`idle` is still computed and still reported**, labelled as what it is: a mixed
  between-passes class containing motion. It is useful as a description of the recording and it
  supports no claim.
- R1 already gates on M1 against both nulls. Since no stage is signal-vital on either, this
  correction does not change any R1 verdict. It is made because the next stage might have leaned
  on the idle column, not because this one did.

## 4. What this costs, stated plainly

**M1 now rests on a null of 4.0 s spans**, the cell-dwell length, where a walk pass is 9 s. That is
the only genuinely static reference this data contains. There is no empty-room capture and no
dedicated dwell recording, which addendum C already established.

**For DC2 this is the third independent argument for the standing block**, and it should not be
traded away: 20 s of standing per participant per block, recorded deliberately, gives a null that
is both genuinely still and long enough to match a full pass. DC1 has neither.

## 5. What does not change

M2 to M5, every conditioning stage, the arms, the heads, the nine pairings, the speed policy and
R1 to R7 are untouched. This addendum changes which null M1 may be claimed against, and nothing
else.
