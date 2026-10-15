### RS2_D4_attn: d4_attn@CR.relgateU+abstain+a2w0.25 against d2p_ar@CR.relgateU+abstain+a2w0.25 (scorer lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 61.67 | 33.33 | 44.17 | 22.50 | -28.33 (-21 / -13 passes) |
| A2 | x1 | 71.67 | 54.17 | 60.83 | 36.67 | -28.33 (-13 / -21 passes) |
| A1 | x1 | 54.17 | 37.50 | 41.67 | 35.83 | -14.17 (-15 / -2 passes) |

Objective (weighted mean of committed + lock): base 101.88, arm 77.08.
Paired gain -24.79 points, 95% interval [-33.96, -15.83], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 61 / 61 / 94 / 67; arm 72 / 83 / 83 / 22
- lock: base 50 / 39 / 56 / 28; arm 61 / 83 / 50 / 17
- guard FAILS: [{'what': 'committed', 'line': 'E_row5', 'base': 66.66666666666666, 'arm': 22.22222222222222}]

**Decision: KEEP BASE.**
