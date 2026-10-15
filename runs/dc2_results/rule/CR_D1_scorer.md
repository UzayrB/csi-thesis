### CR_D1: d1sr@CR.ref against d1sp@CR.ref (scorer lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 37.50 | 18.33 | 33.33 | 15.83 | -6.67 (-5 / -3 passes) |
| A2 | x1 | 74.17 | 50.83 | 50.83 | 36.67 | -37.50 (-28 / -17 passes) |
| A1 | x1 | 38.33 | 29.17 | 28.33 | 14.17 | -25.00 (-12 / -18 passes) |

Objective (weighted mean of committed + lock): base 76.04, arm 57.08.
Paired gain -18.96 points, 95% interval [-27.29, -10.82], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 72 / 50 / 78 / 33; arm 56 / 33 / 61 / 22
- lock: base 50 / 33 / 28 / 17; arm 22 / 33 / 17 / 11
- guard FAILS: [{'what': 'lock', 'line': 'E_col1', 'base': 50.0, 'arm': 22.22222222222222}]

**Decision: KEEP BASE.**
