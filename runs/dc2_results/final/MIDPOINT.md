## MIDPOINT

| test | model | committed | display lock | scorer lock | edges committed (E_col1/E_col5/E_row1/E_row5) | edges display lock |
|---|---|---|---|---|---|---|
| A3 | mid_A3@relgateU | 83.33 [76.67, 90.00] | 62.50 [53.33, 70.83] | 65.83 [57.48, 74.17] | 50 / 50 / 100 / 83 | 50 / 67 / 67 / 67 |
| A3 | baseline ph_A3 (A) | 88.33 [82.50, 94.17] | 65.00 [56.67, 73.33] | 69.17 [60.83, 77.52] | 33 / 100 / 100 / 100 | 17 / 100 / 33 / 100 |
| B2 (A) | mid_B2@relgateU | 87.50 [81.67, 93.33] | 47.50 [37.50, 56.67] | 51.67 [41.67, 60.02] | 100 / 100 / 100 / 100 | 100 / 50 / 17 / 33 |
| B2 (A) | baseline ph_B2 (A) | 57.50 [49.17, 66.67] | 20.83 [13.33, 29.17] | 20.83 [13.33, 29.17] | 100 / 83 / 50 / 17 | 50 / 33 / 17 / 17 |
| B2 (B) | mid_B2@relgateU+cfgBn | 87.50 [81.67, 93.33] | 47.50 [37.50, 56.67] | 51.67 [41.67, 60.02] | 100 / 100 / 100 / 100 | 100 / 50 / 17 / 33 |
| B2 (B) | baseline ph_B2 (B) | 65.83 [57.50, 74.17] | 30.00 [21.67, 38.33] | 33.33 [25.00, 41.67] | 100 / 100 / 83 / 33 | 67 / 33 / 17 / 17 |

Paired against the split baseline on the same passes (points, 95% interval):

| test | committed | display lock | scorer lock |
|---|---|---|---|
| A3 | -5.00 [-10.83, 0.00] | -2.50 [-12.50, 6.69] | -3.33 [-13.33, 6.67] |
| B2 (A) | +30.00 [20.83, 40.00] | +26.67 [16.67, 35.00] | +30.83 [22.48, 39.17] |
| B2 (B) | +21.67 [12.50, 30.83] | +17.50 [6.67, 26.67] | +18.33 [9.17, 26.67] |

Resolution of the drawn dot (m): median / 90th percentile.

| test | overall | walks with a correct lock | along the line, on the true line |
|---|---|---|---|
| A3 | 0.78 / 3.55 | 0.43 / 1.14 | 0.38 / 1.04 |
| B2 (A) | 1.24 / 4.24 | 0.51 / 1.16 | 0.47 / 1.03 |
| B2 (B) | 1.24 / 4.24 | 0.51 / 1.16 | 0.47 / 1.03 |

Reference: the split baseline A3 88.33 / 65.00; B2 57.50 / 20.83; calibrated 65.83 / 30.00. The frozen reference on B2: 50.00 / 12.50.
