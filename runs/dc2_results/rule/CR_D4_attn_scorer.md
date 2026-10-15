### CR_D4_attn: d4_attn@CR.relgateU against d2p_ar@CR.relgateU (scorer lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 58.33 | 30.83 | 43.33 | 21.67 | -24.17 (-18 / -11 passes) |
| A2 | x1 | 74.17 | 55.83 | 60.00 | 35.83 | -34.17 (-17 / -24 passes) |
| A1 | x1 | 50.00 | 37.50 | 40.83 | 35.00 | -11.67 (-11 / -3 passes) |

Objective (weighted mean of committed + lock): base 98.96, arm 75.42.
Paired gain -23.54 points, 95% interval [-33.34, -13.96], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 56 / 61 / 94 / 56; arm 72 / 72 / 89 / 17
- lock: base 50 / 28 / 61 / 28; arm 67 / 78 / 50 / 17
- guard FAILS: [{'what': 'committed', 'line': 'E_row5', 'base': 55.55555555555556, 'arm': 16.666666666666664}]

**Decision: KEEP BASE.**
