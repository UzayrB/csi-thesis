# Pre-registration: the start region from the pre-press windows

Written 2026-09-21, 11:50 SAST, **before any of the arms below were run**. Operator approved with
amendments A to G, which are folded in and marked where they apply.

---

## A. TIME BOX

DC2 is 26 and 27 September in a different room, and preparing it takes priority. **Everything in
this document stops at end of day 2026-09-21 whatever state it is in.** What is measured by then
is reported; nothing half-built carries into DC2 week. A stage that has not produced a satisfied
contract by the stop is recorded as not run, not as pending.

---

## 1. The claim under test

The two seconds before the first press are not in any training set. Every head on record was
trained on `(rec.mode == "walk") & np.isfinite(rec.xy).all(1)` at `pipeline/constrained/dataset.py:121`.
Measured across all eighteen recordings: **1440 pre-press windows, exactly 4 per pass, every one
labelled `walk_edge`, and not one carrying a finite `xy`.** So the model has never seen a
participant outside the grid.

The claim is that those windows carry the **start region**, which is a coarser question than the
line and one the geometry ought to make easy, because the eight regions are up to 7 m apart.

`p2_prepress` already measured the **line** from these windows at chance: 9.17 percent, CI
[7.69, 12.31], against 8.33. It never measured the region. That is the gap this work addresses.

## 2. Why it would be worth having

On the shipped arm over nine pairings and 1080 passes (`q4_arms`, which predates the causal exit,
so these are **headroom sizing and are not quotable figures**):

| | count | share of errors |
|---|---|---|
| wrong line | 436 | |
| of those, a line starting in a **different region** | **359** | **82.3 percent** |
| of those, a reversal of the true line | 27 | 6.2 percent |

The region-to-line map, with its own arithmetic:

| region | lines starting there | share of passes |
|---|---|---|
| SW | C_fwd, E_col1, E_row1 | 20.0 percent |
| NW | D_fwd, E_row5 | 15.0 percent |
| SE | D_rev, E_col5 | 15.0 percent |
| NE | C_rev | 10.0 percent |
| S_mid | A_fwd | 10.0 percent |
| N_mid | A_rev | 10.0 percent |
| W_mid | B_fwd | 10.0 percent |
| E_mid | B_rev | 10.0 percent |

Perfect region knowledge leaves 1.83 candidate lines on average and 3 at worst, taking effective
chance from 8.3 to 54.5 percent.

## 3. The warning that shapes the whole plan

In the same `q4_arms` table, A2 at weight 1.0 makes wrong-region errors **worse**: 421 against 359
at weight 0.5. A strong prior on a region the classifier gets wrong more than half the time costs
more than it buys. **The gain is bounded by classifier accuracy**, and the shipped weight of 0.5 is
a hedge against a weak one. That is why the ceiling is measured before anything is built.

---

## B. THE CORRECTED CHANCE LEVEL, APPLIED RETROSPECTIVELY

`q3_startclf` reports `chance_pct: 12.5`, which is uniform over eight regions. **The classes are
not uniform.** SW holds 20.0 percent of passes, NW and SE 15.0 each, and the five single-line
regions 10.0 each. The honest baseline is the majority class:

> **The baseline for the start-region task is 20.0 percent, not 12.5 percent.**

This changes A3's earlier verdict and the change is **restated here rather than quietly amended**:

- A3's pre-registered bar was **twice chance**. Against the understated 12.5 percent that read as
  25 percent. Against the correct 20.0 percent baseline the bar should have been **40 percent**.
- Edge midpoints at **61.8 percent** clear the corrected bar.
- **Corners at 36.6 percent do not clear the corrected bar.** Under the bar as it should have been
  set, the corners group fails.
- A3's overall 46.7 percent is still above the corrected 20.0 percent baseline, so the classifier
  is not vacuous, but it clears its own bar on the edge midpoints alone.
- **The shipped A1 + A2_0.5 arm does not depend on A3's bar.** It was selected on its own paired
  improvement on the held-out folds, which is unaffected by how chance was stated. Nothing shipped
  rests on the understated figure.

Carried into `reports/SEMIBOUNDED_STATE.md` and the report sections in the same words.

---

## C. STEP 0, THE ORACLE CEILING

Run before anything is built. No new training and no decoder change: `start_terms()` already emits
`{session|stem|pass_id: {line: log offset}}`, so the oracle is a dict substitution.

**Arms.** The true start region supplied as the A2 term at weights 0.5, 1.0, 2.0 and 4.0, plus a
hard arm that forbids entry to every line starting outside the true region. Alongside them, a
**calibrated oracle**: a simulated classifier of accuracy *a* in {0.4, 0.6, 0.8} at the shipped
weight 0.5, which answers the decision-relevant question directly, namely how accurate a real
classifier must be before it buys anything at all.

**Reported per region as well as pooled (amendment C).** A ceiling carried by SW alone is not a
ceiling worth chasing, so the oracle's gain is broken out by true start region.

**Stopping rule, pre-registered.** If the oracle's best weight buys **fewer than 5 points** of
line accuracy on the held-out folds, stop and report the ceiling as the finding. Steps 1 to 3 do
not run.

## D. STEPS 1 TO 3

### Step 1, the pre-press region head

**Labels are free.** Each pass's true start region applies to its own 4 pre-press windows. No new
ground truth is needed.

**Causality.** Windows whose END is at or before the first press. `AFTER_S = 0`, **asserted in
`tests/test_prepress_is_causal.py` in the style of `test_display_is_causal.py`** (amendment D).
The 4 windows are 2 s wide on a 0.5 s stride and cover a 3.5 s span. Measured after the fact over
all 360 passes, that span ends a median 0.282 s BEFORE the press and begins a median 3.782 s
before it: the lattice does not align with the press, so it neither reaches the press nor reaches
back a full 4 s.

