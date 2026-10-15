### D1: d1sr against d1sp (scorer lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 37.50 | 18.33 | 33.33 | 15.83 | -6.67 (-5 / -3 passes) |
| A2 | x1 | 73.33 | 52.50 | 54.17 | 33.33 | -38.33 (-23 / -23 passes) |
| A1 | x1 | 45.83 | 30.83 | 32.50 | 17.50 | -26.67 (-16 / -16 passes) |

Objective (weighted mean of committed + lock): base 78.54, arm 58.96.
Paired gain -19.58 points, 95% interval [-27.51, -11.46], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 72 / 50 / 72 / 33; arm 56 / 44 / 44 / 28
- lock: base 50 / 33 / 28 / 22; arm 17 / 28 / 17 / 11
- guard FAILS: [{'what': 'lock', 'line': 'E_col1', 'base': 50.0, 'arm': 16.666666666666664}, {'what': 'lock', 'line': 'E_row5', 'base': 22.22222222222222, 'arm': 11.11111111111111}]

**Decision: KEEP BASE.**
