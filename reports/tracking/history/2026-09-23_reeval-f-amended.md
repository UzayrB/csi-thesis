# Every arm refused since 2026-09-22, re-evaluated under the amended condition (f)

2026-09-23, batch 23d, item 1. **The amendment is the operator's decision and it is POST HOC, in
those words** (`reports/SEMIBOUNDED_STATE.md` section 10):

> an arm passes (f) if the four edge lines' combined change in correct walks is zero or positive,
> AND no single edge line loses more than TWO walks.

**Applied uniformly, no cherry-picking.** 44 rows: every arm and every weight refused since
2026-09-22 that has a results file. **Only (f) is re-read**; (a), (b), (c) and substitution are
each stage's own verdict from its own results file, so nothing but the amendment moves. Edge
changes are in WALKS on each stage's own evaluation set: 54 per line over nine pairings, 42 over
the held-out seven for `u2_useit` and `u3_trackeradapt`. Intervals recomputed here use the project
bootstrap (`night_common.boot_ci`, 1000 resamples, seed 0) on the per-pairing deltas; where a stage
stored its own interval, that one is shown. Computed by `pipeline/constrained/d1_reeval.py` into
`runs/constrained/fh/d1_reeval/results.json`.

## The answer

**Two arms pass every condition under the amended (f):**

1. **`y2_dial`, the lock estimator mix, at w = 0.10, 0.15, 0.20 and 0.25.** This is the ONLY arm the
   amendment changes. Its edge lines net 0 walks with a worst loss of one (E_row1). **The
   pre-registered selection rule, "the largest w meeting (f)", now selects w = 0.25**: held-out
   **+4.05 [2.26, 6.67]**, median 3 walks per pairing, a non-flat monotone gradient, substitution
   0.862. It was measured on the grid lattice at the causal index horizon; it is re-measured on the
   press-aligned lattice in item 3 before anything ships.
2. **`a_veto_1.0`**, which passed every condition on 2026-09-22 and was DECLINED BY JUDGEMENT, on
   multiple testing across eleven arms, not by a rule. The amendment does not change it.

**Every other arm still fails on a condition the amendment does not touch**, or fails the amended
(f) itself:

- **product fusion on the committed answer at w = 0.25 now passes (f)** (net +5, worst -1) but
  fails its pre-registered (c): the committed gain is not monotone in w. Item 3 re-runs it with w
  chosen on the selection folds, where (c) as clarified permits an interior optimum;
- **switching** (both K) fails the amended (f) on its two-walk floor: E_col5 loses 3;
- **every lock arm of t7, t9 and product fusion** collapses the edge lines far past the floor;
- `b_abstain_0.25` and the other coarse and abstain arms fail (c); `c_coarse_0.25` and
  `c_coarse_0.5` now pass (f) but fail (c);
- the edge pool head (`x2`) passes the amended (f) on the lock and fails (a), with its interval
  entirely below zero.

## The table

