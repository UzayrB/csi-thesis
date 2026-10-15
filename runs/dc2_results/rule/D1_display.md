### D1: d1sr against d1sp (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 37.50 | 18.33 | 33.33 | 16.67 | -5.83 (-5 / -2 passes) |
| A2 | x1 | 73.33 | 45.00 | 54.17 | 30.83 | -33.33 (-23 / -17 passes) |
| A1 | x1 | 45.83 | 28.33 | 32.50 | 15.83 | -25.83 (-16 / -15 passes) |

Objective (weighted mean of committed + lock): base 76.04, arm 58.33.
Paired gain -17.71 points, 95% interval [-26.06, -9.17], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 72 / 50 / 72 / 33; arm 56 / 44 / 44 / 28
- lock: base 50 / 33 / 28 / 22; arm 17 / 22 / 11 / 6
- guard FAILS: [{'what': 'lock', 'line': 'E_col1', 'base': 50.0, 'arm': 16.666666666666664}, {'what': 'lock', 'line': 'E_row1', 'base': 27.77777777777778, 'arm': 11.11111111111111}, {'what': 'lock', 'line': 'E_row5', 'base': 22.22222222222222, 'arm': 5.555555555555555}]

**Decision: KEEP BASE.**
