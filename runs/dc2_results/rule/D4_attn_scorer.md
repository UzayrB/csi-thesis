### D4_attn: d4_attn@relgateU against d2p_ar@relgateU (scorer lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 58.33 | 30.83 | 43.33 | 21.67 | -24.17 (-18 / -11 passes) |
| A2 | x1 | 73.33 | 54.17 | 65.00 | 40.83 | -21.67 (-10 / -16 passes) |
| A1 | x1 | 56.67 | 35.83 | 41.67 | 36.67 | -14.17 (-18 / +1 passes) |

Objective (weighted mean of committed + lock): base 99.58, arm 78.54.
Paired gain -21.04 points, 95% interval [-30.84, -11.88], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 56 / 61 / 89 / 56; arm 72 / 72 / 83 / 17
- lock: base 50 / 33 / 61 / 28; arm 61 / 83 / 50 / 22
- guard FAILS: [{'what': 'committed', 'line': 'E_row5', 'base': 55.55555555555556, 'arm': 16.666666666666664}]

**Decision: KEEP BASE.**
