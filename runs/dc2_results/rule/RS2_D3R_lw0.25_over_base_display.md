### RS2_D3R_lw0.25_over_base: d2pc_ar@CR.relgateU+abstain+a2w0.25+lw0.25 against d2pc_ar@CR.relgateU+abstain+a2w0.25 (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 55.00 | 28.33 | 55.00 | 38.33 | +10.00 (+0 / +12 passes) |
| A2 | x1 | 83.33 | 62.50 | 83.33 | 66.67 | +4.17 (+0 / +5 passes) |
| A1 | x1 | 60.00 | 37.50 | 60.00 | 40.83 | +3.33 (+0 / +4 passes) |

Objective (weighted mean of committed + lock): base 102.50, arm 109.38.
Paired gain +6.88 points, 95% interval [1.87, 11.88], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 67 / 61 / 83 / 56; arm 67 / 61 / 83 / 56
- lock: base 56 / 33 / 50 / 28; arm 11 / 11 / 22 / 0
- guard FAILS: [{'what': 'lock', 'line': 'E_col1', 'base': 55.55555555555556, 'arm': 11.11111111111111}, {'what': 'lock', 'line': 'E_col5', 'base': 33.33333333333333, 'arm': 11.11111111111111}, {'what': 'lock', 'line': 'E_row1', 'base': 50.0, 'arm': 22.22222222222222}, {'what': 'lock', 'line': 'E_row5', 'base': 27.77777777777778, 'arm': 0.0}]

**Decision: KEEP BASE.**
