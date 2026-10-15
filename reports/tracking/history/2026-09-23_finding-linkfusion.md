# Fusing the three links by product: the largest effect measured, refused as written

2026-09-23, batch 23c, item 3. Pre-registration `reports/PREREG_linkfusion_g100native_2026-09-23.md`
and its amendment 1. Stages `z3a_linkprod_w{0,025,05,075,1}`, `z3a_linkprod_T1`,
`z3b_g100native_w{025,05,075,1}`, evaluated by `pipeline/constrained/z3_eval.py` into
`runs/constrained/fh/z3_eval.json`. **Nothing was changed as a result of this document.**

---

## The finding in one line

**Replacing the arithmetic mean of the three link posteriors with their renormalised product lifts
the committed semi-bounded answer from 62.50 to 79.17 on the median of nine (held-out paired
+11.07, interval [5.24, 18.21]), and it is REFUSED under the rule as written: condition (c) is not
monotone, and condition (f) fails by one pass of E_col1 on the committed answer and by 5 to 25
passes per edge line on the lock.**

## The sweep, nine pairings, 1080 passes, held-out seven

Reproduction check passed: w = 0 returned the lock at 57.50 with edge 42.593 / 77.778 / 35.185 /
57.407 and the committed answer at 62.50.

| w | lock held-out | lock paired | lock edge passes E_col1 / E_col5 / E_row1 / E_row5 | committed held-out | committed paired | committed edge passes |
|---|---|---|---|---|---|---|
| 0 (shipped) | 57.50 | | | 75.00 | | |
| **0.25** | 67.50 | +8.93 | -7 / -10 / 0 / -5 | **80.83** | **+11.07 [5.24, 18.21]** | **-1** / +2 / +1 / +3 |
| 0.50 | 68.33 | +10.95 | -13 / -17 / -2 / -9 | 82.50 | +10.83 | -4 / -2 / -1 / +3 |
| 0.75 | 67.50 | +10.48 | -16 / -21 / -2 / -13 | 82.50 | +10.12 | -5 / -7 / -3 / +2 |
| 1.00 | 65.83 | +9.29 [5.00, 13.69] | -20 / -25 / -2 / -13 | 81.67 | +9.64 [2.14, 17.86] | -7 / -9 / -4 / +1 |

Committed answer, median of all nine: **62.50 to 79.17 at w = 0.25**, 78.33 at w = 1. Median gain
**8 passes per pairing**. Session-01 folds at w = 0.25: s0203_to_s01 31.67 to 49.17, s02_to_s01
30.00 to 39.17, s03_to_s01 25.83 to 38.33. **The session-01 folds, flat under every earlier arm, rise 9 to 18 points.** At w = 1, decision
substitution rises (more passes change their line on another participant's radio) and the
along-line substitution ratio rises from 0.26 to 0.40: the product is MORE driven by the radio, not
less.

## Which conditions fail, and by how much

- **(a) and (b) pass on both decisions at every weight.**
- **(c) fails on both:** the lock peaks at w = 0.5, the committed answer at w = 0.25.
- **(f) fails at every weight.** At the lock, heavily. On the committed answer at w = 0.25, by **one
  pass of E_col1** while E_col5, E_row1 and E_row5 gain six passes between them.

This is the third result this batch with the same shape as `y2_dial`: a per-line rule refusing a
change that nets positive across the edge lines. The operator has already ruled that (f) stands as
written, and this is recorded as a refusal.

## What the gain is made of: control T (amendment 1, added after seeing w = 1, stated as such)

A product of three posteriors is much SHARPER than their mean, and the null level (-7.50 nats) and
gate were fitted to the mean's scale. Control T sharpens the mean itself (`p_mean ** 3`, no
cross-link information) and recovers **48 percent** of arm A's committed gain: +4.64, interval
[-0.60, 9.88], which includes zero; lock +2.62 [-0.24, 5.00]; and it damages the edge lines MORE
than A does (lock E_row5 -27 passes).

**Reading, as pre-registered:** about half of arm A's committed gain is emission SCALE against
Room A's fitted constants, and about half is the three links agreeing, which sharpening alone
cannot supply. The scale half is consistent with `HANDOFF_2026-09-22` open item 2, the null level
scoring higher when less negative (65.00 at -6.0, 67.50 at -4.5), which was refused as test-set
fitting. **Both halves bear on DC2**: the null and gate are refit there by protocol, and the link
agreement half is a property of the sensing that ought to travel.

## What is not claimed

- No arm ships and the 62.50 headline stands. The 79.17 is a measured refused arm, not a result
  this project can quote as its performance.
- The w grid was chosen before the run; w = 0.25 being the committed optimum is where the curve
  fell, not a selection. Choosing it now for a ship would be selecting on the held-out folds.
- **Arm B (g100 at native 0.5 m) is small and refused**: committed at most +1.07 [0.12, 2.02],
  non-monotone, lock (b) and (f) fail. Its along-line substitution ratio rises only to 0.29.

## For the operator

If the edge-line rule were to be revisited for this one change, it would be a rule changed after
seeing data and POST HOC in those words, and the pre-registration for DC2 is the honest place to
test it instead: a product-fusion arm frozen now, applied once to Room B, with (f) as written.
