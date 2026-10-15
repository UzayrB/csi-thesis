### RS_D4_attn: d4_attn@CR.relgateU+abstain against d2p_ar@CR.relgateU+abstain (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 56.67 | 30.83 | 41.67 | 21.67 | -24.17 (-18 / -11 passes) |
| A2 | x1 | 71.67 | 49.17 | 61.67 | 32.50 | -26.67 (-12 / -20 passes) |
| A1 | x1 | 53.33 | 34.17 | 43.33 | 33.33 | -10.83 (-12 / -1 passes) |

Objective (weighted mean of committed + lock): base 95.83, arm 74.38.
Paired gain -21.46 points, 95% interval [-30.83, -12.29], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 61 / 56 / 94 / 56; arm 72 / 78 / 83 / 17
- lock: base 44 / 39 / 50 / 28; arm 61 / 72 / 50 / 11
- guard FAILS: [{'what': 'committed', 'line': 'E_row5', 'base': 55.55555555555556, 'arm': 16.666666666666664}, {'what': 'lock', 'line': 'E_row5', 'base': 27.77777777777778, 'arm': 11.11111111111111}]

**Decision: KEEP BASE.**
