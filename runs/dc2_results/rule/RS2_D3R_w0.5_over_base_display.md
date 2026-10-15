### RS2_D3R_w0.5_over_base: d2pc_ar@CR.relgateU+abstain+a2w0.25+w0.5 against d2pc_ar@CR.relgateU+abstain+a2w0.25 (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 55.00 | 28.33 | 39.17 | 36.67 | -7.50 (-19 / +10 passes) |
| A2 | x1 | 83.33 | 62.50 | 35.00 | 64.17 | -46.67 (-58 / +2 passes) |
| A1 | x1 | 60.00 | 37.50 | 27.50 | 37.50 | -32.50 (-39 / +0 passes) |

Objective (weighted mean of committed + lock): base 102.50, arm 78.96.
Paired gain -23.54 points, 95% interval [-31.67, -15.20], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 67 / 61 / 83 / 56; arm 39 / 17 / 22 / 39
- lock: base 56 / 33 / 50 / 28; arm 6 / 0 / 22 / 0
- guard FAILS: [{'what': 'committed', 'line': 'E_col5', 'base': 61.111111111111114, 'arm': 16.666666666666664}, {'what': 'committed', 'line': 'E_row1', 'base': 83.33333333333334, 'arm': 22.22222222222222}, {'what': 'lock', 'line': 'E_col1', 'base': 55.55555555555556, 'arm': 5.555555555555555}, {'what': 'lock', 'line': 'E_col5', 'base': 33.33333333333333, 'arm': 0.0}, {'what': 'lock', 'line': 'E_row1', 'base': 50.0, 'arm': 22.22222222222222}, {'what': 'lock', 'line': 'E_row5', 'base': 27.77777777777778, 'arm': 0.0}]

**Decision: KEEP BASE.**
