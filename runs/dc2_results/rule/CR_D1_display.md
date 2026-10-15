### CR_D1: d1sr@CR.ref against d1sp@CR.ref (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 37.50 | 18.33 | 33.33 | 16.67 | -5.83 (-5 / -2 passes) |
| A2 | x1 | 74.17 | 45.00 | 50.83 | 30.83 | -37.50 (-28 / -17 passes) |
| A1 | x1 | 38.33 | 28.33 | 28.33 | 15.83 | -22.50 (-12 / -15 passes) |

Objective (weighted mean of committed + lock): base 74.38, arm 56.46.
Paired gain -17.92 points, 95% interval [-26.46, -9.17], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 72 / 50 / 78 / 33; arm 56 / 33 / 61 / 22
- lock: base 50 / 33 / 28 / 22; arm 17 / 22 / 11 / 6
- guard FAILS: [{'what': 'lock', 'line': 'E_col1', 'base': 50.0, 'arm': 16.666666666666664}, {'what': 'lock', 'line': 'E_row1', 'base': 27.77777777777778, 'arm': 11.11111111111111}, {'what': 'lock', 'line': 'E_row5', 'base': 22.22222222222222, 'arm': 5.555555555555555}]

**Decision: KEEP BASE.**
