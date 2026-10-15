### CR_D3_w1.0: d1sp@CR.w1.0 against d1sp@CR.ref (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 37.50 | 18.33 | 42.50 | 18.33 | +5.00 (+6 / +0 passes) |
| A2 | x1 | 74.17 | 45.00 | 37.50 | 65.00 | -16.67 (-44 / +24 passes) |
| A1 | x1 | 38.33 | 28.33 | 24.17 | 25.83 | -16.67 (-17 / -3 passes) |

Objective (weighted mean of committed + lock): base 74.38, arm 68.54.
Paired gain -5.83 points, 95% interval [-13.12, 1.67], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 72 / 50 / 78 / 33; arm 22 / 22 / 44 / 33
- lock: base 50 / 33 / 28 / 22; arm 0 / 11 / 6 / 0
- guard FAILS: [{'what': 'committed', 'line': 'E_col1', 'base': 72.22222222222221, 'arm': 22.22222222222222}, {'what': 'committed', 'line': 'E_col5', 'base': 50.0, 'arm': 22.22222222222222}, {'what': 'lock', 'line': 'E_col1', 'base': 50.0, 'arm': 0.0}, {'what': 'lock', 'line': 'E_col5', 'base': 33.33333333333333, 'arm': 11.11111111111111}, {'what': 'lock', 'line': 'E_row1', 'base': 27.77777777777778, 'arm': 5.555555555555555}, {'what': 'lock', 'line': 'E_row5', 'base': 22.22222222222222, 'arm': 0.0}]

**Decision: KEEP BASE.**
