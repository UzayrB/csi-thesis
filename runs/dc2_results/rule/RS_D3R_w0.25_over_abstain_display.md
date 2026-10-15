### RS_D3R_w0.25_over_abstain: d2pc_ar@CR.relgateU+abstain+w0.25 against d2pc_ar@CR.relgateU+abstain (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 52.50 | 28.33 | 50.00 | 38.33 | +7.50 (-3 / +12 passes) |
| A2 | x1 | 84.17 | 62.50 | 53.33 | 66.67 | -26.67 (-37 / +5 passes) |
| A1 | x1 | 56.67 | 37.50 | 34.17 | 40.83 | -19.17 (-27 / +4 passes) |

Objective (weighted mean of committed + lock): base 100.62, arm 92.92.
Paired gain -7.71 points, 95% interval [-14.80, 0.21], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 67 / 61 / 83 / 56; arm 50 / 33 / 50 / 44
- lock: base 56 / 33 / 50 / 28; arm 11 / 11 / 22 / 0
- guard FAILS: [{'what': 'lock', 'line': 'E_col1', 'base': 55.55555555555556, 'arm': 11.11111111111111}, {'what': 'lock', 'line': 'E_col5', 'base': 33.33333333333333, 'arm': 11.11111111111111}, {'what': 'lock', 'line': 'E_row1', 'base': 50.0, 'arm': 22.22222222222222}, {'what': 'lock', 'line': 'E_row5', 'base': 27.77777777777778, 'arm': 0.0}]

**Decision: KEEP BASE.**
