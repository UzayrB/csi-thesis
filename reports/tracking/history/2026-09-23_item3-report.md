# Item 3, batch 23d: product fusion on the committed decision, and the item-1 arms, on the ONE lattice

Pre-registration `reports/PREREG_committed_fusion_2026-09-23.md`, written before any press-aligned
fusion figure. Results `runs/constrained/fh/d3_eval/results.json`, from
`pipeline/constrained/d3_eval.py`. Every run on the ONE lattice, no root set by hand.

**What ships: `a_veto_1.0` on the committed decision. Product fusion does NOT ship, and neither does
`y2_dial`.**

## Reproduction and agreement

- w = 0 returned the committed answer at **74.17 held-out, 67.50 all nine**, exactly what
  `y4_pressalign` measured: PASSED.
- The fusion harness (`z3a_linkprod`) and the veto harness (`u2_useit`) score the committed answer
  identically: their shipped baselines agree on **all nine pairings to the decimal**, and the
  combined run's fusion-alone baseline agrees with `z3a` at w = 1 likewise. Only then is an
  interaction read.

## Product fusion, committed decision only

| w | selection-fold delta | held-out paired [95%] | median passes | all nine | edge walks E_col1 / E_col5 / E_row1 / E_row5 | net | amended (f) |
|---|---|---|---|---|---|---|---|
| 0.25 | +5.00 | +9.64 [5.47, 14.88] | 10 | 77.50 | -1 / 0 / +5 / -2 | +2 | pass |
| 0.50 | +4.58 | +9.64 [4.17, 15.60] | 10 | 79.17 | -5 / -5 / +1 / -1 | -10 | fail |
| 0.75 | +4.17 | +9.05 [4.05, 14.65] | 9 | 77.50 | -6 / -9 / 0 / 0 | -15 | fail |
| **1.00 = w\*** | **+6.25** | **+8.69 [3.10, 14.17]** | 10 | 76.67 | **-6 / -12 / -1 / -1** | **-20** | **fail** |

**The selection folds chose w\* = 1.0** (the largest selection-fold delta, as pre-registered). At w\*,
(a), (b), (c) as clarified and substitution PASS; **the amended (f) FAILS, net -20 walks with E_col5
down 12. The arm is REFUSED.**

**Stated plainly, because it is the uncomfortable fact of this item:** at w = 0.25 every condition
passes, amended (f) included (net +2, worst -2). It was not the pre-registered choice. Choosing it now
would be selecting on the held-out edge lines, which is exactly what the pre-registration forbids,
so it is not shipped. It is the operator's to decide, and a decision to take it would be POST HOC.

Session-01 folds at w\*: 30.00 to 45.00, 31.67 to 38.33, 30.83 to 39.17.

**The split (control T, the mean cubed, w = 1):** committed held-out +2.50 against A's +8.69, so
**29 percent sharpening, 71 percent link agreement** on the one lattice (48 / 52 on the grid).

## The item-1 arms, re-measured on the one lattice

- **`y2_dial` (the lock mix): does not ship.** Its reproduction check anchors on the one lattice's
  render lock (50.00, re-keyed per lattice and recorded as such). Held-out gains +0.71 to +4.05, but
  **no weight meets the amended (f)**: every weight loses one E_row1 walk and nets -1 or worse. The
  amendment's net-zero floor is what refuses it on this lattice.
- **`a_veto_1.0` (the pre-press veto on the committed decision): passes every condition.** Paired
  **+1.67 [0.24, 4.40]**, median **2 passes**, (c) monotone, substitution, amended (f) **net +4, worst 0**.
  Threshold 0.01 chosen on the selection folds. **It ships** on the operator's instruction to include
  a passing item-1 arm.
  **Its caveat, carried beside it:** exactly on the two-pass bar, and the two readings disagree in
  sign: held-out difference of medians **74.17 to 73.33 (-0.83)** against the paired **+1.67**; all
  nine 67.50 to 73.33. It was one of eleven arms scored on the same folds on 2026-09-22. DC2 tests it
  at a 97.5 percent interval (item 5).

## The interaction

`a_veto_1.0` with product fusion at w\* = 1.0: **+0.83 [0.24, 1.43] over fusion alone** (not worse:
the two add), **+9.52 [3.93, 15.12] over shipped**, but amended (f) fails (net -17). Not shipped,
because fusion at w\* is not shipped.

## Substitution

Decision substitution (committed line changing on another participant's radio) rises with fusion
(median +12 passes per pairing at w\*); along-line ratio 0.40 against 0.26 at w\*.
