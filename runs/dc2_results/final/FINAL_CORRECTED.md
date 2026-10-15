## FINAL_CORRECTED

| test | model | committed | display lock | scorer lock | edges committed (E_col1/E_col5/E_row1/E_row5) | edges display lock |
|---|---|---|---|---|---|---|
| A3 | fin_A3@FC.relgateU+abstain+a2w0.25 | 93.33 [88.33, 97.50] | 70.83 [62.50, 79.17] | 70.00 [61.67, 78.33] | 67 / 100 / 100 / 100 | 50 / 100 / 83 / 83 |
| A3 | baseline ph_A3 (A) | 88.33 [82.50, 94.17] | 65.00 [56.67, 73.33] | 69.17 [60.83, 77.52] | 33 / 100 / 100 / 100 | 17 / 100 / 33 / 100 |
| B2 (A) | fin_B2@FC.relgateU+abstain+a2w0.25 | 93.33 [88.33, 97.50] | 72.50 [63.33, 80.00] | 71.67 [62.50, 79.19] | 100 / 100 / 100 / 100 | 100 / 100 / 50 / 50 |
| B2 (A) | baseline ph_B2 (A) | 57.50 [49.17, 66.67] | 20.83 [13.33, 29.17] | 20.83 [13.33, 29.17] | 100 / 83 / 50 / 17 | 50 / 33 / 17 / 17 |

Paired against the split baseline on the same passes (points, 95% interval):

| test | committed | display lock | scorer lock |
|---|---|---|---|
| A3 | +5.00 [0.00, 10.00] | +5.83 [-3.35, 15.00] | +0.83 [-7.50, 10.00] |
| B2 (A) | +35.83 [26.67, 45.00] | +51.67 [42.50, 60.83] | +50.83 [41.67, 59.17] |

Resolution of the drawn dot (m): median / 90th percentile.

| test | overall | walks with a correct lock | along the line, on the true line |
|---|---|---|---|
| A3 | 0.51 / 3.26 | 0.32 / 0.92 | 0.29 / 0.90 |
| B2 (A) | 0.53 / 2.83 | 0.37 / 0.90 | 0.35 / 0.85 |

Reference: the split baseline A3 88.33 / 65.00; B2 57.50 / 20.83; calibrated 65.83 / 30.00. The frozen reference on B2: 50.00 / 12.50.
