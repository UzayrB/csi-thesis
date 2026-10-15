### RS_D4_attn: d4_attn@CR.relgateU+abstain against d2p_ar@CR.relgateU+abstain (scorer lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 56.67 | 33.33 | 41.67 | 21.67 | -26.67 (-18 / -14 passes) |
| A2 | x1 | 71.67 | 55.00 | 61.67 | 38.33 | -26.67 (-12 / -20 passes) |
| A1 | x1 | 53.33 | 37.50 | 43.33 | 35.83 | -11.67 (-12 / -2 passes) |

Objective (weighted mean of committed + lock): base 99.38, arm 76.46.
Paired gain -22.92 points, 95% interval [-32.08, -13.33], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 61 / 56 / 94 / 56; arm 72 / 78 / 83 / 17
- lock: base 50 / 28 / 56 / 28; arm 67 / 83 / 50 / 17
- guard FAILS: [{'what': 'committed', 'line': 'E_row5', 'base': 55.55555555555556, 'arm': 16.666666666666664}]

**Decision: KEEP BASE.**
