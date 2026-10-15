### CR_D3b_relgate+abstain+lw0.25_vs_ref: d1sp@CR.relgate+abstain+lw0.25 against d1sp@CR.ref (scorer lock, configuration A)

| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |
|---|---|---|---|---|---|---|
| B1 | x2 | 37.50 | 18.33 | 56.67 | 44.17 | +45.00 (+23 / +31 passes) |
| A2 | x1 | 74.17 | 50.83 | 53.33 | 35.83 | -35.83 (-25 / -18 passes) |
| A1 | x1 | 38.33 | 29.17 | 40.83 | 29.17 | +2.50 (+3 / +0 passes) |

Objective (weighted mean of committed + lock): base 76.04, arm 90.21.
Paired gain +14.17 points, 95% interval [6.45, 22.29], 360 passes.

Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):

- committed: base 72 / 50 / 78 / 33; arm 67 / 61 / 61 / 17
- lock: base 50 / 33 / 28 / 17; arm 22 / 22 / 6 / 6
- guard FAILS: [{'what': 'committed', 'line': 'E_row5', 'base': 33.33333333333333, 'arm': 16.666666666666664}, {'what': 'lock', 'line': 'E_col1', 'base': 50.0, 'arm': 22.22222222222222}, {'what': 'lock', 'line': 'E_row1', 'base': 27.77777777777778, 'arm': 5.555555555555555}, {'what': 'lock', 'line': 'E_row5', 'base': 16.666666666666664, 'arm': 5.555555555555555}]

**Decision: KEEP BASE.**
