### RS2_D4_attn: d4_attn@CR.relgateU+abstain+a2w0.25 against d2p_ar@CR.relgateU+abstain+a2w0.25 (display lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 61.67 | 30.83 | 44.17 | 21.67 | -26.67 (-21 / -11 passes) |
| A2 | x1 | 71.67 | 49.17 | 60.83 | 32.50 | -27.50 (-13 / -20 passes) |
| A1 | x1 | 54.17 | 34.17 | 41.67 | 33.33 | -13.33 (-15 / -1 passes) |

Objective (weighted mean of committed + lock): base 98.54, arm 75.00.
Paired gain -23.54 points, 95% interval [-32.92, -14.17], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 61 / 61 / 94 / 67; arm 72 / 83 / 83 / 22
- lock: base 44 / 39 / 50 / 28; arm 61 / 72 / 50 / 11
- guard FAILS: [{'what': 'committed', 'line': 'E_row5', 'base': 66.66666666666666, 'arm': 22.22222222222222}, {'what': 'lock', 'line': 'E_row5', 'base': 27.77777777777778, 'arm': 11.11111111111111}]

**Decision: KEEP BASE.**
