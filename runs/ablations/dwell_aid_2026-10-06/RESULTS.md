# Do the static dwells help the final walking tracker? Results

Arms: W, the final tracker's recipe (walking windows of A1, A2, B1); W+D, the same plus every A1 and A2 dwell window. Tested on A3 and B2 (never trained on), semi-constrained mode, the shipped decode (equal to the live app). Three seed sets (PLAN.md addendum, 6 October 20:12). W seed set 0 is byte-identical to the shipped tracker and reproduces its published A3 and B2 figures exactly.

## Per seed set (committed / lock, %; per-frame dot error median m)

| arm | seed set | A3 committed | A3 lock | A3 frame | B2 committed | B2 lock | B2 frame | pooled committed | pooled lock |
|---|---|---|---|---|---|---|---|---|---|
| W | 0 | 93.33 | 70.83 | 0.507 | 93.33 | 72.50 | 0.533 | 93.33 | 71.67 |
| W | 1 | 94.17 | 70.00 | 0.575 | 95.00 | 70.00 | 0.533 | 94.58 | 70.00 |
| W | 2 | 94.17 | 74.17 | 0.494 | 93.33 | 70.00 | 0.565 | 93.75 | 72.08 |
| W+D | 0 | 81.67 | 59.17 | 0.639 | 79.17 | 56.67 | 0.824 | 80.42 | 57.92 |
| W+D | 1 | 77.50 | 59.17 | 0.641 | 80.00 | 55.83 | 0.777 | 78.75 | 57.50 |
| W+D | 2 | 81.67 | 60.83 | 0.612 | 78.33 | 59.17 | 0.746 | 80.00 | 60.00 |

## Edge lines (committed / lock, %, 6 walks each)

| arm | seed set | A3 E_col1 | A3 E_col5 | A3 E_row1 | A3 E_row5 | B2 E_col1 | B2 E_col5 | B2 E_row1 | B2 E_row5 |
|---|---|---|---|---|---|---|---|---|---|
| W | 0 | 67 / 50 | 100 / 100 | 100 / 83 | 100 / 83 | 100 / 100 | 100 / 100 | 100 / 50 | 100 / 50 |
| W | 1 | 67 / 50 | 100 / 100 | 100 / 100 | 100 / 67 | 100 / 100 | 100 / 83 | 100 / 50 | 100 / 67 |
| W | 2 | 67 / 50 | 100 / 100 | 100 / 100 | 100 / 67 | 100 / 100 | 100 / 83 | 83 / 50 | 100 / 50 |
| W+D | 0 | 33 / 0 | 67 / 83 | 100 / 33 | 83 / 50 | 67 / 67 | 67 / 33 | 83 / 0 | 50 / 67 |
| W+D | 1 | 33 / 0 | 67 / 50 | 100 / 33 | 67 / 50 | 67 / 50 | 50 / 0 | 83 / 0 | 33 / 50 |
| W+D | 2 | 50 / 0 | 67 / 83 | 100 / 33 | 83 / 33 | 67 / 33 | 50 / 17 | 83 / 0 | 33 / 67 |

**W mean +- SD over 3 seed sets:** pooled committed 93.89 +- 0.64, pooled lock 71.25 +- 1.10.

**W+D mean +- SD over 3 seed sets:** pooled committed 79.72 +- 0.87, pooled lock 58.47 +- 1.34.

## Paired differences, W+D minus W (percentage points; 95 % t-interval over seed sets)

- **Primary, pooled committed-line error:** per seed set +12.92, +15.83, +13.75; mean +14.17 [+10.43, +17.90].

- lock_pct_pooled: mean -12.78 [-14.93, -10.62]
- committed_err_A3: mean +13.61 [+6.96, +20.27]
- committed_err_B2: mean +14.72 [+13.53, +15.92]
- frame_err_mean_pooled_m: mean +0.21 [+0.11, +0.30]

## Verdict under the rule fixed in PLAN.md: **dwells hurt**

