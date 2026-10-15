### CR_D3_w0.5: d1sp@CR.w0.5 against d1sp@CR.ref (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 37.50 | 18.33 | 41.67 | 19.17 | +5.00 (+5 / +1 passes) |
| A2 | x1 | 74.17 | 45.00 | 41.67 | 66.67 | -10.83 (-39 / +26 passes) |
| A1 | x1 | 38.33 | 28.33 | 25.00 | 26.67 | -15.00 (-16 / -2 passes) |

Objective (weighted mean of committed + lock): base 74.38, arm 70.42.
Paired gain -3.96 points, 95% interval [-11.26, 3.33], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 72 / 50 / 78 / 33; arm 28 / 28 / 39 / 33
- lock: base 50 / 33 / 28 / 22; arm 0 / 17 / 6 / 0
- guard FAILS: [{'what': 'committed', 'line': 'E_col1', 'base': 72.22222222222221, 'arm': 27.77777777777778}, {'what': 'committed', 'line': 'E_row1', 'base': 77.77777777777779, 'arm': 38.88888888888889}, {'what': 'lock', 'line': 'E_col1', 'base': 50.0, 'arm': 0.0}, {'what': 'lock', 'line': 'E_col5', 'base': 33.33333333333333, 'arm': 16.666666666666664}, {'what': 'lock', 'line': 'E_row1', 'base': 27.77777777777778, 'arm': 5.555555555555555}, {'what': 'lock', 'line': 'E_row5', 'base': 22.22222222222222, 'arm': 0.0}]

**Decision: KEEP BASE.**
