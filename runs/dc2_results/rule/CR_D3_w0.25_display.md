### CR_D3_w0.25: d1sp@CR.w0.25 against d1sp@CR.ref (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 37.50 | 18.33 | 42.50 | 20.00 | +6.67 (+6 / +2 passes) |
| A2 | x1 | 74.17 | 45.00 | 59.17 | 67.50 | +7.50 (-18 / +27 passes) |
| A1 | x1 | 38.33 | 28.33 | 29.17 | 28.33 | -9.17 (-11 / +0 passes) |

Objective (weighted mean of committed + lock): base 74.38, arm 77.29.
Paired gain +2.92 points, 95% interval [-2.92, 9.58], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 72 / 50 / 78 / 33; arm 33 / 28 / 72 / 39
- lock: base 50 / 33 / 28 / 22; arm 22 / 28 / 11 / 0
- guard FAILS: [{'what': 'committed', 'line': 'E_col1', 'base': 72.22222222222221, 'arm': 33.33333333333333}, {'what': 'lock', 'line': 'E_col1', 'base': 50.0, 'arm': 22.22222222222222}, {'what': 'lock', 'line': 'E_row1', 'base': 27.77777777777778, 'arm': 11.11111111111111}, {'what': 'lock', 'line': 'E_row5', 'base': 22.22222222222222, 'arm': 0.0}]

**Decision: KEEP BASE.**