| stage | arm | decision | paired held-out [95%] | (a) | (b) | (c) | subs | edge walks E_col1 / E_col5 / E_row1 / E_row5 | net | (f) old | (f) amended | passes all now |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `t7_lockarms` | E_chain_total | lock | +5.83 [2.50, 11.79] | yes | yes | **no** | yes | -7 / -11 / -6 / -12 | -36 | fail | fail | no |
| `t7_lockarms` | E_chain_total_no_prior | lock | +3.33 [0.60, 7.14] | yes | yes | **no** | yes | +0 / -4 / -3 / -6 | -13 | fail | fail | no |
| `t7_lockarms` | E_no_marginal | lock | +1.67 [-0.95, 5.60] | **no** | **no** | **no** | yes | -23 / -23 / -14 / -27 | -87 | fail | fail | no |
| `t7_lockarms` | E_both | lock | +4.17 [0.71, 8.57] | yes | yes | **no** | yes | -23 / -27 / -16 / -28 | -94 | fail | fail | no |
| `t9_lengthnorm` | raw_chain_total | lock | +3.33 [0.60, 7.14] | yes | yes | yes | yes | +0 / -4 / -3 / -6 | -13 | fail | fail | no |
| `t9_lengthnorm` | N_per_step | lock | +3.33 [0.60, 7.14] | yes | yes | yes | yes | +0 / -4 / -3 / -6 | -13 | fail | fail | no |
| `t9_lengthnorm` | N_per_state | lock | +3.33 [0.60, 7.14] | yes | yes | yes | yes | +0 / -4 / -3 / -6 | -13 | fail | fail | no |
| `t9_lengthnorm` | N_per_metre | lock | +3.33 [0.83, 7.38] | yes | yes | yes | yes | +0 / -4 / -3 / -6 | -13 | fail | fail | no |
| `u2_useit` | a_veto_0.25 | committed | +0.00 [0.12, 1.31] | **no** | **no** | yes | yes | +0 / +0 / +0 / +0 | +0 | pass | **pass** | no |
| `u2_useit` | b_abstain_0.25 | committed | +2.50 [0.71, 6.07] | yes | yes | **no** | yes | +0 / +0 / +1 / +1 | +2 | pass | **pass** | no |
| `u2_useit` | c_coarse_0.25 | committed | +2.50 [1.31, 6.19] | yes | yes | **no** | yes | +0 / +1 / +1 / +5 | +7 | pass | **pass** | no |
| `u2_useit` | a_veto_0.5 | committed | +0.83 [0.36, 2.26] | yes | **no** | yes | yes | +0 / +0 / +0 / +0 | +0 | pass | **pass** | no |
| `u2_useit` | b_abstain_0.5 | committed | +3.33 [-0.12, 5.48] | **no** | yes | **no** | yes | +0 / +0 / +0 / -3 | -3 | fail | fail | no |
| `u2_useit` | c_coarse_0.5 | committed | +2.50 [1.19, 6.31] | yes | yes | **no** | yes | +0 / +1 / +0 / +5 | +6 | pass | **pass** | no |
| `u2_useit` | a_veto_1.0 | committed | +1.67 [0.60, 5.00] | yes | yes | yes | yes | +0 / +0 / +1 / +1 | +2 | pass | **pass** | **YES** |
| `u2_useit` | b_abstain_1.0 | committed | +0.83 [-3.33, 2.02] | **no** | **no** | **no** | yes | +0 / -4 / -1 / -9 | -14 | fail | fail | no |
| `u2_useit` | c_coarse_1.0 | committed | +1.67 [-0.95, 5.48] | **no** | yes | **no** | yes | +0 / -3 / +0 / +3 | +0 | fail | fail | no |
| `u2_useit` | e_balanced_veto_0.5 | committed | +0.83 [0.12, 2.38] | yes | **no** | yes | yes | +0 / +0 / +0 / +1 | +1 | pass | **pass** | no |
| `u2_useit` | e_balanced_abstain_0.5 | committed | +3.33 [-0.36, 4.88] | **no** | yes | yes | yes | +0 / +0 / +0 / -5 | -5 | fail | fail | no |
| `u3_trackeradapt` | adapted | committed | -8.81 [-15.72, -2.38] | **no** |  |  |  | -7 / -15 / +2 / -11 | -31 | fail | fail | no |
| `x2/x3_edgepool` | edge100 | lock |  | **no** | **no** |  | **no** | +1 / -1 / +3 / +0 | +3 | fail | **pass** | no |
| `y2_dial` | w_0.05 | lock | +0.95 [0.36, 1.67] | yes | **no** | yes | yes | +0 / +1 / -1 / +1 | +1 | fail | **pass** | no |
| `y2_dial` | w_0.10 | lock | +2.38 [0.95, 3.93] | yes | yes | yes | yes | +0 / +1 / -1 / +0 | +0 | fail | **pass** | **YES** |
| `y2_dial` | w_0.15 | lock | +2.86 [1.67, 4.17] | yes | yes | yes | yes | +0 / +1 / -1 / +0 | +0 | fail | **pass** | **YES** |
| `y2_dial` | w_0.20 | lock | +3.57 [1.79, 5.83] | yes | yes | yes | yes | +0 / +1 / -1 / +0 | +0 | fail | **pass** | **YES** |
| `y2_dial` | w_0.25 | lock | +4.05 [2.26, 6.67] | yes | yes | yes | yes | +0 / +1 / -1 / +0 | +0 | fail | **pass** | **YES** |
| `y3_switch` | K1_t3 | drawn line after the lock | +4.05 [0.87, 8.08] | yes | yes | yes | yes | +5 / -3 / +12 / +1 | +15 | fail | fail | no |
| `y3_switch` | K2_t3 | drawn line after the lock | +4.10 [0.89, 8.09] | yes | yes | yes | yes | +6 / -3 / +15 / +1 | +19 | fail | fail | no |
| `z3` | A_link_product_w0.25 | lock | +8.93 [4.76, 12.62] | yes | yes | **no** | yes | -7 / -10 / +0 / -5 | -22 | fail | fail | no |
| `z3` | A_link_product_w0.5 | lock | +10.95 [5.48, 16.07] | yes | yes | **no** | yes | -13 / -17 / -2 / -9 | -41 | fail | fail | no |
| `z3` | A_link_product_w0.75 | lock | +10.48 [5.60, 15.12] | yes | yes | **no** | yes | -16 / -21 / -2 / -13 | -52 | fail | fail | no |
| `z3` | A_link_product_w1.0 | lock | +9.29 [5.00, 13.69] | yes | yes | **no** | yes | -20 / -25 / -2 / -13 | -60 | fail | fail | no |
| `z3` | A_link_product_w0.25 | committed | +11.07 [5.24, 18.21] | yes | yes | **no** | yes | -1 / +2 / +1 / +3 | +5 | fail | **pass** | no |
| `z3` | A_link_product_w0.5 | committed | +10.83 [4.05, 18.10] | yes | yes | **no** | yes | -4 / -2 / -1 / +3 | -4 | fail | fail | no |
| `z3` | A_link_product_w0.75 | committed | +10.12 [2.74, 17.86] | yes | yes | **no** | yes | -5 / -7 / -3 / +2 | -13 | fail | fail | no |
| `z3` | A_link_product_w1.0 | committed | +9.64 [2.14, 17.86] | yes | yes | **no** | yes | -7 / -9 / -4 / +1 | -19 | fail | fail | no |
| `z3` | B_g100_native_w0.25 | lock | -0.12 [-0.71, 0.60] | **no** | **no** | **no** | yes | +1 / +0 / +0 / +0 | +1 | pass | **pass** | no |
| `z3` | B_g100_native_w0.5 | lock | +0.36 [-0.83, 1.67] | **no** | **no** | **no** | yes | -2 / +0 / -1 / +0 | -3 | fail | fail | no |
| `z3` | B_g100_native_w0.75 | lock | +0.95 [-0.60, 2.62] | **no** | **no** | **no** | yes | -3 / -1 / -2 / -1 | -7 | fail | fail | no |
| `z3` | B_g100_native_w1.0 | lock | +1.55 [0.12, 2.98] | yes | **no** | **no** | yes | -4 / +0 / -2 / -2 | -8 | fail | fail | no |
| `z3` | B_g100_native_w0.25 | committed | +0.60 [0.24, 1.07] | yes | **no** | **no** | yes | +0 / +0 / +0 / +0 | +0 | pass | **pass** | no |
| `z3` | B_g100_native_w0.5 | committed | +0.48 [-0.12, 0.95] | **no** | **no** | **no** | yes | +0 / +0 / +0 / +1 | +1 | pass | **pass** | no |
| `z3` | B_g100_native_w0.75 | committed | +0.83 [0.12, 1.55] | yes | **no** | **no** | yes | +0 / +0 / +0 / +1 | +1 | pass | **pass** | no |
| `z3` | B_g100_native_w1.0 | committed | +1.07 [0.12, 2.02] | yes | yes | **no** | yes | +0 / +0 / +0 / +0 | +0 | pass | **pass** | no |

Blank (a) to (c) or substitution cells are conditions the stage never reached or never measured;
a condition not measured counts as NOT met.


## OPERATOR DECISION, 2026-09-23 (batch 23e, item 5): `y2_dial` STAYS REFUSED

Recorded in the operator's words: "y2_dial stays refused. Record it; do not re-measure." It was refused on the
ONE lattice by one edge walk (E_row1 -1, net -1) at `sd_scale` 1.0, and the drawn-lock correction
(`reports/CORRECTION_drawn_lock_2026-09-23.md`) left open whether the drawn decode would change that.
**It is not re-measured.** The open item is closed by decision, not by a measurement.