**Grouping.** The 4 windows of a pass overlap by 1.5 s, so the effective sample is **240 passes per
cross-day training pairing, not 960 windows**. Every split is **grouped by pass, never by window,
and the grouping is asserted** (amendment D). That is about 30 passes per class.

**Baseline to beat: 20.0 percent**, per amendment B.

**Arms, cheapest first.**

| arm | what it is | why it is ordered here |
|---|---|---|
| A | the existing A3 classifier re-fitted with `AFTER_S = 0` | free, no training, settles whether the current features carry region before the press |
| B | `LinkNet.embed()` with the encoder frozen, linear head on top | a linear head on 240 grouped samples is defensible |
| C | fine-tune the encoder on the 8-class region task | overfits easily at 30 passes per class, so it runs last and only on evidence |

**Reported: the full 8 by 8 region confusion matrix**, not only per-region recall (amendment D).
The argument for this work is that regions metres apart should not be confused, so the matrix is
the evidence for or against it.

### Step 2, substitution

Another participant's CSI over the same windows must change the predicted region, under the
**generalised rule with the ceiling computed from the actual substitution pairs used, never
assumed**, applied **to the region prediction itself** (amendment D). A component is signal-driven
only if swapping the CSI changes its answer.

### Step 3, the previous-pass confound

The walker approaches from wherever the previous pass ended, so a head that scores well may be
reading where they came from rather than where they are. Both are radio, so it is not cheating,
but it is protocol-dependent and a deployment without a fixed pass order would not have it.

Reported as a split on whether the previous pass's end region equals this pass's start region,
**and as the share of passes for which that is true** (amendment D), either way.

## E. SHIP RULE AND KILL RULE

**Ships only if** the paired improvement interval on the **held-out folds** is entirely above zero.
Selection on the two selection folds only, `s01_to_s02` and `s02_to_s01`. Both the difference of
medians and the median of paired deltas reported. **A2's weight re-swept with the real classifier**,
not left at 0.5 and not taken from the oracle's best.

**Kill rule.** If Arm A and Arm B both fail to beat the 20.0 percent baseline with a lower bound
above it, **stop before Arm C and report the negative**. Given the geometry argument, a negative
here is a publishable finding and is written up either way.

---

### OUTCOME, 2026-09-22: the rule fired, and the operator declined it

> **THE RULE'S VERDICT, printed as the rule gave it: `add_0.5` SHIPS.** Its paired improvement
> interval on the seven held-out folds is **[0.24, 1.07]**, entirely above zero, and the guard
> passes. Under the rule as pre-registered above, that is a ship.
>
> **THE OPERATOR DECLINED TO SHIP IT.**
>
> **THIS OVERRIDE IS POST HOC.** It was decided after the data was seen, and it is named post hoc
> in those words rather than dressed up as the rule having been followed.

**The grounds, as given by the operator:**

1. The effect is **five passes in 840**. Held-out deltas: +0.83, +0.83, +1.67, +0.83, 0, 0, 0.
2. Per-pairing rates move in **0.833-point steps** at 120 passes a pairing, so **+0.83 is one pass**.
3. **No weight gradient**: 0.25, 0.5 and 1.0 all return +0.83.
4. **A bootstrap over seven non-negative deltas excludes zero regardless of effect size.** Four
   held-out pairings rose, three were flat, none fell; the interval reports sign consistency, not
   magnitude.

**The shipped arm remains A1 + A2_0.5. Nothing was rendered, nothing was frozen, and the headline
figure is unchanged at 62.50 percent.**

### THE STANDING SHIP RULE IS AMENDED, and that amendment is itself post hoc

For **all future analyses, DC2 included**, the rule above is superseded by:

> An arm ships only if **(a)** its paired improvement interval on the held-out folds is entirely
> above zero, **(b)** the median paired delta is at least **two passes per pairing**, which is
> **1.67 points** at 120 passes a pairing, and **(c)** the effect shows a **monotone response to
> the term's own weight**.

**Recorded as a rule change made after seeing that condition (a) alone can fire at the resolution
floor**, which is exactly what `t5_shipc` demonstrated. Conditions (b) and (c) would each have
caught `add_0.5` on their own. The canonical copy lives in `reports/SEMIBOUNDED_STATE.md` section
10; full working in `reports/PREPRESS_REGION_REPORT_2026-09-21.md` section 9.

## F. IF IT SHIPS  —  NOT TRIGGERED, see the outcome above

One render, one freeze superseding the current one, and the headline semi-bounded figure
re-measured over nine pairings with its interval. **If it does not ship, change nothing and do not
re-render.**

## G. FOR DC2

Whatever the outcome, `reports/DC2_PROTOCOL_2026-09-18.md` gains a note: **the approach walk before
each press should be recorded and its start region labelled**, so the next room's data can train
this properly rather than having it retrofitted.

---

## What this deliberately does not reopen

- **The extended chain into the run-up.** Measured in `p3_direction`, shipped nothing, paired delta
  0.0 points with CI [-0.36, +0.36].
- **A direction prior from the run-up.** Same stage, three weights, same result.
- **The display lead-in.** Measured negative, within 0.5 m fell 38.6 to 20.2 percent.
- **Emissions and the transition model.** The A2 route needs no decoder change at all.

## Standing rules this work runs under

`data/` is read only. `testing/` is never imported. Frozen artefacts are never overwritten. The
pairing key is `session|stem|pass_id`. Completion is decided by output contracts, not exit codes.
No decision rests on a single pairing. British spelling. No em dashes.
