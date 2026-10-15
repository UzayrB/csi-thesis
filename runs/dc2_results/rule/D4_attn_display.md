### D4_attn: d4_attn@relgateU against d2p_ar@relgateU (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 58.33 | 30.83 | 43.33 | 21.67 | -24.17 (-18 / -11 passes) |
| A2 | x1 | 73.33 | 49.17 | 65.00 | 32.50 | -25.00 (-10 / -20 passes) |
| A1 | x1 | 56.67 | 34.17 | 41.67 | 33.33 | -15.83 (-18 / -1 passes) |

Objective (weighted mean of committed + lock): base 97.92, arm 75.62.
Paired gain -22.29 points, 95% interval [-31.68, -13.54], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 56 / 61 / 89 / 56; arm 72 / 72 / 83 / 17
- lock: base 44 / 39 / 50 / 28; arm 61 / 72 / 50 / 11
- guard FAILS: [{'what': 'committed', 'line': 'E_row5', 'base': 55.55555555555556, 'arm': 16.666666666666664}, {'what': 'lock', 'line': 'E_row5', 'base': 27.77777777777778, 'arm': 11.11111111111111}]

**Decision: KEEP BASE.**
